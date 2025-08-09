from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, _system_prompt

from paigeant.contracts import ActivitySpec, WorkflowDependencies

from ..constants import DEFAULT_ITINERARY_EDIT_LIMIT
from ..dispatch import WorkflowDispatcher
from ..tools import _edit_itinerary, _extract_previous_output, _itinerary_editing_prompt

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Registry of all instantiated Paigeant agents keyed by name
AGENT_REGISTRY: Dict[str, "PaigeantAgent"] = {}


class PaigeantOutput(BaseModel, Generic[T]):
    """Base class for paigeant agent outputs."""

    output: T
    added_activities: list[Optional[ActivitySpec]] = Field(default_factory=list)


def create_edit_itinerary_tool(output_type: Type[T]) -> Callable:
    """Return an ``_edit_itinerary`` function parameterized by ``output_type``."""

    def _edit_itinerary(
        ctx: RunContext[WorkflowDependencies],
        run_output: Any,
        follow_up_agents: Optional[Dict[str, Optional[str]]],
    ) -> PaigeantOutput[Any]:
        """Insert additional registered activities into the current workflow."""
        logger.debug(
            f"_edit_itinerary called with follow_up_agents: {follow_up_agents}"
        )

        steps: List[ActivitySpec] = []
        if not follow_up_agents:
            logger.debug("No follow-up agents specified, returning original output")
            return PaigeantOutput[output_type](
                output=run_output,
                added_activities=steps,
            )

        for agent_name, prompt in follow_up_agents.items():
            registered = ctx.deps.activity_registry.get(agent_name)
            if not registered:
                logger.warning(
                    f"Agent {agent_name} not found in activity registry"
                )
            if prompt:
                logger.debug(f"Updating prompt for agent {agent_name}")
                registered.prompt = prompt
            steps.append(registered)

        logger.info(
            f"Added {len(steps)} activities to workflow: {[step.agent_name for step in steps]}"
        )
        return PaigeantOutput[output_type](
            output=run_output,
            added_activities=steps,
        )

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

        # Register this agent instance by name for lookup during execution
        agent_name = getattr(self, "name", self.agent_id)
        AGENT_REGISTRY[agent_name] = self

        self._instructions_functions.append(
            _system_prompt.SystemPromptRunner(_extract_previous_output, dynamic=True)
        )

        if self.can_edit_itinerary:
            logger.info(
                f"Agent {getattr(self, 'name', 'unnamed')} enabled for itinerary editing with max {max_added_steps} steps"
            )
            edit_prompt = _itinerary_editing_prompt(max_added_steps)
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

        activity_spec = self.dispatcher.add_activity(
            agent=self,
            prompt=prompt,
            deps=deps,
        )

        activity_id = f"activity-{uuid.uuid4()}"
        self.dispatcher._agent_registry[self.agent_id][activity_id] = activity_spec

    def register_activity(
        self,
        prompt: str,
        deps: WorkflowDependencies,
    ) -> ActivitySpec:
        """Register an activity without adding it to the itinerary to make it available during execution of the workflow."""
        logger.debug(
            f"Registering activity for agent {self.agent_id} with prompt: {prompt} and deps: {deps}"
        )
        return self.dispatcher.register_activity(agent=self, prompt=prompt, deps=deps)
