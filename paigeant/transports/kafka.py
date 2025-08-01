"""Kafka transport implementation using aiokafka."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Iterable, Optional, Tuple

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from aiokafka.structs import TopicPartition
except Exception:  # pragma: no cover - aiokafka not installed
    AIOKafkaConsumer = None  # type: ignore
    AIOKafkaProducer = None  # type: ignore
    TopicPartition = None  # type: ignore

from ..contracts import PaigeantMessage
from .base import BaseTransport


class KafkaTransport(BaseTransport[Any]):
    """Kafka-based transport for distributed messaging."""

    def __init__(
        self,
        brokers: Iterable[str] | str = "localhost:9092",
        group_id: str = "paigeant",
        dlq_topic: str = "paigeant.deadletter",
    ) -> None:
        if AIOKafkaProducer is None or AIOKafkaConsumer is None:
            raise ImportError("aiokafka package is required for KafkaTransport")

        self.brokers = list(brokers) if isinstance(brokers, Iterable) and not isinstance(brokers, str) else [brokers]  # type: ignore[arg-type]
        self.group_id = group_id
        self.dlq_topic = dlq_topic
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumer: Optional[AIOKafkaConsumer] = None

    async def connect(self) -> None:
        self._producer = AIOKafkaProducer(bootstrap_servers=self.brokers)
        self._consumer = AIOKafkaConsumer(
            bootstrap_servers=self.brokers,
            group_id=self.group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        await self._producer.start()
        await self._consumer.start()

    async def disconnect(self) -> None:
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        if not self._producer:
            raise RuntimeError("KafkaTransport not connected")
        data = message.to_json().encode()
        await self._producer.send_and_wait(topic, value=data)

    async def subscribe(
        self, topic: str, timeout: Optional[float] = None
    ) -> AsyncIterator[Tuple[Any, PaigeantMessage]]:
        if not self._consumer:
            raise RuntimeError("KafkaTransport not connected")
        self._consumer.subscribe([topic])
        start_time = asyncio.get_event_loop().time() if timeout else None

        while True:
            if timeout and start_time is not None:
                if asyncio.get_event_loop().time() - start_time >= timeout:
                    break
            msg = await self._consumer.getone()
            try:
                envelope = PaigeantMessage.from_json(msg.value.decode())
            except Exception:
                await self.nack(msg, requeue=False)
                continue
            yield msg, envelope

    async def ack(self, raw_message: Any) -> None:
        if not self._consumer:
            raise RuntimeError("KafkaTransport not connected")
        tp = TopicPartition(raw_message.topic, raw_message.partition)
        await self._consumer.commit({tp: raw_message.offset + 1})

    async def nack(self, raw_message: Any, requeue: bool = True) -> None:
        if not self._consumer:
            raise RuntimeError("KafkaTransport not connected")
        if requeue:
            tp = TopicPartition(raw_message.topic, raw_message.partition)
            await self._consumer.seek(tp, raw_message.offset)
        else:
            if self._producer:
                await self._producer.send_and_wait(self.dlq_topic, value=raw_message.value)
            await self.ack(raw_message)
