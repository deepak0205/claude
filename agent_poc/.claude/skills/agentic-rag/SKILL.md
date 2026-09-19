---
name: agentic-rag
description: Use when working on this repo (agent_poc) — a Supervisor Agent (LangGraph) orchestrating domain sub-agents (Literature, Disease, Target, Molecule, Clinical Trial backed by real multi-source Neo4j GraphRAG+VectorRAG retrieval across PubMed, ChEMBL, DrugBank open vocab, ClinicalTrials.gov, and OpenTargets; Safety, Competitive as visible placeholder agents) into an Evidence Synthesis Agent for pharma R&D literature review and drug-discovery intelligence.
---

# agentic-rag

## What this project is

A Supervisor Agent (LangGraph) that routes a user query to relevant domain
sub-agents, each of which retrieves grounded evidence and reports back to an
Evidence Synthesis Agent that produces one final, cited answer.

- **Real agents:** Literature, Disease, Target, Molecule, Clinical Trial —
  all query the same Neo4j graph, now populated from five sources (PubMed,
  ChEMBL, DrugBank open-vocabulary data, ClinicalTrials.gov, OpenTargets) via
  a native vector index for chunk embeddings + graph traversal for entity
  expansion (GraphRAG + VectorRAG in one engine), differentiated only by an
  `entity_bias` filter (`disease`/`target`/`molecule`/`clinical_trial`, or
  none for Literature's broadest coverage).
- **Stub agents (visible, not yet wired):** Safety, Competitive — present in
  the graph so the full 7-agent architecture is demoable, but return an
  explicit "not yet wired to a data source" placeholder rather than
  fabricating an answer. No source among the five currently integrated maps
  to either of these.
- **Evidence Synthesis Agent:** one Claude call over all 7 agent results;
  cites only PMIDs actually present in the retrieved evidence, and calls out
  stub-agent gaps explicitly instead of silently omitting them.

Full design rationale, data model, retriever design, and build phases:
`~/.claude/plans/merry-bouncing-feigenbaum.md`.

## Running it

This reflects the plan's target end state — update this section as each
phase actually lands (see phase table in the plan file).

```bash
cd /home/labuser/agent_poc
cp .env.example .env                                  # fill in ANTHROPIC_API_KEY, VOYAGE_API_KEY, NEO4J_*, NCBI_EMAIL
docker compose up -d neo4j
python scripts/seed_demo.py --query "EGFR AND lung cancer" --max-results 200
uvicorn api.main:app --reload &
streamlit run ui/app.py
```

## Running tests

```bash
pytest tests/ -v
```

This also runs automatically after any `Edit`/`Write` under `ingestion/`,
`rag/`, `agents/`, `api/`, `ui/`, or `tests/` via the `PostToolUse` hook in
[.claude/settings.json](../../settings.json).

## Turning a stub agent into a real agent (the pattern used for Molecule/Clinical Trial)

Each remaining stub (Safety, Competitive) becomes real by adding exactly one
new piece per source — nothing else in the graph changes:

1. **Retrieval source** — extend `rag/retriever.py`'s `hybrid_search` (or add
   a sibling retriever) to query the new source, and extend the ingestion
   pipeline (`ingestion/`) to load it into Neo4j with its own node label and
   `entity_bias` value.
2. **Promote the node** — move the agent from `agents/stub_agents.py` to
   `agents/real_agents.py` via `base_subagent.make_agent_node(agent_name,
   RetrievalToolProvider(entity_bias=<new_bias>), model="claude-sonnet-5")`
   (see `agents/tools.py` for `RetrievalToolProvider`). Routing
   (`agents/supervisor.py`), fan-out/fan-in wiring (`agents/graph.py`), and
   synthesis (`agents/synthesis.py`) are shared infrastructure — no changes
   needed there.

## Key invariants to preserve

- Retrieval is grounded, not hallucinated: every real agent's citations come
  from `hybrid_search` results actually returned by Neo4j, never from model
  knowledge.
- The Evidence Synthesis Agent must only cite PMIDs present in the supplied
  agent evidence — never invent one — and must surface, not silently
  resolve, conflicting evidence between agents.
- Stub agents must never call retrieval or the LLM, and must never fabricate
  findings — they always return the fixed placeholder with `confidence=0.0`.
- The LangGraph graph stays a static fan-out/fan-in over all 7 agents (not
  dynamic `Send()`), so the compiled graph always visualizes and demoes the
  full architecture regardless of which agents a given query needs.
