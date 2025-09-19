"""Utility functions to interact with workflow files and runs."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional


class _WorkflowModuleAnalyzer(ast.NodeVisitor):
    """Collect metadata about workflow dispatcher usage in a module."""

    def __init__(self) -> None:
        self.dispatcher_aliases = {"WorkflowDispatcher"}
        self.agent_aliases = {"PaigeantAgent"}
        self.deps_aliases = {"WorkflowDependencies"}
        self.dispatcher_names: list[str] = []
        self.agent_infos: list[dict[str, object]] = []
        self.dependency_classes: list[str] = []
        self.found_dispatcher = False

    # ------------------------------------------------------------------
    # Import handling
    # ------------------------------------------------------------------
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # pragma: no cover - ast
        for alias in node.names:
            target = alias.name.split(".")[-1]
            alias_name = alias.asname or alias.name
            if target == "WorkflowDispatcher":
                self.dispatcher_aliases.add(alias_name)
            elif target == "PaigeantAgent":
                self.agent_aliases.add(alias_name)
            elif target == "WorkflowDependencies":
                self.deps_aliases.add(alias_name)
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Node visitors capturing metadata
    # ------------------------------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:  # pragma: no cover - ast
        value = node.value
        if self._is_call_to(value, self.dispatcher_aliases):
            self.found_dispatcher = True
            for target in node.targets:
                name = self._name_from_target(target)
                if name and name not in self.dispatcher_names:
                    self.dispatcher_names.append(name)
        elif self._is_call_to(value, self.agent_aliases):
            info = self._parse_agent_call(value)
            variables = [
                self._name_from_target(target)
                for target in node.targets
                if self._name_from_target(target)
            ]
            info["variables"] = variables
            self.agent_infos.append(info)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # pragma: no cover - ast
        value = node.value
        if value and self._is_call_to(value, self.dispatcher_aliases):
            self.found_dispatcher = True
            name = self._name_from_target(node.target)
            if name and name not in self.dispatcher_names:
                self.dispatcher_names.append(name)
        elif value and self._is_call_to(value, self.agent_aliases):
            info = self._parse_agent_call(value)
            target_name = self._name_from_target(node.target)
            info["variables"] = [target_name] if target_name else []
            self.agent_infos.append(info)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # pragma: no cover - ast
        if self._is_call_to(node, self.dispatcher_aliases):
            self.found_dispatcher = True
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # pragma: no cover - ast
        for base in node.bases:
            base_name = self._get_expr_name(base)
            if base_name and base_name.split(".")[-1] in self.deps_aliases:
                if node.name not in self.dependency_classes:
                    self.dependency_classes.append(node.name)
                break
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _is_call_to(self, value: ast.AST, candidates: set[str]) -> bool:
        if not isinstance(value, ast.Call):
            return False
        func_name = self._get_expr_name(value.func)
        if not func_name:
            return False
        last = func_name.split(".")[-1]
        return func_name in candidates or last in candidates

    def _name_from_target(self, target: ast.AST) -> Optional[str]:
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return self._get_expr_name(target)
        return None

    def _get_expr_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            value = self._get_expr_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        if isinstance(node, ast.Call):
            return self._get_expr_name(node.func)
        if isinstance(node, ast.Subscript):
            return self._get_expr_name(node.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _parse_agent_call(self, call: ast.Call) -> dict[str, object]:
        info: dict[str, object] = {"name": None, "dispatcher": None, "deps_type": None}
        for keyword in call.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    info["name"] = keyword.value.value
            elif keyword.arg == "dispatcher":
                dispatcher_name = self._get_expr_name(keyword.value)
                if dispatcher_name:
                    info["dispatcher"] = dispatcher_name
            elif keyword.arg in {"deps_type", "deps"}:
                deps_name = self._get_expr_name(keyword.value)
                if deps_name:
                    info["deps_type"] = deps_name
        return info


def _analyze_workflow_file(path: Path) -> Optional[dict[str, object]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    analyzer = _WorkflowModuleAnalyzer()
    analyzer.visit(tree)

    if not analyzer.found_dispatcher:
        return None

    docstring = ast.get_docstring(tree) or ""
    description = docstring.strip().splitlines()[0] if docstring.strip() else ""

    agent_names: list[str] = []
    for info in analyzer.agent_infos:
        name = info.get("name")
        if isinstance(name, str) and name:
            if name not in agent_names:
                agent_names.append(name)
            continue
        variables = info.get("variables") or []
        if isinstance(variables, list):
            for variable in variables:
                if (
                    isinstance(variable, str)
                    and variable
                    and variable not in agent_names
                ):
                    agent_names.append(variable)
                    break

    deps: list[str] = []
    for info in analyzer.agent_infos:
        deps_name = info.get("deps_type")
        if isinstance(deps_name, str) and deps_name and deps_name not in deps:
            deps.append(deps_name)
    for cls_name in analyzer.dependency_classes:
        if cls_name not in deps:
            deps.append(cls_name)

    return {
        "path": path,
        "description": description,
        "agents": agent_names,
        "dependencies": deps,
    }


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
