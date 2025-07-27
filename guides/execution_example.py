"""Example showing how to run the ActivityExecutor with Redis."""

import asyncio
import os
import sys

from paigeant import ActivityExecutor, ActivitySpec, WorkflowDispatcher, get_transport


async def main():
    # Use Redis transport for cross-process messaging
    os.environ["PAIGEANT_TRANSPORT"] = "redis"

    agent_name = sys.argv[1]
    agent_path = sys.argv[2]

    transport = get_transport()
    executor = ActivityExecutor(transport, agent_name=agent_name, agent_path=agent_path)

    # Start executor
    await executor.start()


if __name__ == "__main__":
    asyncio.run(main())
