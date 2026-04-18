from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task
from ui.widgets.label_selector_widget import LabelChipButton
from utils.color_utils import due_state_color, normalize_hex_color
from utils.date_utils import calc_due_state, calc_remaining_days


class TaskCardWidget(QFrame):
    def __init__(
        self,
        task: Task,
        status: Status | None,
        labels: list[Label],
        date_format: str = "%Y-%m-%d",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._task = task
        self._date_format = date_format
        self.setObjectName("taskCardRoot")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        status_color = normalize_hex_color(status.color if status else "#6B7280")
        status_strip = QFrame()
        status_strip.setObjectName("taskCardStatusStrip")
        status_strip.setFixedWidth(8)
        status_strip.setStyleSheet(
            f"background:{status_color};"
            "border:none;"
            "border-top-left-radius:6px;"
            "border-bottom-left-radius:6px;"
        )
        root.addWidget(status_strip)

        card = QWidget()
        body = QVBoxLayout(card)
        body.setContentsMargins(10, 8, 10, 8)
        body.setSpacing(4)
        root.addWidget(card, stretch=1)

        today = date.today()
        due_state = calc_due_state(task.due_date, today)
        remaining_days = calc_remaining_days(task.due_date, today)

        header_line = QHBoxLayout()
        header_line.setContentsMargins(0, 0, 0, 0)
        header_line.setSpacing(6)

        title = QLabel(task.title)
        title.setStyleSheet("font-weight:600;")
        header_line.addWidget(title, stretch=1)

        remain_label = QLabel(self._format_remaining_text(remaining_days))
        remain_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        remain_label.setStyleSheet(f"font-size:8pt; color:{due_state_color(due_state)};")
        header_line.addWidget(remain_label, alignment=Qt.AlignmentFlag.AlignTop)
        body.addLayout(header_line)

        status_text = status.name if status is not None else "未設定"
        status_label = QLabel(f"ステータス: {status_text}")
        status_label.setStyleSheet("color:#374151; font-size:8pt;")
        body.addWidget(status_label)

        if labels:
            labels_row = QHBoxLayout()
            labels_row.setContentsMargins(0, 0, 0, 0)
            labels_row.setSpacing(4)
            for label in labels:
                chip = LabelChipButton(label)
                chip.setCheckable(False)
                chip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                chip.setCursor(Qt.CursorShape.ArrowCursor)
                labels_row.addWidget(chip)
            labels_row.addStretch(1)
            body.addLayout(labels_row)

        bg = normalize_hex_color(task.color or "#F8FAFC")
        self.setStyleSheet(
            f"""
            QFrame#taskCardRoot {{
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                background: {bg};
            }}
            QFrame#taskCardRoot QLabel {{
                border: none;
                background: transparent;
            }}
            """
        )

    def set_task(self, task: Task) -> None:
        self._task = task

    def _format_remaining_text(self, remaining_days: int | None) -> str:
        if remaining_days is None:
            return "期限なし"
        if remaining_days < 0:
            return f"超過{abs(remaining_days)}日"
        if remaining_days == 0:
            return "今日まで"
        return f"残り{remaining_days}日"

    def show_context_menu(self) -> None:
        return

    def open_detail(self) -> None:
        return
