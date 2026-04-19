from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from domain.models.category import Category


class CategoryCardWidget(QFrame):
    """カテゴリカードウィジェット。"""

    def __init__(self, category: Category, parent: QWidget | None = None) -> None:
        """初期化する。"""
        super().__init__(parent)
        self.setObjectName("categoryCard")
        self.setStyleSheet(
            "#categoryCard{border:1px solid #D1D5DB;border-radius:6px;background:#FFFFFF;}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(4)

        name = QLabel(category.name)
        name.setStyleSheet("font-weight:600;color:#111827;")
        root.addWidget(name)
