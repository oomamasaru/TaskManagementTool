from __future__ import annotations

from datetime import datetime

from app.board_store import BoardStore
from app.dto import TaskInputData
from domain.models.task import Task
from infrastructure.providers.datetime_provider import DateTimeProvider
from infrastructure.providers.id_provider import IdProvider


class TaskService:
    def __init__(
        self, store: BoardStore, datetime_provider: DateTimeProvider, id_provider: IdProvider
    ) -> None:
        self._store = store
        self._datetime_provider = datetime_provider
        self._id_provider = id_provider

    def create_task(self, input_data: TaskInputData) -> Task:
        title = input_data.title.strip()
        if not title:
            raise ValueError("タスク名は必須です。")
        self._assert_category_exists(input_data.category_id)
        self._assert_status_exists(input_data.status_id)

        now = self._datetime_provider.now()
        task = Task(
            id=self._id_provider.new_id("task"),
            title=title,
            due_date=input_data.due_date,
            category_id=input_data.category_id,
            label_ids=[*input_data.label_ids],
            color=input_data.color,
            detail=input_data.detail,
            sort_order=self._next_sort_order(input_data.category_id),
            status_id=input_data.status_id,
            completed_at=self._completed_at_for_new_status(input_data.status_id, now),
            created_at=now,
            updated_at=now,
        )
        self._store.board_data.tasks.append(task)
        self._normalize_sort_orders(input_data.category_id)
        return task

    def update_task(self, task_id: str, input_data: TaskInputData) -> Task:
        title = input_data.title.strip()
        if not title:
            raise ValueError("タスク名は必須です。")
        task = self._get_task(task_id)
        self._assert_category_exists(input_data.category_id)
        self._assert_status_exists(input_data.status_id)

        now = self._datetime_provider.now()
        before_category_id = task.category_id
        task.title = title
        task.due_date = input_data.due_date
        task.category_id = input_data.category_id
        task.label_ids = [*input_data.label_ids]
        task.color = input_data.color
        task.detail = input_data.detail
        task.completed_at = self._updated_completed_at(
            task.status_id, input_data.status_id, task, now
        )
        task.status_id = input_data.status_id
        task.updated_at = now

        if before_category_id != task.category_id:
            task.sort_order = self._next_sort_order(task.category_id)
            self._normalize_sort_orders(before_category_id)
        self._normalize_sort_orders(task.category_id)
        return task

    def delete_task(self, task_id: str) -> None:
        task = self._get_task(task_id)
        category_id = task.category_id
        self._store.board_data.tasks = [
            each for each in self._store.board_data.tasks if each.id != task_id
        ]
        self._normalize_sort_orders(category_id)

    def duplicate_task(self, task_id: str) -> Task:
        source = self._get_task(task_id)
        now = self._datetime_provider.now()
        duplicated = Task(
            id=self._id_provider.new_id("task"),
            title=f"{source.title} (copy)",
            due_date=source.due_date,
            category_id=source.category_id,
            label_ids=[*source.label_ids],
            color=source.color,
            detail=source.detail,
            sort_order=self._next_sort_order(source.category_id),
            status_id=source.status_id,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        self._store.board_data.tasks.append(duplicated)
        self._normalize_sort_orders(source.category_id)
        return duplicated

    def move_task(self, task_id: str, category_id: str, order: int) -> None:
        task = self._get_task(task_id)
        self._assert_category_exists(category_id)
        source_category_id = task.category_id
        target_tasks = [
            each
            for each in self._store.board_data.tasks
            if each.category_id == category_id and each.id != task_id
        ]
        target_tasks.sort(key=lambda each: each.sort_order)
        index = max(0, min(len(target_tasks), order))
        target_tasks.insert(index, task)

        task.category_id = category_id
        for idx, each in enumerate(target_tasks, start=1):
            each.sort_order = idx

        if source_category_id != category_id:
            self._normalize_sort_orders(source_category_id)
        self._normalize_sort_orders(category_id)

    def change_status(self, task_id: str, status_id: str) -> Task:
        task = self._get_task(task_id)
        self._assert_status_exists(status_id)
        now = self._datetime_provider.now()
        task.completed_at = self._updated_completed_at(task.status_id, status_id, task, now)
        task.status_id = status_id
        task.updated_at = now
        return task

    def restore_task(self, task_id: str) -> Task:
        return self.change_status(task_id, "not_started")

    def insert_task(self, task: Task) -> None:
        if self._store.find_task(task.id) is not None:
            self.replace_task(task)
            return
        self._assert_category_exists(task.category_id)
        self._assert_status_exists(task.status_id)
        self._store.board_data.tasks.append(task.clone())
        self._normalize_sort_orders(task.category_id)

    def replace_task(self, task: Task) -> None:
        for index, current in enumerate(self._store.board_data.tasks):
            if current.id != task.id:
                continue
            previous_category_id = current.category_id
            self._store.board_data.tasks[index] = task.clone()
            if previous_category_id != task.category_id:
                self._normalize_sort_orders(previous_category_id)
            self._normalize_sort_orders(task.category_id)
            return
        msg = f"Task not found: {task.id}"
        raise ValueError(msg)

    def apply_order_snapshot(self, order_by_category: dict[str, list[str]]) -> None:
        task_map = {task.id: task for task in self._store.board_data.tasks}

        for category_id, task_ids in order_by_category.items():
            self._assert_category_exists(category_id)
            for position, task_id in enumerate(task_ids, start=1):
                task = task_map.get(task_id)
                if task is None:
                    continue
                task.category_id = category_id
                task.sort_order = position

        for category in self._store.get_categories():
            self._normalize_sort_orders(category.id)

    def get_task(self, task_id: str) -> Task:
        return self._get_task(task_id).clone()

    def _get_task(self, task_id: str) -> Task:
        task = self._store.find_task(task_id)
        if task is None:
            msg = f"Task not found: {task_id}"
            raise ValueError(msg)
        return task

    def _next_sort_order(self, category_id: str) -> int:
        tasks = [task for task in self._store.board_data.tasks if task.category_id == category_id]
        return max((task.sort_order for task in tasks), default=0) + 1

    def _normalize_sort_orders(self, category_id: str) -> None:
        tasks = sorted(
            (task for task in self._store.board_data.tasks if task.category_id == category_id),
            key=lambda task: task.sort_order,
        )
        for index, task in enumerate(tasks, start=1):
            task.sort_order = index

    def _assert_category_exists(self, category_id: str) -> None:
        if self._store.find_category(category_id) is not None:
            return
        msg = f"Category not found: {category_id}"
        raise ValueError(msg)

    def _assert_status_exists(self, status_id: str) -> None:
        if self._store.find_status(status_id) is not None:
            return
        msg = f"Status not found: {status_id}"
        raise ValueError(msg)

    def _completed_at_for_new_status(self, status_id: str, now: datetime) -> datetime | None:
        status = self._store.find_status(status_id)
        if status and status.hides_from_board:
            return now
        return None

    def _updated_completed_at(
        self,
        before_status_id: str,
        after_status_id: str,
        task: Task,
        now: datetime,
    ) -> datetime | None:
        before = self._store.find_status(before_status_id)
        after = self._store.find_status(after_status_id)
        before_completed = bool(before and before.hides_from_board)
        after_completed = bool(after and after.hides_from_board)

        if after_completed and not before_completed:
            return now
        if not after_completed:
            return None
        return task.completed_at
