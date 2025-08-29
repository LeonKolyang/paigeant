"""Persistence layer for Paigeant workflows."""

from .models import StepRecord, WorkflowInstance
from .repository import WorkflowRepository
from .sqlite import SQLiteWorkflowRepository

try:  # pragma: no cover - optional dependency
    from .postgres import PostgresWorkflowRepository
except Exception:  # pragma: no cover - optional dependency
    PostgresWorkflowRepository = None  # type: ignore

__all__ = [
    "StepRecord",
    "WorkflowInstance",
    "WorkflowRepository",
    "SQLiteWorkflowRepository",
    "PostgresWorkflowRepository",
]
