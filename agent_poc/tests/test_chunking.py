"""Tests for ingestion.chunking. Pure logic, no mocking needed."""

from ingestion.chunking import _LONG_TEXT_TOKEN_THRESHOLD, chunk_text


def test_short_text_produces_one_chunk_with_correct_offsets():
    text = "EGFR mutations drive resistance in non-small cell lung cancer."
    chunks = chunk_text(text, source="pubmed", chunk_id_prefix="12345")

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["chunk_id"] == "12345_0"
    assert chunk["chunk_index"] == 0
    assert chunk["char_start"] == 0
    assert chunk["char_end"] == len(text)
    assert chunk["text"] == text
    assert chunk["source"] == "pubmed"


def test_empty_text_produces_no_chunks():
    assert chunk_text("", source="pubmed", chunk_id_prefix="1") == []


def test_long_text_produces_multiple_chunks_with_sliding_window():
    # Build text comfortably over the token threshold (word-count heuristic).
    words = [f"word{i}" for i in range(_LONG_TEXT_TOKEN_THRESHOLD * 3)]
    text = " ".join(words)

    chunks = chunk_text(text, source="clinicaltrials", chunk_id_prefix="NCT001")

    assert len(chunks) > 1
    for i, chunk in enumerate(chunks):
        assert chunk["chunk_id"] == f"NCT001_{i}"
        assert chunk["chunk_index"] == i
        assert chunk["source"] == "clinicaltrials"
        # Char offsets must reconstruct the exact substring of `text`.
        assert text[chunk["char_start"] : chunk["char_end"]] == chunk["text"]

    # Windows should overlap: the char_end of a chunk should exceed the
    # char_start of the next chunk (except possibly at the very end).
    for i in range(len(chunks) - 1):
        assert chunks[i]["char_end"] > chunks[i + 1]["char_start"]

    # The final chunk should reach exactly to the end of the text.
    assert chunks[-1]["char_end"] == len(text)


def test_long_text_chunks_are_non_decreasing_and_cover_full_text():
    words = [f"tok{i}" for i in range(_LONG_TEXT_TOKEN_THRESHOLD * 2)]
    text = " ".join(words)

    chunks = chunk_text(text, source="pubmed", chunk_id_prefix="99")

    assert chunks[0]["char_start"] == 0
    assert chunks[-1]["char_end"] == len(text)
    for chunk in chunks:
        assert 0 <= chunk["char_start"] < chunk["char_end"] <= len(text)
