from __future__ import annotations

from app.services.task_service import TaskService
from commands.base_command import BaseCommand


class MoveTaskCommand(BaseCommand):
    """タスク移動コマンド"""

    def __init__(
        self,
        store,
        repository,
        task_service: TaskService,
        task_id: str,
        after_order_task_ids: dict[str, list[str]],
    ) -> None:
        """イニシャライザ

        Args:
            store (BoardStore): ボードストア
            repository (TaskRepository): タスクリポジトリ
            task_service (TaskService): タスクサービス
            task_id (str): タスクID
            after_order_task_ids (dict[str, list[str]]): 移動後のタスクIDの辞書
        """
        super().__init__("タスク移動", store, repository)
        self._task_service = task_service
        self._task_id = task_id
        self._before_order_task_ids = store.task_ids_by_category(include_hidden=True)
        self._after_order_task_ids = after_order_task_ids
        task = store.find_task(task_id)
        self._before_category_id = task.category_id if task else ""
        self._after_category_id = self._resolve_after_category_id(task_id, after_order_task_ids)

    def redo(self) -> None:
        """コマンドをやり直す"""
        self._task_service.apply_order_snapshot(self._after_order_task_ids)
        self._save_board()

    def undo(self) -> None:
        """コマンドを取り消す"""
        self._task_service.apply_order_snapshot(self._before_order_task_ids)
        self._save_board()

    def _resolve_after_category_id(self, task_id: str, order_snapshot: dict[str, list[str]]) -> str:
        """移動後のカテゴリIDを解決する

        Args:
            task_id (str): タスクID
            order_snapshot (dict[str, list[str]]): 移動後のタスクIDの辞書

        Returns:
            str: 移動後のカテゴリID
        """
        for category_id, task_ids in order_snapshot.items():
            if task_id in task_ids:
                return category_id
        return ""
