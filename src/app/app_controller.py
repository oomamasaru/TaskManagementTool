from __future__ import annotations

from app.board_store import BoardStore
from app.dto import TaskInputData
from app.services.category_service import CategoryService
from app.services.completed_task_service import CompletedTaskService
from app.services.filter_service import FilterService
from app.services.label_service import LabelService
from app.services.status_service import StatusService
from app.services.task_service import TaskService
from commands.add_task_command import AddTaskCommand
from commands.change_task_status_command import ChangeTaskStatusCommand
from commands.delete_task_command import DeleteTaskCommand
from commands.duplicate_task_command import DuplicateTaskCommand
from commands.edit_task_command import EditTaskCommand
from commands.move_task_command import MoveTaskCommand
from domain.models.filter_condition import FilterCondition
from infrastructure.repositories.json_board_repository import JsonBoardRepository


class AppController:
    def __init__(
        self,
        store: BoardStore,
        repository: JsonBoardRepository,
        task_service: TaskService,
        category_service: CategoryService,
        label_service: LabelService,
        status_service: StatusService,
        completed_task_service: CompletedTaskService,
        filter_service: FilterService,
    ) -> None:
        self._store = store
        self._repository = repository
        self._task_service = task_service
        self._category_service = category_service
        self._label_service = label_service
        self._status_service = status_service
        self._completed_task_service = completed_task_service
        self._filter_service = filter_service

    def initialize(self) -> None:
        board_data = self._repository.load()
        self._store.load(board_data)

    def add_task(self, input_data: TaskInputData) -> None:
        command = AddTaskCommand(self._store, self._repository, self._task_service, input_data)
        self._store.undo_stack.push(command)

    def edit_task(self, task_id: str, input_data: TaskInputData) -> None:
        command = EditTaskCommand(
            self._store,
            self._repository,
            self._task_service,
            task_id,
            input_data,
        )
        self._store.undo_stack.push(command)

    def delete_task(self, task_id: str) -> None:
        command = DeleteTaskCommand(self._store, self._repository, self._task_service, task_id)
        self._store.undo_stack.push(command)

    def duplicate_task(self, task_id: str) -> None:
        command = DuplicateTaskCommand(self._store, self._repository, self._task_service, task_id)
        self._store.undo_stack.push(command)

    def move_task(self, task_id: str, category_id: str, order: int) -> None:
        before = self._store.task_ids_by_category(include_hidden=True)
        self._task_service.move_task(task_id, category_id, order)
        after = self._store.task_ids_by_category(include_hidden=True)
        self._task_service.apply_order_snapshot(before)
        command = MoveTaskCommand(self._store, self._repository, self._task_service, task_id, after)
        self._store.undo_stack.push(command)

    def move_task_by_snapshot(self, task_id: str, snapshot: dict[str, list[str]]) -> None:
        command = MoveTaskCommand(
            self._store,
            self._repository,
            self._task_service,
            task_id,
            snapshot,
        )
        self._store.undo_stack.push(command)

    def change_task_status(self, task_id: str, status_id: str) -> None:
        command = ChangeTaskStatusCommand(
            self._store,
            self._repository,
            self._status_service,
            task_id,
            status_id,
        )
        self._store.undo_stack.push(command)

    def restore_task(self, task_id: str) -> None:
        self.change_task_status(task_id, StatusService.NOT_STARTED_ID)

    def save(self) -> None:
        self._repository.save(self._store.board_data)
        self._store.notify_board_changed()

    def undo(self) -> None:
        self._store.undo_stack.undo()

    def redo(self) -> None:
        self._store.undo_stack.redo()

    def add_category(self, name: str) -> None:
        self._category_service.add_category(name)
        self.save()

    def update_category(self, category_id: str, name: str) -> None:
        self._category_service.update_category(category_id, name)
        self.save()

    def delete_category(self, category_id: str) -> None:
        self._category_service.delete_category(category_id)
        self.save()

    def add_label(self, name: str, color: str) -> None:
        self._label_service.add_label(name, color)
        self.save()

    def update_label(self, label_id: str, name: str, color: str) -> None:
        self._label_service.update_label(label_id, name, color)
        self.save()

    def delete_label(self, label_id: str) -> None:
        self._label_service.delete_label(label_id)
        self.save()

    def add_status(self, name: str, color: str, hides_from_board: bool = False) -> None:
        self._status_service.add_status(name, color, hides_from_board)
        self.save()

    def update_status(
        self,
        status_id: str,
        name: str,
        color: str,
        hides_from_board: bool,
    ) -> None:
        self._status_service.update_status(status_id, name, color, hides_from_board)
        self.save()

    def delete_status(self, status_id: str, replacement_status_id: str) -> None:
        self._status_service.delete_status(status_id, replacement_status_id)
        self.save()

    def reorder_statuses(self, ordered_status_ids: list[str]) -> None:
        self._status_service.reorder_statuses(ordered_status_ids)
        self.save()

    def get_completed_tasks(self):
        return self._completed_task_service.get_completed_tasks()

    def restore_completed_task(self, task_id: str) -> None:
        self._completed_task_service.restore_task(task_id)
        self.save()

    def delete_completed_task(self, task_id: str) -> None:
        self._completed_task_service.delete_completed_task(task_id)
        self.save()

    def set_filter(
        self,
        search_text: str,
        active_label_ids: set[str],
        include_no_label: bool,
    ) -> None:
        condition = FilterCondition(
            search_text=search_text,
            active_label_ids=active_label_ids,
            include_no_label=include_no_label,
        )
        self._store.set_filter(condition)

    def clear_filter(self) -> None:
        self._store.set_filter(FilterCondition())

    @property
    def store(self) -> BoardStore:
        return self._store
