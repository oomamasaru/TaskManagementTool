from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.models.category import Category
from domain.models.label import Label
from domain.models.task import Task


class CompletedTasksDialog(QDialog):
    """完了済みタスクダイアログ"""

    def __init__(self, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle("完了済みタスク")
        self.resize(900, 520)

        self._tasks: list[Task] = []
        self._action = ""

        root = QVBoxLayout(self)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("検索")
        self._search_edit.textChanged.connect(self._rebuild_table)
        root.addWidget(self._search_edit)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["タスク名", "カテゴリ", "ラベル", "期限", "完了日時", "詳細"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        root.addWidget(self._table)

        button_row = QHBoxLayout()
        self._restore_button = QPushButton("復活")
        self._delete_button = QPushButton("完全削除")
        self._close_button = QPushButton("閉じる")
        self._restore_button.clicked.connect(self._on_restore)
        self._delete_button.clicked.connect(self._on_delete)
        self._close_button.clicked.connect(self.reject)
        button_row.addWidget(self._restore_button)
        button_row.addWidget(self._delete_button)
        button_row.addStretch(1)
        button_row.addWidget(self._close_button)
        root.addLayout(button_row)

        self._categories: dict[str, str] = {}
        self._labels: dict[str, str] = {}

    def load_completed_tasks(
        self,
        tasks: list[Task],
        categories: Iterable[Category] = (),
        labels: Iterable[Label] = (),
    ) -> None:
        """完了済みタスクをロードする

        Args:
            tasks (list[Task]): タスクリスト
            categories (Iterable[Category]): カテゴリリスト
            labels (Iterable[Label]): ラベルリスト
        """
        self._tasks = tasks
        self._categories = {category.id: category.name for category in categories}
        self._labels = {label.id: label.name for label in labels}
        self._rebuild_table()

    def selected_task_id(self) -> str | None:
        """選択されたタスクIDを返す"""
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        if item is None:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))

    def request_restore(self, task_id: str) -> str:
        """復活リクエスト

        Args:
            task_id (str): タスクID
        """
        return task_id

    def request_delete(self, task_id: str) -> str:
        """完全削除リクエスト

        Args:
            task_id (str): タスクID
        """
        return task_id

    @property
    def action(self) -> str:
        """実行するアクションを返す"""
        return self._action

    def _on_restore(self) -> None:
        """復活ボタンが押されたときの処理"""
        self._submit_action("restore")

    def _on_delete(self) -> None:
        """完全削除ボタンが押されたときの処理"""
        self._submit_action("delete")

    def _submit_action(self, action: str) -> None:
        """アクションを送信する

        Args:
            action (str): アクション
        """
        if self.selected_task_id() is None:
            return
        self._action = action
        self.accept()

    def _rebuild_table(self) -> None:
        """テーブルを再構築する"""
        keyword = self._search_edit.text().strip().lower()
        rows = [
            task
            for task in self._tasks
            if not keyword or keyword in task.title.lower() or keyword in task.detail.lower()
        ]
        self._table.setRowCount(len(rows))
        for row, task in enumerate(rows):
            title_item = QTableWidgetItem(task.title)
            title_item.setData(Qt.ItemDataRole.UserRole, task.id)
            category_name = self._categories.get(task.category_id, task.category_id)
            labels = ", ".join(self._labels.get(label_id, label_id) for label_id in task.label_ids)
            due_text = task.due_date.isoformat() if task.due_date else ""
            completed_text = task.completed_at.isoformat(sep=" ") if task.completed_at else ""
            preview = task.detail.replace("\n", " ")[:80]

            self._table.setItem(row, 0, title_item)
            self._table.setItem(row, 1, QTableWidgetItem(category_name))
            self._table.setItem(row, 2, QTableWidgetItem(labels))
            self._table.setItem(row, 3, QTableWidgetItem(due_text))
            self._table.setItem(row, 4, QTableWidgetItem(completed_text))
            self._table.setItem(row, 5, QTableWidgetItem(preview))
