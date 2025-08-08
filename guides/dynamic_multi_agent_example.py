"""Three-agent joke workflow showing sequential message forwarding.

This example demonstrates how to create a workflow where:
1. First agent extracts the joke topic from user input
2. Second agent generates raw jokes based on the topic
3. Third agent selects and formats the best joke
All agents work together in sequence via the workflow dispatcher
"""

import asyncio

from pydantic import BaseModel

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


# First agent: Topic extractor
topic_extractor_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt=(
        "Extract the joke topic from user input. "
        "Return just the topic name (e.g., 'cats', 'programming', 'work'). "
        "If no specific topic is mentioned, return 'general'."
    ),
)

# Second dynamically added agent: Joke forwarder
joke_forwarder_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    output_type=str,
    system_prompt=("Forward the jokes to the next agent. "),
)

# Third agent: Joke generator
joke_generator_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    output_type=list[str],
    system_prompt=(
        "Generate 3 jokes based on the topic from the input. "
        "Use the workflow payload to get the topic extracted by the first agent. "
        "Return a list of joke strings."
    ),
    can_edit_itinerary=True,
)


# Fourth agent: Joke selector and formatter
joke_selector_agent = PaigeantAgent(
    "anthropic:claude-3-5-sonnet-latest",
    deps_type=JokeWorkflowDeps,
    system_prompt=(
        "Select the best joke from the given list. "
        "Format it nicely with proper setup and punchline. "
        "Use the jokes from the previous generator agent."
    ),
)


async def run_three_agent_joke_workflow():
    """Run the three-agent joke workflow."""
    print("Starting three-agent joke workflow...")

    # Setup workflow infrastructure
    transport = get_transport()
    dispatcher = WorkflowDispatcher(transport)

    # Setup dependencies
    http_key = HttpKey(api_key="joke-api-key-12345")
    deps = JokeWorkflowDeps(http_key=http_key, user_token="joke-session-token")

    # Register first activity: Topic extraction
    dispatcher.add_activity(
        agent="topic_extractor_agent",
        prompt="Extract joke topic from: 'Tell me a funny joke about programming!  Add a step to forward the jokes to the joke_forwarder_agent.'",
        deps=deps,
    )

    # Register second activity: Joke generation
    dispatcher.add_activity(
        agent="joke_generator_agent",
        prompt="Generate 3 jokes based on a given topics.",
        deps=deps,
    )

    # Register third activity: Joke selection and formatting
    dispatcher.add_activity(
        agent="joke_selector_agent",
        prompt="Select and format the best joke from the given list",
        deps=deps,
    )

    dispatcher.register_activity(
        agent=joke_forwarder_agent,
        prompt="do nothing",
        deps=deps,
        agent_name="joke_forwarder_agent",
    )

    # Dispatch the workflow
    correlation_id = await dispatcher.dispatch_workflow()
    print(f"Three-agent joke workflow dispatched!")
    print(f"Correlation ID: {correlation_id}")
    print(f"Workflow will process through all three agents in sequence")

    return correlation_id


async def main():
    """Main runner."""
    print("Three-agent workflow starting...")

    correlation_id = await run_three_agent_joke_workflow()

    print(
        f"""
Workflow dispatched with correlation ID: {correlation_id}

To run the workers for each agent, start these in separate terminals:

1. Topic extractor worker:
uv run python guides/execution_example.py topic_extractor_agent guides.three_agent_workflow_example

2. Joke generator worker:
uv run python guides/execution_example.py joke_generator_agent guides.three_agent_workflow_example

3. Joke selector worker:
uv run python guides/execution_example.py joke_selector_agent guides.three_agent_workflow_example
"""
    )


if __name__ == "__main__":
    asyncio.run(main())
