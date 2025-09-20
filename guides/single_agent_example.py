"""Single-agent workflow example using paigeant."""

import asyncio

import httpx
from pydantic import BaseModel
from pydantic_ai import RunContext

from paigeant import (
    PaigeantAgent,
    WorkflowDependencies,
    WorkflowDispatcher,
    get_repository,
    get_transport,
)


class HttpKey(BaseModel):
    api_key: str


class JokeWorkflowDeps(WorkflowDependencies):
    """Dependencies for joke workflow agents."""

    http_key: HttpKey
    user_token: str | None = None


dispatcher = WorkflowDispatcher()

joke_generation_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",  # Use test model to avoid API calls
    deps_type=JokeWorkflowDeps,
    output_type=list[str],
    system_prompt=(
        'Use the "get_jokes" tool to get jokes on the given subject, '
        "then extract each joke into a list."
    ),
    dispatcher=dispatcher,
    name="joke_generation_agent",
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
    print("Running joke generation agent with paigeant workflow...")
    # Setup workflow infrastructure
    transport = get_transport()
    repository = get_repository()

    http_key = HttpKey(api_key="foobar")
    deps = JokeWorkflowDeps(
        http_key=http_key,
        user_token="user-session-token",
    )

    joke_generation_agent.add_to_runway(
        prompt="Generate jokes on the given subject.",
        deps=deps,
    )

    correlation_id = await dispatcher.dispatch_workflow(transport)
    wf = await repository.get_workflow(correlation_id)
    print("Persisted status:", wf.status)


if __name__ == "__main__":
    asyncio.run(main())
