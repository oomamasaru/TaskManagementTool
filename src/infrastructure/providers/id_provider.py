from __future__ import annotations

from uuid import uuid4


class IdProvider:
    def new_id(self, prefix: str = "id") -> str:
        return f"{prefix}_{uuid4().hex[:8]}"

