from __future__ import annotations

import textwrap
from pathlib import Path

from typer.testing import CliRunner

from paigeant.cli import app


def _write_agent_module(path: Path, agent_name: str = "primary") -> None:
    path.write_text(
        textwrap.dedent(
            f'''
            from paigeant import PaigeantAgent, WorkflowDependencies, WorkflowDispatcher


            class CustomDeps(WorkflowDependencies):
                pass


            dispatcher = WorkflowDispatcher()
            agent = PaigeantAgent(
                name="{agent_name}",
                dispatcher=dispatcher,
                deps_type=CustomDeps,
            )
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def test_agent_discover_cli_lists_agents(tmp_path: Path) -> None:
    module_path = tmp_path / "agents.py"
    _write_agent_module(module_path, agent_name="example")

    runner = CliRunner()
    result = runner.invoke(app, ["agent", "discover", "--path", str(tmp_path)])

    assert result.exit_code == 0
    output = result.stdout
    assert "Discovering agents in:" in output
    assert "example" in output
    assert "./agents.py" in output


def test_agent_discover_cli_respects_gitignore(tmp_path: Path) -> None:
    visible = tmp_path / "visible.py"
    ignored = tmp_path / "ignored.py"
    _write_agent_module(visible, agent_name="visible_agent")
    _write_agent_module(ignored, agent_name="ignored_agent")
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["agent", "discover", "--path", str(tmp_path)])

    assert result.exit_code == 0
    output = result.stdout
    assert "visible_agent" in output
    assert "./visible.py" in output
    assert "ignored_agent" not in output


def test_agent_discover_cli_missing_directory() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["agent", "discover", "--path", "./does-not-exist"],
    )

    assert result.exit_code == 1
    assert "Specified path does not exist" in result.stdout
