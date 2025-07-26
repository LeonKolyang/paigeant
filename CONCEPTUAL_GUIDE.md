# Paigeant: Conceptual Guide

*A practical guide to understanding durable workflow orchestration for AI agents*

## The Big Picture: Why Paigeant Exists

### The Problem We're Solving

Imagine you're building a customer onboarding system using AI agents. You might have:
- An agent that validates customer data
- An agent that creates accounts  
- An agent that sets up payment methods
- An agent that sends welcome emails

The naive approach would be to chain these agents together with direct calls:

```
Agent A → Agent B → Agent C → Agent D
```

This creates a **distributed monolith** - if any agent crashes, the entire workflow fails catastrophically. Your customer gets stuck in limbo, and you have no way to recover gracefully.

### The Paigeant Solution

Paigeant transforms this fragile chain into a resilient, message-driven workflow:

```
Agent A → Message Queue → Agent B → Message Queue → Agent C → Message Queue → Agent D
```

Each step is independent, durable, and recoverable. If Agent C crashes, the workflow simply waits until it comes back online, then continues exactly where it left off.

## Core Concepts: The Building Blocks

### 1. The Routing Slip Pattern

Think of a routing slip like a travel itinerary that follows a package through the mail system. In Paigeant, each workflow message carries its own "itinerary" - a list of tasks that need to be completed:

```python
# Example routing slip for customer onboarding
itinerary = [
    "validate-customer-data",    # ← Next step
    "create-customer-account",
    "setup-payment-method", 
    "send-welcome-email"
]
```

As each step completes, it gets moved from the "to-do" list to the "completed" list. The message knows where it's been and where it's going next.

### 2. Messages as Containers

Every workflow is carried by a `PaigeantMessage` that contains:

- **Routing Slip**: The workflow's itinerary
- **Payload**: Data needed by the workflow (customer info, preferences, etc.)
- **Security Context**: Who initiated this workflow and what they're allowed to do
- **Tracking Information**: Unique IDs for monitoring and debugging

Think of it like a FedEx package with a detailed shipping label, contents, sender verification, and tracking number.

### 3. Transport Abstraction

Paigeant doesn't care how messages get delivered - it works with any message broker:

- **In-Memory**: For development and testing
- **RabbitMQ**: For production with high reliability
- **Redis Streams**: For simpler deployments

You can switch between them without changing your workflow logic.

## The Three Architectural Principles

### 1. Asynchronous-First Communication

**Traditional approach (fragile):**
```python
# This blocks and can fail catastrophically
result1 = agent_a.process(data)
result2 = agent_b.process(result1)  # ← Crashes if agent_b is down
result3 = agent_c.process(result2)  # ← Never executes
```

**Paigeant approach (resilient):**
```python
# This sends a message and continues
await dispatcher.dispatch_workflow([
    "process-with-agent-a",
    "process-with-agent-b", 
    "process-with-agent-c"
])
# Each step waits for the previous one, but failures don't cascade
```

### 2. Durable Execution

Your workflow survives crashes because the state lives in the message, not in memory:

- **Server crashes**: Workflow resumes on another server
- **Network failures**: Messages wait in the queue
- **Deployments**: Zero downtime for running workflows

### 3. Security by Design

Each message carries proof of:
- **Who started it**: OAuth tokens for user identity
- **What they can do**: Permission delegation
- **Message integrity**: Cryptographic signatures prevent tampering

## How You Use Paigeant

### Step 1: Define Your Workflow

Think about your business process as a series of independent steps:

```python
from paigeant import ActivitySpec

# Define what needs to happen
onboarding_steps = [
    ActivitySpec(name="validate-customer-data"),
    ActivitySpec(name="create-customer-account"),
    ActivitySpec(name="setup-payment-method"),
    ActivitySpec(name="send-welcome-email"),
]
```

### Step 2: Dispatch the Workflow

Send it into the system with the data it needs:

```python
from paigeant import WorkflowDispatcher, get_transport

transport = get_transport()
dispatcher = WorkflowDispatcher(transport)

correlation_id = await dispatcher.dispatch_workflow(
    activities=onboarding_steps,
    variables={
        "customer_email": "new.customer@example.com",
        "subscription_tier": "premium"
    }
)
```

### Step 3: Build Workers to Handle Each Step

Each activity gets handled by a dedicated service:

```python
# This service handles "validate-customer-data" messages
async def handle_validation(message):
    customer_email = message.payload["customer_email"]
    
    # Use your existing agents/logic here
    is_valid = await customer_validator_agent.validate(customer_email)
    
    if is_valid:
        # Mark this step complete and continue
        message.routing_slip.mark_complete("validate-customer-data")
        await transport.publish("workflows", message)
    else:
        # Handle validation failure
        await handle_validation_error(message)
```

## Integration with AI Agents

### Using Paigeant with pydantic-ai

Paigeant includes built-in integration for pydantic-ai agents:

```python
from paigeant import create_planner_agent, PlannerAgentDeps

# Create an AI agent that can dispatch workflows
agent = create_planner_agent(model="openai:gpt-4")

# Give it the ability to create workflows
deps = PlannerAgentDeps(
    workflow_dispatcher=dispatcher,
    user_obo_token="user-session-token"
)

# Now your agent can create workflows based on natural language
result = await agent.run(
    "I need to onboard a new premium customer. Their email is john@example.com",
    deps=deps
)
```

The AI agent will automatically:
1. Understand the request
2. Call the `dispatch_workflow` tool
3. Create appropriate activities
4. Return a tracking ID

### Workflow Workers Can Use Agents Too

Each step in your workflow can be powered by sophisticated AI:

```python
# A workflow step that uses pydantic-ai internally
async def handle_customer_support_ticket(message):
    ticket_data = message.payload
    
    # Use an AI agent to analyze and route the ticket
    support_agent = Agent(model="openai:gpt-4")
    
    analysis = await support_agent.run(
        f"Analyze this support ticket and determine priority: {ticket_data}"
    )
    
    # Update the workflow with the analysis
    message.payload["analysis"] = analysis.data
    message.routing_slip.mark_complete("analyze-ticket")
    
    await transport.publish("workflows", message)
```

## Real-World Scenarios

### E-commerce Order Processing

```python
order_workflow = [
    ActivitySpec(name="validate-order-details"),
    ActivitySpec(name="check-inventory"),
    ActivitySpec(name="process-payment"),
    ActivitySpec(name="update-inventory"),
    ActivitySpec(name="generate-shipping-label"),
    ActivitySpec(name="send-confirmation-email"),
    ActivitySpec(name="notify-warehouse")
]
```

If payment processing fails, the workflow can:
- Retry with backup payment methods
- Hold inventory while customer updates payment info
- Resume from the exact point of failure

### Customer Support Automation

```python
support_workflow = [
    ActivitySpec(name="classify-ticket-priority"),
    ActivitySpec(name="route-to-specialist-team"),
    ActivitySpec(name="research-customer-history"),
    ActivitySpec(name="generate-initial-response"),
    ActivitySpec(name="schedule-human-follow-up")
]
```

Each step can use AI agents specialized for that task, creating a sophisticated but resilient support pipeline.

## Key Benefits for Developers

### 1. **Gradual Adoption**
- Start with simple workflows
- Add complexity as needed
- Integrate with existing systems

### 2. **Technology Flexibility**
- Use any message broker
- Mix different AI frameworks
- Deploy on any infrastructure

### 3. **Operational Excellence**
- Built-in monitoring via correlation IDs
- Graceful error handling and recovery
- Zero-downtime deployments

### 4. **Security First**
- User permissions flow through the entire workflow
- Messages are tamper-proof
- Audit trails are automatic

## When to Use Paigeant

**Use Paigeant when:**
- Your workflow spans multiple services
- Steps take significant time (minutes to hours)
- Failure recovery is critical
- You need to track complex business processes
- Multiple teams own different parts of the workflow

**Don't use Paigeant when:**
- Everything runs in a single process
- You need millisecond response times
- The workflow is simple and unlikely to fail
- You're just starting with AI agents (start simple first)

## Getting Started

1. **Think in workflows**: Break your business process into independent steps
2. **Start small**: Begin with 2-3 steps to understand the pattern
3. **Add durability gradually**: Start with in-memory transport, upgrade to production brokers
4. **Monitor and observe**: Use correlation IDs to track workflow progress
5. **Scale up**: Add more complex workflows as your confidence grows

Paigeant transforms the complexity of distributed AI systems into manageable, resilient building blocks. It's not magic - it's proven architectural patterns applied to the unique challenges of AI agent orchestration.
