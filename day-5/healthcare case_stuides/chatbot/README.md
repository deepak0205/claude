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
- `backend/main.py` — FastAPI `POST /chat`, `GET /health`.
- `frontend/app.py` — Streamlit chat UI.
- `mcp_server/case_study_server.py` — the same retrieval exposed as a standalone MCP tool/resource server.
- `.claude/` — project subagents (`backend`, `frontend`, `p3-triage`) with a scope-enforcing hook
  and an auto-pytest hook, mirroring `agent_poc`'s conventions.

See `~/.claude/plans/async-splashing-mccarthy.md` for the full build plan and step-by-step rationale.
