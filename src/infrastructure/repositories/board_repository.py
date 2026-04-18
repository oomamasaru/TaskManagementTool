from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.board_data import BoardData


class BoardRepository(ABC):
    @abstractmethod
    def load(self) -> BoardData:
        raise NotImplementedError

    @abstractmethod
    def save(self, data: BoardData) -> None:
        raise NotImplementedError

