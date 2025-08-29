"""In-memory transport for testing."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import AsyncIterator, Deque, Dict, Optional, Tuple

from ..contracts import PaigeantMessage
from .base import BaseTransport


class InMemoryTransport(BaseTransport[Tuple[str, PaigeantMessage]]):
    """Simple in-process queue for unit tests."""

    def __init__(self) -> None:
        self._queues: Dict[str, Deque[Tuple[str, PaigeantMessage]]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        """Publish message to in-memory queue."""
        raw = (message.to_json(), message)
        async with self._lock:
            self._queues[topic].append(raw)

    async def subscribe(
        self, topic: str, lifespan: Optional[float] = None
    ) -> AsyncIterator[Tuple[Tuple[str, PaigeantMessage], PaigeantMessage]]:
        """Subscribe to messages from topic.

        Args:
            topic: The topic to subscribe to
            lifespan: Maximum time in seconds to keep connection open. If None, runs indefinitely.
        """
        start_time = asyncio.get_event_loop().time() if lifespan else None

        while True:
            if lifespan and start_time:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= lifespan:
                    break

            async with self._lock:
                if self._queues[topic]:
                    raw_message = self._queues[topic].popleft()
                    yield raw_message, raw_message[1]
                    continue

            await asyncio.sleep(0.1)

    async def ack(self, raw_message: Tuple[str, PaigeantMessage]) -> None:
        """No-op acknowledgment for in-memory transport."""
        pass
