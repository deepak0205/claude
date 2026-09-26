"""FastAPI surface for the agentic RAG pipeline: `POST /query`, `GET /health`.

In-memory session store (`_sessions`) — no DB, single-instance POC scope,
consistent with `agents/memory.py`'s `ConversationMemory` design (Addendum
1). This is also the HTTP target k6's load tests (`scripts/load_test/*.js`)
hit.
"""

import uuid

from fastapi import FastAPI
from pydantic import BaseModel

from agents import graph
from agents.memory import ConversationMemory, add_turn
from config.settings import settings
from config.telemetry import tracer
from rag import neo4j_client

app = FastAPI()

_sessions: dict[str, ConversationMemory] = {}


class QueryRequest(BaseModel):
    session_id: str | None = None
    query: str


@app.post("/query")
def query(request: QueryRequest) -> dict:
    with tracer.start_as_current_span("api.query"):
        session_id = request.session_id if request.session_id in _sessions else str(uuid.uuid4())
        memory = _sessions.get(session_id, ConversationMemory(session_id=session_id))

        result = graph.run_query(request.query, memory)

        final_answer = result["final_answer"]
        final_citations = result["final_citations"]
        citation_pmids = [c["pmid"] for c in final_citations if "pmid" in c]

        _sessions[session_id] = add_turn(memory, request.query, final_answer, citation_pmids)

        agent_results = {
            name: agent_result.model_dump() for name, agent_result in result["agent_results"].items()
        }

        return {
            "session_id": session_id,
            "routing_decision": result["routing_decision"],
            "agent_results": agent_results,
            "final_answer": final_answer,
            "final_citations": final_citations,
        }


@app.get("/health")
def health() -> dict:
    with tracer.start_as_current_span("api.health"):
        neo4j_up = False
        try:
            neo4j_client.run_query("RETURN 1")
            neo4j_up = True
        except Exception:
            neo4j_up = False

        anthropic_configured = bool(settings.ANTHROPIC_API_KEY)

        status = "ok" if (neo4j_up and anthropic_configured) else "degraded"

        return {"status": status, "neo4j": neo4j_up, "anthropic_configured": anthropic_configured}
