from __future__ import annotations

from PyQt6.QtGui import QUndoCommand

from app.board_store import BoardStore
from infrastructure.repositories.json_board_repository import JsonBoardRepository


class BaseCommand(QUndoCommand):
    def __init__(
        self,
        text: str,
        store: BoardStore,
        repository: JsonBoardRepository,
    ) -> None:
        super().__init__(text)
        self._store = store
        self._repository = repository

    def _save_board(self) -> None:
        self._repository.save(self._store.board_data)
        self._store.notify_board_changed()

