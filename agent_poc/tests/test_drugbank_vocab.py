"""Tests for ingestion/drugbank_vocab.py. Uses a real local CSV via
`tmp_path` (local file I/O is fine per the plan — no network calls exist in
this module at all)."""

import csv

from ingestion.drugbank_vocab import enrich_molecules, load_vocab_csv


def _write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_load_vocab_csv_normalizes_rows(tmp_path):
    csv_path = tmp_path / "drugbank_vocab.csv"
    _write_csv(
        csv_path,
        [
            {
                "DrugBank ID": "DB00530",
                "Common name": "Erlotinib",
                "CAS Number": "183321-74-6",
                "Synonyms": "Erlotinib hydrochloride | OSI-774",
            }
        ],
        fieldnames=["DrugBank ID", "Common name", "CAS Number", "Synonyms"],
    )

    rows = load_vocab_csv(str(csv_path))

    assert rows == [
        {
            "name": "erlotinib",
            "display_name": "Erlotinib",
            "drugbank_id": "DB00530",
            "cas_number": "183321-74-6",
            "aliases": ["Erlotinib hydrochloride", "OSI-774"],
        }
    ]


def test_load_vocab_csv_skips_rows_with_no_common_name(tmp_path):
    csv_path = tmp_path / "drugbank_vocab.csv"
    _write_csv(
        csv_path,
        [
            {"DrugBank ID": "DB00001", "Common name": "", "CAS Number": "", "Synonyms": ""},
            {"DrugBank ID": "DB00002", "Common name": "Aspirin", "CAS Number": "50-78-2", "Synonyms": ""},
        ],
        fieldnames=["DrugBank ID", "Common name", "CAS Number", "Synonyms"],
    )

    rows = load_vocab_csv(str(csv_path))

    assert len(rows) == 1
    assert rows[0]["name"] == "aspirin"
    assert rows[0]["aliases"] == []


def test_load_vocab_csv_handles_missing_optional_columns(tmp_path):
    csv_path = tmp_path / "drugbank_vocab.csv"
    _write_csv(
        csv_path,
        [{"Common name": "Aspirin"}],
        fieldnames=["Common name"],
    )

    rows = load_vocab_csv(str(csv_path))

    assert rows == [
        {
            "name": "aspirin",
            "display_name": "Aspirin",
            "drugbank_id": None,
            "cas_number": None,
            "aliases": [],
        }
    ]


def test_enrich_molecules_shapes_for_load_entities():
    vocab_rows = [
        {
            "name": "erlotinib",
            "display_name": "Erlotinib",
            "drugbank_id": "DB00530",
            "cas_number": "183321-74-6",
            "aliases": ["OSI-774"],
        }
    ]

    enriched = enrich_molecules(vocab_rows)

    assert enriched == [
        {
            "name": "erlotinib",
            "display_name": "Erlotinib",
            "aliases": ["OSI-774"],
            "drugbank_id": "DB00530",
            "cas_number": "183321-74-6",
        }
    ]


def test_enrich_molecules_skips_rows_without_name():
    assert enrich_molecules([{"name": ""}]) == []
    assert enrich_molecules([{}]) == []
