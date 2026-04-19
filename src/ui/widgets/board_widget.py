from __future__ import annotations

from PyQt6.QtCore import QPoint, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from domain.models.category import Category
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task
from ui.widgets.category_column_widget import CategoryColumnWidget


class BoardWidget(QWidget):
    """ボードウィジェット"""

    add_task_requested = pyqtSignal(str)
    """タスク追加リクエストシグナル

    Args:
        str (str): カテゴリID
    """

    task_open_requested = pyqtSignal(str)
    """タスクオープンリクエストシグナル

    Args:
        str (str): タスクID
    """

    task_context_requested = pyqtSignal(str, QPoint)
    """タスクコンテキストリクエストシグナル

    Args:
        str (str): タスクID
        QPoint (QPoint): コンテキストメニューの表示位置
    """

    category_context_requested = pyqtSignal(str, QPoint)
    """カテゴリコンテキストリクエストシグナル

    Args:
        str (str): カテゴリID
        QPoint (QPoint): コンテキストメニューの表示位置
    """

    board_reordered = pyqtSignal(str, dict)
    """ボード再オーダーシグナル

    Args:
        str (str): 移動したタスクID
        dict (dict[str, list[str]]): カテゴリごとのタスクIDのリストの辞書
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self._columns: dict[str, CategoryColumnWidget] = {}
        """カラムの辞書"""

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
        """カラムを再構築する

        Args:
            categories (list[Category]): カテゴリのリスト
            tasks_by_category (dict[str, list[Task]]): カテゴリごとのタスクのリストの辞書
            statuses (dict[str, Status]): ステータスの辞書
            labels (dict[str, Label]): ラベルの辞書
            date_format (str): 日付のフォーマット
        """
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
        """カテゴリごとのタスクIDのリストの辞書を取得する

        Returns:
            dict[str, list[str]]: カテゴリIDごとのタスクIDのリストの辞書
        """
        return {category_id: column.task_ids() for category_id, column in self._columns.items()}

    def _on_tasks_reordered(
        self,
        category_id: str,
        moved_task_id: str,
        _ordered_ids: list[str],
    ) -> None:
        """タスクの並び替えイベントを処理する

        Args:
            category_id (str): カテゴリID
            moved_task_id (str): 移動したタスクID
            _ordered_ids (list[str]): 並び替え後のタスクIDのリスト
        """
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
