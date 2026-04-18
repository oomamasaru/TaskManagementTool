from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Label:
    id: str
    name: str
    color: str
    sort_order: int
