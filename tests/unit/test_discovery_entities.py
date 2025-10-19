from pathlib import Path

import pytest

from paigeant.discovery.entities import (
    AgentDefinition,
    DependencyDefinition,
    DiscoverySource,
    SourcePosition,
    SourceSpan,
    WorkflowAgentRef,
    WorkflowDefinition,
)


def test_source_span_requires_valid_order() -> None:
    start = SourcePosition(line=3, column=0)
    end = SourcePosition(line=2, column=5)
    with pytest.raises(ValueError):
        SourceSpan(start=start, end=end)


def test_agent_definition_defaults_are_immutable() -> None:
    source = DiscoverySource(file_path=Path("agents.py"))
    agent = AgentDefinition(name="demo_agent", source=source)

    assert agent.dependencies == ()
    assert agent.exports == ()
    assert agent.attributes == {}

    with pytest.raises(AttributeError):
        agent.dependencies.append(  # type: ignore[attr-defined]
            DependencyDefinition(name="Deps")
        )


def test_workflow_definition_holds_agent_refs() -> None:
    source = DiscoverySource(file_path=Path("workflow.py"))
    agent_ref = WorkflowAgentRef(name="demo", defined_inline=True)
    workflow = WorkflowDefinition(source=source, agents=[agent_ref])

    assert workflow.agents[0].defined_inline is True
    with pytest.raises(AttributeError):
        workflow.agents.append(  # type: ignore[attr-defined]
            WorkflowAgentRef(name="other")
        )
