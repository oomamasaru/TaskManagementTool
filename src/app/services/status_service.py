from __future__ import annotations

from app.board_store import BoardStore
from domain.models.status import Status
from infrastructure.providers.datetime_provider import DateTimeProvider
from infrastructure.providers.id_provider import IdProvider
from utils.color_utils import normalize_hex_color


class StatusService:
    NOT_STARTED_ID = "not_started"
    COMPLETED_ID = "completed"

    def __init__(
        self,
        store: BoardStore,
        id_provider: IdProvider,
        datetime_provider: DateTimeProvider,
    ) -> None:
        self._store = store
        self._id_provider = id_provider
        self._datetime_provider = datetime_provider

    def add_status(self, name: str, color: str, hides_from_board: bool = False) -> Status:
        status_name = name.strip()
        if not status_name:
            raise ValueError("Status name is required.")
        if any(
            current.name.lower() == status_name.lower()
            for current in self._store.board_data.statuses
        ):
            raise ValueError("Status name already exists.")

        status = self._build_status(
            id_=self._id_provider.new_id("status"),
            name=status_name,
            color=normalize_hex_color(color),
            sort_order=self._next_sort_order(),
            is_system=False,
            hides_from_board=hides_from_board,
        )
        self._store.board_data.statuses.append(status)
        self._normalize_status_order()
        return status

    def update_status(
        self,
        status_id: str,
        name: str,
        color: str,
        hides_from_board: bool,
        sort_order: int | None = None,
    ) -> Status:
        status = self._get_status(status_id)
        if status.id in {self.NOT_STARTED_ID, self.COMPLETED_ID}:
            raise ValueError("The 'not_started' and 'completed' statuses are immutable.")

        status_name = name.strip()
        if not status_name:
            raise ValueError("Status name is required.")
        if any(
            current.id != status_id and current.name.lower() == status_name.lower()
            for current in self._store.board_data.statuses
        ):
            raise ValueError("Status name already exists.")

        status.name = status_name
        status.color = normalize_hex_color(color)
        if not status.is_system:
            status.hides_from_board = hides_from_board
        if sort_order is not None:
            status.sort_order = max(1, sort_order)
        self._normalize_status_order()
        return status

    def delete_status(self, status_id: str, replacement_status_id: str) -> None:
        status = self._get_status(status_id)
        if status.is_system:
            raise ValueError("System status cannot be deleted.")
        replacement = self._get_status(replacement_status_id)
        if status.id == replacement.id:
            raise ValueError("Replacement status must be different.")

        for task in self._store.board_data.tasks:
            if task.status_id != status.id:
                continue
            task.status_id = replacement.id
            if replacement.hides_from_board:
                task.completed_at = self._datetime_provider.now()
            else:
                task.completed_at = None
            task.updated_at = self._datetime_provider.now()

        self._store.board_data.statuses = [
            current for current in self._store.board_data.statuses if current.id != status.id
        ]
        self._normalize_status_order()

    def reorder_statuses(self, ordered_status_ids: list[str]) -> None:
        status_map = {status.id: status for status in self._store.board_data.statuses}
        ordered: list[Status] = []
        seen: set[str] = set()

        for status_id in ordered_status_ids:
            status = status_map.get(status_id)
            if status is None or status_id in seen:
                continue
            ordered.append(status)
            seen.add(status_id)

        for status in sorted(self._store.board_data.statuses, key=lambda item: item.sort_order):
            if status.id in seen:
                continue
            ordered.append(status)
            seen.add(status.id)

        for index, status in enumerate(ordered, start=1):
            status.sort_order = index

        self._store.board_data.statuses = ordered
        self._normalize_status_order()

    def mark_completed(self, task_id: str):
        return self.change_status(task_id, self.COMPLETED_ID)

    def restore_to_not_started(self, task_id: str):
        return self.change_status(task_id, self.NOT_STARTED_ID)

    def change_status(self, task_id: str, status_id: str):
        status = self._get_status(status_id)
        task = self._get_task(task_id)
        now = self._datetime_provider.now()
        task.status_id = status.id
        task.completed_at = now if status.hides_from_board else None
        task.updated_at = now
        return task

    def set_task_status_exact(self, task_id: str, status_id: str, completed_at) -> None:
        self._get_status(status_id)
        task = self._get_task(task_id)
        task.status_id = status_id
        task.completed_at = completed_at
        task.updated_at = self._datetime_provider.now()

    def _get_status(self, status_id: str):
        status = self._store.find_status(status_id)
        if status is None:
            raise ValueError("Status not found.")
        return status

    def _get_task(self, task_id: str):
        task = self._store.find_task(task_id)
        if task is None:
            raise ValueError("Task not found.")
        return task

    def _next_sort_order(self) -> int:
        if not self._store.board_data.statuses:
            return 1
        return max(status.sort_order for status in self._store.board_data.statuses) + 1

    def _normalize_status_order(self) -> None:
        statuses = list(self._store.board_data.statuses)
        statuses.sort(key=lambda status: status.sort_order)

        not_started = next((s for s in statuses if s.id == self.NOT_STARTED_ID), None)
        completed = next((s for s in statuses if s.id == self.COMPLETED_ID), None)
        others = [
            status
            for status in statuses
            if status.id not in {self.NOT_STARTED_ID, self.COMPLETED_ID}
        ]

        ordered: list[Status] = []
        if not_started is not None:
            ordered.append(not_started)
        ordered.extend(others)
        if completed is not None:
            ordered.append(completed)

        for index, status in enumerate(ordered, start=1):
            if status.id == self.NOT_STARTED_ID:
                status.sort_order = 1
            elif status.id == self.COMPLETED_ID:
                status.sort_order = 999
            else:
                status.sort_order = index

        self._store.board_data.statuses = ordered

    def _build_status(
        self,
        id_: str,
        name: str,
        color: str,
        sort_order: int,
        is_system: bool,
        hides_from_board: bool,
    ) -> Status:
        return Status(
            id=id_,
            name=name,
            color=color,
            sort_order=sort_order,
            is_system=is_system,
            hides_from_board=hides_from_board,
        )
