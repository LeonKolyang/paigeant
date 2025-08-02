import pytest

from paigeant.agent.wrapper import PaigeantAgent
from paigeant.contracts import ActivitySpec, PaigeantMessage, RoutingSlip
from paigeant.tools import _edit_itinerary


@pytest.mark.asyncio
async def test_insert_activities():
    step1 = ActivitySpec(agent_name="a1", prompt="p1")
    step2 = ActivitySpec(agent_name="a2", prompt="p2")
    slip = RoutingSlip(itinerary=[step1])
    inserted = slip.insert_activities([step2], limit=2)
    assert inserted == 1
    assert len(slip.itinerary) == 2
    assert slip.itinerary[1].agent_name == "a2"


@pytest.mark.asyncio
async def test_paigeant_agent_wrapper():
    wrapper = PaigeantAgent("test", can_edit_itinerary=True, max_added_steps=2)
    assert wrapper.can_edit_itinerary is True


@pytest.mark.asyncio
async def test_edit_tool_limit():
    """Ensure edit_itinerary respects the insert limit."""
    step1 = ActivitySpec(agent_name="a1", prompt="p1")
    step2 = ActivitySpec(agent_name="a2", prompt="p2")
    step3 = ActivitySpec(agent_name="a3", prompt="p3")
    slip = RoutingSlip(itinerary=[step1])
    message = PaigeantMessage(correlation_id="cid", routing_slip=slip)

    class Ctx:
        def __init__(self):
            self.deps = {"message": message, "itinerary_edit_limit": 1}

    result = await _edit_itinerary(Ctx(), [step2, step3])

    assert slip.inserted_steps == 1
    assert len(slip.itinerary) == 2
    assert "Inserted 1 steps" in result
