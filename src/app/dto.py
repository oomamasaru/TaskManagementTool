from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from domain.models.task import Task


@dataclass(slots=True)
class TaskInputData:
    """タスク入力データ"""

    title: str
    """タイトル"""
    due_date: date | None
    """期限"""
    category_id: str
    """カテゴリID"""
    label_ids: list[str] = field(default_factory=list)
    """ラベルIDのリスト"""
    color: str | None = None
    """色"""
    detail: str = ""
    """詳細"""
    status_id: str = "not_started"
    """ステータスID"""


@dataclass(slots=True)
class TaskSearchResult:
    """タスク検索結果"""

    tasks: list[Task]
    """タスクのリスト"""
    total_count: int
    """タスクの総数"""


@dataclass(slots=True)
class LabelFilterState:
    """ラベルフィルター状態"""

    active_label_ids: set[str] = field(default_factory=set)
    """アクティブなラベルIDのセット"""
    include_no_label: bool = False
    """ラベルなしのタスクを含むかどうか"""
