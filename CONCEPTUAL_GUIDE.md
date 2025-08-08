# Paigeant: Conceptual Guide

Paigeant provides durable workflow orchestration for AI agents. It converts fragile chains of direct calls into message-driven workflows that survive crashes and restarts.

## Problem
Synchronous agent calls like `Agent A -> Agent B -> Agent C` fail if any agent is unavailable.

## Solution
Paigeant moves workflow state into messages and delivers each step through a transport queue:

`Agent A -> queue -> Agent B -> queue -> Agent C`

If an agent crashes, the message stays in the queue until a worker handles it.

## Core Components
- **Routing Slip** – ordered list of `ActivitySpec` items. Tracks executed steps.
- **PaigeantMessage** – envelope containing routing slip, payload, and correlation metadata.
- **Transport** – delivers messages. The library ships with in-memory and Redis implementations.
- **WorkflowDispatcher** – builds a routing slip and publishes the initial message.
- **ActivityExecutor** – worker that subscribes to a topic, runs the agent, and forwards the message.
- **PaigeantAgent** – thin wrapper around `pydantic_ai.Agent` with optional itinerary editing and access to previous outputs.

## Architectural Principles
1. **Asynchronous communication** – every step is delivered over the transport.
2. **Durable execution** – workflow state lives in the message; workers can crash without losing progress.
3. **Composability** – activities are small Python functions or agents; additional steps can be inserted at runtime when `can_edit_itinerary` is enabled.

## Basic Usage

```python
from paigeant import PaigeantAgent, WorkflowDispatcher, get_transport, ActivityExecutor, WorkflowDependencies

dispatcher = WorkflowDispatcher()
agent = PaigeantAgent("anthropic:claude-3-5", dispatcher=dispatcher, deps_type=WorkflowDependencies)
agent.add_to_runway(prompt="do work", deps=WorkflowDependencies())

transport = get_transport()          # inmemory or redis
correlation_id = await dispatcher.dispatch_workflow(transport)

executor = ActivityExecutor(transport, "agent", "module.path")
await executor.start()
```

## When to Use
Paigeant is useful when workflows span multiple services or may run for minutes or hours. It is unnecessary for single-process, low-latency tasks.
