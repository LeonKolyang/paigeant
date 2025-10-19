"""Agent discovery via static AST inspection."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field

from ._ast_utils import MISSING, get_expr_name, literal_value, node_span
from .base_inspector import BaseInspector
from .entities import AgentDefinition, DependencyDefinition, DiscoverySource, SourceSpan


class _AgentCandidate(BaseModel):
    assigned_names: tuple[str, ...] = ()
    explicit_name: Optional[str] = None
    dispatcher: Optional[str] = None
    deps_type: Optional[str] = None
    deps_expr: Optional[str] = None
    literal_args: tuple[Any, ...] = ()
    literal_kwargs: dict[str, Any] = Field(default_factory=dict)
    factory_name: Optional[str] = None
    span: Optional[SourceSpan] = None

    model_config = ConfigDict(frozen=True)


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

    # ------------------------------------------------------------------
    # Assignment handling
    # ------------------------------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:
        value = node.value
        if self._collect_exports(node.targets, value):
            return
        if self.call_matches(value, "PaigeantAgent"):
            assigned = self.assigned_names(node.targets)
            self._candidates.append(self._parse_agent_call(value, assigned))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        value = node.value
        if value and self.call_matches(value, "PaigeantAgent"):
            assigned = self.assigned_names((node.target,))
            self._candidates.append(self._parse_agent_call(value, assigned))
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
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
        literal_kwargs: dict[str, Any] = {}

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
            else:
                value = literal_value(keyword.value)
                if value is not MISSING:
                    literal_kwargs[keyword.arg] = value

        literal_args = []
        for arg in call.args:
            value = literal_value(arg)
            if value is not MISSING:
                literal_args.append(value)

        candidate = _AgentCandidate(
            assigned_names=assigned_names,
            explicit_name=explicit_name,
            dispatcher=dispatcher,
            deps_type=deps_type,
            deps_expr=deps_expr,
            literal_args=tuple(literal_args),
            literal_kwargs=literal_kwargs,
            factory_name=get_expr_name(call.func),
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
            attributes: dict[str, Any] = {}
            if candidate.factory_name:
                attributes["factory"] = candidate.factory_name
            if candidate.literal_args:
                attributes["args"] = list(candidate.literal_args)
            if candidate.literal_kwargs:
                attributes["kwargs"] = candidate.literal_kwargs
            if candidate.assigned_names:
                attributes.setdefault("assigned_names", list(candidate.assigned_names))

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
                    attributes=attributes,
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


def discover_agents_in_module(
    path: Path, *, module: Optional[str] = None
) -> tuple[AgentDefinition, ...]:
    """Parse and analyze ``path`` returning discovered agent definitions."""

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    inspector = AgentModuleInspector(path=path, module=module)
    inspector.visit(tree)
    return inspector.build_definitions()


__all__ = ["AgentModuleInspector", "discover_agents_in_module"]
