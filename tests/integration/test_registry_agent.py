import os

from paigeant import PaigeantAgent, WorkflowDependencies, WorkflowDispatcher, REGISTRY


class DummyDeps(WorkflowDependencies):
    """Simple dependencies class for testing."""
    pass


def test_agent_added_to_registry():
    """Creating a PaigeantAgent should register it in the global registry."""
    # Ensure registry is clean
    REGISTRY.groups.clear()

    os.environ.setdefault("ANTHROPIC_API_KEY", "test")
    dispatcher = WorkflowDispatcher()
    agent_name = "registry_test_agent"

    PaigeantAgent(
        "anthropic:claude-3-5-sonnet-latest",
        dispatcher=dispatcher,
        name=agent_name,
        deps_type=DummyDeps,
    )

    assert any(
        descriptor.name == agent_name
        for group in REGISTRY.groups
        for descriptor in group.agents
    )

