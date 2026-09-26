"""TF-IDF retrieval over the case-study corpus, behind a swappable ToolProvider protocol.

No external embeddings API key required — appropriate for this small, closed corpus.
Swap in a real embeddings backend (e.g. Voyage, as in agent_poc/agents/tools.py) if the
corpus grows past what TF-IDF handles well.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.rag.chunking import Chunk, build_corpus


@dataclass
class RetrievedChunk:
    doc_id: str
    heading: str
    text: str
    score: float


class ToolProvider(Protocol):
    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]: ...


class TfidfRetriever:
    def __init__(self, docs_dir: Path, chunk_size_words: int = 200, chunk_overlap_words: int = 40):
        self.chunks: list[Chunk] = build_corpus(docs_dir, chunk_size_words, chunk_overlap_words)
        if not self.chunks:
            raise ValueError(f"No markdown documents found in {docs_dir}")
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform([c.text for c in self.chunks])

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            RetrievedChunk(doc_id=self.chunks[i].doc_id, heading=self.chunks[i].heading,
                            text=self.chunks[i].text, score=float(scores[i]))
            for i in ranked if scores[i] > 0
        ]


class StubToolProvider:
    """Deterministic fixture retriever for tests — no sklearn/model call involved."""

    def __init__(self, fixture: list[RetrievedChunk]):
        self._fixture = fixture

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        return self._fixture[:top_k]
