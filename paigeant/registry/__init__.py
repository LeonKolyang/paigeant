"""Registry data models and utilities."""

from __future__ import annotations

from .models import (
    AgentDescriptor,
    Group,
    ParamDescriptor,
    RegistryRoot,
    SemanticVersion,
)

# In-memory representation of the agent registry.  This is intentionally
# lightweight – for now it simply keeps track of descriptors that are added at
# runtime.  Future implementations may persist this structure or expose it via
# an API, but keeping the canonical location here makes it easy for agents to
# register themselves.
REGISTRY = RegistryRoot()


def register_agent(descriptor: AgentDescriptor, group: str = "default") -> None:
    """Add ``descriptor`` to ``REGISTRY`` under ``group``.

    Groups are created on-demand.  Duplicate agent names within the same group
    are not checked for; callers should ensure uniqueness if desired.
    """

    group_obj = next((g for g in REGISTRY.groups if g.name == group), None)
    if group_obj is None:
        group_obj = Group(name=group)
        REGISTRY.groups.append(group_obj)
    group_obj.agents.append(descriptor)


__all__ = [
    "SemanticVersion",
    "ParamDescriptor",
    "AgentDescriptor",
    "Group",
    "RegistryRoot",
    "REGISTRY",
    "register_agent",
]
