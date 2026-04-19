from __future__ import annotations

from datetime import datetime


class DateTimeProvider:
    """日時プロバイダ"""

    def now(self) -> datetime:
        """現在日時を取得する"""
        return datetime.now().replace(microsecond=0)
