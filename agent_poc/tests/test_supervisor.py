"""Tests for agents/supervisor.py. agents.llm.call_tool is mocked — zero
live API calls."""

from unittest.mock import patch

from agents.supervisor import AGENT_DESCRIPTIONS, AGENT_NAMES, SYSTEM_PROMPT, select_agents
from config.settings import settings


def test_system_prompt_contains_every_agent_name_and_description():
    for name in AGENT_NAMES:
        assert name in SYSTEM_PROMPT
    for description in AGENT_DESCRIPTIONS.values():
        assert description in SYSTEM_PROMPT


@patch("agents.llm.call_tool")
def test_select_agents_uses_correct_model_and_tool_schema(mock_call_tool):
    mock_call_tool.return_value = {"agents": ["literature", "disease"]}

    result = select_agents("What is the role of EGFR in lung cancer?")

    assert result == ["literature", "disease"]
    mock_call_tool.assert_called_once()
    _, kwargs = mock_call_tool.call_args
    assert kwargs["model"] == settings.SUPERVISOR_MODEL
    assert kwargs["tool_name"] == "select_agents"
    assert kwargs["user_content"] == "What is the role of EGFR in lung cancer?"
    schema = kwargs["tool_schema"]
    assert schema["properties"]["agents"]["items"]["enum"] == AGENT_NAMES
    assert schema["required"] == ["agents"]


@patch("agents.llm.call_tool")
def test_select_agents_filters_invalid_names(mock_call_tool):
    mock_call_tool.return_value = {"agents": ["literature", "not_a_real_agent", "target"]}

    result = select_agents("some query")

    assert result == ["literature", "target"]


@patch("agents.llm.call_tool", side_effect=RuntimeError("api down"))
def test_select_agents_falls_back_to_all_seven_on_exception(mock_call_tool):
    result = select_agents("some query")

    assert result == AGENT_NAMES
    assert set(result) == set(AGENT_NAMES)
    assert len(result) == 7
