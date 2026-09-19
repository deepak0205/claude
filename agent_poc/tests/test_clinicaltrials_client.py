"""Tests for ingestion/clinicaltrials_client.py. `requests.get` is patched
directly — zero live network calls. Covers URL/params construction, retry-
then-succeed behavior, and output shaping against `neo4j_loader.load_trials`'s
actual expected keys."""

from unittest.mock import MagicMock, patch

import requests

from ingestion.clinicaltrials_client import chunk_brief_summaries, fetch_trials, to_trial_records


def _resp(json_data, status_ok=True):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    if status_ok:
        mock_resp.raise_for_status.return_value = None
    else:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("boom")
    return mock_resp


_STUDY = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT001", "briefTitle": "A trial of erlotinib"},
        "statusModule": {"overallStatus": "RECRUITING"},
        "designModule": {"phases": ["PHASE2"]},
        "conditionsModule": {"conditions": ["Lung Cancer"]},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Acme Pharma"}},
        "descriptionModule": {"briefSummary": "A study of erlotinib in lung cancer patients."},
    }
}


def test_fetch_trials_builds_correct_url_and_params():
    resp = _resp({"studies": [_STUDY]})

    with patch("ingestion.clinicaltrials_client.requests.get", return_value=resp) as mock_get:
        trials = fetch_trials("lung cancer", "erlotinib", max_results=50)

    assert mock_get.call_count == 1
    call = mock_get.call_args
    assert call.args[0].endswith("/studies")
    assert call.kwargs["params"] == {
        "query.cond": "lung cancer",
        "pageSize": 50,
        "format": "json",
        "query.intr": "erlotinib",
    }

    assert trials == [
        {
            "nct_id": "NCT001",
            "title": "A trial of erlotinib",
            "phase": "PHASE2",
            "status": "RECRUITING",
            "conditions": ["Lung Cancer"],
            "sponsor": "Acme Pharma",
            "brief_summary": "A study of erlotinib in lung cancer patients.",
        }
    ]


def test_fetch_trials_omits_intervention_param_when_none():
    resp = _resp({"studies": []})

    with patch("ingestion.clinicaltrials_client.requests.get", return_value=resp) as mock_get:
        fetch_trials("lung cancer", None, max_results=10)

    assert "query.intr" not in mock_get.call_args.kwargs["params"]


def test_fetch_trials_caps_page_size_at_1000():
    resp = _resp({"studies": []})

    with patch("ingestion.clinicaltrials_client.requests.get", return_value=resp) as mock_get:
        fetch_trials("lung cancer", None, max_results=5000)

    assert mock_get.call_args.kwargs["params"]["pageSize"] == 1000


def test_fetch_trials_skips_studies_with_no_nct_id():
    broken_study = {"protocolSection": {"identificationModule": {}}}
    resp = _resp({"studies": [broken_study, _STUDY]})

    with patch("ingestion.clinicaltrials_client.requests.get", return_value=resp):
        trials = fetch_trials("lung cancer", None)

    assert len(trials) == 1
    assert trials[0]["nct_id"] == "NCT001"


def test_get_retries_on_http_error_then_succeeds():
    failing_resp = _resp({}, status_ok=False)
    succeeding_resp = _resp({"studies": []})

    with patch(
        "ingestion.clinicaltrials_client.requests.get", side_effect=[failing_resp, succeeding_resp]
    ) as mock_get:
        fetch_trials("lung cancer", None)

    assert mock_get.call_count == 2


def test_get_raises_after_exhausting_retries():
    always_failing = _resp({}, status_ok=False)

    with patch("ingestion.clinicaltrials_client.requests.get", return_value=always_failing) as mock_get:
        import pytest

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_trials("lung cancer", None)

    assert mock_get.call_count == 3


def test_to_trial_records_shapes_for_load_trials():
    trials = [
        {
            "nct_id": "NCT001",
            "title": "A trial of erlotinib",
            "phase": "PHASE2",
            "status": "RECRUITING",
            "conditions": ["Lung Cancer"],
            "sponsor": "Acme Pharma",
            "brief_summary": "...",
        }
    ]

    records = to_trial_records(trials, molecule_name="Erlotinib", disease_name="Lung Cancer")

    assert records == [
        {
            "nct_id": "NCT001",
            "title": "A trial of erlotinib",
            "phase": "PHASE2",
            "status": "RECRUITING",
            "conditions": ["Lung Cancer"],
            "sponsor": "Acme Pharma",
            "molecule_name": "erlotinib",
            "disease_name": "lung cancer",
        }
    ]


def test_to_trial_records_omits_molecule_and_disease_when_not_given():
    trials = [
        {
            "nct_id": "NCT001",
            "title": "t",
            "phase": None,
            "status": "RECRUITING",
            "conditions": [],
            "sponsor": None,
            "brief_summary": "",
        }
    ]

    records = to_trial_records(trials)

    assert "molecule_name" not in records[0]
    assert "disease_name" not in records[0]


def test_chunk_brief_summaries_shapes_one_chunk_per_trial():
    trials = [
        {"nct_id": "NCT001", "brief_summary": "A study of erlotinib."},
        {"nct_id": "NCT002", "brief_summary": ""},
    ]

    chunks = chunk_brief_summaries(trials)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["chunk_id"] == "NCT001_chunk_0"
    assert chunk["nct_id"] == "NCT001"
    assert chunk["text"] == "A study of erlotinib."
    assert chunk["chunk_index"] == 0
    assert chunk["char_start"] == 0
    assert chunk["char_end"] == len("A study of erlotinib.")
    assert chunk["source"] == "clinicaltrials"
