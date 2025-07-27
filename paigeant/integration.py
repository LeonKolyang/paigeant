"""Pydantic-AI integration for paigeant workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent, RunContext

from .contracts import ActivitySpec
from .dispatch import WorkflowDispatcher


class PaigeantAgent(Agent):
    """Base class for paigeant agents with workflow dispatch capability."""

    dispatcher: WorkflowDispatcher
