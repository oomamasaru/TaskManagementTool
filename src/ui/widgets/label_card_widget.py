from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from domain.models.label import Label
from utils.color_utils import normalize_hex_color


class LabelCardWidget(QFrame):
    def __init__(self, label: Label, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("labelCard")
        self.setStyleSheet(
            f"#labelCard{{border:1px solid #D1D5DB;border-radius:6px;"
            f"background:{normalize_hex_color(label.color)};}}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(4)

        name = QLabel(label.name)
        name.setStyleSheet("font-weight:600;color:#111827;")
        color = QLabel(label.color)
        color.setStyleSheet("font-size:8pt;color:#374151;")
        root.addWidget(name)
        root.addWidget(color)
