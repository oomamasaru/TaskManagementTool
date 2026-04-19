from __future__ import annotations

from app.dto import TaskInputData
from app.services.task_service import TaskService
from commands.base_command import BaseCommand


class AddTaskCommand(BaseCommand):
    """タスク追加コマンド"""

    def __init__(
        self, store, repository, task_service: TaskService, input_data: TaskInputData
    ) -> None:
        """イニシャライザ

        Args:
            store (BoardStore): ボードストア
            repository (TaskRepository): タスクリポジトリ
            task_service (TaskService): タスクサービス
            input_data (TaskInputData): タスク入力データ
        """
        super().__init__("タスク追加", store, repository)
        self._task_service = task_service
        self._input_data = input_data
        self._task = None

    def redo(self) -> None:
        """コマンドをやり直す"""
        if self._task is None:
            self._task = self._task_service.create_task(self._input_data)
        else:
            self._task_service.insert_task(self._task)
        self._save_board()

    def undo(self) -> None:
        """コマンドを取り消す"""
        if self._task is None:
            return
        self._task_service.delete_task(self._task.id)
        self._save_board()
