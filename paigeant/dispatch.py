"""Workflow dispatcher for paigeant."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

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

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport
        # store registered activities in the order they are added
        self._registered_activities: List[ActivitySpec] = []

    def register_activity(
        self,
        agent: Any,
        prompt: str,
        deps: Any,
        agent_name: Optional[str] = None,
    ) -> ActivitySpec:
        """Register an activity with the dispatcher."""
        # derive agent name from argument if not provided
        agent_name = agent_name or find_variable_name(agent)

        serialized, deps_type, deps_module = DependencySerializer.serialize(deps)

        activity = ActivitySpec(
            agent_name=agent_name,
            prompt=prompt,
            deps=SerializedDeps(
                data=serialized,
                type=deps_type,
                module=deps_module,
            ),
        )
        self._registered_activities.append(activity)
        return activity

    async def dispatch_workflow(
        self,
        variables: Optional[Dict[str, Any]] = None,
        obo_token: Optional[str] = None,
        topic: str = "workflows",
    ) -> str:
        """
        Construct and dispatch a workflow.

        Args:
            activities: List of activity specifications for the workflow
            variables: Optional variables to pass with the workflow
            obo_token: Optional on-behalf-of token for delegation
            topic: Topic to publish the workflow to

        Returns:
            correlation_id: ID to track the workflow
        """
        correlation_id = str(uuid.uuid4())

        # Build routing slip from activities
        routing_slip = RoutingSlip(itinerary=self._registered_activities)

        # Create the message
        message = PaigeantMessage(
            correlation_id=correlation_id,
            trace_id=correlation_id,
            obo_token=obo_token,
            routing_slip=routing_slip,
            payload=variables or {},
        )

        # Publish to transport
        topic = routing_slip.next_step().agent_name
        await self._transport.publish(topic, message)

        return correlation_id
