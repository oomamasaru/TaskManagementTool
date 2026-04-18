from __future__ import annotations

from enum import Enum


class DueState(str, Enum):
    OVERDUE = "overdue"
    TODAY = "today"
    UPCOMING = "upcoming"
    NONE = "none"

