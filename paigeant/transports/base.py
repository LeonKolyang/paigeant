"""Base transport interface for paigeant messaging."""

from __future__ import annotations

import abc
from typing import AsyncIterator, Generic, Optional, Tuple, TypeVar

from ..contracts import PaigeantMessage

RawMessageT = TypeVar("RawMessageT")


class BaseTransport(Generic[RawMessageT], metaclass=abc.ABCMeta):
    """Abstract base transport for message brokers."""

    async def connect(self) -> None:
        """Open connection to broker (no-op by default)."""
        pass

    async def disconnect(self) -> None:
        """Close connection to broker (no-op by default)."""
        pass

    @abc.abstractmethod
    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        """Send a message to a topic/queue."""
        raise NotImplementedError

    @abc.abstractmethod
    async def subscribe(
        self, topic: str, lifespan: Optional[float] = None
    ) -> AsyncIterator[Tuple[RawMessageT, PaigeantMessage]]:
        """Yield raw transport message and PaigeantMessage pairs.

        Args:
            topic: The topic to subscribe to
            lifespan: Maximum time in seconds to keep connection open. If None, runs indefinitely.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def ack(self, raw_message: RawMessageT) -> None:
        """Acknowledge successful processing."""
        raise NotImplementedError

    async def nack(self, raw_message: RawMessageT, requeue: bool = True) -> None:
        """Negatively acknowledge (default to ack if unsupported)."""
        await self.ack(raw_message)
