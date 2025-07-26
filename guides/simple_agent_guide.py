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

    # Create agent
    agent = create_planner_agent(model="test")
    deps = PlannerAgentDeps(workflow_dispatcher=dispatcher, user_obo_token="token")

    # Dispatch workflow
    activities = [
        ActivitySpec(name="validate"),
        ActivitySpec(name="process"),
        ActivitySpec(name="notify"),
    ]
    correlation_id = await dispatcher.dispatch_workflow(
        activities, variables={"id": "123"}
    )

    print(f"✅ Workflow dispatched: {correlation_id}")


async def multiple_workflows():
    """Multiple workflow examples."""
    print("\n🔄 Multiple workflow examples")

    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    workflows = [
        {
            "name": "Order",
            "activities": ["validate", "payment", "ship"],
            "vars": {"order": "123"},
        },
        {
            "name": "Support",
            "activities": ["triage", "assign", "resolve"],
            "vars": {"ticket": "456"},
        },
        {
            "name": "Onboard",
            "activities": ["setup", "training", "activate"],
            "vars": {"user": "789"},
        },
    ]

    for workflow in workflows:
        activities = [ActivitySpec(name=name) for name in workflow["activities"]]
        correlation_id = await dispatcher.dispatch_workflow(
            activities, variables=workflow["vars"]
        )
        print(f"✅ {workflow['name']}: {correlation_id}")


async def main():
    """Run examples."""
    print("🤖 Paigeant Examples\n")
    await basic_usage()
    await multiple_workflows()
    print("\n🎉 Complete! See tests/ for more examples.")


if __name__ == "__main__":
    asyncio.run(main())
