"""JWS signing and verification services."""

from __future__ import annotations

from typing import Any

from .context import CanonicalMessage, SignatureEnvelope


class JwsService:
    """Signs and verifies messages using JSON Web Signatures.

    The service operates on canonical message representations to ensure
    deterministic signatures.  Signatures are produced in detached payload
    form (RFC 7797) and are expected to use modern algorithms such as ES256
    or EdDSA.
    """

    def __init__(self, key_provider: Any) -> None:
        self.key_provider = key_provider

    async def sign(self, message: CanonicalMessage) -> SignatureEnvelope:  # pragma: no cover - outline
        """Sign ``message`` and return the signature envelope."""
        raise NotImplementedError

    async def verify(self, envelope: SignatureEnvelope) -> bool:  # pragma: no cover
        """Verify the signature for the given ``envelope``."""
        raise NotImplementedError
