"""Hybrid GraphRAG + VectorRAG retriever — the single function every real
sub-agent (Literature/Disease/Target/Molecule/Clinical Trial) calls via
`agents.tools.RetrievalToolProvider`.

`hybrid_search(query, entity_bias, top_k, candidate_pool)`:
1. Embed `query` via `ingestion.embedding.embed_query` (`input_type="query"`).
2. Vector search: `db.index.vector.queryNodes('chunk_embeddings', ...)`,
   joined back to the owning `Paper` (`HAS_CHUNK`) or `Trial` (`HAS_CHUNK`,
   per the Fix-1 extension to `ingestion.neo4j_loader.load_chunks`) to get
   title/journal/year or trial title/phase.
3. Entity-bias reweighting: boosts (never filters) candidates connected to
   the entity label matching `entity_bias`. `None`/`"literature"` = no
   reweighting (broadest coverage, matches the base plan).
4. Graph expansion: one hop from the top candidates to sibling `Paper`s
   sharing a mentioned entity (existing base-plan behavior), *and* to
   sibling `Trial`s sharing a `Molecule`/`Disease` entity (Addendum 3
   extension) — surfaces evidence the vector search didn't directly match.
5. Combine, dedupe by identifier (`pmid` for papers, `nct_id` for trials —
   both stored in `Evidence.pmid`, since `Evidence` has no separate
   trial-id field; a documented POC stand-in per Addendum 3), sort by
   (boosted) similarity score descending, truncate to `top_k`.

Trial-derived `Evidence.year` is `0` (trials expose no single publication
year the way `Paper.pub_date` does) — another documented POC limitation.

Every Cypher block below carries a leading `// marker` comment purely so
`tests/test_retriever.py` can dispatch a mocked `run_query` by query
identity without depending on exact whitespace/formatting.
"""

from ingestion.embedding import embed_query
from rag.neo4j_client import run_query
from agents.state import Evidence

_BIAS_LABELS = {
    "disease": "Disease",
    "target": "Target",
    "molecule": "Molecule",
}

_BOOST_FACTOR = 1.2

# Heuristic score assigned to graph-expansion-only hits (not directly
# matched by the vector search, so they have no native similarity score).
# Deliberately below a typical cosine-similarity vector hit so expansion
# results supplement rather than displace directly-matched evidence.
_EXPANSION_SCORE = 0.35

# Only expand outward from the top-scoring candidates, not the whole pool.
_EXPANSION_SEED_COUNT = 5

_VECTOR_SEARCH_QUERY = """
// vector_search
CALL db.index.vector.queryNodes('chunk_embeddings', $candidate_pool, $embedding)
YIELD node AS chunk, score
OPTIONAL MATCH (p:Paper)-[:HAS_CHUNK]->(chunk)
OPTIONAL MATCH (tr:Trial)-[:HAS_CHUNK]->(chunk)
RETURN chunk.chunk_id AS chunk_id, chunk.text AS snippet, score,
       p.pmid AS pmid, p.title AS title, p.journal AS journal, p.pub_date AS pub_date,
       tr.nct_id AS nct_id, tr.title AS trial_title, tr.phase AS phase
"""

_BIAS_BOOST_QUERY_TEMPLATE = """
// bias_boost
UNWIND $pmids AS pmid
MATCH (p:Paper {{pmid: pmid}})-[:MENTIONS]->(e:{label})
RETURN DISTINCT pmid AS pmid
"""

_EXPAND_PAPER_TO_PAPERS_QUERY = """
// expand_paper_to_papers
UNWIND $seed_pmids AS seed_pmid
MATCH (src:Paper {pmid: seed_pmid})-[:MENTIONS]->(e)<-[:MENTIONS]-(p2:Paper)
WHERE p2.pmid <> seed_pmid
OPTIONAL MATCH (p2)-[:HAS_CHUNK]->(c2:Chunk)
WITH p2, c2
ORDER BY c2.chunk_index ASC
WITH p2, collect(c2.text)[0] AS snippet
RETURN DISTINCT p2.pmid AS pmid, p2.title AS title, p2.journal AS journal,
       p2.pub_date AS pub_date, snippet AS snippet
"""

_EXPAND_PAPER_TO_TRIALS_QUERY = """
// expand_paper_to_trials
UNWIND $seed_pmids AS seed_pmid
MATCH (src:Paper {pmid: seed_pmid})-[:MENTIONS]->(e)
MATCH (tr:Trial)-[:STUDIES|FOR_CONDITION]->(e)
RETURN DISTINCT tr.nct_id AS nct_id, tr.title AS title, tr.phase AS phase
"""

_EXPAND_TRIAL_TO_PAPERS_QUERY = """
// expand_trial_to_papers
UNWIND $seed_nct_ids AS seed_nct_id
MATCH (src:Trial {nct_id: seed_nct_id})-[:STUDIES|FOR_CONDITION]->(e)
MATCH (p2:Paper)-[:MENTIONS]->(e)
OPTIONAL MATCH (p2)-[:HAS_CHUNK]->(c2:Chunk)
WITH p2, c2
ORDER BY c2.chunk_index ASC
WITH p2, collect(c2.text)[0] AS snippet
RETURN DISTINCT p2.pmid AS pmid, p2.title AS title, p2.journal AS journal,
       p2.pub_date AS pub_date, snippet AS snippet
"""


def hybrid_search(
    query: str,
    entity_bias: str | None,
    top_k: int = 5,
    candidate_pool: int = 20,
) -> list[Evidence]:
    """Run the hybrid vector + graph-expansion retrieval described in the
    module docstring and return up to `top_k` `Evidence` objects, sorted by
    (boosted) similarity score descending."""
    embedding = embed_query(query)

    candidates = _vector_search(embedding, candidate_pool)
    if not candidates:
        return []

    _apply_entity_bias(candidates, entity_bias)

    seeds = sorted(candidates, key=lambda r: r["score"], reverse=True)[:_EXPANSION_SEED_COUNT]
    expanded = _graph_expand(seeds)

    combined = _dedupe(candidates + expanded)
    combined.sort(key=lambda r: r["score"], reverse=True)

    return [_row_to_evidence(row) for row in combined[:top_k]]


def _vector_search(embedding: list[float], candidate_pool: int) -> list[dict]:
    rows = run_query(_VECTOR_SEARCH_QUERY, candidate_pool=candidate_pool, embedding=embedding)
    results = []
    for row in rows:
        if not row.get("pmid") and not row.get("nct_id"):
            continue
        results.append(_normalize_vector_row(row))
    return results


def _normalize_vector_row(row: dict) -> dict:
    is_trial = row.get("nct_id") is not None
    if is_trial:
        return {
            "id": row["nct_id"],
            "pmid": row["nct_id"],
            "title": row.get("trial_title") or "",
            "journal": f"ClinicalTrials.gov ({row.get('phase') or 'phase unknown'})",
            "year": 0,
            "snippet": row.get("snippet") or "",
            "score": float(row.get("score") or 0.0),
            "is_trial": True,
            "entities": [],
            "entity_path": [],
        }
    return {
        "id": row["pmid"],
        "pmid": row["pmid"],
        "title": row.get("title") or "",
        "journal": row.get("journal") or "",
        "year": _parse_year(row.get("pub_date")) or 0,
        "snippet": row.get("snippet") or "",
        "score": float(row.get("score") or 0.0),
        "is_trial": False,
        "entities": [],
        "entity_path": [],
    }


def _apply_entity_bias(rows: list[dict], entity_bias: str | None) -> None:
    """Boost (never filter) candidates matching `entity_bias`, in place."""
    if not entity_bias or entity_bias == "literature":
        return

    if entity_bias == "clinical_trial":
        # "Trial involvement" bias: a candidate that *is* a Trial (matched
        # directly by the vector search against a clinicaltrials-sourced
        # chunk) counts as involved: no extra query needed.
        for row in rows:
            if row["is_trial"]:
                row["score"] *= _BOOST_FACTOR
        return

    label = _BIAS_LABELS.get(entity_bias)
    if not label:
        return

    pmids = [row["pmid"] for row in rows if not row["is_trial"]]
    if not pmids:
        return

    boosted_rows = run_query(_BIAS_BOOST_QUERY_TEMPLATE.format(label=label), pmids=pmids)
    boosted_pmids = {r["pmid"] for r in boosted_rows}
    for row in rows:
        if not row["is_trial"] and row["pmid"] in boosted_pmids:
            row["score"] *= _BOOST_FACTOR


def _graph_expand(seed_rows: list[dict]) -> list[dict]:
    if not seed_rows:
        return []

    seed_pmids = [row["pmid"] for row in seed_rows if not row["is_trial"]]
    seed_nct_ids = [row["pmid"] for row in seed_rows if row["is_trial"]]

    expanded: list[dict] = []

    if seed_pmids:
        for row in run_query(_EXPAND_PAPER_TO_PAPERS_QUERY, seed_pmids=seed_pmids):
            expanded.append(_expansion_paper_row(row))
        for row in run_query(_EXPAND_PAPER_TO_TRIALS_QUERY, seed_pmids=seed_pmids):
            expanded.append(_expansion_trial_row(row))

    if seed_nct_ids:
        for row in run_query(_EXPAND_TRIAL_TO_PAPERS_QUERY, seed_nct_ids=seed_nct_ids):
            expanded.append(_expansion_paper_row(row))

    return expanded


def _expansion_paper_row(row: dict) -> dict:
    return {
        "id": row["pmid"],
        "pmid": row["pmid"],
        "title": row.get("title") or "",
        "journal": row.get("journal") or "",
        "year": _parse_year(row.get("pub_date")) or 0,
        "snippet": row.get("snippet") or "",
        "score": _EXPANSION_SCORE,
        "is_trial": False,
        "entities": [],
        "entity_path": ["graph_expansion"],
    }


def _expansion_trial_row(row: dict) -> dict:
    return {
        "id": row["nct_id"],
        "pmid": row["nct_id"],
        "title": row.get("title") or "",
        "journal": f"ClinicalTrials.gov ({row.get('phase') or 'phase unknown'})",
        "year": 0,
        "snippet": "",
        "score": _EXPANSION_SCORE,
        "is_trial": True,
        "entities": [],
        "entity_path": ["graph_expansion"],
    }


def _dedupe(rows: list[dict]) -> list[dict]:
    """Dedupe by `id` (pmid or nct_id), keeping the highest-scoring copy of
    each (a directly-matched vector hit should win over an expansion-only
    duplicate of the same paper/trial)."""
    best: dict[str, dict] = {}
    for row in rows:
        key = row["id"]
        if key not in best or row["score"] > best[key]["score"]:
            best[key] = row
    return list(best.values())


def _parse_year(pub_date: str | None) -> int | None:
    if not pub_date:
        return None
    for token in str(pub_date).split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def _row_to_evidence(row: dict) -> Evidence:
    return Evidence(
        pmid=row["pmid"],
        title=row.get("title") or "",
        journal=row.get("journal") or "",
        year=row.get("year") or 0,
        snippet=row.get("snippet") or "",
        entities=row.get("entities") or [],
        entity_path=row.get("entity_path") or [],
        similarity_score=row.get("score") or 0.0,
    )
