"""Data models for persisted workflow state."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StepRecord(BaseModel):
    """Record of an individual step execution."""

    id: Optional[int] = None
    correlation_id: str
    step_name: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: Optional[str] = None
    output: Optional[dict[str, Any]] = None


class WorkflowInstance(BaseModel):
    """Persisted workflow instance data."""

    correlation_id: str
    routing_slip: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] | None = None
    status: str = "in_progress"
    steps: list[StepRecord] = Field(default_factory=list)
