from __future__ import annotations

from app.services.task_service import TaskService
from commands.base_command import BaseCommand


class DeleteTaskCommand(BaseCommand):
    """タスク削除コマンド"""

    def __init__(self, store, repository, task_service: TaskService, task_id: str) -> None:
        """イニシャライザ

        Args:
            store (BoardStore): ボードストア
            repository (TaskRepository): タスクリポジトリ
            task_service (TaskService): タスクサービス
            task_id (str): タスクID
        """
        super().__init__("タスク削除", store, repository)
        self._task_service = task_service
        self._task_id = task_id
        self._deleted_task = None

    def redo(self) -> None:
        """コマンドをやり直す"""
        if self._deleted_task is None:
            self._deleted_task = self._task_service.get_task(self._task_id)
        self._task_service.delete_task(self._deleted_task.id)
        self._save_board()

    def undo(self) -> None:
        """コマンドを取り消す"""
        if self._deleted_task is None:
            return
        self._task_service.insert_task(self._deleted_task)
        self._save_board()
