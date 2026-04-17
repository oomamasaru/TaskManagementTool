from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from task_manager.models import BoardData


@dataclass
class SnapshotCommand:
    description: str
    before: BoardData
    after: BoardData


class CommandManager:
    """コマンド基盤"""

    def __init__(self) -> None:
        self._undo_stack: list[SnapshotCommand] = []
        """Undoスタック"""
        self._redo_stack: list[SnapshotCommand] = []
        """Redoスタック"""

    def execute(
        self, command: SnapshotCommand, apply_snapshot: Callable[[BoardData], None]
    ) -> None:
        """コマンド実行

        Args:
            command (SnapshotCommand): コマンド
            apply_snapshot (Callable[[BoardData], None]): 状態適用関数
        """
        apply_snapshot(command.after)
        self._undo_stack.append(command)
        self._redo_stack.clear()

    def undo(self, apply_snapshot: Callable[[BoardData], None]) -> bool:
        """Undo実行

        Args:
            apply_snapshot (Callable[[BoardData], None]): 状態適用関数

        Returns:
            bool: 成功/失敗
        """
        if not self._undo_stack:
            return False
        command = self._undo_stack.pop()
        apply_snapshot(command.before)
        self._redo_stack.append(command)
        return True

    def redo(self, apply_snapshot: Callable[[BoardData], None]) -> bool:
        """Redo実行

        Args:
            apply_snapshot (Callable[[BoardData], None]): 状態適用関数

        Returns:
            bool: 成功/失敗
        """
        if not self._redo_stack:
            return False
        command = self._redo_stack.pop()
        apply_snapshot(command.after)
        self._undo_stack.append(command)
        return True

    @property
    def can_undo(self) -> bool:
        """Undo可能か"""
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        """Redo可能か"""
        return bool(self._redo_stack)

    @property
    def undo_text(self) -> str:
        """Undoメニュー表示用テキスト"""
        if not self._undo_stack:
            return ""
        return self._undo_stack[-1].description

    @property
    def redo_text(self) -> str:
        """Redoメニュー表示用テキスト"""
        if not self._redo_stack:
            return ""
        return self._redo_stack[-1].description
