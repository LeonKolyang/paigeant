"""Transport factory and initialization."""

from __future__ import annotations

import os
from typing import Optional

from ..config import PaigeantConfig, load_config
from .base import BaseTransport
from .inmemory import InMemoryTransport


def get_transport(
    backend: Optional[str] = None, config: Optional[PaigeantConfig] = None
) -> BaseTransport:
    """Factory function to get the configured transport."""

    config = config or load_config()
    backend = (
        backend
        or os.getenv("PAIGEANT_TRANSPORT")
        or config.transport.backend
    ).lower()

    if backend == "inmemory":
        return InMemoryTransport()
    elif backend == "redis":
        from .redis import RedisTransport

        redis_conf = config.transport.redis
        return RedisTransport(
            host=redis_conf.host,
            port=redis_conf.port,
            db=redis_conf.db,
            password=redis_conf.password,
        )
    else:
        raise ValueError(f"Unsupported transport backend: {backend}")


__all__ = ["BaseTransport", "InMemoryTransport", "get_transport"]
