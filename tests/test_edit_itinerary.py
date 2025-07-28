import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from paigeant.contracts import ActivitySpec, RoutingSlip, PaigeantMessage
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

    result = await EditItinerary.function(Ctx(), [step2, step3])

    assert slip.inserted_steps == 1
    assert len(slip.itinerary) == 2
    assert "Inserted 1 steps" in result


class DummyAgent:
    def __init__(self) -> None:
        self.tool_registered = False
        self.received_deps: dict | None = None

    def tool(self, *_args, **_kwargs) -> None:
        self.tool_registered = True

    def system_prompt(self, *_args, **_kwargs) -> None:  # pragma: no cover - noop
        pass

    async def run(self, _prompt: str, *, deps=None, **_kw) -> str:
        self.received_deps = deps
        return "ok"


@pytest.mark.asyncio
async def test_pageant_agent_run_passes_deps():
    dummy = DummyAgent()
    wrapper = PageantAgent(dummy, can_edit_itinerary=True, max_added_steps=3)
    step = ActivitySpec(agent_name="a1", prompt="p1")
    msg = PaigeantMessage(correlation_id="cid", routing_slip=RoutingSlip(itinerary=[step]))

    await wrapper.run("test", message=msg, deps={"foo": "bar"})

    assert dummy.tool_registered is True
    assert dummy.received_deps["message"] is msg
    assert dummy.received_deps["foo"] == "bar"
    assert dummy.received_deps["itinerary_edit_limit"] == 3
