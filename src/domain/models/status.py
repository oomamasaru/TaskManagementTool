from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Status:
    """ステータス"""

    id: str
    """ステータスID"""
    name: str
    """ステータス名"""
    color: str
    """ステータス色"""
    sort_order: int
    """表示順序"""
    is_system: bool
    """システムフラグ"""
    hides_from_board: bool
    """ボードから隠すフラグ"""
