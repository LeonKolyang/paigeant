"""Audit logging utilities for security events."""

from __future__ import annotations

from typing import Any


class AuditLog:
    """Records signatures and authorization decisions."""

    async def record(self, event: str, details: Any) -> None:  # pragma: no cover - outline
        """Persist an audit log entry."""
        raise NotImplementedError
