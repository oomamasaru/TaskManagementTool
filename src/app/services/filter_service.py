from __future__ import annotations

from domain.models.filter_condition import FilterCondition
from domain.models.task import Task


class FilterService:
    def matches(self, task: Task, condition: FilterCondition) -> bool:
        search_text = condition.search_text.strip().lower()
        if search_text:
            if search_text not in task.title.lower() and search_text not in task.detail.lower():
                return False

        label_filter_enabled = bool(condition.active_label_ids) or condition.include_no_label
        if label_filter_enabled:
            has_selected_label = bool(set(task.label_ids).intersection(condition.active_label_ids))
            is_no_label_task = not task.label_ids
            if not (has_selected_label or (condition.include_no_label and is_no_label_task)):
                return False

        return True

    def apply(self, tasks: list[Task], condition: FilterCondition) -> list[Task]:
        return [task for task in tasks if self.matches(task, condition)]
