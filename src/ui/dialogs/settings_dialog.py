from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from domain.models.app_settings import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.resize(420, 220)

        root = QVBoxLayout(self)
        form = QFormLayout()
        root.addLayout(form)

        self._data_file_path = QLineEdit()
        self._date_format = QLineEdit()

        form.addRow("データファイル", self._data_file_path)
        form.addRow("日付表示", self._date_format)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def load_settings(self, settings: AppSettings) -> None:
        self._data_file_path.setText(settings.data_file_path)
        self._date_format.setText(settings.date_format)

    def get_input(self) -> AppSettings:
        return AppSettings(
            data_file_path=self._data_file_path.text().strip() or "task_board.json",
            date_format=self._date_format.text().strip() or "%Y-%m-%d",
        )
