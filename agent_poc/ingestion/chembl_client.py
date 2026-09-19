"""ChEMBL REST API client (`{CHEMBL_BASE_URL}`, no API key required).

Queries ChEMBL's public REST API for molecule + target-bioactivity records
against a list of target names, and shapes the results for
`ingestion.neo4j_loader.load_entities(..., label="Molecule")` and
`ingestion.neo4j_loader.load_targets_relation`. Pure structured mapping — no
LLM calls, matching ChEMBL's already-structured data (per Addendum 3's
per-source role table).

Two-step lookup, mirroring ChEMBL's own API shape:
1. `/target/search?q=<name>` resolves a free-text target name (e.g. "EGFR")
   to a ChEMBL target ID.
2. `/activity?target_chembl_id=<id>` lists bioactivity records against that
   target; each activity references a `molecule_chembl_id` we map into a
   Molecule node.

POC simplification: only the first search hit is used to resolve a target
name to a ChEMBL ID (no disambiguation UI), and only the first
`limit_per_target` activities per target are fetched (ChEMBL paginates
heavily; a production integration would follow `page_meta.next`).
"""

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.settings import settings

_retry_on_request_error = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)


@_retry_on_request_error
def _get(url: str, params: dict) -> dict:
    """GET `url` with `params`, retrying on any `requests` exception
    (network error or raised HTTP status) up to 3 attempts."""
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _resolve_target_chembl_id(target_name: str) -> str | None:
    """Resolve a free-text target name to a ChEMBL target ID via
    `/target/search`. Returns `None` if there are no hits."""
    data = _get(f"{settings.CHEMBL_BASE_URL}/target/search", {"q": target_name, "format": "json"})
    hits = data.get("targets") or []
    if not hits:
        return None
    return hits[0].get("target_chembl_id")


def _fetch_activities(target_chembl_id: str, limit: int) -> list[dict]:
    """List bioactivity records against `target_chembl_id` via `/activity`."""
    data = _get(
        f"{settings.CHEMBL_BASE_URL}/activity",
        {"target_chembl_id": target_chembl_id, "limit": limit, "format": "json"},
    )
    return data.get("activities") or []


def fetch_molecules_for_targets(target_names: list[str], limit_per_target: int = 50) -> list[dict]:
    """For each target name, resolve its ChEMBL target ID then fetch
    associated bioactivity records, returning a deduped flat list of
    molecule dicts.

    Each dict is shaped for `neo4j_loader.load_entities(..., label=
    "Molecule")` (`name`, `display_name`, `aliases`, `chembl_id`) plus an
    extra `target_name` key (ignored by `load_entities`'s Cypher, which only
    references the keys above) used internally by `to_target_relations`.
    """
    molecules_by_name: dict[str, dict] = {}
    for target_name in target_names:
        target_chembl_id = _resolve_target_chembl_id(target_name)
        if not target_chembl_id:
            continue
        for activity in _fetch_activities(target_chembl_id, limit=limit_per_target):
            molecule_chembl_id = activity.get("molecule_chembl_id")
            if not molecule_chembl_id:
                continue
            pref_name = activity.get("molecule_pref_name") or molecule_chembl_id
            name = pref_name.lower()
            molecules_by_name.setdefault(
                name,
                {
                    "name": name,
                    "display_name": pref_name,
                    "aliases": [],
                    "chembl_id": molecule_chembl_id,
                    "target_name": target_name.lower(),
                },
            )
    return list(molecules_by_name.values())


def to_target_relations(molecules: list[dict]) -> list[dict]:
    """Shape `fetch_molecules_for_targets`'s output for
    `neo4j_loader.load_targets_relation` (`molecule_name`, `target_name`,
    `source`)."""
    return [
        {"molecule_name": molecule["name"], "target_name": molecule["target_name"], "source": "chembl"}
        for molecule in molecules
        if molecule.get("target_name")
    ]
