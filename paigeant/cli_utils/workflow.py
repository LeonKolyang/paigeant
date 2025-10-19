"""Utility functions to interact with workflow files and runs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from paigeant.discovery import WorkflowDefinition, discover_workflow_in_module

from .fs import _load_gitignore_patterns, _should_ignore_path


def _analyze_workflow_file(path: Path) -> Optional[WorkflowDefinition]:
    return discover_workflow_in_module(path)


def _format_workflow_path(path: Path, search_path: Path) -> str:
    resolved_path = path.resolve()
    candidate_bases = []
    if search_path.is_dir():
        candidate_bases.append(search_path.resolve())
    else:
        candidate_bases.append(search_path.parent.resolve())
    candidate_bases.append(Path.cwd())

    for base in candidate_bases:
        try:
            rel = resolved_path.relative_to(base)
            return f"./{rel}"
        except ValueError:
            continue
    return str(path)


def _unique_preserve_order(values: Iterable[Optional[str]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def workflow_agent_names(definition: WorkflowDefinition) -> list[str]:
    """Return unique agent names referenced in ``definition`` preserving order."""

    return _unique_preserve_order(ref.name for ref in definition.agents)


def workflow_dependency_names(definition: WorkflowDefinition) -> list[str]:
    """Return unique dependency names referenced in ``definition`` preserving order."""

    return _unique_preserve_order(dep.name for dep in definition.dependencies)
