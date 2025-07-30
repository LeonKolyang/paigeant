"""Redis transport for cross-process messaging."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Optional, Tuple

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from ..contracts import PaigeantMessage
from .base import BaseTransport


class RedisTransport(BaseTransport[str]):
    """Redis-based transport for distributed messaging."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
    ) -> None:
        if redis is None:
            raise ImportError("redis package is required for RedisTransport")

        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._redis: Optional[Any] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,
        )
        # Test connection
        await self._redis.ping()

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        """Publish message to Redis list (acting as queue)."""
        if not self._redis:
            await self.connect()

        queue_name = f"paigeant:{topic}"
        message_json = message.to_json()
        await self._redis.lpush(queue_name, message_json)

    async def subscribe(
        self, topic: str, timeout: Optional[float] = None
    ) -> AsyncIterator[Tuple[str, PaigeantMessage]]:
        """Subscribe to messages from Redis queue."""
        if not self._redis:
            await self.connect()

        queue_name = f"paigeant:{topic}"
        start_time = asyncio.get_event_loop().time() if timeout else None

        while True:
            # Check timeout if specified
            if timeout and start_time:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    break

            # Blocking pop with timeout
            result = await self._redis.brpop(queue_name, timeout=1)

            if result:
                _, message_json = result
                try:
                    message_data = json.loads(message_json)
                    message = PaigeantMessage.model_validate(message_data)
                    yield message_json, message
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Failed to parse message: {e}")
                    continue

            # Brief sleep to prevent busy waiting when no messages
            await asyncio.sleep(0.01)

    async def ack(self, raw_message: str) -> None:
        """No-op acknowledgment for Redis transport (message already consumed)."""
        pass
