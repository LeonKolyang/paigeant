# Paigeant

Durable workflow orchestration for AI agents.

Paigeant lets independent `pydantic-ai` agents coordinate through a message queue. Each workflow step is delivered as a message that carries its own routing slip and payload, allowing execution to resume after crashes or deployments.

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
- **PaigeantAgent** – thin wrapper around `pydantic_ai.Agent` with optional itinerary editing and access to previous outputs.
- **ActivityExecutor** – worker that subscribes to a topic, runs the agent, and forwards the message.

## Architectural Principles
1. **Asynchronous communication** – every step is delivered over the transport.
2. **Durable execution** – workflow state lives in the message; workers can crash without losing progress.
3. **Composability** – activities are small Python functions or agents; additional steps can be inserted at runtime when `can_edit_itinerary` is enabled.

## Features
- Asynchronous, message-driven workflows
- Routing slip model with previous-output injection
- Optional itinerary editing: agents can insert additional steps
- Transport abstraction with in-memory and Redis backends
- Minimal dependencies and `pydantic-ai` integration

## Quick Start

```bash
uv add paigeant
```

### Define and dispatch a workflow
Use `WorkflowDispatcher` to build the routing slip and `PaigeantAgent` to register activities. Dispatch the workflow to your chosen transport:

```python
from paigeant import PaigeantAgent, WorkflowDispatcher, get_transport, WorkflowDependencies

dispatcher = WorkflowDispatcher()
agent = PaigeantAgent("anthropic:claude-3-5", dispatcher=dispatcher, deps_type=WorkflowDependencies)
agent.add_to_runway(prompt="do work", deps=WorkflowDependencies())

transport = get_transport()  # in-memory by default, configurable via PAIGEANT_TRANSPORT or config.yaml
correlation_id = await dispatcher.dispatch_workflow(transport)
```

### Run a worker
An `ActivityExecutor` pulls messages from the transport and executes the agent's activity. Start one using the CLI:

```bash
uv run paigeant execute agent my.module
```

## Transports
The library currently supports in-memory queues for testing and Redis lists for cross-process messaging. Other brokers can be added by implementing `BaseTransport`.

## Development
```bash
uv pip install -e .[test]
uv run pytest -q
```

## Project Status
Early development. Implemented components: message contracts, workflow dispatcher, activity executor, `PaigeantAgent`, in-memory transport, Redis transport.

## License
MIT

