from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from domain.models.label import Label
from ui.widgets.label_selector_widget import LabelChipButton
from utils.color_utils import (
    TASK_LABEL_COLORS,
    contrast_text_color,
    darken_hex_color,
    normalize_hex_color,
)


class LabelFilterBar(QWidget):
    """ラベルフィルタバー"""

    changed = pyqtSignal(set, bool)
    """変更シグナル"""

    def __init__(self, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

        self._labels: dict[str, Label] = {}
        self._buttons: dict[str, LabelChipButton] = {}
        self._active_label_ids: set[str] = set()
        self._include_no_label = False
        self._no_label_button: LabelChipButton | None = None

    def set_labels(self, labels: list[Label]) -> None:
        """ラベルを設定する

        Args:
            labels (list[Label]): ラベルリスト
        """
        self._labels = {label.id: label for label in labels}
        self._rebuild()

    def set_active(self, active_label_ids: set[str], include_no_label: bool) -> None:
        """アクティブなラベルを設定する

        Args:
            active_label_ids (set[str]): アクティブなラベルIDのセット
            include_no_label (bool): ラベルなしのタスクを含むかどうか
        """
        self._active_label_ids = set(active_label_ids)
        self._include_no_label = include_no_label
        self._apply_colors()

    def active_label_ids(self) -> set[str]:
        """アクティブなラベルIDのセットを返す

        Returns:
            set[str]: アクティブなラベルIDのセット
        """
        return set(self._active_label_ids)

    def include_no_label(self) -> bool:
        """ラベルなしのタスクを含むかどうかを返す

        Returns:
            bool: ラベルなしのタスクを含むかどうか
        """
        return self._include_no_label

    def _rebuild(self) -> None:
        """ラベルフィルターバーを再構築する"""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons.clear()

        for label in sorted(self._labels.values(), key=lambda item: item.sort_order):
            button = LabelChipButton(label)
            button.clicked.connect(
                lambda _checked=False, label_id=label.id: self._toggle_label(label_id)
            )
            self._layout.addWidget(button)
            self._buttons[label.id] = button

        no_label_chip = Label(
            id="__no_label__",
            name="ラベル設定なし",
            color=self._no_label_base_color(),
            sort_order=-1,
        )
        self._no_label_button = LabelChipButton(no_label_chip)
        self._no_label_button.clicked.connect(self._toggle_no_label)
        self._layout.addWidget(self._no_label_button)
        self._layout.addStretch(1)
        self._apply_colors()

    def _no_label_base_color(self) -> str:
        """ラベル設定なしのベースカラーを返す"""
        return next(
            (
                normalize_hex_color(str(color.get("bg", "")))
                for color in TASK_LABEL_COLORS
                if str(color.get("id", "")) == "gray"
            ),
            normalize_hex_color("#E5E7EB"),
        )

    def _apply_colors(self) -> None:
        """ラベルフィルターバーに色を適用する"""
        for label_id, button in self._buttons.items():
            label = self._labels[label_id]
            on = label_id in self._active_label_ids
            base = normalize_hex_color(label.color)
            inactive = darken_hex_color(base, 0.55)
            color = base if on else inactive
            text_color = contrast_text_color(color)
            border_color = "#111827" if on else "#9CA3AF"
            button.setChecked(on)
            button.setStyleSheet(self._build_chip_stylesheet(color, text_color, border_color))

        if self._no_label_button is not None:
            self._no_label_button.setChecked(self._include_no_label)
            no_label_base = self._no_label_base_color()
            no_label_inactive = darken_hex_color(no_label_base, 0.55)
            no_label_bg = no_label_base if self._include_no_label else no_label_inactive
            no_label_text = contrast_text_color(no_label_bg)
            no_label_border = "#111827" if self._include_no_label else "#9CA3AF"
            self._no_label_button.setStyleSheet(
                self._build_chip_stylesheet(no_label_bg, no_label_text, no_label_border)
            )

    def _toggle_label(self, label_id: str) -> None:
        """ラベルを切り替える"""
        if label_id in self._active_label_ids:
            self._active_label_ids.remove(label_id)
        else:
            self._active_label_ids.add(label_id)
        self._apply_colors()
        self.changed.emit(set(self._active_label_ids), self._include_no_label)

    def _toggle_no_label(self) -> None:
        """ラベル設定なしを切り替える"""
        self._include_no_label = not self._include_no_label
        self._apply_colors()
        self.changed.emit(set(self._active_label_ids), self._include_no_label)

    def _build_chip_stylesheet(self, bg: str, text: str, border: str) -> str:
        """チップのスタイルシートを構築する"""
        return f"""
                QToolButton {{
                    background:{bg};
                    color:{text};
                    border:1px solid {border};
                    border-radius:10px;
                    padding:1px 10px;
                    font-size:8pt;
                }}
                QToolButton:hover {{
                    border:1px solid #374151;
                }}
                """
