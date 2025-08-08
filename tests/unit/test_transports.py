"""Transport tests."""

import pytest

from paigeant.contracts import ActivitySpec, PaigeantMessage, RoutingSlip
from paigeant.transports.inmemory import InMemoryTransport


@pytest.mark.asyncio
async def test_inmemory_transport_basic():
    """Test basic InMemoryTransport publish/subscribe."""
    transport = InMemoryTransport()

    # Create test message
    activity = ActivitySpec(agent_name="test_agent", prompt="Test task")
    message = PaigeantMessage(
        correlation_id="test-123",
        routing_slip=RoutingSlip(itinerary=[activity]),
        payload={"test": "data"},
    )

    # Publish message
    await transport.publish("test_topic", message)

    # Subscribe and verify message
    message_received = False
    async for raw_msg, received_msg in transport.subscribe("test_topic"):
        assert received_msg.correlation_id == "test-123"
        assert received_msg.payload["test"] == "data"

        # Acknowledge message
        await transport.ack(raw_msg)
        message_received = True
        break

    assert message_received


@pytest.mark.asyncio
async def test_redis_transport_import():
    """Test Redis transport can be imported (even if redis not available)."""
    try:
        from paigeant.transports.redis import RedisTransport

        # If redis is available, test basic instantiation
        try:
            transport = RedisTransport()
            assert transport.host == "localhost"
            assert transport.port == 6379
        except ImportError:
            # Redis not available, just test import worked
            pass
    except ImportError:
        pytest.fail("RedisTransport should be importable")
