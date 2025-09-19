"""Test fixtures containing dummy agents for discovery tests."""

from unittest.mock import Mock

# Create mock agents that simulate real PaigeantAgent instances
test_agent = Mock()
test_agent.name = "test_agent"
test_agent.__class__.__name__ = "PaigeantAgent"

another_agent = Mock()
another_agent.name = "another_agent"
another_agent.__class__.__name__ = "PaigeantAgent"

# Additional agent for testing
joke_agent = Mock()
joke_agent.name = "joke_agent"
joke_agent.__class__.__name__ = "PaigeantAgent"
