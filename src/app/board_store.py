from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QUndoStack

from domain.models.board_data import BoardData
from domain.models.category import Category
from domain.models.filter_condition import FilterCondition
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task


class BoardStore(QObject):
    """ボードの状態を保持するクラス"""

    board_changed = pyqtSignal()
    filter_changed = pyqtSignal()

    def __init__(self) -> None:
        """イニシャライザ"""
        super().__init__()
        self.board_data: BoardData = BoardData()
        """ボードデータ"""
        self.filter_condition = FilterCondition()
        """フィルター条件"""
        self.selected_task_id: str | None = None
        """選択中のタスクID"""
        self.undo_stack = QUndoStack(self)
        """アンドゥスタック"""

    def load(self, data: BoardData) -> None:
        """ボードデータを読み込む

        Args:
            data (BoardData): ボードデータ
        """
        self.board_data = data
        self.filter_condition = FilterCondition(
            active_label_ids={label.id for label in data.labels},
            include_no_label=True,
        )
        self.selected_task_id = None
        self.undo_stack.clear()
        self.notify_board_changed()

    def get_tasks_for_category(self, category_id: str) -> list[Task]:
        """指定されたカテゴリのタスクを取得する

        Args:
            category_id (str): カテゴリID

        Returns:
            list[Task]: タスクのリスト
        """
        hidden_status_ids = self._hidden_status_ids()
        tasks = [
            task
            for task in self.board_data.tasks
            if task.category_id == category_id and task.status_id not in hidden_status_ids
        ]
        filtered = [task for task in tasks if self._matches_filter(task)]
        return sorted(filtered, key=lambda task: task.sort_order)

    def get_completed_tasks(self) -> list[Task]:
        """完了したタスクを取得する

        Returns:
            list[Task]: 完了したタスクのリスト
        """
        hidden_status_ids = self._hidden_status_ids()
        tasks = [task for task in self.board_data.tasks if task.status_id in hidden_status_ids]
        tasks.sort(
            key=lambda task: task.completed_at.isoformat() if task.completed_at else "",
            reverse=True,
        )
        return tasks

    def get_categories(self) -> list[Category]:
        """カテゴリを取得する"""
        return sorted(self.board_data.categories, key=lambda category: category.sort_order)

    def get_labels(self) -> list[Label]:
        """ラベルを取得する"""
        return sorted(self.board_data.labels, key=lambda label: label.sort_order)

    def get_statuses(self) -> list[Status]:
        """ステータスを取得する"""
        return sorted(self.board_data.statuses, key=lambda status: status.sort_order)

    def set_filter(self, condition: FilterCondition) -> None:
        """フィルター条件を設定する

        Args:
            condition (FilterCondition): フィルター条件
        """
        self.filter_condition = condition
        self.filter_changed.emit()
        self.notify_board_changed()

    def task_ids_by_category(self, include_hidden: bool = False) -> dict[str, list[str]]:
        """カテゴリごとのタスクIDを取得する

        Args:
            include_hidden (bool): 完了したタスクを含むかどうか

        Returns:
            dict[str, list[str]]: カテゴリIDごとのタスクIDの辞書
        """
        hidden_status_ids = self._hidden_status_ids()
        result: dict[str, list[str]] = {}
        for category in self.get_categories():
            tasks = [
                task
                for task in self.board_data.tasks
                if task.category_id == category.id
                and (include_hidden or task.status_id not in hidden_status_ids)
            ]
            tasks.sort(key=lambda task: task.sort_order)
            result[category.id] = [task.id for task in tasks]
        return result

    def find_task(self, task_id: str) -> Task | None:
        """タスクIDからタスクを取得する

        Args:
            task_id (str): タスクID

        Returns:
            Task | None: タスク
        """
        return next((task for task in self.board_data.tasks if task.id == task_id), None)

    def find_status(self, status_id: str) -> Status | None:
        """ステータスIDからステータスを取得する

        Args:
            status_id (str): ステータスID

        Returns:
            Status | None: ステータス
        """
        return next((status for status in self.board_data.statuses if status.id == status_id), None)

    def find_category(self, category_id: str) -> Category | None:
        """カテゴリIDからカテゴリを取得する

        Args:
            category_id (str): カテゴリID

        Returns:
            Category | None: カテゴリ
        """
        return next(
            (category for category in self.board_data.categories if category.id == category_id),
            None,
        )

    def notify_board_changed(self) -> None:
        """ボード変更通知を発行する"""
        self.board_changed.emit()

    def clone_task(self, task_id: str) -> Task:
        """タスクをクローンする

        Args:
            task_id (str): タスクID

        Returns:
            Task: クローンしたタスク
        """
        task = self.find_task(task_id)
        if task is None:
            msg = f"Task not found: {task_id}"
            raise ValueError(msg)
        return deepcopy(task)

    def _hidden_status_ids(self) -> set[str]:
        """ボードから隠すステータスIDを取得する

        Returns:
            set[str]: 隠すステータスIDのセット
        """
        return {status.id for status in self.board_data.statuses if status.hides_from_board}

    def _matches_filter(self, task: Task) -> bool:
        """タスクがフィルター条件に一致するかどうかを判定する

        Args:
            task (Task): タスク

        Returns:
            bool: タスクがフィルター条件に一致するかどうか
        """
        condition = self.filter_condition

        search_text = condition.search_text.strip().lower()
        if search_text:
            title = task.title.lower()
            detail = task.detail.lower()
            if search_text not in title and search_text not in detail:
                return False

        label_filter_enabled = bool(condition.active_label_ids) or condition.include_no_label
        if label_filter_enabled:
            has_selected_label = bool(set(task.label_ids).intersection(condition.active_label_ids))
            is_no_label_task = not task.label_ids
            if not (has_selected_label or (condition.include_no_label and is_no_label_task)):
                return False

        return True
