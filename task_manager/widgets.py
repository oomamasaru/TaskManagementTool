from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from const import message as msg
from task_manager.models import Label, Status, Task


def parse_due_date(value: str | None) -> date | None:
    """期限を解析する

    Args:
        value (str | None): 期限の文字列

    Returns:
        date | None: 解析された期限の日付
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def darken_hex_color(hex_color: str, factor: float = 0.55) -> str:
    """16進数カラーコードを暗くする

    Args:
        hex_color (str): 16進数カラーコード
        factor (float, optional): 暗くする倍率. Defaults to 0.55.

    Returns:
        str: 暗くした16進数カラーコード
    """
    text = hex_color.strip().lstrip("#")
    if len(text) != 6:
        return "#6B7280"
    try:
        r = int(text[0:2], 16)
        g = int(text[2:4], 16)
        b = int(text[4:6], 16)
    except ValueError:
        return "#6B7280"
    r = int(max(0, min(255, r * factor)))
    g = int(max(0, min(255, g * factor)))
    b = int(max(0, min(255, b * factor)))
    return f"#{r:02X}{g:02X}{b:02X}"


class TaskCardWidget(QFrame):
    def __init__(
        self,
        task: Task,
        status: Status | None,
        labels: list[Label],
        parent: QWidget | None = None,
    ) -> None:
        """イニシャライザ

        Args:
            task (Task): タスク
            status (Status | None): ステータス
            labels (list[Label]): ラベル
            parent (QWidget | None, optional): 親ウィジェット. Defaults to None.
        """
        super().__init__(parent)
        self.task = task
        self.status = status
        self.labels = labels
        self._build_ui()

    def _build_ui(self) -> None:
        """UIを構築する"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("taskCard")
        base_color = self.task.color or "#FFFFFF"
        self.setStyleSheet(
            f"""
            QFrame#taskCard {{
                background-color: {base_color};
                border: 1px solid #D1D5DB;
                border-radius: 8px;
            }}
            QLabel {{
                color: #111827;
            }}
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        status_bar = QFrame(self)
        status_bar.setFixedWidth(8)
        status_color = self.status.color if self.status else "#6B7280"
        status_bar.setStyleSheet(
            f"QFrame {{ background-color: {status_color}; border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}"
        )
        root.addWidget(status_bar)

        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 8, 10, 8)
        body_layout.setSpacing(4)
        root.addWidget(body)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        title_label = QLabel(self.task.title, body)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: 600;")
        top_row.addWidget(title_label, 1)

        remain_label = QLabel(self._remaining_text(), body)
        remain_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        remain_label.setStyleSheet(f"font-size: 11px; color: {self._remaining_color()};")
        top_row.addWidget(remain_label, 0)
        body_layout.addLayout(top_row)

        due_date = self.task.due_date if self.task.due_date else msg.LBL_DUE_DATE_NONE
        due_label = QLabel(f"{msg.LBL_DUE_DATE}: {due_date}", body)
        due_label.setStyleSheet("font-size: 11px; color: #374151;")
        body_layout.addWidget(due_label)

        if self.labels:
            text = " / ".join([x.name for x in self.labels])
        else:
            text = msg.LBL_LABEL_NONE
        label_label = QLabel(text, body)
        label_label.setStyleSheet("font-size: 11px; color: #1F2937;")
        label_label.setWordWrap(True)
        body_layout.addWidget(label_label)

    def _remaining_text(self) -> str:
        """残り日数を返す"""
        due = parse_due_date(self.task.due_date)
        if not due:
            return msg.LBL_DUE_DATE_NONE
        diff = (due - date.today()).days
        if diff < 0:
            return msg.LBL_DUE_OVER.format(days=abs(diff))
        if diff == 0:
            return msg.LBL_DUE_TODAY
        return msg.LBL_DUE_REMAINING.format(days=diff)

    def _remaining_color(self) -> str:
        """残り日数の色を返す"""
        due = parse_due_date(self.task.due_date)
        if not due:
            return "#9CA3AF"
        diff = (due - date.today()).days
        if diff < 0:
            return "#B91C1C"
        if diff == 0:
            return "#C2410C"
        if diff <= 3:
            return "#9A3412"
        return "#6B7280"


class TaskListWidget(QListWidget):
    """タスクリストウィジェット"""

    dropped = pyqtSignal()

    def __init__(self, category_id: str, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            category_id (str): カテゴリID
            parent (QWidget | None, optional): 親ウィジェット. Defaults to None.
        """
        super().__init__(parent)
        self.category_id = category_id
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                background: #F9FAFB;
            }
            QListWidget::item {
                margin: 4px;
            }
            """
        )

    def dropEvent(self, event) -> None:  # noqa: N802
        super().dropEvent(event)
        self.dropped.emit()
