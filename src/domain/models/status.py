from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Status:
    id: str
    name: str
    color: str
    sort_order: int
    is_system: bool
    hides_from_board: bool
