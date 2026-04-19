from __future__ import annotations

import atexit
import faulthandler
import gc
import sys
import threading
import traceback
from pathlib import Path
from types import TracebackType

from PyQt6.QtCore import QtMsgType, qInstallMessageHandler
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
from utils.debug_trace import trace_debug


def build_controller(data_file_path: Path) -> AppController:
    """`controller` を構築する

    Args:
        data_file_path (Path): `data_file_path` を指定する

    Returns:
        AppController: 処理結果を返す
    """
    trace_debug(f"build_controller:start path={data_file_path}")
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
    trace_debug("build_controller:done")
    return controller


_FAULT_LOG_STREAM = None


def _format_exception(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> str:
    """例外情報を文字列化する。"""
    return "".join(traceback.format_exception(exc_type, exc, tb)).strip()


def _install_debug_hooks(app: QApplication) -> None:
    """一時的な終了原因調査用フックを設定する。"""
    global _FAULT_LOG_STREAM

    trace_debug("debug_hooks:install:start")

    app.aboutToQuit.connect(lambda: trace_debug("app_signal:aboutToQuit"))
    app.lastWindowClosed.connect(lambda: trace_debug("app_signal:lastWindowClosed"))
    app.applicationStateChanged.connect(
        lambda state: trace_debug(f"app_signal:applicationStateChanged state={state.name}")
    )
    app.focusWindowChanged.connect(
        lambda window: trace_debug(
            "app_signal:focusWindowChanged "
            f"window={type(window).__name__ if window is not None else 'None'}"
        )
    )

    def on_exit() -> None:
        trace_debug("python_hook:atexit")

    atexit.register(on_exit)

    def on_excepthook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        trace_debug(f"python_hook:sys.excepthook\n{_format_exception(exc_type, exc, tb)}")
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = on_excepthook

    def on_thread_excepthook(args: threading.ExceptHookArgs) -> None:
        trace_debug(
            "python_hook:threading.excepthook\n"
            f"{_format_exception(args.exc_type, args.exc_value, args.exc_traceback)}"
        )
        threading.__excepthook__(args)

    threading.excepthook = on_thread_excepthook

    def on_qt_message(msg_type: QtMsgType, _context, message: str) -> None:
        trace_debug(f"qt_message:{msg_type.name}:{message}")

    qInstallMessageHandler(on_qt_message)

    fault_log_path = Path.cwd() / "debug_fault.log"
    _FAULT_LOG_STREAM = fault_log_path.open("a", encoding="utf-8")
    faulthandler.enable(file=_FAULT_LOG_STREAM, all_threads=True)
    trace_debug(f"debug_hooks:install:done fault_log={fault_log_path}")


def main() -> int:
    """アプリケーションのエントリーポイントを実行する

    Returns:
        int: 処理結果を返す
    """
    trace_debug("main:start")
    gc.disable()
    trace_debug(f"main:gc_disabled isenabled={gc.isenabled()}")
    app = QApplication(sys.argv)
    _install_debug_hooks(app)
    trace_debug(f"main:QApplication created quitOnLastWindowClosed={app.quitOnLastWindowClosed()}")
    app_font = app.font()
    if app_font.pointSize() <= 0:
        app_font.setPointSize(9)
        app.setFont(app_font)
        trace_debug("main:default font size adjusted to 9")
    app.setWindowIcon(QIcon())
    data_file_path = Path.cwd() / "task_board.json"
    trace_debug(f"main:data_file_path={data_file_path}")
    controller = build_controller(data_file_path)
    window = MainWindow(controller)
    trace_debug("main:MainWindow created")
    window.show()
    trace_debug("main:MainWindow shown")
    result = app.exec()
    trace_debug(f"main:app.exec returned result={result}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
