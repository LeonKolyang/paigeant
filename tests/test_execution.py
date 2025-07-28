"""Activity execution tests."""

import pytest
from pydantic import BaseModel

from paigeant import ActivityExecutor, get_transport
from paigeant.contracts import (
    ActivityFailed,
    ActivitySpec,
    PaigeantMessage,
    RoutingSlip,
    SerializedDeps,
)
from paigeant.utils.retry import compute_backoff


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


def test_message_bump_attempt():
    msg = PaigeantMessage(correlation_id="cid", routing_slip=RoutingSlip())
    bumped = msg.bump_attempt()
    assert bumped.attempt == msg.attempt + 1
    assert bumped.message_id != msg.message_id


def test_compute_backoff_growth():
    first = compute_backoff(1, base=2, jitter=0)
    second = compute_backoff(2, base=2, jitter=0)
    assert second > first


@pytest.mark.asyncio
async def test_retry_on_failure(monkeypatch):
    transport = get_transport()

    class DummyAgent:
        def __init__(self):
            self.calls = 0

        async def run(self, prompt: str, deps=None):
            self.calls += 1
            if self.calls < 2:
                raise ActivityFailed("boom", retryable=True)
            return {"ok": True}

    # create dummy module
    import types, sys

    module = types.ModuleType("test_module")
    module.test_agent = DummyAgent()
    sys.modules["test_module"] = module

    executor = ActivityExecutor(transport, "test_agent", "test_module")

    activity = ActivitySpec(agent_name="test_agent", prompt="do it")
    msg = PaigeantMessage(correlation_id="cid", routing_slip=RoutingSlip(itinerary=[activity]), payload={})

    async def fake_sleep(_):
        pass

    monkeypatch.setattr("paigeant.utils.retry.schedule_retry", fake_sleep)

    await executor._handle_activity(activity, msg)
    # one retry should be queued
    assert transport._queues["test_agent"]
    raw, retry_msg = transport._queues["test_agent"].popleft()
    assert retry_msg.attempt == 2

    await executor._handle_activity(activity, retry_msg)
    step = executor._steps[("cid", "test_agent")]
    assert step.status == "success"
