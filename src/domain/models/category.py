from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Category:
    """カテゴリ"""

    id: str
    """カテゴリID"""
    name: str
    """カテゴリ名"""
    sort_order: int
    """表示順序"""
