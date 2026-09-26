# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] - 2026-09-26

### Added
- `GET /metrics` — bounded traffic/usage analytics (total requests, average latency, last 500 requests' lengths/timings). Backed by the new `backend/metrics.py` `MetricsStore`; stores lengths/counts only, never raw question/answer text or the API key.
- `GET /corpus` — knowledge-base stats (doc count, chunk count, total characters, per-doc chunk counts), computed once at import from the existing retriever/chunker.
- Analytics tab in the Streamlit UI (`frontend/app.py`) with two dashboards: **Traffic** (live `/metrics` charts) and **Knowledge base** (`/corpus` chart + an embedded interactive knowledge graph of `backend/docs`, generated via `/graphify`).
- `specs/` directory: `openapi.json` (generated from the live FastAPI schema via `specs/generate_openapi.py`) and `SPEC.md` (hand-written requirements/design spec — endpoints, concurrency model, dashboards/privacy, versioning, testing/load-testing strategy).
- `graphify-out/graph.html` + `GRAPH_REPORT.md` — interactive knowledge graph of the case-study docs (8 communities, cross-doc rationale/similarity edges). Regenerate with `/graphify backend/docs` whenever `backend/docs/*.md` changes.
- Dark theme (`.streamlit/config.toml`) and a gradient header for the previously "pale" UI.
- App version exposed as `APP_VERSION = "1.0.0"` in `backend/main.py`, surfaced in `GET /health` and the FastAPI OpenAPI metadata.

### Changed
- `/chat` is now safe under real concurrent load: a `_registry_lock` guards session get-or-create, and a per-`session_id` lock serializes same-session turns (required because `ConversationMemory`'s summary-fold step is multi-step and non-atomic) while leaving different sessions fully concurrent.
- `load_test/chat_load_test.js` rewritten from a flat `vus: 5, duration: 20s` script to a staged ramp (0→10→40 VUs) with per-VU persistent `session_id`, tighter thresholds (`p95<3000ms`, `p99<6000ms`, error rate `<5%`, check pass rate `>95%`), and a `has session_id field` check — actually simulates multiple concurrent users instead of one VU repeating serially.
- `backend/agent.py`'s `ChatAgent` now tracks `last_chunks_retrieved`/`last_context_chars` per call so `/metrics` can report real retrieval sizes.

### No breaking changes
`/chat` and `/health` request/response shapes are unchanged; `/health` gained one new field (`version`).

### Known limitations (unchanged from v0, not addressed in v1)
- `_sessions`/`_session_locks` grow unbounded for the lifetime of the process — no session eviction yet.
- Running the k6 script's 40-VU stage against a *real* Groq key may surface Groq's own rate limits as `http_req_failed`; this is expected, not a regression in this app's concurrency handling. Tune `target` down for real-key runs, or stub `ChatAgent.answer` to load-test the locking path in isolation.
