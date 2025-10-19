"""Helpers for translating discovery definitions into legacy metadata structures."""

from __future__ import annotations

from collections.abc import Iterable

from .entities import (
    AgentDefinition,
    DependencyDefinition,
    WorkflowAgentRef,
    WorkflowDefinition,
)

__all__ = [
    "agent_definition_to_legacy",
    "workflow_definition_to_legacy",
]


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _iter_agent_names(refs: Iterable[WorkflowAgentRef]) -> Iterable[str]:
    for ref in refs:
        if ref.name:
            yield ref.name


def _iter_dependency_names(
    dependencies: Iterable[DependencyDefinition],
) -> Iterable[str]:
    for dep in dependencies:
        if dep.name:
            yield dep.name


def agent_definition_to_legacy(definition: AgentDefinition) -> dict[str, object]:
    """Return legacy agent metadata derived from an AgentDefinition."""

    export_names = _unique_preserve_order(definition.exports)
    dependencies = _unique_preserve_order(
        _iter_dependency_names(definition.dependencies)
    )

    return {
        "name": definition.name,
        "path": definition.source.file_path,
        "dispatcher": definition.dispatcher,
        "exports": export_names,
        "dependencies": dependencies,
        "attributes": dict(definition.attributes),
    }


def workflow_definition_to_legacy(definition: WorkflowDefinition) -> dict[str, object]:
    """Return legacy workflow metadata derived from a WorkflowDefinition."""

    agents = _unique_preserve_order(_iter_agent_names(definition.agents))
    dependencies = _unique_preserve_order(
        _iter_dependency_names(definition.dependencies)
    )

    return {
        "path": definition.source.file_path,
        "description": definition.description or "",
        "agents": agents,
        "dependencies": dependencies,
        "dispatchers": list(definition.dispatchers),
        "metadata": dict(definition.metadata),
    }
