from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from task_manager.models import BoardData, default_board_data


class StorageError(Exception):
    pass


class StorageManager:
    """タスクボードデータの永続化(読み書き)を担当するクラス"""

    def __init__(self, file_path: Path) -> None:
        """イニシャライザ

        Args:
            file_path (Path): 保存先データファイルのパス
        """
        self.file_path = file_path
        """保存先ファイルパス"""
        self.backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        """バックアップファイルパス"""

    def load(self) -> BoardData:
        """保存データ読み込み

        Returns:
            BoardData: タスクボードデータ
        """
        if not self.file_path.exists():
            data = default_board_data()
            self.save(data)
            return data

        try:
            raw = self.file_path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            return BoardData.from_dict(payload)
        except Exception as exc:
            if self.backup_path.exists():
                try:
                    backup_raw = self.backup_path.read_text(encoding="utf-8")
                    backup_payload = json.loads(backup_raw)
                    return BoardData.from_dict(backup_payload)
                except Exception as backup_exc:
                    raise StorageError(
                        "保存データとバックアップの両方を読み込めませんでした。"
                    ) from backup_exc
            raise StorageError("保存データを読み込めませんでした。") from exc

    def save(self, board_data: BoardData) -> None:
        """タスクボードデータの保存

        Args:
            board_data (BoardData): タスクボードデータ
        """
        payload = board_data.to_dict()
        content = json.dumps(payload, ensure_ascii=False, indent=2)

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if self.file_path.exists():
            shutil.copy2(self.file_path, self.backup_path)

        fd, temp_name = tempfile.mkstemp(
            prefix=f"{self.file_path.stem}_",
            suffix=".tmp",
            dir=str(self.file_path.parent),
            text=True,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", closefd=True) as f:
                f.write(content)
            temp_path.replace(self.file_path)
        except Exception as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise StorageError("データ保存に失敗しました。") from exc
