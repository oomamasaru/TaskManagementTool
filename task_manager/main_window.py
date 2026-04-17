from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from const import message as msg
from task_manager.controller import BoardController
from task_manager.dialogs import (
    CompletedTasksDialog,
    LabelManagerDialog,
    SettingsDialog,
    StatusManagerDialog,
    TaskDialog,
)
from task_manager.models import Label, Task
from task_manager.widgets import TaskCardWidget, TaskListWidget, darken_hex_color


class MainWindow(QMainWindow):
    """メインウィンドウ"""

    def __init__(self, controller: BoardController) -> None:
        """イニシャライザ

        Args:
            controller (BoardController): ボードコントローラ
        """
        super().__init__()
        self.controller = controller
        self.setWindowTitle(msg.TITLE_APP)
        self.resize(1300, 760)

        self.task_lists: dict[str, TaskListWidget] = {}
        self.active_label_filters: set[str] = set()
        self.filter_no_label = False
        self.label_buttons: dict[str, QPushButton] = {}
        self.no_label_button: QPushButton | None = None
        self.completed_dialog: CompletedTasksDialog | None = None

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._refresh_all()

    def _build_ui(self) -> None:
        """UIをビルドする"""
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        self.setCentralWidget(central)

        top_bar = QHBoxLayout()
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText(msg.LBL_SEARCH_TASK)
        self.filter_clear_button = QPushButton(msg.BTN_FILTER_CLEAR, self)
        self.completed_button = QPushButton(msg.BTN_COMPLETED_TASKS, self)
        top_bar.addWidget(self.search_edit, 1)
        top_bar.addWidget(self.filter_clear_button)
        top_bar.addWidget(self.completed_button)
        root.addLayout(top_bar)

        self.label_filter_wrap = QWidget(self)
        self.label_filter_layout = QHBoxLayout(self.label_filter_wrap)
        self.label_filter_layout.setContentsMargins(0, 0, 0, 0)
        self.label_filter_layout.setSpacing(6)

        label_scroll = QScrollArea(self)
        label_scroll.setWidgetResizable(True)
        label_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        label_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        label_scroll.setFrameShape(QFrame.Shape.NoFrame)
        label_scroll.setMaximumHeight(52)
        label_scroll.setWidget(self.label_filter_wrap)
        root.addWidget(label_scroll)

        self.board_scroll = QScrollArea(self)
        self.board_scroll.setWidgetResizable(True)
        self.board_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.board_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.board_content = QWidget(self)
        self.board_layout = QHBoxLayout(self.board_content)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(10)
        self.board_scroll.setWidget(self.board_content)
        root.addWidget(self.board_scroll, 1)

    def _build_menu(self) -> None:
        """メニューをビルドする"""
        manage_menu = self.menuBar().addMenu(msg.MENU_MANAGE)
        action_menu = self.menuBar().addMenu(msg.MENU_ACTION)

        self.add_category_action = QAction(msg.MENU_ADD_CATEGORY, self)
        self.delete_category_action = QAction(msg.MENU_DELETE_CATEGORY, self)
        self.label_manage_action = QAction(msg.MENU_LABEL_MANAGE, self)
        self.status_manage_action = QAction(msg.MENU_STATUS_MANAGE, self)
        self.settings_action = QAction(msg.MENU_SETTINGS, self)
        self.undo_action = QAction(msg.MENU_UNDO, self)
        self.redo_action = QAction(msg.MENU_REDO, self)

        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])

        manage_menu.addAction(self.add_category_action)
        manage_menu.addAction(self.delete_category_action)
        manage_menu.addSeparator()
        manage_menu.addAction(self.label_manage_action)
        manage_menu.addAction(self.status_manage_action)
        manage_menu.addSeparator()
        manage_menu.addAction(self.settings_action)

        action_menu.addAction(self.undo_action)
        action_menu.addAction(self.redo_action)

    def _connect_signals(self) -> None:
        """シグナルを接続する"""
        self.search_edit.textChanged.connect(self._refresh_board)
        self.filter_clear_button.clicked.connect(self._clear_filters)
        self.completed_button.clicked.connect(self._open_completed_dialog)

        self.add_category_action.triggered.connect(self._add_category)
        self.delete_category_action.triggered.connect(self._delete_category)
        self.label_manage_action.triggered.connect(self._open_label_manager)
        self.status_manage_action.triggered.connect(self._open_status_manager)
        self.settings_action.triggered.connect(self._open_settings)
        self.undo_action.triggered.connect(self._undo)
        self.redo_action.triggered.connect(self._redo)

        self.controller.changed.connect(self._on_board_changed)
        self.controller.undo_redo_changed.connect(self._update_undo_redo_actions)

    def _on_board_changed(self) -> None:
        """ボード変更時の処理"""
        self._refresh_all()
        if self.completed_dialog and self.completed_dialog.isVisible():
            self._refresh_completed_dialog_data()

    def _refresh_all(self) -> None:
        """全データをリフレッシュする"""
        self._refresh_label_filters()
        self._refresh_board()
        self._update_undo_redo_actions()

    def _refresh_label_filters(self) -> None:
        while self.label_filter_layout.count():
            item = self.label_filter_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.label_buttons.clear()
        labels = self.controller.labels
        known_ids = {x.id for x in labels}
        self.active_label_filters = {x for x in self.active_label_filters if x in known_ids}

        for label in labels:
            button = QPushButton(label.name, self.label_filter_wrap)
            button.setCheckable(True)
            button.setChecked(label.id in self.active_label_filters)
            button.clicked.connect(
                lambda checked, label_id=label.id: self._toggle_label_filter(label_id, checked)
            )
            self._apply_label_button_style(button, label, button.isChecked())
            self.label_filter_layout.addWidget(button)
            self.label_buttons[label.id] = button

        self.no_label_button = QPushButton(msg.LBL_NO_LABEL_FILTER, self.label_filter_wrap)
        self.no_label_button.setCheckable(True)
        self.no_label_button.setChecked(self.filter_no_label)
        self.no_label_button.clicked.connect(self._toggle_no_label_filter)
        self._apply_no_label_button_style(self.no_label_button, self.no_label_button.isChecked())
        self.label_filter_layout.addWidget(self.no_label_button)
        self.label_filter_layout.addStretch(1)

    def _apply_label_button_style(self, button: QPushButton, label: Label, checked: bool) -> None:
        """ラベルボタンのスタイルを適用する

        Args:
            button (QPushButton): ボタン
            label (Label): ラベル
            checked (bool): チェック状態
        """
        if checked:
            bg = label.color
            fg = "#111827"
        else:
            bg = darken_hex_color(label.color, factor=0.45)
            fg = "#F9FAFB"
        button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid #374151;
                border-radius: 14px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            """
        )

    def _apply_no_label_button_style(self, button: QPushButton, checked: bool) -> None:
        """ラベル設定なしボタンのスタイルを適用する

        Args:
            button (QPushButton): ボタン
            checked (bool): チェック状態
        """
        if checked:
            bg = "#D1D5DB"
            fg = "#111827"
        else:
            bg = "#4B5563"
            fg = "#F9FAFB"
        button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid #374151;
                border-radius: 14px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            """
        )

    def _toggle_label_filter(self, label_id: str, checked: bool) -> None:
        """ラベルフィルターを切り替える

        Args:
            label_id (str): ラベルID
            checked (bool): チェック状態
        """
        if checked:
            self.active_label_filters.add(label_id)
        else:
            self.active_label_filters.discard(label_id)
        label = self.controller.get_label(label_id)
        if label and label_id in self.label_buttons:
            self._apply_label_button_style(self.label_buttons[label_id], label, checked)
        self._refresh_board()

    def _toggle_no_label_filter(self, checked: bool) -> None:
        """ラベル設定なしフィルターを切り替える

        Args:
            checked (bool): チェック状態
        """
        self.filter_no_label = checked
        if self.no_label_button:
            self._apply_no_label_button_style(self.no_label_button, checked)
        self._refresh_board()

    def _clear_filters(self) -> None:
        """フィルターをクリアする"""
        self.search_edit.clear()
        self.active_label_filters.clear()
        self.filter_no_label = False
        self._refresh_label_filters()
        self._refresh_board()

    def _is_filter_active(self) -> bool:
        """フィルターがアクティブかどうかを判定する"""
        return bool(
            self.search_edit.text().strip() or self.active_label_filters or self.filter_no_label
        )

    def _filtered_tasks(self) -> list[Task]:
        """フィルターされたタスクを取得する"""
        query = self.search_edit.text().strip().lower()
        status_map = {x.id: x for x in self.controller.statuses}
        tasks = []
        for task in self.controller.tasks:
            status = status_map.get(task.status_id)
            if status and status.hides_from_board:
                continue

            text_match = True
            if query:
                text = f"{task.title} {task.detail}".lower()
                text_match = query in text

            label_match = True
            if self.active_label_filters or self.filter_no_label:
                label_match = bool(set(task.label_ids) & self.active_label_filters)
                if self.filter_no_label and not task.label_ids:
                    label_match = True

            if text_match and label_match:
                tasks.append(task)
        return tasks

    def _refresh_board(self) -> None:
        """ボードをリフレッシュする"""
        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.task_lists.clear()

        filter_active = self._is_filter_active()
        tasks = self._filtered_tasks()
        tasks_by_category: dict[str, list[Task]] = {}
        for task in sorted(tasks, key=lambda x: (x.category_id, x.sort_order, x.updated_at)):
            tasks_by_category.setdefault(task.category_id, []).append(task)

        labels_map = {x.id: x for x in self.controller.labels}
        status_map = {x.id: x for x in self.controller.statuses}

        for category in self.controller.categories:
            column = QFrame(self.board_content)
            column.setFrameShape(QFrame.Shape.StyledPanel)
            column.setMinimumWidth(300)
            column.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(8, 8, 8, 8)
            column_layout.setSpacing(6)

            header = QHBoxLayout()
            title = QLabel(category.name, column)
            title.setStyleSheet("font-size: 16px; font-weight: 700;")
            add_button = QPushButton(msg.BTN_TASK_ADD, column)
            add_button.clicked.connect(
                lambda _=False, category_id=category.id: self._open_task_dialog(
                    default_category_id=category_id
                )
            )
            header.addWidget(title, 1)
            header.addWidget(add_button, 0)
            column_layout.addLayout(header)

            list_widget = TaskListWidget(category.id, column)
            if filter_active:
                list_widget.setDragDropMode(list_widget.DragDropMode.NoDragDrop)
                list_widget.setToolTip(msg.TIP_NO_REORDER_FILTER)
            list_widget.itemClicked.connect(
                lambda item, lw=list_widget: self._on_task_clicked(lw, item)
            )
            list_widget.customContextMenuRequested.connect(
                lambda pos, lw=list_widget: self._show_task_context_menu(lw, pos)
            )
            list_widget.dropped.connect(self._on_tasks_dropped)
            column_layout.addWidget(list_widget, 1)

            for task in tasks_by_category.get(category.id, []):
                list_item = QListWidgetItem()
                list_item.setData(Qt.ItemDataRole.UserRole, task.id)
                card = TaskCardWidget(
                    task=task,
                    status=status_map.get(task.status_id),
                    labels=[labels_map[x] for x in task.label_ids if x in labels_map],
                    parent=list_widget,
                )
                list_item.setSizeHint(card.sizeHint())
                list_widget.addItem(list_item)
                list_widget.setItemWidget(list_item, card)

            self.task_lists[category.id] = list_widget
            self.board_layout.addWidget(column)

        self.board_layout.addStretch(1)

    def _on_task_clicked(self, list_widget: TaskListWidget, item: QListWidgetItem) -> None:
        """タスククリック時の処理"""
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            self._open_task_dialog(
                task_id=str(task_id), default_category_id=list_widget.category_id
            )

    def _show_task_context_menu(self, list_widget: TaskListWidget, pos) -> None:
        """タスクコンテキストメニューを表示する"""
        item = list_widget.itemAt(pos)
        if not item:
            return
        task_id = str(item.data(Qt.ItemDataRole.UserRole))
        task = self.controller.get_task(task_id)
        if not task:
            return

        menu = QMenu(self)
        delete_action = menu.addAction(msg.BTN_DELETE)
        action = menu.exec(list_widget.viewport().mapToGlobal(pos))
        if action != delete_action:
            return

        answer = QMessageBox.warning(
            self,
            msg.TITLE_CONFIRM,
            msg.MSG_CONFIRM_DELETE_TASK.format(title=task.title),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._run_safely(lambda: self.controller.delete_task(task_id))

    def _open_task_dialog(
        self, task_id: str | None = None, default_category_id: str | None = None
    ) -> None:
        """タスクダイアログを開く"""
        task = self.controller.get_task(task_id) if task_id else None
        dialog = TaskDialog(
            categories=self.controller.categories,
            labels=self.controller.labels,
            statuses=self.controller.statuses,
            task=task,
            default_category_id=default_category_id,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        result = dialog.result_data
        if not result:
            return

        if result.action == "save":
            if task:
                self._run_safely(lambda: self.controller.update_task(task.id, **result.payload))
            else:
                self._run_safely(lambda: self.controller.add_task(**result.payload))
            return

        if result.action == "delete" and task:
            answer = QMessageBox.warning(
                self,
                msg.TITLE_CONFIRM,
                msg.MSG_CONFIRM_DELETE_TASK.format(title=task.title),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._run_safely(lambda: self.controller.delete_task(task.id))
            return

        if result.action == "duplicate" and task:
            self._run_safely(lambda: self.controller.duplicate_task(task.id))

    def _on_tasks_dropped(self) -> None:
        """タスクドロップ時の処理"""
        if self._is_filter_active():
            return
        layout: dict[str, list[str]] = {}
        for category_id, list_widget in self.task_lists.items():
            ids: list[str] = []
            for index in range(list_widget.count()):
                item = list_widget.item(index)
                task_id = item.data(Qt.ItemDataRole.UserRole)
                if task_id:
                    ids.append(str(task_id))
            layout[category_id] = ids
        self._run_safely(lambda: self.controller.apply_board_layout(layout))

    def _open_completed_dialog(self) -> None:
        """完了済みタスクダイアログを開く"""
        if not self.completed_dialog:
            self.completed_dialog = CompletedTasksDialog(self)
            self.completed_dialog.edit_requested.connect(self._edit_completed_task)
            self.completed_dialog.restore_requested.connect(self._restore_completed_task)
            self.completed_dialog.delete_requested.connect(self._delete_completed_task)
        self._refresh_completed_dialog_data()
        self.completed_dialog.show()
        self.completed_dialog.raise_()
        self.completed_dialog.activateWindow()

    def _refresh_completed_dialog_data(self) -> None:
        if not self.completed_dialog:
            return
        category_names = {x.id: x.name for x in self.controller.categories}
        label_names = {x.id: x.name for x in self.controller.labels}
        self.completed_dialog.set_context(
            self.controller.get_completed_tasks(),
            category_names,
            label_names,
        )

    def _edit_completed_task(self, task_id: str) -> None:
        """完了済みタスクを編集"""
        self._open_task_dialog(task_id=task_id)
        if self.completed_dialog and self.completed_dialog.isVisible():
            self._refresh_completed_dialog_data()

    def _restore_completed_task(self, task_id: str) -> None:
        """完了済みタスクを復元"""
        self._run_safely(lambda: self.controller.restore_completed_task(task_id))

    def _delete_completed_task(self, task_id: str) -> None:
        task = self.controller.get_task(task_id)
        if not task:
            return
        answer = QMessageBox.warning(
            self,
            msg.TITLE_CONFIRM,
            msg.MSG_CONFIRM_DELETE_COMPLETED_TASK.format(title=task.title),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._run_safely(lambda: self.controller.delete_task(task_id))

    def _add_category(self) -> None:
        """カテゴリを追加"""
        name, ok = QInputDialog.getText(self, msg.TITLE_ADD_CATEGORY, msg.LBL_CATEGORY_NAME)
        if not ok:
            return
        self._run_safely(lambda: self.controller.add_category(name))

    def _delete_category(self) -> None:
        """カテゴリを削除"""
        categories = self.controller.categories
        if len(categories) <= 1:
            QMessageBox.warning(self, msg.TITLE_DELETE_IMPOSSIBLE, msg.ERR_CATEGORY_MIN_REQUIRED)
            return

        options = [f"{x.name} ({x.id})" for x in categories]
        selected, ok = QInputDialog.getItem(
            self,
            msg.TITLE_DELETE_CATEGORY,
            msg.LBL_SELECT_CATEGORY_TO_DELETE,
            options,
            0,
            False,
        )
        if not ok:
            return
        category = next((x for x in categories if selected.endswith(f"({x.id})")), None)
        if not category:
            return

        task_count = len([x for x in self.controller.tasks if x.category_id == category.id])
        if task_count != 0:
            message = msg.MSG_CONFIRM_DELETE_CATEGORY_WITH_TASKS.format(
                name=category.name, count=task_count
            )
            delete_button_text = msg.BTN_DELETE_WITH_TASKS

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle(msg.TITLE_CONFIRM_DELETE_CATEGORY)
            box.setText(message)
            delete_button = box.addButton(delete_button_text, QMessageBox.ButtonRole.AcceptRole)
            cancel_button = box.addButton(msg.BTN_DELETE_CANCEL, QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(cancel_button)
            box.exec()
            if box.clickedButton() != delete_button:
                return
        self._run_safely(lambda: self.controller.delete_category(category.id))

    def _open_label_manager(self) -> None:
        """ラベルマネージャーを開く"""
        dialog = LabelManagerDialog(self.controller, self)
        dialog.exec()

    def _open_status_manager(self) -> None:
        """ステータスマネージャーを開く"""
        dialog = StatusManagerDialog(self.controller, self)
        dialog.exec()

    def _open_settings(self) -> None:
        """設定ダイアログを開く"""
        SettingsDialog(self).exec()

    def _undo(self) -> None:
        """元に戻す"""
        self._run_safely(self.controller.undo)

    def _redo(self) -> None:
        """やり直し"""
        self._run_safely(self.controller.redo)

    def _update_undo_redo_actions(self) -> None:
        """元に戻す/やり直しの有効/無効状態を更新する"""
        undo_text = self.controller.undo_text
        redo_text = self.controller.redo_text
        self.undo_action.setEnabled(self.controller.can_undo)
        self.redo_action.setEnabled(self.controller.can_redo)
        self.undo_action.setText(f"{msg.MENU_UNDO} ({undo_text})" if undo_text else msg.MENU_UNDO)
        self.redo_action.setText(f"{msg.MENU_REDO} ({redo_text})" if redo_text else msg.MENU_REDO)

    def _run_safely(self, action: Callable[[], object]) -> None:
        try:
            action()
        except Exception as exc:
            QMessageBox.critical(self, msg.TITLE_ERROR, str(exc))


def run_app(controller: BoardController) -> None:
    """アプリケーションを起動する

    Args:
        controller (BoardController): ボードコントローラ
    """
    app = QApplication.instance() or QApplication([])
    window = MainWindow(controller)
    window.show()
    app.exec()
