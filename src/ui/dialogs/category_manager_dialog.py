from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from domain.models.category import Category
from ui.widgets.category_card_widget import CategoryCardWidget


class CategoryListWidget(QListWidget):
    """カテゴリのドラッグ並び替えを扱うリスト。"""

    reordered = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        """初期化する。"""
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """ドロップ完了時に並び順変更を通知する。"""
        super().dropEvent(event)
        self.reordered.emit(self.category_ids())

    def category_ids(self) -> list[str]:
        """現在表示順のカテゴリID一覧を返す。"""
        return [str(self.item(row).data(Qt.ItemDataRole.UserRole)) for row in range(self.count())]


class CategoryManagerDialog(QDialog):
    """カテゴリ管理ダイアログ。"""

    add_requested = pyqtSignal(str)
    update_requested = pyqtSignal(str, str)
    delete_requested = pyqtSignal(str)
    reorder_requested = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        """初期化する。"""
        super().__init__(parent)
        self.setWindowTitle("カテゴリ管理")
        self.resize(500, 420)

        self._categories_by_id: dict[str, Category] = {}

        root = QVBoxLayout(self)
        self._list = CategoryListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.itemSelectionChanged.connect(self._sync_delete_button_state)
        self._list.reordered.connect(self._on_list_reordered)
        root.addWidget(self._list)

        row = QHBoxLayout()
        add_button = QPushButton("追加")
        self._delete_button = QPushButton("削除")
        self._delete_button.setEnabled(False)
        close_button = QPushButton("閉じる")

        add_button.clicked.connect(self.request_add)
        self._delete_button.clicked.connect(self._on_delete)
        close_button.clicked.connect(self.accept)

        row.addWidget(add_button)
        row.addWidget(self._delete_button)
        row.addStretch(1)
        row.addWidget(close_button)
        root.addLayout(row)

    def load_categories(self, categories: list[Category]) -> None:
        """カテゴリ一覧を読み込む。"""
        self._categories_by_id = {category.id: category for category in categories}
        self._list.clear()

        for category in sorted(categories, key=lambda each: each.sort_order):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, category.id)
            card = CategoryCardWidget(category, self._list)
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

        self._sync_delete_button_state()

    def request_add(self) -> None:
        """カテゴリ追加を要求する。"""
        name, ok = QInputDialog.getText(self, "カテゴリ追加", "カテゴリ名")
        if not ok:
            return
        self.add_requested.emit(name)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """行ダブルクリック時にカテゴリ名編集を行う。"""
        category_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        category = self._categories_by_id.get(category_id)
        if category is None:
            return

        name, ok = QInputDialog.getText(
            self,
            "カテゴリ編集",
            "カテゴリ名",
            text=category.name,
        )
        if not ok:
            return
        self.update_requested.emit(category.id, name)

    def _on_delete(self) -> None:
        """選択中カテゴリの削除を要求する。"""
        item = self._list.currentItem()
        if item is None:
            return
        self.delete_requested.emit(str(item.data(Qt.ItemDataRole.UserRole)))

    def _sync_delete_button_state(self) -> None:
        """削除ボタンの有効状態を同期する。"""
        self._delete_button.setEnabled(self._list.currentItem() is not None)

    def _on_list_reordered(self, ordered_category_ids: list[str]) -> None:
        """カテゴリの並び替え要求を通知する。"""
        self.reorder_requested.emit(ordered_category_ids)
