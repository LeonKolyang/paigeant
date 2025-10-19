"""Utilities for discovering Paigeant agents in the environment."""

from __future__ import annotations

import pkgutil
import sys
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Optional

from pydantic_ai import Agent

from paigeant.cli_utils.fs import _iter_python_files
from paigeant.discovery import discover_agents_in_module


def find_agent_in_file(agent_name: str, base_path: Path) -> Agent:
    module_name = base_path.stem
    spec = spec_from_file_location(module_name, base_path)
    if spec and spec.loader:
        module_obj = module_from_spec(spec)
        sys.modules[module_name] = module_obj
        spec.loader.exec_module(module_obj)

        if hasattr(module_obj, agent_name):
            return getattr(module_obj, agent_name)
        else:
            raise ValueError(f"Agent '{agent_name}' not found in file {base_path}")


def find_agent_in_directory(agent_name: str, base_path: Path) -> Agent:
    # Add base_path to sys.path temporarily for imports
    str_base_path = str(base_path)
    if str_base_path not in sys.path:
        sys.path.insert(0, str_base_path)

    try:
        for module in pkgutil.walk_packages([str_base_path]):
            module_name = module.name
            print(f"Checking module: {module_name}")
            if module_name.startswith("paigeant"):
                continue
            try:
                module_obj = import_module(module_name)
                if hasattr(module_obj, agent_name):
                    return getattr(module_obj, agent_name)
            except Exception as e:
                print(f"Error importing {module_name}, working dir {Path.cwd()}: {e}")
                continue
    finally:
        # Clean up sys.path
        if str_base_path in sys.path:
            sys.path.remove(str_base_path)


def discover_agent(agent_name: str, base_path: Optional[Path] = None) -> Agent:
    """Import available modules to locate an agent by name.

    This performs a best-effort scan of modules on the current working
    directory's ``sys.path``. Any module that defines a ``PaigeantAgent``
    with a matching ``name`` will register itself in ``AGENT_REGISTRY``
    when imported. The scan stops once the requested agent is found.

    Args:
        agent_name: Name of the agent to find
        base_path: Path to search - can be a .py file or directory

    Raises:
        ValueError: If no agent with ``agent_name`` can be located.
    """
    search_path = (base_path or Path.cwd()).expanduser()
    if search_path.exists():
        search_path = search_path.resolve()

    # Handle single Python file
    if search_path.suffix == ".py" and search_path.is_file():
        return find_agent_in_file(agent_name, search_path)

    # Handle directory - scan for Python modules
    if search_path.is_dir():
        result = find_agent_in_directory(agent_name, search_path)
        if result is not None:
            return result
        search_hint = f"in directory {search_path}"
    else:
        if base_path is None:
            search_hint = f"in directory {search_path}"
        elif not search_path.exists():
            search_hint = f"because {search_path} does not exist"
        else:
            search_hint = f"because {search_path} is not a Python file or directory"

    raise ValueError(f"Agent '{agent_name}' not found {search_hint}.")


def _extract_agent_names(py_file: Path) -> list[str]:
    """Parse ``py_file`` and return Paigeant agent names defined within."""

    try:
        definitions = discover_agents_in_module(py_file)
    except (OSError, SyntaxError):
        return []

    names: list[str] = []
    for definition in definitions:
        if definition.name and definition.name not in names:
            names.append(definition.name)
        for export in definition.exports:
            if export and export not in names:
                names.append(export)
    return names


def discover_agents_in_path(
    search_path: Path, respect_gitignore: bool = True
) -> list[dict[str, object]]:
    """Discover Paigeant agents by analyzing Python modules under ``search_path``."""

    resolved_path = search_path.expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Search path does not exist: {resolved_path}")

    discoveries: list[dict[str, object]] = []
    seen: set[tuple[str, Path]] = set()

    for py_file in _iter_python_files(resolved_path, respect_gitignore):
        for agent_name in _extract_agent_names(py_file):
            key = (agent_name, py_file)
            if key in seen:
                continue
            discoveries.append({"name": agent_name, "path": py_file})
            seen.add(key)

    discoveries.sort(key=lambda item: (str(item["path"]), item["name"]))

    return discoveries
