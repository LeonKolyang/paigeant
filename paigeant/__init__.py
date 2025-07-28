"""Paigeant: Durable workflow orchestration for AI agents."""

from .contracts import ActivitySpec, PaigeantMessage, RoutingSlip
from .dispatch import WorkflowDispatcher
from .execute import ActivityExecutor
from .agent.wrapper import PageantAgent
from .transports import get_transport

__version__ = "0.1.0"
__all__ = [
    "ActivitySpec",
    "ActivityExecutor",
    "RoutingSlip",
    "PaigeantMessage",
    "WorkflowDispatcher",
    "get_transport",
    "PaigeantAgent",
]
