from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from domain.models.category import Category
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task
from ui.widgets.task_card_widget import TaskCardWidget


class TaskListWidget(QListWidget):
    reordered = pyqtSignal(str, str, list)

    def __init__(self, category_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._category_id = category_id
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)

    def set_category_id(self, category_id: str) -> None:
        self._category_id = category_id

    def mimeData(self, items):  # noqa: N802
        mime_data = super().mimeData(items)
        if items:
            mime_data.setText(str(items[0].data(Qt.ItemDataRole.UserRole)))
        return mime_data

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        moved_task_id = event.mimeData().text()
        super().dropEvent(event)
        self.reordered.emit(self._category_id, moved_task_id, self.task_ids())

    def task_ids(self) -> list[str]:
        ids: list[str] = []
        for row in range(self.count()):
            item = self.item(row)
            ids.append(str(item.data(Qt.ItemDataRole.UserRole)))
        return ids


class CategoryColumnWidget(QFrame):
    add_task_requested = pyqtSignal(str)
    task_open_requested = pyqtSignal(str)
    task_context_requested = pyqtSignal(str, QPoint)
    category_context_requested = pyqtSignal(str, QPoint)
    tasks_reordered = pyqtSignal(str, str, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._category: Category | None = None

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("QFrame{border:1px solid #E5E7EB;border-radius:6px;background:#F9FAFB;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._header_widget = QWidget()
        self._header_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._header_widget.customContextMenuRequested.connect(self._on_category_context_menu)
        header = QHBoxLayout(self._header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        self._title_label = QLabel("-")
        self._title_label.setStyleSheet("font-weight:700;")
        self._add_button = QPushButton("＋")
        self._add_button.setFixedWidth(28)
        self._add_button.clicked.connect(self._emit_add_task)
        header.addWidget(self._title_label)
        header.addStretch(1)
        header.addWidget(self._add_button)
        root.addWidget(self._header_widget)

        self._list = TaskListWidget("")
        self._list.setSpacing(6)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.reordered.connect(self.tasks_reordered.emit)
        root.addWidget(self._list)

    def set_category(self, category: Category) -> None:
        self._category = category
        self._title_label.setText(category.name)
        self._list.set_category_id(category.id)

    def render_tasks(
        self,
        tasks: list[Task],
        statuses: dict[str, Status],
        labels: dict[str, Label],
        date_format: str,
    ) -> None:
        self._list.clear()
        for task in tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            card = TaskCardWidget(
                task=task,
                status=statuses.get(task.status_id),
                labels=[labels[label_id] for label_id in task.label_ids if label_id in labels],
                date_format=date_format,
            )
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

    def task_ids(self) -> list[str]:
        return self._list.task_ids()

    def _emit_add_task(self) -> None:
        if self._category is None:
            return
        self.add_task_requested.emit(self._category.id)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        self.task_open_requested.emit(str(item.data(Qt.ItemDataRole.UserRole)))

    def _on_context_menu(self, point: QPoint) -> None:
        item = self._list.itemAt(point)
        if item is None:
            if self._category is None:
                return
            global_pos = self._list.viewport().mapToGlobal(point)
            self.category_context_requested.emit(self._category.id, global_pos)
            return
        task_id = str(item.data(Qt.ItemDataRole.UserRole))
        global_pos = self._list.viewport().mapToGlobal(point)
        self.task_context_requested.emit(task_id, global_pos)

    def _on_category_context_menu(self, point: QPoint) -> None:
        if self._category is None:
            return
        global_pos = self._header_widget.mapToGlobal(point)
        self.category_context_requested.emit(self._category.id, global_pos)
