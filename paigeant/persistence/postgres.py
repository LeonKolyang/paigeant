"""PostgreSQL implementation of the workflow repository."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import asyncpg

from .models import StepRecord, WorkflowInstance
from .repository import WorkflowRepository


class PostgresWorkflowRepository(WorkflowRepository):
    """Persist workflow state using PostgreSQL."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._initialized = False

    async def _connect(self) -> asyncpg.Connection:
        conn = await asyncpg.connect(self._dsn)
        if not self._initialized:
            await self._ensure_schema(conn)
            self._initialized = True
        return conn

    async def _ensure_schema(self, conn: asyncpg.Connection) -> None:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                correlation_id TEXT PRIMARY KEY,
                routing_slip JSONB NOT NULL,
                payload JSONB,
                status TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS step_history (
                id SERIAL PRIMARY KEY,
                correlation_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                status TEXT,
                output JSONB
            )
            """
        )

    # ------------------------------------------------------------------
    async def create_workflow(
        self, correlation_id: str, routing_slip: dict, payload: dict | None = None
    ) -> None:
        conn = await self._connect()
        try:
            await conn.execute(
                "INSERT INTO workflows (correlation_id, routing_slip, payload, status) VALUES ($1, $2, $3, $4)",
                correlation_id,
                json.dumps(routing_slip),
                json.dumps(payload or {}),
                "in_progress",
            )
        finally:
            await conn.close()

    async def update_routing_slip(self, correlation_id: str, routing_slip: dict) -> None:
        conn = await self._connect()
        try:
            await conn.execute(
                "UPDATE workflows SET routing_slip = $1 WHERE correlation_id = $2",
                json.dumps(routing_slip),
                correlation_id,
            )
        finally:
            await conn.close()

    async def mark_step_started(self, correlation_id: str, step_name: str) -> None:
        conn = await self._connect()
        try:
            await conn.execute(
                "INSERT INTO step_history (correlation_id, step_name, started_at) VALUES ($1, $2, $3)",
                correlation_id,
                step_name,
                datetime.utcnow(),
            )
        finally:
            await conn.close()

    async def mark_step_completed(
        self,
        correlation_id: str,
        step_name: str,
        status: str,
        output: dict | None = None,
    ) -> None:
        conn = await self._connect()
        try:
            await conn.execute(
                """
                UPDATE step_history
                SET completed_at = $1, status = $2, output = $3
                WHERE correlation_id = $4 AND step_name = $5
                """,
                datetime.utcnow(),
                status,
                json.dumps(output or {}),
                correlation_id,
                step_name,
            )
        finally:
            await conn.close()

    async def update_payload(self, correlation_id: str, payload: dict) -> None:
        conn = await self._connect()
        try:
            await conn.execute(
                "UPDATE workflows SET payload = $1 WHERE correlation_id = $2",
                json.dumps(payload),
                correlation_id,
            )
        finally:
            await conn.close()

    async def mark_workflow_completed(
        self, correlation_id: str, status: str = "completed"
    ) -> None:
        conn = await self._connect()
        try:
            await conn.execute(
                "UPDATE workflows SET status = $1 WHERE correlation_id = $2",
                status,
                correlation_id,
            )
        finally:
            await conn.close()

    async def get_workflow(self, correlation_id: str) -> WorkflowInstance | None:
        conn = await self._connect()
        try:
            row = await conn.fetchrow(
                "SELECT correlation_id, routing_slip, payload, status FROM workflows WHERE correlation_id = $1",
                correlation_id,
            )
            if not row:
                return None
            steps_rows = await conn.fetch(
                "SELECT id, correlation_id, step_name, started_at, completed_at, status, output FROM step_history WHERE correlation_id = $1 ORDER BY id",
                correlation_id,
            )
        finally:
            await conn.close()
        steps = [
            StepRecord(
                id=r["id"],
                correlation_id=r["correlation_id"],
                step_name=r["step_name"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                status=r["status"],
                output=r["output"],
            )
            for r in steps_rows
        ]
        return WorkflowInstance(
            correlation_id=row["correlation_id"],
            routing_slip=row["routing_slip"],
            payload=row["payload"],
            status=row["status"],
            steps=steps,
        )

    async def list_workflows(self) -> list[WorkflowInstance]:
        conn = await self._connect()
        try:
            rows = await conn.fetch(
                "SELECT correlation_id, routing_slip, payload, status FROM workflows"
            )
        finally:
            await conn.close()
        return [
            WorkflowInstance(
                correlation_id=r["correlation_id"],
                routing_slip=r["routing_slip"],
                payload=r["payload"],
                status=r["status"],
                steps=[],
            )
            for r in rows
        ]
