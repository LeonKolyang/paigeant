"""Tests for forwarding Paigeant messages between workflow steps."""

import pytest

from paigeant.contracts import ActivitySpec, PaigeantMessage, RoutingSlip
from paigeant.transports.inmemory import InMemoryTransport


@pytest.mark.asyncio
async def test_message_forwarding_to_next_step():
    transport = InMemoryTransport()

    step1 = ActivitySpec(agent_name="agent1", prompt="do 1")
    step2 = ActivitySpec(agent_name="agent2", prompt="do 2")

    message = PaigeantMessage(
        correlation_id="corr-1",
        routing_slip=RoutingSlip(itinerary=[step1, step2]),
        payload={},
    )

    await message.forward_to_next_step(transport)

    assert len(message.routing_slip.itinerary) == 1
    assert message.routing_slip.executed[0].agent_name == "agent1"

    iterator = transport.subscribe("agent2")
    raw, forwarded = await anext(iterator)
    assert forwarded is message
