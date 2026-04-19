from __future__ import annotations

from uuid import uuid4


class IdProvider:
    """IDプロバイダ"""

    def new_id(self, prefix: str = "id") -> str:
        """新しいIDを生成する"""
        return f"{prefix}_{uuid4().hex[:8]}"
