import os
import sys
from pathlib import Path
import asyncio
import multiprocessing

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ["PAIGEANT_TRANSPORT"] = "redis"

sys.path.append(str(Path(__file__).resolve().parents[2]))

from paigeant import get_transport
from guides.dynamic_multi_agent_example import run_three_agent_joke_workflow


def _run_agent_process(agent_name: str, executed):
    from typer.testing import CliRunner
    from unittest.mock import patch
    from paigeant.cli import app
    from paigeant.execute import ActivityExecutor

    async def fake_handle(self, activity, message):
        executed.append(activity.agent_name)
        if activity.agent_name == "joke_generator_agent":
            forwarder = message.activity_registry["joke_forwarder_agent"]
            message.routing_slip.insert_activities([forwarder])
        await message.forward_to_next_step(self._transport)

    original_start = ActivityExecutor.start

    async def start_with_timeout(self, timeout=None):
        await original_start(self, timeout=0.2)

    runner = CliRunner()
    with patch(
        "paigeant.execute.ActivityExecutor._handle_activity", new=fake_handle
    ), patch("paigeant.cli.ActivityExecutor.start", new=start_with_timeout):
        result = runner.invoke(
            app, ["execute", agent_name, "guides.dynamic_multi_agent_example"]
        )
        assert result.exit_code == 0


def _flushdb() -> None:
    transport = get_transport()
    async def inner():
        await transport.connect()
        await transport._redis.flushdb()
        await transport.disconnect()
    asyncio.run(inner())


def test_dynamic_agent_cli_execution():
    _flushdb()
    asyncio.run(run_three_agent_joke_workflow())

    agent_names = [
        "topic_extractor_agent",
        "joke_generator_agent",
        "joke_forwarder_agent",
        "joke_selector_agent",
    ]

    with multiprocessing.Manager() as manager:
        executed = manager.list()
        for name in agent_names:
            proc = multiprocessing.Process(
                target=_run_agent_process, args=(name, executed)
            )
            proc.start()
            proc.join()
            assert proc.exitcode == 0

        assert list(executed) == agent_names
