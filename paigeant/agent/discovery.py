"""Utilities for discovering Paigeant agents in the environment."""

from __future__ import annotations

import pkgutil
import sys
from importlib import import_module
from importlib.util import find_spec, module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent

from paigeant.cli_utils.fs import _iter_python_files
from paigeant.discovery.agents import ImportedSymbol, inspect_agents_in_module
from paigeant.discovery.entities import AgentDefinition


class _ModuleReport(BaseModel):
    """Summary of agent-related metadata discovered in a module."""

    path: Path
    module: Optional[str]
    package: Optional[str]
    is_package: bool
    definitions: tuple[AgentDefinition, ...]
    export_names: frozenset[str]
    imports: tuple[ImportedSymbol, ...]

    model_config = ConfigDict(frozen=True)


def _module_name_from_path(
    search_root: Path, module_root: Path, file_path: Path
) -> tuple[Optional[str], bool]:
    """Return dotted module path and package flag for ``file_path``."""

    try:
        relative = file_path.relative_to(module_root)
    except ValueError:
        if search_root.is_file() and file_path == search_root:
            return search_root.stem, False
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


def _build_symbol_index(
    reports: list[_ModuleReport],
) -> Dict[str, Dict[str, AgentDefinition]]:
    symbol_map: Dict[str, Dict[str, AgentDefinition]] = {}
    reports_by_module: Dict[str, _ModuleReport] = {
        report.module: report for report in reports if report.module
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


def _create_report(
    path: Path, module_name: Optional[str], is_package: bool
) -> Optional[_ModuleReport]:
    try:
        report = inspect_agents_in_module(path, module=module_name)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None

    package_name = _package_name_for_module(module_name, is_package)

    return _ModuleReport(
        path=path,
        module=module_name,
        package=package_name,
        is_package=is_package,
        definitions=report.definitions,
        export_names=frozenset(report.export_names),
        imports=report.imported_symbols,
    )


def _analyze_module(
    py_file: Path, search_root: Path, module_root: Path
) -> Optional[_ModuleReport]:
    module_name, is_package = _module_name_from_path(search_root, module_root, py_file)
    return _create_report(py_file, module_name, is_package)


def _candidate_roots(search_root: Path, module_root: Path) -> tuple[Path, ...]:
    roots: list[Path] = []

    def _add(path: Optional[Path]) -> None:
        if path is None:
            return
        try:
            resolved = path.resolve()
        except OSError:
            return
        if not resolved.exists():
            return
        directory = resolved if resolved.is_dir() else resolved.parent
        if directory == directory.parent:
            return
        if directory not in roots:
            roots.append(directory)

    _add(Path.cwd())
    _add(module_root)
    _add(module_root.parent)
    if search_root.is_file():
        _add(search_root.parent)
    else:
        _add(search_root)

    return tuple(roots)


def _within_allowed_roots(path: Path, roots: tuple[Path, ...]) -> bool:
    for root in roots:
        try:
            path.resolve().relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _resolve_module_origin(
    module_name: str, allowed_roots: tuple[Path, ...]
) -> tuple[Optional[Path], bool]:
    try:
        spec = find_spec(module_name)
    except (ImportError, ValueError):
        spec = None

    if spec and spec.origin not in {None, "namespace", "built-in"}:
        origin_path = Path(spec.origin)
        if origin_path.suffix == ".py" and origin_path.exists():
            if not allowed_roots or _within_allowed_roots(origin_path, allowed_roots):
                return origin_path, bool(spec.submodule_search_locations)

    module_parts = Path(*module_name.split("."))
    search_roots = allowed_roots or (Path.cwd(),)
    for root in search_roots:
        try:
            resolved_root = root.resolve()
        except OSError:
            continue

        candidate_file = (resolved_root / module_parts).with_suffix(".py")
        if candidate_file.exists():
            return candidate_file, False

        candidate_init = resolved_root / module_parts / "__init__.py"
        if candidate_init.exists():
            return candidate_init, True

    return None, False


def _analyze_imported_module(
    module_name: str, allowed_roots: tuple[Path, ...]
) -> Optional[_ModuleReport]:
    origin_path, is_package = _resolve_module_origin(module_name, allowed_roots)
    if origin_path is None:
        return None
    return _create_report(origin_path, module_name, is_package)


def _extend_reports_with_imports(
    reports: list[_ModuleReport], search_root: Path, module_root: Path
) -> None:
    if not reports:
        return

    allowed_roots = _candidate_roots(search_root, module_root)

    known_modules: dict[str, _ModuleReport] = {
        report.module: report for report in reports if report.module
    }

    visited = set(known_modules)
    queue: list[_ModuleReport] = [report for report in reports if report.module]

    while queue:
        report = queue.pop()
        for symbol in report.imports:
            target_module = _resolve_imported_module(report.package, symbol)
            if not target_module or target_module in visited:
                continue
            visited.add(target_module)
            extra_report = _analyze_imported_module(target_module, allowed_roots)
            if extra_report is None:
                continue
            reports.append(extra_report)
            if extra_report.module and extra_report.module not in known_modules:
                known_modules[extra_report.module] = extra_report
                queue.append(extra_report)


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
            except Exception:
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

    _extend_reports_with_imports(reports, resolved_path, module_root)

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
