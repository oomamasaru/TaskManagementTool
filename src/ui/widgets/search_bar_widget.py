from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class SearchBarWidget(QWidget):
    search_changed = pyqtSignal(str)
    clear_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
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
        return self._search_edit.text()

    def clear(self) -> None:
        self._search_edit.clear()

    def _on_clear_clicked(self) -> None:
        self.clear()
        self.clear_requested.emit()

