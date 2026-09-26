"""Tests for api/main.py. `agents.graph.run_query` is mocked for `/query`;
`rag.neo4j_client.run_query` is mocked for `/health`. No live LLM/Neo4j/HTTP
calls beyond the FastAPI TestClient's in-process requests."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import _sessions, app

client = TestClient(app)


def setup_function(_):
    _sessions.clear()


def _fake_result(routing=None, answer="the answer", citations=None):
    from agents.state import AgentResult

    routing = routing or ["literature"]
    citations = citations if citations is not None else [{"pmid": "111", "agent_source": "literature"}]
    return {
        "query": "q",
        "session_id": "s",
        "contextualized_query": "q",
        "routing_decision": routing,
        "agent_results": {
            "literature": AgentResult(agent_name="literature", summary="found stuff", key_citations=["111"], confidence=0.9)
        },
        "final_answer": answer,
        "final_citations": citations,
    }


@patch("agents.graph.run_query")
def test_query_creates_new_session_when_none_given(mock_run_query):
    mock_run_query.return_value = _fake_result()

    response = client.post("/query", json={"session_id": None, "query": "What is EGFR?"})

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] is not None
    assert body["final_answer"] == "the answer"
    assert body["final_citations"] == [{"pmid": "111", "agent_source": "literature"}]
    assert body["routing_decision"] == ["literature"]
    assert body["agent_results"]["literature"]["summary"] == "found stuff"
    assert body["session_id"] in _sessions


@patch("agents.graph.run_query")
def test_query_persists_session_across_two_calls(mock_run_query):
    mock_run_query.return_value = _fake_result()

    first = client.post("/query", json={"session_id": None, "query": "What is EGFR?"})
    session_id = first.json()["session_id"]

    second = client.post("/query", json={"session_id": session_id, "query": "What about its safety profile?"})

    assert second.status_code == 200
    assert second.json()["session_id"] == session_id

    # The second call's run_query should have been invoked with a
    # ConversationMemory carrying exactly one prior turn (from the first call).
    assert mock_run_query.call_count == 2
    second_call_args = mock_run_query.call_args_list[1]
    second_query, second_memory = second_call_args.args
    assert second_query == "What about its safety profile?"
    assert len(second_memory.turns) == 1
    assert second_memory.turns[0].query == "What is EGFR?"
    assert second_memory.turns[0].answer == "the answer"
    assert second_memory.turns[0].citations == ["111"]


@patch("agents.graph.run_query")
def test_query_unknown_session_id_creates_new_session(mock_run_query):
    mock_run_query.return_value = _fake_result()

    response = client.post("/query", json={"session_id": "does-not-exist", "query": "What is EGFR?"})

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] is not None


@patch("rag.neo4j_client.run_query")
def test_health_ok_when_neo4j_up_and_anthropic_configured(mock_run_query):
    mock_run_query.return_value = [{"1": 1}]

    with patch("api.main.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = "sk-test"
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["neo4j"] is True
    assert body["anthropic_configured"] is True


@patch("rag.neo4j_client.run_query", side_effect=RuntimeError("connection refused"))
def test_health_degraded_when_neo4j_down(mock_run_query):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["neo4j"] is False
