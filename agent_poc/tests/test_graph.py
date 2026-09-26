"""Tests for agents/graph.py. All 7 agent singletons, supervisor.select_agents,
synthesis.synthesize, and memory.contextualize_query are mocked — zero live
LLM/Neo4j calls. The compiled graph itself (`agents.graph.compiled_graph`)
is real, exercising the actual LangGraph fan-out/fan-in wiring."""

from unittest.mock import patch

from agents import graph
from agents.memory import ConversationMemory
from agents.state import AgentResult

ALL_AGENT_NAMES = ["literature", "disease", "target", "molecule", "clinical_trial", "safety", "competitive"]


def _make_agent_mock(agent_name):
    def run(query, selected):
        return AgentResult(
            agent_name=agent_name,
            summary=f"{agent_name} summary (selected={selected})",
            key_citations=["111"] if selected else [],
            confidence=1.0 if selected else 0.0,
        )

    return run


def _patch_all_agents():
    patches = [patch(f"agents.graph.{name}_agent", side_effect=_make_agent_mock(name)) for name in ALL_AGENT_NAMES]
    return patches


def test_run_query_routes_selected_flag_correctly_and_populates_all_seven_results():
    routed = ["literature", "target"]

    patchers = _patch_all_agents()
    for p in patchers:
        p.start()
    try:
        with patch("agents.supervisor.select_agents", return_value=routed) as mock_select, patch(
            "agents.synthesis.synthesize",
            return_value={"answer": "final synthesized answer", "citations": [{"pmid": "111", "agent_source": "literature"}]},
        ) as mock_synth, patch("agents.memory.contextualize_query", return_value="contextualized query") as mock_ctx:
            memory = ConversationMemory(session_id="s1")
            result = graph.run_query("original query", memory)
    finally:
        for p in patchers:
            p.stop()

    mock_ctx.assert_called_once_with(memory, "original query")
    mock_select.assert_called_once_with("contextualized query")

    assert set(result["agent_results"].keys()) == set(ALL_AGENT_NAMES)
    for name, agent_result in result["agent_results"].items():
        expected_selected = name in routed
        assert agent_result.summary == f"{name} summary (selected={expected_selected})"

    assert result["final_answer"] == "final synthesized answer"
    assert result["final_citations"] == [{"pmid": "111", "agent_source": "literature"}]
    assert result["routing_decision"] == routed

    mock_synth.assert_called_once()
    args, kwargs = mock_synth.call_args
    call_query = args[0] if args else kwargs.get("query")
    assert call_query == "contextualized query"


def test_run_query_no_agents_selected_all_results_still_present():
    patchers = _patch_all_agents()
    for p in patchers:
        p.start()
    try:
        with patch("agents.supervisor.select_agents", return_value=[]), patch(
            "agents.synthesis.synthesize", return_value={"answer": "answer", "citations": []}
        ), patch("agents.memory.contextualize_query", return_value="q"):
            memory = ConversationMemory(session_id="s2")
            result = graph.run_query("q", memory)
    finally:
        for p in patchers:
            p.stop()

    assert set(result["agent_results"].keys()) == set(ALL_AGENT_NAMES)
    for agent_result in result["agent_results"].values():
        assert "selected=False" in agent_result.summary
