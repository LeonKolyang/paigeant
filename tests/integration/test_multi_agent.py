import os
from unittest.mock import patch

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
async def test_two_agent_integration():
    """Test workflow with two agents where first forwards to second."""

    print("Running two-agent workflow integration test...")
    os.environ["PAIGEANT_TRANSPORT"] = "redis"

    # Agent definitions
    first_agent_name = "joke_processor_agent"
    second_agent_name = "joke_formatter_agent"

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

    async def fake_handle(self, activity, message):
        await message.forward_to_next_step(self._transport)

    # Run first executor
    first_executor = ActivityExecutor(transport, agent_name=first_agent_name)
    with patch(
        "paigeant.execute.ActivityExecutor._handle_activity", new=fake_handle
    ):
        await first_executor.start(lifespan=5)

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
    second_executor = ActivityExecutor(transport, agent_name=second_agent_name)
    with patch(
        "paigeant.execute.ActivityExecutor._handle_activity", new=fake_handle
    ):
        await second_executor.start(lifespan=5)

    # Verify second agent processed
    second_queue_after = await transport._redis.llen(second_queue)
    print(f"Second agent queue after: {second_queue_after}")

    assert (
        second_queue_after < second_queue_length
    ), "Second agent should have processed message"

    print("Two-agent integration test passed - both agents executed in sequence")
    print("Message forwarding validation successful!")
