"""Tests for agents.base_subagent.make_agent_node."""

from unittest.mock import MagicMock, patch

from agents.base_subagent import make_agent_node
from agents.state import AgentResult
from agents.tools import StubToolProvider


def test_not_selected_is_zero_call():
    tool_provider = MagicMock()
    tool_provider.tools = [{"name": "search_evidence"}]

    with patch("agents.base_subagent.run_agent_loop") as mock_run_agent_loop:
        node = make_agent_node("literature", tool_provider, model="claude-sonnet-5")
        result = node("some query", False)

    assert result == AgentResult(
        agent_name="literature",
        summary="literature agent was not selected for this query.",
        key_citations=[],
        confidence=0.0,
    )
    mock_run_agent_loop.assert_not_called()
    tool_provider.execute.assert_not_called()


def test_stub_tool_provider_selected_is_zero_call():
    tool_provider = StubToolProvider()

    with patch("agents.base_subagent.run_agent_loop") as mock_run_agent_loop:
        node = make_agent_node("molecule", tool_provider, model="claude-sonnet-5")
        result = node("some query", True)

    assert result == AgentResult(
        agent_name="molecule",
        summary="molecule agent is not yet wired to a data source in this POC.",
        key_citations=[],
        confidence=0.0,
    )
    mock_run_agent_loop.assert_not_called()


def test_real_path_filters_citations_to_seen_pmids_and_clamps_confidence():
    tool_provider = MagicMock()
    tool_provider.tools = [{"name": "search_evidence"}]

    def fake_run_agent_loop(model, system, user_content, tools, tool_executor, finish_tool_name, finish_tool_schema, max_iterations=5):
        # Drive seen_pmids by invoking the real tracking_executor once, as
        # run_agent_loop itself would when the model calls a regular tool.
        tool_provider.execute.return_value = "1. PMID: 111 some evidence text"
        tool_executor("search_evidence", {"query": "EGFR"})
        return {"summary": "found stuff", "key_citations": ["111", "999"], "confidence": 1.7}

    with patch("agents.base_subagent.run_agent_loop", side_effect=fake_run_agent_loop):
        node = make_agent_node("literature", tool_provider, model="claude-sonnet-5")
        result = node("some query", True)

    assert result.agent_name == "literature"
    assert result.summary == "found stuff"
    assert result.key_citations == ["111"]
    assert result.confidence == 1.0
    tool_provider.execute.assert_called_once_with("search_evidence", {"query": "EGFR"})


def test_real_path_exception_falls_back_to_error_result():
    tool_provider = MagicMock()
    tool_provider.tools = [{"name": "search_evidence"}]

    with patch("agents.base_subagent.run_agent_loop", side_effect=RuntimeError("api down")):
        node = make_agent_node("target", tool_provider, model="claude-sonnet-5")
        result = node("some query", True)

    assert result == AgentResult(
        agent_name="target",
        summary="target agent failed: api down",
        key_citations=[],
        confidence=0.0,
    )
