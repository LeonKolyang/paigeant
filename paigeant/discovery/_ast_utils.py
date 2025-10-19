"""Shared AST helpers for discovery inspectors."""

from __future__ import annotations

import ast
from typing import Any, Iterable, Optional

from .entities import SourcePosition, SourceSpan

MISSING = object()


def get_expr_name(node: ast.AST) -> Optional[str]:
    """Return dotted name for expressions like attributes or names."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        value = get_expr_name(node.value)
        return f"{value}.{node.attr}" if value else node.attr
    if isinstance(node, ast.Subscript):
        return get_expr_name(node.value)
    if isinstance(node, ast.Call):
        return get_expr_name(node.func)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def name_from_target(target: ast.AST) -> Optional[str]:
    """Extract the name assigned to in assignment targets."""

    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return get_expr_name(target)
    return None


def assigned_names(targets: Iterable[ast.AST]) -> tuple[str, ...]:
    """Return tuple of identifier names from assignment targets."""

    names: list[str] = []
    for target in targets:
        name = name_from_target(target)
        if name:
            names.append(name)
    return tuple(names)


def is_call_to(node: ast.AST, candidates: set[str]) -> bool:
    """Return True if ``node`` is a call to any dotted name in ``candidates``."""

    if not isinstance(node, ast.Call):
        return False
    func_name = get_expr_name(node.func)
    if not func_name:
        return False
    last = func_name.split(".")[-1]
    return func_name in candidates or last in candidates


def literal_value(node: ast.AST) -> Any:
    """Best-effort extraction of Python literal values from AST nodes."""

    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = literal_value(node.operand)
        if operand is MISSING:
            return MISSING
        if isinstance(operand, (int, float, complex)):
            return -operand
        return MISSING
    if isinstance(node, (ast.Tuple, ast.List)):
        items = []
        for element in node.elts:
            value = literal_value(element)
            if value is MISSING:
                return MISSING
            items.append(value)
        return tuple(items) if isinstance(node, ast.Tuple) else items
    if isinstance(node, ast.Dict):
        result: dict[Any, Any] = {}
        for key_node, value_node in zip(node.keys, node.values, strict=True):
            key = literal_value(key_node)
            value = literal_value(value_node)
            if key is MISSING or value is MISSING:
                return MISSING
            result[key] = value
        return result
    return MISSING


def node_span(node: ast.AST) -> Optional[SourceSpan]:
    """Return a SourceSpan for the provided node if pos info is available."""

    lineno = getattr(node, "lineno", None)
    col_offset = getattr(node, "col_offset", None)
    if lineno is None or col_offset is None:
        return None

    start = SourcePosition(line=lineno, column=col_offset)
    end_lineno = getattr(node, "end_lineno", None)
    end_col = getattr(node, "end_col_offset", None)
    if end_lineno is None or end_col is None:
        return SourceSpan(start=start)
    end = SourcePosition(line=end_lineno, column=end_col)
    return SourceSpan(start=start, end=end)


__all__ = [
    "get_expr_name",
    "is_call_to",
    "literal_value",
    "name_from_target",
    "assigned_names",
    "node_span",
    "MISSING",
]
