from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from domain.models.label import Label
from ui.dialogs.color_select_dialog import ColorSelectDialog
from ui.widgets.label_card_widget import LabelCardWidget
from utils.color_utils import TASK_LABEL_COLORS
from utils.debug_trace import trace_debug


class _LabelListItemWidget(QWidget):
    """ラベル一覧の1行表示ウィジェット。"""

    def __init__(self, label: Label, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.checkbox = QCheckBox(self)
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        card = LabelCardWidget(label, self)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(card, stretch=1)


class LabelManagerDialog(QDialog):
    """ラベル管理ダイアログ。"""

    add_requested = pyqtSignal(str, str)
    update_requested = pyqtSignal(str, str, str)
    delete_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """初期化する。"""
        super().__init__(parent)
        self.setWindowTitle("ラベル管理")
        self.resize(500, 420)
        trace_debug(f"LabelManagerDialog:init id={id(self)} parent={type(parent).__name__}")

        self._labels_by_id: dict[str, Label] = {}
        self._checked_label_ids: set[str] = set()

        root = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        root.addWidget(self._list)

        row = QHBoxLayout()
        add_button = QPushButton("追加")
        self._delete_button = QPushButton("削除")
        self._delete_button.setEnabled(False)
        close_button = QPushButton("閉じる")

        add_button.clicked.connect(self._on_add)
        self._delete_button.clicked.connect(self._on_delete)
        close_button.clicked.connect(self.accept)

        row.addWidget(add_button)
        row.addWidget(self._delete_button)
        row.addStretch(1)
        row.addWidget(close_button)
        root.addLayout(row)

    def load_labels(self, labels: list[Label]) -> None:
        """ラベル一覧を読み込む。"""
        previous_checked_ids = set(self._checked_label_ids)
        self._labels_by_id = {label.id: label for label in labels}
        self._checked_label_ids.clear()
        self._list.clear()

        for label in sorted(labels, key=lambda each: each.sort_order):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, label.id)

            row_widget = _LabelListItemWidget(label, self._list)
            checked = label.id in previous_checked_ids
            row_widget.checkbox.setChecked(checked)
            if checked:
                self._checked_label_ids.add(label.id)
            row_widget.checkbox.toggled.connect(
                lambda is_checked, label_id=label.id: self._on_toggle_checked(
                    label_id,
                    is_checked,
                )
            )

            item.setSizeHint(row_widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, row_widget)

        self._sync_delete_button_state()

    def _on_add(self) -> None:
        trace_debug(f"LabelManagerDialog:_on_add:start id={id(self)}")
        dialog = ColorSelectDialog(
            title="ラベル追加",
            presets=TASK_LABEL_COLORS,
            color_key="bg",
            default_color="#DBEAFE",
            default_name="",
            show_name_input=True,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            trace_debug(f"LabelManagerDialog:_on_add:cancel id={id(self)}")
            return
        trace_debug(f"LabelManagerDialog:_on_add:emit add_requested id={id(self)}")
        self.add_requested.emit(dialog.selected_name(), dialog.selected_color())

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        label_id = str(item.data(Qt.ItemDataRole.UserRole))
        label = self._labels_by_id.get(label_id)
        if label is None:
            return

        dialog = ColorSelectDialog(
            title="ラベル編集",
            presets=TASK_LABEL_COLORS,
            color_key="bg",
            default_color=label.color,
            default_name=label.name,
            show_name_input=True,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.update_requested.emit(label.id, dialog.selected_name(), dialog.selected_color())

    def _on_toggle_checked(self, label_id: str, checked: bool) -> None:
        if checked:
            self._checked_label_ids.add(label_id)
        else:
            self._checked_label_ids.discard(label_id)
        self._sync_delete_button_state()

    def _on_delete(self) -> None:
        if not self._checked_label_ids:
            trace_debug(f"LabelManagerDialog:_on_delete:skip no checked id={id(self)}")
            return

        target_ids = [
            label.id
            for label in sorted(self._labels_by_id.values(), key=lambda each: each.sort_order)
            if label.id in self._checked_label_ids
        ]
        for label_id in target_ids:
            trace_debug(
                f"LabelManagerDialog:_on_delete:emit delete_requested id={id(self)} label_id={label_id}"
            )
            self.delete_requested.emit(label_id)

    def _sync_delete_button_state(self) -> None:
        self._delete_button.setEnabled(bool(self._checked_label_ids))

    def done(self, result: int) -> None:
        """終了時に結果を記録する。"""
        trace_debug(
            f"LabelManagerDialog:done id={id(self)} result={result} visible={self.isVisible()}"
        )
        super().done(result)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """クローズイベント時のログを記録する。"""
        trace_debug(f"LabelManagerDialog:closeEvent id={id(self)}")
        super().closeEvent(event)
