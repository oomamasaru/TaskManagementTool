from __future__ import annotations

from pathlib import Path
from shutil import copy2


class BackupManager:
    def create_backup(self, path: str | Path) -> None:
        source = Path(path)
        if not source.exists():
            return
        backup = source.with_suffix(f"{source.suffix}.bak")
        copy2(source, backup)

