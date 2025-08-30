from pathlib import Path
from types import SimpleNamespace

import pytest

from paigeant import WorkflowDependencies, WorkflowDispatcher
from paigeant.agent.wrapper import PaigeantAgent
from paigeant.execute import ActivityExecutor
from paigeant.persistence import SQLiteWorkflowRepository
from paigeant.transports.inmemory import InMemoryTransport


class DummyAgent(PaigeantAgent):
    def __init__(self, dispatcher, name):
        super().__init__("test", dispatcher=dispatcher, name=name)

    async def run(self, prompt: str, deps: WorkflowDependencies | None = None):
        return SimpleNamespace(output=f"{self.name}-done")


dispatcher = WorkflowDispatcher()
agent1 = DummyAgent(dispatcher, name="agent1")
agent2 = DummyAgent(dispatcher, name="agent2")


@pytest.mark.asyncio
async def test_workflow_persistence_restart_and_idempotency(tmp_path):
    transport = InMemoryTransport()
    repo_path = tmp_path / "wf.db"
    repo = SQLiteWorkflowRepository(repo_path)

    deps = WorkflowDependencies()
    agent1.add_to_runway(prompt="step1", deps=deps)
    agent2.add_to_runway(prompt="step2", deps=deps)

    corr_id = await dispatcher.dispatch_workflow(transport, repository=repo)

    raw = transport._queues["agent1"].popleft()
    msg = raw[1]
    dup = msg.model_copy(deep=True)
    transport._queues["agent1"].append((dup.to_json(), dup))

    executor1 = ActivityExecutor(transport, agent_name="agent1", repository=repo, base_path=Path(__file__))
    await executor1._handle_activity(executor1.extract_activity(msg), msg)
    raw_dup = transport._queues["agent1"].popleft()
    msg_dup = raw_dup[1]
    await executor1._handle_activity(executor1.extract_activity(msg_dup), msg_dup)

    repo = SQLiteWorkflowRepository(repo_path)
    executor2 = ActivityExecutor(transport, agent_name="agent2", repository=repo, base_path=Path(__file__))
    while transport._queues["agent2"]:
        raw2 = transport._queues["agent2"].popleft()
        msg2 = raw2[1]
        await executor2._handle_activity(executor2.extract_activity(msg2), msg2)

    wf = await repo.get_workflow(corr_id)
    assert wf is not None
    assert wf.status == "completed"
    assert {s.step_name for s in wf.steps} == {"agent1", "agent2"}
