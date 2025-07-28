import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from paigeant.contracts import ActivitySpec, RoutingSlip
from paigeant.agent.wrapper import PageantAgent
from paigeant.tools.edit_itinerary import EditItinerary


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
async def test_pageant_agent_wrapper():
    base = Agent(TestModel())
    wrapper = PageantAgent(base, can_edit_itinerary=True, max_added_steps=2)
    assert wrapper.can_edit_itinerary is True
