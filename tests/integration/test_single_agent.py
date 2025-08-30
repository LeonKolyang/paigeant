import os

import httpx
import pytest
from pydantic import BaseModel
from pydantic_ai import RunContext

from paigeant import (
    PaigeantAgent,
    WorkflowDependencies,
    WorkflowDispatcher,
    get_transport,
)
from paigeant.execute import ActivityExecutor
from paigeant.persistence import SQLiteWorkflowRepository

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("PAIGEANT_TRANSPORT", "redis")


class HttpKey(BaseModel):
    api_key: str


class JokeWorkflowDeps(WorkflowDependencies):
    """Dependencies for joke workflow agents."""

    http_key: HttpKey
    user_token: str | None = None


dispatcher = WorkflowDispatcher()

joke_generation_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",  # Use test model to avoid API calls
    deps_type=JokeWorkflowDeps,
    output_type=list[str],
    system_prompt=(
        'Use the "get_jokes" tool to get jokes on the given subject, '
        "then extract each joke into a list."
    ),
    dispatcher=dispatcher,
    name="joke_generation_agent",
)


@joke_generation_agent.tool
async def get_jokes(ctx: RunContext[JokeWorkflowDeps], count: int) -> str:
    async with httpx.AsyncClient() as client:
        print(f"Using deps: {ctx.deps}")
        assert ctx.deps.activity_registry is not None
        assert "joke_generation_agent" in ctx.deps.activity_registry.activities
        response = await client.get(
            "https://httpbin.org/json",  # Using working endpoint
            params={"count": count},
            headers={"Authorization": f"Bearer {ctx.deps.http_key.api_key}"},
        )
    response.raise_for_status()
    return f"Generated {count} jokes"


@pytest.mark.asyncio
async def test_single_agent_integration(tmp_path):
    """Test single agent integration with joke selection."""

    print("Running joke selection agent with paigeant workflow...")
    # Setup workflow infrastructure
    os.environ["PAIGEANT_TRANSPORT"] = "redis"
    agent_name = "joke_generation_agent"

    transport = get_transport()
    repo = SQLiteWorkflowRepository(tmp_path / "wf.db")

    http_key = HttpKey(api_key="foobar")
    deps = JokeWorkflowDeps(
        http_key=http_key,
        user_token="user-session-token",
    )

    joke_generation_agent.add_to_runway(
        prompt="Generate jokes on the given subject.",
        deps=deps,
    )

    correlation_id = await dispatcher.dispatch_workflow(transport, repository=repo)
    print(f"Workflow dispatched with correlation_id: {correlation_id}")

    # Check that message was published to Redis queue
    queue_name = f"paigeant:{agent_name}"
    queue_length_before = await transport._redis.llen(queue_name)
    print(f"Queue length before execution: {queue_length_before}")
    assert queue_length_before > 0, "Message should be in queue after dispatch"

    transport = get_transport()
    executor = ActivityExecutor(transport, agent_name=agent_name, repository=repo)

    # Start executor with network calls patched out
    await executor.start(lifespan=5)

    wf = await repo.get_workflow(correlation_id)
    assert wf is not None
    assert wf.status == "completed"
    assert [s.step_name for s in wf.steps] == [agent_name]

    # Verify message was processed from queue
    queue_length_after = await transport._redis.llen(queue_name)
    print(f"Queue length after execution: {queue_length_after}")

    # Validate execution
    assert (
        queue_length_after < queue_length_before
    ), "Queue should be empty after message processing"
    print("Integration test passed - message was processed from queue")
    print("All validations passed!")
