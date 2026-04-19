from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.board_data import BoardData


class BoardRepository(ABC):
    """ボードリポジトリ"""

    @abstractmethod
    def load(self) -> BoardData:
        """ボードデータをロードする"""
        raise NotImplementedError

    @abstractmethod
    def save(self, data: BoardData) -> None:
        """ボードデータを保存する"""
        raise NotImplementedError
