from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.models.category import Category


class CategoryManagerDialog(QDialog):
    add_requested = pyqtSignal(str)
    update_requested = pyqtSignal(str, str)
    delete_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("カテゴリ管理")
        self.resize(420, 340)

        self._names_by_id: dict[str, str] = {}
        self._is_loading = False

        root = QVBoxLayout(self)
        self._table = QTableWidget(0, 1)
        self._table.setHorizontalHeaderLabels(["カテゴリ"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self._table)

        row = QHBoxLayout()
        add_button = QPushButton("追加")
        delete_button = QPushButton("削除")
        close_button = QPushButton("閉じる")
        add_button.clicked.connect(self.request_add)
        delete_button.clicked.connect(self._on_delete)
        close_button.clicked.connect(self.accept)
        row.addWidget(add_button)
        row.addWidget(delete_button)
        row.addStretch(1)
        row.addWidget(close_button)
        root.addLayout(row)

    def load_categories(self, categories: list[Category]) -> None:
        self._is_loading = True
        try:
            self._table.setRowCount(len(categories))
            self._names_by_id = {}
            for row, category in enumerate(categories):
                item = QTableWidgetItem(category.name)
                item.setData(Qt.ItemDataRole.UserRole, category.id)
                self._table.setItem(row, 0, item)
                self._names_by_id[category.id] = category.name
        finally:
            self._is_loading = False

    def request_add(self) -> None:
        name, ok = QInputDialog.getText(self, "カテゴリ追加", "名前")
        if not ok:
            return
        self.add_requested.emit(name)

    def _on_delete(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        self.delete_requested.emit(str(item.data(Qt.ItemDataRole.UserRole)))

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_loading:
            return

        category_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not category_id:
            return

        old_name = self._names_by_id.get(category_id, "")
        new_name = item.text().strip()

        if not new_name:
            self._restore_item_text(item, old_name)
            return

        if new_name.lower() != old_name.lower() and self._has_duplicate_name(category_id, new_name):
            self._restore_item_text(item, old_name)
            return

        if new_name == old_name:
            if item.text() != old_name:
                self._restore_item_text(item, old_name)
            return

        if item.text() != new_name:
            self._restore_item_text(item, new_name)

        self._names_by_id[category_id] = new_name
        self.update_requested.emit(category_id, new_name)

    def _restore_item_text(self, item: QTableWidgetItem, value: str) -> None:
        blocker = QSignalBlocker(self._table)
        item.setText(value)
        del blocker

    def _has_duplicate_name(self, category_id: str, new_name: str) -> bool:
        lower_name = new_name.lower()
        return any(
            current_id != category_id and current_name.lower() == lower_name
            for current_id, current_name in self._names_by_id.items()
        )
