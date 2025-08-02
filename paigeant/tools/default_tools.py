from __future__ import annotations

from typing import List, Optional

from pydantic_ai import RunContext

from ..constants import DEFAULT_ITINERARY_EDIT_LIMIT
from ..contracts import ActivitySpec, PaigeantMessage, WorkflowDependencies


async def _edit_itinerary(
    ctx: RunContext[WorkflowDependencies], new_steps: List[ActivitySpec]
) -> str:
    """Tool to insert additional steps into the current workflow."""
    message: PaigeantMessage = ctx.deps.get("message")
    limit: int = ctx.deps.get("itinerary_edit_limit", DEFAULT_ITINERARY_EDIT_LIMIT)
    inserted = message.routing_slip.insert_activities(new_steps, limit=limit)
    return f"Inserted {inserted} steps into the workflow"


async def _extract_previous_output(
    ctx: RunContext[WorkflowDependencies],
) -> Optional[str]:
    """Extract output from the previous agent in the workflow."""
    if previous_output := ctx.deps.previous_output:
        return f"If required, use the previous output: {previous_output.output} from {previous_output.agent_name}."
    return None
