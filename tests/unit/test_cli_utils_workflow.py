from pathlib import Path

from paigeant.cli_utils.workflow import workflow_agent_names, workflow_dependency_names
from paigeant.discovery import (
    DependencyDefinition,
    DiscoverySource,
    WorkflowAgentRef,
    WorkflowDefinition,
)


def _definition_with(
    *,
    agents: tuple[WorkflowAgentRef, ...],
    dependencies: tuple[DependencyDefinition, ...],
) -> WorkflowDefinition:
    return WorkflowDefinition(
        source=DiscoverySource(file_path=Path("workflows/example.py")),
        agents=agents,
        dependencies=dependencies,
    )


def test_workflow_agent_names_deduplicates_and_ignores_missing() -> None:
    definition = _definition_with(
        agents=(
            WorkflowAgentRef(name="alpha"),
            WorkflowAgentRef(name="alpha"),
            WorkflowAgentRef(name=""),
            WorkflowAgentRef(name="beta"),
        ),
        dependencies=(),
    )

    assert workflow_agent_names(definition) == ["alpha", "beta"]


def test_workflow_dependency_names_deduplicates_and_ignores_missing() -> None:
    definition = _definition_with(
        agents=(),
        dependencies=(
            DependencyDefinition(name="HttpKey"),
            DependencyDefinition(name="HttpKey"),
            DependencyDefinition(name=""),
            DependencyDefinition(name="Database"),
        ),
    )

    assert workflow_dependency_names(definition) == ["HttpKey", "Database"]
