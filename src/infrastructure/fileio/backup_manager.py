from __future__ import annotations

from pathlib import Path
from shutil import copy2


class BackupManager:
    """バックアップマネージャー"""

    def create_backup(self, path: str | Path) -> None:
        """バックアップを作成する

        Args:
            path (str | Path): バックアップ元パス
        """
        source = Path(path)
        if not source.exists():
            return
        backup = source.with_suffix(f"{source.suffix}.bak")
        copy2(source, backup)
