from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime


@dataclass(slots=True)
class Task:
    id: str
    title: str
    due_date: date | None
    category_id: str
    label_ids: list[str]
    color: str | None
    detail: str
    sort_order: int
    status_id: str
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def clone(self) -> "Task":
        return replace(self, label_ids=[*self.label_ids])

