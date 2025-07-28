from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StepExecution(BaseModel):
    """Minimal execution record used for retry handling."""

    step_name: str
    workflow_id: str
    status: str = "pending"  # pending, success, failed
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: Optional[dict[str, Any]] = None
    retry_count: int = 0
    retry_limit: int = 3
    last_error: Optional[str] = None
    last_attempt_ts: datetime = Field(default_factory=datetime.utcnow)
