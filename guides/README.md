# Paigeant Workflow Guides

Examples showing how to implement workflow patterns with paigeant.

## Example Scripts

### `dispatcher_example.py` - Workflow Dispatch Pattern
Shows how to use `WorkflowDispatcher` with pydantic-ai agents to create distributed workflows.

**Features:**
- Multi-agent joke generation workflow using `PaigeantAgent`
- Cross-agent dependency injection
- Workflow coordination via dispatcher

### `execution_example.py` - Activity Executor Pattern  
Demonstrates how to run `ActivityExecutor` workers for handling workflow activities.

**Features:**
- Redis transport for cross-process messaging
- Command-line agent loading
- Activity execution infrastructure

### `three_agent_workflow_example.py` - Sequential Multi-Agent Workflow
Shows a complete three-agent workflow with automatic message forwarding between agents.

**Features:**
- Sequential agent processing (input → enrichment → output)
- Automatic message forwarding between workflow steps
- Distributed execution across multiple worker processes
- End-to-end workflow correlation tracking

## Key Patterns

### 1. PaigeantAgent vs Direct Calls
```python
# Paigeant: Specialized workflow agents
joke_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt="Generate jokes using workflow tools"
)

# Workflow dispatch replaces direct agent calls
correlation_id = await dispatcher.dispatch_workflow(activities)
```

### 2. Activity Execution
```python
# Worker process handling specific activities
executor = ActivityExecutor(
    transport, 
    agent_name="joke-generator",
    agent_path="guides.dispatcher_example"
)
await executor.start()  # Listens for workflow activities
```

## Running the Examples

```bash
# Run workflow dispatcher example
uv run python guides/dispatcher_example.py

# Run activity executor (requires Redis)
export PAIGEANT_TRANSPORT=redis
uv run python guides/execution_example.py joke-generator guides.dispatcher_example
```

## Key Benefits

- **Loose coupling** - Activities handled by separate processes
- **Fault tolerance** - Individual activity failures don't crash workflows  
- **Scalability** - Multiple workers can handle same activity type
- **Observability** - Built-in correlation tracking across distributed activities

## On-Behalf-Of (OBO) Tokens and Delegated Identity

Paigeant workflows can propagate a user's identity end-to-end. When dispatching a
workflow, pass `obo_token`:

```python
dispatcher.dispatch_workflow(..., obo_token=user_token)
```

Workers validate the token and expose claims via `ActivityContext.user_claims`.
You can optionally obtain AWS credentials with `ctx.assume_web_identity(...)` for
per-user isolation. This ensures each message carries its own delegated auth
context in line with zero‑trust principles.
