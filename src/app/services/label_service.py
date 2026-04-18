from __future__ import annotations

from app.board_store import BoardStore
from domain.models.label import Label
from infrastructure.providers.id_provider import IdProvider
from utils.color_utils import normalize_hex_color


class LabelService:
    def __init__(self, store: BoardStore, id_provider: IdProvider) -> None:
        self._store = store
        self._id_provider = id_provider

    def add_label(self, name: str, color: str) -> Label:
        label_name = name.strip()
        if not label_name:
            raise ValueError("ラベル名は必須です。")
        if any(label.name.lower() == label_name.lower() for label in self._store.board_data.labels):
            raise ValueError("同名のラベルが存在します。")

        label = Label(
            id=self._id_provider.new_id("label"),
            name=label_name,
            color=normalize_hex_color(color),
            sort_order=self._next_sort_order(),
        )
        self._store.board_data.labels.append(label)
        self._normalize_sort_order()
        return label

    def update_label(self, label_id: str, name: str, color: str) -> Label:
        label = self._get_label(label_id)
        label_name = name.strip()
        if not label_name:
            raise ValueError("ラベル名は必須です。")
        if any(
            current.id != label_id and current.name.lower() == label_name.lower()
            for current in self._store.board_data.labels
        ):
            raise ValueError("同名のラベルが存在します。")

        label.name = label_name
        label.color = normalize_hex_color(color)
        return label

    def delete_label(self, label_id: str) -> None:
        self._get_label(label_id)
        self._store.board_data.labels = [
            label for label in self._store.board_data.labels if label.id != label_id
        ]
        for task in self._store.board_data.tasks:
            task.label_ids = [current for current in task.label_ids if current != label_id]
        self._normalize_sort_order()

    def _get_label(self, label_id: str) -> Label:
        label = next(
            (current for current in self._store.board_data.labels if current.id == label_id), None
        )
        if label is None:
            raise ValueError("ラベルが見つかりません。")
        return label

    def _next_sort_order(self) -> int:
        return max(
            (label.sort_order for label in self._store.board_data.labels),
            default=0,
        ) + 1

    def _normalize_sort_order(self) -> None:
        self._store.board_data.labels.sort(key=lambda label: label.sort_order)
        for index, label in enumerate(self._store.board_data.labels, start=1):
            label.sort_order = index
