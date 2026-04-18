from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    data_file_path: str = "task_board.json"
    date_format: str = "%Y-%m-%d"

    def data_path(self) -> Path:
        return Path(self.data_file_path)
