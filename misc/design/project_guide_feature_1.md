Sure, here’s the complete document in Markdown, including the context, transport layer design, pydantic‑AI integration, and a code outline for the `WorkflowDispatcher`:

---

# Paigeant Feature 1 – Transport Layer & Pydantic‑AI Integration

This handover brief is intended for a coding assistant in your IDE. It summarises the rationale and implementation tasks for **Feature 1 (Transport Layer)** and outlines how this layer integrates with the **pydantic‑AI** agent framework.

## 1. Project context

* **paigeant** orchestrates durable, multi‑agent workflows. It separates the **Task Layer** (pydantic‑AI agents run inside a single process) from the **Workflow Layer** (distributed execution via message queues). Dispatching a workflow is an explicit boundary crossing.
* **pydantic‑AI** is the agent framework used in the Task Layer. Agents run large language models (LLMs), register tools, and support dependency injection via dataclass‑based contexts.
* **Asynchronous messaging is mandatory.** LinkedIn discussions stress that agent‑to‑agent calls must go through durable queues/streams rather than synchronous RPC, and messages require on‑behalf‑of tokens and signatures for delegated authority.

## 2. Transport Layer

### Objectives

1. Abstract the broker details behind a `BaseTransport` interface.
2. Support RabbitMQ (`aio‑pika`), Redis Streams (`redis.asyncio`) and an in‑memory transport for tests.
3. Provide asynchronous `publish`, `subscribe`, `ack`/`nack` semantics.
4. Use a `PaigeantMessage` data model to carry message metadata, routing slip and payload.

### Key classes (simplified view)

* **PaigeantMessage** – Pydantic model containing:

  * `message_id` (unique per message), `correlation_id` (workflow ID), `trace_id`, `timestamp`, optional `obo_token` and `signature`, `routing_slip` (list of steps, executed steps, compensations), and `payload` (JSON data). Includes `to_json()`/`from_json()` helpers.
* **BaseTransport** – abstract class with async methods `connect`, `disconnect`, `publish(topic, message)`, `subscribe(topic) -> AsyncIterator`, `ack(raw_message)` and `nack(raw_message, requeue=True)`.
* **Concrete transports**:

  * *InMemoryTransport*: simple deque‑based queue for unit tests; no‑op `ack`.
  * *RabbitMQTransport*: uses `aio-pika`. Publishes persistent messages to a queue per topic and yields `AbstractIncomingMessage` objects for acknowledgement.
  * *RedisStreamTransport*: uses Redis Streams and consumer groups. Publishes with `XADD`, consumes with `XREADGROUP`, and acknowledges with `XACK`.

The environment variable `PAIGEANT_TRANSPORT` selects the transport (`inmemory`, `rabbitmq`, `redis`).

## 3. Integrating paigeant with pydantic‑AI

### How pydantic‑AI works

* An **Agent** encapsulates a model (e.g. `openai:gpt-4o`) and optionally a set of tools (callable functions). Tools are decorated functions annotated with input types; the LLM can call them during a run.
* **Dependency injection**: When you instantiate an agent, you specify a `deps_type` dataclass. On each run, you pass an instance of that dataclass via the `deps` argument. Inside tool functions, a `RunContext` object gives access to `ctx.deps` and `ctx.usage` (for usage accounting).
* Tools return results synchronously or asynchronously. The LLM decides when to call them based on their docstrings and the system prompt.

### WorkflowDispatcher integration

To dispatch a paigeant workflow from within a pydantic‑AI agent, you define a tool that wraps the `WorkflowDispatcher.dispatch_workflow()` method. The dispatcher takes a list of `ActivitySpec` objects and optional variables and obo token, builds a `PaigeantMessage` with a new correlation ID and routing slip, then publishes it to the configured transport.

#### Steps to implement

1. **Define dependencies** for the planner agent:

   ```python
   from dataclasses import dataclass
   from paigeant.dispatch import WorkflowDispatcher

   @dataclass
   class PlannerAgentDeps:
       workflow_dispatcher: WorkflowDispatcher
       user_obo_token: str | None = None
   ```

   The agent will receive an instance of `WorkflowDispatcher` and an optional on‑behalf‑of token.

2. **Create the agent** specifying `deps_type` and `output_type` if you want structured returns:

   ```python
   from pydantic_ai import Agent, RunContext

   planner_agent = Agent(
       model='openai:gpt-4o',
       deps_type=PlannerAgentDeps,
       system_prompt=("You are a master workflow planner. "
                      "Use the dispatch_workflow tool to start distributed workflows."),
   )
   ```

3. **Register the `dispatch_workflow` tool**:

   ```python
   from paigeant.contracts import ActivitySpec

   @planner_agent.tool
   async def dispatch_workflow(
       ctx: RunContext[PlannerAgentDeps],
       activities: list[ActivitySpec],
       variables: dict[str, Any] | None = None,
   ) -> str:
       """Construct and dispatch a new distributed workflow.
       Returns the correlation ID of the workflow."""
       dispatcher = ctx.deps.workflow_dispatcher
       obo_token = ctx.deps.user_obo_token
       correlation_id = await dispatcher.dispatch_workflow(
           activities=activities,
           variables=variables,
           obo_token=obo_token,
       )
       return correlation_id
   ```

   The docstring is crucial: it tells the LLM what this tool does. The LLM will call `dispatch_workflow` when it decides a distributed workflow is needed.

4. **Instantiate and run the agent**:

   ```python
   from paigeant.transports import get_transport
   from paigeant.dispatch import WorkflowDispatcher

   # Choose transport (defaults to InMemoryTransport for local development)
   transport = get_transport()
   dispatcher = WorkflowDispatcher(transport)

   deps = PlannerAgentDeps(workflow_dispatcher=dispatcher, user_obo_token="token123")

   # The prompt instructs the LLM to plan a multi‑step workflow
   result = await planner_agent.run(
       prompt="Onboard new customer 'cust-456' with order ORD-123.",
       deps=deps,
   )

   # The result.output will be the correlation ID of the dispatched workflow
   print("Correlation ID:", result.output)
   ```

5. **Downstream processing**: On the workflow side, a paigeant worker picks up the message from the transport, deserialises `PaigeantMessage`, and executes the current activity. This is implemented in later features (routing slip execution and worker runtime). The pydantic‑AI agent does not wait for the workflow’s completion—it simply receives the correlation ID and returns.

### Code outline for `WorkflowDispatcher`

The dispatcher class encapsulates the logic to build a routing slip, wrap it in a `PaigeantMessage` and publish it via the configured transport.  It returns the `correlation_id` used to identify the workflow.

```python
from typing import Iterable, Mapping, Any
import uuid
from paigeant.contracts import ActivitySpec, RoutingSlip, PaigeantMessage
from paigeant.transports import BaseTransport

class WorkflowDispatcher:
    """A service responsible for dispatching new workflows."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport

    async def dispatch_workflow(
        self,
        activities: Iterable[ActivitySpec],
        variables: Mapping[str, Any] | None = None,
        obo_token: str | None = None,
    ) -> str:
        """Construct and dispatch a workflow.

        Args:
            activities: Ordered iterable of activity specifications.
            variables: Optional dictionary of initial workflow variables.
            obo_token: Optional on‑behalf‑of token for identity propagation.

        Returns:
            The correlation ID for the dispatched workflow.
        """
        # Create a correlation ID for the workflow
        correlation_id = str(uuid.uuid4())
        # Build the routing slip: itinerary is the list of activity names
        routing_slip = RoutingSlip(itinerary=[spec.name for spec in activities])
        # Build the payload: include activity arguments and initial variables
        payload: dict[str, Any] = {
            "activities": [spec.model_dump() for spec in activities],
            "variables": dict(variables or {}),
        }
        # Assemble the message
        message = PaigeantMessage(
            correlation_id=correlation_id,
            routing_slip=routing_slip,
            payload=payload,
            obo_token=obo_token,
        )
        # Publish to a topic (e.g. a queue named "workflows")
        await self._transport.publish("workflows", message)
        return correlation_id
```

In a fuller implementation the dispatcher might use a dedicated `RoutingSlipBuilder` helper to add variables and sign the message, and choose the topic based on the first activity.  However, this outline shows the essential pattern: build the message, publish it via the injected transport, and return the correlation ID.

### Why this pattern

* It honours the architectural boundary between synchronous agent calls and asynchronous workflows.
* The LLM sees a clearly defined tool with an explicit return type (`str` correlation ID) rather than overloading `agent.run()` with hidden messaging semantics.
* Dependency injection enables easy testing: you can pass a mock `WorkflowDispatcher` to assert that the agent calls the tool with correct parameters.

## 4. Instructions for the coding assistant

When implementing this feature:

1. **Create or update the `paigeant` package** with the transport code and message contracts outlined above.
2. **Implement `WorkflowDispatcher`** (not shown here) to build a `RoutingSlip`, create a `PaigeantMessage`, and call `transport.publish()` with an appropriate topic name (e.g. `"workflows"`). Return the `correlation_id` to the caller.
3. **Write pydantic‑AI integration code** similar to the planner example above. Ensure the tool’s signature uses `RunContext` and the dependencies dataclass.
4. **Ensure docstrings** of tools are succinct and descriptive so the LLM understands when to call them.
5. **Test locally** with the in‑memory transport. Simulate a multi‑step workflow by creating a dummy worker that consumes messages from the in‑memory queue.
6. **Later features** (routing slip execution, worker runtime, state store, CLI, observability, security) will build on this foundation, but the transport layer and dispatcher/agent integration are the critical first pieces.

With these guidelines, the coding assistant should be able to implement the transport layer and integrate paigeant with pydantic‑AI seamlessly.


Here are more implementation details:
Thanks for providing additional documents and PDFs. I’ll incorporate these materials into the review of the design and code for the first feature (Transport Layer). I'll analyze them alongside the previously given materials and proceed with necessary research and assessments.


After reviewing the LinkedIn discussions, the design documents (notably the “Agent Messaging Implementation Strategies” report and the revised design document), and your experimental code, I’ve distilled the key principles behind **paigeant** and examined Feature 1 (Transport Layer) against those principles. Below is a summary of the analysis, identification of any gaps/contradictions, and a proposed implementation that follows messaging best‑practices.

---

### 1. What the documents & discussions convey

* **Asynchronous-first and durable messaging** – Both LinkedIn posts emphasise that agent‑to‑agent interactions must move away from synchronous RPC patterns. Long‑running tasks and unreliable connections in cloud environments make a queue/stream imperative. Durable queues (e.g., AMQP/Kafka/Redis Streams) ensure work isn’t lost when intermediate services restart.
* **Clean separation of Task vs. Workflow layers** – The paigeant design argues that a pydantic‑ai agent should never mask a network call as a synchronous function. Instead, dispatching a workflow via a tool clearly signals the boundary crossing.
* **Pluggable transport layer** – The revised design document calls for an abstract transport interface with concrete implementations for RabbitMQ, Redis Streams and an in‑memory queue. This keeps workflow code independent of the broker.
* **Universal message contract** – Messages must carry a correlation ID (returned to the caller), a unique message ID for idempotency, a routing slip, optional on‑behalf‑of token and signature, and trace context. This enables idempotent processing, security and observability.
* **Zero‑trust & delegated authority** – LinkedIn discussion #2 notes the need for message‑level authorisation and an on‑behalf‑of model, which informs the `obo_token` and `signature` fields in the message headers.

### 2. Observations & recommended adjustments

1. **Transport interface differences** – The project guide’s interface (`publish`, `subscribe`, `ack`) omits `connect`/`disconnect`, whereas the design document expects connection management. Including `connect` and `disconnect` clarifies lifecycle management and mirrors common messaging libraries.
2. **In‑memory transport for testing** – The design document specifies an `InMemoryTransport` for tests, which is missing from the project guide. Adding this makes unit tests easy without a real broker.
3. **Use Redis Streams rather than pub/sub** – The experimental code uses Redis pub/sub for demo purposes, but pub/sub offers no durability. Redis Streams provide at‑least‑once delivery and message acknowledgements, aligning with paigeant’s durability goal.
4. **Message contract** – The project guide loosely mentions a `PaigeantMessage` with headers and payload. Based on the design docs, it should explicitly include `message_id`, `correlation_id`, `trace_id`, `routing_slip`, `payload`, `timestamp`, `obo_token` and `signature`. Using a Pydantic model for this contract ensures validation and versioning.
5. **Acknowledgement semantics** – RabbitMQ and Redis Streams handle acknowledgements differently. The interface should provide `ack` and optionally `nack` with a `requeue` flag. In-memory transport can ignore acknowledgements.

### 3. Implementation of Feature 1 (Transport Layer)

Below is a proposed Python implementation that realises Feature 1 while adhering to the above guidelines. It defines a universal `PaigeantMessage` and transport interface, and implements three transports: in-memory (for tests), RabbitMQ (via `aio-pika`), and Redis Streams (via `redis.asyncio`). The transports are selected at runtime via an environment variable.

```python
# paigeant/contracts.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ActivitySpec(BaseModel):
    """Defines one step in a workflow."""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class RoutingSlip(BaseModel):
    """Describes remaining, executed and compensating activities."""
    itinerary: List[str] = Field(default_factory=list)
    executed: List[str] = Field(default_factory=list)
    compensations: List[str] = Field(default_factory=list)

    def next_step(self) -> Optional[str]:
        return self.itinerary[0] if self.itinerary else None

    def mark_complete(self) -> None:
        if self.itinerary:
            self.executed.append(self.itinerary.pop(0))

class PaigeantMessage(BaseModel):
    """
    Envelope exchanged over the bus. Includes metadata, routing slip and payload.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    obo_token: Optional[str] = None
    signature: Optional[str] = None
    routing_slip: RoutingSlip
    payload: Dict[str, Any] = Field(default_factory=dict)
    spec_version: str = "1.0"

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "PaigeantMessage":
        return cls.model_validate_json(data)
```

```python
# paigeant/transports/base.py
from __future__ import annotations
import abc
from typing import Any, AsyncIterator, Generic, Tuple, TypeVar
from ..contracts import PaigeantMessage

RawMessageT = TypeVar("RawMessageT")

class BaseTransport(Generic[RawMessageT], metaclass=abc.ABCMeta):
    async def connect(self) -> None:
        """Open connection to broker (no-op by default)."""
        return None

    async def disconnect(self) -> None:
        """Close connection to broker (no-op by default)."""
        return None

    @abc.abstractmethod
    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        """Send a message to a topic/queue."""
        raise NotImplementedError

    @abc.abstractmethod
    async def subscribe(self, topic: str) -> AsyncIterator[Tuple[RawMessageT, PaigeantMessage]]:
        """Yield raw transport message and PaigeantMessage pairs."""
        raise NotImplementedError

    @abc.abstractmethod
    async def ack(self, raw_message: RawMessageT) -> None:
        """Acknowledge successful processing."""
        raise NotImplementedError

    async def nack(self, raw_message: RawMessageT, requeue: bool = True) -> None:
        """Negatively acknowledge (default to ack if unsupported)."""
        await self.ack(raw_message)
```

```python
# paigeant/transports/inmemory.py
from __future__ import annotations
import asyncio
from collections import defaultdict, deque
from typing import AsyncIterator, Deque, Dict, Tuple
from ..contracts import PaigeantMessage
from .base import BaseTransport

class InMemoryTransport(BaseTransport[Tuple[str, PaigeantMessage]]):
    """
    Simple in‑process queue for unit tests.
    """
    def __init__(self) -> None:
        self._queues: Dict[str, Deque[Tuple[str, PaigeantMessage]]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        raw = (message.to_json(), message)
        async with self._lock:
            self._queues[topic].append(raw)

    async def subscribe(self, topic: str) -> AsyncIterator[Tuple[Tuple[str, PaigeantMessage], PaigeantMessage]]:
        while True:
            async with self._lock:
                raw_message = self._queues[topic].popleft() if self._queues[topic] else None
            if raw_message is None:
                await asyncio.sleep(0.1)
                continue
            yield raw_message, raw_message[1]

    async def ack(self, raw_message: Tuple[str, PaigeantMessage]) -> None:
        return None
```

```python
# paigeant/transports/rabbitmq.py
from __future__ import annotations
import json
import logging
from typing import AsyncIterator, Tuple
import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from ..contracts import PaigeantMessage
from .base import BaseTransport

logger = logging.getLogger(__name__)

class RabbitMQTransport(BaseTransport[AbstractIncomingMessage]):
    """
    AMQP transport backed by RabbitMQ/aio‑pika.
    """
    def __init__(self, dsn: str | None = None) -> None:
        import os
        self._dsn = dsn or os.getenv("RABBITMQ_DSN", "amqp://guest:guest@localhost/")
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return
        self._connection = await aio_pika.connect_robust(self._dsn)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)

    async def disconnect(self) -> None:
        if self._channel:
            await self._channel.close()
            self._channel = None
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        if not self._channel:
            await self.connect()
        assert self._channel is not None
        body = message.to_json().encode("utf-8")
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                correlation_id=message.correlation_id,
                message_id=message.message_id,
            ),
            routing_key=topic,
        )

    async def subscribe(self, topic: str) -> AsyncIterator[Tuple[AbstractIncomingMessage, PaigeantMessage]]:
        if not self._channel:
            await self.connect()
        assert self._channel is not None
        queue = await self._channel.declare_queue(name=topic, durable=True)
        async with queue.iterator() as queue_iter:
            async for incoming in queue_iter:
                try:
                    msg_obj = PaigeantMessage.from_json(incoming.body.decode("utf-8"))
                except json.JSONDecodeError:
                    await incoming.reject(requeue=False)
                    continue
                yield incoming, msg_obj

    async def ack(self, raw_message: AbstractIncomingMessage) -> None:
        await raw_message.ack()

    async def nack(self, raw_message: AbstractIncomingMessage, requeue: bool = True) -> None:
        await raw_message.reject(requeue=requeue)
```

```python
# paigeant/transports/redis_stream.py
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from typing import AsyncIterator, Optional, Tuple
import redis.asyncio as aioredis
from ..contracts import PaigeantMessage
from .base import BaseTransport

logger = logging.getLogger(__name__)

class RedisStreamTransport(BaseTransport[Tuple[str, str]]):
    """
    Transport backed by Redis Streams (requires redis.asyncio).
    """
    def __init__(self, url: Optional[str] = None) -> None:
        import os
        self._url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        if not self._redis:
            self._redis = aioredis.from_url(self._url, decode_responses=True)

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def publish(self, topic: str, message: PaigeantMessage) -> None:
        if not self._redis:
            await self.connect()
        assert self._redis is not None
        await self._redis.xadd(topic, {"data": message.to_json()}, id="*")

    async def subscribe(self, topic: str) -> AsyncIterator[Tuple[Tuple[str, str], PaigeantMessage]]:
        if not self._redis:
            await self.connect()
        assert self._redis is not None
        group = f"{topic}-group"
        consumer = str(uuid.uuid4())
        # Create group if missing
        try:
            await self._redis.xgroup_create(name=topic, groupname=group, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
        while True:
            entries = await self._redis.xreadgroup(group, consumer, {topic: ">"}, count=1, block=1000)
            if not entries:
                continue
            for stream_name, messages in entries:
                for message_id, fields in messages:
                    data = fields.get("data")
                    if not data:
                        await self._redis.xack(topic, group, message_id)
                        continue
                    try:
                        msg_obj = PaigeantMessage.from_json(data)
                    except json.JSONDecodeError:
                        await self._redis.xack(topic, group, message_id)
                        continue
                    yield (stream_name, message_id), msg_obj

    async def ack(self, raw_message: Tuple[str, str]) -> None:
        if not self._redis:
            await self.connect()
        assert self._redis is not None
        stream_name, message_id = raw_message
        group = f"{stream_name}-group"
        await self._redis.xack(stream_name, group, message_id)

    async def nack(self, raw_message: Tuple[str, str], requeue: bool = True) -> None:
        stream_name, message_id = raw_message
        await self.ack(raw_message)
        if requeue:
            if not self._redis:
                await self.connect()
            assert self._redis is not None
            result = await self._redis.xrange(stream_name, min=message_id, max=message_id, count=1)
            if result:
                _, fields = result[0]
                data = fields.get("data")
                if data:
                    await self._redis.xadd(stream_name, {"data": data}, id="*")
```

```python
# paigeant/transports/__init__.py
"""
Transport backends for paigeant. The factory get_transport() reads
PAIGEANT_TRANSPORT to pick between 'inmemory', 'rabbitmq' and 'redis'.
"""
from __future__ import annotations
import os
from .base import BaseTransport
from .inmemory import InMemoryTransport

try:
    from .rabbitmq import RabbitMQTransport  # noqa
except Exception:
    RabbitMQTransport = None  # type: ignore

try:
    from .redis_stream import RedisStreamTransport  # noqa
except Exception:
    RedisStreamTransport = None  # type: ignore

def get_transport() -> BaseTransport:
    backend = os.getenv("PAIGEANT_TRANSPORT", "inmemory").lower()
    if backend == "rabbitmq":
        if RabbitMQTransport is None:
            raise ImportError("aio-pika must be installed for RabbitMQ support")
        return RabbitMQTransport()  # type: ignore
    if backend == "redis":
        if RedisStreamTransport is None:
            raise ImportError("redis.asyncio must be installed for Redis Streams support")
        return RedisStreamTransport()  # type: ignore
    return InMemoryTransport()
```

### 4. How this aligns with the initial discussions

* **Message-driven agent orchestration**: The transport layer abstracts away the broker details, making it straightforward to route tasks through RabbitMQ or Redis Streams, exactly as Clemens Vasters suggested when he noted that long-running agent calls need to “run behind a queue/stream”.
* **Security & delegated authority**: The `PaigeantMessage` includes an `obo_token` and optional `signature`, addressing the call for message‑level authorisation in the LinkedIn conversation.
* **Clean API boundary**: By surfacing dispatching through a dedicated tool and message contract, we maintain the clear separation between synchronous task execution and asynchronous workflow orchestration that the design documents advocate.

With these components in place, the first feature (Transport Layer) is ready for integration into the rest of the paigeant framework. Subsequent features—routing slip execution, state storage, worker runtime, CLI, observability, and security—can now build upon this foundation.
