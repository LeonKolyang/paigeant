"""Agent discovery via static AST inspection."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict

from ._ast_utils import get_expr_name, node_span
from .base_inspector import BaseInspector
from .entities import AgentDefinition, DependencyDefinition, DiscoverySource, SourceSpan


class _AgentCandidate(BaseModel):
    assigned_names: tuple[str, ...] = ()
    explicit_name: Optional[str] = None
    dispatcher: Optional[str] = None
    deps_type: Optional[str] = None
    deps_expr: Optional[str] = None
    span: Optional[SourceSpan] = None

    model_config = ConfigDict(frozen=True)


class ImportedSymbol(BaseModel):
    """Representation of a symbol imported into a module."""

    module: Optional[str] = None
    name: str
    alias: str
    level: int = 0
    span: Optional[SourceSpan] = None

    model_config = ConfigDict(frozen=True)


@dataclass(frozen=True)
class ModuleAgentReport:
    """Summary of Paigeant agent analysis for a module."""

    path: Path
    module: Optional[str]
    definitions: tuple[AgentDefinition, ...]
    export_names: tuple[str, ...]
    imported_symbols: tuple[ImportedSymbol, ...]


class AgentModuleInspector(BaseInspector):
    """Collect Paigeant agent definitions from a Python module."""

    def __init__(self, *, path: Path, module: Optional[str] = None) -> None:
        super().__init__(path=path, module=module)
        self.register_symbol("PaigeantAgent", {"PaigeantAgent"})
        self.add_import_rule("PaigeantAgent", ("PaigeantAgent",))
        self.add_import_rule(
            "PaigeantAgent",
            ("Agent",),
            modules=("paigeant.agent.wrapper", "paigeant"),
        )
        self._candidates: list[_AgentCandidate] = []
        self._export_names: set[str] = set()
        self._imported_symbols: list[ImportedSymbol] = []

    # ------------------------------------------------------------------
    # Assignment handling
    # ------------------------------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:
        if self._handle_assignment(node.value, node.targets):
            return
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._handle_assignment(node.value, (node.target,)):
            return
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # pragma: no cover - AST
        for alias in node.names:
            if alias.name == "*":
                continue
            alias_name = alias.asname or alias.name.split(".")[-1]
            self._imported_symbols.append(
                ImportedSymbol(
                    module=node.module,
                    name=alias.name,
                    alias=alias_name,
                    level=node.level or 0,
                    span=node_span(node),
                )
            )
        super().visit_ImportFrom(node)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _handle_assignment(
        self, value: ast.AST | None, targets: Iterable[ast.AST]
    ) -> bool:
        if value is None:
            return False
        if self._collect_exports(targets, value):
            return True
        if self.call_matches(value, "PaigeantAgent"):
            assigned = self.assigned_names(targets)
            self._candidates.append(self._parse_agent_call(value, assigned))
            return True
        return False

    def _collect_exports(self, targets: Iterable[ast.AST], value: ast.AST) -> bool:
        """Record ``__all__`` assignments for export awareness."""

        for target in targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                names = self._extract_export_names(value)
                self._export_names.update(names)
                return True
        return False

    def _extract_export_names(self, value: ast.AST) -> list[str]:
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            names: list[str] = []
            for element in value.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    names.append(element.value)
            return names
        return []

    def _parse_agent_call(
        self, call: ast.Call, assigned_names: tuple[str, ...]
    ) -> _AgentCandidate:
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

        candidate = _AgentCandidate(
            assigned_names=assigned_names,
            explicit_name=explicit_name,
            dispatcher=dispatcher,
            deps_type=deps_type,
            deps_expr=deps_expr,
            span=node_span(call),
        )
        return candidate

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build_definitions(self) -> tuple[AgentDefinition, ...]:
        definitions: list[AgentDefinition] = []
        for index, candidate in enumerate(self._candidates, start=1):
            agent_name = self._resolve_agent_name(candidate, index)
            dependencies = self._build_dependencies(candidate)
            exports = self._resolve_exports(candidate.assigned_names)

            source = DiscoverySource(
                file_path=self.path,
                module=self.module,
                span=candidate.span,
            )
            definitions.append(
                AgentDefinition(
                    name=agent_name,
                    source=source,
                    dispatcher=candidate.dispatcher,
                    dependencies=dependencies,
                    exports=exports,
                )
            )
        return tuple(definitions)

    def _resolve_agent_name(self, candidate: _AgentCandidate, index: int) -> str:
        if candidate.explicit_name:
            return candidate.explicit_name
        for name in candidate.assigned_names:
            if name:
                return name
        return f"<anonymous-agent-{index}>"

    def _build_dependencies(
        self, candidate: _AgentCandidate
    ) -> tuple[DependencyDefinition, ...]:
        deps: list[DependencyDefinition] = []
        if candidate.deps_type:
            deps.append(DependencyDefinition(name=candidate.deps_type, kind="type"))
        if candidate.deps_expr:
            deps.append(DependencyDefinition(name=candidate.deps_expr, kind="value"))
        return tuple(deps)

    def _resolve_exports(self, assigned: tuple[str, ...]) -> tuple[str, ...]:
        if not assigned:
            return tuple()
        if self._export_names:
            exports = [name for name in assigned if name in self._export_names]
            if exports:
                return tuple(exports)
        return tuple(name for name in assigned if name)

    # ------------------------------------------------------------------
    # Metadata accessors
    # ------------------------------------------------------------------
    @property
    def export_names(self) -> tuple[str, ...]:
        return tuple(self._export_names)

    @property
    def imported_symbols(self) -> tuple[ImportedSymbol, ...]:
        return tuple(self._imported_symbols)


def discover_agents_in_module(
    path: Path, *, module: Optional[str] = None
) -> tuple[AgentDefinition, ...]:
    """Parse and analyze ``path`` returning discovered agent definitions."""

    report = inspect_agents_in_module(path, module=module)
    return report.definitions


def inspect_agents_in_module(
    path: Path, *, module: Optional[str] = None
) -> ModuleAgentReport:
    """Inspect ``path`` returning a rich module analysis report."""

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    inspector = AgentModuleInspector(path=path, module=module)
    inspector.visit(tree)
    return ModuleAgentReport(
        path=path,
        module=module,
        definitions=inspector.build_definitions(),
        export_names=inspector.export_names,
        imported_symbols=inspector.imported_symbols,
    )


__all__ = [
    "AgentModuleInspector",
    "ImportedSymbol",
    "ModuleAgentReport",
    "discover_agents_in_module",
    "inspect_agents_in_module",
]
