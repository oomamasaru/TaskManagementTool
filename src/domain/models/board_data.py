from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.app_settings import AppSettings
from domain.models.category import Category
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task


@dataclass(slots=True)
class BoardData:
    version: int = 1
    categories: list[Category] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    statuses: list[Status] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    settings: AppSettings = field(default_factory=AppSettings)

