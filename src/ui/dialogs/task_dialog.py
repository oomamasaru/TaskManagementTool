from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.dto import TaskInputData
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task
from ui.widgets.label_selector_widget import LabelSelectorWidget
from utils.color_utils import TASK_LABEL_COLORS, normalize_hex_color


class TaskDialog(QDialog):
    """タスクダイアログ"""

    def __init__(
        self,
        labels: list[Label],
        statuses: list[Status],
        task: Task | None = None,
        default_category_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """イニシャライザ

        Args:
            labels (list[Label]): ラベルリスト
            statuses (list[Status]): ステータスリスト
            task (Task | None, optional): タスク. Defaults to None.
            default_category_id (str | None, optional): デフォルトカテゴリID. Defaults to None.
            parent (QWidget | None, optional): 親ウィジェット. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("タスク")
        self.resize(480, 560)

        self._task = task
        self._category_id = task.category_id if task is not None else (default_category_id or "")
        self._action = "save"

        root = QVBoxLayout(self)
        form = QFormLayout()
        root.addLayout(form)

        self._title_edit = QLineEdit()
        form.addRow("タスク名", self._title_edit)

        due_row = QHBoxLayout()
        self._due_enabled = QCheckBox("期限を設定")
        self._due_date = QDateEdit()
        self._due_date.setCalendarPopup(True)
        self._due_date.setDate(QDate.currentDate())
        self._due_date.setEnabled(False)
        self._due_enabled.toggled.connect(self._due_date.setEnabled)
        due_row.addWidget(self._due_enabled)
        due_row.addWidget(self._due_date)
        due_widget = QWidget()
        due_widget.setLayout(due_row)
        form.addRow("期限", due_widget)

        self._status_combo = QComboBox()
        for status in statuses:
            self._status_combo.addItem(status.name, status.id)
        form.addRow("ステータス", self._status_combo)

        color_panel_layout = QVBoxLayout()
        self._color_buttons: dict[str, QPushButton] = {}
        swatch_widget = QWidget()
        swatch_layout = QGridLayout(swatch_widget)
        swatch_layout.setContentsMargins(0, 0, 0, 0)
        swatch_layout.setHorizontalSpacing(8)
        swatch_layout.setVerticalSpacing(8)
        for index, preset in enumerate(TASK_LABEL_COLORS):
            color = str(preset["bg"])
            button = QPushButton("")
            button.setCheckable(True)
            button.setFixedSize(24, 24)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(color)
            button.clicked.connect(
                lambda _checked=False, value=color: self._on_color_button_clicked(value)
            )
            self._color_buttons[color] = button
            row = index // 8
            col = index % 8
            swatch_layout.addWidget(button, row, col)
        color_panel_layout.addWidget(swatch_widget)

        color_row = QHBoxLayout()
        self._color_edit = QLineEdit()
        self._color_edit.setPlaceholderText("#FEF3C7")
        self._color_edit.textChanged.connect(self._sync_color_button_selection_from_text)
        color_picker_button = QPushButton("カラーピッカー")
        color_picker_button.clicked.connect(self._open_color_dialog)
        color_row.addWidget(self._color_edit, stretch=1)
        color_row.addWidget(color_picker_button)
        color_panel_layout.addLayout(color_row)
        color_widget = QWidget()
        color_widget.setLayout(color_panel_layout)
        form.addRow("色", color_widget)

        self._detail_edit = QTextEdit()
        self._detail_edit.setPlaceholderText("詳細")
        self._detail_edit.setMinimumHeight(120)
        form.addRow("詳細", self._detail_edit)

        label_header = QHBoxLayout()
        label_header.addWidget(QLabel("ラベル"))
        label_header.addStretch(1)
        self._open_label_manager_button = QPushButton("ラベル管理")
        self._open_label_manager_button.clicked.connect(self._on_open_label_manager)
        label_header.addWidget(self._open_label_manager_button)
        root.addLayout(label_header)

        self._label_selector = LabelSelectorWidget(labels)
        root.addWidget(self._label_selector)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        action_row = QHBoxLayout()
        self._duplicate_button = QPushButton("複製")
        self._duplicate_button.clicked.connect(self._on_duplicate)
        self._delete_button = QPushButton("削除")
        self._delete_button.clicked.connect(self._on_delete)
        action_row.addWidget(self._duplicate_button)
        action_row.addWidget(self._delete_button)
        root.addLayout(action_row)

        if task is None:
            self._duplicate_button.setVisible(False)
            self._delete_button.setVisible(False)
            self._select_combo_data(self._status_combo, "not_started")
            self._sync_color_button_selection_from_text()
        else:
            self.set_task(task)

    def set_task(self, task: Task) -> None:
        """タスクを設定する

        Args:
            task (Task): タスク
        """
        self._task = task
        self._title_edit.setText(task.title)
        self._detail_edit.setPlainText(task.detail)
        self._color_edit.setText(task.color or "")
        self._select_color_preset_by_value(task.color)
        self._category_id = task.category_id
        self._select_combo_data(self._status_combo, task.status_id)

        if task.due_date:
            self._due_enabled.setChecked(True)
            self._due_date.setDate(
                QDate(task.due_date.year, task.due_date.month, task.due_date.day)
            )
        else:
            self._due_enabled.setChecked(False)

        self._label_selector.set_selected_label_ids(task.label_ids)

    def get_input(self) -> TaskInputData:
        """入力値を取得する

        Returns:
            TaskInputData: 入力値
        """
        title = self._title_edit.text()
        due_date: date | None = None
        if self._due_enabled.isChecked():
            value = self._due_date.date()
            due_date = date(value.year(), value.month(), value.day())
        label_ids = self._label_selector.selected_label_ids()

        return TaskInputData(
            title=title,
            due_date=due_date,
            category_id=self._category_id,
            label_ids=label_ids,
            color=self._color_edit.text().strip() or None,
            detail=self._detail_edit.toPlainText(),
            status_id=str(self._status_combo.currentData()),
        )

    def set_input(self, input_data: TaskInputData) -> None:
        """入力値をフォームへ復元する。

        Args:
            input_data (TaskInputData): 復元する入力値
        """
        self._title_edit.setText(input_data.title)
        self._detail_edit.setPlainText(input_data.detail)
        self._color_edit.setText(input_data.color or "")
        self._sync_color_button_selection_from_text()
        self._category_id = input_data.category_id
        self._select_combo_data(self._status_combo, input_data.status_id)
        if input_data.due_date is None:
            self._due_enabled.setChecked(False)
        else:
            self._due_enabled.setChecked(True)
            self._due_date.setDate(
                QDate(
                    input_data.due_date.year,
                    input_data.due_date.month,
                    input_data.due_date.day,
                )
            )
        self._label_selector.set_selected_label_ids(input_data.label_ids)

    def request_delete(self) -> bool:
        """削除をリクエストしたか

        Returns:
            bool: 削除をリクエストしたか
        """
        return self._action == "delete"

    def request_duplicate(self) -> bool:
        """複製をリクエストしたか

        Returns:
            bool: 複製をリクエストしたか
        """
        return self._action == "duplicate"

    def request_manage_labels(self) -> bool:
        """ラベル管理画面を開く要求かどうかを返す。"""
        return self._action == "manage_labels"

    def _select_combo_data(self, combo: QComboBox, data: str) -> None:
        """コンボボックスのデータを設定する

        Args:
            combo (QComboBox): コンボボックス
            data (str): データ
        """
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _on_save(self) -> None:
        """保存ボタンがクリックされたときのハンドラ"""
        self._action = "save"
        self.accept()

    def _on_delete(self) -> None:
        """削除ボタンがクリックされたときのハンドラ"""
        self._action = "delete"
        self.accept()

    def _on_duplicate(self) -> None:
        """複製ボタンがクリックされたときのハンドラ"""
        self._action = "duplicate"
        self.accept()

    def _on_open_label_manager(self) -> None:
        """ラベル管理ボタンがクリックされたときのハンドラ。"""
        self._action = "manage_labels"
        self.reject()

    def _on_color_button_clicked(self, color: str) -> None:
        """カラーボタンがクリックされたときのハンドラ

        Args:
            color (str): 色
        """
        self._color_edit.setText(color)
        self._set_color_button_selection(color)

    def _open_color_dialog(self) -> None:
        """カラーダイアログを開く"""
        color = QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        value = color.name().upper()
        self._color_edit.setText(value)
        self._sync_color_button_selection_from_text()

    def _select_color_preset_by_value(self, value: str | None) -> None:
        """カラープリセットを値で選択する

        Args:
            value (str | None): 値
        """
        normalized = normalize_hex_color(value or "", default="")
        selected = normalized if normalized and normalized in self._color_buttons else None
        self._set_color_button_selection(selected)

    def _sync_color_button_selection_from_text(self) -> None:
        """カラーボタンの選択をテキストから同期する"""
        self._select_color_preset_by_value(self._color_edit.text())

    def _set_color_button_selection(self, color: str | None) -> None:
        """カラーボタンの選択を設定する

        Args:
            color (str | None): 色
        """
        for swatch_color, button in self._color_buttons.items():
            selected = swatch_color == color
            button.setChecked(selected)
            border = "2px solid #111827" if selected else "1px solid #9CA3AF"
            button.setStyleSheet(
                f"QPushButton{{background:{swatch_color};border:{border};border-radius:4px;}}"
            )
