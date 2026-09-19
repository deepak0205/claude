"""Sanity-check counts across every node/relationship type in the graph.

No arguments — connects using whatever `NEO4J_URI/USER/PASSWORD` are set in
the environment/`.env` (via `config.settings`) and prints a table of counts
to stdout. Intended as the manual post-`seed_demo.py` verification step
(per the base plan's Phase 0-2 "done when" criteria) — not covered by the
automated test suite, which mocks `rag.neo4j_client.run_query` everywhere
and never touches a live database.
"""

import os
import sys

# Standalone script (no `scripts/__init__.py`) — see seed_demo.py's matching
# comment for why the repo root needs inserting onto `sys.path` here.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.neo4j_client import run_query

NODE_LABELS = ["Paper", "Chunk", "Disease", "Target", "Molecule", "Trial"]

RELATIONSHIP_TYPES = [
    "HAS_CHUNK",
    "MENTIONS",
    "ASSOCIATED_WITH",
    "TARGETS",
    "STUDIES",
    "FOR_CONDITION",
]


def count_nodes(label: str) -> int:
    rows = run_query(f"MATCH (n:{label}) RETURN count(n) AS count")
    return rows[0]["count"] if rows else 0


def count_relationships(rel_type: str) -> int:
    rows = run_query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count")
    return rows[0]["count"] if rows else 0


def main() -> None:
    print("Node counts:")
    node_counts = {}
    for label in NODE_LABELS:
        count = count_nodes(label)
        node_counts[label] = count
        print(f"  {label:<10} {count}")

    print("\nRelationship counts:")
    rel_counts = {}
    for rel_type in RELATIONSHIP_TYPES:
        count = count_relationships(rel_type)
        rel_counts[rel_type] = count
        print(f"  {rel_type:<16} {count}")

    print("\nSanity checks:")
    if node_counts["Paper"] == 0:
        print("  [WARN] no Paper nodes — has seed_demo.py been run?")
    if node_counts["Chunk"] == 0:
        print("  [WARN] no Chunk nodes — vector search will return nothing")
    if rel_counts["HAS_CHUNK"] == 0 and node_counts["Chunk"] > 0:
        print("  [WARN] Chunk nodes exist but no HAS_CHUNK relationships — chunks are orphaned")
    if node_counts["Molecule"] == 0:
        print("  [INFO] no Molecule nodes yet (ChEMBL/DrugBank/ClinicalTrials stages may not have run)")
    if node_counts["Trial"] == 0:
        print("  [INFO] no Trial nodes yet (ClinicalTrials.gov stage may not have run)")
    if all(v > 0 for v in node_counts.values()) and all(v > 0 for v in rel_counts.values()):
        print("  [OK] every node/relationship type has at least one instance")


if __name__ == "__main__":
    main()
