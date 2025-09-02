# Paigeant

**Durable, asynchronous workflows for distributed AI agents**

Paigeant is a developer tool that delivers developer delight and joy while working with asynchronous agents. It orchestrates independent `pydantic-ai` agents across service boundaries using message-driven workflows.

## Why Paigeant?

- 🕒 **Async-first communication** – All inter-agent calls flow through a message broker, decoupling services in time and space.
- 💾 **Durable execution** – Workflow state travels with the message, so crashed workers pick up exactly where they left off.
- 🔐 **Zero-trust messaging** – Built-in OAuth 2.0 on-behalf-of tokens and JSON Web Signatures keep messages authentic and tamper-proof.
- 🗺️ **Routing slip pattern** – Every message carries its own itinerary and log for end-to-end visibility.
- 🧩 **Composable workflows** – Activities are small, testable functions or agents. When `can_edit_itinerary` is enabled, steps can be inserted at runtime.
- 🔌 **Pluggable transports** – Comes with in-memory and Redis transports. Implement `BaseTransport` to add your own broker.
- 🎯 **Developer ergonomics** – A FastAPI-style API, dependency injection, and a CLI make agent workflows a pleasure to build.

## Quick Start

Install with [uv](https://docs.astral.sh/uv/):

```bash
uv add paigeant
```

Or via pip:

```bash
pip install paigeant
```

### Define a workflow and dispatch it

```python
from paigeant import PaigeantAgent, WorkflowDispatcher, WorkflowDependencies, get_transport

dispatcher = WorkflowDispatcher()

# Two agents on the runway
extractor = PaigeantAgent(
    "anthropic:claude-3-5",
    dispatcher=dispatcher,
    deps_type=WorkflowDependencies,
)
writer = PaigeantAgent(
    "openrouter:gpt-4o-mini",
    dispatcher=dispatcher,
    deps_type=WorkflowDependencies,
    can_edit_itinerary=True,
)

# Helper agent registered but not on the runway
notifier = PaigeantAgent("notifier-agent", dispatcher=dispatcher, deps_type=WorkflowDependencies)

extractor.add_to_runway(prompt="Extract a joke topic", deps=WorkflowDependencies())
writer.add_to_runway(
    prompt="""
    Write a joke about the topic.
    After writing, call _edit_itinerary({"notifier-agent": "Send the joke to Slack"}).
    """,
    deps=WorkflowDependencies(),
)

# Dynamic agent invoked at runtime
notifier.register_activity(prompt="Post the joke to Slack", deps=WorkflowDependencies())

transport = get_transport()  # in-memory by default
correlation_id = await dispatcher.dispatch_workflow(transport)
```

Start a worker to process messages:

```bash
uv run paigeant execute <agent_name>
```

Inspect workflow status:

```bash
uv run paigeant workflows
uv run paigeant workflow <correlation_id>
```

## Core Concepts

- 🗺️ **Routing Slip** – ordered list of `ActivitySpec` items representing the remaining itinerary and logs of executed steps.
- ✉️ **PaigeantMessage** – the envelope exchanged over the broker containing the routing slip, payload, correlation ID, trace context, and optional security fields.
- 📮 **Transport** – abstracts the broker. Ships with in-memory and Redis implementations.
- 🤖 **PaigeantAgent** – lightweight wrapper around `pydantic_ai.Agent` that can access previous outputs and optionally edit the itinerary.
- 👷 **ActivityExecutor** – worker that subscribes to a queue, runs the agent, and forwards the message.

## Use Cases

- 🌐 **Distributed AI workflows** – Coordinate microservices or serverless functions without brittle RPC chains.
- ⏱️ **Long-running and resilient workflows** – Durable messaging ensures progress survives restarts or failures.
- 🔄 **Dynamic itineraries** – Agents can insert follow-up steps based on intermediate results or user input.
- 🤝 **Federated architectures** – Combine `pydantic-ai` and `pydantic-graph` for complex in-process logic while using Paigeant for cross-service orchestration.

## Known Limitations

- 📚 **Static activity discovery** – Activities must be known ahead of time; dynamic discovery is planned.
- 🚚 **Limited transport support** – Only in-memory and Redis transports exist today; RabbitMQ, Kafka, and others are on the roadmap.
- 🧪 **Experimental persistence** – The optional persistence layer for querying workflow state is still experimental.
- 🔁 **No built-in retry or compensation** – Robust retry semantics and Saga-style compensations are coming.
- ⛓️ **No parallel execution** – Workflows are sequential; scatter-gather patterns are planned.

## Roadmap

- 📇 **Dynamic registry and service discovery** – Central registry so agents can publish capabilities and planners can assemble workflows without pre-configuration.
- ↩️ **Robust retries and compensation** – Exponential backoff, dead-letter queues, and Saga-style rollback for resilience.
- 🧷 **Pluggable persistence and monitoring** – `SagaRepository` and UI for querying workflow state by correlation ID.
- 🕸️ **Parallel execution** – Scatter-gather patterns to run tasks concurrently with an aggregator step.
- 🌍 **Cross-language interoperability** – JSON Schema definitions for message and routing-slip formats to support TypeScript, .NET, Rust, and more.
- 👀 **Enhanced observability** – Built-in distributed tracing today; metrics and dashboards on the horizon.

## Contributing

Paigeant is open source under the MIT License. Contributions welcome!

- 🐞 Report bugs and request features via GitHub Issues.
- 🔧 Submit PRs with new transports, registry improvements, or examples.
- 📖 Check the design docs for deeper architectural insights.

## License

MIT

