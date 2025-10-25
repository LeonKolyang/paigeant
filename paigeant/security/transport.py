"""Transport-level security configuration."""

from __future__ import annotations

from typing import Any


class TransportSecurity:
    """Configures TLS, mTLS or SASL settings for transports."""

    async def configure(self, transport: Any) -> None:  # pragma: no cover - outline
        """Apply security configuration to ``transport``."""
        raise NotImplementedError
