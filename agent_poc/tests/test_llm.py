"""Tests for agents.llm.run_agent_loop. `agents.llm.client.messages.create`
is mocked directly — zero live API calls."""

import copy
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agents.llm import run_agent_loop

FINISH_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}


def _block(type_, name=None, input=None, id=None):
    return SimpleNamespace(type=type_, name=name, input=input, id=id)


def _response(*blocks):
    return SimpleNamespace(content=list(blocks))


def test_finishes_immediately_without_calling_tool_executor():
    finish_block = _block("tool_use", name="report_findings", input={"summary": "done"}, id="t1")
    tool_executor_calls = []

    def tool_executor(name, input):
        tool_executor_calls.append((name, input))
        return "should not be called"

    with patch("agents.llm.client.messages.create", return_value=_response(finish_block)) as mock_create:
        result = run_agent_loop(
            model="claude-sonnet-5",
            system="sys",
            user_content="query",
            tools=[{"name": "search_evidence", "input_schema": {}}],
            tool_executor=tool_executor,
            finish_tool_name="report_findings",
            finish_tool_schema=FINISH_SCHEMA,
        )

    assert result == {"summary": "done"}
    assert tool_executor_calls == []
    assert mock_create.call_count == 1


def test_regular_tool_call_then_finish():
    search_block = _block("tool_use", name="search_evidence", input={"query": "EGFR"}, id="t1")
    finish_block = _block("tool_use", name="report_findings", input={"summary": "done"}, id="t2")
    tool_executor_calls = []
    message_snapshots = []
    responses = [_response(search_block), _response(finish_block)]

    def tool_executor(name, input):
        tool_executor_calls.append((name, input))
        return "PMID: 111 some text"

    def fake_create(*args, **kwargs):
        # `messages` is a mutable list the loop keeps appending to, so snapshot
        # (deep copy) it at call time rather than relying on Mock's recorded
        # reference, which would reflect the list's *final* state instead.
        message_snapshots.append(copy.deepcopy(kwargs["messages"]))
        return responses.pop(0)

    with patch("agents.llm.client.messages.create", side_effect=fake_create) as mock_create:
        result = run_agent_loop(
            model="claude-sonnet-5",
            system="sys",
            user_content="query",
            tools=[{"name": "search_evidence", "input_schema": {}}],
            tool_executor=tool_executor,
            finish_tool_name="report_findings",
            finish_tool_schema=FINISH_SCHEMA,
        )

    assert result == {"summary": "done"}
    assert tool_executor_calls == [("search_evidence", {"query": "EGFR"})]
    assert mock_create.call_count == 2
    for call in mock_create.call_args_list:
        assert call.kwargs["tool_choice"] == {"type": "any", "disable_parallel_tool_use": True}

    # Verify the tool_result message threaded the correct tool_use_id.
    second_call_messages = message_snapshots[1]
    tool_result_msg = second_call_messages[-1]
    assert tool_result_msg["role"] == "user"
    assert tool_result_msg["content"][0]["tool_use_id"] == "t1"
    assert tool_result_msg["content"][0]["content"] == "PMID: 111 some text"


def test_max_iterations_exhausted_triggers_forced_final_call():
    # Model never calls the finish tool; always calls the regular tool.
    search_block = _block("tool_use", name="search_evidence", input={"query": "x"}, id="t1")
    finish_block = _block("tool_use", name="report_findings", input={"summary": "forced"}, id="tf")

    responses = [_response(search_block), _response(search_block), _response(finish_block)]

    with patch("agents.llm.client.messages.create", side_effect=responses) as mock_create:
        result = run_agent_loop(
            model="claude-sonnet-5",
            system="sys",
            user_content="query",
            tools=[{"name": "search_evidence", "input_schema": {}}],
            tool_executor=lambda name, input: "PMID: 1",
            finish_tool_name="report_findings",
            finish_tool_schema=FINISH_SCHEMA,
            max_iterations=2,
        )

    assert result == {"summary": "forced"}
    assert mock_create.call_count == 3
    final_call = mock_create.call_args_list[-1]
    assert final_call.kwargs["tool_choice"] == {
        "type": "tool",
        "name": "report_findings",
        "disable_parallel_tool_use": True,
    }
    # The forced final call should only offer the finish tool.
    assert len(final_call.kwargs["tools"]) == 1
    assert final_call.kwargs["tools"][0]["name"] == "report_findings"


def test_tool_executor_exception_becomes_is_error_tool_result():
    search_block = _block("tool_use", name="search_evidence", input={"query": "x"}, id="t1")
    finish_block = _block("tool_use", name="report_findings", input={"summary": "recovered"}, id="t2")
    message_snapshots = []
    responses = [_response(search_block), _response(finish_block)]

    def failing_then_ok_executor(name, input):
        raise RuntimeError("boom")

    def fake_create(*args, **kwargs):
        message_snapshots.append(copy.deepcopy(kwargs["messages"]))
        return responses.pop(0)

    with patch("agents.llm.client.messages.create", side_effect=fake_create):
        result = run_agent_loop(
            model="claude-sonnet-5",
            system="sys",
            user_content="query",
            tools=[{"name": "search_evidence", "input_schema": {}}],
            tool_executor=failing_then_ok_executor,
            finish_tool_name="report_findings",
            finish_tool_schema=FINISH_SCHEMA,
        )

    assert result == {"summary": "recovered"}

    second_call_messages = message_snapshots[1]
    tool_result_msg = second_call_messages[-1]["content"][0]
    assert tool_result_msg["is_error"] is True
    assert tool_result_msg["content"] == "boom"
