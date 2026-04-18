from __future__ import annotations

from app.dto import TaskInputData
from app.services.task_service import TaskService
from commands.base_command import BaseCommand


class AddTaskCommand(BaseCommand):
    def __init__(self, store, repository, task_service: TaskService, input_data: TaskInputData) -> None:
        super().__init__("タスク追加", store, repository)
        self._task_service = task_service
        self._input_data = input_data
        self._task = None

    def redo(self) -> None:
        if self._task is None:
            self._task = self._task_service.create_task(self._input_data)
        else:
            self._task_service.insert_task(self._task)
        self._save_board()

    def undo(self) -> None:
        if self._task is None:
            return
        self._task_service.delete_task(self._task.id)
        self._save_board()

