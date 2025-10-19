"""Activity execution engine for paigeant workflows."""

from __future__ import annotations

import logging
from typing import Any

from anyio import Path
from mistralai_azure import Optional
from pydantic_ai import Agent

from paigeant.agent.discovery import discover_agent
from paigeant.deps.deserializer import DependencyDeserializer

from .contracts import (
    ActivitySpec,
    PaigeantMessage,
    PreviousOutput,
    WorkflowDependencies,
)
from .persistence import WorkflowRepository, get_repository
from .transports import BaseTransport

logger = logging.getLogger(__name__)


class ActivityExecutor:
    """Executes workflow activities by listening to transport messages."""

    def __init__(
        self,
        transport: BaseTransport,
        agent_name: str,
        base_path: Optional[Path] = None,
        repository: WorkflowRepository | None = None,
    ) -> None:
        self._transport = transport
        self._agent_name = agent_name
        self.agent: Agent = discover_agent(agent_name, base_path)
        self.executed_activities = []
        self._repository = repository or get_repository()

    def extract_activity(self, message: PaigeantMessage) -> ActivitySpec:
        """Return the next activity from the message's routing slip."""
        return message.routing_slip.next_step()

    async def start(self, lifespan=None) -> None:
        """Start listening for workflow messages on the given topic."""
        if not self.agent:
            raise ValueError(f"Agent {self._agent_name} not found in registry.")

        async for raw_message, message in self._transport.subscribe(
            self._agent_name, lifespan=lifespan
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

        raw_deps: Any = None
        if activity.deps and activity.deps.data:
            try:
                raw_deps = DependencyDeserializer.deserialize(
                    deps_data=activity.deps.data,
                    deps_type=activity.deps.type,
                    deps_module=activity.deps.module,
                    fallback_module=self.agent.__module__,
                )
            except Exception as e:
                print(f"Failed to deserialize deps: {e}")

        if self._repository is not None:
            await self._repository.mark_step_started(
                message.correlation_id, activity.agent_name
            )

        full_deps = self._add_workflow_dependencies(raw_deps, message)
        try:
            result = await self.agent.run(activity.prompt, deps=full_deps)
        except Exception as e:
            if self._repository is not None:
                await self._repository.mark_step_completed(
                    message.correlation_id,
                    activity.agent_name,
                    status="failed",
                    output={"error": str(e)},
                )
            raise

        added = (
            result.output.added_activities
            if hasattr(result, "output") and hasattr(result.output, "added_activities")
            else []
        )
        message.routing_slip.insert_activities(added)

        if hasattr(result, "output"):
            step_output = (
                result.output.output
                if hasattr(result.output, "output")
                else result.output
            )
        elif result is not None:
            step_output = str(result)
        else:
            step_output = None

        message.payload[self._agent_name] = step_output

        if self._repository is not None:
            await self._repository.update_payload(
                message.correlation_id, message.payload
            )
            await self._repository.mark_step_completed(
                message.correlation_id,
                activity.agent_name,
                status="completed",
                output={"result": step_output},
            )

        logger.info(
            f"Agent {self._agent_name} completed for correlation_id={message.correlation_id}"
        )
        print(result)

        await message.forward_to_next_step(self._transport, self._repository)

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
