"""Pydantic models describing registry entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class SemanticVersion(BaseModel):
    """Semantic version with ``major.minor.patch`` components."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemanticVersion":
        """Parse a dotted semantic version string."""
        parts = value.split(".")
        if len(parts) != 3:
            raise ValueError("Semantic version must have three components")
        major, minor, patch = (int(p) for p in parts)
        return cls(major=major, minor=minor, patch=patch)

    def __str__(self) -> str:  # pragma: no cover - simple formatting
        return f"{self.major}.{self.minor}.{self.patch}"


class ParamDescriptor(BaseModel):
    """Describes a single input or output parameter for an agent."""

    name: str
    type_ref: str = Field(..., description="Dotted path or schema reference")
    required: bool = True
    description: Optional[str] = None
    default_json: Optional[Any] = None


class AgentDescriptor(BaseModel):
    """Metadata describing an agent instance in the registry."""

    # Identity
    name: str
    version: SemanticVersion
    description: Optional[str] = None
    owner: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

    # Capabilities / contracts
    supported_prompts: List[str] = Field(default_factory=list)
    inputs: List[ParamDescriptor] = Field(default_factory=list)
    outputs: List[ParamDescriptor] = Field(default_factory=list)
    side_effects: List[str] = Field(default_factory=list)

    # Addressing & transport metadata
    transport: str
    address: str
    dlq_address: Optional[str] = None

    # Optional descriptive fields
    wot_thing: Optional[dict[str, Any]] = None

    @field_validator("transport")
    @classmethod
    def _ensure_transport(cls, v: str) -> str:
        if not v:
            raise ValueError("transport must be a non-empty string")
        return v


class Group(BaseModel):
    """Logical grouping of agents."""

    name: str
    agents: List[AgentDescriptor] = Field(default_factory=list)


class RegistryRoot(BaseModel):
    """Root snapshot document for the registry."""

    groups: List[Group] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    schema_version: str = "1"
