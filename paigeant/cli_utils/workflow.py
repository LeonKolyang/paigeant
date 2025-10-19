"""Utility functions to interact with workflow files and runs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from paigeant.discovery import (
    discover_workflow_in_module,
    workflow_definition_to_legacy,
)

from .fs import _load_gitignore_patterns, _should_ignore_path


def _analyze_workflow_file(path: Path) -> Optional[dict[str, object]]:
    definition = discover_workflow_in_module(path)
    if definition is None:
        return None
    return workflow_definition_to_legacy(definition)


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
