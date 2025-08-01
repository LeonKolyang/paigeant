"""Activity execution engine for paigeant workflows."""

from __future__ import annotations

import logging
from importlib import import_module
from typing import Any

from pydantic_ai import Agent

from paigeant.deps.deserializer import DependencyDeserializer

from .contracts import (
    ActivitySpec,
    PaigeantMessage,
    PreviousOutput,
    WorkflowDependencies,
)
from .transports import BaseTransport

logger = logging.getLogger(__name__)


class ActivityExecutor:
    """Executes workflow activities by listening to transport messages."""

    def __init__(
        self, transport: BaseTransport, agent_name: str, agent_path: str
    ) -> None:
        self._transport = transport
        self._agent_name = agent_name
        self._agent_path = agent_path
        self.executed_activities = []  # Track successfully executed activities

    def extract_activity(self, message: PaigeantMessage) -> ActivitySpec:
        """Extract routing slip from the message."""
        return message.routing_slip.next_step()

    async def start(self, timeout=None) -> None:
        """Start listening for workflow messages on the given topic."""
        async for raw_message, message in self._transport.subscribe(
            self._agent_name, timeout=timeout
        ):
            activity = self.extract_activity(message)
            await self._handle_activity(activity, message)
            # Acknowledge the message was processed
            await self._transport.ack(raw_message)

    async def _handle_activity(
        self, activity: ActivitySpec, message: PaigeantMessage
    ) -> None:
        """Handle incoming workflow activity."""
        print(f"Received activity: {activity}")
        print(f"Agent path: {self._agent_path}, Agent name: {self._agent_name}")

        agent_module = import_module(self._agent_path)
        agent: Agent = getattr(agent_module, self._agent_name, None)

        # Deserialize deps
        deps: Any = None
        if activity.deps and activity.deps.data:
            try:
                deps = DependencyDeserializer.deserialize(
                    deps_data=activity.deps.data,
                    deps_type=activity.deps.type,
                    deps_module=activity.deps.module,
                    fallback_module=self._agent_path,
                )
            except Exception as e:
                print(f"Failed to deserialize deps: {e}")

        # Add previous agent outputs to deps for easy access
        enhanced_deps = self._add_previous_outputs_to_deps(deps, message)

        result = await agent.run(activity.prompt, deps=enhanced_deps)

        # Store agent result in message payload for downstream agents
        if hasattr(result, "output"):
            message.payload[self._agent_name] = result.output
        elif result is not None:
            # Fallback for agents that don't return RunResult objects
            message.payload[self._agent_name] = str(result)
        else:
            # Store indication that agent completed successfully but returned None
            message.payload[self._agent_name] = None

        logger.info(
            f"Agent {self._agent_name} completed for correlation_id={message.correlation_id}"
        )
        print(result)

        # Forward message to next activity in workflow
        await message.forward_to_next_step(self._transport)

    def _add_previous_outputs_to_deps(
        self, deps: WorkflowDependencies, message: PaigeantMessage
    ) -> WorkflowDependencies:
        """Add previous agent outputs to deps for easy access by the next agent."""

        # If no previous outputs, return deps unchanged
        if not message.payload:
            return deps

        # Get the latest output (last agent that ran)
        latest_agent = message.routing_slip.previous_step().agent_name
        latest_output = message.payload[latest_agent]
        previous_output = PreviousOutput(agent_name=latest_agent, output=latest_output)

        # If deps is None, create WorkflowDependencies with latest output
        if deps is None:
            return WorkflowDependencies(previous_output=previous_output)

        # If deps is already WorkflowDependencies, update it
        if isinstance(deps, WorkflowDependencies):
            deps.previous_output = previous_output
            return deps

        # Fallback: deps exists but is not WorkflowDependencies
        # This shouldn't happen in normal operation, but handle it gracefully
        logger.warning(
            f"Agent {self._agent_name} has non-WorkflowDependencies deps: {type(deps)}. "
            "Previous outputs will not be available."
        )
        return deps
