"""Transport factory and initialization."""

from __future__ import annotations

import os

from .base import BaseTransport
from .inmemory import InMemoryTransport

try:
    from .kafka import KafkaTransport
except Exception:
    KafkaTransport = None  # type: ignore


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
    elif backend == "kafka":
        if KafkaTransport is None:
            raise ImportError("aiokafka package is required for KafkaTransport")
        return KafkaTransport(
            brokers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            group_id=os.getenv("KAFKA_GROUP_ID", "paigeant"),
        )
    else:
        raise ValueError(f"Unsupported transport backend: {backend}")


__all__ = ["BaseTransport", "InMemoryTransport", "KafkaTransport", "get_transport"]
