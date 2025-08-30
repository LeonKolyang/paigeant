import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from paigeant import WorkflowDispatcher, get_transport
from paigeant.execute import ActivityExecutor
from paigeant.persistence import SQLiteWorkflowRepository


class DummyAgent:
    name = "test_agent"

    async def run(self, prompt: str, deps=None):
        return SimpleNamespace(output="ok")


test_agent = DummyAgent()


@pytest.mark.asyncio
async def test_workflow_persistence_instrumentation(tmp_path):
    """Workflow execution should record state in repository."""

    dispatcher = WorkflowDispatcher()
    dispatcher.add_activity(test_agent, prompt="do it", deps=None, agent_name="test_agent")

    transport = get_transport("inmemory")
    repo = SQLiteWorkflowRepository(tmp_path / "wf.db")

    correlation_id = await dispatcher.dispatch_workflow(
        transport, repository=repo
    )

    executor = ActivityExecutor(
        transport,
        agent_name="test_agent",
        base_path=Path(__file__),
        repository=repo,
    )

    await executor.start(lifespan=1)

    wf = await repo.get_workflow(correlation_id)
    assert wf is not None
    assert wf.status == "completed"
    assert wf.payload == {"test_agent": "ok"}
    assert len(wf.steps) == 1
    step = wf.steps[0]
    assert step.step_name == "test_agent"
    assert step.status == "completed"
