# Case Study Chatbot — v1.0.0 Requirements & Design Spec

## Overview
v0 was a single-user RAG chatbot POC. v1 adds: verified concurrent-session handling,
usage/knowledge-base analytics surfaced in the UI, a machine-readable API spec, and a
visual refresh. No breaking changes to `/chat` or `/health` request/response shapes.

## Endpoints
Source of truth: `specs/openapi.json` (regenerate with `python specs/generate_openapi.py`
after any route/model change in `backend/main.py`; `tests/test_specs.py` fails CI if it drifts).

| Method | Path       | Purpose                                              |
|--------|------------|-------------------------------------------------------|
| GET    | /health    | Liveness + version + corpus size                     |
| POST   | /chat      | Ask a question, get a grounded answer                |
| GET    | /metrics   | Traffic/usage analytics (bounded recent-request log)  |
| GET    | /corpus    | Knowledge-base stats (docs, chunks, chars)            |

## Concurrency model
`/chat` runs synchronously inside Starlette's threadpool, so concurrent requests genuinely
run on separate OS threads. Two locks address the two races that matter:
- `_registry_lock` — guards the get-or-create step for a session's `ConversationMemory`
  and its per-session lock (a single dict `setdefault` is atomic under the GIL, but the
  *pair* of setdefaults is not).
- Per-session `threading.Lock` — held around `agent.answer(...)`. `ConversationMemory`'s
  fold-overflow step is a multi-step read/pop/append sequence, not atomic; concurrent
  requests to the *same* session could otherwise corrupt `turns`/`summary`. This lock
  serializes same-session turns (which is correct conversational semantics anyway) while
  leaving requests to *different* sessions fully concurrent.

Known limitation carried from v0, not fixed in v1: `_sessions`/`_session_locks` grow
unbounded for the life of the process (no eviction/TTL).

## Analytics dashboards
- **Traffic** (`GET /metrics`): total requests, average latency, and a bounded
  (`maxlen=500`) rolling log of per-request lengths/counts — question length, chunks
  retrieved, context characters sent to the LLM, response length, latency. Privacy: the
  log stores counts and lengths only; it never stores the raw question, the raw answer,
  or the API key (enforced by `tests/test_metrics.py`'s field-name guard and
  `tests/test_api.py`'s response-body content check).
- **Knowledge base** (`GET /corpus`): per-document chunk count and character count, plus
  corpus totals — computed once at process startup since the corpus is static.
- The knowledge-base dashboard also embeds a `/graphify`-generated interactive relationship
  graph of `backend/docs/` (`graphify-out/graph.html`). Regenerate manually with
  `/graphify backend/docs` whenever the corpus changes; the frontend shows a friendly
  message if the file doesn't exist yet.

## Versioning
`APP_VERSION = "1.0.0"` in `backend/main.py`, surfaced in `/health` and in the OpenAPI
`info.version` field. A git tag `v1.0.0` is created after `pytest tests/ -v` and a k6
smoke run pass. Changes are logged in `CHANGELOG.md` (Keep a Changelog style).

## Testing & load-testing strategy
- `pytest tests/ -v` covers retrieval, memory, the API surface, metrics bounding/privacy,
  and concurrency (distinct sessions overlap in wall time; same-session requests never
  corrupt turn state).
- `load_test/chat_load_test.js` (k6) ramps 0→10→40 virtual users, each with its own
  isolated JS runtime and therefore its own persistent `session_id` across that VU's
  iterations — genuinely simulating many simultaneous distinct users, not one shared
  session. Thresholds: p95 < 3s, p99 < 6s, error rate < 5%, check pass rate > 95%.
  Running with a *real* Groq key at 40 VUs may surface Groq's own rate limits as
  `http_req_failed` — that reflects the upstream API, not this app's concurrency handling.
  To load-test the locking path in isolation, stub `ChatAgent.answer` or tune `target` down.

## Non-goals
No auth, no persistent/external session store, no horizontal scaling, no PII/PHI (corpus
is public case-study text).
