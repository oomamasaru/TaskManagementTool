from __future__ import annotations

from app.services.task_service import TaskService
from commands.base_command import BaseCommand


class DuplicateTaskCommand(BaseCommand):
    def __init__(self, store, repository, task_service: TaskService, source_task_id: str) -> None:
        super().__init__("タスク複製", store, repository)
        self._task_service = task_service
        self._source_task_id = source_task_id
        self._duplicated_task = None

    def redo(self) -> None:
        if self._duplicated_task is None:
            self._duplicated_task = self._task_service.duplicate_task(self._source_task_id)
        else:
            self._task_service.insert_task(self._duplicated_task)
        self._save_board()

    def undo(self) -> None:
        if self._duplicated_task is None:
            return
        self._task_service.delete_task(self._duplicated_task.id)
        self._save_board()

