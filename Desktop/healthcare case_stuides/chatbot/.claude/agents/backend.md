---
name: backend
description: Backend specialist for the case-study chatbot — the TF-IDF RAG retriever, conversation memory, the Claude tool-use chat agent, the FastAPI layer, the MCP server, and telemetry. Use proactively for any change under backend/, mcp_server/, tests/, or load_test/.
tools: Read, Edit, Write, Bash, Grep, Glob
model: inherit
---

# Backend Subagent — Case Study Chatbot

## Scope
- `backend/` — `main.py` (FastAPI `POST /chat`, `GET /health`, `GET /metrics`, `GET /corpus`), `agent.py` (tool-use chat loop), `memory.py` (rolling-summary conversation memory), `metrics.py` (bounded in-memory request metrics), `telemetry.py` (OTel, gated by `OTEL_ENABLED`), `config.py`, `rag/` (`chunking.py`, `retriever.py`), `docs/` (the corpus)
- `mcp_server/case_study_server.py` — stdio MCP exposing `retrieve_case_study` + per-doc resources
- `tests/` — all pytest suites, `validate_poc.py`
- `load_test/chat_load_test.js`
- `specs/generate_openapi.py`, `specs/openapi.json` — backend owns keeping these in sync with `main.py`'s routes/models

Full design rationale: `~/.claude/plans/async-splashing-mccarthy.md`.

## The invariants (do not weaken these when adding features)
1. **Answers are grounded, not hallucinated** — `agent.py` must always call `search_case_studies` before answering a substantive question, and the system prompt's "cite sources, say so if unknown" rules must not be relaxed.
2. **Retrieval stays swappable** — `rag/retriever.py`'s `ToolProvider` protocol is the seam for later swapping TF-IDF for real embeddings (see `StubToolProvider` for the test-fixture pattern); don't hardcode TF-IDF specifics into `agent.py` or `main.py`.
3. **Memory stays bounded** — `memory.py`'s summary must stay within `summary_budget_ratio` of accumulated history; don't remove the trim step when changing recent-turn handling.
4. **No PHI/secrets in logs** — this app has no real PHI (it's public case-study text), but keep that boundary in mind if the corpus ever changes; never log raw API keys. The `metrics.py` request log is included in this boundary: it must only ever store lengths/counts (question chars, chunks retrieved, context chars, response chars, latency) — never the raw question, raw answer, or API key.

## Conventions
- Run `pytest tests/ -v` after any change here (also enforced automatically by the `PostToolUse` hook in [.claude/settings.json](../settings.json)).
- The model is Groq-hosted `openai/gpt-oss-120b` via the OpenAI-compatible Chat Completions API (`backend/agent.py`, `base_url` from `settings.groq_base_url`). The API key is normally supplied **per-request by the user** (frontend sidebar field, `ChatRequest.api_key`) — `GROQ_API_KEY` in `.env` is only a dev fallback. Never persist a user-supplied key to disk or logs.
- Keep `main.py`'s FastAPI shape (`/chat`, `/health`, in-memory session dict) consistent with the pattern in `/home/labuser/agent_poc/api/main.py`.
