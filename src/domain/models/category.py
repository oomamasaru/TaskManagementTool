from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Category:
    id: str
    name: str
    sort_order: int
