"""SQLite implementation of the workflow repository."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import StepRecord, WorkflowInstance
from .repository import WorkflowRepository


class SQLiteWorkflowRepository(WorkflowRepository):
    """Persist workflow state using SQLite."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema management
    def _ensure_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                correlation_id TEXT PRIMARY KEY,
                routing_slip TEXT NOT NULL,
                payload TEXT,
                status TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS step_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                correlation_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                status TEXT,
                output TEXT
            )
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Helper methods
    def _execute(self, query: str, *params: Any) -> None:
        cur = self._conn.cursor()
        cur.execute(query, params)
        self._conn.commit()

    def _fetchone(self, query: str, *params: Any) -> sqlite3.Row | None:
        cur = self._conn.cursor()
        cur.execute(query, params)
        return cur.fetchone()

    def _fetchall(self, query: str, *params: Any) -> list[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()

    # ------------------------------------------------------------------
    # Repository API
    async def create_workflow(
        self, correlation_id: str, routing_slip: dict, payload: dict | None = None
    ) -> None:
        await asyncio.to_thread(
            self._execute,
            "INSERT INTO workflows (correlation_id, routing_slip, payload, status) VALUES (?, ?, ?, ?)",
            correlation_id,
            json.dumps(routing_slip),
            json.dumps(payload or {}),
            "in_progress",
        )

    async def update_routing_slip(self, correlation_id: str, routing_slip: dict) -> None:
        await asyncio.to_thread(
            self._execute,
            "UPDATE workflows SET routing_slip = ? WHERE correlation_id = ?",
            json.dumps(routing_slip),
            correlation_id,
        )

    async def mark_step_started(self, correlation_id: str, step_name: str) -> None:
        await asyncio.to_thread(
            self._execute,
            "INSERT INTO step_history (correlation_id, step_name, started_at) VALUES (?, ?, ?)",
            correlation_id,
            step_name,
            datetime.utcnow().isoformat(),
        )

    async def mark_step_completed(
        self,
        correlation_id: str,
        step_name: str,
        status: str,
        output: dict | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._execute,
            """
            UPDATE step_history
            SET completed_at = ?, status = ?, output = ?
            WHERE correlation_id = ? AND step_name = ?
            """,
            datetime.utcnow().isoformat(),
            status,
            json.dumps(output or {}),
            correlation_id,
            step_name,
        )

    async def update_payload(self, correlation_id: str, payload: dict) -> None:
        await asyncio.to_thread(
            self._execute,
            "UPDATE workflows SET payload = ? WHERE correlation_id = ?",
            json.dumps(payload),
            correlation_id,
        )

    async def mark_workflow_completed(
        self, correlation_id: str, status: str = "completed"
    ) -> None:
        await asyncio.to_thread(
            self._execute,
            "UPDATE workflows SET status = ? WHERE correlation_id = ?",
            status,
            correlation_id,
        )

    async def get_workflow(self, correlation_id: str) -> WorkflowInstance | None:
        row = await asyncio.to_thread(
            self._fetchone,
            "SELECT correlation_id, routing_slip, payload, status FROM workflows WHERE correlation_id = ?",
            correlation_id,
        )
        if not row:
            return None
        steps_rows = await asyncio.to_thread(
            self._fetchall,
            "SELECT id, correlation_id, step_name, started_at, completed_at, status, output FROM step_history WHERE correlation_id = ? ORDER BY id",
            correlation_id,
        )
        steps = [
            StepRecord(
                id=r["id"],
                correlation_id=r["correlation_id"],
                step_name=r["step_name"],
                started_at=datetime.fromisoformat(r["started_at"]) if r["started_at"] else None,
                completed_at=datetime.fromisoformat(r["completed_at"]) if r["completed_at"] else None,
                status=r["status"],
                output=json.loads(r["output"]) if r["output"] else None,
            )
            for r in steps_rows
        ]
        return WorkflowInstance(
            correlation_id=row["correlation_id"],
            routing_slip=json.loads(row["routing_slip"]),
            payload=json.loads(row["payload"]) if row["payload"] else None,
            status=row["status"],
            steps=steps,
        )

    async def list_workflows(self) -> list[WorkflowInstance]:
        rows = await asyncio.to_thread(
            self._fetchall,
            "SELECT correlation_id, routing_slip, payload, status FROM workflows",
        )
        workflows: list[WorkflowInstance] = []
        for row in rows:
            workflows.append(
                WorkflowInstance(
                    correlation_id=row["correlation_id"],
                    routing_slip=json.loads(row["routing_slip"]),
                    payload=json.loads(row["payload"]) if row["payload"] else None,
                    status=row["status"],
                    steps=[],
                )
            )
        return workflows
