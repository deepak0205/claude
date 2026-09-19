"""Tests for ingestion/chembl_client.py. `requests.get` is patched directly
— zero live network calls. Covers URL/params construction, retry-then-
succeed behavior, and output shaping against `neo4j_loader.load_entities`/
`load_targets_relation`'s actual expected keys."""

from unittest.mock import MagicMock, patch

import requests

from ingestion.chembl_client import fetch_molecules_for_targets, to_target_relations


def _resp(json_data, status_ok=True):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_data
    if status_ok:
        mock_resp.raise_for_status.return_value = None
    else:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("boom")
    return mock_resp


def test_fetch_molecules_for_targets_builds_correct_urls_and_params():
    target_search_resp = _resp({"targets": [{"target_chembl_id": "CHEMBL203"}]})
    activity_resp = _resp(
        {
            "activities": [
                {"molecule_chembl_id": "CHEMBL553", "molecule_pref_name": "Erlotinib"},
            ]
        }
    )

    with patch("ingestion.chembl_client.requests.get", side_effect=[target_search_resp, activity_resp]) as mock_get:
        molecules = fetch_molecules_for_targets(["EGFR"], limit_per_target=10)

    assert mock_get.call_count == 2

    first_call = mock_get.call_args_list[0]
    assert first_call.args[0].endswith("/target/search")
    assert first_call.kwargs["params"] == {"q": "EGFR", "format": "json"}

    second_call = mock_get.call_args_list[1]
    assert second_call.args[0].endswith("/activity")
    assert second_call.kwargs["params"] == {
        "target_chembl_id": "CHEMBL203",
        "limit": 10,
        "format": "json",
    }

    assert molecules == [
        {
            "name": "erlotinib",
            "display_name": "Erlotinib",
            "aliases": [],
            "chembl_id": "CHEMBL553",
            "target_name": "egfr",
        }
    ]


def test_fetch_molecules_for_targets_skips_target_with_no_search_hits():
    target_search_resp = _resp({"targets": []})

    with patch("ingestion.chembl_client.requests.get", side_effect=[target_search_resp]) as mock_get:
        molecules = fetch_molecules_for_targets(["NotARealTarget"])

    assert mock_get.call_count == 1
    assert molecules == []


def test_fetch_molecules_for_targets_dedupes_by_molecule_name():
    target_search_resp = _resp({"targets": [{"target_chembl_id": "CHEMBL203"}]})
    activity_resp = _resp(
        {
            "activities": [
                {"molecule_chembl_id": "CHEMBL553", "molecule_pref_name": "Erlotinib"},
                {"molecule_chembl_id": "CHEMBL553", "molecule_pref_name": "Erlotinib"},
            ]
        }
    )

    with patch("ingestion.chembl_client.requests.get", side_effect=[target_search_resp, activity_resp]):
        molecules = fetch_molecules_for_targets(["EGFR"])

    assert len(molecules) == 1


def test_get_retries_on_http_error_then_succeeds():
    failing_resp = _resp({}, status_ok=False)
    succeeding_resp = _resp({"targets": [{"target_chembl_id": "CHEMBL203"}]})

    with patch(
        "ingestion.chembl_client.requests.get", side_effect=[failing_resp, succeeding_resp]
    ) as mock_get:
        with patch("ingestion.chembl_client._fetch_activities", return_value=[]):
            fetch_molecules_for_targets(["EGFR"])

    assert mock_get.call_count == 2


def test_get_raises_after_exhausting_retries():
    always_failing = _resp({}, status_ok=False)

    with patch("ingestion.chembl_client.requests.get", return_value=always_failing) as mock_get:
        import pytest

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_molecules_for_targets(["EGFR"])

    assert mock_get.call_count == 3


def test_to_target_relations_shapes_for_load_targets_relation():
    molecules = [
        {"name": "erlotinib", "display_name": "Erlotinib", "aliases": [], "chembl_id": "CHEMBL553", "target_name": "egfr"}
    ]

    relations = to_target_relations(molecules)

    assert relations == [{"molecule_name": "erlotinib", "target_name": "egfr", "source": "chembl"}]


def test_to_target_relations_skips_molecules_without_target_name():
    molecules = [{"name": "erlotinib", "display_name": "Erlotinib", "aliases": [], "chembl_id": "CHEMBL553"}]

    assert to_target_relations(molecules) == []
