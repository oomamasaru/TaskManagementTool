from __future__ import annotations

import json
from pathlib import Path

from domain.models.app_settings import AppSettings
from domain.models.board_data import BoardData
from domain.models.category import Category
from domain.models.status import Status
from infrastructure.fileio.atomic_file_writer import AtomicFileWriter
from infrastructure.fileio.backup_manager import BackupManager
from infrastructure.repositories.board_repository import BoardRepository
from infrastructure.serializers.board_serializer import BoardSerializer


class JsonBoardRepository(BoardRepository):
    def __init__(
        self,
        path: str | Path,
        serializer: BoardSerializer | None = None,
        writer: AtomicFileWriter | None = None,
        backup_manager: BackupManager | None = None,
    ) -> None:
        self._path = Path(path)
        self._serializer = serializer or BoardSerializer()
        self._writer = writer or AtomicFileWriter()
        self._backup_manager = backup_manager or BackupManager()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> BoardData:
        if not self._path.exists():
            return self._create_and_persist_default_board()

        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            board = self._serializer.from_dict(payload)
            return self._prepare_loaded_board(board)
        except Exception:
            backup = self._path.with_suffix(f"{self._path.suffix}.bak")
            if backup.exists():
                payload = json.loads(backup.read_text(encoding="utf-8"))
                board = self._serializer.from_dict(payload)
                return self._prepare_loaded_board(board)
            return self._create_and_persist_default_board()

    def save(self, data: BoardData) -> None:
        data.settings.data_file_path = str(self._path)
        self._backup_manager.create_backup(self._path)
        payload = self._serializer.to_dict(data)
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        self._writer.write(self._path, content)

    def _ensure_required_statuses(self, board: BoardData) -> None:
        status_ids = {status.id for status in board.statuses}
        if "not_started" not in status_ids:
            board.statuses.append(
                Status(
                    id="not_started",
                    name="未着手",
                    color="#6B7280",
                    sort_order=1,
                    is_system=True,
                    hides_from_board=False,
                )
            )
        if "completed" not in status_ids:
            board.statuses.append(
                Status(
                    id="completed",
                    name="完了",
                    color="#059669",
                    sort_order=999,
                    is_system=True,
                    hides_from_board=True,
                )
            )
        board.statuses.sort(key=lambda status: status.sort_order)

    def _ensure_category(self, board: BoardData) -> None:
        if board.categories:
            return
        board.categories.append(Category(id="cat_a", name="A", sort_order=1))

    def _prepare_loaded_board(self, board: BoardData) -> BoardData:
        board.settings.data_file_path = str(self._path)
        self._ensure_required_statuses(board)
        self._ensure_category(board)
        return board

    def _create_and_persist_default_board(self) -> BoardData:
        board = default_board_data()
        board.settings.data_file_path = str(self._path)
        self.save(board)
        return board


def default_board_data() -> BoardData:
    return BoardData(
        version=1,
        categories=[
            Category(id="cat_a", name="A", sort_order=1),
            Category(id="cat_b", name="B", sort_order=2),
        ],
        statuses=[
            Status(
                id="not_started",
                name="未着手",
                color="#6B7280",
                sort_order=1,
                is_system=True,
                hides_from_board=False,
            ),
            Status(
                id="in_progress",
                name="作業中",
                color="#2563EB",
                sort_order=2,
                is_system=False,
                hides_from_board=False,
            ),
            Status(
                id="completed",
                name="完了",
                color="#059669",
                sort_order=999,
                is_system=True,
                hides_from_board=True,
            ),
        ],
        settings=AppSettings(),
    )
