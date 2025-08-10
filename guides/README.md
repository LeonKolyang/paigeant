# Paigeant Workflow Guides

Examples demonstrating distributed workflow patterns with `paigeant`. These guides highlight how `WorkflowDispatcher` builds workflows and how `PaigeantAgent` defines activities that an `ActivityExecutor` later consumes.

## Example scripts

### `single_agent_example.py` — single agent workflow
Shows registering a `PaigeantAgent` and dispatching work through `WorkflowDispatcher`.

### `multi_agent_example.py` — sequential pipeline
Runs three agents in order, passing outputs through queued messages.

### `dynamic_multi_agent_example.py` — dynamic itinerary editing
Adds steps at runtime using an agent with `can_edit_itinerary=True`.

## Running the examples

Each script uses `WorkflowDispatcher` to enqueue work and `PaigeantAgent` to define activities. To process queued messages, run an `ActivityExecutor` using the CLI.

```bash
# Dispatch a single-agent workflow
uv run python guides/single_agent_example.py

# Start a worker for multi-agent examples (requires Redis)
export PAIGEANT_TRANSPORT=redis
uv run paigeant execute joke_generator_agent
```

## Key benefits

- decoupled agents executed in separate processes
- durable messaging isolates failures
- workflows can edit itineraries at runtime
