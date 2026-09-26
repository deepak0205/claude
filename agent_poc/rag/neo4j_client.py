"""Thin wrapper around the `neo4j` Python driver.

Deliberately minimal for the POC: a single lazily-initialized module-level
driver built from `config.settings`, and one `run_query` helper that opens a
session, runs a query, and returns plain-dict records. No connection-pooling
tuning beyond driver defaults, no transaction functions/retries beyond what
the driver itself does.
"""

import time

from neo4j import GraphDatabase
from opentelemetry import trace

from config.settings import settings
from config.telemetry import neo4j_query_duration_histogram, traced

_driver = None


def get_driver():
    """Return the module-level driver, creating it on first use."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


@traced("neo4j.run_query")
def run_query(cypher: str, **params) -> list[dict]:
    """Run `cypher` with `params` in its own session and return the results
    as a list of plain dicts (one per record), closing the session
    afterwards.

    Span attributes are deliberately redacted: only the cypher text and the
    *names* of the passed param keys are recorded (never param values, and
    never the `embedding` key specifically) — `hybrid_search`'s vector query
    passes a 1024-float `embedding` param that would otherwise bloat every
    span.
    """
    span = trace.get_current_span()
    span.set_attribute("neo4j.cypher", cypher)
    span.set_attribute("neo4j.param_keys", sorted(k for k in params if k != "embedding"))

    driver = get_driver()
    start = time.perf_counter()
    with driver.session() as session:
        result = session.run(cypher, **params)
        records = [record.data() for record in result]
    neo4j_query_duration_histogram.record(time.perf_counter() - start)
    return records


def close_driver() -> None:
    """Close and clear the module-level driver, if one was created."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
