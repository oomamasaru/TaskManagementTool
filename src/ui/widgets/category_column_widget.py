from __future__ import annotations

import contextlib

from PyQt6.QtCore import (
    QEasingCurve,
    QMimeData,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from domain.models.category import Category
from domain.models.label import Label
from domain.models.status import Status
from domain.models.task import Task
from ui.widgets.task_card_widget import TaskCardWidget


class TaskListWidget(QListWidget):
    """タスクリストウィジェット"""

    drop_committed = pyqtSignal(str, str, list, bool, object, object)
    """ドロップ完了シグナル

    Args:
        category_id (str): カテゴリID
        moved_task_id (str): 移動したタスクID
        task_ids (list[str]): タスクIDリスト
        is_same_category_drop (bool): 同一カテゴリ内でのドロップ
        before_positions (object): ドロップ前の位置
        after_positions (object): ドロップ後の位置
    """

    def __init__(self, category_id: str, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            category_id (str): カテゴリID
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self._category_id = category_id
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)

    def set_category_id(self, category_id: str) -> None:
        """カテゴリIDを設定する

        Args:
            category_id (str): カテゴリID
        """
        self._category_id = category_id

    def mimeData(self, items: list[QListWidgetItem]) -> QMimeData:  # noqa: N802
        """MIMEデータを取得する

        Args:
            items:

        Returns:
            QMimeData: MIMEデータ
        """
        mime_data = super().mimeData(items)
        if items:
            mime_data.setText(str(items[0].data(Qt.ItemDataRole.UserRole)))
        return mime_data

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """ドラッグエンターイベント

        Args:
            event (QDragEnterEvent): ドロップイベント
        """
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """ドロップイベント

        Args:
            event (QDropEvent): ドロップイベント
        """
        is_same_category_drop = event.source() is self
        before_positions = self._capture_item_positions() if is_same_category_drop else {}
        moved_task_id = event.mimeData().text()
        super().dropEvent(event)
        after_positions = self._capture_item_positions() if is_same_category_drop else {}
        self.drop_committed.emit(
            self._category_id,
            moved_task_id,
            self.task_ids(),
            is_same_category_drop,
            before_positions,
            after_positions,
        )

    def task_ids(self) -> list[str]:
        """タスクIDリストを取得する

        Returns:
            list[str]: タスクIDリスト
        """
        return [str(self.item(row).data(Qt.ItemDataRole.UserRole)) for row in range(self.count())]

    def task_widget(self, task_id: str) -> TaskCardWidget | None:
        """タスクウィジェットを取得する

        Args:
            task_id (str): タスクID

        Returns:
            TaskCardWidget | None: タスクウィジェット
        """
        for row in range(self.count()):
            item = self.item(row)
            if str(item.data(Qt.ItemDataRole.UserRole)) != task_id:
                continue
            widget = self.itemWidget(item)
            if isinstance(widget, TaskCardWidget):
                return widget
            return None
        return None

    def _capture_item_positions(self) -> dict[str, QPoint]:
        """アイテム位置を取得する

        Returns:
            dict[str, QPoint]: アイテム位置の辞書
        """
        return {
            str(self.item(row).data(Qt.ItemDataRole.UserRole)): self.visualItemRect(
                self.item(row)
            ).topLeft()
            for row in range(self.count())
        }


class CategoryColumnWidget(QFrame):
    """カテゴリカラムウィジェット"""

    add_task_requested = pyqtSignal(str)
    """タスク追加要求シグナル

    Args:
        category_id (str): カテゴリID
    """
    task_open_requested = pyqtSignal(str)
    """タスクオープン要求シグナル
    Args:
        task_id (str): タスクID
    """
    """
    Args:
        task_id (str): タスクID
    """
    task_context_requested = pyqtSignal(str, QPoint)
    """タスクコンテキスト要求シグナル
    Args:
        task_id (str): タスクID
        position (QPoint): 位置
    """
    category_context_requested = pyqtSignal(str, QPoint)
    """カテゴリコンテキスト要求シグナル
    Args:
        category_id (str): カテゴリID
        position (QPoint): 位置
    """
    tasks_reordered = pyqtSignal(str, str, list)
    """タスク再注文シグナル
    Args:
        category_id (str): カテゴリID
        moved_task_id (str): 移動したタスクID
        task_ids (list[str]): タスクIDリスト
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """イニシャライザ

        Args:
            parent (QWidget | None): 親ウィジェット
        """
        super().__init__(parent)
        self._category: Category | None = None
        self._reorder_animation: QParallelAnimationGroup | None = None
        self._reorder_overlay: QWidget | None = None
        self._reorder_hidden_cards: list[QWidget] = []
        self._reorder_ghosts: list[QLabel] = []
        self._pending_reorder_payload: tuple[str, str, list] | None = None

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("QFrame{border:1px solid #E5E7EB;border-radius:6px;background:#F9FAFB;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._header_widget = QWidget()
        self._header_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._header_widget.customContextMenuRequested.connect(self._on_category_context_menu)
        header = QHBoxLayout(self._header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        self._title_label = QLabel("-")
        self._title_label.setStyleSheet("font-weight:700;")
        self._add_button = QPushButton("+")
        self._add_button.setFixedWidth(28)
        self._add_button.clicked.connect(self._emit_add_task)
        header.addWidget(self._title_label)
        header.addStretch(1)
        header.addWidget(self._add_button)
        root.addWidget(self._header_widget)

        self._list = TaskListWidget("")
        self._list.setSpacing(6)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.drop_committed.connect(self._on_drop_committed)
        root.addWidget(self._list)

    def set_category(self, category: Category) -> None:
        """カテゴリを設定する

        Args:
            category (Category): カテゴリ
        """
        self._category = category
        self._title_label.setText(category.name)
        self._list.set_category_id(category.id)

    def render_tasks(
        self,
        tasks: list[Task],
        statuses: dict[str, Status],
        labels: dict[str, Label],
        date_format: str,
    ) -> None:
        """タスクをレンダリングする

        Args:
            tasks (list[Task]): タスクリスト
            statuses (dict[str, Status]): ステータス辞書
            labels (dict[str, Label]): ラベル辞書
            date_format (str): 日付フォーマット
        """
        self._finalize_active_reorder_animation(emit_pending=False)
        self._list.clear()
        for task in tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            card = TaskCardWidget(
                task=task,
                status=statuses.get(task.status_id),
                labels=[labels[label_id] for label_id in task.label_ids if label_id in labels],
                date_format=date_format,
            )
            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

    def task_ids(self) -> list[str]:
        """タスクIDリストを取得する

        Returns:
            list[str]: タスクIDリスト
        """
        return self._list.task_ids()

    def _emit_add_task(self) -> None:
        """タスク追加を要求する"""
        if self._category is None:
            return
        self.add_task_requested.emit(self._category.id)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """アイテムダブルクリックイベント

        Args:
            item (QListWidgetItem): アイテム
        """
        self.task_open_requested.emit(str(item.data(Qt.ItemDataRole.UserRole)))

    def _on_context_menu(self, point: QPoint) -> None:
        """コンテキストメニューイベント

        Args:
            point (QPoint): 位置
        """
        item = self._list.itemAt(point)
        if item is None:
            if self._category is None:
                return
            global_pos = self._list.viewport().mapToGlobal(point)
            self.category_context_requested.emit(self._category.id, global_pos)
            return
        task_id = str(item.data(Qt.ItemDataRole.UserRole))
        global_pos = self._list.viewport().mapToGlobal(point)
        self.task_context_requested.emit(task_id, global_pos)

    def _on_category_context_menu(self, point: QPoint) -> None:
        """カテゴリコンテキストメニューイベント

        Args:
            point (QPoint): 位置
        """
        if self._category is None:
            return
        global_pos = self._header_widget.mapToGlobal(point)
        self.category_context_requested.emit(self._category.id, global_pos)

    def _on_drop_committed(
        self,
        category_id: str,
        moved_task_id: str,
        ordered_ids: list[str],
        is_same_category_drop: bool,
        before_positions_obj: object,
        after_positions_obj: object,
    ) -> None:
        """ドロップコミットイベント

        Args:
            category_id (str): カテゴリID
            moved_task_id (str): 移動したタスクID
            ordered_ids (list[str]): タスクIDリスト
            is_same_category_drop (bool): 同一カテゴリ内でのドロップ
            before_positions_obj (object): ドロップ前の位置
            after_positions_obj (object): ドロップ後の位置
        """
        self._finalize_active_reorder_animation(emit_pending=True)

        payload = (category_id, moved_task_id, ordered_ids)
        if not is_same_category_drop:
            self.tasks_reordered.emit(*payload)
            return

        before_positions = before_positions_obj if isinstance(before_positions_obj, dict) else {}
        after_positions = after_positions_obj if isinstance(after_positions_obj, dict) else {}
        started = self._start_reorder_animation(before_positions, after_positions)
        if not started:
            self.tasks_reordered.emit(*payload)
            return
        self._pending_reorder_payload = payload

    def _start_reorder_animation(
        self,
        before_positions: dict[str, QPoint],
        after_positions: dict[str, QPoint],
    ) -> bool:
        """再注文アニメーションを開始する

        Args:
            before_positions (dict[str, QPoint]): ドロップ前の位置
            after_positions (dict[str, QPoint]): ドロップ後の位置

        Returns:
            bool: アニメーションが開始されたかどうか
        """
        moving_task_ids = [
            task_id
            for task_id, before_pos in before_positions.items()
            if task_id in after_positions and before_pos != after_positions[task_id]
        ]
        if not moving_task_ids:
            return False

        viewport = self._list.viewport()
        overlay = QWidget(viewport)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        overlay.setGeometry(viewport.rect())
        overlay.show()

        group = QParallelAnimationGroup(self)
        hidden_cards: list[QWidget] = []
        ghosts: list[QLabel] = []

        for task_id in moving_task_ids:
            card = self._list.task_widget(task_id)
            if card is None:
                continue
            start_pos = before_positions.get(task_id)
            end_pos = after_positions.get(task_id)
            if not isinstance(start_pos, QPoint) or not isinstance(end_pos, QPoint):
                continue

            ghost = QLabel(overlay)
            ghost.setPixmap(card.grab())
            ghost.setFixedSize(card.size())
            ghost.move(start_pos)
            ghost.show()
            ghost.raise_()
            ghosts.append(ghost)

            card.setVisible(False)
            hidden_cards.append(card)

            animation = QPropertyAnimation(ghost, b"pos", group)
            animation.setDuration(180)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.setStartValue(start_pos)
            animation.setEndValue(end_pos)
            group.addAnimation(animation)

        if group.animationCount() == 0:
            overlay.deleteLater()
            for card in hidden_cards:
                card.setVisible(True)
            return False

        self._reorder_animation = group
        self._reorder_overlay = overlay
        self._reorder_hidden_cards = hidden_cards
        self._reorder_ghosts = ghosts
        self._reorder_animation.finished.connect(self._on_reorder_animation_finished)
        self._reorder_animation.start()
        return True

    def _on_reorder_animation_finished(self) -> None:
        """再注文アニメーション完了イベント"""
        payload = self._pending_reorder_payload
        self._pending_reorder_payload = None
        self._cleanup_reorder_animation()
        if payload is not None:
            self.tasks_reordered.emit(*payload)

    def _finalize_active_reorder_animation(self, emit_pending: bool) -> None:
        """アクティブな再注文アニメーションを終了する

        Args:
            emit_pending (bool): ペンディング中のアニメーションを送信するかどうか
        """
        if self._reorder_animation is None:
            return
        with contextlib.suppress(TypeError):
            self._reorder_animation.finished.disconnect(self._on_reorder_animation_finished)
        self._reorder_animation.stop()

        payload = self._pending_reorder_payload
        self._pending_reorder_payload = None
        self._cleanup_reorder_animation()

        if emit_pending and payload is not None:
            self.tasks_reordered.emit(*payload)

    def _cleanup_reorder_animation(self) -> None:
        """再注文アニメーションをクリーンアップする"""
        for card in self._reorder_hidden_cards:
            with contextlib.suppress(RuntimeError):
                card.setVisible(True)
        self._reorder_hidden_cards.clear()

        for ghost in self._reorder_ghosts:
            ghost.deleteLater()
        self._reorder_ghosts.clear()

        if self._reorder_overlay is not None:
            self._reorder_overlay.deleteLater()
            self._reorder_overlay = None

        if self._reorder_animation is not None:
            self._reorder_animation.deleteLater()
            self._reorder_animation = None
