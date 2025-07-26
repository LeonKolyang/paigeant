"""Simple paigeant agent usage examples."""

import asyncio

from paigeant import (
    ActivitySpec,
    PlannerAgentDeps,
    WorkflowDispatcher,
    create_planner_agent,
    get_transport,
)


async def basic_usage():
    """Basic agent setup and workflow dispatch."""
    print("🚀 Basic paigeant usage")

    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    # Create agent and dependencies
    agent = create_planner_agent(model="test")
    deps = PlannerAgentDeps(workflow_dispatcher=dispatcher, user_obo_token="token")

    # Dispatch simple workflow
    activities = [
        ActivitySpec(name="validate"),
        ActivitySpec(name="process"),
        ActivitySpec(name="notify"),
    ]
    correlation_id = await dispatcher.dispatch_workflow(
        activities, variables={"id": "123"}
    )

    print(f"✅ Workflow dispatched: {correlation_id}")


async def enterprise_example():
    """Enterprise workflow example."""
    print("\n🏢 Enterprise example")

    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    # Enterprise onboarding workflow
    activities = [
        ActivitySpec(name="validate"),
        ActivitySpec(name="setup"),
        ActivitySpec(name="notify"),
    ]
    correlation_id = await dispatcher.dispatch_workflow(
        activities=activities,
        variables={"customer": "TechCorp", "tier": "enterprise"},
        obo_token="enterprise-token",
    )

    print(f"✅ Enterprise workflow: {correlation_id}")


async def main():
    """Run examples."""
    print("🤖 Paigeant Examples\n")
    await basic_usage()
    await enterprise_example()
    print("\n🎉 Complete! See tests/ for more examples.")


if __name__ == "__main__":
    asyncio.run(main())
