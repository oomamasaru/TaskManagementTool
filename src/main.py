from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app.app_controller import AppController
from app.board_store import BoardStore
from app.services.category_service import CategoryService
from app.services.completed_task_service import CompletedTaskService
from app.services.filter_service import FilterService
from app.services.label_service import LabelService
from app.services.status_service import StatusService
from app.services.task_service import TaskService
from infrastructure.providers.datetime_provider import DateTimeProvider
from infrastructure.providers.id_provider import IdProvider
from infrastructure.repositories.json_board_repository import JsonBoardRepository
from ui.main_window import MainWindow


def build_controller(data_file_path: Path) -> AppController:
    store = BoardStore()
    repository = JsonBoardRepository(path=data_file_path)
    datetime_provider = DateTimeProvider()
    id_provider = IdProvider()

    task_service = TaskService(store, datetime_provider, id_provider)
    category_service = CategoryService(store, id_provider)
    label_service = LabelService(store, id_provider)
    status_service = StatusService(store, id_provider, datetime_provider)
    completed_task_service = CompletedTaskService(store, datetime_provider)
    filter_service = FilterService()

    controller = AppController(
        store=store,
        repository=repository,
        task_service=task_service,
        category_service=category_service,
        label_service=label_service,
        status_service=status_service,
        completed_task_service=completed_task_service,
        filter_service=filter_service,
    )
    controller.initialize()
    return controller


def main() -> int:
    app = QApplication(sys.argv)
    app_font = app.font()
    if app_font.pointSize() <= 0:
        app_font.setPointSize(9)
        app.setFont(app_font)
    app.setWindowIcon(QIcon())
    data_file_path = Path.cwd() / "task_board.json"
    controller = build_controller(data_file_path)
    window = MainWindow(controller)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
