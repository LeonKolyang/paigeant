"""Workflow dispatcher for paigeant."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from paigeant.agent.wrapper import PaigeantAgent

from .contracts import ActivitySpec, PaigeantMessage, RoutingSlip, SerializedDeps
from .deps.serializer import DependencySerializer
from .transports import BaseTransport


def find_variable_name(obj: Any) -> str:
    """Best-effort lookup of the variable name referencing ``obj``."""
    for name, value in globals().items():
        if value is obj:
            return name
    return getattr(obj, "__name__", str(obj))


class WorkflowDispatcher:
    """Service responsible for dispatching new workflows."""

    def __init__(self) -> None:
        self._itinerary: List[ActivitySpec] = []
        self._activity_registry: Dict[str, ActivitySpec] = {}
        self._agent_registry: Dict[str, PaigeantAgent] = {}

    def _create_activity(
        self,
        agent: Any,
        prompt: str,
        deps: Any,
        agent_name: Optional[str] = None,
    ) -> ActivitySpec:
        """Create an ActivitySpec from agent, prompt, and dependencies."""
        agent_name = (
            agent_name or getattr(agent, "name", None) or find_variable_name(agent)
        )
        serialized, deps_type, deps_module = DependencySerializer.serialize(deps)

        return ActivitySpec(
            agent_name=agent_name,
            prompt=prompt,
            deps=SerializedDeps(data=serialized, type=deps_type, module=deps_module),
        )

    def add_activity(
        self,
        agent: PaigeantAgent,
        prompt: str,
        deps: Any,
        agent_name: Optional[str] = None,
        register_only: bool = False,
    ) -> ActivitySpec:
        """Add an activity to the workflow itinerary and registry."""
        activity = self._create_activity(agent, prompt, deps, agent_name)

        self._activity_registry[activity.agent_name] = activity
        if not register_only:
            self._itinerary.append(activity)

        return activity

    def register_activity(self, *args, **kwargs) -> ActivitySpec:
        """Register an activity without adding to itinerary."""
        return self.add_activity(*args, register_only=True, **kwargs)

    async def dispatch_workflow(
        self,
        transport: BaseTransport,
        variables: Optional[Dict[str, Any]] = None,
        obo_token: Optional[str] = None,
    ) -> str:
        """Dispatch the current itinerary over ``transport``.

        Args:
            transport: Channel used to publish the workflow message.
            variables: Optional variables to include with the workflow.
            obo_token: Optional on-behalf-of token for delegation.

        Returns:
            Correlation identifier for tracking the workflow.
        """
        correlation_id = str(uuid.uuid4())
        routing_slip = RoutingSlip(itinerary=self._itinerary)
        message = PaigeantMessage(
            correlation_id=correlation_id,
            obo_token=obo_token,
            routing_slip=routing_slip,
            payload=variables or {},
            activity_registry=self._activity_registry,
        )
        first_step = routing_slip.next_step()
        await transport.publish(first_step.agent_name, message)
        return correlation_id
