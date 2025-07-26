"""Example demonstrating workflow dispatch with paigeant."""

import asyncio

from paigeant import (
    PlannerAgentDeps,
    WorkflowDispatcher,
    create_planner_agent,
    get_transport,
)


async def main():
    """Demonstrate workflow dispatch."""
    # Initialize transport and dispatcher
    transport = get_transport()
    await transport.connect()

    dispatcher = WorkflowDispatcher(transport)

    # Create agent dependencies
    deps = PlannerAgentDeps(
        workflow_dispatcher=dispatcher, user_obo_token="example-token"
    )

    # Create the planner agent
    planner = create_planner_agent()

    # Run the agent to dispatch a workflow
    result = await planner.run(
        "Create a customer onboarding workflow with steps: validate-customer, create-account, send-welcome-email",
        deps=deps,
    )

    print(f"Workflow dispatched with correlation ID: {result.data}")

    await transport.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
