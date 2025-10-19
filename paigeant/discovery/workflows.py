"""Workflow discovery via static AST inspection."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict

from ._ast_utils import get_expr_name, node_span
from .base_inspector import BaseInspector
from .entities import (
    DependencyDefinition,
    DiscoverySource,
    SourceSpan,
    WorkflowAgentRef,
    WorkflowDefinition,
)


class WorkflowModuleInspector(BaseInspector):
    """Collect workflow metadata defined within a Python module."""

    def __init__(self, *, path: Path, module: Optional[str] = None) -> None:
        super().__init__(path=path, module=module)
        self.register_symbol("WorkflowDispatcher", {"WorkflowDispatcher"})
        self.register_symbol("PaigeantAgent", {"PaigeantAgent"})
        self.register_symbol("WorkflowDependencies", {"WorkflowDependencies"})
        self.add_import_rule("WorkflowDispatcher", ("WorkflowDispatcher",))
        self.add_import_rule("PaigeantAgent", ("PaigeantAgent",))
        self.add_import_rule("WorkflowDependencies", ("WorkflowDependencies",))
        self.dispatcher_names: list[str] = []
        self.found_dispatcher = False
        self._agent_probes: list[_AgentProbe] = []
        self._dependency_classes: list[_DependencyCandidate] = []

    # ------------------------------------------------------------------
    # Assignment handling
    # ------------------------------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:  # pragma: no cover - AST
        self._handle_assignment(node.value, node.targets)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # pragma: no cover - AST
        self._handle_assignment(node.value, (node.target,))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # pragma: no cover - AST
        if self.call_matches(node, "WorkflowDispatcher"):
            self.found_dispatcher = True
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # pragma: no cover - AST
        for base in node.bases:
            base_name = get_expr_name(base)
            deps_aliases = self.aliases_for("WorkflowDependencies")
            if base_name and base_name.split(".")[-1] in deps_aliases:
                self._dependency_classes.append(
                    _DependencyCandidate(name=node.name, span=node_span(node))
                )
                break
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Build workflow definition
    # ------------------------------------------------------------------
    def build_definition(
        self, *, docstring: Optional[str]
    ) -> Optional[WorkflowDefinition]:
        if not self.found_dispatcher and not self.dispatcher_names:
            return None

        description = ""
        if docstring:
            stripped = docstring.strip()
            if stripped:
                description = stripped.splitlines()[0]

        source = DiscoverySource(file_path=self.path, module=self.module)

        dispatchers = tuple(self.dispatcher_names)
        agents = tuple(self._build_agent_ref(probe) for probe in self._agent_probes)
        dependencies = tuple(self._collect_dependencies())

        metadata = {}
        if self._agent_probes:
            metadata["agent_count"] = len(self._agent_probes)

        return WorkflowDefinition(
            source=source,
            description=description or None,
            dispatchers=dispatchers,
            agents=agents,
            dependencies=dependencies,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _handle_assignment(
        self, value: ast.AST | None, targets: Iterable[ast.AST]
    ) -> None:
        if value is None:
            return
        if self.call_matches(value, "WorkflowDispatcher"):
            self._mark_dispatcher(targets)
            return
        if self.call_matches(value, "PaigeantAgent"):
            assigned = self.assigned_names(targets)
            self._agent_probes.append(self._parse_agent_call(value, assigned))

    def _mark_dispatcher(self, targets: Iterable[ast.AST]) -> None:
        self.found_dispatcher = True
        for name in self.assigned_names(targets):
            if name and name not in self.dispatcher_names:
                self.dispatcher_names.append(name)

    def _parse_agent_call(
        self, call: ast.Call, assigned_names: tuple[str, ...]
    ) -> _AgentProbe:
        explicit_name: Optional[str] = None
        dispatcher: Optional[str] = None
        deps_type: Optional[str] = None
        deps_expr: Optional[str] = None
        for keyword in call.keywords:
            if keyword.arg is None:
                continue
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    explicit_name = keyword.value.value
            elif keyword.arg == "dispatcher":
                dispatcher = get_expr_name(keyword.value)
            elif keyword.arg == "deps_type":
                deps_type = get_expr_name(keyword.value)
            elif keyword.arg == "deps":
                deps_expr = get_expr_name(keyword.value)

        variables = tuple(name for name in assigned_names if name)
        span = node_span(call)
        return _AgentProbe(
            variables=variables,
            explicit_name=explicit_name,
            dispatcher=dispatcher,
            deps_type=deps_type,
            deps_expr=deps_expr,
            span=span,
        )

    def _build_agent_ref(self, probe: _AgentProbe) -> WorkflowAgentRef:
        name = probe.explicit_name or (probe.variables[0] if probe.variables else None)
        if not name:
            name = "<anonymous-agent>"

        reference = WorkflowAgentRef(
            name=name,
            dispatcher=probe.dispatcher,
            dependency=probe.deps_type or probe.deps_expr,
            defined_inline=bool(probe.variables),
            source=DiscoverySource(
                file_path=self.path,
                module=self.module,
                span=probe.span,
            ),
            agent_key=probe.variables[0] if probe.variables else probe.explicit_name,
        )
        return reference

    def _collect_dependencies(self) -> list[DependencyDefinition]:
        collected: dict[str, DependencyDefinition] = {}

        for probe in self._agent_probes:
            if probe.deps_type and probe.deps_type not in collected:
                collected[probe.deps_type] = DependencyDefinition(
                    name=probe.deps_type,
                    kind="type",
                    source=DiscoverySource(
                        file_path=self.path,
                        module=self.module,
                        span=probe.span,
                    ),
                )
            if probe.deps_expr and probe.deps_expr not in collected:
                collected[probe.deps_expr] = DependencyDefinition(
                    name=probe.deps_expr,
                    kind="value",
                    source=DiscoverySource(
                        file_path=self.path,
                        module=self.module,
                        span=probe.span,
                    ),
                )

        for dep in self._dependency_classes:
            if dep.name not in collected:
                collected[dep.name] = DependencyDefinition(
                    name=dep.name,
                    kind="class",
                    source=DiscoverySource(
                        file_path=self.path,
                        module=self.module,
                        span=dep.span,
                    ),
                )

        return list(collected.values())


class _AgentProbe(BaseModel):
    variables: tuple[str, ...] = ()
    explicit_name: Optional[str] = None
    dispatcher: Optional[str] = None
    deps_type: Optional[str] = None
    deps_expr: Optional[str] = None
    span: Optional[SourceSpan] = None

    model_config = ConfigDict(frozen=True)


class _DependencyCandidate(BaseModel):
    name: str
    span: Optional[SourceSpan] = None

    model_config = ConfigDict(frozen=True)


def discover_workflow_in_module(
    path: Path, *, module: Optional[str] = None
) -> Optional[WorkflowDefinition]:
    """Parse and inspect ``path`` returning workflow metadata if present."""

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    inspector = WorkflowModuleInspector(path=path, module=module)
    inspector.visit(tree)
    docstring = ast.get_docstring(tree)
    return inspector.build_definition(docstring=docstring)


__all__ = ["WorkflowModuleInspector", "discover_workflow_in_module"]
