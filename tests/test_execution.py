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
import types
import sys


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
async def test_handle_activity_updates_payload_and_forwards(monkeypatch):
    """_handle_activity should update message payload and forward."""
    transport = get_transport()
    executor = ActivityExecutor(transport, "DummyAgent", "dummy_module")

    class DummyAgent:
        async def run(self, prompt, deps=None):
            return {"result": prompt.upper()}

    dummy_mod = types.ModuleType("dummy_module")
    dummy_mod.DummyAgent = DummyAgent()
    monkeypatch.setitem(sys.modules, "dummy_module", dummy_mod)

    activity = ActivitySpec(agent_name="DummyAgent", prompt="hello")
    message = PaigeantMessage(
        correlation_id="c1",
        routing_slip=RoutingSlip(itinerary=[activity]),
        payload={},
    )

    called = False

    async def forward_stub(self, _transport):
        nonlocal called
        called = True

    monkeypatch.setattr(PaigeantMessage, "forward_to_next_step", forward_stub)

    await executor._handle_activity(message, activity)

    assert message.payload["result"] == "HELLO"
    assert called
