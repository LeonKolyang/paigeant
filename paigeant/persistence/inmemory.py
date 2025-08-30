"""In-memory implementation of the workflow repository."""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from .models import StepRecord, WorkflowInstance
from .repository import WorkflowRepository


class InMemoryWorkflowRepository(WorkflowRepository):
    """Store workflow state in local memory.

    Useful for tests or when no database is configured. Data is not
    persisted across process restarts.
    """

    def __init__(self) -> None:
        self._workflows: Dict[str, WorkflowInstance] = {}
        self._step_id = 0

    # ------------------------------------------------------------------
    async def create_workflow(
        self, correlation_id: str, routing_slip: dict, payload: dict | None = None
    ) -> None:
        self._workflows[correlation_id] = WorkflowInstance(
            correlation_id=correlation_id,
            routing_slip=routing_slip,
            payload=payload or {},
            status="in_progress",
            steps=[],
        )

    async def update_routing_slip(self, correlation_id: str, routing_slip: dict) -> None:
        wf = self._workflows.get(correlation_id)
        if wf:
            wf.routing_slip = routing_slip

    async def mark_step_started(
        self, correlation_id: str, step_name: str, run_id: int = 1
    ) -> None:
        wf = self._workflows.get(correlation_id)
        if not wf:
            return
        # ignore duplicate starts for the same run
        for step in wf.steps:
            if step.step_name == step_name and step.run_id == run_id:
                return
        self._step_id += 1
        wf.steps.append(
            StepRecord(
                id=self._step_id,
                correlation_id=correlation_id,
                step_name=step_name,
                run_id=run_id,
                started_at=datetime.utcnow(),
            )
        )

    async def mark_step_completed(
        self,
        correlation_id: str,
        step_name: str,
        status: str,
        output: dict | None = None,
        run_id: int = 1,
    ) -> None:
        wf = self._workflows.get(correlation_id)
        if not wf:
            return
        for step in wf.steps:
            if (
                step.step_name == step_name
                and step.run_id == run_id
                and step.completed_at is None
            ):
                step.completed_at = datetime.utcnow()
                step.status = status
                step.output = output or {}
                break

    async def update_payload(self, correlation_id: str, payload: dict) -> None:
        wf = self._workflows.get(correlation_id)
        if wf:
            wf.payload = payload

    async def mark_workflow_completed(
        self, correlation_id: str, status: str = "completed"
    ) -> None:
        wf = self._workflows.get(correlation_id)
        if wf:
            wf.status = status

    async def get_workflow(self, correlation_id: str) -> WorkflowInstance | None:
        return self._workflows.get(correlation_id)

    async def list_workflows(self) -> list[WorkflowInstance]:
        return list(self._workflows.values())
