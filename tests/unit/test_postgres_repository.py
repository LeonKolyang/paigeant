import os
import uuid

import pytest

from paigeant.persistence import PostgresWorkflowRepository


def _get_dsn() -> str | None:
    return os.getenv("TEST_PG_DSN", "postgresql://postgres:postgres@localhost:5432/postgres")


@pytest.mark.asyncio
async def test_postgres_repository_crud():
    dsn = _get_dsn()
    try:
        repo = PostgresWorkflowRepository(dsn)
        # attempt connection
        conn = await repo._connect()
        await conn.close()
    except Exception:
        pytest.skip("PostgreSQL server not available")

    corr_id = str(uuid.uuid4())
    routing_slip = {"itinerary": ["step1"]}
    payload = {"foo": "bar"}

    await repo.create_workflow(corr_id, routing_slip, payload)
    await repo.mark_step_started(corr_id, "step1", run_id=1)
    await repo.mark_step_completed(
        corr_id, "step1", status="completed", output={"x": 1}, run_id=1
    )
    await repo.update_payload(corr_id, {"foo": "baz"})
    await repo.update_routing_slip(corr_id, {"itinerary": []})
    await repo.mark_workflow_completed(corr_id)

    wf = await repo.get_workflow(corr_id)
    assert wf is not None
    assert wf.correlation_id == corr_id
    assert wf.routing_slip == {"itinerary": []}
    assert wf.payload == {"foo": "baz"}
    assert wf.status == "completed"
    assert len(wf.steps) == 1
    step = wf.steps[0]
    assert step.step_name == "step1"
    assert step.status == "completed"
    assert step.output == {"x": 1}

    all_wfs = await repo.list_workflows()
    assert any(w.correlation_id == corr_id for w in all_wfs)


@pytest.mark.asyncio
async def test_postgres_repository_idempotent_step_updates():
    dsn = _get_dsn()
    try:
        repo = PostgresWorkflowRepository(dsn)
        conn = await repo._connect()
        await conn.close()
    except Exception:
        pytest.skip("PostgreSQL server not available")

    corr_id = str(uuid.uuid4())
    await repo.create_workflow(corr_id, {"itinerary": ["step1"]}, {})

    await repo.mark_step_started(corr_id, "step1", run_id=1)
    await repo.mark_step_started(corr_id, "step1", run_id=1)
    await repo.mark_step_completed(corr_id, "step1", status="completed", run_id=1)
    await repo.mark_step_completed(corr_id, "step1", status="completed", run_id=1)

    await repo.mark_step_started(corr_id, "step1", run_id=2)
    await repo.mark_step_started(corr_id, "step1", run_id=2)
    await repo.mark_step_completed(corr_id, "step1", status="completed", run_id=2)
    await repo.mark_step_completed(corr_id, "step1", status="completed", run_id=2)

    wf = await repo.get_workflow(corr_id)
    assert wf is not None
    assert len(wf.steps) == 2
    assert all(step.status == "completed" for step in wf.steps)
