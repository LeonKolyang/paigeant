# Paigeant

Durable workflow orchestration for AI agents.

## Overview

Paigeant provides the messaging infrastructure to connect multiple AI agents into resilient, distributed workflows. It's designed to complement frameworks like pydantic-ai by handling the cross-service orchestration layer.

## Key Features

- **Asynchronous messaging** - All inter-agent communication is async-first
- **Durable execution** - Workflows survive crashes and restarts
- **Pluggable transports** - Support for in-memory, RabbitMQ, Redis Streams
- **Routing slip pattern** - Workflow logic travels with the message
- **Security-ready** - Built-in support for on-behalf-of tokens and signatures

## Quick Start

### Basic Workflow Dispatch

```python
import asyncio
from paigeant import ActivitySpec, WorkflowDispatcher, get_transport

async def main():
    transport = get_transport()
    await transport.connect()
    
    dispatcher = WorkflowDispatcher(transport)
    
    activities = [
        ActivitySpec(name="validate-input"),
        ActivitySpec(name="create-account"),
        ActivitySpec(name="send-notification")
    ]
    
    correlation_id = await dispatcher.dispatch_workflow(activities)
    print(f"Workflow dispatched: {correlation_id}")
    
    await transport.disconnect()

asyncio.run(main())
```

### With pydantic-ai Integration

```python
from paigeant import create_planner_agent, PlannerAgentDeps, WorkflowDispatcher, get_transport

# Setup
transport = get_transport()
dispatcher = WorkflowDispatcher(transport)
deps = PlannerAgentDeps(workflow_dispatcher=dispatcher)

# Create agent
agent = create_planner_agent()

# Run agent - it can dispatch workflows via tools
result = await agent.run(
    "Create a customer onboarding workflow",
    deps=deps
)
```

## Architecture

Paigeant follows a federated architecture:

- **Task Layer** (pydantic-ai): In-process agent execution
- **Workflow Layer** (paigeant): Cross-service message orchestration

Messages carry their own routing slip, eliminating the need for centralized orchestrators while maintaining workflow visibility.

## Installation

```bash
uv add paigeant
```

For development:

```bash
git clone https://github.com/your-org/paigeant
cd paigeant
uv pip install -e .
```

## Testing

```bash
uv run pytest tests/ -v
```

## Configuration

Set transport via environment variable:

```bash
export PAIGEANT_TRANSPORT=inmemory  # default
export PAIGEANT_TRANSPORT=rabbitmq
export PAIGEANT_TRANSPORT=redis
```

## Status

🚧 **Early Development** - This is Feature 1 (Transport Layer) of the paigeant roadmap.

Coming next:
- Routing slip execution engine
- Worker runtime
- RabbitMQ and Redis transports
- State store integration
