"""Persistence layer for Paigeant workflows."""

from __future__ import annotations

import os
from typing import Optional

from ..config import PaigeantConfig, load_config
from .inmemory import InMemoryWorkflowRepository
from .models import StepRecord, WorkflowInstance
from .repository import WorkflowRepository
from .sqlite import SQLiteWorkflowRepository

try:  # pragma: no cover - optional dependency
    from .postgres import PostgresWorkflowRepository
except Exception:  # pragma: no cover - optional dependency
    PostgresWorkflowRepository = None  # type: ignore

_repository_instance: WorkflowRepository | None = None


def get_repository(
    database_url: Optional[str] = None, config: Optional[PaigeantConfig] = None
) -> WorkflowRepository:
    """Factory function to obtain a workflow repository.

    The repository backend is selected based on ``database_url`` which can be
    provided explicitly, via environment variable ``PAIGEANT_DATABASE_URL`` or
    ``DATABASE_URL``, or from loaded configuration. When no database is
    configured, an in-memory repository is returned.
    """

    global _repository_instance
    if _repository_instance is not None and database_url is None and config is None:
        return _repository_instance

    config = config or load_config()
    database_url = (
        database_url
        or os.getenv("PAIGEANT_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or getattr(config, "database_url", None)
    )

    if not database_url:
        _repository_instance = InMemoryWorkflowRepository()
        return _repository_instance

    if database_url.startswith("sqlite://"):
        path = database_url.replace("sqlite://", "", 1)
        _repository_instance = SQLiteWorkflowRepository(path)
    elif database_url.startswith("postgres://") or database_url.startswith(
        "postgresql://"
    ):
        if PostgresWorkflowRepository is None:
            raise RuntimeError("Postgres support not available")
        _repository_instance = PostgresWorkflowRepository(database_url)
    else:
        raise ValueError(f"Unsupported database backend: {database_url}")

    return _repository_instance


__all__ = [
    "StepRecord",
    "WorkflowInstance",
    "WorkflowRepository",
    "SQLiteWorkflowRepository",
    "PostgresWorkflowRepository",
    "InMemoryWorkflowRepository",
    "get_repository",
]
