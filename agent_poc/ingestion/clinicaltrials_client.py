"""ClinicalTrials.gov API v2 client (`{CLINICALTRIALS_BASE_URL}`, no API key
required).

Queries `/studies` for a condition (+ optional intervention), shapes the
results for `ingestion.neo4j_loader.load_trials`, and chunks each trial's
brief summary for embedding — structured trial metadata plus one piece of
narrative text per trial (per Addendum 3's per-source role table, trials are
one of only two sources, alongside PubMed, with text worth chunking and
embedding).
"""

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.settings import settings
from config.telemetry import ingestion_stage_counter, traced

_retry_on_request_error = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)


@_retry_on_request_error
def _get(url: str, params: dict) -> dict:
    """GET `url` with `params`, retrying on any `requests` exception up to
    3 attempts."""
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


@traced("ingestion.clinicaltrials_client.fetch_trials")
def fetch_trials(condition: str, intervention: str | None = None, max_results: int = 50) -> list[dict]:
    """Query `/studies?query.cond=<condition>&query.intr=<intervention>` and
    return a flat list of trial dicts: `nct_id, title, phase, status,
    conditions, sponsor, brief_summary`.

    Single-page fetch only (`pageSize` capped at `max_results`, capped at
    the API's 1000 max) — a production integration would follow the
    response's `nextPageToken` for more results; out of scope for this POC.
    """
    params: dict = {"query.cond": condition, "pageSize": min(max_results, 1000), "format": "json"}
    if intervention:
        params["query.intr"] = intervention

    data = _get(f"{settings.CLINICALTRIALS_BASE_URL}/studies", params)
    studies = data.get("studies") or []

    trials: list[dict] = []
    for study in studies[:max_results]:
        protocol = study.get("protocolSection") or {}
        ident = protocol.get("identificationModule") or {}
        nct_id = ident.get("nctId")
        if not nct_id:
            continue

        status_mod = protocol.get("statusModule") or {}
        design_mod = protocol.get("designModule") or {}
        cond_mod = protocol.get("conditionsModule") or {}
        sponsor_mod = protocol.get("sponsorCollaboratorsModule") or {}
        desc_mod = protocol.get("descriptionModule") or {}

        phases = design_mod.get("phases") or []
        trials.append(
            {
                "nct_id": nct_id,
                "title": ident.get("briefTitle"),
                "phase": ",".join(phases) if phases else None,
                "status": status_mod.get("overallStatus"),
                "conditions": cond_mod.get("conditions") or [],
                "sponsor": (sponsor_mod.get("leadSponsor") or {}).get("name"),
                "brief_summary": desc_mod.get("briefSummary") or "",
            }
        )
    ingestion_stage_counter.add(
        len(trials), {"module": "clinicaltrials_client", "function": "fetch_trials"}
    )
    return trials


@traced("ingestion.clinicaltrials_client.to_trial_records")
def to_trial_records(
    trials: list[dict], molecule_name: str | None = None, disease_name: str | None = None
) -> list[dict]:
    """Shape `fetch_trials`'s output for `neo4j_loader.load_trials`
    (`nct_id, title, phase, status, conditions, sponsor`, plus optional
    `molecule_name`/`disease_name` to drive that loader's
    `(Trial)-[:STUDIES]->(Molecule)` / `(Trial)-[:FOR_CONDITION]->(Disease)`
    MERGE).

    `molecule_name`/`disease_name` are applied to every trial in the batch
    since they were the query's own `intervention`/`condition` filters —
    the same values used to fetch this batch via `fetch_trials`.
    """
    records = []
    for trial in trials:
        record = {
            "nct_id": trial["nct_id"],
            "title": trial.get("title"),
            "phase": trial.get("phase"),
            "status": trial.get("status"),
            "conditions": trial.get("conditions") or [],
            "sponsor": trial.get("sponsor"),
        }
        if molecule_name:
            record["molecule_name"] = molecule_name.lower()
        if disease_name:
            record["disease_name"] = disease_name.lower()
        records.append(record)
    return records


@traced("ingestion.clinicaltrials_client.chunk_brief_summaries")
def chunk_brief_summaries(trials: list[dict]) -> list[dict]:
    """One chunk per trial's `brief_summary`, shaped to match
    `ingestion.chunking.py`'s documented chunk dict shape: `{chunk_id, text,
    chunk_index, char_start, char_end, source}`.

    NOTE (documented assumption): `ingestion/chunking.py` may not exist yet
    at the time this module is written (a parallel subagent owns it per
    Addendum 3's delegation split) — this function does not import it, it
    only matches the plan's documented output shape so `embedding.py` /
    `neo4j_loader.load_chunks` can consume it the same way as PubMed
    chunks. Each dict also carries `nct_id` (not one of `load_chunks`'s
    referenced keys, which currently only wires `(Paper)-[:HAS_CHUNK]->
    (Chunk)` via a `pmid` key) so a future loader extension can wire
    `(Trial)-[:HAS_CHUNK]->(Chunk)` — trials have no `pmid`, so today's
    `load_chunks` cannot link these chunks to their Trial node without that
    extension; flagged here rather than silently guessed at.
    """
    chunks = []
    for trial in trials:
        text = trial.get("brief_summary") or ""
        if not text:
            continue
        chunks.append(
            {
                "chunk_id": f"{trial['nct_id']}_chunk_0",
                "nct_id": trial["nct_id"],
                "text": text,
                "chunk_index": 0,
                "char_start": 0,
                "char_end": len(text),
                "source": "clinicaltrials",
            }
        )
    ingestion_stage_counter.add(
        len(chunks), {"module": "clinicaltrials_client", "function": "chunk_brief_summaries"}
    )
    return chunks
