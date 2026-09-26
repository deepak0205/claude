"""Tests for ingestion.pubmed_client. `Bio.Entrez.esearch`/`efetch`/`read`
are mocked directly - zero live network calls."""

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from ingestion.pubmed_client import fetch_abstracts, search_pmids


def _handle():
    handle = MagicMock()
    handle.close = MagicMock()
    return handle


def test_search_pmids_returns_id_list():
    with patch("ingestion.pubmed_client.Entrez.esearch", return_value=_handle()) as mock_esearch, patch(
        "ingestion.pubmed_client.Entrez.read", return_value={"IdList": ["111", "222"]}
    ):
        result = search_pmids("EGFR AND lung cancer", max_results=10)

    assert result == ["111", "222"]
    mock_esearch.assert_called_once()
    assert mock_esearch.call_args.kwargs["term"] == "EGFR AND lung cancer"
    assert mock_esearch.call_args.kwargs["retmax"] == 10


def test_search_pmids_retries_on_http_error_then_succeeds():
    call_count = {"n": 0}

    def flaky_esearch(**kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
        return _handle()

    # tenacity's wait strategy is baked into the decorator at import time, so
    # this test pays the real (short, min=1s) backoff between attempts
    # rather than mocking it away.
    with patch("ingestion.pubmed_client.Entrez.esearch", side_effect=flaky_esearch), patch(
        "ingestion.pubmed_client.Entrez.read", return_value={"IdList": ["1"]}
    ):
        result = search_pmids("query", max_results=5)

    assert result == ["1"]
    assert call_count["n"] == 2


def test_search_pmids_raises_after_exhausting_retries():
    def always_fails(**kwargs):
        raise urllib.error.HTTPError("url", 500, "Server Error", {}, None)

    with patch("ingestion.pubmed_client.Entrez.esearch", side_effect=always_fails):
        with pytest.raises(urllib.error.HTTPError):
            search_pmids("query", max_results=5)


_GOOD_RECORD = {
    "PubmedArticle": [
        {
            "MedlineCitation": {
                "PMID": "111",
                "Article": {
                    "ArticleTitle": "A great paper",
                    "Abstract": {"AbstractText": ["Some findings about EGFR."]},
                    "Journal": {
                        "Title": "Journal of Things",
                        "JournalIssue": {"PubDate": {"Year": "2023", "Month": "Jan"}},
                    },
                },
            },
            "PubmedData": {"ArticleIdList": []},
        },
        {
            # Empty abstract -> should be skipped.
            "MedlineCitation": {
                "PMID": "222",
                "Article": {
                    "ArticleTitle": "No abstract paper",
                    "Abstract": {"AbstractText": []},
                    "Journal": {"Title": "Journal of Nothing", "JournalIssue": {"PubDate": {}}},
                },
            },
            "PubmedData": {"ArticleIdList": []},
        },
        {
            # Missing Abstract key entirely -> should also be skipped.
            "MedlineCitation": {
                "PMID": "333",
                "Article": {
                    "ArticleTitle": "Also no abstract",
                    "Journal": {"Title": "Journal of Void", "JournalIssue": {"PubDate": {}}},
                },
            },
            "PubmedData": {"ArticleIdList": []},
        },
    ]
}


def test_fetch_abstracts_skips_empty_and_missing_abstracts():
    with patch("ingestion.pubmed_client.Entrez.efetch", return_value=_handle()), patch(
        "ingestion.pubmed_client.Entrez.read", return_value=_GOOD_RECORD
    ):
        result = fetch_abstracts(["111", "222", "333"])

    assert len(result) == 1
    assert result[0]["pmid"] == "111"
    assert result[0]["title"] == "A great paper"
    assert "EGFR" in result[0]["abstract"]
    assert result[0]["journal"] == "Journal of Things"


def test_fetch_abstracts_batches_in_groups_of_50():
    pmids = [str(i) for i in range(120)]
    calls = []

    def fake_efetch(**kwargs):
        calls.append(kwargs["id"])
        return _handle()

    with patch("ingestion.pubmed_client.Entrez.efetch", side_effect=fake_efetch), patch(
        "ingestion.pubmed_client.Entrez.read", return_value={"PubmedArticle": []}
    ):
        fetch_abstracts(pmids)

    assert len(calls) == 3
    assert len(calls[0].split(",")) == 50
    assert len(calls[1].split(",")) == 50
    assert len(calls[2].split(",")) == 20


def test_fetch_abstracts_empty_input_makes_no_calls():
    with patch("ingestion.pubmed_client.Entrez.efetch") as mock_efetch:
        result = fetch_abstracts([])

    assert result == []
    mock_efetch.assert_not_called()
