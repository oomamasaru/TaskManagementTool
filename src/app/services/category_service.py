from __future__ import annotations

from app.board_store import BoardStore
from domain.models.category import Category
from infrastructure.providers.id_provider import IdProvider


class CategoryService:
    """カテゴリを操作するためのサービス。

    タスクの追加、削除、並び替えなど、カテゴリに関するビジネスロジックを提供します。
    """

    def __init__(self, store: BoardStore, id_provider: IdProvider) -> None:
        """イニシャライザ

        Args:
            store (BoardStore): ボードのデータを管理するストア
            id_provider (IdProvider): IDを生成するプロバイダ
        """
        self._store = store
        self._id_provider = id_provider

    def add_category(self, name: str) -> Category:
        """カテゴリを追加する

        Args:
            name (str): 追加するカテゴリの名前

        Returns:
            Category: 追加されたカテゴリ
        """
        category_name = name.strip()
        if not category_name:
            raise ValueError("カテゴリ名は必須です。")
        existing_names = {category.name.lower() for category in self._store.board_data.categories}
        if category_name.lower() in existing_names:
            raise ValueError("同名のカテゴリが存在します。")

        category = Category(
            id=self._id_provider.new_id("cat"),
            name=category_name,
            sort_order=self._next_sort_order(),
        )
        self._store.board_data.categories.append(category)
        self._normalize_sort_order()
        return category

    def update_category(self, category_id: str, name: str) -> Category:
        """カテゴリ名を更新する"""
        category = self._store.find_category(category_id)
        if category is None:
            raise ValueError("カテゴリが見つかりません。")

        category_name = name.strip()
        if not category_name:
            raise ValueError("カテゴリ名は必須です。")
        if any(
            current.id != category_id and current.name.lower() == category_name.lower()
            for current in self._store.board_data.categories
        ):
            raise ValueError("同名のカテゴリが既に存在します。")

        category.name = category_name
        return category

    def delete_category(self, category_id: str) -> None:
        """カテゴリを削除する

        Args:
            category_id (str): 削除するカテゴリのID
        """
        if self._store.find_category(category_id) is None:
            raise ValueError("カテゴリが見つかりません。")

        self._store.board_data.categories = [
            category for category in self._store.board_data.categories if category.id != category_id
        ]
        self._store.board_data.tasks = [
            task for task in self._store.board_data.tasks if task.category_id != category_id
        ]
        self._normalize_sort_order()

    def reorder_categories(self, ordered_category_ids: list[str]) -> None:
        """カテゴリの表示順序を変更する

        Args:
            ordered_category_ids (list[str]): カテゴリIDの順序
        """
        mapping = {category.id: category for category in self._store.board_data.categories}
        ordered: list[Category] = []
        for category_id in ordered_category_ids:
            category = mapping.pop(category_id, None)
            if category is not None:
                ordered.append(category)
        ordered.extend(mapping.values())
        for index, category in enumerate(ordered, start=1):
            category.sort_order = index
        self._store.board_data.categories = ordered
        self._normalize_sort_order()

    def _next_sort_order(self) -> int:
        """次のソート順序を取得する

        Returns:
            int: 次のソート順序
        """
        return max(
            (category.sort_order for category in self._store.board_data.categories),
            default=0,
        ) + 1

    def _normalize_sort_order(self) -> None:
        """カテゴリのソート順序を正規化する"""
        self._store.board_data.categories.sort(key=lambda category: category.sort_order)
        for index, category in enumerate(self._store.board_data.categories, start=1):
            category.sort_order = index
