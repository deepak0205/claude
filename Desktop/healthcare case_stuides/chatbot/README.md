# Claude Healthcare Case Study Chatbot

A small RAG chatbot that answers questions about the 5 Claude-in-healthcare case studies
(Banner Health, Qualified Health, Carta Healthcare, Elation Health, Commure) and this
project's HLD/LLD/dev-plan docs — built as a POC following an AIDLC-style process, reusing
patterns from `/home/labuser/agent_poc`.

## Setup
```bash
cd "healthcare case_stuides/chatbot"
pip install -r requirements.txt
cp .env.example .env   # GROQ_API_KEY here is only a dev fallback — see below
```

## Run
```bash
# terminal 1
uvicorn backend.main:app --reload

# terminal 2
streamlit run frontend/app.py
```
Open the Streamlit UI, paste a Groq API key (from [console.groq.com/keys](https://console.groq.com/keys))
into the sidebar field, then chat. The key is sent per-request to the backend and never written to disk —
if you'd rather not use the UI field, set `GROQ_API_KEY` in `.env` as a dev fallback instead.

## Test
```bash
pytest tests/ -v
python tests/validate_poc.py
```

## Load test
```bash
GROQ_API_KEY=your-real-key k6 run load_test/chat_load_test.js
```
Without a real key the backend correctly rejects every request with 400/401, which will fail the script's `status is 200` check — that's expected, not a bug.

Stages ramp 0→10→40 concurrent virtual users (see `load_test/chat_load_test.js`); each VU keeps its own persistent `session_id` across iterations, so this actually exercises the per-session locking in `backend/main.py`, not one VU repeating serially. At 40 VUs against a *real* Groq key you may see Groq's own rate limits surface as `http_req_failed` — that's expected, tune `--vus`/`target` down for real-key runs.

## Analytics dashboards
The Streamlit UI's **📊 Analytics** tab has two dashboards, both reading live backend state (no fabricated data):
- **Traffic** — `GET /metrics`: total requests, average latency, and per-request latency/context-size trends (last 500 requests, lengths/counts only — never raw text or the API key).
- **Knowledge base** — `GET /corpus`: doc/chunk/character counts, a per-doc chunk-count chart, and an embedded interactive knowledge graph of `backend/docs` (`graphify-out/graph.html`). Regenerate the graph after editing the docs:
  ```bash
  /graphify backend/docs
  ```

## Specs
- `specs/openapi.json` — generated from the live FastAPI schema. Regenerate before tagging a release:
  ```bash
  python specs/generate_openapi.py
  ```
- `specs/SPEC.md` — requirements/design spec (endpoints, concurrency model, dashboards/privacy, versioning, testing/load-testing strategy).

## MCP server (standalone)
```bash
python -m mcp_server.case_study_server
```

## Architecture
- `backend/rag/` — TF-IDF retrieval over the 4 markdown docs in `backend/docs/` (no external
  embeddings API needed; swap in real embeddings via the `ToolProvider` protocol if the corpus grows).
- `backend/agent.py` — tool-use loop over Groq's `openai/gpt-oss-120b` (OpenAI-compatible Chat Completions API), grounded in retrieved passages only. The Groq API key comes per-request from the user via the frontend's sidebar field (`ChatRequest.api_key`), not from server config.
- `backend/memory.py` — rolling-summary conversation memory (last N turns verbatim, older turns
  folded into a summary capped at ~12% of accumulated history).
- `backend/main.py` — FastAPI `POST /chat`, `GET /health`, `GET /metrics`, `GET /corpus`. Per-session locking makes `/chat` safe under real concurrent load.
- `backend/metrics.py` — bounded in-memory request metrics backing `/metrics` (lengths/counts only).
- `frontend/app.py` — Streamlit chat UI.
- `mcp_server/case_study_server.py` — the same retrieval exposed as a standalone MCP tool/resource server.
- `.claude/` — project subagents (`backend`, `frontend`, `p3-triage`) with a scope-enforcing hook
  and an auto-pytest hook, mirroring `agent_poc`'s conventions.

See `~/.claude/plans/async-splashing-mccarthy.md` for the full build plan and step-by-step rationale.
