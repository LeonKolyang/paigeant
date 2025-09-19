"""Key management utilities for signing and verification."""

from __future__ import annotations

from typing import Any


class KeyProvider:
    """Provides signing and verification keys with rotation support."""

    async def get_signing_key(self) -> Any:  # pragma: no cover - outline
        """Return the current private key used for signing."""
        raise NotImplementedError

    async def get_verification_keys(self) -> dict[str, Any]:  # pragma: no cover
        """Return mapping of ``kid`` to public keys for verification."""
        raise NotImplementedError
