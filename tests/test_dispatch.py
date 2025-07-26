"""Core workflow dispatch and message contract tests."""

import pytest

from paigeant import ActivitySpec, PaigeantMessage, WorkflowDispatcher, get_transport
from paigeant.contracts import RoutingSlip
from paigeant.transports.inmemory import InMemoryTransport


@pytest.mark.asyncio
async def test_workflow_dispatch():
    """Test basic workflow dispatch."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    activities = [
        ActivitySpec(name="validate"),
        ActivitySpec(name="process"),
        ActivitySpec(name="notify"),
    ]
    correlation_id = await dispatcher.dispatch_workflow(activities)

    assert correlation_id is not None
    assert len(correlation_id) > 0


@pytest.mark.asyncio
async def test_message_contracts():
    """Test message serialization and routing slip operations."""
    # Test routing slip
    slip = RoutingSlip(itinerary=["step1", "step2", "step3"])
    assert slip.next_step() == "step1"

    slip.mark_complete("step1")
    assert slip.next_step() == "step2"
    assert "step1" in slip.executed

    # Test message serialization
    message = PaigeantMessage(
        correlation_id="test-123",
        routing_slip=RoutingSlip(itinerary=["step1", "step2"]),
        payload={"key": "value"},
    )

    json_data = message.to_json()
    restored = PaigeantMessage.from_json(json_data)

    assert restored.correlation_id == "test-123"
    assert restored.routing_slip.itinerary == ["step1", "step2"]
    assert restored.payload["key"] == "value"


@pytest.mark.asyncio
async def test_end_to_end_flow():
    """Test complete message flow through transport."""
    transport = InMemoryTransport()
    dispatcher = WorkflowDispatcher(transport)

    activities = [ActivitySpec(name="step1"), ActivitySpec(name="step2")]
    correlation_id = await dispatcher.dispatch_workflow(
        activities=activities, variables={"var": "value"}, obo_token="token"
    )

    # Verify message was published
    subscriber = transport.subscribe("workflows")
    raw_message, paigeant_message = await subscriber.__anext__()

    assert paigeant_message.correlation_id == correlation_id
    assert paigeant_message.obo_token == "token"
    assert paigeant_message.payload["var"] == "value"
    assert paigeant_message.routing_slip.itinerary == ["step1", "step2"]

    await transport.ack(raw_message)
