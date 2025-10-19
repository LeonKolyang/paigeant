"""Shared base classes for discovery inspectors."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, Optional, Sequence

from pydantic import BaseModel, ConfigDict

from ._ast_utils import assigned_names, is_call_to


class ImportRule(BaseModel):
    """Describes how to capture aliases for imported symbols."""

    canonical: str
    targets: tuple[str, ...]
    modules: Optional[tuple[str, ...]] = None

    model_config = ConfigDict(frozen=True)

    def matches(self, module: Optional[str], target: str) -> bool:
        if target not in self.targets:
            return False
        if self.modules is None:
            return True
        return module in self.modules


class BaseInspector(ast.NodeVisitor):
    """Common functionality shared by discovery inspectors."""

    def __init__(self, *, path: Path, module: Optional[str] = None) -> None:
        self._path = path
        self._module = module
        self._aliases: dict[str, set[str]] = {}
        self._import_rules: list[ImportRule] = []

    # ------------------------------------------------------------------
    # Alias registration utilities
    # ------------------------------------------------------------------
    def register_symbol(self, canonical: str, initial: Iterable[str] = ()) -> None:
        self._aliases.setdefault(canonical, set()).update(initial)

    def add_import_rule(
        self,
        canonical: str,
        targets: Sequence[str],
        *,
        modules: Sequence[str] | None = None,
    ) -> None:
        rule = ImportRule(
            canonical=canonical,
            targets=tuple(targets),
            modules=None if modules is None else tuple(modules),
        )
        self._import_rules.append(rule)

    def register_alias(self, canonical: str, alias: str) -> None:
        self._aliases.setdefault(canonical, set()).add(alias)

    def aliases_for(self, canonical: str) -> set[str]:
        return self._aliases.setdefault(canonical, set())

    def call_matches(self, node: ast.AST, canonical: str) -> bool:
        return is_call_to(node, self.aliases_for(canonical))

    def assigned_names(self, targets: Iterable[ast.AST]) -> tuple[str, ...]:
        return assigned_names(targets)

    # ------------------------------------------------------------------
    # AST hooks
    # ------------------------------------------------------------------
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # pragma: no cover - AST
        for alias in node.names:
            target = alias.name.split(".")[-1]
            alias_name = alias.asname or alias.name
            for rule in self._import_rules:
                if rule.matches(node.module, target):
                    self.register_alias(rule.canonical, alias_name)
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Shared context properties
    # ------------------------------------------------------------------
    @property
    def path(self) -> Path:
        return self._path

    @property
    def module(self) -> Optional[str]:
        return self._module


__all__ = ["BaseInspector", "ImportRule"]
