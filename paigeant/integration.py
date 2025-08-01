"""Pydantic-AI integration for paigeant workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent, RunContext, _system_prompt

from .contracts import ActivitySpec, WorkflowDependencies
from .dispatch import WorkflowDispatcher


async def extract_previous_output(
    ctx: RunContext[WorkflowDependencies],
) -> Optional[str]:
    """Extract output from the previous agent in the workflow."""
    if previous_output := ctx.deps.previous_output:
        return f"If required, use the previous output: {previous_output.output} from {previous_output.agent_name}."
    return None


class PaigeantAgent(Agent):
    """Base class for paigeant agents with workflow dispatch capability."""

    dispatcher: WorkflowDispatcher

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.tool(extract_previous_output)
        self._instructions_functions.append(
            _system_prompt.SystemPromptRunner(extract_previous_output, dynamic=True)
        )
