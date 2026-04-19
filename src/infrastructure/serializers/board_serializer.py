from __future__ import annotations

from datetime import date, datetime
from typing import Any

from domain.models.app_settings import AppSettings
from domain.models.board_data import BoardData
from domain.models.category import Category
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task


class BoardSerializer:
    """ボードシリアライザ"""

    def to_dict(self, data: BoardData) -> dict[str, Any]:
        """ボードデータをディクショナリに変換する

        Args:
            data (BoardData): ボードデータ

        Returns:
            dict[str, Any]: ディクショナリ
        """
        return {
            "version": data.version,
            "categories": [
                {"id": c.id, "name": c.name, "sort_order": c.sort_order} for c in data.categories
            ],
            "labels": [
                {"id": l.id, "name": l.name, "color": l.color, "sort_order": l.sort_order}
                for l in data.labels
            ],
            "statuses": [
                {
                    "id": s.id,
                    "name": s.name,
                    "color": s.color,
                    "sort_order": s.sort_order,
                    "is_system": s.is_system,
                    "hides_from_board": s.hides_from_board,
                }
                for s in data.statuses
            ],
            "tasks": [self._task_to_dict(t) for t in data.tasks],
            "settings": {
                "data_file_path": data.settings.data_file_path,
                "date_format": data.settings.date_format,
            },
        }

    def from_dict(self, payload: dict[str, Any]) -> BoardData:
        """ディクショナリからボードデータを復元する

        Args:
            payload (dict[str, Any]): ディクショナリ

        Returns:
            BoardData: ボードデータ
        """
        settings = self._build_settings(payload.get("settings", {}))
        return BoardData(
            version=int(payload.get("version", 1)),
            categories=[
                Category(
                    id=str(item["id"]),
                    name=str(item["name"]),
                    sort_order=int(item.get("sort_order", index + 1)),
                )
                for index, item in enumerate(payload.get("categories", []))
            ],
            labels=[
                Label(
                    id=str(item["id"]),
                    name=str(item["name"]),
                    color=str(item.get("color", "#BFDBFE")),
                    sort_order=int(item.get("sort_order", index + 1)),
                )
                for index, item in enumerate(payload.get("labels", []))
            ],
            statuses=[
                Status(
                    id=str(item["id"]),
                    name=str(item["name"]),
                    color=str(item.get("color", "#6B7280")),
                    sort_order=int(item.get("sort_order", index + 1)),
                    is_system=bool(item.get("is_system", False)),
                    hides_from_board=bool(item.get("hides_from_board", False)),
                )
                for index, item in enumerate(payload.get("statuses", []))
            ],
            tasks=[self._task_from_dict(item) for item in payload.get("tasks", [])],
            settings=settings,
        )

    def _task_to_dict(self, task: Task) -> dict[str, Any]:
        """タスクをディクショナリに変換する

        Args:
            task (Task): タスク

        Returns:
            dict[str, Any]: ディクショナリ
        """
        return {
            "id": task.id,
            "title": task.title,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "category_id": task.category_id,
            "label_ids": task.label_ids,
            "color": task.color,
            "detail": task.detail,
            "sort_order": task.sort_order,
            "status_id": task.status_id,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    def _task_from_dict(self, item: dict[str, Any]) -> Task:
        """ディクショナリからタスクを復元する

        Args:
            item (dict[str, Any]): ディクショナリ

        Returns:
            Task: タスク
        """
        created_at = self._parse_datetime(item.get("created_at")) or datetime.now()
        updated_at = self._parse_datetime(item.get("updated_at")) or created_at
        return Task(
            id=str(item["id"]),
            title=str(item.get("title", "")),
            due_date=self._parse_date(item.get("due_date")),
            category_id=str(item["category_id"]),
            label_ids=[str(label_id) for label_id in item.get("label_ids", [])],
            color=item.get("color"),
            detail=str(item.get("detail", "")),
            sort_order=int(item.get("sort_order", 1)),
            status_id=str(item.get("status_id", "not_started")),
            completed_at=self._parse_datetime(item.get("completed_at")),
            created_at=created_at,
            updated_at=updated_at,
        )

    def _build_settings(self, item: dict[str, Any]) -> AppSettings:
        """設定をビルドする

        Args:
            item (dict[str, Any]): ディクショナリ

        Returns:
            AppSettings: 設定
        """
        return AppSettings(
            data_file_path=str(item.get("data_file_path", "task_board.json")),
            date_format=str(item.get("date_format", "%Y-%m-%d")),
        )

    def _parse_date(self, value: Any) -> date | None:
        """日付をパースする

        Args:
            value (Any): 日付

        Returns:
            date | None: 日付
        """
        if not value:
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    def _parse_datetime(self, value: Any) -> datetime | None:
        """日時をパースする

        Args:
            value (Any): 日時

        Returns:
            datetime | None: 日時
        """
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
