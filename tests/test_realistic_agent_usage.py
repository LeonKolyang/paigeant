"""Production-ready agent usage patterns."""

import pytest

from paigeant import (
    ActivitySpec,
    PlannerAgentDeps,
    WorkflowDispatcher,
    create_planner_agent,
    get_transport,
)


@pytest.mark.asyncio
async def test_enterprise_scenarios():
    """Test enterprise workflow scenarios."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    scenarios = [
        {
            "name": "customer_onboarding",
            "activities": ["validate", "setup", "notify"],
            "context": {"customer": "TechCorp", "tier": "enterprise"},
        },
        {
            "name": "incident_response",
            "activities": ["detect", "analyze", "resolve"],
            "context": {"severity": "high", "system": "payment"},
        },
    ]

    for scenario in scenarios:
        activities = [ActivitySpec(name=name) for name in scenario["activities"]]
        correlation_id = await dispatcher.dispatch_workflow(
            activities=activities, variables=scenario["context"]
        )
        assert correlation_id is not None


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in agent workflows."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    # Test with missing activities
    with pytest.raises(ValueError):
        await dispatcher.dispatch_workflow([])

    # Test with valid workflow
    activities = [ActivitySpec(name="validate"), ActivitySpec(name="process")]
    correlation_id = await dispatcher.dispatch_workflow(activities)
    assert correlation_id is not None


@pytest.mark.asyncio
async def test_user_context_patterns():
    """Test user context and token handling."""
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    deps = PlannerAgentDeps(
        workflow_dispatcher=dispatcher, user_obo_token="user-session-token"
    )

    agent = create_planner_agent(model="test")
    assert agent._deps_type == PlannerAgentDeps

    # Test workflow with user context
    activities = [
        ActivitySpec(name="authorize"),
        ActivitySpec(name="execute"),
        ActivitySpec(name="audit"),
    ]
    correlation_id = await dispatcher.dispatch_workflow(
        activities=activities,
        variables={"user_id": "user123"},
        obo_token=deps.user_obo_token,
    )

    assert correlation_id is not None
