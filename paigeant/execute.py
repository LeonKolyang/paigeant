"""Activity execution engine for paigeant workflows."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import Agent

from paigeant.agent.wrapper import AGENT_REGISTRY
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

    def __init__(self, transport: BaseTransport, agent_name: str) -> None:
        self._transport = transport
        self._agent_name = agent_name
        self.executed_activities = []

    def extract_activity(self, message: PaigeantMessage) -> ActivitySpec:
        """Return the next activity from the message's routing slip."""
        return message.routing_slip.next_step()

    async def start(self, timeout=None) -> None:
        """Start listening for workflow messages on the given topic."""
        async for raw_message, message in self._transport.subscribe(
            self._agent_name, timeout=timeout
        ):
            activity = self.extract_activity(message)
            await self._handle_activity(activity, message)
            await self._transport.ack(raw_message)

    async def _handle_activity(
        self, activity: ActivitySpec, message: PaigeantMessage
    ) -> None:
        """Handle incoming workflow activity."""
        print(f"Received activity: {activity}")
        print(f"Agent name: {self._agent_name}")

        agent: Agent | None = AGENT_REGISTRY.get(self._agent_name)
        if agent is None:
            raise ValueError(f"Agent {self._agent_name} not found in registry")

        raw_deps: Any = None
        if activity.deps and activity.deps.data:
            try:
                raw_deps = DependencyDeserializer.deserialize(
                    deps_data=activity.deps.data,
                    deps_type=activity.deps.type,
                    deps_module=activity.deps.module,
                    fallback_module=agent.__module__,
                )
            except Exception as e:
                print(f"Failed to deserialize deps: {e}")

        full_deps = self._add_workflow_dependencies(raw_deps, message)
        result = await agent.run(activity.prompt, deps=full_deps)

        added = (
            result.output.added_activities
            if hasattr(result.output, "added_activities")
            else []
        )
        message.routing_slip.insert_activities(added)

        if hasattr(result, "output"):
            message.payload[self._agent_name] = result.output
        elif result is not None:
            message.payload[self._agent_name] = str(result)
        else:
            message.payload[self._agent_name] = None

        logger.info(
            f"Agent {self._agent_name} completed for correlation_id={message.correlation_id}"
        )
        print(result)

        await message.forward_to_next_step(self._transport)

    def _add_workflow_dependencies(
        self, deps: WorkflowDependencies | None, message: PaigeantMessage
    ) -> WorkflowDependencies | None:
        """Combine deserialized dependencies with workflow context."""

        if not message.payload:
            if isinstance(deps, WorkflowDependencies):
                deps.activity_registry = message.activity_registry
            return deps

        latest_agent = message.routing_slip.previous_step().agent_name
        previous_output = PreviousOutput(
            agent_name=latest_agent, output=message.payload[latest_agent]
        )

        if deps is None:
            return WorkflowDependencies(
                previous_output=previous_output,
                activity_registry=message.activity_registry,
            )

        if isinstance(deps, WorkflowDependencies):
            deps.previous_output = previous_output
            deps.activity_registry = message.activity_registry
            return deps

        logger.warning(
            f"Agent {self._agent_name} has non-WorkflowDependencies deps: {type(deps)}. "
            "Previous outputs will not be available."
        )
        return deps
