# Paigeant

**Durable workflow orchestration for AI agents in distributed systems**

*Transform fragile agent call chains into resilient, production-ready workflows*

---

## What is Paigeant?

Paigeant is a Python library that provides the messaging infrastructure to orchestrate AI agents across distributed services. It solves the fundamental problem of building resilient, multi-agent workflows that can survive crashes, network failures, and deployments without losing work or state.

**The Problem**: Chaining AI agents together with direct calls creates a "distributed monolith" - if any agent crashes, the entire workflow fails catastrophically.

**The Solution**: Paigeant transforms fragile call chains into durable, message-driven workflows where each step is independent, recoverable, and can resume exactly where it left off.

```
Fragile: Agent A → Agent B → Agent C → Agent D (crashes cascade)
Fragile: Agent A calls Agent B, which calls Agent C, which calls Agent D

Resilient: Agent A → Queue → Agent B → Queue → Agent C → Queue → Agent D
```

## Core Principles

Paigeant is built on three foundational architectural principles:

1. **Asynchronous-First Communication** - All inter-agent communication is async by default, eliminating blocking calls and cascade failures
2. **Durable Execution** - Workflows survive crashes because state lives in messages, not memory
3. **Zero-Trust Messaging** - Built-in security with OAuth delegation and cryptographic message integrity

## What You Can Build

### Real-World Use Cases

**Customer Onboarding Pipeline**
```python
onboarding_workflow = [
    "validate-customer-data",
    "create-customer-account", 
    "setup-payment-method",
    "send-welcome-email"
]
```
If payment processing fails, the workflow holds state and retries with backup methods - no lost progress.

**E-commerce Order Processing**
```python
order_workflow = [
    "validate-order",
    "check-inventory", 
    "process-payment",
    "update-inventory",
    "generate-shipping-label",
    "send-confirmation"
]
```
Each step can be handled by specialized AI agents, with automatic retry and recovery.

**Support Ticket Automation**
```python
support_workflow = [
    "classify-ticket-priority",
    "route-to-specialist",
    "research-customer-history", 
    "generate-response",
    "schedule-follow-up"
]
```
Sophisticated AI analysis at each step, with human handoff capabilities.

## Key Features

- **Asynchronous messaging** - Non-blocking, resilient inter-agent communication
- **Durable execution** - Workflows survive crashes, restarts, and deployments  
- **Pluggable transports** - In-memory, RabbitMQ, Redis Streams support
- **Routing slip pattern** - Workflow logic travels with the message
- **Security-ready** - OAuth tokens and message signing built-in
- **Observable** - Correlation IDs for monitoring and debugging
- **AI-native** - Built-in pydantic-ai integration

## Quick Start

The following example shows how to run a single agent workflow and explains the core concepts along the way.

### 1. Install Paigeant

```bash
uv add paigeant
```

### 2. Define an agent and workflow

Create `guides/quickstart_demo.py`:

```python
import asyncio
from paigeant import PaigeantAgent, WorkflowDependencies, WorkflowDispatcher, get_transport

class DemoDeps(WorkflowDependencies):
    """Per-request context shared across activities."""
    pass

dispatcher = WorkflowDispatcher()

echo_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    system_prompt="Repeat the user's input.",
    dispatcher=dispatcher,
    name="echo_agent",
)

async def main():
    transport = get_transport()
    # Register work for the agent
    echo_agent.add_to_runway(prompt="hello from paigeant", deps=DemoDeps())
    # Send the workflow to the transport
    correlation_id = await dispatcher.dispatch_workflow(transport)
    print("dispatched workflow", correlation_id)

if __name__ == "__main__":
    asyncio.run(main())
```

`PaigeantAgent` wraps an LLM with its own instructions. Calling `add_to_runway` creates an `ActivitySpec` describing a unit of work for that agent. The `WorkflowDispatcher` collects these activities and sends them through the chosen transport.

### 3. Run a worker

Workers execute activities from the transport. Start one for the echo agent:

```bash
uv run paigeant execute echo_agent guides.quickstart_demo
```

The `paigeant execute` command loads the agent and waits for messages addressed to it.

### 4. Dispatch the workflow

In another terminal run:

```bash
uv run python guides/quickstart_demo.py
```

The worker prints the agent's response and the workflow completes. This pattern scales to multiple agents and transports without changing your workflow code.

## AI Agent Integration

### With pydantic-ai

Paigeant includes built-in integration for pydantic-ai agents:

```python
from paigeant import create_planner_agent, PlannerAgentDeps

# Create an AI agent that can dispatch workflows
agent = create_planner_agent(model="openai:gpt-4")

# Give it workflow dispatch capabilities
deps = PlannerAgentDeps(
    workflow_dispatcher=dispatcher,
    user_obo_token="user-session-token"
)

# Agent creates workflows from natural language
result = await agent.run(
    "I need to onboard a new premium customer: john@example.com",
    deps=deps
)
```

The AI agent automatically:
1. Understands the request
2. Creates appropriate workflow activities  
3. Dispatches the workflow
4. Returns a tracking ID

### Agents as Workflow Steps

Each workflow step can use sophisticated AI internally:

```python
async def handle_support_ticket(message):
    ticket_data = message.payload
    
    # Use AI agent for analysis
    support_agent = Agent(model="openai:gpt-4")
    analysis = await support_agent.run(
        f"Analyze this support ticket: {ticket_data}"
    )
    
    # Continue workflow with analysis
    message.payload["analysis"] = analysis.data
    message.routing_slip.mark_complete("analyze-ticket")
    await transport.publish("workflows", message)
```

## How It Works: Technical Architecture

### The Routing Slip Pattern

Every workflow message carries its own "itinerary" - a routing slip that tracks:

- **Activities to complete**: The workflow's task list
- **Completed activities**: What's been done
- **Payload data**: Information flowing through the workflow
- **Security context**: User permissions and message integrity

```python
# Example message structure
{
    "correlation_id": "uuid-here",
    "routing_slip": {
        "itinerary": ["validate", "create", "notify"],
        "completed": ["validate"],
        "current": "create"
    },
    "payload": {
        "customer_email": "user@example.com",
        "subscription_tier": "premium"
    },
    "security": {
        "obo_token": "oauth-token",
        "jws_signature": "cryptographic-signature"
    }
}
```

### Federated Architecture

Paigeant follows a clean separation of concerns:

- **Task Layer** (pydantic-ai): In-process agent execution and reasoning
- **Workflow Layer** (paigeant): Cross-service message orchestration

This federated approach means:
- No centralized orchestrator (eliminating single points of failure)
- Each service owns its business logic
- Workflow state travels with the message
- Easy to scale and deploy independently

### Transport Abstraction

Paigeant works with any message broker:

```python
# Development
export PAIGEANT_TRANSPORT=inmemory

# Production options  
export PAIGEANT_TRANSPORT=rabbitmq
export PAIGEANT_TRANSPORT=redis
```

You can switch transports without changing workflow code, enabling:
- **Local development** with in-memory queues
- **Production deployment** with enterprise message brokers
- **Hybrid architectures** mixing different transports

## Key Benefits

### For Developers
- **Gradual adoption** - Start simple, add complexity as needed
- **Technology flexibility** - Mix different AI frameworks and infrastructure  
- **Built-in observability** - Correlation IDs for monitoring and debugging
- **Security first** - User permissions flow through entire workflows

### For Operations
- **Fault tolerance** - Graceful error handling and recovery
- **Zero-downtime deployments** - Running workflows survive updates
- **Horizontal scaling** - Add workers without workflow changes
- **Audit trails** - Complete workflow history and state tracking

### For Business
- **Process reliability** - Critical workflows never lose progress
- **Automatic recovery** - Temporary failures don't break business processes  
- **Workflow visibility** - Track complex processes end-to-end
- **Faster iterations** - Independent services deploy and scale separately

## When to Use Paigeant

**Use Paigeant when:**
- Your workflow spans multiple services or teams
- Steps take significant time (minutes to hours)
- Failure recovery is business-critical
- You need to track complex business processes
- You're building production AI systems

**Don't use Paigeant when:**
- Everything runs in a single process
- You need millisecond response times  
- The workflow is simple and unlikely to fail
- You're just starting with AI agents (start simple first)

## Installation & Setup

### Installation

```bash
uv add paigeant
```

### Development Setup

```bash
git clone https://github.com/your-org/paigeant
cd paigeant
uv pip install -e .
```

### Configuration

Configure your transport layer via environment variables:

```bash
# For development and testing
export PAIGEANT_TRANSPORT=inmemory  # default

# For production
export PAIGEANT_TRANSPORT=rabbitmq
export PAIGEANT_TRANSPORT=redis
```

### Testing

Run the test suite:

```bash
uv run pytest tests/ -v
```

## Getting Started Guide

1. **Think in workflows**: Break your business process into independent steps
2. **Start small**: Begin with 2-3 steps to understand the pattern  
3. **Add durability gradually**: Start with in-memory transport, upgrade to production brokers
4. **Monitor and observe**: Use correlation IDs to track workflow progress
5. **Scale up**: Add more complex workflows as your confidence grows

## Project Status

**Early Development** - This is Feature 1 (Transport Layer) of the paigeant roadmap.

**Current capabilities:**
- Core message contracts and routing slip pattern
- In-memory transport for development
- Basic workflow dispatch and execution
- pydantic-ai agent integration

**Coming next:**
- RabbitMQ and Redis transport implementations
- Advanced routing slip execution engine  
- Production worker runtime
- State store integration for persistence
- Comprehensive monitoring and observability

## Contributing

Paigeant is designed to solve real-world distributed AI challenges. We welcome contributions, especially:

- Transport implementations (Kafka, Azure Service Bus, etc.)
- Security enhancements (additional JOSE support)
- Monitoring and observability features
- Documentation and examples

## License

MIT License - see LICENSE file for details.

---

*Paigeant transforms the complexity of distributed AI systems into manageable, resilient building blocks. It's not magic - it's proven architectural patterns applied to the unique challenges of AI agent orchestration.*
