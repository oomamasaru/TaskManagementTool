from __future__ import annotations

from datetime import datetime


class DateTimeProvider:
    def now(self) -> datetime:
        return datetime.now().replace(microsecond=0)

