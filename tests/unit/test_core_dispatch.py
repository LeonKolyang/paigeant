"""Core workflow dispatch functionality tests."""

import pytest
from pydantic import BaseModel

from paigeant import WorkflowDispatcher, get_transport
from paigeant.contracts import ActivitySpec, SerializedDeps


class MockDeps(BaseModel):
    api_key: str = "test-key"


@pytest.mark.asyncio
async def test_activity_registration_and_dispatch():
    """Test registering activities and dispatching workflow."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    # Register an activity with dependencies
    deps = MockDeps(api_key="secret-key")
    activity = dispatcher.register_activity(
        agent="test_agent", prompt="Process test task", deps=deps
    )

    # Verify activity was created correctly
    assert activity.agent_name == "test_agent"
    assert activity.prompt == "Process test task"
    assert activity.deps is not None
    assert activity.deps.type == "MockDeps"

    # Dispatch workflow
    correlation_id = await dispatcher.dispatch_workflow()
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
