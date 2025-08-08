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

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("PAIGEANT_TRANSPORT", "redis")


class HttpKey(BaseModel):
    api_key: str


class JokeWorkflowDeps(WorkflowDependencies):
    """Dependencies for joke workflow agents."""

    http_key: HttpKey
    user_token: str | None = None


dispatcher = WorkflowDispatcher()


# Two-agent workflow for joke processing
joke_processor_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt=(
        "Process the joke request and extract the topic. Return just the topic name."
    ),
    dispatcher=dispatcher,
    name="joke_processor_agent",
)

joke_formatter_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt=(
        "Format the received topic into a nice joke request format. "
        "Return a formatted string like 'Please tell me a joke about [topic]'."
    ),
    dispatcher=dispatcher,
    name="joke_formatter_agent",
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
<<<<<<<< HEAD:tests/integration/test_multi_agent.py
    agent_path = "tests.integration.test_multi_agent"
========
    agent_path = "tests.integration.test_integration"
>>>>>>>> main:tests/integration/test_integration.py

    transport = get_transport()

    http_key = HttpKey(api_key="test-key")
    deps = JokeWorkflowDeps(
        http_key=http_key,
        user_token="test-token",
    )

    # Register two activities in sequence
    joke_processor_agent.add_to_runway(
        prompt="Extract topic from: 'I want jokes about cats'",
        deps=deps,
    )

    joke_formatter_agent.add_to_runway(
        prompt="Format the topic received from previous step",
        deps=deps,
    )

    correlation_id = await dispatcher.dispatch_workflow(transport)
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
<<<<<<<< HEAD:tests/integration/test_multi_agent.py
========


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
>>>>>>>> main:tests/integration/test_integration.py
