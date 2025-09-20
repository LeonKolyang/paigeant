from __future__ import annotations

import sys
import textwrap
import types
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# if "paigeant" not in sys.modules:
#     fake_paigeant = types.ModuleType("paigeant")
#     fake_paigeant.ActivityExecutor = object
#     fake_paigeant.get_repository = lambda: None
#     fake_paigeant.get_transport = lambda: None
#     fake_paigeant.__path__ = [str(BASE_DIR / "paigeant")]
#     sys.modules["paigeant"] = fake_paigeant

#     fake_agent_pkg = types.ModuleType("paigeant.agent")
#     fake_agent_pkg.__path__ = [str(BASE_DIR / "paigeant" / "agent")]
#     sys.modules["paigeant.agent"] = fake_agent_pkg

#     fake_agent_discovery = types.ModuleType("paigeant.agent.discovery")
#     fake_agent_discovery.discover_agent = lambda *args, **kwargs: None
#     sys.modules["paigeant.agent.discovery"] = fake_agent_discovery
#     fake_agent_pkg.discovery = fake_agent_discovery
#     fake_paigeant.agent = fake_agent_pkg

from typer.testing import CliRunner

from paigeant.cli import (
    _analyze_workflow_file,
    _format_workflow_path,
    _load_gitignore_patterns,
    _should_ignore_path,
    app,
)


def _write_workflow(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            '''
            """Example workflow."""

            from paigeant.dispatch import WorkflowDispatcher
            from paigeant.agent import PaigeantAgent, WorkflowDependencies


            class CustomDeps(WorkflowDependencies):
                pass


            dispatcher = WorkflowDispatcher()
            agent = PaigeantAgent(
                name="primary",
                dispatcher=dispatcher,
                deps_type=CustomDeps,
            )
            '''
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def test_load_gitignore_patterns_reads_patterns(tmp_path):
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")

    patterns = _load_gitignore_patterns(tmp_path)

    assert "ignored.py" in patterns


def test_should_ignore_path_matches_patterns(tmp_path):
    target = tmp_path / "ignored.py"
    target.write_text("", encoding="utf-8")

    patterns = {"ignored.py"}

    assert _should_ignore_path(target, patterns, tmp_path) is True


def test_analyze_workflow_file_collects_metadata(tmp_path):
    workflow_file = tmp_path / "workflow.py"
    _write_workflow(workflow_file)

    metadata = _analyze_workflow_file(workflow_file)

    assert metadata is not None
    assert metadata["path"] == workflow_file
    assert metadata["description"] == "Example workflow."
    assert metadata["agents"] == ["primary"]
    assert metadata["dependencies"] == ["CustomDeps"]


def test_format_workflow_path_prefers_search_path(tmp_path):
    workflow_file = tmp_path / "workflow.py"
    workflow_file.write_text("", encoding="utf-8")

    formatted = _format_workflow_path(workflow_file, tmp_path)

    assert formatted == "./workflow.py"


def test_workflow_discover_cli_respects_gitignore(tmp_path):
    visible = tmp_path / "visible.py"
    ignored = tmp_path / "ignored.py"
    _write_workflow(visible)
    _write_workflow(ignored)
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["workflow", "discover", "--path", str(tmp_path)])

    assert result.exit_code == 0
    output = result.stdout
    assert "Discovering workflows in:" in output
    assert "visible.py" in output
    assert "primary" in output
    assert "CustomDeps" in output
    assert "ignored.py" not in output
