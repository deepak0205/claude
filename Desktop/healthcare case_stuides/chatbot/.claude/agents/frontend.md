---
name: frontend
description: Frontend specialist for the case-study chatbot's Streamlit chat UI — chat input, message history, and answer rendering. Use proactively for any change under frontend/.
tools: Read, Edit, Write, Bash, Grep, Glob
model: inherit
---

# Frontend Subagent — Case Study Chatbot

## Scope
- `frontend/app.py` — Streamlit UI, calls the FastAPI `POST /chat`/`GET /metrics`/`GET /corpus` endpoints over HTTP; kept as a separate process from `backend/`, matching the architecture's separation of concerns.
- `.streamlit/config.toml` — theme configuration for this app.

Full design rationale: `~/.claude/plans/async-splashing-mccarthy.md`.

## What the UI renders
`frontend/app.py` calls `POST /chat` on the FastAPI service (`backend/main.py`) and renders exactly what's returned — never fabricates or reformats an answer itself. Required elements:
- Sidebar field for the user's own Groq API key (`type="password"`, kept only in `st.session_state`, sent with each request as `ChatRequest.api_key` — never written to disk by this app)
- Chat input, disabled until a key is entered + running message history (`st.session_state.history`)
- Session continuity via `session_id` returned by the backend
- Plain error message (including the backend's 400 detail when the key is missing/rejected) if a request fails, rather than an uncaught exception

## Conventions
- Never log or persist the user's API key; it should only ever live in `st.session_state` for the current browser session.
- After any change here, manually smoke-test with `streamlit run frontend/app.py` against a running `uvicorn backend.main:app --reload` — enter a real Groq key, ask a question, and confirm the answer renders and cites a source doc. There's no UI test suite, so this isn't covered by the `pytest` hook.
