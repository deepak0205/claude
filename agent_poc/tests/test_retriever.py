"""Tests for rag/retriever.py. `rag.neo4j_client.run_query` and
`ingestion.embedding.embed_query` are mocked entirely — no live Neo4j or
Voyage calls. `run_query` is dispatched by the `// marker` comment each
query in `rag/retriever.py` carries, so tests don't depend on exact Cypher
formatting."""

from unittest.mock import patch

from agents.state import Evidence
from rag.retriever import hybrid_search


def _marker(cypher: str) -> str:
    for line in cypher.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            return stripped[2:].strip()
    return ""


def _make_run_query(responses: dict[str, list[dict]]):
    def _run_query(cypher, **kwargs):
        return responses.get(_marker(cypher), [])

    return _run_query


def _paper_vector_row(pmid, score, title="Title", journal="J", pub_date="2022 Jan", snippet="snippet text"):
    return {
        "chunk_id": f"c_{pmid}",
        "snippet": snippet,
        "score": score,
        "pmid": pmid,
        "title": title,
        "journal": journal,
        "pub_date": pub_date,
        "nct_id": None,
        "trial_title": None,
        "phase": None,
    }


def _trial_vector_row(nct_id, score, title="Trial Title", phase="Phase 2", snippet="trial snippet"):
    return {
        "chunk_id": f"c_{nct_id}",
        "snippet": snippet,
        "score": score,
        "pmid": None,
        "title": None,
        "journal": None,
        "pub_date": None,
        "nct_id": nct_id,
        "trial_title": title,
        "phase": phase,
    }


def test_hybrid_search_basic_vector_only_no_bias():
    responses = {
        "vector_search": [_paper_vector_row("1", 0.9), _paper_vector_row("2", 0.8)],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1, 0.2]) as mock_embed, \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)):
        results = hybrid_search("egfr resistance", entity_bias=None, top_k=5, candidate_pool=20)

    mock_embed.assert_called_once_with("egfr resistance")
    assert len(results) == 2
    assert all(isinstance(r, Evidence) for r in results)
    assert results[0].pmid == "1"
    assert results[0].similarity_score == 0.9
    assert results[1].pmid == "2"


def test_hybrid_search_returns_empty_when_no_vector_hits():
    responses = {"vector_search": []}
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)):
        results = hybrid_search("no matches", entity_bias=None)

    assert results == []


def test_hybrid_search_literature_bias_does_not_reweight():
    responses = {
        "vector_search": [_paper_vector_row("1", 0.5), _paper_vector_row("2", 0.9)],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)) as mock_run:
        results = hybrid_search("query", entity_bias="literature")

    # No bias_boost query should have been issued for literature bias.
    markers = [_marker(call.args[0]) for call in mock_run.call_args_list]
    assert "bias_boost" not in markers
    assert results[0].pmid == "2"
    assert results[0].similarity_score == 0.9


def test_hybrid_search_disease_bias_boosts_matching_candidates():
    responses = {
        "vector_search": [_paper_vector_row("1", 0.5), _paper_vector_row("2", 0.6)],
        "bias_boost": [{"pmid": "1"}],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)) as mock_run:
        results = hybrid_search("egfr in lung cancer", entity_bias="disease", top_k=5)

    bias_calls = [c for c in mock_run.call_args_list if _marker(c.args[0]) == "bias_boost"]
    assert len(bias_calls) == 1
    assert set(bias_calls[0].kwargs["pmids"]) == {"1", "2"}

    # pmid "1" was boosted (0.5 * 1.2 = 0.6) so it should now outrank pmid "2" (0.6).
    assert results[0].pmid == "1"
    assert results[0].similarity_score >= 0.6
    assert results[1].pmid == "2"


def test_hybrid_search_target_bias_uses_target_label():
    responses = {
        "vector_search": [_paper_vector_row("1", 0.5)],
        "bias_boost": [{"pmid": "1"}],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)) as mock_run:
        hybrid_search("egfr", entity_bias="target")

    bias_call = next(c for c in mock_run.call_args_list if _marker(c.args[0]) == "bias_boost")
    assert ":Target)" in bias_call.args[0]


def test_hybrid_search_clinical_trial_bias_boosts_trial_rows_without_extra_query():
    responses = {
        "vector_search": [_paper_vector_row("1", 0.9), _trial_vector_row("NCT001", 0.5)],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)) as mock_run:
        results = hybrid_search("trial evidence", entity_bias="clinical_trial")

    markers = [_marker(c.args[0]) for c in mock_run.call_args_list]
    assert "bias_boost" not in markers  # no extra query for clinical_trial bias

    trial_evidence = next(r for r in results if r.pmid == "NCT001")
    assert trial_evidence.similarity_score == 0.6  # 0.5 * 1.2


def test_hybrid_search_dedupes_expansion_duplicate_of_existing_candidate():
    responses = {
        "vector_search": [_paper_vector_row("1", 0.9)],
        "expand_paper_to_papers": [
            {"pmid": "1", "title": "Title", "journal": "J", "pub_date": "2022", "snippet": "dup"},
            {"pmid": "2", "title": "Other", "journal": "J2", "pub_date": "2021", "snippet": "new"},
        ],
        "expand_paper_to_trials": [],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)):
        results = hybrid_search("query", entity_bias=None, top_k=10)

    pmids = [r.pmid for r in results]
    assert pmids.count("1") == 1
    assert "2" in pmids
    # the original vector-matched score (0.9) should win over the
    # expansion-only duplicate's heuristic score.
    assert next(r for r in results if r.pmid == "1").similarity_score == 0.9


def test_hybrid_search_dedupes_by_nct_id():
    responses = {
        "vector_search": [_trial_vector_row("NCT001", 0.7)],
        "expand_paper_to_papers": [],
        "expand_paper_to_trials": [],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)):
        results = hybrid_search("trial", entity_bias=None)

    assert len(results) == 1
    assert results[0].pmid == "NCT001"


def test_hybrid_search_expands_from_trial_seeds_to_papers():
    responses = {
        "vector_search": [_trial_vector_row("NCT001", 0.7)],
        "expand_trial_to_papers": [
            {"pmid": "99", "title": "Sibling paper", "journal": "J", "pub_date": "2020", "snippet": "s"}
        ],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)) as mock_run:
        results = hybrid_search("trial", entity_bias=None, top_k=10)

    call = next(c for c in mock_run.call_args_list if _marker(c.args[0]) == "expand_trial_to_papers")
    assert call.kwargs["seed_nct_ids"] == ["NCT001"]
    assert any(r.pmid == "99" for r in results)


def test_hybrid_search_truncates_to_top_k():
    responses = {
        "vector_search": [_paper_vector_row(str(i), 0.1 * i) for i in range(1, 11)],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)):
        results = hybrid_search("query", entity_bias=None, top_k=3)

    assert len(results) == 3
    # highest scores first
    assert [r.similarity_score for r in results] == sorted(
        [r.similarity_score for r in results], reverse=True
    )


def test_hybrid_search_results_are_well_formed_evidence():
    responses = {
        "vector_search": [_paper_vector_row("1", 0.9, title="T", journal="J", pub_date="2022 Jan 05")],
    }
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)):
        results = hybrid_search("query", entity_bias=None)

    evidence = results[0]
    assert isinstance(evidence, Evidence)
    assert evidence.pmid == "1"
    assert evidence.title == "T"
    assert evidence.journal == "J"
    assert evidence.year == 2022
    assert evidence.snippet == "snippet text"
    assert evidence.entities == []
    assert evidence.similarity_score == 0.9


def test_hybrid_search_passes_candidate_pool_to_vector_query():
    responses = {"vector_search": [_paper_vector_row("1", 0.5)]}
    with patch("rag.retriever.embed_query", return_value=[0.1]), \
         patch("rag.retriever.run_query", side_effect=_make_run_query(responses)) as mock_run:
        hybrid_search("query", entity_bias=None, candidate_pool=42)

    vector_call = next(c for c in mock_run.call_args_list if _marker(c.args[0]) == "vector_search")
    assert vector_call.kwargs["candidate_pool"] == 42
