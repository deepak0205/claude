"""Thin wrapper around the `neo4j` Python driver.

Deliberately minimal for the POC: a single lazily-initialized module-level
driver built from `config.settings`, and one `run_query` helper that opens a
session, runs a query, and returns plain-dict records. No connection-pooling
tuning beyond driver defaults, no transaction functions/retries beyond what
the driver itself does.
"""

from neo4j import GraphDatabase

from config.settings import settings

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


def run_query(cypher: str, **params) -> list[dict]:
    """Run `cypher` with `params` in its own session and return the results
    as a list of plain dicts (one per record), closing the session
    afterwards."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, **params)
        return [record.data() for record in result]


def close_driver() -> None:
    """Close and clear the module-level driver, if one was created."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
