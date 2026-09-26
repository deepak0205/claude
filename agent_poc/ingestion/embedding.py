"""Voyage AI embedding client for ingestion (documents) and retrieval
(queries), per the plan's asymmetric `input_type="document"` at index time /
`"query"` at query time.

The `voyageai.Client` is lazy-initialized at module level so importing this
module never requires `VOYAGE_API_KEY` to be set (e.g. in tests that mock
the client entirely).
"""

import voyageai

from config.settings import settings
from config.telemetry import ingestion_stage_counter, traced

# Voyage's batch embed endpoint accepts many texts per call; chunk into
# groups of 128 as a conservative, well-under-any-documented-limit default.
_BATCH_SIZE = 128

_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    return _client


@traced("ingestion.embedding.embed_documents")
def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed `texts` for indexing (`input_type="document"`), batched in
    groups of `_BATCH_SIZE`."""
    if not texts:
        return []

    client = _get_client()
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start : start + _BATCH_SIZE]
        result = client.embed(batch, model=settings.VOYAGE_EMBED_MODEL, input_type="document")
        embeddings.extend(result.embeddings)
    ingestion_stage_counter.add(
        len(embeddings), {"module": "embedding", "function": "embed_documents"}
    )
    return embeddings


@traced("ingestion.embedding.embed_query")
def embed_query(text: str) -> list[float]:
    """Embed a single query string (`input_type="query"`)."""
    client = _get_client()
    result = client.embed([text], model=settings.VOYAGE_EMBED_MODEL, input_type="query")
    return result.embeddings[0]
