import os
import sys
import asyncio
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ["PAIGEANT_TRANSPORT"] = "redis"

from paigeant.cli import app
from paigeant import get_transport
from paigeant.execute import ActivityExecutor

sys.path.append(str(Path(__file__).resolve().parents[2]))
from guides.dynamic_multi_agent_example import run_three_agent_joke_workflow


def _redis_len(queue: str) -> int:
    transport = get_transport()
    async def inner():
        await transport.connect()
        length = await transport._redis.llen(queue)
        await transport.disconnect()
        return length
    return asyncio.run(inner())


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

    agent_path = "guides.dynamic_multi_agent_example"
    agent_names = [
        "topic_extractor_agent",
        "joke_generator_agent",
        "joke_forwarder_agent",
        "joke_selector_agent",
    ]

    executed = []

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
        for name in agent_names:
            queue = f"paigeant:{name}"
            before = _redis_len(queue)
            assert before > 0
            result = runner.invoke(app, [name, agent_path])
            assert result.exit_code == 0
            after = _redis_len(queue)
            assert after < before

    assert executed == agent_names
