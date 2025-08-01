"""RabbitMQ transport for paigeant messaging."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional, Tuple

import aio_pika

from ..contracts import PaigeantMessage
from .base import BaseTransport


class RabbitMQTransport(BaseTransport[aio_pika.IncomingMessage]):
    """AMQP transport implementation using RabbitMQ via aio-pika."""

    def __init__(self, url: str = "amqp://guest:guest@localhost/") -> None:
        self.url = url
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None

    async def connect(self) -> None:
        if not self._connection:
            self._connection = await aio_pika.connect_robust(self.url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=1)

    async def disconnect(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None

    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        if not self._channel:
            await self.connect()
        assert self._channel
        await self._channel.declare_queue(topic, durable=True)
        body = message.to_json().encode("utf-8")
        await self._channel.default_exchange.publish(
            aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=topic,
        )

    async def subscribe(
        self, topic: str, timeout: Optional[float] = None
    ) -> AsyncIterator[Tuple[aio_pika.IncomingMessage, PaigeantMessage]]:
        if not self._channel:
            await self.connect()
        assert self._channel
        queue = await self._channel.declare_queue(topic, durable=True)
        start_time = asyncio.get_event_loop().time() if timeout else None
        while True:
            if timeout and start_time is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    break
            try:
                msg: aio_pika.IncomingMessage = await queue.get(timeout=1)
            except asyncio.TimeoutError:
                continue
            if msg is None:
                continue
            try:
                paige_msg = PaigeantMessage.from_json(msg.body.decode("utf-8"))
            except Exception:
                await msg.reject(requeue=False)
                continue
            yield msg, paige_msg

    async def ack(self, raw_message: aio_pika.IncomingMessage) -> None:
        raw_message.ack()

    async def nack(self, raw_message: aio_pika.IncomingMessage, requeue: bool = True) -> None:
        raw_message.reject(requeue=requeue)

