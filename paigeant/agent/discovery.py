"""Utilities for discovering Paigeant agents in the environment."""

from __future__ import annotations

import ast
import pkgutil
import sys
from dataclasses import dataclass
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Dict, Optional

from pydantic_ai import Agent

from paigeant.cli_utils.fs import _iter_python_files
from paigeant.discovery.agents import AgentModuleInspector, ImportedSymbol
from paigeant.discovery.entities import AgentDefinition


@dataclass(frozen=True)
class _ModuleReport:
    """Summary of agent-related metadata discovered in a module."""

    path: Path
    module: Optional[str]
    package: Optional[str]
    is_package: bool
    definitions: tuple[AgentDefinition, ...]
    export_names: frozenset[str]
    imports: tuple[ImportedSymbol, ...]


def _module_name_from_path(
    search_root: Path, module_root: Path, file_path: Path
) -> tuple[Optional[str], bool]:
    """Return dotted module path and package flag for ``file_path``."""

    if search_root.is_file():
        if file_path == search_root:
            return search_root.stem, False
        return None, False

    try:
        relative = file_path.relative_to(module_root)
    except ValueError:
        return None, False

    parts = list(relative.parts)
    if not parts:
        return None, False

    is_package = parts[-1] == "__init__.py"
    if is_package:
        parts = parts[:-1]
    else:
        leaf = parts[-1]
        parts[-1] = leaf[:-3] if leaf.endswith(".py") else leaf

    prefix: list[str] = []
    root_init = module_root / "__init__.py"
    if module_root.is_dir() and root_init.exists():
        prefix.append(module_root.name)

    module_parts = prefix + parts if parts else prefix
    module_name = ".".join(module_parts) if module_parts else None
    return module_name, is_package


def _package_name_for_module(
    module_name: Optional[str], is_package: bool
) -> Optional[str]:
    if module_name is None:
        return None
    if is_package:
        return module_name
    if "." in module_name:
        return module_name.rsplit(".", 1)[0]
    return None


def _resolve_imported_module(
    package: Optional[str], symbol: ImportedSymbol
) -> Optional[str]:
    level = symbol.level or 0
    target = symbol.module or ""
    if level == 0:
        return target or None
    if not package:
        return None

    dot = len(package)
    for _ in range(level, 1, -1):
        try:
            dot = package.rindex(".", 0, dot)
        except ValueError:
            return None

    prefix = package[:dot]
    if target:
        if prefix:
            return f"{prefix}.{target}"
        return target
    return prefix or None


def _lookup_definition(
    symbol_map: Dict[str, Dict[str, AgentDefinition]],
    module_name: Optional[str],
    symbol: ImportedSymbol,
) -> Optional[AgentDefinition]:
    if not module_name:
        return None
    exports = symbol_map.get(module_name)
    if not exports:
        return None
    symbol_key = symbol.name.split(".")[-1]
    return exports.get(symbol_key)


def _build_symbol_index(reports: list[_ModuleReport]) -> Dict[str, Dict[str, AgentDefinition]]:
    symbol_map: Dict[str, Dict[str, AgentDefinition]] = {}
    reports_by_module: Dict[str, _ModuleReport] = {
        report.module: report
        for report in reports
        if report.module
    }

    for report in reports:
        if not report.module:
            continue
        module_exports = symbol_map.setdefault(report.module, {})
        for definition in report.definitions:
            for export in definition.exports:
                module_exports.setdefault(export, definition)

    changed = True
    while changed:
        changed = False
        for module_name, report in reports_by_module.items():
            module_exports = symbol_map.setdefault(module_name, {})
            export_names = report.export_names
            for symbol in report.imports:
                alias = symbol.alias
                if not alias:
                    continue
                if export_names and alias not in export_names:
                    continue
                target_module = _resolve_imported_module(report.package, symbol)
                if not target_module:
                    continue
                definition = _lookup_definition(symbol_map, target_module, symbol)
                if not definition:
                    continue
                if alias not in module_exports:
                    module_exports[alias] = definition
                    changed = True

    return symbol_map


def _analyze_module(
    py_file: Path, search_root: Path, module_root: Path
) -> Optional[_ModuleReport]:
    module_name, is_package = _module_name_from_path(search_root, module_root, py_file)
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None

    inspector = AgentModuleInspector(path=py_file, module=module_name)
    inspector.visit(tree)
    definitions = inspector.build_definitions()
    package_name = _package_name_for_module(module_name, is_package)

    return _ModuleReport(
        path=py_file,
        module=module_name,
        package=package_name,
        is_package=is_package,
        definitions=definitions,
        export_names=frozenset(inspector.export_names),
        imports=inspector.imported_symbols,
    )


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
            if module_name.startswith("paigeant"):
                continue
            try:
                module_obj = import_module(module_name)
                if hasattr(module_obj, agent_name):
                    return getattr(module_obj, agent_name)
            except Exception as e:
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


def discover_agents_in_path(
    search_path: Path, respect_gitignore: bool = True
) -> list[dict[str, object]]:
    """Discover Paigeant agents by analyzing Python modules under ``search_path``."""

    resolved_path = search_path.expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Search path does not exist: {resolved_path}")

    module_root = resolved_path if resolved_path.is_dir() else resolved_path.parent

    reports: list[_ModuleReport] = []
    for py_file in _iter_python_files(resolved_path, respect_gitignore):
        report = _analyze_module(py_file, resolved_path, module_root)
        if report is None:
            continue
        reports.append(report)

    symbol_index = _build_symbol_index(reports)

    discoveries: list[dict[str, object]] = []
    seen: set[tuple[str, Path]] = set()

    for report in reports:
        for definition in report.definitions:
            candidates = [definition.name, *definition.exports]
            for agent_name in candidates:
                if not agent_name:
                    continue
                key = (agent_name, report.path)
                if key in seen:
                    continue
                discoveries.append({"name": agent_name, "path": report.path})
                seen.add(key)

    for report in reports:
        module_name = report.module
        if not module_name:
            continue
        exported = symbol_index.get(module_name, {})
        if not exported:
            continue

        direct_names = {
            export_name
            for definition in report.definitions
            for export_name in definition.exports
        }

        for alias in exported:
            if alias in direct_names:
                continue
            key = (alias, report.path)
            if key in seen:
                continue
            discoveries.append({"name": alias, "path": report.path})
            seen.add(key)

    discoveries.sort(key=lambda item: (str(item["path"]), item["name"]))

    return discoveries
