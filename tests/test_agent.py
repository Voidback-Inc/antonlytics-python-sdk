"""
Basic tests for Antonlytics SDK.
"""

import pytest
from antonlytics import Agent, AntonlyticsError, AuthenticationError


def test_agent_initialization():
    """Test agent initialization."""
    agent = Agent(api_key="test_key", project_id="test_project")
    assert agent.api_key == "test_key"
    assert agent.project_id == "test_project"


def test_agent_requires_api_key():
    """Test that API key is required."""
    with pytest.raises(AntonlyticsError):
        Agent(api_key="", project_id="test_project")


def test_agent_requires_project_id():
    """Test that project ID is required."""
    with pytest.raises(AntonlyticsError):
        Agent(api_key="test_key", project_id="")


def test_ingest_requires_text():
    """Test that ingest requires text."""
    agent = Agent(api_key="test_key", project_id="test_project")
    with pytest.raises(AntonlyticsError):
        agent.ingest("")


def test_chat_requires_message():
    """Test that chat requires message."""
    agent = Agent(api_key="test_key", project_id="test_project")
    with pytest.raises(AntonlyticsError):
        agent.chat("")


def test_set_system_prompt_requires_prompt():
    """Test that set_system_prompt requires prompt."""
    agent = Agent(api_key="test_key", project_id="test_project")
    with pytest.raises(AntonlyticsError):
        agent.set_system_prompt("")
