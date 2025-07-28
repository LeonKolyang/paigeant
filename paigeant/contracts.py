"""Core message contracts for paigeant workflow system."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .transports import BaseTransport


class SerializedDeps(BaseModel):
    data: Optional[dict]  # serialized values (or None if no deps)
    type: Optional[str]  # class name, e.g. "MyDeps"
    module: Optional[str]  # module path, e.g. "my_project.agents.deps"


class ActivitySpec(BaseModel):
    """Defines one step in a workflow."""

    agent_name: str
    prompt: str
    deps: Optional[SerializedDeps] = None  # Additional dependencies for the activity
    arguments: Dict[str, Any] = Field(default_factory=dict)


class RoutingSlip(BaseModel):
    """Describes remaining, executed and compensating activities."""

    itinerary: List[ActivitySpec] = Field(default_factory=list)
    executed: List[ActivitySpec] = Field(default_factory=list)
    compensations: List[ActivitySpec] = Field(default_factory=list)

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

    def to_json(self) -> str:
        """Serialize message to JSON."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "PaigeantMessage":
        """Deserialize message from JSON."""
        return cls.model_validate_json(data)

    async def forward_to_next_step(self, transport: "BaseTransport") -> None:
        """Advance workflow and publish message to next activity if any."""
        current = self.routing_slip.next_step()
        if current is None:
            return

        self.routing_slip.mark_complete(current)
        next_activity = self.routing_slip.next_step()
        if next_activity:
            await transport.publish(next_activity.agent_name, self)
