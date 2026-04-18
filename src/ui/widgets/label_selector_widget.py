from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import QPoint, QRect, QSize, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from domain.models.label import Label
from utils.color_utils import normalize_hex_color


class FlowLayout(QLayout):
    """Flow layout for chip-like widgets."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 6) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(
            margins.left(),
            margins.top(),
            -margins.right(),
            -margins.bottom(),
        )
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._items:
            item_size = item.sizeHint()
            next_x = x + item_size.width() + spacing

            if line_height > 0 and next_x - spacing > effective_rect.right():
                x = effective_rect.x()
                y = y + line_height + spacing
                next_x = x + item_size.width() + spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))

            x = next_x
            line_height = max(line_height, item_size.height())

        return y + line_height - rect.y() + margins.bottom()


class LabelChipButton(QToolButton):
    """Toggle chip shown in candidate area."""

    def __init__(self, label: Label, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.label_data = label
        self.setText(label.name)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._refresh_style()

        self.toggled.connect(self._refresh_style)

    def _refresh_style(self) -> None:
        bg = normalize_hex_color(self.label_data.color)
        if self.isChecked():
            border = "#111827"
            text = "#111827"
        else:
            border = "#9CA3AF"
            text = "#4B5563"

        self.setStyleSheet(
            f"""
            QToolButton {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 10px;
                font-size: 8pt;
                padding: 1px 10px;
            }}
            QToolButton:hover {{
                border: 1px solid #374151;
            }}
            """
        )


class LabelSelectorWidget(QWidget):
    """Selected label view + candidate label selector."""

    def __init__(self, labels: list[Label], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._labels_by_id = {label.id: label for label in labels}
        self._buttons_by_id: dict[str, LabelChipButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self._selected_title = QLabel("選択済み")
        root.addWidget(self._selected_title)

        self._selected_frame = QFrame()
        self._selected_frame.setObjectName("selectedLabelsFrame")
        self._selected_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._selected_frame.setStyleSheet(
            """
            QFrame#selectedLabelsFrame {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
            }
            """
        )
        self._selected_layout = FlowLayout(self._selected_frame, margin=8, spacing=6)
        root.addWidget(self._selected_frame)

        self._candidate_title = QLabel("候補")
        root.addWidget(self._candidate_title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(110)

        self._candidate_container = QWidget()
        self._candidate_layout = FlowLayout(self._candidate_container, margin=8, spacing=6)
        self._scroll.setWidget(self._candidate_container)
        root.addWidget(self._scroll)

        for label in labels:
            button = LabelChipButton(label)
            button.toggled.connect(self._refresh_selected_view)
            self._buttons_by_id[label.id] = button
            self._candidate_layout.addWidget(button)

        self._refresh_selected_view()

    def selected_label_ids(self) -> list[str]:
        return [label_id for label_id, button in self._buttons_by_id.items() if button.isChecked()]

    def set_selected_label_ids(self, label_ids: Iterable[str]) -> None:
        selected_set = set(label_ids)
        for label_id, button in self._buttons_by_id.items():
            blocker = QSignalBlocker(button)
            button.setChecked(label_id in selected_set)
            del blocker
        self._refresh_selected_view()

    def _refresh_selected_view(self) -> None:
        while self._selected_layout.count():
            item = self._selected_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        selected_ids = self.selected_label_ids()
        if not selected_ids:
            empty_label = QLabel("未選択")
            empty_label.setStyleSheet("color: #6B7280; padding: 2px 4px;")
            self._selected_layout.addWidget(empty_label)
            return

        for label_id in selected_ids:
            label = self._labels_by_id[label_id]
            chip = SelectedLabelChipWidget(label)
            chip.remove_requested.connect(self._remove_label)
            self._selected_layout.addWidget(chip)

    def _remove_label(self, label_id: str) -> None:
        button = self._buttons_by_id.get(label_id)
        if button is None:
            return
        button.setChecked(False)


class SelectedLabelChipWidget(QFrame):
    remove_requested = pyqtSignal(str)

    def __init__(self, label: Label, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = label
        chip_bg = normalize_hex_color(label.color)

        self.setObjectName("selectedLabelChip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(22)

        layout = QHBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.setContentsMargins(10, 1, 8, 1)
        layout.setSpacing(4)

        self._name_label = QLabel(label.name)
        self._name_label.setObjectName("selectedLabelChipLabel")

        self._remove_button = QToolButton()
        self._remove_button.setObjectName("selectedLabelChipRemoveButton")
        self._remove_button.setText("x")
        self._remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_button.setAutoRaise(True)
        self._remove_button.clicked.connect(self._on_remove_clicked)

        layout.addWidget(self._name_label)
        layout.addWidget(self._remove_button)

        self.setStyleSheet(
            f"""
            QFrame#selectedLabelChip {{
                background-color: {chip_bg};
                border: 1px solid #111827;
                border-radius: 11px;
            }}
            QLabel#selectedLabelChipLabel {{
                color: #111827;
                background: transparent;
                border: none;
                font-size: 8pt;
            }}
            QToolButton#selectedLabelChipRemoveButton {{
                color: #374151;
                background: transparent;
                border: none;
                font-size: 7pt;
                font-weight: 600;
                padding: 0px;
            }}
            QToolButton#selectedLabelChipRemoveButton:hover {{
                color: #111827;
            }}
            """
        )

    def _on_remove_clicked(self) -> None:
        self.remove_requested.emit(self._label.id)
