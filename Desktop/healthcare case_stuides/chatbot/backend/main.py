"""FastAPI layer: POST /chat, GET /health, GET /metrics, GET /corpus.
In-memory session store keyed by session_id.

The Groq API key is normally supplied per-request by the user via the frontend's API-key
field, not baked into server config — this backend never persists it to disk.
"""
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.agent import ChatAgent
from backend.config import DOCS_DIR, settings
from backend.memory import ConversationMemory
from backend.metrics import RequestRecord, metrics_store
from backend.rag.chunking import load_docs
from backend.rag.retriever import TfidfRetriever
from backend.telemetry import init_telemetry

APP_VERSION = "1.0.0"

app = FastAPI(title="Case Study Chatbot", version=APP_VERSION)

init_telemetry()
_retriever = TfidfRetriever(DOCS_DIR)
_sessions: dict[str, ConversationMemory] = {}
_session_locks: dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()


def _get_session(session_id: str) -> tuple[ConversationMemory, threading.Lock]:
    with _registry_lock:
        memory = _sessions.setdefault(session_id, ConversationMemory(
            recent_turns=settings.memory_recent_turns,
            summary_budget_ratio=settings.memory_summary_budget_ratio,
        ))
        lock = _session_locks.setdefault(session_id, threading.Lock())
    return memory, lock


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    api_key: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str


class RequestLogEntry(BaseModel):
    timestamp: float
    session_id: str
    question_chars: int
    chunks_retrieved: int
    context_chars: int
    response_chars: int
    latency_ms: float


class MetricsResponse(BaseModel):
    total_requests: int
    avg_latency_ms: float
    recent_requests: list[RequestLogEntry]


class DocStats(BaseModel):
    doc_id: str
    chunk_count: int
    char_count: int


class CorpusResponse(BaseModel):
    total_docs: int
    total_chunks: int
    total_chars: int
    docs: list[DocStats]


def _build_corpus_response() -> CorpusResponse:
    raw_docs = load_docs(DOCS_DIR)
    chunk_counts: dict[str, int] = {}
    for c in _retriever.chunks:
        chunk_counts[c.doc_id] = chunk_counts.get(c.doc_id, 0) + 1
    docs = [
        DocStats(doc_id=doc_id, chunk_count=chunk_counts.get(doc_id, 0), char_count=len(text))
        for doc_id, text in sorted(raw_docs.items())
    ]
    return CorpusResponse(
        total_docs=len(docs),
        total_chunks=len(_retriever.chunks),
        total_chars=sum(d.char_count for d in docs),
        docs=docs,
    )


_corpus_response = _build_corpus_response()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "groq_key_env_fallback_configured": bool(settings.groq_api_key),
        "corpus_chunks": len(_retriever.chunks),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    api_key = req.api_key or settings.groq_api_key
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Groq API key is required — provide it in the request or set GROQ_API_KEY in .env",
        )

    session_id = req.session_id or str(uuid.uuid4())
    memory, lock = _get_session(session_id)
    agent = ChatAgent(_retriever, api_key=api_key)

    start = time.perf_counter()
    with lock:
        answer = agent.answer(memory, req.message)
    latency_ms = (time.perf_counter() - start) * 1000

    metrics_store.record(RequestRecord(
        timestamp=time.time(),
        session_id=session_id,
        question_chars=len(req.message),
        chunks_retrieved=agent.last_chunks_retrieved,
        context_chars=agent.last_context_chars,
        response_chars=len(answer),
        latency_ms=latency_ms,
    ))
    return ChatResponse(session_id=session_id, answer=answer)


@app.get("/metrics", response_model=MetricsResponse)
def metrics() -> MetricsResponse:
    snap = metrics_store.snapshot()
    return MetricsResponse(
        total_requests=snap["total_requests"],
        avg_latency_ms=snap["avg_latency_ms"],
        recent_requests=[RequestLogEntry(**vars(r)) for r in snap["recent"]],
    )


@app.get("/corpus", response_model=CorpusResponse)
def corpus() -> CorpusResponse:
    return _corpus_response
