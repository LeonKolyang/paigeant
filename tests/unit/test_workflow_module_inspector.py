from __future__ import annotations

import ast
from pathlib import Path

from paigeant.discovery.workflows import (
    WorkflowModuleInspector,
    discover_workflow_in_module,
)


def _write_module(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "workflow.py"
    path.write_text(content, encoding="utf-8")
    return path


def test_basic_workflow_metadata(tmp_path: Path) -> None:
    source = '''"""My workflow docstring."""

from paigeant import PaigeantAgent, WorkflowDependencies, WorkflowDispatcher

class JokeDeps(WorkflowDependencies):
    pass

main_dispatcher = WorkflowDispatcher()

primary_agent = PaigeantAgent(
    "anthropic:model",
    dispatcher=main_dispatcher,
    name="primary_agent",
    deps_type=JokeDeps,
)
secondary = PaigeantAgent("anthropic:model", dispatcher=main_dispatcher)
'''
    module_path = _write_module(tmp_path, source)

    tree = ast.parse(source)
    inspector = WorkflowModuleInspector(path=module_path, module="demo.workflow")
    inspector.visit(tree)
    definition = inspector.build_definition(docstring=ast.get_docstring(tree))

    assert definition is not None
    assert definition.description == "My workflow docstring."
    assert definition.dispatchers == ("main_dispatcher",)
    assert len(definition.agents) == 2

    primary = definition.agents[0]
    assert primary.name == "primary_agent"
    assert primary.defined_inline is True
    assert primary.agent_key == "primary_agent"
    assert primary.dependency == "JokeDeps"
    assert primary.dispatcher == "main_dispatcher"
    assert primary.source and primary.source.file_path == module_path

    secondary = definition.agents[1]
    assert secondary.name == "secondary"
    assert secondary.defined_inline is True
    assert secondary.dispatcher == "main_dispatcher"

    dependency_names = {dep.name for dep in definition.dependencies}
    assert dependency_names == {"JokeDeps"}
    assert definition.metadata.get("agent_count") == 2


def test_returns_none_when_no_dispatcher(tmp_path: Path) -> None:
    source = """from paigeant import PaigeantAgent

standalone = PaigeantAgent("model")
"""
    module_path = _write_module(tmp_path, source)

    result = discover_workflow_in_module(module_path)

    assert result is None


def test_alias_detection(tmp_path: Path) -> None:
    source = """from paigeant import WorkflowDispatcher
from paigeant.agent.wrapper import PaigeantAgent as AgentAlias

custom = WorkflowDispatcher()

agent = AgentAlias("model", dispatcher=custom, name="alias_agent")
"""
    module_path = _write_module(tmp_path, source)

    result = discover_workflow_in_module(module_path)

    assert result is not None
    assert result.dispatchers == ("custom",)
    assert result.agents[0].name == "alias_agent"
    assert result.agents[0].dispatcher == "custom"
