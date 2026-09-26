import dataclasses

from backend.metrics import MetricsStore, RequestRecord


def _record(i: int) -> RequestRecord:
    return RequestRecord(
        timestamp=float(i),
        session_id=f"s{i}",
        question_chars=10,
        chunks_retrieved=2,
        context_chars=100,
        response_chars=50,
        latency_ms=float(i * 10),
    )


def test_maxlen_evicts_oldest():
    store = MetricsStore(maxlen=5)
    for i in range(8):
        store.record(_record(i))
    snap = store.snapshot()
    assert len(snap["recent"]) == 5
    assert [r.session_id for r in snap["recent"]] == ["s3", "s4", "s5", "s6", "s7"]


def test_total_requests_not_capped_by_maxlen():
    store = MetricsStore(maxlen=5)
    for i in range(8):
        store.record(_record(i))
    assert store.snapshot()["total_requests"] == 8


def test_avg_latency_ms_computed_correctly():
    store = MetricsStore(maxlen=10)
    store.record(_record(1))  # latency 10
    store.record(_record(2))  # latency 20
    assert store.snapshot()["avg_latency_ms"] == 15.0


def test_avg_latency_ms_zero_when_empty():
    store = MetricsStore(maxlen=10)
    assert store.snapshot()["avg_latency_ms"] == 0.0


def test_request_record_never_stores_api_key_or_raw_text():
    field_names = {f.name for f in dataclasses.fields(RequestRecord)}
    assert "api_key" not in field_names
    assert "message" not in field_names
    assert "answer" not in field_names
