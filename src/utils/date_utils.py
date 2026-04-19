from __future__ import annotations

from datetime import date

from domain.enums.due_state import DueState


def calc_due_state(due_date: date | None, today: date | None = None) -> DueState:
    """期限状態を計算する

    Args:
        due_date (date | None): 期限日
        today (date | None, optional): 今日. Defaults to None.

    Returns:        DueState: 期限状態
    """
    if due_date is None:
        return DueState.NONE
    base = today or date.today()
    if due_date < base:
        return DueState.OVERDUE
    if due_date == base:
        return DueState.TODAY
    return DueState.UPCOMING


def calc_remaining_days(due_date: date | None, today: date | None = None) -> int | None:
    """残日数を計算する

    Args:
        due_date (date | None): 期限日
        today (date | None, optional): 今日. Defaults to None.

    Returns:
        int | None: 残日数
    """
    if due_date is None:
        return None
    base = today or date.today()
    return (due_date - base).days
