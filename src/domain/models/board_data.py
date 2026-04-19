from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.app_settings import AppSettings
from domain.models.category import Category
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task


@dataclass(slots=True)
class BoardData:
    """ボードのデータを保持するクラス"""

    version: int = 1
    """バージョン"""

    categories: list[Category] = field(default_factory=list)
    """カテゴリ"""

    labels: list[Label] = field(default_factory=list)
    """ラベル"""

    statuses: list[Status] = field(default_factory=list)
    """ステータス"""

    tasks: list[Task] = field(default_factory=list)
    """タスク"""

    settings: AppSettings = field(default_factory=AppSettings)
    """設定"""
