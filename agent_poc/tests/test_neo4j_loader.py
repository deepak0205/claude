"""Tests for ingestion/neo4j_loader.py. `rag.neo4j_client.run_query` is
patched directly — zero live Neo4j connections. Every assertion checks that
a whole batch is passed as one `run_query` call (not one call per row) and
that the Cypher shape matches the expected `UNWIND`/`MERGE`/label."""

from unittest.mock import patch

from ingestion.neo4j_loader import (
    load_associations,
    load_chunks,
    load_entities,
    load_mentions,
    load_papers,
    load_targets_relation,
    load_trials,
)


def test_load_papers_batches_in_one_call():
    papers = [{"pmid": "1"}, {"pmid": "2"}, {"pmid": "3"}]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_papers(papers)

    assert mock_run_query.call_count == 1
    cypher, kwargs = mock_run_query.call_args.args[0], mock_run_query.call_args.kwargs
    assert "UNWIND $batch AS row" in cypher
    assert "MERGE (p:Paper {pmid: row.pmid})" in cypher
    assert kwargs["batch"] == papers


def test_load_papers_no_op_on_empty_list():
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_papers([])

    mock_run_query.assert_not_called()


def test_load_chunks_batches_and_links_paper():
    chunks = [
        {"chunk_id": "c1", "pmid": "1", "text": "t", "embedding": [0.1], "source": "pubmed"},
        {"chunk_id": "c2", "pmid": "2", "text": "t2", "embedding": [0.2], "source": "pubmed"},
    ]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_chunks(chunks)

    assert mock_run_query.call_count == 1
    cypher = mock_run_query.call_args.args[0]
    kwargs = mock_run_query.call_args.kwargs
    assert "UNWIND $batch AS row" in cypher
    assert "MERGE (c:Chunk {chunk_id: row.chunk_id})" in cypher
    assert "MATCH (p:Paper {pmid: row.pmid})" in cypher
    assert "MERGE (p)-[:HAS_CHUNK]->(c)" in cypher
    assert "c.embedding = row.embedding" in cypher
    assert "c.source = row.source" in cypher
    assert kwargs["batch"] == chunks


def test_load_chunks_batches_and_links_trial():
    chunks = [
        {"chunk_id": "NCT001_chunk_0", "nct_id": "NCT001", "text": "t", "embedding": [0.1], "source": "clinicaltrials"},
        {"chunk_id": "NCT002_chunk_0", "nct_id": "NCT002", "text": "t2", "embedding": [0.2], "source": "clinicaltrials"},
    ]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_chunks(chunks)

    assert mock_run_query.call_count == 1
    cypher = mock_run_query.call_args.args[0]
    kwargs = mock_run_query.call_args.kwargs
    assert "UNWIND $batch AS row" in cypher
    assert "MERGE (c:Chunk {chunk_id: row.chunk_id})" in cypher
    assert "MATCH (tr:Trial {nct_id: row.nct_id})" in cypher
    assert "MERGE (tr)-[:HAS_CHUNK]->(c)" in cypher
    assert kwargs["batch"] == chunks


def test_load_chunks_splits_mixed_pmid_and_nct_id_batch():
    chunks = [
        {"chunk_id": "c1", "pmid": "1", "text": "t", "embedding": [0.1], "source": "pubmed"},
        {"chunk_id": "NCT001_chunk_0", "nct_id": "NCT001", "text": "t2", "embedding": [0.2], "source": "clinicaltrials"},
    ]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_chunks(chunks)

    assert mock_run_query.call_count == 2
    calls = mock_run_query.call_args_list
    paper_call = next(c for c in calls if "MATCH (p:Paper {pmid: row.pmid})" in c.args[0])
    trial_call = next(c for c in calls if "MATCH (tr:Trial {nct_id: row.nct_id})" in c.args[0])
    assert paper_call.kwargs["batch"] == [chunks[0]]
    assert trial_call.kwargs["batch"] == [chunks[1]]


def test_load_entities_disease_batches_by_name():
    entities = [{"name": "lung cancer", "display_name": "Lung Cancer", "aliases": []}]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_entities(entities, "Disease")

    assert mock_run_query.call_count == 1
    cypher = mock_run_query.call_args.args[0]
    kwargs = mock_run_query.call_args.kwargs
    assert "UNWIND $batch AS row" in cypher
    assert "MERGE (n:Disease {name: row.name})" in cypher
    assert kwargs["batch"] == entities


def test_load_entities_molecule_sets_id_fields():
    entities = [{"name": "erlotinib", "display_name": "Erlotinib", "aliases": [], "chembl_id": "CHEMBL553"}]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_entities(entities, "Molecule")

    cypher = mock_run_query.call_args.args[0]
    assert "MERGE (n:Molecule {name: row.name})" in cypher
    assert "chembl_id" in cypher
    assert "drugbank_id" in cypher
    assert "cas_number" in cypher


def test_load_entities_rejects_unsupported_label():
    import pytest

    with pytest.raises(ValueError):
        load_entities([{"name": "x"}], "Paper")


def test_load_entities_no_op_on_empty_list():
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_entities([], "Target")

    mock_run_query.assert_not_called()


def test_load_mentions_batches_chunk_and_paper_rollup():
    mentions = [{"chunk_id": "c1", "pmid": "1", "label": "Target", "name": "egfr"}]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_mentions(mentions)

    assert mock_run_query.call_count == 1
    cypher = mock_run_query.call_args.args[0]
    kwargs = mock_run_query.call_args.kwargs
    assert "UNWIND $batch AS row" in cypher
    assert "MERGE (c)-[:MENTIONS]->(e)" in cypher
    assert "MERGE (p)-[:MENTIONS]->(e)" in cypher
    assert kwargs["batch"] == mentions


def test_load_associations_batches_and_appends_sources():
    associations = [
        {"disease_name": "lung cancer", "target_name": "egfr", "source": "pubmed_extraction"}
    ]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_associations(associations)

    assert mock_run_query.call_count == 1
    cypher = mock_run_query.call_args.args[0]
    kwargs = mock_run_query.call_args.kwargs
    assert "UNWIND $batch AS row" in cypher
    assert "MERGE (d)-[r:ASSOCIATED_WITH]->(t)" in cypher
    assert "r.sources" in cypher
    assert "coalesce(r.sources, [])" in cypher
    assert "opentargets_score" in cypher
    assert kwargs["batch"] == associations


def test_load_targets_relation_batches_and_appends_sources():
    relations = [
        {"molecule_name": "erlotinib", "target_name": "egfr", "source": "chembl"}
    ]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_targets_relation(relations)

    assert mock_run_query.call_count == 1
    cypher = mock_run_query.call_args.args[0]
    kwargs = mock_run_query.call_args.kwargs
    assert "UNWIND $batch AS row" in cypher
    assert "MERGE (m)-[r:TARGETS]->(t)" in cypher
    assert "r.sources" in cypher
    assert kwargs["batch"] == relations


def test_load_trials_batches_and_links_molecule_and_disease():
    trials = [
        {
            "nct_id": "NCT001",
            "title": "A trial",
            "phase": "Phase 2",
            "status": "Recruiting",
            "conditions": ["lung cancer"],
            "sponsor": "Acme",
            "molecule_name": "erlotinib",
            "disease_name": "lung cancer",
        }
    ]
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_trials(trials)

    assert mock_run_query.call_count == 1
    cypher = mock_run_query.call_args.args[0]
    kwargs = mock_run_query.call_args.kwargs
    assert "UNWIND $batch AS row" in cypher
    assert "MERGE (tr:Trial {nct_id: row.nct_id})" in cypher
    assert "MERGE (tr)-[:STUDIES]->(m)" in cypher
    assert "MERGE (tr)-[:FOR_CONDITION]->(d)" in cypher
    assert kwargs["batch"] == trials


def test_load_trials_no_op_on_empty_list():
    with patch("ingestion.neo4j_loader.run_query") as mock_run_query:
        load_trials([])

    mock_run_query.assert_not_called()
