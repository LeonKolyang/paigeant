"""Routing slip tests."""

import pytest

from paigeant.contracts import ActivitySpec, RoutingSlip, SerializedDeps


@pytest.mark.asyncio
async def test_routing_slip_operations():
    """Test routing slip workflow state management."""
    activity1 = ActivitySpec(
        agent_name="agent1",
        prompt="Task 1",
        deps=SerializedDeps(data={"key": "value"}, type="dict", module="builtins"),
    )
    activity2 = ActivitySpec(agent_name="agent2", prompt="Task 2")

    slip = RoutingSlip(itinerary=[activity1, activity2])

    # Test next_step
    next_activity = slip.next_step()
    assert next_activity.agent_name == "agent1"
    assert next_activity.prompt == "Task 1"

    # Test mark_complete
    slip.mark_complete(activity1)

    assert len(slip.itinerary) == 1
    assert len(slip.executed) == 1
    assert slip.executed[0].agent_name == "agent1"

    # Test next step after completion
    next_activity = slip.next_step()
    assert next_activity.agent_name == "agent2"


@pytest.mark.asyncio
async def test_empty_routing_slip():
    """Test routing slip with no activities."""
    slip = RoutingSlip()

    assert slip.next_step() is None
    assert len(slip.itinerary) == 0
    assert len(slip.executed) == 0
