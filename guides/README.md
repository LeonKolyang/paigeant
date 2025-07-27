# Paigeant Workflow Guides

Practical examples showing how to implement workflow patterns with paigeant.

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

## Key Patterns

### 1. PaigeantAgent vs Direct Calls
```python
# ✅ Paigeant: Specialized workflow agents
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
