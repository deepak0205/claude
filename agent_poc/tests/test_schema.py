"""Tests for rag/schema.py. `rag.neo4j_client.run_query` is patched directly
— zero live Neo4j connections."""

from unittest.mock import patch

from rag.schema import ensure_schema


def test_ensure_schema_runs_all_constraints_and_indexes():
    with patch("rag.schema.run_query") as mock_run_query:
        ensure_schema()

    statements = [call.args[0] for call in mock_run_query.call_args_list]

    # 6 uniqueness constraints + 1 vector index + 1 fulltext index + 3
    # lookup indexes = 11 statements, one call each (no batching needed for
    # DDL).
    assert len(statements) == 11


def test_constraints_cover_all_six_unique_node_keys():
    with patch("rag.schema.run_query") as mock_run_query:
        ensure_schema()

    statements = " ".join(call.args[0] for call in mock_run_query.call_args_list)

    for expected in [
        "(p:Paper) REQUIRE p.pmid IS UNIQUE",
        "(c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
        "(d:Disease) REQUIRE d.name IS UNIQUE",
        "(t:Target) REQUIRE t.name IS UNIQUE",
        "(m:Molecule) REQUIRE m.name IS UNIQUE",
        "(tr:Trial) REQUIRE tr.nct_id IS UNIQUE",
    ]:
        assert expected in statements


def test_all_ddl_statements_are_idempotent():
    with patch("rag.schema.run_query") as mock_run_query:
        ensure_schema()

    for call in mock_run_query.call_args_list:
        assert "IF NOT EXISTS" in call.args[0]


def test_vector_index_shape():
    with patch("rag.schema.run_query") as mock_run_query:
        ensure_schema()

    statements = [call.args[0] for call in mock_run_query.call_args_list]
    vector_statements = [s for s in statements if "VECTOR INDEX" in s]

    assert len(vector_statements) == 1
    stmt = vector_statements[0]
    assert "chunk_embeddings" in stmt
    assert "FOR (c:Chunk) ON (c.embedding)" in stmt
    assert "vector.dimensions" in stmt and "1024" in stmt
    assert "vector.similarity_function" in stmt and "cosine" in stmt


def test_fulltext_index_covers_entity_names():
    with patch("rag.schema.run_query") as mock_run_query:
        ensure_schema()

    statements = [call.args[0] for call in mock_run_query.call_args_list]
    fulltext_statements = [s for s in statements if "FULLTEXT INDEX" in s]

    assert len(fulltext_statements) == 1
    stmt = fulltext_statements[0]
    assert "entity_fulltext" in stmt
    assert "Disease|Target|Molecule" in stmt
    assert "n.name" in stmt


def test_molecule_lookup_indexes_present_and_non_unique():
    with patch("rag.schema.run_query") as mock_run_query:
        ensure_schema()

    statements = [call.args[0] for call in mock_run_query.call_args_list]
    lookup_statements = [
        s for s in statements if "CREATE INDEX" in s and "Molecule" in s
    ]

    assert len(lookup_statements) == 3
    for prop in ["chembl_id", "drugbank_id", "cas_number"]:
        assert any(prop in s for s in lookup_statements)
    for s in lookup_statements:
        assert "CONSTRAINT" not in s
