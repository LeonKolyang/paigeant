"""Pydantic-AI integration for paigeant workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent, RunContext

from .contracts import ActivitySpec
from .dispatch import WorkflowDispatcher


@dataclass
class PlannerAgentDeps:
    """Dependencies for a planner agent that can dispatch workflows."""

    workflow_dispatcher: WorkflowDispatcher
    user_obo_token: Optional[str] = None


def create_planner_agent(model: str = "test") -> Agent[PlannerAgentDeps, str]:
    """Create a planner agent with workflow dispatch capability."""

    agent = Agent(model=model, deps_type=PlannerAgentDeps)

    @agent.tool
    async def dispatch_workflow(
        ctx: RunContext[PlannerAgentDeps],
        activity_names: List[str],
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Construct and dispatch a new distributed workflow.

        Args:
            activity_names: List of activity names to execute in sequence
            variables: Optional variables to pass to the workflow

        Returns:
            correlation_id: ID to track the dispatched workflow
        """
        # Convert activity names to ActivitySpec objects
        activities = [ActivitySpec(name=name) for name in activity_names]

        # Dispatch the workflow
        correlation_id = await ctx.deps.workflow_dispatcher.dispatch_workflow(
            activities=activities,
            variables=variables,
            obo_token=ctx.deps.user_obo_token,
        )

        return correlation_id

    return agent
