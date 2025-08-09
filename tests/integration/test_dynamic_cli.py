import asyncio
import multiprocessing
import os
import sys
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ["PAIGEANT_TRANSPORT"] = "redis"

sys.path.append(str(Path(__file__).resolve().parents[2]))

from guides.dynamic_multi_agent_example import run_three_agent_joke_workflow
from paigeant import get_transport


def _run_agent_process(agent_name: str, executed):
    from unittest.mock import patch

    from typer.testing import CliRunner

    from paigeant.cli import app

    async def fake_handle(self, activity, message):
        executed.append(activity.agent_name)
        if activity.agent_name == "joke_generator_agent":
            forwarder = message.activity_registry["joke_forwarder_agent"]
            message.routing_slip.insert_activities([forwarder])
        await message.forward_to_next_step(self._transport)

    runner = CliRunner()
    with patch("paigeant.execute.ActivityExecutor._handle_activity", new=fake_handle):
        result = runner.invoke(
            app,
            [
                "execute",
                agent_name,
                "guides.dynamic_multi_agent_example",
                "--lifespan",
                "30.0",
            ],
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
        processes = [
            multiprocessing.Process(target=_run_agent_process, args=(name, executed))
            for name in agent_names
        ]
        for proc in processes:
            proc.start()
        for proc in processes:
            proc.join()
            assert proc.exitcode == 0

        assert list(executed) == agent_names
