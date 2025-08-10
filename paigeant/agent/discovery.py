"""Utilities for discovering Paigeant agents in the environment."""

from __future__ import annotations

import pkgutil
from importlib import import_module
from pathlib import Path

from .wrapper import AGENT_REGISTRY


def discover_agent(agent_name: str) -> None:
    """Import available modules to locate an agent by name.

    This performs a best-effort scan of modules on the current working
    directory's ``sys.path``. Any module that defines a ``PaigeantAgent``
    with a matching ``name`` will register itself in ``AGENT_REGISTRY``
    when imported. The scan stops once the requested agent is found.

    Raises:
        ValueError: If no agent with ``agent_name`` can be located.
    """

    if agent_name in AGENT_REGISTRY:
        return

    search_path = [str(Path.cwd())]
    for module in pkgutil.walk_packages(search_path):
        module_name = module.name
        if module_name.startswith("paigeant"):
            continue
        try:
            import_module(module_name)
        except Exception:
            continue
        if agent_name in AGENT_REGISTRY:
            return

    raise ValueError(f"Agent {agent_name} not found in available modules")
