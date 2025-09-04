"""Middleware helpers for applying security checks."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from .context import SecurityContext


Handler = Callable[[Any], Awaitable[Any]]


def with_security(handler: Handler) -> Handler:
    """Wrap ``handler`` with token validation and policy enforcement.

    This is a placeholder demonstrating where security hooks would execute.
    The middleware would typically construct a :class:`SecurityContext`, validate
    incoming tokens, verify message signatures and consult the
    :class:`~paigeant.security.policy.PolicyEngine` before invoking ``handler``.
    """

    async def _wrapper(message: Any) -> Any:  # pragma: no cover - outline
        context = SecurityContext()
        _ = context  # placeholder to avoid linter errors
        return await handler(message)

    return _wrapper
