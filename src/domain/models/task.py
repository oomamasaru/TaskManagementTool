from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime


@dataclass(slots=True)
class Task:
    """タスク"""

    id: str
    """タスクID"""
    title: str
    """タイトル"""
    due_date: date | None
    """期限"""
    category_id: str
    """カテゴリID"""
    label_ids: list[str]
    """ラベルIDのリスト"""
    color: str | None
    """ラベル色"""
    detail: str
    """詳細"""
    sort_order: int
    """表示順序"""
    status_id: str
    """ステータスID"""
    completed_at: datetime | None
    """完了日時"""
    created_at: datetime
    """作成日時"""
    updated_at: datetime
    """更新日時"""

    def clone(self) -> Task:
        """タスクをクローンする"""
        return replace(self, label_ids=[*self.label_ids])
