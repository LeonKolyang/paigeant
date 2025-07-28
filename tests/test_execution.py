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


@pytest.mark.asyncio
async def test_forward_to_next_step():
    """Activity executor should forward message to next activity."""
    transport = get_transport()

    import types, sys
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    dummy = types.ModuleType("dummy_agent")
    dummy.test_agent = Agent(model=TestModel())
    sys.modules["dummy_agent"] = dummy

    executor = ActivityExecutor(transport, "test_agent", "dummy_agent")

    step1 = ActivitySpec(agent_name="test_agent", prompt="step1")
    step2 = ActivitySpec(agent_name="next_agent", prompt="step2")
    message = PaigeantMessage(
        correlation_id="cid-1",
        routing_slip=RoutingSlip(itinerary=[step1, step2]),
        payload={},
    )

    await executor._handle_activity(step1, message)

    assert message.routing_slip.executed[0].agent_name == "test_agent"
    assert len(transport._queues["next_agent"]) == 1
