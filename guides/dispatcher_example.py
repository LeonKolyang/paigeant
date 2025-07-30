"""Multi-agent workflow using paigeant (mjoke_generation_agent = Agent(mparison version).

Compare this directly with multi_agent_example_messaging.py to see
how to convert direct agent calls into workflow dispatch using planner agent.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from paigeant import PaigeantAgent, WorkflowDispatcher, get_transport


class HttpKey(BaseModel):
    api_key: str


class JokeWorkflowDeps(BaseModel):
    """Dependencies for joke workflow agents."""

    model_config = {"arbitrary_types_allowed": True}

    http_key: HttpKey
    user_token: str | None = None


joke_selection_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt=(
        "Use the `joke_factory` tool to generate some jokes on the given subject, "
        "then choose the best. You must return just a single joke."
    ),
)


@joke_selection_agent.tool
async def joke_factory(ctx: RunContext[JokeWorkflowDeps], count: int) -> list[str]:
    r = await joke_generation_agent.run(
        f"Please generate {count} jokes.",
        deps=ctx.deps,
        usage=ctx.usage,
    )

    return r.output


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
        print(f"🔧 Using deps: {ctx.deps}")
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
    os.environ["PAIGEANT_TRANSPORT"] = "redis"

    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    http_key = HttpKey(api_key="foobar")
    deps = JokeWorkflowDeps(
        http_key=http_key,
        user_token="user-session-token",
    )

    dispatcher.register_activity(
        agent="joke_generation_agent",
        prompt="Generate jokes on the given subject.",
        deps=deps,
    )

    correlation_id = await dispatcher.dispatch_workflow()


if __name__ == "__main__":
    asyncio.run(main())

"""
COMPARISON WITH ORIGINAL:

ORIGINAL (multi_agent_example_messaging.py):
    @joke_selection_agent.tool
    async def joke_factory(ctx: RunContext[HttpKey], count: int) -> list[str]:
        # Direct agent call - tight coupling
        r = await joke_generation_agent.run(
            f"Please generate {count} jokes.",
            deps=ctx.deps,
            usage=ctx.usage,
        )
        return ["scheduled joke generation"]

    # Usage:
    result = await joke_selection_agent.run("Tell me a joke", deps=http_key)

PAIGEANT VERSION (this file):
    # No custom tools needed - planner agent has built-in workflow dispatch
    
    # Usage:
    result = await joke_selection_agent.run(
        "Create a workflow to generate 3 programming jokes with activities: generate-jokes, select-best, format-result",
        deps=planner_deps
    )

KEY DIFFERENCES:
- Uses create_planner_agent() which has built-in workflow dispatch capability
- No custom tools needed - planner agent understands natural language workflow requests
- PlannerAgentDeps provides workflow_dispatcher access automatically
- Natural language instruction directly creates and dispatches workflow
- Returns correlation ID for tracking instead of immediate result
- Activities can be processed by separate workers (not shown in this minimal example)

ARCHITECTURE BENEFITS:
- Loose coupling: workflow activities are dispatched, not directly executed
- Scalability: activities can be processed by distributed workers
- Flexibility: workflow can be modified without changing agent code
- Traceability: correlation IDs allow tracking workflow execution
"""
