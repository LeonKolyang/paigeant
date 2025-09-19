"""Runtime policy enforcement for Paigeant."""

from __future__ import annotations

from typing import Any


class PolicyEngine:
    """Evaluates authorization policies at runtime."""

    async def evaluate(self, context: Any, action: str, resource: str) -> bool:  # pragma: no cover
        """Return ``True`` if the ``action`` on ``resource`` is permitted."""
        raise NotImplementedError
