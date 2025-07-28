from __future__ import annotations

from typing import Any, Dict

from pydantic_ai import Agent

from ..contracts import PaigeantMessage
from ..tools.edit_itinerary import EditItinerary


class PageantAgent:
    """Wrapper around pydantic-ai Agent with optional itinerary editing."""

    def __init__(
        self,
        base_agent: Agent,
        *,
        can_edit_itinerary: bool = False,
        max_added_steps: int = 3,
    ) -> None:
        self.agent = base_agent
        self.can_edit_itinerary = can_edit_itinerary
        self.max_added_steps = max_added_steps

        if self.can_edit_itinerary:
            # register the edit_itinerary tool with the underlying agent
            self.agent.tool(EditItinerary.function, name=EditItinerary.name)
            self.agent.system_prompt(
                lambda: (
                    f"You may use the `edit_itinerary` tool to insert additional steps into the workflow. "
                    f"You are allowed up to {self.max_added_steps} insertions."
                )
            )

    async def run(
        self,
        prompt: str,
        *,
        message: PaigeantMessage,
        deps: Any = None,
    ) -> Any:
        ctx_deps: Dict[str, Any] = {
            "message": message,
            "itinerary_edit_limit": self.max_added_steps,
        }
        if deps:
            if isinstance(deps, dict):
                ctx_deps.update(deps)
            elif hasattr(deps, "model_dump"):
                ctx_deps.update(deps.model_dump())
            else:
                ctx_deps.update(vars(deps))

        return await self.agent.run(prompt, deps=ctx_deps)
