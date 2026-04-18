from __future__ import annotations

from app.dto import TaskInputData
from app.services.task_service import TaskService
from commands.base_command import BaseCommand


class EditTaskCommand(BaseCommand):
    def __init__(
        self,
        store,
        repository,
        task_service: TaskService,
        task_id: str,
        input_data: TaskInputData,
    ) -> None:
        super().__init__("タスク編集", store, repository)
        self._task_service = task_service
        self._task_id = task_id
        self._input_data = input_data
        self._before_task = self._task_service.get_task(task_id)
        self._after_task = None

    def redo(self) -> None:
        if self._after_task is None:
            updated = self._task_service.update_task(self._task_id, self._input_data)
            self._after_task = updated.clone()
        else:
            self._task_service.replace_task(self._after_task)
        self._save_board()

    def undo(self) -> None:
        self._task_service.replace_task(self._before_task)
        self._save_board()

