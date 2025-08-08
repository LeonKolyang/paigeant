# Paigeant Tests

Simple, focused tests for the paigeant workflow dispatch library.

## Test Files

- **`test_dispatch.py`** - Core workflow dispatch and message contracts
- **`test_agent_usage.py`** - Basic pydantic-ai agent integration  
- **`test_realistic_agent_usage.py`** - Production-ready usage patterns

## Test Philosophy

- **Minimal workflows**: Max 3 activities unless more needed for specific test
- **Grouped scenarios**: Similar tests combined, no duplication
- **Starting point**: Basic coverage to build upon, not comprehensive

## Running Tests

```bash
# Basic functionality test
uv run python -c "
import asyncio
from paigeant import PaigeantAgent, WorkflowDependencies, WorkflowDispatcher, get_transport

class Deps(WorkflowDependencies):
    pass

async def test():
    transport = get_transport()
    dispatcher = WorkflowDispatcher()
    agent = PaigeantAgent('model', dispatcher=dispatcher, name='validate', deps_type=Deps)
    agent.add_to_runway(prompt='process task', deps=Deps())
    correlation_id = await dispatcher.dispatch_workflow(transport)
    print(f'Test passed: {correlation_id}')

asyncio.run(test())
"

# Run examples
uv run python guides/single_agent_example.py
```

## Test Structure

Each test file focuses on specific functionality:

### Core Dispatch (`test_dispatch.py`)
- Basic workflow dispatch
- Message serialization and routing slips
- End-to-end transport flow

### Agent Usage (`test_agent_usage.py`)  
- Agent creation and dependencies
- Workflow dispatch through agents
- Multiple scenario handling

### Realistic Usage (`test_realistic_agent_usage.py`)
- Enterprise workflow scenarios
- Error handling patterns
- User context and token management

All tests use simple 3-activity workflows unless specific functionality requires more steps.
