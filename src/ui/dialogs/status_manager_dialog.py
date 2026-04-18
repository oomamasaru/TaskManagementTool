from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from domain.models.status import Status
from ui.dialogs.color_select_dialog import ColorSelectDialog
from utils.color_utils import STATUS_COLORS, contrast_text_color, normalize_hex_color


class StatusCardWidget(QFrame):
    def __init__(self, status: Status, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        bg_color = normalize_hex_color(status.color)
        text_color = contrast_text_color(bg_color)

        self.setObjectName("statusCard")
        self.setStyleSheet(
            f"#statusCard{{border:1px solid #D1D5DB;border-radius:6px;background:{bg_color};}}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(4)

        name = QLabel(status.name)
        name.setStyleSheet(f"font-weight:600;color:{text_color};")
        root.addWidget(name)

        detail_text = []
        if status.is_system:
            detail_text.append("システム")
        if status.hides_from_board:
            detail_text.append("一覧非表示")
        detail = QLabel(" / ".join(detail_text))
        detail.setStyleSheet(f"font-size:8pt;color:{text_color};")
        root.addWidget(detail)


class StatusListWidget(QListWidget):
    reordered = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def drop_event(self, event: QDropEvent) -> None:
        super().dropEvent(event)
        self.reordered.emit(self.status_ids())

    def status_ids(self) -> list[str]:
        return [
            str(self.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.count())
        ]


class StatusManagerDialog(QDialog):
    add_requested = pyqtSignal(str, str, bool)
    update_requested = pyqtSignal(str, str, str, bool)
    delete_requested = pyqtSignal(str, str)
    reorder_requested = pyqtSignal(list)

    IMMUTABLE_STATUS_IDS = frozenset({"not_started", "completed"})

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ステータス管理")
        self.resize(620, 460)
        self._statuses_by_id: dict[str, Status] = {}

        root = QVBoxLayout(self)
        self._list = StatusListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.reordered.connect(self._on_list_reordered)
        root.addWidget(self._list)

        row = QHBoxLayout()
        add_button = QPushButton("追加")
        delete_button = QPushButton("削除")
        close_button = QPushButton("閉じる")
        add_button.clicked.connect(self._on_add)
        delete_button.clicked.connect(self._on_delete)
        close_button.clicked.connect(self.accept)
        row.addWidget(add_button)
        row.addWidget(delete_button)
        row.addStretch(1)
        row.addWidget(close_button)
        root.addLayout(row)

    def load_statuses(self, statuses: list[Status]) -> None:
        self._statuses_by_id = {status.id: status for status in statuses}
        self._list.clear()
        for status in sorted(statuses, key=lambda item: item.sort_order):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, status.id)
            if status.id in self.IMMUTABLE_STATUS_IDS:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            card = StatusCardWidget(status)
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

    def _on_add(self) -> None:
        dialog = ColorSelectDialog(
            title="ステータス追加",
            presets=STATUS_COLORS,
            color_key="main",
            default_color="#2563EB",
            default_name="",
            show_name_input=True,
            show_hide_checkbox=True,
            default_hide_checkbox=False,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.add_requested.emit(
            dialog.selected_name(),
            dialog.selected_color(),
            dialog.hide_checkbox_value(),
        )

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        _, status = self._status_from_item(item)
        if status is None:
            return

        if status.id in self.IMMUTABLE_STATUS_IDS:
            QMessageBox.information(self, "情報", "未設定と完了ステータスは変更できません。")
            return

        dialog = ColorSelectDialog(
            title="ステータス編集",
            presets=STATUS_COLORS,
            color_key="main",
            default_color=status.color,
            default_name=status.name,
            show_name_input=True,
            show_hide_checkbox=True,
            default_hide_checkbox=status.hides_from_board,
            hide_checkbox_enabled=not status.is_system,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        hides_from_board = dialog.hide_checkbox_value()
        if status.is_system and status.id == "completed":
            hides_from_board = True
        self.update_requested.emit(
            status.id,
            dialog.selected_name(),
            dialog.selected_color(),
            hides_from_board,
        )

    def _on_delete(self) -> None:
        status_id, status = self._status_from_item(self._list.currentItem())
        if status is None:
            return
        if status.is_system:
            QMessageBox.information(self, "情報", "システムステータスは削除できません。")
            return

        replacement_id, ok = self._ask_replacement(status_id)
        if not ok or replacement_id is None:
            return
        self.delete_requested.emit(status_id, replacement_id)

    def _on_list_reordered(self, ordered_status_ids: list[str]) -> None:
        self.reorder_requested.emit(self._normalized_order_ids(ordered_status_ids))

    def _normalized_order_ids(self, ordered_status_ids: list[str]) -> list[str]:
        seen: set[str] = set()
        movable_ids: list[str] = []
        for status_id in ordered_status_ids:
            if status_id in self.IMMUTABLE_STATUS_IDS:
                continue
            if status_id not in self._statuses_by_id:
                continue
            if status_id in seen:
                continue
            seen.add(status_id)
            movable_ids.append(status_id)

        result: list[str] = []
        if "not_started" in self._statuses_by_id:
            result.append("not_started")
        result.extend(movable_ids)
        if "completed" in self._statuses_by_id:
            result.append("completed")
        return result

    def _status_from_item(self, item: QListWidgetItem | None) -> tuple[str, Status | None]:
        if item is None:
            return "", None
        status_id = str(item.data(Qt.ItemDataRole.UserRole))
        return status_id, self._statuses_by_id.get(status_id)

    def _ask_replacement(self, deleting_status_id: str) -> tuple[str | None, bool]:
        rows = [
            (status.id, status.name)
            for status in sorted(self._statuses_by_id.values(), key=lambda item: item.sort_order)
            if status.id != deleting_status_id
        ]
        if not rows:
            return None, False
        names = [name for _, name in rows]
        selected_name, ok = QInputDialog.getItem(
            self,
            "代替ステータス",
            "削除対象の代替先を選択してください",
            names,
            editable=False,
        )
        if not ok:
            return None, False
        replacement_id = next(
            (status_id for status_id, name in rows if name == selected_name),
            None,
        )
        if replacement_id is None:
            return None, False
        return replacement_id, True
