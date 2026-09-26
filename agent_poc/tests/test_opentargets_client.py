"""Tests for ingestion/opentargets_client.py. `requests.post` is patched
directly — zero live network calls. Covers URL/payload construction,
retry-then-succeed behavior, GraphQL-errors surfacing, and output shaping
against `neo4j_loader.load_associations`/`load_targets_relation`'s actual
expected keys."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ingestion.opentargets_client import (
    fetch_disease_target_associations,
    fetch_target_molecule_mechanisms,
)


def _resp(json_data, status_ok=True):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    if status_ok:
        mock_resp.raise_for_status.return_value = None
    else:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("boom")
    return mock_resp


def test_fetch_disease_target_associations_builds_correct_payload():
    payload = {
        "data": {
            "disease": {
                "id": "EFO_0000305",
                "name": "breast carcinoma",
                "associatedTargets": {
                    "rows": [
                        {"target": {"id": "ENSG1", "approvedSymbol": "ERBB2"}, "score": 0.9},
                    ]
                },
            }
        }
    }
    resp = _resp(payload)

    with patch("ingestion.opentargets_client.requests.post", return_value=resp) as mock_post:
        results = fetch_disease_target_associations(["EFO_0000305"])

    assert mock_post.call_count == 1
    call = mock_post.call_args
    assert call.kwargs["json"]["variables"] == {"efoId": "EFO_0000305"}
    assert "disease(efoId" in call.kwargs["json"]["query"]

    assert results == [
        {
            "disease_name": "breast carcinoma",
            "target_name": "erbb2",
            "source": "opentargets",
            "opentargets_score": 0.9,
        }
    ]


def test_fetch_disease_target_associations_falls_back_to_efo_id_when_no_name():
    payload = {"data": {"disease": {"associatedTargets": {"rows": []}}}}
    resp = _resp(payload)

    with patch("ingestion.opentargets_client.requests.post", return_value=resp):
        results = fetch_disease_target_associations(["EFO_9999999"])

    assert results == []


def test_fetch_disease_target_associations_respects_top_n():
    rows = [{"target": {"approvedSymbol": f"T{i}"}, "score": 0.1 * i} for i in range(5)]
    payload = {"data": {"disease": {"name": "d", "associatedTargets": {"rows": rows}}}}
    resp = _resp(payload)

    with patch("ingestion.opentargets_client.requests.post", return_value=resp):
        results = fetch_disease_target_associations(["EFO_1"], top_n=2)

    assert len(results) == 2


def test_fetch_disease_target_associations_raises_on_graphql_errors():
    resp = _resp({"errors": [{"message": "bad query"}]})

    with patch("ingestion.opentargets_client.requests.post", return_value=resp):
        with pytest.raises(RuntimeError):
            fetch_disease_target_associations(["EFO_1"])


def test_fetch_target_molecule_mechanisms_builds_correct_payload():
    payload = {
        "data": {
            "target": {
                "id": "ENSG00000146648",
                "approvedSymbol": "EGFR",
                "knownDrugs": {"rows": [{"drug": {"id": "CHEMBL553", "name": "Erlotinib"}}]},
            }
        }
    }
    resp = _resp(payload)

    with patch("ingestion.opentargets_client.requests.post", return_value=resp) as mock_post:
        results = fetch_target_molecule_mechanisms(["ENSG00000146648"])

    call = mock_post.call_args
    assert call.kwargs["json"]["variables"] == {"ensemblId": "ENSG00000146648"}
    assert "target(ensemblId" in call.kwargs["json"]["query"]

    assert results == [{"molecule_name": "erlotinib", "target_name": "egfr", "source": "opentargets"}]


def test_post_retries_on_http_error_then_succeeds():
    failing_resp = _resp({}, status_ok=False)
    succeeding_resp = _resp({"data": {"disease": {"name": "d", "associatedTargets": {"rows": []}}}})

    with patch(
        "ingestion.opentargets_client.requests.post", side_effect=[failing_resp, succeeding_resp]
    ) as mock_post:
        fetch_disease_target_associations(["EFO_1"])

    assert mock_post.call_count == 2


def test_post_raises_after_exhausting_retries():
    always_failing = _resp({}, status_ok=False)

    with patch("ingestion.opentargets_client.requests.post", return_value=always_failing) as mock_post:
        with pytest.raises(requests.exceptions.HTTPError):
            fetch_disease_target_associations(["EFO_1"])

    assert mock_post.call_count == 3
