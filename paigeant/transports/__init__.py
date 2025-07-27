"""Transport factory and initialization."""

from __future__ import annotations

import os

from .base import BaseTransport
from .inmemory import InMemoryTransport


def get_transport() -> BaseTransport:
    """Factory function to get the configured transport."""
    backend = os.getenv("PAIGEANT_TRANSPORT", "inmemory").lower()

    if backend == "inmemory":
        return InMemoryTransport()
    elif backend == "redis":
        from .redis import RedisTransport

        return RedisTransport(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
        )
    else:
        raise ValueError(f"Unsupported transport backend: {backend}")


__all__ = ["BaseTransport", "InMemoryTransport", "get_transport"]
