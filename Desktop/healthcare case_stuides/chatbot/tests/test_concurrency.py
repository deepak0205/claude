import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from backend import main


def test_distinct_sessions_run_concurrently_not_serialized(monkeypatch):
    def slow_answer(self, memory, user_message):
        time.sleep(0.2)
        memory.add_turn("user", user_message)
        memory.add_turn("assistant", "ok")
        return "ok"

    monkeypatch.setattr(main.ChatAgent, "answer", slow_answer)

    client = TestClient(main.app)
    n = 6

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [
            pool.submit(client.post, "/chat", json={"message": "hi", "api_key": "test-key"})
            for _ in range(n)
        ]
        results = [f.result() for f in futures]
    elapsed = time.perf_counter() - start

    assert all(r.status_code == 200 for r in results)
    # If serialized, n distinct-session requests would take ~= n * 0.2s.
    # Real concurrency should keep this well under that.
    assert elapsed < n * 0.2


def test_same_session_requests_serialize_without_corruption(monkeypatch):
    calls = []

    def slow_answer(self, memory, user_message):
        calls.append(len(memory.turns))
        time.sleep(0.05)
        memory.add_turn("user", user_message)
        memory.add_turn("assistant", "ok")
        return "ok"

    monkeypatch.setattr(main.ChatAgent, "answer", slow_answer)

    client = TestClient(main.app)
    session_id = "shared-session-under-test"
    n = 4

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [
            pool.submit(
                client.post, "/chat",
                json={"message": "hi", "session_id": session_id, "api_key": "test-key"},
            )
            for _ in range(n)
        ]
        results = [f.result() for f in futures]

    assert all(r.status_code == 200 for r in results)
    # Each request adds exactly 2 turns; if the per-session lock held, the observed
    # turn-counts at call-start are a clean permutation of [0, 2, 4, 6] — never a
    # repeated or corrupted value from interleaved reads.
    assert sorted(calls) == [0, 2, 4, 6]
