"""Tests for agents/tools.py. No live API/retrieval calls — `search_fn` is
injected directly into `RetrievalToolProvider`."""

from types import SimpleNamespace

import pytest

from agents.tools import RetrievalToolProvider, StubToolProvider


def _fake_evidence(n=2):
    return [
        SimpleNamespace(
            pmid=f"{1000 + i}",
            title=f"Title {i}",
            journal=f"Journal {i}",
            year=2020 + i,
            snippet=f"Snippet {i}",
        )
        for i in range(n)
    ]


def test_execute_calls_search_fn_with_clamped_top_k_below_min():
    calls = []

    def fake_search_fn(query, entity_bias, top_k):
        calls.append((query, entity_bias, top_k))
        return _fake_evidence()

    provider = RetrievalToolProvider(entity_bias="disease", search_fn=fake_search_fn)
    provider.execute("search_evidence", {"query": "EGFR", "top_k": 0})

    assert calls == [("EGFR", "disease", 1)]


def test_execute_calls_search_fn_with_clamped_top_k_above_max():
    calls = []

    def fake_search_fn(query, entity_bias, top_k):
        calls.append((query, entity_bias, top_k))
        return _fake_evidence()

    provider = RetrievalToolProvider(entity_bias=None, search_fn=fake_search_fn)
    provider.execute("search_evidence", {"query": "EGFR", "top_k": 999})

    assert calls == [("EGFR", None, 20)]


def test_execute_uses_default_top_k_when_missing():
    calls = []

    def fake_search_fn(query, entity_bias, top_k):
        calls.append(top_k)
        return _fake_evidence()

    provider = RetrievalToolProvider(entity_bias="target", search_fn=fake_search_fn)
    provider.execute("search_evidence", {"query": "EGFR"})

    assert calls == [5]


def test_execute_formats_output_with_pmid_prefix():
    def fake_search_fn(query, entity_bias, top_k):
        return _fake_evidence(3)

    provider = RetrievalToolProvider(entity_bias=None, search_fn=fake_search_fn)
    output = provider.execute("search_evidence", {"query": "EGFR", "top_k": 5})

    for i in range(3):
        assert f"PMID: {1000 + i}" in output
        assert f"Title {i}" in output
        assert f"Journal {i}" in output
        assert f"Snippet {i}" in output


def test_execute_is_stateless_across_calls():
    def fake_search_fn(query, entity_bias, top_k):
        return _fake_evidence(1)

    provider = RetrievalToolProvider(entity_bias=None, search_fn=fake_search_fn)
    provider.execute("search_evidence", {"query": "a", "top_k": 3})
    provider.execute("search_evidence", {"query": "b", "top_k": 7})

    # No per-call state leaked onto the singleton.
    assert not hasattr(provider, "last_query")
    assert not hasattr(provider, "last_top_k")


def test_retrieval_tool_provider_tools_shape():
    provider = RetrievalToolProvider(entity_bias=None, search_fn=lambda *a, **k: [])
    assert len(provider.tools) == 1
    tool = provider.tools[0]
    assert tool["name"] == "search_evidence"
    assert tool["strict"] is True
    assert tool["input_schema"]["additionalProperties"] is False
    assert tool["input_schema"]["required"] == ["query"]


def test_stub_tool_provider_has_no_tools():
    provider = StubToolProvider()
    assert provider.tools == []


def test_stub_tool_provider_execute_raises():
    provider = StubToolProvider()
    with pytest.raises(NotImplementedError):
        provider.execute("anything", {})
