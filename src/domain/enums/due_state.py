from __future__ import annotations

from enum import StrEnum


class DueState(StrEnum):
    """期限状態"""

    OVERDUE = "overdue"
    TODAY = "today"
    UPCOMING = "upcoming"
    NONE = "none"
