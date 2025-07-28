from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from .models import WorkflowRun, StepExecution, WorkflowVariable


class WorkflowDB:
    """Simple async database helper for workflow persistence."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_async_engine(
            database_url, echo=False, future=True, connect_args={"check_same_thread": False}
        )

    async def init_db(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with AsyncSession(self.engine) as session:
            yield session

    async def create_run(self, correlation_id: str) -> WorkflowRun:
        run = WorkflowRun(correlation_id=correlation_id)
        async with self.session() as session:
            session.add(run)
            await session.commit()
            await session.refresh(run)
        return run

    async def record_step_start(
        self, run_id: UUID, step: str, payload: dict
    ) -> StepExecution:
        step_row = StepExecution(
            workflow_run_id=run_id,
            step_name=step,
            status="in_progress",
            input_payload=payload,
        )
        async with self.session() as session:
            session.add(step_row)
            await session.commit()
            await session.refresh(step_row)
        return step_row

    async def record_step_result(self, step_id: UUID, result: dict | str) -> None:
        async with self.session() as session:
            step = await session.get(StepExecution, step_id)
            if step is None:
                return
            step.output_payload = result
            step.status = "completed"
            step.finished_at = datetime.utcnow()
            await session.commit()

    async def record_step_error(self, step_id: UUID, error: str) -> None:
        async with self.session() as session:
            step = await session.get(StepExecution, step_id)
            if step is None:
                return
            step.status = "failed"
            step.error_message = error
            step.finished_at = datetime.utcnow()
            await session.commit()

    async def set_variable(self, run_id: UUID, key: str, value: dict) -> None:
        var = WorkflowVariable(workflow_run_id=run_id, key=key, value=value)
        async with self.session() as session:
            await session.merge(var)
            await session.commit()

    async def get_variable(self, run_id: UUID, key: str) -> dict | None:
        async with self.session() as session:
            var = await session.get(WorkflowVariable, (run_id, key))
            return var.value if var else None
