from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FilterCondition:
    """フィルター条件"""

    search_text: str = ""
    """検索テキスト"""
    active_label_ids: set[str] = field(default_factory=set)
    """アクティブなラベルIDのセット"""
    include_no_label: bool = False
    """ラベルなしのタスクを含むかどうか"""
