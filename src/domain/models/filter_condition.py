from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FilterCondition:
    search_text: str = ""
    active_label_ids: set[str] = field(default_factory=set)
    include_no_label: bool = False

