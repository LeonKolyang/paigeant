from pathlib import Path

from paigeant.discovery import (
    AgentDefinition,
    DependencyDefinition,
    DiscoverySource,
    WorkflowAgentRef,
    WorkflowDefinition,
    agent_definition_to_legacy,
    workflow_definition_to_legacy,
)


def test_workflow_definition_to_legacy_deduplicates_and_preserves_metadata() -> None:
    source = DiscoverySource(file_path=Path("workflows/example.py"))
    definition = WorkflowDefinition(
        source=source,
        description="Example workflow",
        dispatchers=("primary", "primary"),
        agents=(
            WorkflowAgentRef(name="alpha"),
            WorkflowAgentRef(name="alpha"),
            WorkflowAgentRef(name="beta"),
        ),
        dependencies=(
            DependencyDefinition(name="HttpKey"),
            DependencyDefinition(name="HttpKey"),
            DependencyDefinition(name="Database"),
        ),
        metadata={"topic": "jokes"},
    )

    result = workflow_definition_to_legacy(definition)

    assert result["path"] == source.file_path
    assert result["description"] == "Example workflow"
    assert result["agents"] == ["alpha", "beta"]
    assert result["dependencies"] == ["HttpKey", "Database"]
    assert result["dispatchers"] == ["primary", "primary"]
    assert result["metadata"] == {"topic": "jokes"}


def test_workflow_definition_to_legacy_normalizes_missing_values() -> None:
    source = DiscoverySource(file_path=Path("workflows/empty.py"))
    definition = WorkflowDefinition(source=source)

    result = workflow_definition_to_legacy(definition)

    assert result["description"] == ""
    assert result["agents"] == []
    assert result["dependencies"] == []
    assert result["dispatchers"] == []
    assert result["metadata"] == {}


def test_agent_definition_to_legacy_deduplicates_and_copies_fields() -> None:
    source = DiscoverySource(file_path=Path("agents/example.py"))
    definition = AgentDefinition(
        name="topic_extractor",
        source=source,
        dispatcher="Dispatcher",
        dependencies=(
            DependencyDefinition(name="HttpKey"),
            DependencyDefinition(name="HttpKey"),
            DependencyDefinition(name="Logger"),
        ),
        exports=("TopicExtractor", "TopicExtractor", "topic_extractor"),
        attributes={"description": "Extract topics"},
    )

    result = agent_definition_to_legacy(definition)

    assert result["name"] == "topic_extractor"
    assert result["path"] == source.file_path
    assert result["dispatcher"] == "Dispatcher"
    assert result["dependencies"] == ["HttpKey", "Logger"]
    assert result["exports"] == ["TopicExtractor", "topic_extractor"]
    assert result["attributes"] == {"description": "Extract topics"}
    assert result["attributes"] is not definition.attributes


def test_agent_definition_to_legacy_handles_missing_fields() -> None:
    source = DiscoverySource(file_path=Path("agents/minimal.py"))
    definition = AgentDefinition(name="minimal", source=source)

    result = agent_definition_to_legacy(definition)

    assert result["dispatcher"] is None
    assert result["dependencies"] == []
    assert result["exports"] == []
    assert result["attributes"] == {}
