"""Workflow dispatcher for paigeant."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .contracts import ActivitySpec, PaigeantMessage, RoutingSlip
from .transports import BaseTransport


class WorkflowDispatcher:
    """Service responsible for dispatching new workflows."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport

    async def dispatch_workflow(
        self,
        activities: List[ActivitySpec],
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
        itinerary = [activity.name for activity in activities]
        routing_slip = RoutingSlip(itinerary=itinerary)

        # Create the message
        message = PaigeantMessage(
            correlation_id=correlation_id,
            obo_token=obo_token,
            routing_slip=routing_slip,
            payload=variables or {},
        )

        # Publish to transport
        await self._transport.publish(topic, message)

        return correlation_id
