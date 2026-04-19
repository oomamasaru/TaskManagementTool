from __future__ import annotations

import contextlib
from collections.abc import Callable

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.app_controller import AppController
from ui.dialogs.category_manager_dialog import CategoryManagerDialog
from ui.dialogs.completed_tasks_dialog import CompletedTasksDialog
from ui.dialogs.label_manager_dialog import LabelManagerDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.status_manager_dialog import StatusManagerDialog
from ui.dialogs.task_dialog import TaskDialog
from ui.widgets.board_widget import BoardWidget
from ui.widgets.label_filter_bar import LabelFilterBar
from ui.widgets.search_bar_widget import SearchBarWidget


class MainWindow(QMainWindow):
    """メインウィンドウ"""

    def __init__(self, controller: AppController) -> None:
        """イニシャライザ

        Args:
            controller (AppController): アプリケーションコントローラー
        """
        super().__init__()
        self._controller = controller
        self._store = controller.store
        self.setWindowTitle("Task Management Tool")
        self.resize(1280, 760)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self._search_bar = SearchBarWidget()
        self._search_bar.search_changed.connect(self._on_filter_changed)
        self._search_bar.clear_requested.connect(self._on_filter_changed)
        layout.addWidget(self._search_bar)

        self._label_filter_bar = LabelFilterBar()
        self._label_filter_bar.changed.connect(self._on_filter_changed)
        layout.addWidget(self._label_filter_bar)

        self._completed_button = QPushButton("完了済みタスク一覧")
        self._completed_button.clicked.connect(self.open_completed_tasks_dialog)
        layout.addWidget(self._completed_button)

        self._board_widget = BoardWidget()
        self._board_widget.add_task_requested.connect(self._open_add_task_dialog_for_category)
        self._board_widget.task_open_requested.connect(self.open_task_dialog)
        self._board_widget.task_context_requested.connect(self._open_task_context_menu)
        self._board_widget.category_context_requested.connect(self._open_category_context_menu)
        self._board_widget.board_reordered.connect(self._on_board_reordered)
        layout.addWidget(self._board_widget, stretch=1)

        self._create_menu()

        self._store.board_changed.connect(self.refresh_view)
        self._store.undo_stack.canUndoChanged.connect(self._sync_undo_redo_state)
        self._store.undo_stack.canRedoChanged.connect(self._sync_undo_redo_state)
        self.refresh_view()

    def open_task_dialog(
        self,
        task_id: str | None = None,
        default_category_id: str | None = None,
    ) -> None:
        """タスクダイアログを開く

        Args:
            task_id (str | None): タスクID
            default_category_id (str | None): デフォルトカテゴリID
        """
        categories = self._store.get_categories()
        labels = self._store.get_labels()
        statuses = self._store.get_statuses()
        task = self._store.find_task(task_id) if task_id else None
        resolved_category_id = (
            task.category_id
            if task
            else (default_category_id or (categories[0].id if categories else None))
        )
        if task is None and not resolved_category_id:
            self._show_error("カテゴリがありません。先にカテゴリを追加してください。")
            return

        dialog = TaskDialog(
            labels=labels,
            statuses=statuses,
            task=task,
            default_category_id=resolved_category_id,
            parent=self,
        )
        if dialog.exec() == dialog.DialogCode.Rejected:
            return

        try:
            if task and dialog.request_delete():
                self._confirm_and_delete_task(task.id)
                return
            if task and dialog.request_duplicate():
                self._controller.duplicate_task(task.id)
                return
            input_data = dialog.get_input()
            if task is None:
                self._controller.add_task(input_data)
            else:
                self._controller.edit_task(task.id, input_data)
        except Exception as exc:
            self._show_error(str(exc))

    def _open_add_task_dialog_for_category(self, category_id: str) -> None:
        """カテゴリごとのタスクダイアログを開く

        Args:
            category_id (str): カテゴリID
        """
        self.open_task_dialog(default_category_id=category_id)

    def open_completed_tasks_dialog(self) -> None:
        """完了済みタスクダイアログを開く"""
        dialog = CompletedTasksDialog(self)
        dialog.load_completed_tasks(
            tasks=self._controller.get_completed_tasks(),
            categories=self._store.get_categories(),
            labels=self._store.get_labels(),
        )
        if dialog.exec() == dialog.DialogCode.Rejected:
            return

        task_id = dialog.selected_task_id()
        if task_id is None:
            return
        try:
            if dialog.action == "restore":
                self._controller.restore_completed_task(task_id)
            elif dialog.action == "delete":
                self._controller.delete_completed_task(task_id)
        except Exception as exc:
            self._show_error(str(exc))

    def open_label_manager_dialog(self) -> None:
        """ラベルマネージャーダイアログを開く"""
        dialog = LabelManagerDialog(self)

        def refresh() -> None:
            dialog.load_labels(self._store.get_labels())

        refresh()
        dialog.add_requested.connect(self._on_add_label)
        dialog.update_requested.connect(self._on_update_label)
        dialog.delete_requested.connect(self._on_delete_label)
        self._store.board_changed.connect(refresh)
        try:
            dialog.exec()
        finally:
            with contextlib.suppress(TypeError):
                self._store.board_changed.disconnect(refresh)

    def open_status_manager_dialog(self) -> None:
        """ステータスマネージャーダイアログを開く"""
        dialog = StatusManagerDialog(self)

        def refresh() -> None:
            """リフレッシュ"""
            dialog.load_statuses(self._store.get_statuses())

        refresh()
        dialog.add_requested.connect(self._on_add_status)
        dialog.update_requested.connect(self._on_update_status)
        dialog.delete_requested.connect(self._on_delete_status)
        dialog.reorder_requested.connect(self._on_reorder_statuses)
        self._store.board_changed.connect(refresh)
        try:
            dialog.exec()
        finally:
            with contextlib.suppress(TypeError):
                self._store.board_changed.disconnect(refresh)

    def open_category_manager_dialog(self) -> None:
        """カテゴリマネージャーダイアログを開く"""
        dialog = CategoryManagerDialog(self)

        def refresh() -> None:
            dialog.load_categories(self._store.get_categories())

        refresh()
        dialog.add_requested.connect(self._on_add_category)
        dialog.update_requested.connect(self._on_update_category)
        dialog.delete_requested.connect(self._on_delete_category)
        self._store.board_changed.connect(refresh)
        try:
            dialog.exec()
        finally:
            with contextlib.suppress(TypeError):
                self._store.board_changed.disconnect(refresh)

    def open_settings_dialog(self) -> None:
        """設定ダイアログを開く"""
        dialog = SettingsDialog(self)
        dialog.load_settings(self._store.board_data.settings)
        if dialog.exec() == dialog.DialogCode.Rejected:
            return

        self._store.board_data.settings = dialog.get_input()
        try:
            self._controller.save()
        except Exception as exc:
            self._show_error(str(exc))

    def refresh_view(self) -> None:
        """ビューをリフレッシュする"""
        categories = self._store.get_categories()
        labels = self._store.get_labels()
        statuses = self._store.get_statuses()
        status_map = {status.id: status for status in statuses}
        label_map = {label.id: label for label in labels}
        tasks_by_category = {
            category.id: self._store.get_tasks_for_category(category.id) for category in categories
        }
        self._board_widget.rebuild_columns(
            categories=categories,
            tasks_by_category=tasks_by_category,
            statuses=status_map,
            labels=label_map,
            date_format=self._store.board_data.settings.date_format,
        )
        self._label_filter_bar.set_labels(labels)
        self._label_filter_bar.set_active(
            self._store.filter_condition.active_label_ids,
            self._store.filter_condition.include_no_label,
        )
        self._sync_undo_redo_state()

    def _create_menu(self) -> None:
        """メニューを作成する"""
        menu_bar = self.menuBar()
        manage_menu = menu_bar.addMenu("管理")
        edit_menu = menu_bar.addMenu("編集")

        open_category_action = QAction("カテゴリ管理", self)
        open_category_action.triggered.connect(self.open_category_manager_dialog)
        manage_menu.addAction(open_category_action)

        open_label_action = QAction("ラベル管理", self)
        open_label_action.triggered.connect(self.open_label_manager_dialog)
        manage_menu.addAction(open_label_action)

        open_status_action = QAction("ステータス管理", self)
        open_status_action.triggered.connect(self.open_status_manager_dialog)
        manage_menu.addAction(open_status_action)

        settings_action = QAction("設定", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        manage_menu.addAction(settings_action)

        self._undo_action = QAction("Undo", self)
        self._undo_action.setShortcut("Ctrl+Z")
        self._undo_action.triggered.connect(self._controller.undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("Redo", self)
        self._redo_action.setShortcut("Ctrl+Y")
        self._redo_action.triggered.connect(self._controller.redo)
        edit_menu.addAction(self._redo_action)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """クローズイベントハンドラ"""
        with contextlib.suppress(TypeError, RuntimeError):
            self._store.board_changed.disconnect(self.refresh_view)
        with contextlib.suppress(TypeError, RuntimeError):
            self._store.undo_stack.canUndoChanged.disconnect(self._sync_undo_redo_state)
        with contextlib.suppress(TypeError, RuntimeError):
            self._store.undo_stack.canRedoChanged.disconnect(self._sync_undo_redo_state)
        super().closeEvent(event)

    def _sync_undo_redo_state(self, *_args: object) -> None:
        """アンドゥリドゥ状態を同期する"""
        try:
            self._undo_action.setEnabled(self._store.undo_stack.canUndo())
            self._redo_action.setEnabled(self._store.undo_stack.canRedo())
        except RuntimeError:
            # Window teardown can outlive QUndoStack (C++ object), so ignore late signal calls.
            return

    def _on_filter_changed(self, *_args: object) -> None:
        """フィルター変更ハンドラ"""
        self._controller.set_filter(
            search_text=self._search_bar.search_text(),
            active_label_ids=self._label_filter_bar.active_label_ids(),
            include_no_label=self._label_filter_bar.include_no_label(),
        )

    def _open_task_context_menu(self, task_id: str, pos: QPoint) -> None:
        """タスクコンテキストメニューを開く

        Args:
            task_id (str): タスクID
            pos (QPoint): マウスカーソル位置
        """
        task = self._store.find_task(task_id)
        if task is None:
            return

        menu = QMenu(self)
        edit_action = menu.addAction("編集")
        duplicate_action = menu.addAction("複製")
        delete_action = menu.addAction("削除")
        menu.addSeparator()

        status_menu = menu.addMenu("ステータス")
        for status in self._store.get_statuses():
            action = status_menu.addAction(status.name)
            action.setCheckable(True)
            action.setChecked(task.status_id == status.id)
            action.triggered.connect(
                lambda _checked=False, status_id=status.id: self._on_change_status(
                    task_id, status_id
                )
            )

        selected = menu.exec(pos)
        if selected is edit_action:
            self.open_task_dialog(task_id)
        elif selected is duplicate_action:
            self._controller.duplicate_task(task_id)
        elif selected is delete_action:
            self._confirm_and_delete_task(task_id)

    def _open_category_context_menu(self, category_id: str, pos: QPoint) -> None:
        """カテゴリコンテキストメニューを開く

        Args:
            category_id (str): カテゴリID
            pos (QPoint): マウスカーソル位置
        """
        category = self._store.find_category(category_id)
        if category is None:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("カテゴリ削除")
        selected = menu.exec(pos)
        if selected is delete_action:
            self._on_delete_category(category_id)

    def _on_change_status(self, task_id: str, status_id: str) -> None:
        """ステータス変更ハンドラ

        Args:
            task_id (str): タスクID
            status_id (str): ステータスID
        """
        self._run_controller_action(self._controller.change_task_status, task_id, status_id)

    def _on_board_reordered(self, moved_task_id: str, snapshot: dict[str, list[str]]) -> None:
        """ボード再配置ハンドラ

        Args:
            moved_task_id (str): 移動したタスクID
            snapshot (dict[str, list[str]]): 移動前のタスク配置スナップショット
        """
        task_id = moved_task_id or self._detect_moved_task_id(snapshot)
        if not task_id:
            return
        self._run_controller_action(self._controller.move_task_by_snapshot, task_id, snapshot)

    def _detect_moved_task_id(self, snapshot: dict[str, list[str]]) -> str:
        """移動したタスクIDを検出する

        Args:
            snapshot (dict[str, list[str]]): 移動前のタスク配置スナップショット

        Returns:
            str: 移動したタスクID
        """
        before = self._store.task_ids_by_category()
        for category_id, after_ids in snapshot.items():
            before_ids = before.get(category_id, [])
            if before_ids == after_ids:
                continue
            for task_id in after_ids:
                if task_id not in before_ids:
                    return task_id
            if after_ids:
                return after_ids[0]
        return ""

    def _confirm_and_delete_task(self, task_id: str) -> None:
        """確認してタスクを削除する

        Args:
            task_id (str): タスクID
        """
        answer = QMessageBox.question(
            self,
            "確認",
            "このタスクを削除しますか?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._controller.delete_task(task_id)

    def _on_add_label(self, name: str, color: str) -> None:
        """ラベル追加ハンドラ

        Args:
            name (str): ラベル名
            color (str): ラベルカラー
        """
        self._run_controller_action(self._controller.add_label, name, color)

    def _on_update_label(self, label_id: str, name: str, color: str) -> None:
        """ラベル更新ハンドラ

        Args:
            label_id (str): ラベルID
            name (str): ラベル名
            color (str): ラベルカラー
        """
        self._run_controller_action(self._controller.update_label, label_id, name, color)

    def _on_delete_label(self, label_id: str) -> None:
        """ラベル削除ハンドラ

        Args:
            label_id (str): ラベルID
        """
        self._run_controller_action(self._controller.delete_label, label_id)

    def _on_add_status(self, name: str, color: str, hides_from_board: bool) -> None:
        """ステータス追加ハンドラ

        Args:
            name (str): ステータス名
            color (str): ステータスカラー
            hides_from_board (bool): ボードに表示するかどうか
        """
        self._run_controller_action(self._controller.add_status, name, color, hides_from_board)

    def _on_update_status(
        self,
        status_id: str,
        name: str,
        color: str,
        hides_from_board: bool,
    ) -> None:
        """ステータス更新ハンドラ

        Args:
            status_id (str): ステータスID
            name (str): ステータス名
            color (str): ステータスカラー
            hides_from_board (bool): ボードに表示するかどうか
        """
        self._run_controller_action(
            self._controller.update_status,
            status_id,
            name,
            color,
            hides_from_board,
        )

    def _on_delete_status(self, status_id: str, replacement_status_id: str) -> None:
        """ステータス削除ハンドラ

        Args:
            status_id (str): ステータスID
            replacement_status_id (str): 代替ステータスID
        """
        self._run_controller_action(
            self._controller.delete_status,
            status_id,
            replacement_status_id,
        )

    def _on_reorder_statuses(self, ordered_status_ids: list[str]) -> None:
        """ステータス再オーダーハンドラ

        Args:
            ordered_status_ids (list[str]): 並び替え後のステータスIDのリスト
        """
        self._run_controller_action(self._controller.reorder_statuses, ordered_status_ids)

    def _on_add_category(self, name: str) -> None:
        """カテゴリ追加ハンドラ

        Args:
            name (str): カテゴリ名
        """
        self._run_controller_action(self._controller.add_category, name)

    def _on_update_category(self, category_id: str, name: str) -> None:
        """カテゴリ更新ハンドラ

        Args:
            category_id (str): カテゴリID
            name (str): カテゴリ名
        """
        self._run_controller_action(self._controller.update_category, category_id, name)

    def _on_delete_category(self, category_id: str) -> None:
        """カテゴリ削除ハンドラ

        Args:
            category_id (str): カテゴリID
        """
        target = self._store.find_category(category_id)
        if target is None:
            return
        count = sum(1 for task in self._store.board_data.tasks if task.category_id == category_id)
        # タスクが1件でもある場合のみ確認ダイアログを表示
        is_confirm = count != 0
        if is_confirm:
            answer = QMessageBox.question(
                self,
                "カテゴリ削除確認",
                f"カテゴリ {target.name} を削除すると、その中のタスク {count} 件も削除されます。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            is_confirm = answer != QMessageBox.StandardButton.Yes

        if is_confirm:
            return
        self._run_controller_action(self._controller.delete_category, category_id)

    def _run_controller_action(self, action: Callable[..., object], *args: object) -> None:
        """コントローラーアクションを実行する

        Args:
            action (Callable[..., object]): コントローラーアクション
            *args (object): アクションの引数
        """
        try:
            action(*args)
        except Exception as exc:
            self._show_error(str(exc))

    def _show_error(self, message: str) -> None:
        """エラーメッセージを表示する

        Args:
            message (str): エラーメッセージ
        """
        QMessageBox.critical(self, "エラー", message)
