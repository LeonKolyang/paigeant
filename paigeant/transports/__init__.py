"""Transport factory and initialization."""

from __future__ import annotations

import os
from typing import Optional

from .base import BaseTransport
from .inmemory import InMemoryTransport
from .rabbitmq import RabbitMQTransport


def get_transport(backend: Optional[str] = None) -> BaseTransport:
    """Factory function to get the configured transport."""
    backend = (
        os.getenv("PAIGEANT_TRANSPORT", "inmemory").lower()
        if not backend
        else backend.lower()
    )

    if backend == "inmemory":
        return InMemoryTransport()
    elif backend == "redis":
        from .redis import RedisTransport

        return RedisTransport(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
        )
    elif backend in {"rabbit", "rabbitmq"}:
        from .rabbitmq import RabbitMQTransport

        return RabbitMQTransport(url=os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/"))
    else:
        raise ValueError(f"Unsupported transport backend: {backend}")


__all__ = ["BaseTransport", "InMemoryTransport", "RabbitMQTransport", "get_transport"]
