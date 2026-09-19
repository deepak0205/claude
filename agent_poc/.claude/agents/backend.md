---
name: backend
description: Backend specialist for the agentic RAG pipeline — multi-source ingestion (PubMed, ChEMBL, DrugBank open vocab, ClinicalTrials.gov, OpenTargets), the Neo4j GraphRAG+VectorRAG retriever, the LangGraph Supervisor/sub-agents/Evidence Synthesis graph, and the FastAPI layer. Use proactively for any change under ingestion/, rag/, agents/, api/, config/, or scripts/.
tools: Read, Edit, Write, Bash, Grep, Glob
model: inherit
---

# Backend Subagent — Agentic RAG (agent_poc)

## Scope
- `ingestion/` — `pubmed_client.py`, `entity_extraction.py`, `chunking.py`, `embedding.py`, `chembl_client.py`, `drugbank_vocab.py`, `clinicaltrials_client.py`, `opentargets_client.py`, `neo4j_loader.py`
- `rag/` — `neo4j_client.py`, `schema.py` (constraints + vector index), `retriever.py` (`hybrid_search`)
- `agents/` — `state.py`, `llm.py`, `supervisor.py`, `base_subagent.py`, `real_agents.py`, `stub_agents.py`, `synthesis.py`, `graph.py`
- `api/main.py` — FastAPI `POST /query`, `GET /health`
- `config/settings.py`, `scripts/` (seed/verify/CLI tooling)
- `tests/` (all pytest suites)

Full design rationale: `~/.claude/plans/merry-bouncing-feigenbaum.md`. Project overview: [.claude/skills/agentic-rag/SKILL.md](../skills/agentic-rag/SKILL.md).

## The invariants (do not weaken these when adding features)
1. **Retrieval is grounded, not hallucinated** — every real agent's citations come from `hybrid_search` results actually returned by Neo4j (vector search + graph expansion), never from model knowledge.
2. **Structured output only** — Supervisor routing, sub-agent findings, and synthesis all use a strict tool schema with forced `tool_choice`; never parse free text out of a Claude response.
3. **Synthesis cites only real PMIDs** — the Evidence Synthesis Agent (`agents/synthesis.py`) must only cite PMIDs present in the supplied agent evidence, and must surface (not silently resolve) conflicting evidence between agents.
4. **Stub agents never fabricate** — Safety/Competitive (`agents/stub_agents.py`) must never call retrieval or the LLM; they always return the fixed placeholder with `confidence=0.0`.
5. **Static fan-out/fan-in** — `agents/graph.py` wires all 7 agents as fixed edges `supervisor -> agent -> evidence_synthesis` (not dynamic `Send()`), so the compiled graph always visualizes and demoes the full architecture regardless of which agents a given query needs. Each node checks `routing_decision` itself.

## Turning a stub agent into a real agent (the next-phase pattern)
Two pieces, one existing pipeline:
1. **Retrieval source** — extend `rag/retriever.py` (or add a sibling retriever) to query the new source, and extend `ingestion/` to load it into Neo4j with its own node label and `entity_bias` value.
2. **Promote the node** — move it from `agents/stub_agents.py` to `agents/real_agents.py` via `base_subagent.make_agent_node(agent_name, RetrievalToolProvider(entity_bias=<new_bias>), model="claude-sonnet-5")` (see `agents/tools.py` for `RetrievalToolProvider`). Routing, graph wiring, and synthesis are shared infrastructure — no changes needed there.

## Conventions
- Run `pytest tests/ -v` after any change here (also enforced automatically by the `PostToolUse` hook in [.claude/settings.json](../settings.json)).
- New Neo4j queries should be checked against `rag/schema.py`'s actual constraints/index names — don't assume a label or index exists without checking `schema.py` first.
- Keep per-role model choices (`claude-sonnet-5` for Supervisor/sub-agents, `claude-opus-5` for synthesis, `claude-haiku-4-5` for ingestion extraction) and prompt-caching (`cache_control` on each agent's fixed system prompt) as designed in the plan — don't silently change models or drop caching when touching `agents/llm.py`.
