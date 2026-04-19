from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    """アプリケーション設定"""

    data_file_path: str = "task_board.json"
    """データファイルのパス"""
    date_format: str = "%Y-%m-%d"
    """日付フォーマット"""

    def data_path(self) -> Path:
        """データファイルのパスを取得する"""
        return Path(self.data_file_path)
