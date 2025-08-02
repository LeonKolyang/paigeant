from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, _system_prompt

from paigeant.contracts import ActivitySpec, WorkflowDependencies

from ..constants import DEFAULT_ITINERARY_EDIT_LIMIT
from ..dispatch import WorkflowDispatcher, find_variable_name
from ..tools import _edit_itinerary, _extract_previous_output, _itinerary_editing_prompt

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PaigeantOutput(BaseModel, Generic[T]):
    """Base class for paigeant agent outputs."""

    output: T
    added_activities: list[Optional[ActivitySpec]] = Field(default_factory=list)


def create_edit_itinerary_tool(output_type: Type[T]) -> Callable:
    """Create a dynamically typed _edit_itinerary function."""

    def _edit_itinerary(
        ctx: RunContext[WorkflowDependencies],
        run_output: Any,  # This will be dynamically typed
        follow_up_agents: Optional[Dict[str, Optional[str]]],
    ) -> PaigeantOutput[Any]:
        """Tool to insert additional agent activities defined in ctx.activity_registry into the current workflow.
        Takes a dict with agent names as keys and optional prompts as values.
        Agents not in ctx.activity_registry will raise an error.
        """
        logger.debug(
            f"_edit_itinerary called with follow_up_agents: {follow_up_agents}"
        )

        new_steps: List[ActivitySpec] = []
        if not follow_up_agents:
            logger.debug("No follow-up agents specified, returning original output")
            return PaigeantOutput[output_type](
                output=run_output,
                added_activities=new_steps,
            )

        for agent_name, prompt in follow_up_agents.items():
            activity_from_registry = ctx.deps.activity_registry.get(agent_name)
            if not activity_from_registry:
                logger.warning(f"Agent {agent_name} not found in activity registry")
                # raise ValueError(f"Agent {agent_name} not found in activity registry.")
            if prompt:
                logger.debug(f"Updating prompt for agent {agent_name}")
                activity_from_registry.prompt = prompt
            new_steps.append(activity_from_registry)

        logger.info(
            f"Added {len(new_steps)} activities to workflow: {[step.agent_name for step in new_steps]}"
        )
        return PaigeantOutput[output_type](
            output=run_output,
            added_activities=new_steps,
        )

    # Update the function's type annotations at runtime
    _edit_itinerary.__annotations__["run_output"] = output_type
    _edit_itinerary.__annotations__["return"] = PaigeantOutput[output_type]

    return _edit_itinerary


class PaigeantAgent(Agent):
    """Base class for paigeant agents with workflow dispatch capability."""

    def __init__(
        self,
        *args,
        dispatcher: WorkflowDispatcher,
        can_edit_itinerary: bool = False,
        max_added_steps: int = DEFAULT_ITINERARY_EDIT_LIMIT,
        **kwargs,
    ):
        self.agent_id = f"agent-{uuid.uuid4()}"

        logger.debug(
            f"Initializing PaigeantAgent with can_edit_itinerary={can_edit_itinerary}, max_added_steps={max_added_steps}, uuid={self.agent_id}"
        )

        self.dispatcher = dispatcher
        self.can_edit_itinerary = can_edit_itinerary
        self.max_added_steps = max_added_steps

        output_type = kwargs.pop("output_type", str)
        _edit_itinerary_func = create_edit_itinerary_tool(output_type)
        kwargs["output_type"] = _edit_itinerary_func

        super().__init__(*args, **kwargs)

        # Use the system prompt runner to handle itinerary editing to explicitly set dynamic=True
        self._instructions_functions.append(
            _system_prompt.SystemPromptRunner(_extract_previous_output, dynamic=True)
        )

        if self.can_edit_itinerary:
            logger.info(
                f"Agent {getattr(self, 'name', 'unnamed')} enabled for itinerary editing with max {max_added_steps} steps"
            )
            edit_prompt = _itinerary_editing_prompt(max_added_steps)
            # Get existing system prompts and add the new one
            existing_prompts = getattr(self, "_system_prompts", ())
            self._system_prompts = existing_prompts + (edit_prompt,)

            self.tool(_edit_itinerary)

        self.dispatcher._agent_registry[self.agent_id] = {}

    def add_to_runway(
        self,
        prompt: str,
        deps: WorkflowDependencies,
    ):
        """Add this agent to the workflow itinerary with the given prompt and dependencies."""
        logger.debug(
            f"Adding agent {self.agent_id} to runway with prompt: {prompt} and deps: {deps}"
        )

        # Create activity spec for this agent
        activity = self.dispatcher.add_activity(
            agent=self,
            prompt=prompt,
            deps=deps,
        )

        activity_id = f"activity-{uuid.uuid4()}"

        # Register the activity in the dispatcher
        self.dispatcher._agent_registry[self.agent_id][activity_id] = activity
