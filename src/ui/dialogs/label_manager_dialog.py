from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
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


class LabelManagerDialog(QDialog):
    """ラベル管理ダイアログ"""

    add_requested = pyqtSignal(str, str)
    """
    追加リクエスト

    Args:
        name (str): 名前
        color (str): 色
    """
    update_requested = pyqtSignal(str, str, str)
    """
    更新リクエスト

    Args:
        label_id (str): ラベルID
        name (str): 名前
        color (str): 色
    """
    delete_requested = pyqtSignal(str)
    """
    削除リクエスト

    Args:
        label_id (str): ラベルID
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle("ラベル管理")
        self.resize(500, 420)
        self._labels_by_id: dict[str, Label] = {}

        root = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemClicked.connect(self._on_item_clicked)
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

    def load_labels(self, labels: list[Label]) -> None:
        """ラベルを読み込む

        Args:
            labels (list[Label]): ラベルのリスト
        """
        self._labels_by_id = {label.id: label for label in labels}
        self._list.clear()
        for label in sorted(labels, key=lambda item: item.sort_order):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, label.id)
            card = LabelCardWidget(label)
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

    def _on_add(self) -> None:
        """追加ボタンが押されたときの処理"""
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
            return
        self.add_requested.emit(dialog.selected_name(), dialog.selected_color())

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """アイテムがクリックされたときの処理"""
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

    def _on_delete(self) -> None:
        """削除ボタンが押されたときの処理"""
        item = self._list.currentItem()
        if item is None:
            return
        label_id = str(item.data(Qt.ItemDataRole.UserRole))
        self.delete_requested.emit(label_id)
