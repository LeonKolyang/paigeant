import os
from unittest.mock import AsyncMock, patch

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


class HttpKey(BaseModel):
    api_key: str


class JokeWorkflowDeps(WorkflowDependencies):
    """Dependencies for joke workflow agents."""

    http_key: HttpKey
    user_token: str | None = None


joke_selection_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt=(
        "Use the `joke_factory` tool to generate some jokes on the given subject, "
        "then choose the best. You must return just a single joke."
    ),
)


@joke_selection_agent.tool
async def joke_factory(ctx: RunContext[JokeWorkflowDeps], count: int) -> list[str]:
    r = await joke_generation_agent.run(
        f"Please generate {count} jokes.",
        deps=ctx.deps,
        usage=ctx.usage,
    )

    return r.output


joke_generation_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",  # Use test model to avoid API calls
    deps_type=JokeWorkflowDeps,
    output_type=list[str],
    system_prompt=(
        'Use the "get_jokes" tool to get jokes on the given subject, '
        "then extract each joke into a list."
    ),
)


@joke_generation_agent.tool
async def get_jokes(ctx: RunContext[JokeWorkflowDeps], count: int) -> str:
    async with httpx.AsyncClient() as client:
        print(f"Using deps: {ctx.deps}")
        response = await client.get(
            "https://httpbin.org/json",  # Using working endpoint
            params={"count": count},
            headers={"Authorization": f"Bearer {ctx.deps.http_key.api_key}"},
        )
    await response.raise_for_status()
    return f"Generated {count} jokes"


# Two-agent workflow for joke processing
joke_processor_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt=(
        "Process the joke request and extract the topic. Return just the topic name."
    ),
)

joke_formatter_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt=(
        "Format the received topic into a nice joke request format. "
        "Return a formatted string like 'Please tell me a joke about [topic]'."
    ),
)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_two_agent_integration(mock_get):
    """Test workflow with two agents where first forwards to second."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    print("Running two-agent workflow integration test...")
    os.environ["PAIGEANT_TRANSPORT"] = "redis"

    # Agent definitions
    first_agent_name = "joke_processor_agent"
    second_agent_name = "joke_formatter_agent"
    agent_path = "tests.integration.test_integration"

    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    http_key = HttpKey(api_key="test-key")
    deps = JokeWorkflowDeps(
        http_key=http_key,
        user_token="test-token",
    )

    # Register two activities in sequence
    dispatcher.add_activity(
        agent=first_agent_name,
        prompt="Extract topic from: 'I want jokes about cats'",
        deps=deps,
    )

    dispatcher.add_activity(
        agent=second_agent_name,
        prompt="Format the topic received from previous step",
        deps=deps,
    )

    correlation_id = await dispatcher.dispatch_workflow()
    print(f"Two-agent workflow dispatched with correlation_id: {correlation_id}")

    # Check first agent queue
    first_queue = f"paigeant:{first_agent_name}"
    first_queue_before = await transport._redis.llen(first_queue)
    print(f"First agent queue length: {first_queue_before}")
    assert first_queue_before > 0, "First agent should have message in queue"

    # Run first executor
    first_executor = ActivityExecutor(
        transport, agent_name=first_agent_name, agent_path=agent_path
    )
    await first_executor.start(timeout=5)

    # Verify first agent processed and second agent received message
    first_queue_after = await transport._redis.llen(first_queue)
    second_queue = f"paigeant:{second_agent_name}"
    second_queue_length = await transport._redis.llen(second_queue)

    print(f"First agent queue after: {first_queue_after}")
    print(f"Second agent queue length: {second_queue_length}")

    assert (
        first_queue_after < first_queue_before
    ), "First agent should have processed message"
    assert (
        second_queue_length > 0
    ), "Second agent should have received forwarded message"

    # Run second executor
    second_executor = ActivityExecutor(
        transport, agent_name=second_agent_name, agent_path=agent_path
    )
    await second_executor.start(timeout=5)

    # Verify second agent processed
    second_queue_after = await transport._redis.llen(second_queue)
    print(f"Second agent queue after: {second_queue_after}")

    assert (
        second_queue_after < second_queue_length
    ), "Second agent should have processed message"

    print("Two-agent integration test passed - both agents executed in sequence")
    print("Message forwarding validation successful!")


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_single_agent_integration(mock_get):
    """Test single agent integration with joke selection."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    print("Running joke selection agent with paigeant workflow...")
    # Setup workflow infrastructure
    os.environ["PAIGEANT_TRANSPORT"] = "redis"
    agent_name = "joke_generation_agent"
    agent_path = "tests.integration.test_integration"

    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    http_key = HttpKey(api_key="foobar")
    deps = JokeWorkflowDeps(
        http_key=http_key,
        user_token="user-session-token",
    )

    dispatcher.add_activity(
        agent=agent_name,
        prompt="Generate jokes on the given subject.",
        deps=deps,
    )

    correlation_id = await dispatcher.dispatch_workflow()
    print(f"Workflow dispatched with correlation_id: {correlation_id}")

    # Check that message was published to Redis queue
    queue_name = f"paigeant:{agent_name}"
    queue_length_before = await transport._redis.llen(queue_name)
    print(f"Queue length before execution: {queue_length_before}")
    assert queue_length_before > 0, "Message should be in queue after dispatch"

    transport = get_transport()
    executor = ActivityExecutor(transport, agent_name=agent_name, agent_path=agent_path)

    # Start executor
    await executor.start(timeout=5)

    # Verify message was processed from queue
    queue_length_after = await transport._redis.llen(queue_name)
    print(f"Queue length after execution: {queue_length_after}")

    # Validate execution
    assert (
        queue_length_after < queue_length_before
    ), "Queue should be empty after message processing"
    print("Integration test passed - message was processed from queue")
    print("All validations passed!")
