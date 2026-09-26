"""Tests for agents/memory.py. The Anthropic client is fully mocked at the
agents.llm boundary (call_tool / count_tokens) — zero live API calls."""

from unittest.mock import patch

import pytest

from agents.memory import ConversationMemory, add_turn, build_context, contextualize_query
from config.settings import settings


def _mem(session_id="s1", turns=None, summary=""):
    return ConversationMemory(session_id=session_id, turns=turns or [], summary=summary)


# --- add_turn / overflow folding ---


@patch("agents.llm.count_tokens", return_value=10)
@patch("agents.llm.call_tool")
def test_add_turn_retains_only_active_turns_and_folds_overflow(mock_call_tool, mock_count_tokens):
    mock_call_tool.return_value = {"summary": "folded summary"}

    memory = _mem()
    n_additions = settings.MEMORY_ACTIVE_TURNS + 3
    for i in range(n_additions):
        memory = add_turn(memory, query=f"q{i}", answer=f"a{i}", citations=[f"PMID:{i}"])

    # Exactly MEMORY_ACTIVE_TURNS turns retained, verbatim, newest-last.
    assert len(memory.turns) == settings.MEMORY_ACTIVE_TURNS
    expected_first_retained = n_additions - settings.MEMORY_ACTIVE_TURNS
    assert memory.turns[0].query == f"q{expected_first_retained}"
    assert memory.turns[-1].query == f"q{n_additions - 1}"

    # One fold call per overflow event (3 additions overflowed by 1 each).
    assert mock_call_tool.call_count == 3

    # The *last* fold call should have been given exactly the turn that was
    # pushed out on that addition (q9, the 10th turn, once q12 came in),
    # never one of the turns still retained in memory.turns.
    last_call_user_content = mock_call_tool.call_args.kwargs["user_content"]
    assert f"q{n_additions - settings.MEMORY_ACTIVE_TURNS - 1}" in last_call_user_content
    for retained_turn in memory.turns:
        assert retained_turn.query not in last_call_user_content or retained_turn.query == f"q{n_additions - settings.MEMORY_ACTIVE_TURNS - 1}"


@patch("agents.llm.count_tokens", side_effect=[999_999, 1])
@patch("agents.llm.call_tool")
def test_fold_into_summary_retries_once_when_over_budget(mock_call_tool, mock_count_tokens):
    mock_call_tool.return_value = {"summary": "some summary"}

    memory = _mem(turns=[
        {"query": f"q{i}", "answer": f"a{i}", "citations": []} for i in range(settings.MEMORY_ACTIVE_TURNS)
    ])
    memory = add_turn(memory, query="overflow-trigger", answer="a", citations=[])

    # First call_tool for the initial summary attempt, second because
    # count_tokens reported it as over-budget; count_tokens's second
    # (under-budget) reading stops the retry loop there.
    assert mock_call_tool.call_count == 2
    assert mock_count_tokens.call_count == 2
    assert memory.summary == "some summary"


@patch("agents.llm.count_tokens", return_value=999_999)
@patch("agents.llm.call_tool")
def test_fold_into_summary_hard_truncates_if_still_over_budget_after_retry(mock_call_tool, mock_count_tokens):
    mock_call_tool.return_value = {"summary": "x" * 10_000}

    memory = _mem(turns=[
        {"query": f"q{i}", "answer": f"a{i}", "citations": []} for i in range(settings.MEMORY_ACTIVE_TURNS)
    ])
    memory = add_turn(memory, query="overflow-trigger", answer="a", citations=[])

    assert mock_call_tool.call_count == 2
    budget = int(settings.MEMORY_SUMMARY_BUDGET_FRACTION * min(settings.MODEL_MAX_CONTEXT.values()))
    assert len(memory.summary) <= budget * 4


# --- build_context ---


@patch("agents.llm.count_tokens", return_value=999_999)
def test_build_context_truncates_oversized_summary(mock_count_tokens):
    memory = _mem(summary="y" * 10_000)
    model = "claude-opus-5"

    context = build_context(memory, model)

    budget = int(settings.MEMORY_SUMMARY_BUDGET_FRACTION * min(settings.MODEL_MAX_CONTEXT.values()))
    assert "Summary of earlier conversation:" in context
    assert "Recent exchanges:" in context
    # The summary segment embedded in context must not exceed the hard cap.
    summary_segment = context.split("Summary of earlier conversation:\n")[1].split("\n\nRecent exchanges:")[0]
    assert len(summary_segment) <= budget * 4


def test_build_context_renders_turns_verbatim():
    memory = _mem(
        summary="earlier stuff",
        turns=[{"query": "What is EGFR?", "answer": "A receptor tyrosine kinase.", "citations": ["PMID:1"]}],
    )
    with patch("agents.llm.count_tokens", return_value=1):
        context = build_context(memory, "claude-opus-5")

    assert "Q: What is EGFR?" in context
    assert "A: A receptor tyrosine kinase." in context
    assert "earlier stuff" in context


# --- contextualize_query ---


@patch("agents.llm.call_tool")
def test_contextualize_query_no_history_is_zero_cost(mock_call_tool):
    memory = _mem()
    result = contextualize_query(memory, "What is EGFR?")

    assert result == "What is EGFR?"
    mock_call_tool.assert_not_called()


@patch("agents.llm.count_tokens", return_value=1)
@patch("agents.llm.call_tool")
def test_contextualize_query_with_history_rewrites_once(mock_call_tool, mock_count_tokens):
    mock_call_tool.return_value = {"contextualized_query": "What is the safety profile of EGFR-targeted therapies?"}
    memory = _mem(
        turns=[{"query": "Tell me about EGFR", "answer": "It's a receptor.", "citations": ["PMID:1"]}],
    )

    result = contextualize_query(memory, "what about its safety profile")

    assert result == "What is the safety profile of EGFR-targeted therapies?"
    assert mock_call_tool.call_count == 1
    assert mock_call_tool.call_args.kwargs["tool_name"] == "rewrite_query"


@patch("agents.llm.count_tokens", return_value=1)
@patch("agents.llm.call_tool", side_effect=RuntimeError("api down"))
def test_contextualize_query_falls_back_to_raw_query_on_error(mock_call_tool, mock_count_tokens):
    memory = _mem(
        turns=[{"query": "Tell me about EGFR", "answer": "It's a receptor.", "citations": ["PMID:1"]}],
    )

    result = contextualize_query(memory, "what about its safety profile")

    assert result == "what about its safety profile"


@patch("agents.llm.count_tokens", return_value=1)
@patch("agents.llm.call_tool", return_value={})
def test_contextualize_query_falls_back_when_field_missing(mock_call_tool, mock_count_tokens):
    memory = _mem(
        turns=[{"query": "Tell me about EGFR", "answer": "It's a receptor.", "citations": ["PMID:1"]}],
    )

    result = contextualize_query(memory, "what about its safety profile")

    assert result == "what about its safety profile"
