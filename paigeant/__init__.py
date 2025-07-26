"""Paigeant: Durable workflow orchestration for AI agents."""

from .contracts import ActivitySpec, PaigeantMessage, RoutingSlip
from .dispatch import WorkflowDispatcher
from .integration import PlannerAgentDeps, create_planner_agent
from .transports import get_transport

__version__ = "0.1.0"
__all__ = [
    "ActivitySpec",
    "RoutingSlip",
    "PaigeantMessage",
    "WorkflowDispatcher",
    "PlannerAgentDeps",
    "create_planner_agent",
    "get_transport",
]
