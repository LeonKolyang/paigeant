"""Paigeant: Durable workflow orchestration for AI agents."""

from .contracts import ActivitySpec, PaigeantMessage, RoutingSlip
from .models import StepExecution
from .dispatch import WorkflowDispatcher
from .execute import ActivityExecutor
from .integration import PaigeantAgent
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
    "StepExecution",
]
