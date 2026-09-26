"""Bounded in-memory request metrics for the Analytics dashboard.

Stores lengths/counts only — never raw question/answer text or the API key.
"""
import threading
from collections import deque
from dataclasses import dataclass


@dataclass
class RequestRecord:
    timestamp: float
    session_id: str
    question_chars: int
    chunks_retrieved: int
    context_chars: int
    response_chars: int
    latency_ms: float


class MetricsStore:
    def __init__(self, maxlen: int = 500):
        self._lock = threading.Lock()
        self._log: deque[RequestRecord] = deque(maxlen=maxlen)
        self._total_requests = 0
        self._total_latency_ms = 0.0

    def record(self, rec: RequestRecord) -> None:
        with self._lock:
            self._log.append(rec)
            self._total_requests += 1
            self._total_latency_ms += rec.latency_ms

    def snapshot(self) -> dict:
        with self._lock:
            avg = self._total_latency_ms / self._total_requests if self._total_requests else 0.0
            return {
                "recent": list(self._log),
                "total_requests": self._total_requests,
                "avg_latency_ms": avg,
            }


metrics_store = MetricsStore(maxlen=500)
