"""PubMed/PMC ingestion client built on Biopython's `Bio.Entrez` wrapper
around NCBI E-utilities.

Two entry points used by `scripts/seed_demo.py`:
- `search_pmids(query, max_results)` -> list of PMID strings (`esearch`).
- `fetch_abstracts(pmids)` -> list of dicts with `pmid, title, abstract,
  journal, pub_date, doi`, fetched in batches of ~50 (`efetch`), skipping any
  record with an empty/missing abstract.

Network calls are wrapped in `tenacity` retries (exponential backoff, 3
attempts) since NCBI's client raises `urllib.error.HTTPError` on
429/5xx-style failures.
"""

import urllib.error

from Bio import Entrez
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.settings import settings

_BATCH_SIZE = 50

Entrez.email = settings.NCBI_EMAIL or None
if settings.NCBI_API_KEY:
    Entrez.api_key = settings.NCBI_API_KEY

_retry_on_transient = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(urllib.error.HTTPError),
)


@_retry_on_transient
def _esearch(query: str, max_results: int):
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    try:
        return Entrez.read(handle)
    finally:
        handle.close()


@_retry_on_transient
def _efetch_batch(pmids: list[str]):
    handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml")
    try:
        return Entrez.read(handle)
    finally:
        handle.close()


def search_pmids(query: str, max_results: int) -> list[str]:
    """Return up to `max_results` PMIDs matching `query` via `esearch`."""
    record = _esearch(query, max_results)
    return list(record.get("IdList", []))


def _extract_abstract_text(article: dict) -> str:
    abstract_block = article.get("Abstract", {})
    abstract_texts = abstract_block.get("AbstractText", [])
    if not abstract_texts:
        return ""
    # AbstractText elements may be plain strings or structured (labeled)
    # sections (e.g. "Background", "Methods") - join them all.
    parts = [str(part) for part in abstract_texts]
    return " ".join(parts).strip()


def _extract_doi(article_record: dict) -> str:
    pubmed_data = article_record.get("PubmedData", {})
    for article_id in pubmed_data.get("ArticleIdList", []):
        if getattr(article_id, "attributes", {}).get("IdType") == "doi":
            return str(article_id)
    return ""


def _extract_pub_date(article: dict) -> str:
    journal_issue = article.get("Journal", {}).get("JournalIssue", {})
    pub_date = journal_issue.get("PubDate", {})
    year = pub_date.get("Year", "")
    month = pub_date.get("Month", "")
    day = pub_date.get("Day", "")
    return " ".join(str(p) for p in (year, month, day) if p)


def _parse_record(pubmed_article: dict) -> dict | None:
    medline_citation = pubmed_article.get("MedlineCitation", {})
    article = medline_citation.get("Article", {})

    pmid = str(medline_citation.get("PMID", ""))
    abstract = _extract_abstract_text(article)
    if not abstract:
        return None

    title = str(article.get("ArticleTitle", ""))
    journal = str(article.get("Journal", {}).get("Title", ""))
    pub_date = _extract_pub_date(article)
    doi = _extract_doi(pubmed_article)

    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "journal": journal,
        "pub_date": pub_date,
        "doi": doi,
    }


def fetch_abstracts(pmids: list[str]) -> list[dict]:
    """Fetch abstract records for `pmids` in batches of `_BATCH_SIZE`.

    Skips any record with an empty/missing abstract. Returns dicts with
    `pmid, title, abstract, journal, pub_date, doi`.
    """
    results: list[dict] = []
    for start in range(0, len(pmids), _BATCH_SIZE):
        batch = pmids[start : start + _BATCH_SIZE]
        if not batch:
            continue
        record = _efetch_batch(batch)
        for pubmed_article in record.get("PubmedArticle", []):
            parsed = _parse_record(pubmed_article)
            if parsed is not None:
                results.append(parsed)
    return results
