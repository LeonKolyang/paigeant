"""Paigeant: Durable workflow orchestration for AI agents."""

from .agent.wrapper import PaigeantAgent
from .contracts import ActivitySpec, PaigeantMessage, RoutingSlip, WorkflowDependencies
from .dispatch import WorkflowDispatcher
from .execute import ActivityExecutor
from .transports import get_transport
from .persistence import get_repository
from .registry import REGISTRY

__version__ = "0.2.0"
__all__ = [
    "ActivitySpec",
    "ActivityExecutor",
    "RoutingSlip",
    "PaigeantMessage",
    "WorkflowDispatcher",
    "get_transport",
    "get_repository",
    "PaigeantAgent",
    "WorkflowDependencies",
    "REGISTRY",
]
