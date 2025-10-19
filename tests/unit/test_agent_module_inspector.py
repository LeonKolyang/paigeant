from __future__ import annotations

import ast
from pathlib import Path

import pytest

from paigeant.discovery.agents import AgentModuleInspector, discover_agents_in_module


def _write_module(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "sample.py"
    path.write_text(content, encoding="utf-8")
    return path


def test_discovers_agent_with_explicit_name(tmp_path: Path) -> None:
    source = """
from paigeant import PaigeantAgent, WorkflowDispatcher

service_dispatcher = WorkflowDispatcher()

__all__ = ["primary_agent"]

primary_agent = PaigeantAgent(
    "anthropic:model",
    dispatcher=service_dispatcher,
    deps_type=WorkflowDispatcher,
    name="primary_agent",
    can_edit_itinerary=True,
)
"""
    module_path = _write_module(tmp_path, source)

    inspector = AgentModuleInspector(path=module_path, module="test.sample")
    inspector.visit(ast.parse(source))
    results = inspector.build_definitions()

    assert len(results) == 1
    agent = results[0]
    assert agent.name == "primary_agent"
    assert agent.dispatcher == "service_dispatcher"


def test_falls_back_to_assignment_name(tmp_path: Path) -> None:
    source = """
from paigeant import PaigeantAgent

fallback = PaigeantAgent("model", dispatcher=dispatcher)
"""
    module_path = _write_module(tmp_path, source)

    definitions = discover_agents_in_module(module_path)

    assert len(definitions) == 1
    agent = definitions[0]
    assert agent.name == "fallback"
    assert agent.dispatcher == "dispatcher"
    assert agent.exports == ("fallback",)


def test_detects_import_alias(tmp_path: Path) -> None:
    source = """
from paigeant.agent.wrapper import PaigeantAgent as CustomAgent

second = CustomAgent("model", dispatcher=main_dispatcher)
"""
    module_path = _write_module(tmp_path, source)

    definitions = discover_agents_in_module(module_path)

    assert len(definitions) == 1
    assert definitions[0].name == "second"
    assert definitions[0].dispatcher == "main_dispatcher"


@pytest.mark.parametrize(
    "assignment",
    [
        "PaigeantAgent('model', dispatcher=disp)",
        "PaigeantAgent('model', dispatcher=disp, name='override')",
    ],
)
def test_multiple_candidates_record_unique_names(
    tmp_path: Path, assignment: str
) -> None:
    source = f"""
from paigeant import PaigeantAgent

def build():
    agent_var = {assignment}
    return agent_var
"""
    module_path = _write_module(tmp_path, source)

    definitions = discover_agents_in_module(module_path)

    # Function-local assignment should still resolve name, using explicit name if present
    assert len(definitions) == 1
    agent = definitions[0]
    if "override" in assignment:
        assert agent.name == "override"
    else:
        assert agent.name == "agent_var"
