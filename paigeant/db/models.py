from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class WorkflowRun(SQLModel, table=True):
    """Represents an instance of a workflow execution."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    status: str = Field(default="in_progress")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    correlation_id: Optional[str] = None


class StepExecution(SQLModel, table=True):
    """Tracks execution details for a single workflow step."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_run_id: UUID = Field(foreign_key="workflowrun.id")
    step_name: str
    status: str = Field(default="pending")
    attempt: int = 1
    input_payload: dict = Field(sa_column=Column(JSON))
    output_payload: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    max_retries: int = 3


class WorkflowVariable(SQLModel, table=True):
    """Key-value store for workflow variables."""

    workflow_run_id: UUID = Field(foreign_key="workflowrun.id", primary_key=True)
    key: str = Field(primary_key=True)
    value: dict = Field(sa_column=Column(JSON))
