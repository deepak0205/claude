"""Minimal shared pydantic models for the agentic tool-use layer.

Not the full LangGraph `GraphState` — that's deferred to `agents/graph.py`
in a later phase. `Evidence` matches the shape returned by
`rag/retriever.py:hybrid_search`; `AgentResult` matches the shape of the
`report_findings` tool every real sub-agent finishes with.
"""

from pydantic import BaseModel


class Evidence(BaseModel):
    pmid: str
    title: str
    journal: str
    year: int
    snippet: str
    entities: list[str] = []
    entity_path: list[str] = []
    similarity_score: float = 0.0


class AgentResult(BaseModel):
    agent_name: str
    summary: str
    key_citations: list[str] = []
    confidence: float = 0.0
