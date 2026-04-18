from __future__ import annotations

from PyQt6.QtCore import QPoint, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from domain.models.category import Category
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task
from ui.widgets.category_column_widget import CategoryColumnWidget


class BoardWidget(QWidget):
    add_task_requested = pyqtSignal(str)
    task_open_requested = pyqtSignal(str)
    task_context_requested = pyqtSignal(str, QPoint)
    category_context_requested = pyqtSignal(str, QPoint)
    board_reordered = pyqtSignal(str, dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns: dict[str, CategoryColumnWidget] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._layout = QHBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(10)
        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll)

    def rebuild_columns(
        self,
        categories: list[Category],
        tasks_by_category: dict[str, list[Task]],
        statuses: dict[str, Status],
        labels: dict[str, Label],
        date_format: str,
    ) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._columns.clear()

        for category in categories:
            column = CategoryColumnWidget()
            column.set_category(category)
            column.render_tasks(
                tasks=tasks_by_category.get(category.id, []),
                statuses=statuses,
                labels=labels,
                date_format=date_format,
            )
            column.add_task_requested.connect(self.add_task_requested.emit)
            column.task_open_requested.connect(self.task_open_requested.emit)
            column.task_context_requested.connect(self.task_context_requested.emit)
            column.category_context_requested.connect(self.category_context_requested.emit)
            column.tasks_reordered.connect(self._on_tasks_reordered)
            self._layout.addWidget(column, stretch=1)
            self._columns[category.id] = column

    def task_ids_by_category(self) -> dict[str, list[str]]:
        return {category_id: column.task_ids() for category_id, column in self._columns.items()}

    def _on_tasks_reordered(
        self,
        category_id: str,
        moved_task_id: str,
        _ordered_ids: list[str],
    ) -> None:
        snapshot = self.task_ids_by_category()
        if moved_task_id:
            # Cross-column drop can momentarily leave the moved task in both source and target
            # list widgets depending on Qt event timing. Normalize here so moved_task_id belongs
            # only to the target category before persisting order.
            for each_category_id, task_ids in snapshot.items():
                if each_category_id == category_id:
                    continue
                snapshot[each_category_id] = [
                    task_id for task_id in task_ids if task_id != moved_task_id
                ]
        self.board_reordered.emit(moved_task_id, snapshot)
