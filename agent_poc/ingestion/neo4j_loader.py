"""Batched `UNWIND` + `MERGE` writers shared by every source ingestion
client (PubMed, ChEMBL, DrugBank vocab, ClinicalTrials.gov, OpenTargets).

Every function takes a list of dicts and does exactly one write via
`rag.neo4j_client.run_query` — never one query per item — by wrapping the
whole batch in a single `UNWIND $batch AS row` statement. This is the one
place Cypher-writing happens for loading data, so re-running ingestion for
any source stays idempotent (every write is a `MERGE`).
"""

from rag.neo4j_client import run_query
from config.telemetry import ingestion_stage_counter, traced

_ENTITY_LABELS = {"Disease", "Target", "Molecule"}


@traced("ingestion.neo4j_loader.load_papers")
def load_papers(papers: list[dict]) -> None:
    """MERGE `Paper` nodes by `pmid`, SET other properties.

    Each dict may contain: pmid, pmcid, title, abstract, journal, pub_date,
    doi.
    """
    if not papers:
        return
    run_query(
        """
        UNWIND $batch AS row
        MERGE (p:Paper {pmid: row.pmid})
        SET p.pmcid = row.pmcid,
            p.title = row.title,
            p.abstract = row.abstract,
            p.journal = row.journal,
            p.pub_date = row.pub_date,
            p.doi = row.doi
        """,
        batch=papers,
    )
    ingestion_stage_counter.add(len(papers), {"module": "neo4j_loader", "function": "load_papers"})


_CHUNK_SET_CLAUSE = """
        MERGE (c:Chunk {chunk_id: row.chunk_id})
        SET c.text = row.text,
            c.embedding = row.embedding,
            c.source = row.source,
            c.chunk_index = row.chunk_index,
            c.char_start = row.char_start,
            c.char_end = row.char_end
"""


@traced("ingestion.neo4j_loader.load_chunks")
def load_chunks(chunks: list[dict]) -> None:
    """MERGE `Chunk` nodes by `chunk_id`, SET props (including `embedding`
    and `source`), and link each chunk to its owning parent node.

    Each dict carries EITHER a `pmid` key (PubMed abstract chunk -> MERGE
    `(Paper)-[:HAS_CHUNK]->(Chunk)`) OR an `nct_id` key (ClinicalTrials
    brief-summary chunk, from `ingestion.clinicaltrials_client.
    chunk_brief_summaries` -> MERGE `(Trial)-[:HAS_CHUNK]->(Chunk)`) —
    mutually exclusive. The batch is split in Python into a `pmid` list and
    an `nct_id` list so each gets its own single batched `UNWIND`+`MERGE`
    query (still at most 2 `run_query` calls total, never one per row).

    Each dict may contain: chunk_id, pmid OR nct_id, text, embedding,
    source, chunk_index, char_start, char_end.
    """
    if not chunks:
        return

    paper_chunks = [c for c in chunks if c.get("pmid") is not None]
    trial_chunks = [c for c in chunks if c.get("nct_id") is not None]

    if paper_chunks:
        run_query(
            f"""
            UNWIND $batch AS row
            {_CHUNK_SET_CLAUSE}
            WITH c, row
            MATCH (p:Paper {{pmid: row.pmid}})
            MERGE (p)-[:HAS_CHUNK]->(c)
            """,
            batch=paper_chunks,
        )

    if trial_chunks:
        run_query(
            f"""
            UNWIND $batch AS row
            {_CHUNK_SET_CLAUSE}
            WITH c, row
            MATCH (tr:Trial {{nct_id: row.nct_id}})
            MERGE (tr)-[:HAS_CHUNK]->(c)
            """,
            batch=trial_chunks,
        )

    ingestion_stage_counter.add(len(chunks), {"module": "neo4j_loader", "function": "load_chunks"})


@traced("ingestion.neo4j_loader.load_entities")
def load_entities(entities: list[dict], label: str) -> None:
    """Generic MERGE-by-`name` loader for Disease/Target/Molecule nodes.

    SETs `display_name`, `aliases`, and (for `Molecule`) `chembl_id`/
    `drugbank_id`/`cas_number` when present in the dict. `label` must be one
    of Disease/Target/Molecule (matches the constraints in `rag/schema.py`).
    """
    if not entities:
        return
    if label not in _ENTITY_LABELS:
        raise ValueError(f"Unsupported entity label: {label!r}")

    if label == "Molecule":
        cypher = f"""
        UNWIND $batch AS row
        MERGE (n:{label} {{name: row.name}})
        SET n.display_name = row.display_name,
            n.aliases = row.aliases,
            n.chembl_id = coalesce(row.chembl_id, n.chembl_id),
            n.drugbank_id = coalesce(row.drugbank_id, n.drugbank_id),
            n.cas_number = coalesce(row.cas_number, n.cas_number)
        """
    else:
        cypher = f"""
        UNWIND $batch AS row
        MERGE (n:{label} {{name: row.name}})
        SET n.display_name = row.display_name,
            n.aliases = row.aliases
        """

    run_query(cypher, batch=entities)
    ingestion_stage_counter.add(len(entities), {"module": "neo4j_loader", "function": "load_entities"})


@traced("ingestion.neo4j_loader.load_mentions")
def load_mentions(mentions: list[dict]) -> None:
    """MERGE `(Chunk)-[:MENTIONS]->(entity)` plus the `(Paper)-[:MENTIONS]
    ->(entity)` rollup, matching by `chunk_id`/`pmid` + entity `label` +
    `name`.

    Each dict must contain: chunk_id, pmid, label (Disease/Target/Molecule),
    name.
    """
    if not mentions:
        return
    run_query(
        """
        UNWIND $batch AS row
        MATCH (c:Chunk {chunk_id: row.chunk_id})
        MATCH (p:Paper {pmid: row.pmid})
        MATCH (e {name: row.name})
        WHERE row.label IN labels(e)
        MERGE (c)-[:MENTIONS]->(e)
        MERGE (p)-[:MENTIONS]->(e)
        """,
        batch=mentions,
    )
    ingestion_stage_counter.add(len(mentions), {"module": "neo4j_loader", "function": "load_mentions"})


@traced("ingestion.neo4j_loader.load_associations")
def load_associations(associations: list[dict]) -> None:
    """MERGE `(Disease)-[:ASSOCIATED_WITH]->(Target)`, appending `source`
    into the relationship's `sources` list property (deduped, pure Cypher —
    no APOC) and optionally setting `opentargets_score`.

    Each dict must contain: disease_name, target_name, source. May contain:
    opentargets_score.
    """
    if not associations:
        return
    run_query(
        """
        UNWIND $batch AS row
        MATCH (d:Disease {name: row.disease_name})
        MATCH (t:Target {name: row.target_name})
        MERGE (d)-[r:ASSOCIATED_WITH]->(t)
        SET r.sources = CASE
                WHEN row.source IN coalesce(r.sources, []) THEN r.sources
                ELSE coalesce(r.sources, []) + row.source
            END,
            r.opentargets_score = coalesce(row.opentargets_score, r.opentargets_score)
        """,
        batch=associations,
    )
    ingestion_stage_counter.add(
        len(associations), {"module": "neo4j_loader", "function": "load_associations"}
    )


@traced("ingestion.neo4j_loader.load_targets_relation")
def load_targets_relation(relations: list[dict]) -> None:
    """MERGE `(Molecule)-[:TARGETS]->(Target)`, same `sources` append
    pattern as `load_associations`, optionally setting `opentargets_score`.

    Each dict must contain: molecule_name, target_name, source. May contain:
    opentargets_score.
    """
    if not relations:
        return
    run_query(
        """
        UNWIND $batch AS row
        MATCH (m:Molecule {name: row.molecule_name})
        MATCH (t:Target {name: row.target_name})
        MERGE (m)-[r:TARGETS]->(t)
        SET r.sources = CASE
                WHEN row.source IN coalesce(r.sources, []) THEN r.sources
                ELSE coalesce(r.sources, []) + row.source
            END,
            r.opentargets_score = coalesce(row.opentargets_score, r.opentargets_score)
        """,
        batch=relations,
    )
    ingestion_stage_counter.add(
        len(relations), {"module": "neo4j_loader", "function": "load_targets_relation"}
    )


@traced("ingestion.neo4j_loader.load_trials")
def load_trials(trials: list[dict]) -> None:
    """MERGE `Trial` nodes by `nct_id`, SET props; MERGE
    `(Trial)-[:STUDIES]->(Molecule)` and `(Trial)-[:FOR_CONDITION]->
    (Disease)` from keys on each trial dict.

    Each dict may contain: nct_id, title, phase, status, conditions,
    sponsor, molecule_name, disease_name.
    """
    if not trials:
        return
    run_query(
        """
        UNWIND $batch AS row
        MERGE (tr:Trial {nct_id: row.nct_id})
        SET tr.title = row.title,
            tr.phase = row.phase,
            tr.status = row.status,
            tr.conditions = row.conditions,
            tr.sponsor = row.sponsor
        WITH tr, row
        FOREACH (ignoreMe IN CASE WHEN row.molecule_name IS NOT NULL THEN [1] ELSE [] END |
            MERGE (m:Molecule {name: row.molecule_name})
            MERGE (tr)-[:STUDIES]->(m)
        )
        WITH tr, row
        FOREACH (ignoreMe IN CASE WHEN row.disease_name IS NOT NULL THEN [1] ELSE [] END |
            MERGE (d:Disease {name: row.disease_name})
            MERGE (tr)-[:FOR_CONDITION]->(d)
        )
        """,
        batch=trials,
    )
    ingestion_stage_counter.add(len(trials), {"module": "neo4j_loader", "function": "load_trials"})
