"""Activity execution engine for paigeant workflows."""

from __future__ import annotations

from importlib import import_module
from typing import Any
from datetime import datetime

from pydantic import BaseModel
from pydantic_ai import Agent

from paigeant.deps.deserializer import DependencyDeserializer

from .contracts import ActivityFailed, ActivitySpec, PaigeantMessage
from .models import StepExecution
from .transports import BaseTransport
from .utils.retry import schedule_retry


class HttpKey(BaseModel):
    api_key: str


class ActivityExecutor:
    """Executes workflow activities by listening to transport messages."""

    def __init__(
        self, transport: BaseTransport, agent_name: str, agent_path: str
    ) -> None:
        self._transport = transport
        self._agent_name = agent_name
        self._agent_path = agent_path
        self._steps: dict[tuple[str, str], StepExecution] = {}

    def extract_activity(self, message: PaigeantMessage) -> ActivitySpec:
        """Extract routing slip from the message."""
        return message.routing_slip.next_step()

    async def start(self) -> None:
        """Start listening for workflow messages on the given topic."""
        async for raw_message, message in self._transport.subscribe(self._agent_name):
            activity = self.extract_activity(message)
            await self._handle_activity(activity, message)
            # Acknowledge the message was processed
            await self._transport.ack(raw_message)

    async def _handle_activity(self, activity: ActivitySpec, message: PaigeantMessage) -> None:
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
                    fallback_module=self._agent_path,  # optional fallback if needed
                )
            except Exception as e:
                print(f"❌ Failed to deserialize deps: {e}")

        key = (message.correlation_id, activity.agent_name)
        step = self._steps.get(key)
        if not step:
            step = StepExecution(
                step_name=activity.agent_name,
                workflow_id=message.correlation_id,
                inputs=message.payload,
            )
            self._steps[key] = step

        step.last_attempt_ts = datetime.utcnow()

        try:
            result = await agent.run(activity.prompt, deps=deps)
            step.status = "success"
            step.outputs = result if isinstance(result, dict) else {"result": result}
            message.routing_slip.mark_complete(activity)
            if isinstance(result, dict):
                message.payload.update(result)

            next_step = message.routing_slip.next_step()
            if next_step:
                await self._transport.publish(next_step.agent_name, message)
        except ActivityFailed as e:
            step.retry_count += 1
            step.last_error = str(e)
            if not e.retryable or step.retry_count > step.retry_limit:
                step.status = "failed"
            else:
                await schedule_retry(step.retry_count)
                new_msg = message.bump_attempt()
                await self._transport.publish(activity.agent_name, new_msg)
        print(step)
