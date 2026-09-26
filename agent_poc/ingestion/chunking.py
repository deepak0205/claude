"""Text chunking for ingestion (PubMed abstracts, ClinicalTrials.gov brief
summaries).

The common case is one chunk per document, since abstracts/brief summaries
are short. A sliding-window fallback kicks in only when the text exceeds
`_LONG_TEXT_TOKEN_THRESHOLD` tokens, using a cheap whitespace word-count as
an approximation of token count (avoids an Anthropic API round-trip -
`agents.llm.count_tokens` - for every single document during bulk ingestion;
words and tokens are close enough at this threshold for a chunking decision,
which only needs to be roughly right, not exact).
"""

from config.telemetry import ingestion_stage_counter, traced

_LONG_TEXT_TOKEN_THRESHOLD = 500
_WINDOW_WORDS = 400
_OVERLAP_WORDS = 50


def _approx_token_count(text: str) -> int:
    return len(text.split())


def _sliding_window_spans(text: str, window_words: int, overlap_words: int) -> list[tuple[int, int]]:
    """Return `(char_start, char_end)` spans over `text`, splitting on
    whitespace-delimited words with a sliding window + overlap."""
    words = text.split()
    if not words:
        return [(0, len(text))]

    # Precompute each word's (start, end) offset in the original text so
    # window boundaries can be reported as exact character offsets.
    word_spans: list[tuple[int, int]] = []
    cursor = 0
    for word in words:
        start = text.index(word, cursor)
        end = start + len(word)
        word_spans.append((start, end))
        cursor = end

    spans: list[tuple[int, int]] = []
    step = max(window_words - overlap_words, 1)
    i = 0
    while i < len(word_spans):
        window_end_idx = min(i + window_words, len(word_spans))
        char_start = word_spans[i][0]
        char_end = word_spans[window_end_idx - 1][1]
        spans.append((char_start, char_end))
        if window_end_idx >= len(word_spans):
            break
        i += step
    return spans


@traced("ingestion.chunking.chunk_text")
def chunk_text(text: str, source: str, chunk_id_prefix: str) -> list[dict]:
    """Split `text` into one or more chunk dicts.

    One chunk in the common case (short text). Falls back to a sliding
    window (with overlap) if `text` exceeds `_LONG_TEXT_TOKEN_THRESHOLD`
    approximate tokens (word-count heuristic, see module docstring).

    Each returned dict: `{chunk_id, text, chunk_index, char_start, char_end,
    source}`. `chunk_id` is `f"{chunk_id_prefix}_{chunk_index}"`.
    """
    if not text:
        return []

    if _approx_token_count(text) <= _LONG_TEXT_TOKEN_THRESHOLD:
        spans = [(0, len(text))]
    else:
        spans = _sliding_window_spans(text, _WINDOW_WORDS, _OVERLAP_WORDS)

    chunks = []
    for chunk_index, (char_start, char_end) in enumerate(spans):
        chunks.append(
            {
                "chunk_id": f"{chunk_id_prefix}_{chunk_index}",
                "text": text[char_start:char_end],
                "chunk_index": chunk_index,
                "char_start": char_start,
                "char_end": char_end,
                "source": source,
            }
        )
    ingestion_stage_counter.add(len(chunks), {"module": "chunking", "function": "chunk_text"})
    return chunks
