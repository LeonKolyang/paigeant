import uuid

import pytest

from paigeant.persistence import SQLiteWorkflowRepository


@pytest.mark.asyncio
async def test_sqlite_repository_crud(tmp_path):
    db_path = tmp_path / "wf.db"
    repo = SQLiteWorkflowRepository(db_path)

    corr_id = str(uuid.uuid4())
    routing_slip = {"itinerary": ["step1"]}
    payload = {"foo": "bar"}

    await repo.create_workflow(corr_id, routing_slip, payload)
    await repo.mark_step_started(corr_id, "step1")
    await repo.mark_step_completed(corr_id, "step1", status="completed", output={"x": 1})
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
async def test_sqlite_repository_idempotent_step_updates(tmp_path):
    repo = SQLiteWorkflowRepository(tmp_path / "wf.db")
    corr_id = str(uuid.uuid4())
    await repo.create_workflow(corr_id, {"itinerary": ["step1"]}, {})

    # Duplicate calls should not create duplicate records
    await repo.mark_step_started(corr_id, "step1")
    await repo.mark_step_started(corr_id, "step1")
    await repo.mark_step_completed(corr_id, "step1", status="completed")
    await repo.mark_step_completed(corr_id, "step1", status="completed")

    wf = await repo.get_workflow(corr_id)
    assert wf is not None
    assert len(wf.steps) == 1
    assert wf.steps[0].status == "completed"
