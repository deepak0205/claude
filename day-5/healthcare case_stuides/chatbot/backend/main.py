"""FastAPI layer: POST /chat, GET /health. In-memory session store keyed by session_id.

The Groq API key is normally supplied per-request by the user via the frontend's API-key
field, not baked into server config — this backend never persists it to disk.
"""
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.agent import ChatAgent
from backend.config import DOCS_DIR, settings
from backend.memory import ConversationMemory
from backend.rag.retriever import TfidfRetriever
from backend.telemetry import init_telemetry

app = FastAPI(title="Case Study Chatbot")

init_telemetry()
_retriever = TfidfRetriever(DOCS_DIR)
_sessions: dict[str, ConversationMemory] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    api_key: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
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
    memory = _sessions.setdefault(session_id, ConversationMemory(
        recent_turns=settings.memory_recent_turns,
        summary_budget_ratio=settings.memory_summary_budget_ratio,
    ))
    agent = ChatAgent(_retriever, api_key=api_key)
    answer = agent.answer(memory, req.message)
    return ChatResponse(session_id=session_id, answer=answer)
