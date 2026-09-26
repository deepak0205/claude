"""Tests for agents/synthesis.py. agents.llm.call_tool is mocked — zero
live API calls."""

from unittest.mock import patch

from agents.state import AgentResult
from agents.synthesis import synthesize


def _results():
    return {
        "literature": AgentResult(
            agent_name="literature",
            summary="EGFR mutations drive resistance in NSCLC.",
            key_citations=["111", "222"],
            confidence=0.9,
        ),
        "safety": AgentResult(
            agent_name="safety",
            summary="safety agent is not yet wired to a data source in this POC.",
            key_citations=[],
            confidence=0.0,
        ),
    }


@patch("agents.llm.call_tool")
def test_citation_outside_allowed_set_is_dropped(mock_call_tool):
    mock_call_tool.return_value = {
        "answer": "EGFR mutations drive resistance [PMID: 111].",
        "citations": [
            {"pmid": "111", "agent_source": "literature"},
            {"pmid": "999", "agent_source": "literature"},  # not in any agent's key_citations
        ],
    }

    result = synthesize("What drives EGFR resistance?", _results())

    assert result["citations"] == [{"pmid": "111", "agent_source": "literature"}]
    assert all(c["pmid"] != "999" for c in result["citations"])


@patch("agents.llm.call_tool")
def test_stub_agent_results_included_in_system_prompt(mock_call_tool):
    mock_call_tool.return_value = {"answer": "answer text", "citations": []}

    synthesize("What drives EGFR resistance?", _results())

    _, kwargs = mock_call_tool.call_args
    system = kwargs["system"]
    assert "safety" in system
    assert "not yet wired to a data source in this POC" in system
    assert "literature" in system
    assert "EGFR mutations drive resistance in NSCLC." in system


@patch("agents.llm.call_tool")
def test_allowed_pmids_built_from_all_agents_key_citations(mock_call_tool):
    mock_call_tool.return_value = {
        "answer": "answer text",
        "citations": [{"pmid": "222", "agent_source": "literature"}],
    }

    result = synthesize("query", _results())

    assert result["citations"] == [{"pmid": "222", "agent_source": "literature"}]


@patch("agents.llm.call_tool")
def test_system_prompt_instructs_leading_with_direct_answer(mock_call_tool):
    mock_call_tool.return_value = {"answer": "answer text", "citations": []}

    synthesize("What drives EGFR resistance?", _results())

    _, kwargs = mock_call_tool.call_args
    system = kwargs["system"]
    assert "Lead the answer with the direct answer to the user's query" in system


@patch("agents.llm.call_tool")
def test_synthesize_returns_answer_and_uses_synthesis_model(mock_call_tool):
    from config.settings import settings

    mock_call_tool.return_value = {"answer": "final answer", "citations": []}

    result = synthesize("query", _results())

    assert result["answer"] == "final answer"
    _, kwargs = mock_call_tool.call_args
    assert kwargs["model"] == settings.SYNTHESIS_MODEL
    assert kwargs["tool_name"] == "synthesize"
