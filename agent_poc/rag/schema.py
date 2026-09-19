"""Idempotent Neo4j DDL for agent_poc.

`ensure_schema()` runs the constraints/indexes below via
`rag.neo4j_client.run_query`, every statement using `IF NOT EXISTS` so it's
safe to call on every `seed_demo.py` run.

Node uniqueness constraints: `Paper.pmid`, `Chunk.chunk_id`, `Disease.name`,
`Target.name`, `Molecule.name`, `Trial.nct_id`. Canonicalization for the
entity nodes (Disease/Target/Molecule) stays naive lowercase string
normalization, per the base plan's documented POC limitation — no ontology
lookup.

A native vector index (`chunk_embeddings`) on `Chunk.embedding`, 1024-dim
cosine similarity — matches Voyage AI's `voyage-3.5` embedding size. Neo4j
5.11+ supports this natively, no plugin required.

A fulltext index (`entity_fulltext`) over `Disease.name`, `Target.name`,
`Molecule.name`, supporting keyword lookups alongside vector search.

Non-unique indexes on `Molecule.chembl_id`, `Molecule.drugbank_id`,
`Molecule.cas_number` for fast lookup during DrugBank/ChEMBL enrichment
merges (Addendum 3) — these are not uniqueness constraints since a Molecule
node's identity key stays `name`.

Property-only conventions with no dedicated DDL (Neo4j has no schema for
plain properties, only for constraints/indexes):
- `Chunk.source`: `"pubmed"` or `"clinicaltrials"` — the two sources with
  narrative text worth chunking+embedding; ChEMBL/OpenTargets/DrugBank are
  structured-only and surfaced via graph traversal, not vector search.
- `ASSOCIATED_WITH` (Disease->Target) and `TARGETS` (Molecule->Target) edge
  properties: `sources: list[str]` (e.g. `["pubmed_extraction",
  "opentargets"]`) and an optional `opentargets_score: float`. One
  MERGE-friendly edge type per relationship, enriched by multiple sources,
  rather than a parallel edge type per source.
"""

from rag.neo4j_client import run_query

CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE p.pmid IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Target) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Molecule) REQUIRE m.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (tr:Trial) REQUIRE tr.nct_id IS UNIQUE",
]

VECTOR_INDEX = """
CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}
"""

FULLTEXT_INDEX = """
CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
FOR (n:Disease|Target|Molecule) ON EACH [n.name]
"""

LOOKUP_INDEXES = [
    "CREATE INDEX molecule_chembl_id IF NOT EXISTS FOR (m:Molecule) ON (m.chembl_id)",
    "CREATE INDEX molecule_drugbank_id IF NOT EXISTS FOR (m:Molecule) ON (m.drugbank_id)",
    "CREATE INDEX molecule_cas_number IF NOT EXISTS FOR (m:Molecule) ON (m.cas_number)",
]


def ensure_schema() -> None:
    """Create all constraints/indexes if they don't already exist. Safe to
    call repeatedly (every statement is `IF NOT EXISTS`)."""
    for statement in CONSTRAINTS:
        run_query(statement)

    run_query(VECTOR_INDEX)
    run_query(FULLTEXT_INDEX)

    for statement in LOOKUP_INDEXES:
        run_query(statement)
