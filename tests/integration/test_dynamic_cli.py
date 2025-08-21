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


def _run_agent_process(agent_name: str, executed, errors):
    from typer.testing import CliRunner

    from paigeant.cli import app

    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "execute",
            agent_name,
            "--lifespan",
            "30.0",
        ],
    )
    if result.exit_code == 0:
        executed.append(agent_name)
    else:
        output = result.stdout or ""
        if result.exception:
            output += f"\n{result.exception}"
        errors[agent_name] = output


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
        "joke_forwarder_agent",
        "topic_extractor_agent",
        "joke_generator_agent",
        "joke_selector_agent",
    ]

    with multiprocessing.Manager() as manager:
        executed = manager.list()
        errors = manager.dict()
        processes = [
            multiprocessing.Process(
                target=_run_agent_process, args=(name, executed, errors)
            )
            for name in agent_names
        ]
        for proc in processes:
            proc.start()
        for proc, name in zip(processes, agent_names):
            proc.join()
            assert proc.exitcode == 0, errors.get(name)

        assert not errors, dict(errors)
        assert set(executed) == set(agent_names)
