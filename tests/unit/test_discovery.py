"""Tests for agent discovery functionality."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from paigeant.agent.discovery import (
    discover_agent,
    find_agent_in_directory,
    find_agent_in_file,
)


@pytest.fixture
def test_agent_file():
    """Path to the test agents fixture file."""
    return Path(__file__).parent.parent / "fixtures" / "test_agents.py"


@pytest.fixture
def test_agent_dir():
    """Path to the fixtures directory containing test agents."""
    return Path(__file__).parent.parent / "fixtures"


class TestFindAgentInFile:
    """Tests for find_agent_in_file function."""

    def test_find_existing_agent(self, test_agent_file):
        """Test finding an agent that exists in a file."""
        agent = find_agent_in_file("test_agent", test_agent_file)
        assert agent is not None
        assert agent.name == "test_agent"

    def test_agent_not_found_in_file(self, test_agent_file):
        """Test error when agent doesn't exist in file."""
        with pytest.raises(ValueError) as exc:
            find_agent_in_file("nonexistent_agent", test_agent_file)
        message = str(exc.value)
        assert "Agent 'nonexistent_agent'" in message
        assert str(test_agent_file) in message


class TestFindAgentInDirectory:
    """Tests for find_agent_in_directory function."""

    def test_find_existing_agent_in_directory(self, test_agent_dir):
        """Test finding an agent that exists in a directory."""
        agent = find_agent_in_directory("test_agent", test_agent_dir)
        assert agent is not None
        assert agent.name == "test_agent"

    def test_agent_not_found_in_directory(self, test_agent_dir):
        """Test when agent doesn't exist in any module in directory."""
        result = find_agent_in_directory("nonexistent_agent", test_agent_dir)
        # Function returns None when agent is not found
        assert result is None


class TestDiscoverAgent:
    """Tests for discover_agent function."""

    def test_discover_agent_from_file(self, test_agent_file):
        """Test discovering agent from a specific file."""
        agent = discover_agent("test_agent", test_agent_file)
        assert agent is not None
        assert agent.name == "test_agent"

    def test_discover_agent_from_directory(self, test_agent_dir):
        """Test discovering agent from a directory."""
        agent = discover_agent("test_agent", test_agent_dir)
        assert agent is not None
        assert agent.name == "test_agent"

    def test_discover_multiple_agents_in_file(self, test_agent_file):
        """Test discovering different agents from the same file."""
        agent1 = discover_agent("test_agent", test_agent_file)
        agent2 = discover_agent("another_agent", test_agent_file)
        agent3 = discover_agent("joke_agent", test_agent_file)

        assert agent1.name == "test_agent"
        assert agent2.name == "another_agent"
        assert agent3.name == "joke_agent"

    def test_discover_agent_default_path(self, monkeypatch, tmp_path):
        """Test discovering agent with default path (current directory)."""
        # Use a real temporary path instead of Mock
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        # Since we can't easily mock the directory scanning,
        # just test that it raises ValueError when agent is not found
        with pytest.raises(ValueError) as exc:
            discover_agent("nonexistent_agent")
        message = str(exc.value)
        assert "Agent 'nonexistent_agent'" in message
        assert "in directory" in message
        assert str(tmp_path.resolve()) in message

    def test_discover_agent_invalid_path(self):
        """Test error when path is neither file nor directory."""
        invalid_path = Path("/nonexistent/path")
        with pytest.raises(ValueError) as exc:
            discover_agent("test_agent", invalid_path)
        message = str(exc.value)
        assert "Agent 'test_agent'" in message
        assert str(invalid_path) in message
        assert "does not exist" in message
