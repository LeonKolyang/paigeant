from __future__ import annotations

import textwrap
from pathlib import Path

from typer.testing import CliRunner

from paigeant.cli import app

RUNNER = CliRunner()


def _write_module(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def _write_agent_module(path: Path, agent_name: str = "primary") -> None:
    _write_module(
        path,
        f"""
        from paigeant import PaigeantAgent, WorkflowDependencies, WorkflowDispatcher


        class CustomDeps(WorkflowDependencies):
            pass


        dispatcher = WorkflowDispatcher()
        agent = PaigeantAgent(
            name="{agent_name}",
            dispatcher=dispatcher,
            deps_type=CustomDeps,
        )
        """,
    )


def _write_workflow_module(path: Path) -> None:
    _write_module(
        path,
        """
        \"\"\"Example workflow.\"\"\"

        from paigeant.dispatch import WorkflowDispatcher
        from paigeant.agent import PaigeantAgent, WorkflowDependencies


        class CustomDeps(WorkflowDependencies):
            pass


        dispatcher = WorkflowDispatcher()
        primary = PaigeantAgent(
            name="primary",
            dispatcher=dispatcher,
            deps_type=CustomDeps,
        )
        secondary = PaigeantAgent(
            name="secondary",
            dispatcher=dispatcher,
            deps_type=CustomDeps,
        )
        duplicate = PaigeantAgent(
            name="primary",
            dispatcher=dispatcher,
            deps_type=CustomDeps,
        )
        """,
    )


def test_workflow_discover_cli_respects_gitignore(tmp_path: Path) -> None:
    visible = tmp_path / "visible.py"
    ignored = tmp_path / "ignored.py"
    _write_workflow_module(visible)
    _write_workflow_module(ignored)
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")

    result = RUNNER.invoke(app, ["workflow", "discover", "--path", str(tmp_path)])

    assert result.exit_code == 0
    assert "ignored.py" not in result.stdout


def test_agent_discover_cli_lists_agents(tmp_path: Path) -> None:
    module_path = tmp_path / "agents.py"
    _write_agent_module(module_path, agent_name="example")

    result = RUNNER.invoke(app, ["agent", "discover", "--path", str(tmp_path)])

    assert result.exit_code == 0
    assert "example" in result.stdout


def test_agent_discover_cli_respects_gitignore(tmp_path: Path) -> None:
    visible = tmp_path / "visible.py"
    ignored = tmp_path / "ignored.py"
    _write_agent_module(visible, agent_name="visible_agent")
    _write_agent_module(ignored, agent_name="ignored_agent")
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")

    result = RUNNER.invoke(app, ["agent", "discover", "--path", str(tmp_path)])

    assert result.exit_code == 0
    assert "ignored_agent" not in result.stdout
