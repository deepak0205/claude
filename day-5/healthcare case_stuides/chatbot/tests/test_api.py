from fastapi.testclient import TestClient

from backend import main


def test_health_ok():
    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["corpus_chunks"] > 0


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
