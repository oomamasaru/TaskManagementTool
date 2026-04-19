from __future__ import annotations

from pathlib import Path


class AtomicFileWriter:
    """アトミックファイルライター"""

    def write(self, path: str | Path, content: str) -> None:
        """ファイルを書き込む

        Args:
            path (str | Path): ファイルパス
            content (str): 書き込む内容
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = target.with_suffix(f"{target.suffix}.tmp")
        try:
            tmp_path.write_text(content, encoding="utf-8")
            tmp_path.replace(target)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
