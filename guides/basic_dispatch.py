"""Simple example showing basic workflow dispatch."""

import asyncio

from paigeant import ActivitySpec, WorkflowDispatcher, get_transport


async def main():
    """Basic workflow dispatch example."""
    # Initialize transport
    transport = get_transport()
    await transport.connect()

    # Create dispatcher
    dispatcher = WorkflowDispatcher(transport)

    # Define workflow activities
    activities = [
        ActivitySpec(name="validate-input", arguments={"schema": "customer"}),
        ActivitySpec(name="create-account", arguments={"service": "accounts"}),
        ActivitySpec(name="send-notification", arguments={"type": "welcome"}),
    ]

    # Dispatch workflow
    correlation_id = await dispatcher.dispatch_workflow(
        activities=activities,
        variables={"customer_id": "cust-123", "plan": "premium"},
        obo_token="user-token-456",
    )

    print(f"✅ Workflow dispatched successfully!")
    print(f"📋 Correlation ID: {correlation_id}")
    print(f"🔗 Activities: {[a.name for a in activities]}")

    await transport.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
