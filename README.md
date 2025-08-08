# Paigeant

Durable workflow orchestration for AI agents.

Paigeant lets independent `pydantic-ai` agents coordinate through a message queue. Each workflow step is delivered as a message that carries its own routing slip and payload, allowing execution to resume after crashes or deployments.

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

Define and dispatch a workflow:

```python
from paigeant import PaigeantAgent, WorkflowDispatcher, get_transport, WorkflowDependencies

dispatcher = WorkflowDispatcher()
agent = PaigeantAgent("anthropic:claude-3-5", dispatcher=dispatcher, deps_type=WorkflowDependencies)
agent.add_to_runway(prompt="do work", deps=WorkflowDependencies())

transport = get_transport()          # inmemory by default or PAIGEANT_TRANSPORT=redis
correlation_id = await dispatcher.dispatch_workflow(transport)
```

Run a worker:

```python
from paigeant import ActivityExecutor

executor = ActivityExecutor(transport, "agent", "my.module")
await executor.start()
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
