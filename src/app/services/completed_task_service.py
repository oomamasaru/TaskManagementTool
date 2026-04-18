from __future__ import annotations

from app.board_store import BoardStore
from infrastructure.providers.datetime_provider import DateTimeProvider


class CompletedTaskService:
    def __init__(self, store: BoardStore, datetime_provider: DateTimeProvider) -> None:
        self._store = store
        self._datetime_provider = datetime_provider

    def get_completed_tasks(self):
        tasks = self._store.get_completed_tasks()
        return sorted(
            tasks,
            key=lambda task: task.completed_at.isoformat() if task.completed_at else "",
            reverse=True,
        )

    def restore_task(self, task_id: str):
        task = self._store.find_task(task_id)
        if task is None:
            raise ValueError("タスクが見つかりません。")
        task.status_id = "not_started"
        task.completed_at = None
        task.updated_at = self._datetime_provider.now()
        return task

    def delete_completed_task(self, task_id: str) -> None:
        task = self._store.find_task(task_id)
        if task is None:
            raise ValueError("タスクが見つかりません。")
        self._store.board_data.tasks = [
            current for current in self._store.board_data.tasks if current.id != task_id
        ]
