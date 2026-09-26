from fastapi.testclient import TestClient

from backend import main


def test_health_ok():
    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["corpus_chunks"] > 0
    assert body["version"] == main.APP_VERSION


def test_chat_without_api_key_is_rejected():
    client = TestClient(main.app)
    resp = client.post("/chat", json={"message": "hello"})
    assert resp.status_code == 400
    assert "api key" in resp.json()["detail"].lower()


def test_chat_returns_answer_with_session_id(monkeypatch):
    def fake_answer(self, memory, user_message):
        memory.add_turn("user", user_message)
        memory.add_turn("assistant", "stubbed answer citing claude-healthcare-case-studies.md")
        return "stubbed answer citing claude-healthcare-case-studies.md"

    monkeypatch.setattr(main.ChatAgent, "answer", fake_answer)

    client = TestClient(main.app)
    resp = client.post("/chat", json={"message": "What did Carta Healthcare achieve?", "api_key": "test-key"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert "stubbed answer" in body["answer"]


def test_chat_reuses_session_memory(monkeypatch):
    calls = []

    def fake_answer(self, memory, user_message):
        calls.append(len(memory.turns))
        memory.add_turn("user", user_message)
        memory.add_turn("assistant", "ok")
        return "ok"

    monkeypatch.setattr(main.ChatAgent, "answer", fake_answer)

    client = TestClient(main.app)
    first = client.post("/chat", json={"message": "hello", "api_key": "test-key"}).json()
    client.post("/chat", json={
        "message": "follow up", "session_id": first["session_id"], "api_key": "test-key",
    })
    assert calls == [0, 2]


def test_metrics_reflects_chat_calls(monkeypatch):
    def fake_answer(self, memory, user_message):
        memory.add_turn("user", user_message)
        memory.add_turn("assistant", "ok")
        return "ok"

    monkeypatch.setattr(main.ChatAgent, "answer", fake_answer)

    client = TestClient(main.app)
    before = client.get("/metrics").json()["total_requests"]

    secret_key = "super-secret-test-key"
    resp = client.post("/chat", json={"message": "hello", "api_key": secret_key})
    assert resp.status_code == 200

    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    body = metrics_resp.json()
    assert body["total_requests"] == before + 1
    assert len(body["recent_requests"]) > 0
    assert secret_key not in metrics_resp.text
    assert "hello" not in metrics_resp.text


def test_corpus_endpoint():
    client = TestClient(main.app)
    resp = client.get("/corpus")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_docs"] >= 4
    assert body["total_chunks"] > 0
    for doc in body["docs"]:
        assert doc["chunk_count"] > 0
