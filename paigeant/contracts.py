"""Core message contracts for paigeant workflow system."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .constants import DEFAULT_ITINERARY_EDIT_LIMIT

if TYPE_CHECKING:
    from .transports import BaseTransport

logger = logging.getLogger(__name__)


class PreviousOutput(BaseModel):
    """Output produced by a prior agent in the workflow."""

    agent_name: str
    output: Any


class SerializedDeps(BaseModel):
    data: Optional[dict] = Field(default=None, description="Serialized values")
    type: Optional[str] = Field(default=None, description="Class name")
    module: Optional[str] = Field(default=None, description="Module path")


class ActivitySpec(BaseModel):
    """Defines one step in a workflow."""

    agent_name: str
    prompt: str
    deps: Optional[SerializedDeps] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)


class WorkflowDependencies(BaseModel):
    """Container for data shared across workflow activities."""

    user_token: Optional[str] = None
    previous_output: Optional[PreviousOutput] = None
    itinerary_edit_limit: Optional[int] = DEFAULT_ITINERARY_EDIT_LIMIT
    activity_registry: Optional[Dict[str, ActivitySpec]] = None


class RoutingSlip(BaseModel):
    """Describes remaining, executed and compensating activities."""

    itinerary: List[ActivitySpec] = Field(default_factory=list)
    executed: List[ActivitySpec] = Field(default_factory=list)
    compensations: List[ActivitySpec] = Field(default_factory=list)
    inserted_steps: int = 0

    def next_step(self) -> Optional[ActivitySpec]:
        """Get the next step to execute."""
        return self.itinerary[0] if self.itinerary else None

    @property
    def current_activity(self) -> Optional[ActivitySpec]:
        """Alias for ``next_step`` for semantic clarity."""
        return self.next_step()

    def is_finished(self) -> bool:
        """Return ``True`` when all activities have been executed."""
        return not self.itinerary

    def mark_complete(self, step: ActivitySpec) -> None:
        """Mark a step as completed and remove from itinerary."""
        if self.itinerary and self.itinerary[0] == step:
            completed_step = self.itinerary.pop(0)
            self.executed.append(completed_step)

    def insert_activities(self, new_steps: List[ActivitySpec], limit: int = 3) -> int:
        """Insert new activities immediately after the current step."""
        remaining = max(0, limit - self.inserted_steps)
        allowed = new_steps[:remaining]
        if not allowed:
            return 0
        insert_pos = 1
        self.itinerary = (
            self.itinerary[:insert_pos] + allowed + self.itinerary[insert_pos:]
        )
        self.inserted_steps += len(allowed)
        return len(allowed)

    def previous_step(self) -> Optional[ActivitySpec]:
        """Get the last executed step."""
        return self.executed[-1] if self.executed else None


class PaigeantMessage(BaseModel):
    """
    Envelope exchanged over the bus. Includes metadata, routing slip and payload.
    """

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    obo_token: Optional[str] = None
    signature: Optional[str] = None
    routing_slip: RoutingSlip
    payload: Dict[str, Any] = Field(default_factory=dict)
    spec_version: str = "1.0"
    activity_registry: Optional[Dict[str, ActivitySpec]] = None

    def to_json(self) -> str:
        """Serialize message to JSON."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "PaigeantMessage":
        """Deserialize message from JSON."""
        return cls.model_validate_json(data)

    async def forward_to_next_step(self, transport: "BaseTransport") -> None:
        """Advance workflow and publish message to next activity if any.

        Raises:
            Exception: If forwarding fails after marking current step complete.
                      The workflow state may be inconsistent in this case.
        """
        current = self.routing_slip.next_step()
        if current is None:
            logger.debug(
                f"No current activity to forward for correlation_id={self.correlation_id}"
            )
            return

        self.routing_slip.mark_complete(current)
        logger.info(
            f"Completed activity {current.agent_name} for correlation_id={self.correlation_id}"
        )

        next_activity = self.routing_slip.next_step()
        if next_activity is None:
            logger.info(f"Workflow completed for correlation_id={self.correlation_id}")
            return

        try:
            await transport.publish(next_activity.agent_name, self)
            logger.info(
                f"Forwarded message to {next_activity.agent_name} for correlation_id={self.correlation_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to forward message to {next_activity.agent_name} "
                f"for correlation_id={self.correlation_id}: {e}. "
                "Current activity already marked complete; workflow state may be inconsistent."
            )
            raise
