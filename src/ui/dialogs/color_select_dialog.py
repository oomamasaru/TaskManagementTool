from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.color_utils import normalize_hex_color


class ColorSelectDialog(QDialog):
    def __init__(
        self,
        title: str,
        presets: list[dict[str, str]],
        color_key: str,
        default_color: str | None = None,
        default_name: str | None = None,
        show_name_input: bool = False,
        show_hide_checkbox: bool = False,
        default_hide_checkbox: bool = False,
        hide_checkbox_enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 220)
        self._preset_colors = [str(preset[color_key]) for preset in presets]
        self._swatch_buttons: dict[str, QPushButton] = {}
        self._show_name_input = show_name_input

        root = QVBoxLayout(self)
        self._name_edit: QLineEdit | None = None
        self._hide_checkbox: QCheckBox | None = None

        if show_name_input:
            root.addWidget(QLabel("名前"))
            self._name_edit = QLineEdit()
            self._name_edit.setText(default_name or "")
            root.addWidget(self._name_edit)

        root.addWidget(QLabel("プリセット色ボタン（または直接入力）"))

        swatch_widget = QWidget()
        swatch_layout = QGridLayout(swatch_widget)
        swatch_layout.setContentsMargins(0, 0, 0, 0)
        swatch_layout.setHorizontalSpacing(8)
        swatch_layout.setVerticalSpacing(8)
        for index, color in enumerate(self._preset_colors):
            button = QPushButton("")
            button.setCheckable(True)
            button.setFixedSize(24, 24)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(color)
            button.clicked.connect(lambda _checked=False, value=color: self._on_swatch_clicked(value))
            self._swatch_buttons[color] = button
            row = index // 8
            col = index % 8
            swatch_layout.addWidget(button, row, col)
        root.addWidget(swatch_widget)

        row = QHBoxLayout()
        self._color_edit = QLineEdit()
        self._color_edit.setPlaceholderText("#RRGGBB")
        self._color_edit.textChanged.connect(self._sync_swatch_selection_from_text)
        picker_button = QPushButton("カラーピッカー")
        picker_button.clicked.connect(self._open_color_dialog)
        row.addWidget(self._color_edit, stretch=1)
        row.addWidget(picker_button)
        root.addLayout(row)

        if show_hide_checkbox:
            self._hide_checkbox = QCheckBox("一覧から隠す")
            self._hide_checkbox.setChecked(default_hide_checkbox)
            self._hide_checkbox.setEnabled(hide_checkbox_enabled)
            root.addWidget(self._hide_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        initial = normalize_hex_color(default_color or "", default="")
        if initial:
            self._color_edit.setText(initial)
        self._sync_swatch_selection_from_text()

    def selected_color(self) -> str:
        return self._color_edit.text().strip()

    def selected_name(self) -> str:
        if self._name_edit is None:
            return ""
        return self._name_edit.text().strip()

    def hide_checkbox_value(self) -> bool:
        if self._hide_checkbox is None:
            return False
        return self._hide_checkbox.isChecked()

    @classmethod
    def pick_color(
        cls,
        title: str,
        presets: list[dict[str, str]],
        color_key: str,
        default_color: str | None = None,
        parent: QWidget | None = None,
    ) -> tuple[str, bool]:
        dialog = cls(title, presets, color_key, default_color, parent)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return "", False
        return dialog.selected_color(), True

    def accept(self) -> None:
        if self._show_name_input and not self.selected_name():
            QMessageBox.information(self, "入力エラー", "名前を入力してください。")
            return
        if not normalize_hex_color(self.selected_color(), default=""):
            QMessageBox.information(self, "入力エラー", "色は #RRGGBB 形式で入力してください。")
            return
        super().accept()

    def _on_swatch_clicked(self, color: str) -> None:
        self._color_edit.setText(color)
        self._set_selected_swatch(color)

    def _open_color_dialog(self) -> None:
        color = QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        self._color_edit.setText(color.name().upper())
        self._sync_swatch_selection_from_text()

    def _sync_swatch_selection_from_text(self) -> None:
        color = normalize_hex_color(self._color_edit.text(), default="")
        if color in self._swatch_buttons:
            self._set_selected_swatch(color)
            return
        self._set_selected_swatch(None)

    def _set_selected_swatch(self, color: str | None) -> None:
        for swatch_color, button in self._swatch_buttons.items():
            selected = swatch_color == color
            button.setChecked(selected)
            border = "2px solid #111827" if selected else "1px solid #9CA3AF"
            button.setStyleSheet(
                f"QPushButton{{background:{swatch_color};border:{border};border-radius:4px;}}"
            )
