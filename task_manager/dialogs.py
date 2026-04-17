from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from const import message as msg
from task_manager.controller import BoardController
from task_manager.models import Label, Status, Task
from task_manager.widgets import parse_due_date


@dataclass
class TaskDialogResult:
    action: str
    payload: dict


class TaskDialog(QDialog):
    def __init__(
        self,
        *,
        categories: list,
        labels: list[Label],
        statuses: list[Status],
        task: Task | None = None,
        default_category_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """イニシャライザ

        Args:
            categories (list): カテゴリリスト
            labels (list[Label]): ラベルリスト
            statuses (list[Status]): ステータスリスト
            task (Task | None): タスクデータ
            default_category_id (str | None): デフォルトカテゴリID
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle(msg.TITLE_TASK_DETAIL)
        self.resize(520, 560)

        self._task = task
        self._categories = categories
        self._labels = labels
        self._statuses = statuses
        self._result: TaskDialogResult | None = None
        self._selected_color: str | None = task.color if task else None

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        root.addLayout(form)

        self.title_edit = QLineEdit(self)
        self.title_edit.setPlaceholderText(msg.MUTATION_ADD_TASK)
        form.addRow(msg.LBL_TASK_NAME_REQ, self.title_edit)

        due_row = QHBoxLayout()
        self.due_enabled = QCheckBox(msg.LBL_DUE_DATE_SET, self)
        self.due_edit = QDateEdit(self)
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDate(QDate.currentDate())
        self.due_edit.setDisplayFormat("yyyy-MM-dd")
        due_row.addWidget(self.due_enabled)
        due_row.addWidget(self.due_edit, 1)
        form.addRow(msg.LBL_DUE_DATE, self._wrap_layout(due_row))

        self.category_combo = QComboBox(self)
        for category in categories:
            self.category_combo.addItem(category.name, category.id)
        form.addRow(msg.LBL_CATEGORY_REQ, self.category_combo)

        self.status_combo = QComboBox(self)
        for status in statuses:
            self.status_combo.addItem(status.name, status.id)
        form.addRow(msg.LBL_STATUS_REQ, self.status_combo)

        self.label_list = QListWidget(self)
        self.label_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.label_list.setMaximumHeight(130)
        for label in labels:
            item = QListWidgetItem(label.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(Qt.ItemDataRole.UserRole, label.id)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.label_list.addItem(item)
        form.addRow(msg.LBL_LABEL, self.label_list)

        color_row = QHBoxLayout()
        self.color_preview = QLabel(self)
        self.color_preview.setFixedSize(60, 24)
        self.color_preview.setStyleSheet("border: 1px solid #D1D5DB;")
        self.color_pick_button = QPushButton(msg.BTN_PICK_COLOR, self)
        self.color_clear_button = QPushButton(msg.BTN_CLEAR_COLOR, self)
        color_row.addWidget(self.color_preview)
        color_row.addWidget(self.color_pick_button)
        color_row.addWidget(self.color_clear_button)
        color_row.addStretch(1)
        form.addRow(msg.LBL_TASK_COLOR, self._wrap_layout(color_row))

        self.detail_edit = QTextEdit(self)
        self.detail_edit.setPlaceholderText(msg.LBL_DETAIL)
        self.detail_edit.setMinimumHeight(140)
        form.addRow(msg.LBL_DETAIL, self.detail_edit)

        if task:
            info = QLabel(
                msg.LBL_DATE_INFO.format(
                    created=task.created_at,
                    updated=task.updated_at,
                    completed=task.completed_at or "-",
                ),
                self,
            )
            info.setStyleSheet("color: #6B7280;")
            form.addRow(msg.LBL_DATETIME, info)

        button_row = QHBoxLayout()
        if task:
            self.duplicate_button = QPushButton(msg.BTN_DUPLICATE, self)
            self.delete_button = QPushButton(msg.BTN_DELETE, self)
            button_row.addWidget(self.duplicate_button)
            button_row.addWidget(self.delete_button)
            button_row.addStretch(1)
        else:
            self.duplicate_button = None
            self.delete_button = None

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        button_row.addWidget(self.button_box)
        root.addLayout(button_row)

        self.color_pick_button.clicked.connect(self._pick_color)
        self.color_clear_button.clicked.connect(self._clear_color)
        self.button_box.accepted.connect(self._save)
        self.button_box.rejected.connect(self.reject)
        if self.delete_button:
            self.delete_button.clicked.connect(self._delete)
        if self.duplicate_button:
            self.duplicate_button.clicked.connect(self._duplicate)
        self.due_enabled.toggled.connect(self.due_edit.setEnabled)

        self._load_initial(default_category_id)
        self._apply_color_preview()

    def _wrap_layout(self, layout) -> QWidget:
        """レイアウトをウィジェットでラップする

        Args:
            layout (QLayout): レイアウト
        Returns:
            QWidget: ウィジェット
        """
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget

    def _load_initial(self, default_category_id: str | None) -> None:
        """初期値をロードする

        Args:
            default_category_id (str | None): デフォルトカテゴリID
        """
        if self._task:
            self.title_edit.setText(self._task.title)
            due = parse_due_date(self._task.due_date)
            if due:
                self.due_enabled.setChecked(True)
                self.due_edit.setDate(QDate(due.year, due.month, due.day))
            else:
                self.due_enabled.setChecked(False)
                self.due_edit.setEnabled(False)
            index = self.category_combo.findData(self._task.category_id)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            index = self.status_combo.findData(self._task.status_id)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
            checked_labels = set(self._task.label_ids)
            for i in range(self.label_list.count()):
                item = self.label_list.item(i)
                label_id = item.data(Qt.ItemDataRole.UserRole)
                if label_id in checked_labels:
                    item.setCheckState(Qt.CheckState.Checked)
            self.detail_edit.setText(self._task.detail)
        else:
            self.due_enabled.setChecked(False)
            self.due_edit.setEnabled(False)
            if default_category_id:
                index = self.category_combo.findData(default_category_id)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            index = self.status_combo.findData("not_started")
            if index >= 0:
                self.status_combo.setCurrentIndex(index)

    def _pick_color(self) -> None:
        """色を選択する"""
        color = QColorDialog.getColor(
            QColor(self._selected_color or "#FEF3C7"), self, msg.LBL_TASK_COLOR
        )
        if color.isValid():
            self._selected_color = color.name().upper()
            self._apply_color_preview()

    def _clear_color(self) -> None:
        """色を解除する"""
        self._selected_color = None
        self._apply_color_preview()

    def _apply_color_preview(self) -> None:
        """色プレビューを適用する"""
        display = self._selected_color or "#FFFFFF"
        self.color_preview.setStyleSheet(f"background-color: {display}; border: 1px solid #D1D5DB;")

    def _build_payload(self) -> dict:
        """ペイロードを構築する

        Returns:
            dict: ペイロード
        """
        label_ids: list[str] = []
        for i in range(self.label_list.count()):
            item = self.label_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                label_ids.append(str(item.data(Qt.ItemDataRole.UserRole)))
        due_date = (
            self.due_edit.date().toString("yyyy-MM-dd") if self.due_enabled.isChecked() else None
        )
        return {
            "title": self.title_edit.text().strip(),
            "due_date": due_date,
            "category_id": str(self.category_combo.currentData()),
            "label_ids": label_ids,
            "color": self._selected_color,
            "detail": self.detail_edit.toPlainText(),
            "status_id": str(self.status_combo.currentData()),
        }

    def _save(self) -> None:
        """保存する"""
        payload = self._build_payload()
        if not payload["title"]:
            QMessageBox.warning(self, msg.TITLE_INPUT_ERROR, msg.ERR_TASK_NAME_REQUIRED)
            return
        self._result = TaskDialogResult(action="save", payload=payload)
        self.accept()

    def _delete(self) -> None:
        """削除する"""
        self._result = TaskDialogResult(action="delete", payload={})
        self.accept()

    def _duplicate(self) -> None:
        """複製する"""
        self._result = TaskDialogResult(action="duplicate", payload={})
        self.accept()

    @property
    def result_data(self) -> TaskDialogResult | None:
        """結果データを返す

        Returns:
            TaskDialogResult | None: 結果データ
        """
        return self._result


class LabelEditDialog(QDialog):
    """ラベル編集ダイアログ"""

    def __init__(
        self,
        *,
        title: str,
        default_name: str = "",
        default_color: str = "#BFDBFE",
        default_sort_order: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        """イニシャライザ

        Args:
            title (str): タイトル
            default_name (str): デフォルト名
            default_color (str): デフォルト色
            default_sort_order (int): デフォルトソート順
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(380, 180)
        self._color = default_color

        root = QFormLayout(self)
        self.name_edit = QLineEdit(default_name, self)
        root.addRow(msg.LBL_NAME_REQ, self.name_edit)

        color_row = QHBoxLayout()
        self.color_preview = QLabel(self)
        self.color_preview.setFixedSize(56, 24)
        self.color_button = QPushButton(msg.BTN_PICK_COLOR, self)
        color_row.addWidget(self.color_preview)
        color_row.addWidget(self.color_button)
        color_row.addStretch(1)
        root.addRow(msg.LBL_COLOR_REQ, self._wrap_layout(color_row))

        self.sort_order_spin = QSpinBox(self)
        self.sort_order_spin.setMinimum(1)
        self.sort_order_spin.setMaximum(9999)
        self.sort_order_spin.setValue(default_sort_order)
        root.addRow(msg.LBL_SORT_ORDER, self.sort_order_spin)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        root.addRow(self.buttons)

        self.color_button.clicked.connect(self._pick_color)
        self.buttons.accepted.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        self._apply_color_preview()

    def _wrap_layout(self, layout) -> QWidget:
        """レイアウトをウィジェットでラップする

        Args:
            layout (QLayout): レイアウト
        Returns:
            QWidget: ウィジェット
        """
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget

    def _pick_color(self) -> None:
        """色を選択する"""
        color = QColorDialog.getColor(QColor(self._color), self, msg.BTN_PICK_COLOR)
        if color.isValid():
            self._color = color.name().upper()
            self._apply_color_preview()

    def _apply_color_preview(self) -> None:
        """色プレビューを適用する"""
        self.color_preview.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #D1D5DB; border-radius: 3px;"
        )

    def _validate_and_accept(self) -> None:
        """検証して保存する"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, msg.TITLE_INPUT_ERROR, msg.LBL_NAME_REQ)
            return
        self.accept()

    @property
    def value(self) -> tuple[str, str, int]:
        return self.name_edit.text().strip(), self._color, self.sort_order_spin.value()


class StatusEditDialog(LabelEditDialog):
    pass


class CompletedTasksDialog(QDialog):
    """完了済みタスクダイアログ"""

    edit_requested = pyqtSignal(str)
    restore_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle(msg.TITLE_COMPLETED_TASKS)
        self.resize(920, 480)
        self._tasks: list[Task] = []
        self._category_names: dict[str, str] = {}
        self._label_names: dict[str, str] = {}

        root = QVBoxLayout(self)
        top_row = QHBoxLayout()
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText(msg.LBL_SEARCH_COMPLETED_TASK)
        top_row.addWidget(self.search_edit, 1)
        root.addLayout(top_row)

        self.table = QTableWidget(self)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            [
                msg.MUTATION_ADD_TASK,
                msg.LBL_ORIGINAL_CATEGORY,
                msg.LBL_LABEL,
                msg.LBL_DUE_DATE,
                msg.LBL_COMPLETED_AT,
                msg.LBL_DETAIL_PREVIEW,
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        button_row = QHBoxLayout()
        self.detail_button = QPushButton(msg.BTN_DETAIL, self)
        self.restore_button = QPushButton(msg.BTN_RESTORE, self)
        self.delete_button = QPushButton(msg.BTN_FULL_DELETE, self)
        self.close_button = QPushButton(msg.BTN_CLOSE, self)
        button_row.addWidget(self.detail_button)
        button_row.addWidget(self.restore_button)
        button_row.addWidget(self.delete_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)
        root.addLayout(button_row)

        self.search_edit.textChanged.connect(self.refresh)
        self.table.doubleClicked.connect(lambda _index: self._emit_detail())
        self.detail_button.clicked.connect(self._emit_detail)
        self.restore_button.clicked.connect(self._emit_restore)
        self.delete_button.clicked.connect(self._emit_delete)
        self.close_button.clicked.connect(self.close)

    def set_context(
        self,
        tasks: list[Task],
        category_names: dict[str, str],
        label_names: dict[str, str],
    ) -> None:
        """コンテキストを設定する

        Args:
            tasks (list[Task]): タスクリスト
            category_names (dict[str, str]): カテゴリ名辞書
            label_names (dict[str, str]): ラベル名辞書
        """
        self._tasks = list(tasks)
        self._category_names = dict(category_names)
        self._label_names = dict(label_names)
        self.refresh()

    def refresh(self) -> None:
        """テーブルをリフレッシュする"""
        query = self.search_edit.text().strip().lower()
        filtered = []
        for task in self._tasks:
            text = f"{task.title} {task.detail}".lower()
            if query and query not in text:
                continue
            filtered.append(task)

        self.table.setRowCount(len(filtered))
        for row, task in enumerate(filtered):
            labels = [self._label_names.get(x, x) for x in task.label_ids]
            self.table.setItem(row, 0, QTableWidgetItem(task.title))
            self.table.setItem(
                row, 1, QTableWidgetItem(self._category_names.get(task.category_id, "-"))
            )
            self.table.setItem(
                row, 2, QTableWidgetItem(", ".join(labels) if labels else msg.LBL_LABEL_NONE)
            )
            self.table.setItem(row, 3, QTableWidgetItem(task.due_date or msg.LBL_DUE_DATE_NONE))
            self.table.setItem(row, 4, QTableWidgetItem(task.completed_at or "-"))
            preview = task.detail.strip().replace("\n", " ")
            self.table.setItem(row, 5, QTableWidgetItem(preview[:80]))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, task.id)

        if filtered:
            self.table.selectRow(0)
        self.table.resizeColumnsToContents()

    def _selected_task_id(self) -> str | None:
        """選択されたタスクIDを返す"""
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))

    def _emit_detail(self) -> None:
        """詳細を表示する"""
        task_id = self._selected_task_id()
        if task_id:
            self.edit_requested.emit(task_id)

    def _emit_restore(self) -> None:
        """復元する"""
        task_id = self._selected_task_id()
        if task_id:
            self.restore_requested.emit(task_id)

    def _emit_delete(self) -> None:
        """削除する"""
        task_id = self._selected_task_id()
        if task_id:
            self.delete_requested.emit(task_id)


class LabelManagerDialog(QDialog):
    """ラベル管理ダイアログ"""

    def __init__(self, controller: BoardController, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            controller (BoardController): ボードコントローラ
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle(msg.TITLE_LABEL_MANAGER)
        self.resize(520, 380)

        root = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            [msg.LBL_NAME_REQ, msg.LBL_COLOR_REQ, msg.LBL_SORT_ORDER]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.add_button = QPushButton(msg.BTN_ADD, self)
        self.edit_button = QPushButton(msg.BTN_EDIT, self)
        self.delete_button = QPushButton(msg.BTN_DELETE, self)
        self.close_button = QPushButton(msg.BTN_CLOSE, self)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)
        root.addLayout(buttons)

        self.add_button.clicked.connect(self._add)
        self.edit_button.clicked.connect(self._edit)
        self.delete_button.clicked.connect(self._delete)
        self.close_button.clicked.connect(self.close)
        self.controller.changed.connect(self.refresh)
        self.refresh()

    def closeEvent(self, event) -> None:
        """閉じるイベント

        Args:
            event (QCloseEvent): 閉じるイベント
        """
        try:
            self.controller.changed.disconnect(self.refresh)
        except TypeError:
            pass
        super().closeEvent(event)

    def refresh(self) -> None:
        """テーブルをリフレッシュする"""
        labels = self.controller.labels
        self.table.setRowCount(len(labels))
        for row, label in enumerate(labels):
            self.table.setItem(row, 0, QTableWidgetItem(label.name))
            color_item = QTableWidgetItem(label.color)
            color_item.setBackground(QColor(label.color))
            self.table.setItem(row, 1, color_item)
            self.table.setItem(row, 2, QTableWidgetItem(str(label.sort_order)))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, label.id)
        if labels:
            self.table.selectRow(0)
        self.table.resizeColumnsToContents()

    def _selected_label_id(self) -> str | None:
        """選択されたラベルIDを返す"""
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))

    def _add(self) -> None:
        """ラベルを追加する"""
        dialog = LabelEditDialog(title=msg.TITLE_LABEL_ADD, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, color, _ = dialog.value
        try:
            self.controller.add_label(name, color)
        except Exception as exc:
            QMessageBox.critical(self, msg.TITLE_ERROR, str(exc))

    def _edit(self) -> None:
        """ラベルを編集する"""
        label_id = self._selected_label_id()
        if not label_id:
            return
        label = self.controller.get_label(label_id)
        if not label:
            return
        dialog = LabelEditDialog(
            title=msg.TITLE_LABEL_EDIT,
            default_name=label.name,
            default_color=label.color,
            default_sort_order=label.sort_order,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, color, sort_order = dialog.value
        try:
            self.controller.update_label(label_id, name, color, sort_order)
        except Exception as exc:
            QMessageBox.critical(self, msg.TITLE_ERROR, str(exc))

    def _delete(self) -> None:
        """ラベルを削除する"""
        label_id = self._selected_label_id()
        if not label_id:
            return
        label = self.controller.get_label(label_id)
        if not label:
            return
        answer = QMessageBox.question(
            self,
            msg.TITLE_CONFIRM,
            msg.MSG_CONFIRM_DELETE_LABEL.format(name=label.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_label(label_id)
        except Exception as exc:
            QMessageBox.critical(self, msg.TITLE_ERROR, str(exc))


class StatusManagerDialog(QDialog):
    """ステータス管理ダイアログ"""

    def __init__(self, controller: BoardController, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            controller (BoardController): ボードコントローラ
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle(msg.TITLE_STATUS_MANAGER)
        self.resize(580, 380)

        root = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            [msg.LBL_NAME_REQ, msg.LBL_COLOR_REQ, msg.LBL_SORT_ORDER, msg.LBL_IS_FIXED]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.add_button = QPushButton(msg.BTN_ADD, self)
        self.edit_button = QPushButton(msg.BTN_EDIT, self)
        self.delete_button = QPushButton(msg.BTN_DELETE, self)
        self.close_button = QPushButton(msg.BTN_CLOSE, self)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)
        root.addLayout(buttons)

        self.add_button.clicked.connect(self._add)
        self.edit_button.clicked.connect(self._edit)
        self.delete_button.clicked.connect(self._delete)
        self.close_button.clicked.connect(self.close)
        self.controller.changed.connect(self.refresh)
        self.refresh()

    def closeEvent(self, event) -> None:
        """閉じるイベント

        Args:
            event (QCloseEvent): 閉じるイベント
        """
        try:
            self.controller.changed.disconnect(self.refresh)
        except TypeError:
            pass
        super().closeEvent(event)

    def refresh(self) -> None:
        """テーブルをリフレッシュする"""
        statuses = self.controller.statuses
        self.table.setRowCount(len(statuses))
        for row, status in enumerate(statuses):
            self.table.setItem(row, 0, QTableWidgetItem(status.name))
            color_item = QTableWidgetItem(status.color)
            color_item.setBackground(QColor(status.color))
            self.table.setItem(row, 1, color_item)
            self.table.setItem(row, 2, QTableWidgetItem(str(status.sort_order)))
            self.table.setItem(row, 3, QTableWidgetItem("○" if status.is_system else ""))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, status.id)
        if statuses:
            self.table.selectRow(0)
        self.table.resizeColumnsToContents()

    def _selected_status_id(self) -> str | None:
        """選択されたステータスIDを返す"""
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))

    def _add(self) -> None:
        """ステータスを追加する"""
        dialog = StatusEditDialog(title=msg.TITLE_STATUS_ADD, default_color="#2563EB", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, color, _ = dialog.value
        try:
            self.controller.add_status(name, color)
        except Exception as exc:
            QMessageBox.critical(self, msg.TITLE_ERROR, str(exc))

    def _edit(self) -> None:
        """ステータスを編集する"""
        status_id = self._selected_status_id()
        if not status_id:
            return
        status = self.controller.get_status(status_id)
        if not status:
            return
        dialog = StatusEditDialog(
            title=msg.TITLE_STATUS_EDIT,
            default_name=status.name,
            default_color=status.color,
            default_sort_order=status.sort_order,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, color, sort_order = dialog.value
        try:
            self.controller.update_status(status_id, name, color, sort_order)
        except Exception as exc:
            QMessageBox.critical(self, msg.TITLE_ERROR, str(exc))

    def _delete(self) -> None:
        """ステータスを削除する"""
        status_id = self._selected_status_id()
        if not status_id:
            return
        status = self.controller.get_status(status_id)
        if not status:
            return
        if status.is_system:
            QMessageBox.warning(self, msg.TITLE_DELETE_IMPOSSIBLE, msg.ERR_SYSTEM_STATUS_DELETE)
            return

        used_tasks = [x for x in self.controller.tasks if x.status_id == status_id]
        replacement_status_id: str | None = None
        if used_tasks:
            candidates = [x for x in self.controller.statuses if x.id != status_id]
            names = [x.name for x in candidates]
            selected_name, ok = QInputDialog.getItem(
                self,
                msg.TITLE_REPLACEMENT_STATUS_SELECT,
                msg.LBL_REPLACEMENT_STATUS_GUIDE,
                names,
                0,
                False,
            )
            if not ok:
                return
            selected = next((x for x in candidates if x.name == selected_name), None)
            if not selected:
                return
            replacement_status_id = selected.id

        answer = QMessageBox.question(
            self,
            msg.TITLE_CONFIRM,
            f"ステータス「{status.name}」を削除します。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.controller.delete_status(status_id, replacement_status_id)
        except Exception as exc:
            QMessageBox.critical(self, msg.TITLE_ERROR, str(exc))


class SettingsDialog(QDialog):
    """設定ダイアログ"""

    def __init__(self, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle(msg.TITLE_SETTINGS)
        self.resize(420, 200)

        root = QVBoxLayout(self)
        label = QLabel(msg.LBL_SETTINGS_FUTURE, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(label, 1)

        close_button = QPushButton(msg.BTN_CLOSE, self)
        close_button.clicked.connect(self.close)
        root.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)
