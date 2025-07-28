import asyncio
import pytest

from paigeant.db import WorkflowDB

@pytest.mark.asyncio
async def test_workflow_db_lifecycle(tmp_path):
    db_path = tmp_path / "test.db"
    db = WorkflowDB(f"sqlite+aiosqlite:///{db_path}")
    await db.init_db()

    run = await db.create_run("abc")
    assert run.correlation_id == "abc"

    step = await db.record_step_start(run.id, "step1", {"foo": "bar"})
    assert step.step_name == "step1"

    await db.record_step_result(step.id, {"ok": True})
    value = await db.get_variable(run.id, "missing")
    assert value is None

    await db.set_variable(run.id, "x", {"a": 1})
    value = await db.get_variable(run.id, "x")
    assert value == {"a": 1}
