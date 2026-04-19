from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Label:
    """ラベル"""

    id: str
    """ラベルID"""
    name: str
    """ラベル名"""
    color: str
    """ラベル色"""
    sort_order: int
    """表示順序"""
