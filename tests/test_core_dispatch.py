"""Core workflow dispatch functionality tests."""

import os
import pytest
from pydantic import BaseModel

from paigeant import (
    PaigeantAgent,
    WorkflowDependencies,
    WorkflowDispatcher,
    get_transport,
)
from paigeant.contracts import ActivitySpec, SerializedDeps

os.environ.setdefault("ANTHROPIC_API_KEY", "test")


class MockDeps(WorkflowDependencies):
    api_key: str = "test-key"


@pytest.mark.asyncio
async def test_activity_registration_and_dispatch():
    """Test registering activities and dispatching workflow."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher()

    test_agent = PaigeantAgent(
        "anthropic:claude-3-5-sonnet-latest",
        dispatcher=dispatcher,
        name="test_agent",
        deps_type=MockDeps,
    )

    # Register an activity with dependencies
    deps = MockDeps(api_key="secret-key")
    test_agent.add_to_runway(prompt="Process test task", deps=deps)

    # Verify activity was created correctly
    activity = dispatcher._itinerary[0]
    assert activity.agent_name == "test_agent"
    assert activity.prompt == "Process test task"
    assert activity.deps is not None
    assert activity.deps.type == "MockDeps"

    # Dispatch workflow
    correlation_id = await dispatcher.dispatch_workflow(transport)
    assert correlation_id is not None
    assert len(correlation_id) > 0


@pytest.mark.asyncio
async def test_message_serialization():
    """Test message contracts can be serialized/deserialized."""
    from paigeant.contracts import PaigeantMessage, RoutingSlip

    activity = ActivitySpec(
        agent_name="test-agent",
        prompt="Test prompt",
        deps=SerializedDeps(
            data={"api_key": "test"}, type="MockDeps", module="test_module"
        ),
    )

    message = PaigeantMessage(
        correlation_id="test-123",
        routing_slip=RoutingSlip(itinerary=[activity]),
        payload={"key": "value"},
    )

    # Test serialization round-trip
    json_data = message.to_json()
    restored = PaigeantMessage.from_json(json_data)

    assert restored.correlation_id == "test-123"
    assert len(restored.routing_slip.itinerary) == 1
    assert restored.routing_slip.itinerary[0].agent_name == "test-agent"
    assert restored.payload["key"] == "value"


@pytest.mark.asyncio
async def test_dispatcher_topic():
    """WorkflowDispatcher publishes message with trace_id and correct topic."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher()

    class Deps(WorkflowDependencies):
        token: str

    agent1 = PaigeantAgent(
        "anthropic:claude-3-5-sonnet-latest",
        dispatcher=dispatcher,
        name="agent1",
        deps_type=Deps,
    )
    agent2 = PaigeantAgent(
        "anthropic:claude-3-5-sonnet-latest",
        dispatcher=dispatcher,
        name="agent2",
    )

    agent1.add_to_runway(prompt="p1", deps=Deps(token="x"))
    agent2.add_to_runway(prompt="p2", deps=None)

    correlation_id = await dispatcher.dispatch_workflow(transport, {"foo": "bar"})

    # First queue should contain the published message
    queue = transport._queues["agent1"]
    assert len(queue) == 1
    _, message = queue[0]
    assert message.routing_slip.itinerary[0].agent_name == "agent1"
    assert message.routing_slip.itinerary[1].agent_name == "agent2"


@pytest.mark.asyncio
async def test_activity_serialization_in_registry():
    """Registered activities should store serialized deps."""
    dispatcher = WorkflowDispatcher()

    class D(WorkflowDependencies):
        value: int

    agentA = PaigeantAgent(
        "anthropic:claude-3-5-sonnet-latest",
        dispatcher=dispatcher,
        name="agentA",
        deps_type=D,
    )

    agentA.add_to_runway(prompt="p", deps=D(value=3))

    stored = dispatcher._itinerary[0]
    assert stored.deps.type == "D"
    assert stored.deps.data == {
        "activity_registry": None,
        "itinerary_edit_limit": 3,
        "previous_output": None,
        "user_token": None,
        "value": 3,
    }
