from __future__ import annotations

from typing import List

from pydantic_ai import Tool, RunContext

from ..contracts import ActivitySpec, PaigeantMessage


async def _edit_itinerary(ctx: RunContext[dict], new_steps: List[ActivitySpec]) -> str:
    """Tool to insert additional steps into the current workflow."""
    message: PaigeantMessage = ctx.deps.get("message")
    limit: int = ctx.deps.get("itinerary_edit_limit", 3)
    inserted = message.routing_slip.insert_activities(new_steps, limit=limit)
    return f"Inserted {inserted} steps into the workflow"


EditItinerary = Tool(
    _edit_itinerary,
    name="edit_itinerary",
    description="Add new steps to the workflow itinerary.",
)
