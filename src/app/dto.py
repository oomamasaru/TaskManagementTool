from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from domain.models.task import Task


@dataclass(slots=True)
class TaskInputData:
    title: str
    due_date: date | None
    category_id: str
    label_ids: list[str] = field(default_factory=list)
    color: str | None = None
    detail: str = ""
    status_id: str = "not_started"


@dataclass(slots=True)
class TaskSearchResult:
    tasks: list[Task]
    total_count: int


@dataclass(slots=True)
class LabelFilterState:
    active_label_ids: set[str] = field(default_factory=set)
    include_no_label: bool = False

