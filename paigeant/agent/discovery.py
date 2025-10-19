"""Utilities for discovering Paigeant agents in the environment."""

from __future__ import annotations

import pkgutil
import sys
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Iterable, Optional

from pydantic_ai import Agent

from paigeant.cli_utils.fs import _load_gitignore_patterns, _should_ignore_path
from paigeant.agent.wrapper import PaigeantAgent


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
            raise ValueError(f"Agent {agent_name} not found in file {base_path}")


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
    base_path = base_path if base_path else Path.cwd()

    # Handle single Python file
    if base_path.suffix == ".py" and base_path.is_file():
        return find_agent_in_file(agent_name, base_path)

    # Handle directory - scan for Python modules
    if base_path.is_dir():
        result = find_agent_in_directory(agent_name, base_path)
        if result is not None:
            return result
        else:
            raise ValueError(f"Agent {agent_name} not found in available modules")

    raise ValueError(f"Agent {agent_name} not found in available modules")


def _iter_python_files(search_path: Path, respect_gitignore: bool) -> Iterable[Path]:
    if search_path.is_file():
        yield search_path
        return

    gitignore_patterns = set()
    if respect_gitignore:
        gitignore_patterns = _load_gitignore_patterns(search_path)

    all_python_files = sorted(search_path.rglob("*.py"))
    for py_file in all_python_files:
        if respect_gitignore and _should_ignore_path(py_file, gitignore_patterns, search_path):
            continue
        if py_file.is_file():
            yield py_file


def _module_name_for_file(py_file: Path, base_path: Path) -> str:
    try:
        relative = py_file.relative_to(base_path)
        module_parts = list(relative.with_suffix("").parts)
        if module_parts:
            return "paigeant_discover." + ".".join(module_parts)
    except ValueError:
        pass
    return f"paigeant_discover.{py_file.stem}"


def discover_agents_in_path(
    search_path: Path, respect_gitignore: bool = True
) -> list[dict[str, object]]:
    """Discover Paigeant agents by importing Python modules under ``search_path``."""

    resolved_path = search_path.expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Search path does not exist: {resolved_path}")

    discoveries: list[dict[str, object]] = []
    seen: set[tuple[str, Path]] = set()

    for py_file in _iter_python_files(resolved_path, respect_gitignore):
        module_name = _module_name_for_file(py_file, resolved_path)
        module_obj: Optional[ModuleType] = None
        try:
            spec = spec_from_file_location(module_name, py_file)
            if not spec or not spec.loader:
                continue
            module_obj = module_from_spec(spec)
            sys.modules[module_name] = module_obj
            spec.loader.exec_module(module_obj)
        except SyntaxError:
            continue
        except Exception:
            continue
        finally:
            sys.modules.pop(module_name, None)

        if module_obj is None:
            continue

        for value in vars(module_obj).values():
            if not isinstance(value, PaigeantAgent):
                continue
            agent_name = getattr(value, "name", None)
            if not isinstance(agent_name, str) or not agent_name:
                continue
            key = (agent_name, py_file)
            if key in seen:
                continue
            discoveries.append({"name": agent_name, "path": py_file})
            seen.add(key)

    discoveries.sort(key=lambda item: (str(item["path"]), item["name"]))

    return discoveries
