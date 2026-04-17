from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from typing import TypeVar

from PyQt6.QtCore import QObject, pyqtSignal

from task_manager.commands import CommandManager, SnapshotCommand
from task_manager.models import (
    COMPLETED_STATUS_ID,
    NOT_STARTED_STATUS_ID,
    BoardData,
    Category,
    Label,
    Prefix,
    Status,
    Task,
    default_categories,
    default_statuses,
    generate_id,
    now_iso,
)
from task_manager.storage import StorageManager
from const import message as msg

T = TypeVar("T")


def _repair_broken_task(  # noqa: C901
    board: BoardData,
    category_ids: set[str],
    first_category_id: str,
    status_map: dict[str, Status],
    label_ids: set[str],
) -> None:
    """壊れているタスクを修復する

    Args:
        board (BoardData): boardデータ
        category_ids (set[str]): カテゴリIDのセット
        first_category_id (str): 最初のカテゴリID
        status_map (dict[str, Status]): ステータスマップ
        label_ids (set[str]): ラベルIDのセット
    """
    for task in board.tasks:
        if not task.id:
            task.id = generate_id(Prefix.TASK)
        # カテゴリIDがない場合は、最初のカテゴリIDを設定する
        if task.category_id not in category_ids:
            task.category_id = first_category_id
        # 既存のステータスにない場合は、未着手に設定する
        if task.status_id not in status_map:
            task.status_id = NOT_STARTED_STATUS_ID

        if task.label_ids:
            # 既存のラベルにない場合は、ラベルIDを削除する
            task.label_ids = [x for x in task.label_ids if x in label_ids]

        # タスクが表示対象の場合、完了日時をNoneにする
        status = status_map.get(task.status_id)
        if (status and not status.hides_from_board) or task.completed_at == "":
            task.completed_at = None

        if task.due_date == "":
            task.due_date = None
        if task.color == "":
            task.color = None
        if not task.created_at:
            task.created_at = now_iso()
        if not task.updated_at:
            task.updated_at = now_iso()


def _repair_broken_status(board: BoardData, fixed_defaults: dict[str, Status]) -> None:
    """壊れているステータスを強制的に修正する

    Args:
        board (BoardData): boardデータ
        fixed_defaults (dict[str, Status]): 固定ステータスマップ
    """
    for status in board.statuses:
        # 未着手
        if status.id == NOT_STARTED_STATUS_ID:
            status.is_system = True
            status.hides_from_board = False
            if not status.color:
                status.color = fixed_defaults[NOT_STARTED_STATUS_ID].color
            if not status.name:
                status.name = fixed_defaults[NOT_STARTED_STATUS_ID].name
        # 完了
        if status.id == COMPLETED_STATUS_ID:
            status.is_system = True
            status.hides_from_board = True
            if not status.color:
                status.color = fixed_defaults[COMPLETED_STATUS_ID].color
            if not status.name:
                status.name = fixed_defaults[COMPLETED_STATUS_ID].name


class BoardController(QObject):
    """操作ハンドラと状態管理を担うコントローラ"""

    changed = pyqtSignal()
    """状態が変更されたことを通知するシグナル"""
    undo_redo_changed = pyqtSignal()
    """undo/redo の有効/無効状態が変わったことを通知するシグナル"""

    def __init__(self, storage: StorageManager) -> None:
        """イニシャライザ

        Args:
            storage (StorageManager): ストレージマネージャ
        """
        super().__init__()
        self.storage = storage
        self.command_manager = CommandManager()
        """コマンドマネージャ"""
        self.data = self.storage.load()
        """タスクボードデータ"""
        self._normalize_inplace(self.data)
        self.storage.save(self.data)

    @property
    def categories(self) -> list[Category]:
        return sorted(self.data.categories, key=lambda x: (x.sort_order, x.name))

    @property
    def labels(self) -> list[Label]:
        return sorted(self.data.labels, key=lambda x: (x.sort_order, x.name))

    @property
    def statuses(self) -> list[Status]:
        return sorted(self.data.statuses, key=lambda x: (x.sort_order, x.name))

    @property
    def tasks(self) -> list[Task]:
        return list(self.data.tasks)

    def get_task(self, task_id: str) -> Task | None:
        for task in self.data.tasks:
            if task.id == task_id:
                return task
        return None

    def get_status(self, status_id: str) -> Status | None:
        return self.data.get_status(status_id)

    def get_label(self, label_id: str) -> Label | None:
        return self.data.get_label(label_id)

    def get_category(self, category_id: str) -> Category | None:
        return self.data.get_category(category_id)

    def get_completed_tasks(self) -> list[Task]:
        """完了済みタスクを取得する

        Args:
            status (Status): ステータス

        Returns:
            list[Task]: 完了済みタスク
        """
        hidden_status_ids = {x.id for x in self.statuses if x.hides_from_board}
        tasks = [x for x in self.data.tasks if x.status_id in hidden_status_ids]
        return sorted(
            tasks,
            key=lambda x: (x.completed_at or "", x.updated_at),
            reverse=True,
        )

    def add_category(self, name: str) -> None:
        """カテゴリを追加する

        Args:
            name (str): カテゴリ名
        """
        display_name = name.strip()
        if not display_name:
            raise ValueError(msg.ERR_CATEGORY_NAME_REQUIRED)
        existing = [x.sort_order for x in self.data.categories]
        sort_order = (max(existing) + 1) if existing else 1
        category = Category(
            id=generate_id(Prefix.CATEGORY),
            name=display_name,
            sort_order=sort_order,
        )
        self._run_mutation(
            msg.MUTATION_ADD_CATEGORY,
            lambda board: board.categories.append(category),
            undoable=False,
        )

    def delete_category(self, category_id: str) -> int:
        """カテゴリを削除する

        Args:
            category_id (str): カテゴリID

        Returns:
            int: 削除したタスク数
        """
        if len(self.data.categories) <= 1:
            raise ValueError(msg.ERR_CATEGORY_MIN_REQUIRED)

        removed_count = 0

        def mutator(board: BoardData) -> None:
            nonlocal removed_count
            before_count = len(board.tasks)
            board.categories = [x for x in board.categories if x.id != category_id]
            board.tasks = [x for x in board.tasks if x.category_id != category_id]
            removed_count = before_count - len(board.tasks)

        self._run_mutation(msg.MUTATION_DELETE_CATEGORY, mutator, undoable=False)
        return removed_count

    def add_label(self, name: str, color: str) -> None:
        """ラベルを追加する

        Args:
            name (str): ラベル名
            color (str): ラベルカラー
        """
        label_name = name.strip()
        if not label_name:
            raise ValueError(msg.ERR_LABEL_NAME_REQUIRED)
        next_order = max([x.sort_order for x in self.data.labels], default=0) + 1
        label = Label(
            id=generate_id(Prefix.LABEL), name=label_name, color=color, sort_order=next_order
        )
        self._run_mutation(
            msg.MUTATION_ADD_LABEL,
            lambda board: board.labels.append(label),
            undoable=False,
        )

    def update_label(self, label_id: str, name: str, color: str, sort_order: int) -> None:
        """ラベルを更新する

        Args:
            label_id (str): ラベルID
            name (str): ラベル名
            color (str): ラベルカラー
            sort_order (int): ソート順序
        """
        if not name.strip():
            raise ValueError(msg.ERR_LABEL_NAME_REQUIRED)

        def mutator(board: BoardData) -> None:
            target = next((x for x in board.labels if x.id == label_id), None)
            if not target:
                raise ValueError(msg.ERR_LABEL_NOT_FOUND)
            target.name = name.strip()
            target.color = color
            target.sort_order = max(1, sort_order)

        self._run_mutation(msg.MUTATION_UPDATE_LABEL, mutator, undoable=False)

    def delete_label(self, label_id: str) -> None:
        """ラベルを削除する

        Args:
            label_id (str): ラベルID
        """

        def mutator(board: BoardData) -> None:
            board.labels = [x for x in board.labels if x.id != label_id]
            for task in board.tasks:
                task.label_ids = [x for x in task.label_ids if x != label_id]
                task.updated_at = now_iso()

        self._run_mutation(msg.MUTATION_DELETE_LABEL, mutator, undoable=False)

    def add_status(self, name: str, color: str) -> None:
        """ステータスを追加する

        Args:
            name (str): ステータス名
            color (str): ステータスカラー
        """
        status_name = name.strip()
        if not status_name:
            raise ValueError(msg.ERR_STATUS_NAME_REQUIRED)
        next_order = max([x.sort_order for x in self.data.statuses], default=0) + 1
        status = Status(
            id=generate_id(Prefix.STATUS),
            name=status_name,
            color=color,
            sort_order=next_order,
            is_system=False,
            hides_from_board=False,
        )
        self._run_mutation(
            msg.MUTATION_ADD_STATUS,
            lambda board: board.statuses.append(status),
            undoable=False,
        )

    def update_status(self, status_id: str, name: str, color: str, sort_order: int) -> None:
        """ステータスを更新する

        Args:
            status_id (str): ステータスID
            name (str): ステータス名
            color (str): ステータスカラー
            sort_order (int): ソート順序
        """
        if not name.strip():
            raise ValueError(msg.ERR_STATUS_NAME_REQUIRED)

        def mutator(board: BoardData) -> None:
            target = next((x for x in board.statuses if x.id == status_id), None)
            if not target:
                raise ValueError(msg.ERR_STATUS_NOT_FOUND)
            target.name = name.strip()
            target.color = color
            target.sort_order = max(1, sort_order)

        self._run_mutation(msg.MUTATION_UPDATE_STATUS, mutator, undoable=False)

    def delete_status(self, status_id: str, replacement_status_id: str | None) -> None:
        """ステータスを削除する

        Args:
            status_id (str): ステータスID
            replacement_status_id (str | None): 移動先のステータスID
        """
        self._validate_delete_status(status_id, replacement_status_id)

        def mutator(board: BoardData) -> None:
            if replacement_status_id:
                self._migrate_tasks_to_new_status(board, status_id, replacement_status_id)
            board.statuses = [x for x in board.statuses if x.id != status_id]

        self._run_mutation(msg.MUTATION_DELETE_STATUS, mutator, undoable=False)

    def _validate_delete_status(self, status_id: str, replacement_status_id: str | None) -> None:
        """ステータス削除のバリデーション

        Args:
            status_id (str): ステータスID
            replacement_status_id (str | None): 移動先のステータスID
        """
        target = self.get_status(status_id)
        if not target:
            raise ValueError(msg.ERR_STATUS_NOT_FOUND)
        if target.is_system:
            raise ValueError(msg.ERR_SYSTEM_STATUS_DELETE)

        used_count = len([x for x in self.data.tasks if x.status_id == status_id])
        if used_count > 0 and not replacement_status_id:
            raise ValueError(msg.ERR_REPLACEMENT_STATUS_REQUIRED)
        if replacement_status_id == status_id:
            raise ValueError(msg.ERR_SAME_REPLACEMENT_STATUS)

    def _migrate_tasks_to_new_status(
        self, board: BoardData, old_status_id: str, new_status_id: str
    ) -> None:
        """タスクを指定した新しいステータスに移行する

        Args:
            board (BoardData): ボードデータ
            old_status_id (str): 移動元のステータスID
            new_status_id (str): 移動先のステータスID
        """
        replacement = next((x for x in board.statuses if x.id == new_status_id), None)
        if not replacement:
            raise ValueError(msg.ERR_REPLACEMENT_STATUS_NOT_FOUND)

        now = now_iso()
        for task in board.tasks:
            if task.status_id == old_status_id:
                task.status_id = new_status_id
                task.updated_at = now
                if replacement.hides_from_board:
                    if not task.completed_at:
                        task.completed_at = now
                else:
                    task.completed_at = None

    def add_task(
        self,
        *,
        title: str,
        due_date: str | None,
        category_id: str,
        label_ids: list[str],
        color: str | None,
        detail: str,
        status_id: str,
    ) -> str:
        """タスクを追加する

        Args:
            title (str): タスク名
            due_date (str | None): 期限
            category_id (str): カテゴリID
            label_ids (list[str]): ラベルIDリスト
            color (str | None): タスクカラー
            detail (str): タスク詳細
            status_id (str): ステータスID

        Returns:
            str: タスクID
        """
        task_id = generate_id(Prefix.TASK)
        task_title = title.strip()
        if not task_title:
            raise ValueError(msg.ERR_TASK_NAME_REQUIRED)

        def mutator(board: BoardData) -> None:
            category_ids = {x.id for x in board.categories}
            status_ids = {x.id for x in board.statuses}
            target_category = category_id if category_id in category_ids else board.categories[0].id
            target_status = status_id if status_id in status_ids else NOT_STARTED_STATUS_ID
            next_order = self._next_task_sort_order(board, target_category)
            now = now_iso()
            status = next((x for x in board.statuses if x.id == target_status), None)
            completed_at = now if status and status.hides_from_board else None

            board.tasks.append(
                Task(
                    id=task_id,
                    title=task_title,
                    due_date=due_date,
                    category_id=target_category,
                    label_ids=list(label_ids),
                    color=color,
                    detail=detail,
                    sort_order=next_order,
                    status_id=target_status,
                    completed_at=completed_at,
                    created_at=now,
                    updated_at=now,
                )
            )

        self._run_mutation(msg.MUTATION_ADD_TASK, mutator, undoable=True)
        return task_id

    def update_task(
        self,
        task_id: str,
        *,
        title: str,
        due_date: str | None,
        category_id: str,
        label_ids: list[str],
        color: str | None,
        detail: str,
        status_id: str,
    ) -> None:
        """タスクを更新する

        Args:
            task_id (str): タスクID
            title (str): タスク名
            due_date (str | None): 期限
            category_id (str): カテゴリID
            label_ids (list[str]): ラベルIDリスト
            color (str | None): タスクカラー
            detail (str): タスク詳細
            status_id (str): ステータスID
        """
        task_title = title.strip()
        if not task_title:
            raise ValueError(msg.ERR_TASK_NAME_REQUIRED)

        def mutator(board: BoardData) -> None:
            task = next((x for x in board.tasks if x.id == task_id), None)
            if not task:
                raise ValueError(msg.ERR_TASK_NOT_FOUND)

            category_ids = {x.id for x in board.categories}
            status_map = {x.id: x for x in board.statuses}
            target_category = category_id if category_id in category_ids else task.category_id
            target_status = status_id if status_id in status_map else NOT_STARTED_STATUS_ID

            old_status = status_map.get(task.status_id)
            new_status = status_map.get(target_status)

            if task.category_id != target_category:
                task.category_id = target_category
                task.sort_order = self._next_task_sort_order(board, target_category)

            task.title = task_title
            task.due_date = due_date
            task.label_ids = list(label_ids)
            task.color = color
            task.detail = detail
            task.status_id = target_status
            task.updated_at = now_iso()

            if new_status and new_status.hides_from_board:
                if not old_status or not old_status.hides_from_board:
                    task.completed_at = now_iso()
            else:
                task.completed_at = None

        self._run_mutation(msg.MUTATION_UPDATE_TASK, mutator, undoable=True)

    def delete_task(self, task_id: str) -> None:
        """タスクを削除する

        Args:
            task_id (str): タスクID
        """

        def mutator(board: BoardData) -> None:
            before_count = len(board.tasks)
            board.tasks = [x for x in board.tasks if x.id != task_id]
            if len(board.tasks) == before_count:
                raise ValueError(msg.ERR_TASK_NOT_FOUND)

        self._run_mutation(msg.MUTATION_DELETE_TASK, mutator, undoable=True)

    def duplicate_task(self, task_id: str) -> str:
        """タスクを複製する

        Args:
            task_id (str): タスクID
        Returns:
            str: 新規タスクID
        """
        new_task_id = generate_id(Prefix.TASK)

        def mutator(board: BoardData) -> None:
            source = next((x for x in board.tasks if x.id == task_id), None)
            if not source:
                raise ValueError(msg.ERR_TASK_NOT_FOUND)
            now = now_iso()
            status_map = {x.id: x for x in board.statuses}
            status = status_map.get(source.status_id)
            board.tasks.append(
                Task(
                    id=new_task_id,
                    title=source.title,
                    due_date=source.due_date,
                    category_id=source.category_id,
                    label_ids=list(source.label_ids),
                    color=source.color,
                    detail=source.detail,
                    sort_order=self._next_task_sort_order(board, source.category_id),
                    status_id=source.status_id,
                    completed_at=now if status and status.hides_from_board else None,
                    created_at=now,
                    updated_at=now,
                )
            )

        self._run_mutation(msg.MUTATION_DUPLICATE_TASK, mutator, undoable=True)
        return new_task_id

    def restore_completed_task(self, task_id: str) -> None:
        """完了したタスクを未完了に戻す

        Args:
            task_id (str): タスクID
        """

        def mutator(board: BoardData) -> None:
            task = next((x for x in board.tasks if x.id == task_id), None)
            if not task:
                raise ValueError(msg.ERR_TASK_NOT_FOUND)
            task.status_id = NOT_STARTED_STATUS_ID
            task.completed_at = None
            task.updated_at = now_iso()

        self._run_mutation(msg.MUTATION_RESTORE_TASK, mutator, undoable=True)

    def apply_board_layout(self, layout_by_category: dict[str, list[str]]) -> None:
        """ボードレイアウトを適用する

        Args:
            layout_by_category (dict[str, list[str]]): カテゴリIDごとのタスクIDリスト
        """

        def mutator(board: BoardData) -> None:
            status_map = {x.id: x for x in board.statuses}
            visible_tasks = [
                x
                for x in board.tasks
                if not (status_map.get(x.status_id) and status_map[x.status_id].hides_from_board)
            ]
            visible_task_ids = {x.id for x in visible_tasks}
            assigned_ids: set[str] = set()

            existing_by_category: dict[str, list[str]] = defaultdict(list)
            for task in sorted(
                visible_tasks, key=lambda x: (x.category_id, x.sort_order, x.updated_at)
            ):
                existing_by_category[task.category_id].append(task.id)

            for category in sorted(board.categories, key=lambda x: (x.sort_order, x.name)):
                requested = [
                    task_id
                    for task_id in layout_by_category.get(category.id, [])
                    if task_id in visible_task_ids and task_id not in assigned_ids
                ]
                assigned_ids.update(requested)
                fallback = [
                    x for x in existing_by_category.get(category.id, []) if x not in assigned_ids
                ]
                final_ids = requested + fallback
                for index, task_id in enumerate(final_ids, start=1):
                    task = next((x for x in board.tasks if x.id == task_id), None)
                    if not task:
                        continue
                    task.category_id = category.id
                    task.sort_order = index
                    task.updated_at = now_iso()

        self._run_mutation(msg.MUTATION_REORDER_TASKS, mutator, undoable=True)

    def undo(self) -> bool:
        """アンドゥ

        Returns:
            bool: 成功したかどうか
        """
        executed = self.command_manager.undo(self._apply_snapshot)
        if executed:
            self.undo_redo_changed.emit()
        return executed

    def redo(self) -> bool:
        """リドゥ

        Returns:
            bool: 成功したかどうか
        """
        executed = self.command_manager.redo(self._apply_snapshot)
        if executed:
            self.undo_redo_changed.emit()
        return executed

    @property
    def can_undo(self) -> bool:
        return self.command_manager.can_undo

    @property
    def can_redo(self) -> bool:
        return self.command_manager.can_redo

    @property
    def undo_text(self) -> str:
        return self.command_manager.undo_text

    @property
    def redo_text(self) -> str:
        return self.command_manager.redo_text

    def _run_mutation(
        self,
        description: str,
        mutator: Callable[[BoardData], None],
        *,
        undoable: bool,
    ) -> bool:
        """Mutation を実行する

        Args:
            description (str): 操作の説明
            mutator (Callable[[BoardData], None]): 操作内容
            undoable (bool): アンドゥ可能かどうか
        Returns:
            bool: 成功したかどうか
        """
        before = self.data.clone()
        after = self.data.clone()
        mutator(after)
        self._normalize_inplace(after)
        if before.to_dict() == after.to_dict():
            return False

        if undoable:
            command = SnapshotCommand(description=description, before=before, after=after)
            self.command_manager.execute(command, self._apply_snapshot)
            self.undo_redo_changed.emit()
        else:
            self._apply_snapshot(after)
        return True

    def _apply_snapshot(self, board: BoardData) -> None:
        """Boardを適用する

        Args:
            board (BoardData): boardデータ
        """
        candidate = board.clone()
        self._normalize_inplace(candidate)
        self.storage.save(candidate)
        self.data = candidate
        self.changed.emit()

    def _normalize_inplace(self, board: BoardData) -> None:
        """Board をインプレースで正規化する

        Args:
            board (BoardData): boardデータ
        """
        board.version = 1
        board.categories = self._dedupe(board.categories)
        board.labels = self._dedupe(board.labels)
        board.statuses = self._dedupe(board.statuses)
        board.tasks = self._dedupe(board.tasks)

        self._normalize_categories_and_labels(board)
        status_map = self._normalize_statuses(board)
        self._normalize_tasks(board, status_map)

        board.sort_all()

    def _normalize_categories_and_labels(self, board: BoardData) -> None:
        """カテゴリとラベルを正規化する

        Args:
            board (BoardData): boardデータ
        """
        if not board.categories:
            board.categories = default_categories()

        board.categories.sort(key=lambda x: (x.sort_order, x.name))
        board.labels.sort(key=lambda x: (x.sort_order, x.name))

        for index, category in enumerate(board.categories, start=1):
            category.sort_order = index
        for index, label in enumerate(board.labels, start=1):
            label.sort_order = index

    def _normalize_statuses(self, board: BoardData) -> dict[str, Status]:
        """ステータスを正規化する

        Args:
            board (BoardData): boardデータ
        Returns:
            dict[str, Status]: ステータスマップ
        """
        fixed_defaults = {x.id: x for x in default_statuses()}
        for status_id in [NOT_STARTED_STATUS_ID, COMPLETED_STATUS_ID]:
            if not any(x.id == status_id for x in board.statuses):
                board.statuses.append(fixed_defaults[status_id])

        _repair_broken_status(board, fixed_defaults)
        board.statuses.sort(key=lambda x: (x.sort_order, x.name))

        return {x.id: x for x in board.statuses}

    def _normalize_tasks(self, board: BoardData, status_map: dict[str, Status]) -> None:
        """タスクを正規化する

        Args:
            board (BoardData): boardデータ
            status_map (dict[str, Status]): ステータスマップ
        """
        category_ids = {x.id for x in board.categories}
        label_ids = {x.id for x in board.labels}
        first_category_id = board.categories[0].id

        _repair_broken_task(board, category_ids, first_category_id, status_map, label_ids)

        by_category: dict[str, list[Task]] = defaultdict(list)
        for task in board.tasks:
            by_category[task.category_id].append(task)

        for tasks in by_category.values():
            tasks.sort(key=lambda x: (x.sort_order, x.updated_at))
            for index, task in enumerate(tasks, start=1):
                task.sort_order = index

    @staticmethod
    def _dedupe(items: list[T]) -> list[T]:
        """重複を削除する

        Args:
            items (list): 重複削除対象のリスト

        Returns:
            list: 重複削除後のリスト
        """
        seen: set[str] = set()
        result = []
        for item in items:
            item_id = getattr(item, "id", None)
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)
            result.append(item)
        return result

    @staticmethod
    def _next_task_sort_order(board: BoardData, category_id: str) -> int:
        """次のタスクソート順序を取得する

        Args:
            board (BoardData): boardデータ
            category_id (str): カテゴリID

        Returns:
            int: 次のタスクソート順序
        """
        sort_orders = [x.sort_order for x in board.tasks if x.category_id == category_id]
        return max(sort_orders, default=0) + 1
