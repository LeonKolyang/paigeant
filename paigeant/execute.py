"""Activity execution engine for paigeant workflows."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent

from paigeant.deps.deserializer import DependencyDeserializer

from .contracts import ActivitySpec, PaigeantMessage
from .transports import BaseTransport


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

    def extract_activity(self, message: PaigeantMessage) -> ActivitySpec:
        """Extract routing slip from the message."""
        return message.routing_slip.next_step()

    async def start(self) -> None:
        """Start listening for workflow messages on the given topic."""
        async for raw_message, message in self._transport.subscribe(self._agent_name):
            activity = self.extract_activity(message)
            await self._handle_activity(activity)
            # Acknowledge the message was processed
            await self._transport.ack(raw_message)

    async def _handle_activity(self, activity: ActivitySpec) -> None:
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

        result = await agent.run(activity.prompt, deps=deps)
        print(result)
