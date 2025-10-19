# Paigeant

**Durable, asynchronous workflows for distributed AI agents**

Paigeant offers the runway for Pydantic AI agents dive into long running tasks, fail gracefully without crashing workflows, and dynamically make use of agents available in the environment. 

## What does Paigeant have to offer?

- 🕒 **Distributed runtime environments** – Execute each agent in it's own compute instance, enabling clear role assignments and strong fault isolation.
- 🌍 **Enhanced context** – Agents know about available agents and their capabilities and can add them dynamically to the workflow execution. 
- 💾 **Always a backup** – Workflow state travels with the message, making a single agent execution repeatable.
- 🔐 **Security as a first-class citizen** – Built-in OAuth 2.0 on-behalf-of tokens and JSON Web Signatures ensure that secrets stay between agents. Designated runtime environments allow for precise role assignment.
- 👯 **Self-guided choreography** – Workflow execution without an orchestrator, agents pass a routing slip around. This makes Paigeant a lightweight but yet powerful execution engine.
- 👠 **Flexible runway** – Agents can communicate with in-memory, Redis or RabbitMQ transport. The `BaseTransport` class allows to bring your own broker.
- 🎯 **Easy to manage** – A FastAPI-style API, dependency injection, and a CLI make it easy to define and deploy your workflow.

## Quick Start
> [!IMPORTANT]
> Pypi package is coming soon! For now:   
> Clone the repository, run `uv sync` and call `uv run paigeant` from the root of this project.

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
# joke_builder.py
from paigeant import PaigeantAgent, WorkflowDispatcher, WorkflowDependencies, get_transport    
from slack_sdk.web.async_client import AsyncWebClient

dispatcher = WorkflowDispatcher()

# PaigeantAgent is a subclass of pydantic AI's Agent, adding Paigeant's execution capabilities
# Two agents which will be out on the runway
extractor = PaigeantAgent(
    "anthropic:claude-3-5",
    output_type=str,
    deps_type=WorkflowDependencies,
    dispatcher=dispatcher,
    name="extractor"
)
writer = PaigeantAgent(
    "openrouter:gpt-4o-mini",
    output_type=str,
    deps_type=WorkflowDependencies,
    dispatcher=dispatcher,
    can_edit_itinerary=True,
    name="writer"
)

# Helper agent registered waiting backstage
notifier = PaigeantAgent(
    "openrouter:gpt-4o-mini",
    deps_type=WorkflowDependencies
    dispatcher=dispatcher, 
    name="notifier-agent", 
    )

@notifier.tool
async def send_joke_to_slack(ctx: RunContext[WorkflowDependencies]):
    client = AsyncWebClient(token=os.environ['SLACK_BOT_TOKEN'])
    await client.chat_postMessage(channel="team-dad-jokes", text=ctx.previous_output)

async def main():
    # Agents added to the workflow
    extractor.add_to_runway(prompt="Come up with a topic for a joke", deps=WorkflowDependencies())
    writer.add_to_runway(
        prompt="""
        Write a joke about the topic.
        If the joke is a dad joke, send it to slack with the notifier agent.
        Don't want to miss that.
        """,
        deps=WorkflowDependencies(),
    )

    # Agent registered as available activity for other agents
    notifier.register_activity(prompt="Post the joke to Slack", deps=WorkflowDependencies())

    # Trigger the workflow run to start the show
    transport = get_transport()  
    correlation_id = await dispatcher.dispatch_workflow(transport)
    print("Workflow with correlation id {correlation_id} kicked off.")

if __name__ == "__main__":
    asyncio.run(main())
```

Start a worker for each agent, for example on the same device or each in their own thread, process, deployment, etc:

```bash
uv run paigeant execute extractor
uv run paigeant execute writer
uv run paigeant execute notifier-agent
```

Trigger the workflow:
```bash
uv run python joke_builder.py
```

Inspect workflow status:

```bash
uv run paigeant workflows
uv run paigeant workflow <correlation_id>
```

Discover agents defined in your project:

```bash
uv run paigeant agent discover --path ./guides
# Include files matched by .gitignore entries
uv run paigeant agent discover --path ./guides --no-respect-gitignore
```

## Core Concepts

- 🤖 **PaigeantAgent** – lightweight wrapper around `pydantic_ai.Agent` that can access previous outputs and optionally edit the itinerary.
- 🗺️ **Routing Slip** – ordered list of `ActivitySpec` items representing the remaining itinerary and logs of executed steps.
- ✉️ **PaigeantMessage** – the envelope exchanged over the broker containing the routing slip, payload, correlation ID, trace context, and optional security fields.
- 📮 **Transport** – abstracts the broker. Ships with in-memory, Redis and RabbitMQ implementations.
- 👷 **ActivityExecutor** – worker that subscribes to a queue, runs the agent, and forwards the message.

## Use Cases

- 🌐 **Distributed AI workflows** – Coordinate microservices or serverless functions without synchronous call chains.
- ⏱️ **Long-running and resilient workflows** – Durable messaging ensures progress survives restarts or failures.
- 🔄 **Dynamic itineraries** – Agents can insert follow-up steps based on intermediate results or user input.
- 🤝 **Federated architectures** – Combine `pydantic-ai` and `pydantic-graph` for complex in-process logic while using Paigeant for cross-service orchestration.

## Roadmap

| Feature Category | Feature |  |  |
|------------------|-------------|------------|------------|
| **Transports** | ✅ InMemory | ✅ Redis | 🔜 RabbitMQ, Kafka |
| **Workflow State Persistence** | ✅ InMemory, SQLite | ✅ PostgreSQL | 🔜 MongoDB, Cassandra |
| **Security** | ✅ Basic Auth | ✅ OAuth 2.0, JWS | 🔜 RBAC, Audit Logs, OBO-Token |
| **Observability** | ✅ Logging | ✅ Tracing | 🔜 Metrics, Dashboards |
| **Execution** | ✅ Sequential | ✅ Durable | 🔜 Parallel, Compensation |
| **Discovery** | ✅ Static | 🔜 Dynamic | 🔜 Service Mesh |
| **Context** | ✅ RoutingSlip | 🔜 Agent Memory |

## Contributing

Paigeant is open source under the MIT License. Contributions welcome!

- 🐞 Report bugs and request features via GitHub Issues.
- 🔧 Submit PRs with new transports, registry improvements, or examples.
- 📖 Check the design docs under `misc/design` for deeper architectural insights.

## License

MIT

