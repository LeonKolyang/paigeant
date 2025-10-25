"""Utilities for validating and exchanging security tokens."""

from __future__ import annotations

from typing import Any, Dict


class TokenValidator:
    """Validates sender-constrained and audience-bound tokens.

    Concrete implementations should retrieve signing keys via JWKS and perform
    all necessary validation steps such as expiration, issuer, audience and
    mTLS/DPoP binding checks.
    """

    async def validate(self, token: str) -> Dict[str, Any]:  # pragma: no cover - outline
        """Validate ``token`` and return its claims."""
        raise NotImplementedError


class TokenExchanger:
    """Exchanges tokens to enforce least-privilege delegation per hop."""

    async def exchange(self, token: str, audience: str) -> str:  # pragma: no cover
        """Produce a new token scoped to ``audience`` for OBO delegation."""
        raise NotImplementedError
