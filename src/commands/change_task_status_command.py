from __future__ import annotations

from app.services.status_service import StatusService
from commands.base_command import BaseCommand


class ChangeTaskStatusCommand(BaseCommand):
    """タスクステータス変更コマンド"""

    def __init__(
        self,
        store,
        repository,
        status_service: StatusService,
        task_id: str,
        after_status_id: str,
    ) -> None:
        """イニシャライザ

        Args:
            store (BoardStore): ボードストア
            repository (TaskRepository): タスクリポジトリ
            status_service (StatusService): ステータスサービス
            task_id (str): タスクID
            after_status_id (str): 変更後のステータスID
        """
        super().__init__("ステータス変更", store, repository)
        self._store = store
        self._status_service = status_service
        self._task_id = task_id
        self._before_task = store.clone_task(task_id)
        self._after_status_id = after_status_id
        self._after_completed_at = None
        self._has_executed = False

    def redo(self) -> None:
        """コマンドをやり直す"""
        if not self._has_executed:
            self._status_service.change_status(self._task_id, self._after_status_id)
            current = self._store.find_task(self._task_id)
            self._after_completed_at = current.completed_at if current else None
            self._has_executed = True
        else:
            self._status_service.set_task_status_exact(
                self._task_id, self._after_status_id, self._after_completed_at
            )
        self._save_board()

    def undo(self) -> None:
        """コマンドを取り消す"""
        self._status_service.set_task_status_exact(
            self._task_id,
            self._before_task.status_id,
            self._before_task.completed_at,
        )
        self._save_board()
