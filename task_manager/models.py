from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

NOT_STARTED_STATUS_ID = "not_started"
"""未着手ステータスID"""
COMPLETED_STATUS_ID = "completed"
"""完了ステータスID"""


class Prefix(StrEnum):
    TASK = "task"
    STATUS = "status"
    LABEL = "label"
    CATEGORY = "category"


def now_iso() -> str:
    """現在時刻をISO 8601形式文字列で取得(マイクロ秒以下切り捨て)

    Returns:
        str: "YYYY-MM-DDTHH:MM:SS"
    """
    return datetime.now().replace(microsecond=0).isoformat()


def generate_id(prefix: Prefix) -> str:
    """指定されたプレフィックスとUUIDを組み合わせた文字列を生成

    Args:
        prefix (str): プレフィックス文字列

    Returns:
        str: "<プレフィックス>_<UUID(8桁)>"
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class Category:
    """カテゴリクラス

    Attributes:
        id (str): カテゴリID
        name (str): カテゴリ名
        sort_order (int): ソート順序
    """

    id: str
    """カテゴリID"""
    name: str
    """カテゴリ名"""
    sort_order: int
    """ソート順序"""

    @classmethod
    def from_dict(cls, data: dict) -> Category:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            sort_order=int(data.get("sort_order", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sort_order": self.sort_order,
        }


@dataclass
class Label:
    """ラベルクラス

    Attributes:
        id (str): ラベルID
        name (str): ラベル名
        color (str): ラベルカラー
        sort_order (int): ソート順序
    """

    id: str
    """ラベルID"""
    name: str
    """ラベル名"""
    color: str
    """ラベルカラー"""
    sort_order: int
    """ソート順序"""

    @classmethod
    def from_dict(cls, data: dict) -> Label:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#BFDBFE")),
            sort_order=int(data.get("sort_order", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "sort_order": self.sort_order,
        }


@dataclass
class Status:
    """ステータスクラス

    Attributes:
        id (str): ステータスID
        name (str): ステータス名
        color (str): ステータスカラー
        sort_order (int): ソート順序
        is_system (bool): システムフラグ
        hides_from_board (bool): ボード非表示フラグ
    """

    id: str
    """ステータスID"""
    name: str
    """ステータス名"""
    color: str
    """ステータスカラー"""
    sort_order: int
    """ソート順序"""
    is_system: bool
    """システムフラグ"""
    hides_from_board: bool
    """ボード非表示フラグ"""

    @classmethod
    def from_dict(cls, data: dict) -> Status:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#6B7280")),
            sort_order=int(data.get("sort_order", 0)),
            is_system=bool(data.get("is_system", False)),
            hides_from_board=bool(data.get("hides_from_board", False)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "sort_order": self.sort_order,
            "is_system": self.is_system,
            "hides_from_board": self.hides_from_board,
        }


@dataclass
class Task:
    """タスククラス

    Attributes:
        id (str): タスクID
        title (str): タスク名
        due_date (str | None): 期限日
        category_id (str): カテゴリID
        label_ids (list[str]): ラベルIDリスト
        color (str | None): タスクカラー
        detail (str): タスク詳細
        sort_order (int): ソート順序
        status_id (str): ステータスID
        completed_at (str | None): 完了日時
        created_at (str): 作成日時
        updated_at (str): 更新日時
    """

    id: str
    "タスクID"
    title: str
    "タスク名"
    due_date: str | None
    "期限日"
    category_id: str
    "カテゴリID"
    label_ids: list[str]
    "ラベルIDリスト"
    color: str | None
    "タスクカラー"
    detail: str
    "タスク詳細"
    sort_order: int
    "ソート順序"
    status_id: str
    "ステータスID"
    completed_at: str | None
    "完了日時"
    created_at: str
    "作成日時"
    updated_at: str
    "更新日時"

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        raw_labels = data.get("label_ids", [])
        if not isinstance(raw_labels, list):
            raw_labels = []
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            due_date=data.get("due_date"),
            category_id=str(data.get("category_id", "")),
            label_ids=[str(x) for x in raw_labels],
            color=data.get("color"),
            detail=str(data.get("detail", "")),
            sort_order=int(data.get("sort_order", 0)),
            status_id=str(data.get("status_id", NOT_STARTED_STATUS_ID)),
            completed_at=data.get("completed_at"),
            created_at=str(data.get("created_at", now_iso())),
            updated_at=str(data.get("updated_at", now_iso())),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "due_date": self.due_date,
            "category_id": self.category_id,
            "label_ids": self.label_ids,
            "color": self.color,
            "detail": self.detail,
            "sort_order": self.sort_order,
            "status_id": self.status_id,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class BoardData:
    """タスクボード全体データクラス

    Attributes:
        version (int): バージョン
        categories (list[Category]): カテゴリリスト
        labels (list[Label]): ラベルリスト
        statuses (list[Status]): ステータスリスト
        tasks (list[Task]): タスクリスト
    """

    version: int = 1
    """バージョン"""
    categories: list[Category] = field(default_factory=list)
    """カテゴリリスト"""
    labels: list[Label] = field(default_factory=list)
    """ラベルリスト"""
    statuses: list[Status] = field(default_factory=list)
    """ステータスリスト"""
    tasks: list[Task] = field(default_factory=list)
    """タスクリスト"""

    @classmethod
    def from_dict(cls, data: dict) -> BoardData:
        return cls(
            version=int(data.get("version", 1)),
            categories=[Category.from_dict(x) for x in data.get("categories", [])],
            labels=[Label.from_dict(x) for x in data.get("labels", [])],
            statuses=[Status.from_dict(x) for x in data.get("statuses", [])],
            tasks=[Task.from_dict(x) for x in data.get("tasks", [])],
        )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "categories": [x.to_dict() for x in self.categories],
            "labels": [x.to_dict() for x in self.labels],
            "statuses": [x.to_dict() for x in self.statuses],
            "tasks": [x.to_dict() for x in self.tasks],
        }

    def clone(self) -> BoardData:
        """ディープコピーを返す"""
        return copy.deepcopy(self)

    def sort_all(self) -> None:
        """全データのソート"""
        self.categories.sort(key=lambda x: (x.sort_order, x.name))
        self.labels.sort(key=lambda x: (x.sort_order, x.name))
        self.statuses.sort(key=lambda x: (x.sort_order, x.name))
        self.tasks.sort(key=lambda x: (x.category_id, x.sort_order, x.created_at))

    def get_status(self, status_id: str) -> Status | None:
        """ステータスを取得"""
        for status in self.statuses:
            if status.id == status_id:
                return status
        return None

    def get_category(self, category_id: str) -> Category | None:
        """カテゴリを取得"""
        for category in self.categories:
            if category.id == category_id:
                return category
        return None

    def get_label(self, label_id: str) -> Label | None:
        """ラベルを取得"""
        for label in self.labels:
            if label.id == label_id:
                return label
        return None


def default_statuses() -> list[Status]:
    """デフォルトステータスリストを取得

    Returns:
        list[Status]: デフォルトステータスリスト
    """
    return [
        Status(
            id=NOT_STARTED_STATUS_ID,
            name="未着手",
            color="#6B7280",
            sort_order=1,
            is_system=True,
            hides_from_board=False,
        ),
        Status(
            id="in_progress",
            name="作業中",
            color="#2563EB",
            sort_order=2,
            is_system=False,
            hides_from_board=False,
        ),
        Status(
            id=COMPLETED_STATUS_ID,
            name="完了",
            color="#059669",
            sort_order=999,
            is_system=True,
            hides_from_board=True,
        ),
    ]


def default_categories() -> list[Category]:
    """デフォルトカテゴリリストを取得

    Returns:
        list[Category]: デフォルトカテゴリリスト
    """
    return [Category(id="cat_a", name="A", sort_order=1)]


def default_board_data() -> BoardData:
    """初期タスクボードデータ

    Returns:
        BoardData: 初期タスクボードデータ
    """
    return BoardData(
        version=1,
        categories=default_categories(),
        labels=[],
        statuses=default_statuses(),
        tasks=[],
    )
