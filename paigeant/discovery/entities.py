"""Typed metadata contracts for discovery results."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourcePosition(BaseModel):
    """Represents a 1-based line and 0-based column within a source file."""

    line: int = Field(..., ge=1)
    column: int = Field(..., ge=0)

    model_config = ConfigDict(frozen=True)


class SourceSpan(BaseModel):
    """Span of source code that produced the discovery entity."""

    start: SourcePosition
    end: Optional[SourcePosition] = None

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _ensure_order(self) -> SourceSpan:  # pragma: no cover - simple guard
        if self.end is None:
            return self
        if self.end.line < self.start.line:
            raise ValueError("end position must not precede start")
        if self.end.line == self.start.line and self.end.column < self.start.column:
            raise ValueError("end position must not precede start")
        return self


class DiscoverySource(BaseModel):
    """Origin metadata for a discovered entity."""

    file_path: Path
    module: Optional[str] = None
    span: Optional[SourceSpan] = None

    model_config = ConfigDict(frozen=True)


class DependencyDefinition(BaseModel):
    """Describes a dependency required by an agent or workflow."""

    name: str
    source: Optional[DiscoverySource] = None
    kind: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class WorkflowAgentRef(BaseModel):
    """Reference to an agent used within a workflow."""

    name: str
    dispatcher: Optional[str] = None
    dependency: Optional[str] = None
    defined_inline: bool = False
    source: Optional[DiscoverySource] = None
    agent_key: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class AgentDefinition(BaseModel):
    """Metadata describing a discovered agent implementation."""

    name: str
    source: DiscoverySource
    dispatcher: Optional[str] = None
    dependencies: tuple[DependencyDefinition, ...] = Field(default_factory=tuple)
    exports: tuple[str, ...] = Field(default_factory=tuple)
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class WorkflowDefinition(BaseModel):
    """Metadata describing a discovered workflow module."""

    source: DiscoverySource
    description: Optional[str] = None
    dispatchers: tuple[str, ...] = Field(default_factory=tuple)
    agents: tuple[WorkflowAgentRef, ...] = Field(default_factory=tuple)
    dependencies: tuple[DependencyDefinition, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)
