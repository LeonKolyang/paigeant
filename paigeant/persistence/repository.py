"""Repository abstraction for workflow state persistence."""

from __future__ import annotations

from typing import Protocol

from .models import WorkflowInstance


class WorkflowRepository(Protocol):
    """Protocol for workflow state persistence backends."""

    async def create_workflow(
        self, correlation_id: str, routing_slip: dict, payload: dict | None = None
    ) -> None:
        """Persist initial workflow state."""

    async def update_routing_slip(self, correlation_id: str, routing_slip: dict) -> None:
        """Persist updated routing slip."""

    async def mark_step_started(self, correlation_id: str, step_name: str) -> None:
        """Record start of a step."""

    async def mark_step_completed(
        self,
        correlation_id: str,
        step_name: str,
        status: str,
        output: dict | None = None,
    ) -> None:
        """Record completion of a step."""

    async def update_payload(self, correlation_id: str, payload: dict) -> None:
        """Persist workflow payload updates."""

    async def mark_workflow_completed(
        self, correlation_id: str, status: str = "completed"
    ) -> None:
        """Mark the workflow as finished."""

    async def get_workflow(self, correlation_id: str) -> WorkflowInstance | None:
        """Retrieve the workflow instance by id."""

    async def list_workflows(self) -> list[WorkflowInstance]:
        """Return all persisted workflows."""
