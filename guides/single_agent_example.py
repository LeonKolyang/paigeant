"""Multi-agent workflow using paigeant (mjoke_generation_agent = Agent(mparison version).

Compare this directly with multi_agent_example_messaging.py to see
how to convert direct agent calls into workflow dispatch using planner agent.
"""

import asyncio

import httpx
from pydantic import BaseModel
from pydantic_ai import RunContext

from paigeant import (
    PaigeantAgent,
    WorkflowDependencies,
    WorkflowDispatcher,
    get_transport,
)


class HttpKey(BaseModel):
    api_key: str


class JokeWorkflowDeps(WorkflowDependencies):
    """Dependencies for joke workflow agents."""

    http_key: HttpKey
    user_token: str | None = None


joke_generation_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",  # Use test model to avoid API calls
    deps_type=JokeWorkflowDeps,
    output_type=list[str],
    system_prompt=(
        'Use the "get_jokes" tool to get jokes on the given subject, '
        "then extract each joke into a list."
    ),
)


@joke_generation_agent.tool
async def get_jokes(ctx: RunContext[JokeWorkflowDeps], count: int) -> str:
    async with httpx.AsyncClient() as client:
        print(f"Using deps: {ctx.deps}")
        response = await client.get(
            "https://httpbin.org/json",  # Using working endpoint
            params={"count": count},
            headers={"Authorization": f"Bearer {ctx.deps.http_key.api_key}"},
        )
    response.raise_for_status()
    return f"Generated {count} jokes"


async def main():
    print("Running joke selection agent with paigeant workflow...")
    # Setup workflow infrastructure
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    http_key = HttpKey(api_key="foobar")
    deps = JokeWorkflowDeps(
        http_key=http_key,
        user_token="user-session-token",
    )

    dispatcher.add_activity(
        agent="joke_generation_agent",
        prompt="Generate jokes on the given subject.",
        deps=deps,
    )

    correlation_id = await dispatcher.dispatch_workflow()


if __name__ == "__main__":
    asyncio.run(main())
