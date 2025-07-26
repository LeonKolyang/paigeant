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
    else:
        raise ValueError(f"Unsupported transport backend: {backend}")


__all__ = ["BaseTransport", "InMemoryTransport", "get_transport"]
