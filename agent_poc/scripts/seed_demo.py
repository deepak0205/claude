"""Full multi-source ingestion pipeline for one demo topic.

Orchestrates all five sources in the order Addendum 3 specifies — OpenTargets
last, since it enriches entities the PubMed/ChEMBL/ClinicalTrials steps must
have already created:

1. `rag.schema.ensure_schema()` — constraints + vector/fulltext/lookup indexes.
2. PubMed: search -> fetch -> extract entities per abstract -> chunk -> embed
   -> load (papers, chunks, entities, mentions, disease-target associations,
   molecule-target relations).
3. ChEMBL: fetch molecules for the targets discovered in step 2 -> load.
4. DrugBank vocab: if `settings.DRUGBANK_VOCAB_PATH` is set, load + enrich
   molecules by name match.
5. ClinicalTrials.gov: fetch trials for `--condition`/`--intervention` ->
   chunk+embed brief summaries -> load trials + chunks.
6. OpenTargets: enrich `ASSOCIATED_WITH`/`TARGETS` edges for the
   diseases/targets already in the graph.

Every write goes through the already-tested `ingestion.neo4j_loader`
functions, so the only untested logic here is argument parsing and
sequencing (per Addendum 3's test scope note) — this script is meant for
manual/live running by the user against a real Neo4j + live API keys, not
for the automated test suite.

Usage:
    python scripts/seed_demo.py --query "EGFR AND lung cancer" \\
        --condition "lung cancer" --intervention erlotinib --max-results 200
"""

import argparse
import os
import sys

# Standalone script (no `scripts/__init__.py`), so running it directly as
# `python scripts/seed_demo.py` only puts `scripts/` itself on `sys.path`,
# not the repo root — insert the repo root so the top-level packages below
# (`config`, `ingestion`, `rag`) resolve regardless of invocation style.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from ingestion import chembl_client, chunking, clinicaltrials_client, drugbank_vocab, embedding, entity_extraction, opentargets_client, pubmed_client
from ingestion.neo4j_loader import (
    load_associations,
    load_chunks,
    load_entities,
    load_mentions,
    load_papers,
    load_targets_relation,
    load_trials,
)
from rag.schema import ensure_schema


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the agent_poc Neo4j graph from all five sources.")
    parser.add_argument(
        "--query",
        default=settings.DEMO_TOPIC_QUERY,
        help="PubMed search term (esearch query string).",
    )
    parser.add_argument(
        "--condition",
        default=None,
        help="Condition to search ClinicalTrials.gov for (defaults to --query if unset).",
    )
    parser.add_argument(
        "--intervention",
        default=None,
        help="Optional intervention/drug name to narrow the ClinicalTrials.gov search.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=settings.DEMO_MAX_RESULTS,
        help="Max PubMed abstracts and max ClinicalTrials.gov studies to pull.",
    )
    return parser.parse_args(argv)


def _embed_and_attach(chunks: list[dict]) -> list[dict]:
    """Embed each chunk's `text` (document-side) and attach as `embedding`,
    in place. Returns the same list for chaining convenience."""
    if not chunks:
        return chunks
    vectors = embedding.embed_documents([c["text"] for c in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def seed_pubmed(query: str, max_results: int) -> tuple[list[str], list[str]]:
    """Run the PubMed ingestion stage. Returns `(target_names, disease_names)`
    discovered across all abstracts, for use by the ChEMBL/OpenTargets
    stages below."""
    print(f"[pubmed] searching for PMIDs matching: {query!r} (max {max_results})")
    pmids = pubmed_client.search_pmids(query, max_results)
    print(f"[pubmed] found {len(pmids)} PMIDs")

    papers = pubmed_client.fetch_abstracts(pmids)
    print(f"[pubmed] fetched {len(papers)} abstracts (non-empty)")

    all_chunks: list[dict] = []
    all_mentions: list[dict] = []
    diseases_by_name: dict[str, dict] = {}
    targets_by_name: dict[str, dict] = {}
    molecules_by_name: dict[str, dict] = {}
    associations: list[dict] = []
    target_relations: list[dict] = []

    for paper in papers:
        pmid = paper["pmid"]
        entities = entity_extraction.extract_entities(paper["abstract"])

        chunks = chunking.chunk_text(paper["abstract"], source="pubmed", chunk_id_prefix=f"pmid_{pmid}")
        for chunk in chunks:
            chunk["pmid"] = pmid
        all_chunks.extend(chunks)

        for disease in entities["diseases"]:
            diseases_by_name[disease["name"].lower()] = {
                "name": disease["name"].lower(),
                "display_name": disease["name"],
                "aliases": disease.get("aliases", []),
            }
        for target in entities["targets"]:
            targets_by_name[target["name"].lower()] = {
                "name": target["name"].lower(),
                "display_name": target["name"],
                "aliases": target.get("aliases", []),
            }
        for molecule in entities["molecules"]:
            molecules_by_name[molecule["name"].lower()] = {
                "name": molecule["name"].lower(),
                "display_name": molecule["name"],
                "aliases": molecule.get("aliases", []),
            }

        for chunk in chunks:
            for disease in entities["diseases"]:
                all_mentions.append(
                    {"chunk_id": chunk["chunk_id"], "pmid": pmid, "label": "Disease", "name": disease["name"].lower()}
                )
            for target in entities["targets"]:
                all_mentions.append(
                    {"chunk_id": chunk["chunk_id"], "pmid": pmid, "label": "Target", "name": target["name"].lower()}
                )
            for molecule in entities["molecules"]:
                all_mentions.append(
                    {"chunk_id": chunk["chunk_id"], "pmid": pmid, "label": "Molecule", "name": molecule["name"].lower()}
                )

        for relation in entities["disease_target_relations"]:
            associations.append(
                {
                    "disease_name": relation["disease"].lower(),
                    "target_name": relation["target"].lower(),
                    "source": "pubmed_extraction",
                }
            )
        for relation in entities["molecule_target_relations"]:
            target_relations.append(
                {
                    "molecule_name": relation["molecule"].lower(),
                    "target_name": relation["target"].lower(),
                    "source": "pubmed_extraction",
                }
            )

    _embed_and_attach(all_chunks)

    load_papers(papers)
    load_chunks(all_chunks)
    load_entities(list(diseases_by_name.values()), "Disease")
    load_entities(list(targets_by_name.values()), "Target")
    load_entities(list(molecules_by_name.values()), "Molecule")
    load_mentions(all_mentions)
    load_associations(associations)
    load_targets_relation(target_relations)

    print(
        f"[pubmed] loaded {len(papers)} papers, {len(all_chunks)} chunks, "
        f"{len(diseases_by_name)} diseases, {len(targets_by_name)} targets, "
        f"{len(molecules_by_name)} molecules, {len(associations)} disease-target "
        f"associations, {len(target_relations)} molecule-target relations"
    )
    return list(targets_by_name.keys()), list(diseases_by_name.keys())


def seed_chembl(target_names: list[str]) -> None:
    if not target_names:
        print("[chembl] no targets discovered from PubMed, skipping")
        return
    print(f"[chembl] fetching molecules for {len(target_names)} targets")
    molecules = chembl_client.fetch_molecules_for_targets(target_names)
    load_entities(molecules, "Molecule")
    relations = chembl_client.to_target_relations(molecules)
    load_targets_relation(relations)
    print(f"[chembl] loaded {len(molecules)} molecules, {len(relations)} molecule-target relations")


def seed_drugbank() -> None:
    if not settings.DRUGBANK_VOCAB_PATH:
        print("[drugbank] DRUGBANK_VOCAB_PATH not set, skipping")
        return
    print(f"[drugbank] loading open-vocabulary CSV from {settings.DRUGBANK_VOCAB_PATH}")
    rows = drugbank_vocab.load_vocab_csv(settings.DRUGBANK_VOCAB_PATH)
    molecules = drugbank_vocab.enrich_molecules(rows)
    load_entities(molecules, "Molecule")
    print(f"[drugbank] enriched {len(molecules)} molecules")


def seed_clinicaltrials(condition: str, intervention: str | None, max_results: int) -> None:
    print(f"[clinicaltrials] searching studies for condition={condition!r} intervention={intervention!r}")
    trials = clinicaltrials_client.fetch_trials(condition, intervention=intervention, max_results=max_results)
    print(f"[clinicaltrials] found {len(trials)} trials")

    records = clinicaltrials_client.to_trial_records(trials, molecule_name=intervention, disease_name=condition)
    load_trials(records)

    chunks = clinicaltrials_client.chunk_brief_summaries(trials)
    _embed_and_attach(chunks)
    load_chunks(chunks)

    print(f"[clinicaltrials] loaded {len(records)} trials, {len(chunks)} brief-summary chunks")


def seed_opentargets(target_names: list[str], disease_names: list[str]) -> None:
    if not target_names and not disease_names:
        print("[opentargets] no targets/diseases discovered yet, skipping")
        return
    print(
        f"[opentargets] enriching associations/mechanisms for {len(disease_names)} diseases, "
        f"{len(target_names)} targets (POC limitation: names are passed directly as "
        f"EFO/Ensembl IDs — see ingestion/opentargets_client.py docstring)"
    )
    associations = opentargets_client.fetch_disease_target_associations(disease_names)
    load_associations(associations)

    mechanisms = opentargets_client.fetch_target_molecule_mechanisms(target_names)
    load_targets_relation(mechanisms)

    print(f"[opentargets] loaded {len(associations)} associations, {len(mechanisms)} target-molecule relations")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    condition = args.condition or args.query

    print("[schema] ensuring constraints/indexes exist")
    ensure_schema()

    target_names, disease_names = seed_pubmed(args.query, args.max_results)
    seed_chembl(target_names)
    seed_drugbank()
    seed_clinicaltrials(condition, args.intervention, args.max_results)
    seed_opentargets(target_names, disease_names)

    print("[done] seeding complete")


if __name__ == "__main__":
    main()
