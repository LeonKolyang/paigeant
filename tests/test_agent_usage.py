"""Basic pydantic-ai agent integration tests."""

import pytest

from paigeant import (
    ActivitySpec,
    PlannerAgentDeps,
    WorkflowDispatcher,
    create_planner_agent,
    get_transport,
)


@pytest.mark.asyncio
async def test_agent_creation():
    """Test agent creation and dependencies."""
    # Test agent creation
    agent = create_planner_agent(model="test")
    assert agent is not None
    assert agent._deps_type == PlannerAgentDeps

    # Test dependencies
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)
    deps = PlannerAgentDeps(workflow_dispatcher=dispatcher, user_obo_token="token")

    assert deps.workflow_dispatcher is dispatcher
    assert deps.user_obo_token == "token"


@pytest.mark.asyncio
async def test_workflow_dispatch():
    """Test workflow dispatch through agent dependencies."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    activities = [
        ActivitySpec(name="validate"),
        ActivitySpec(name="process"),
        ActivitySpec(name="notify"),
    ]
    correlation_id = await dispatcher.dispatch_workflow(
        activities, variables={"id": "123"}
    )

    assert correlation_id is not None


@pytest.mark.asyncio
async def test_multiple_scenarios():
    """Test different workflow scenarios."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    scenarios = [
        {"activities": ["validate", "payment", "ship"], "vars": {"order": "123"}},
        {"activities": ["triage", "assign", "resolve"], "vars": {"ticket": "456"}},
        {"activities": ["setup", "training", "activate"], "vars": {"user": "789"}},
    ]

    correlation_ids = []
    for scenario in scenarios:
        activities = [ActivitySpec(name=name) for name in scenario["activities"]]
        correlation_id = await dispatcher.dispatch_workflow(
            activities, variables=scenario["vars"]
        )
        correlation_ids.append(correlation_id)

    assert len(set(correlation_ids)) == 3
