"""OpenTargets GraphQL API client (`{OPENTARGETS_GRAPHQL_URL}`, no API key
required).

POST's simplified GraphQL queries for disease-target association scores and
target-molecule (known-drug) mechanism data, for entities already loaded
into the graph from PubMed/ChEMBL. Per Addendum 3's per-source role table,
OpenTargets *enriches* existing `(Disease)-[:ASSOCIATED_WITH]->(Target)` /
`(Molecule)-[:TARGETS]->(Target)` edges with a `score`/`sources` property
rather than creating new node types.

**Documented POC simplifications** (the full OpenTargets GraphQL schema is
extensive; this is intentionally not production-grade coverage):
- `fetch_disease_target_associations` takes each input string as a
  ready-to-use EFO ID (e.g. `"EFO_0000305"`) and passes it straight to the
  `disease(efoId: ...)` query root. A real integration would first resolve
  a free-text disease name to its EFO ID via OpenTargets' own search
  endpoint; that resolution step is out of scope here.
- `fetch_target_molecule_mechanisms` similarly takes each input string as a
  ready-to-use Ensembl gene ID and passes it to `target(ensemblId: ...)`.
  Resolving a gene symbol (e.g. `"EGFR"`) to its Ensembl ID via search is
  likewise out of scope.
- Only the first `top_n` rows of each association/known-drugs list are
  read; OpenTargets paginates these lists for large results.
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

_DISEASE_TARGET_ASSOCIATIONS_QUERY = """
query DiseaseAssociatedTargets($efoId: String!) {
  disease(efoId: $efoId) {
    id
    name
    associatedTargets {
      rows {
        target { id approvedSymbol }
        score
      }
    }
  }
}
"""

_TARGET_KNOWN_DRUGS_QUERY = """
query TargetKnownDrugs($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    knownDrugs {
      rows {
        drug { id name }
      }
    }
  }
}
"""


@_retry_on_request_error
def _post_graphql(query: str, variables: dict) -> dict:
    """POST a GraphQL `query`/`variables` payload, retrying on any
    `requests` exception up to 3 attempts. Raises `RuntimeError` if the
    GraphQL response itself reports `errors` (a 200 OK with a GraphQL-level
    error is not a `requests` exception, so it wouldn't otherwise retry or
    surface)."""
    response = requests.post(
        settings.OPENTARGETS_GRAPHQL_URL,
        json={"query": query, "variables": variables},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"OpenTargets GraphQL errors: {payload['errors']}")
    return payload.get("data") or {}


def fetch_disease_target_associations(disease_efo_ids_or_names: list[str], top_n: int = 25) -> list[dict]:
    """For each EFO ID, fetch its top `top_n` associated targets and return
    dicts shaped for `neo4j_loader.load_associations` (`disease_name,
    target_name, source, opentargets_score`)."""
    results: list[dict] = []
    for efo_id in disease_efo_ids_or_names:
        data = _post_graphql(_DISEASE_TARGET_ASSOCIATIONS_QUERY, {"efoId": efo_id})
        disease = data.get("disease") or {}
        disease_name = (disease.get("name") or efo_id).lower()
        rows = ((disease.get("associatedTargets") or {}).get("rows")) or []
        for row in rows[:top_n]:
            target = row.get("target") or {}
            symbol = target.get("approvedSymbol")
            if not symbol:
                continue
            results.append(
                {
                    "disease_name": disease_name,
                    "target_name": symbol.lower(),
                    "source": "opentargets",
                    "opentargets_score": row.get("score"),
                }
            )
    return results


def fetch_target_molecule_mechanisms(target_names: list[str], top_n: int = 25) -> list[dict]:
    """For each Ensembl target ID, fetch its top `top_n` known drugs and
    return dicts shaped for `neo4j_loader.load_targets_relation`
    (`molecule_name, target_name, source`)."""
    results: list[dict] = []
    for ensembl_id in target_names:
        data = _post_graphql(_TARGET_KNOWN_DRUGS_QUERY, {"ensemblId": ensembl_id})
        target = data.get("target") or {}
        symbol = (target.get("approvedSymbol") or ensembl_id).lower()
        rows = ((target.get("knownDrugs") or {}).get("rows")) or []
        for row in rows[:top_n]:
            drug = row.get("drug") or {}
            drug_name = drug.get("name")
            if not drug_name:
                continue
            results.append(
                {
                    "molecule_name": drug_name.lower(),
                    "target_name": symbol,
                    "source": "opentargets",
                }
            )
    return results
