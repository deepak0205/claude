"""DrugBank *open vocabulary* CSV loader — local file only, no network call.

Per Addendum 3's explicit scope decision, this module reads a **local CSV
file that the user downloads themselves** from DrugBank's free,
license-free "open data" vocabulary page (drug names, synonyms, and
external IDs only — CAS numbers, DrugBank IDs). It never calls the licensed
DrugBank API/database, requires no credentials, and makes no network
requests at all; `DRUGBANK_VOCAB_PATH` (see `config/settings.py`) simply
points at wherever the user saved that CSV.

Expected CSV columns (DrugBank's standard open-vocabulary export):
`DrugBank ID`, `Common name`, `CAS Number`, `Synonyms` (synonyms pipe-`|`-
separated within the cell). Only these four columns are read; any other
columns in the export are ignored.
"""

import csv


def load_vocab_csv(path: str) -> list[dict]:
    """Read the DrugBank open-vocabulary CSV at `path` and return one
    normalized dict per row: `{name (lowercased common name), display_name
    (original-case common name), drugbank_id, cas_number, aliases:
    list[str]}`. Rows with no `Common name` are skipped."""
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            common_name = (raw.get("Common name") or "").strip()
            if not common_name:
                continue
            drugbank_id = (raw.get("DrugBank ID") or "").strip() or None
            cas_number = (raw.get("CAS Number") or "").strip() or None
            synonyms_raw = (raw.get("Synonyms") or "").strip()
            aliases = [s.strip() for s in synonyms_raw.split("|") if s.strip()] if synonyms_raw else []
            rows.append(
                {
                    "name": common_name.lower(),
                    "display_name": common_name,
                    "drugbank_id": drugbank_id,
                    "cas_number": cas_number,
                    "aliases": aliases,
                }
            )
    return rows


def enrich_molecules(vocab_rows: list[dict]) -> list[dict]:
    """Shape `load_vocab_csv`'s output for `neo4j_loader.load_entities(...,
    label="Molecule")`. Uses the same `name` key as PubMed/ChEMBL-derived
    Molecule nodes so the loader's `MERGE (n:Molecule {name: row.name})`
    matches the existing node and enriches it (`drugbank_id`, `cas_number`,
    `aliases`) rather than creating a duplicate."""
    return [
        {
            "name": row["name"],
            "display_name": row.get("display_name") or row["name"],
            "aliases": row.get("aliases", []),
            "drugbank_id": row.get("drugbank_id"),
            "cas_number": row.get("cas_number"),
        }
        for row in vocab_rows
        if row.get("name")
    ]
