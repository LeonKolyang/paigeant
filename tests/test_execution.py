"""Activity execution tests."""

import pytest
from pydantic import BaseModel

from paigeant import ActivityExecutor, get_transport
from paigeant.contracts import (
    ActivitySpec,
    PaigeantMessage,
    RoutingSlip,
    SerializedDeps,
)


class MockDeps(BaseModel):
    value: str = "test"


@pytest.mark.asyncio
async def test_activity_extraction():
    """Test extracting activities from messages."""
    transport = get_transport()
    executor = ActivityExecutor(transport, "test_agent", "test_module")

    activity = ActivitySpec(
        agent_name="test_agent",
        prompt="Test task",
        deps=SerializedDeps(data={"value": "test"}, type="MockDeps", module="__main__"),
    )

    message = PaigeantMessage(
        correlation_id="test-123",
        routing_slip=RoutingSlip(itinerary=[activity]),
        payload={},
    )

    extracted = executor.extract_activity(message)
    assert extracted.agent_name == "test_agent"
    assert extracted.prompt == "Test task"
