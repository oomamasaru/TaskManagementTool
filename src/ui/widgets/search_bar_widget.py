from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class SearchBarWidget(QWidget):
    """検索バーウィジェット

    - 検索テキスト入力欄
    - クリアボタン
    """

    search_changed = pyqtSignal(str)
    """
    検索テキスト変更シグナル

    Args:
        text (str): 検索テキスト
    """
    clear_requested = pyqtSignal()
    """
    クリアリクエストシグナル
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("タスク名/詳細を検索")
        self._search_edit.textChanged.connect(self.search_changed.emit)

        self._clear_button = QPushButton("クリア")
        self._clear_button.clicked.connect(self._on_clear_clicked)

        layout.addWidget(self._search_edit, stretch=1)
        layout.addWidget(self._clear_button)

    def search_text(self) -> str:
        """検索テキストを返す"""
        return self._search_edit.text()

    def clear(self) -> None:
        """検索テキストをクリアする"""
        self._search_edit.clear()

    def _on_clear_clicked(self) -> None:
        """クリアボタンがクリックされたときの処理"""
        self.clear()
        self.clear_requested.emit()
