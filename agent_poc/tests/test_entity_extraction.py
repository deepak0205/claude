"""Tests for ingestion.entity_extraction. `agents.llm.call_tool` is mocked
directly - zero live Anthropic API calls."""

from unittest.mock import patch

import anthropic
import pytest

from ingestion.entity_extraction import (
    ENTITY_EXTRACTION_MODEL,
    RECORD_ENTITIES_TOOL_NAME,
    SYSTEM_PROMPT_BLOCKS,
    extract_entities,
)

_EXPECTED_SHAPE = {
    "diseases": [{"name": "lung cancer", "aliases": ["NSCLC"]}],
    "targets": [{"name": "EGFR", "aliases": []}],
    "molecules": [{"name": "erlotinib", "aliases": []}],
    "disease_target_relations": [{"disease": "lung cancer", "target": "EGFR"}],
    "molecule_target_relations": [{"molecule": "erlotinib", "target": "EGFR"}],
}


def test_extract_entities_returns_expected_shape():
    with patch("ingestion.entity_extraction.llm.call_tool", return_value=_EXPECTED_SHAPE) as mock_call:
        result = extract_entities("EGFR mutations drive resistance in NSCLC treated with erlotinib.")

    assert result == _EXPECTED_SHAPE
    assert set(result.keys()) == {
        "diseases",
        "targets",
        "molecules",
        "disease_target_relations",
        "molecule_target_relations",
    }
    mock_call.assert_called_once()


def test_extract_entities_uses_cached_system_prompt_and_haiku_model():
    with patch("ingestion.entity_extraction.llm.call_tool", return_value=_EXPECTED_SHAPE) as mock_call:
        extract_entities("some abstract text")

    kwargs = mock_call.call_args.kwargs
    assert kwargs["model"] == ENTITY_EXTRACTION_MODEL == "claude-haiku-4-5-20251001"
    assert kwargs["system"] == SYSTEM_PROMPT_BLOCKS
    assert kwargs["tool_name"] == RECORD_ENTITIES_TOOL_NAME
    assert kwargs["system"][-1]["cache_control"] == {"type": "ephemeral"}


def test_extract_entities_empty_text_short_circuits_without_llm_call():
    with patch("ingestion.entity_extraction.llm.call_tool") as mock_call:
        result = extract_entities("   ")

    mock_call.assert_not_called()
    assert result == {
        "diseases": [],
        "targets": [],
        "molecules": [],
        "disease_target_relations": [],
        "molecule_target_relations": [],
    }


def test_extract_entities_retries_on_api_error_then_succeeds():
    call_count = {"n": 0}

    def flaky_call_tool(**kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise anthropic.APIConnectionError(request=None)
        return _EXPECTED_SHAPE

    with patch("ingestion.entity_extraction.llm.call_tool", side_effect=flaky_call_tool):
        result = extract_entities("abstract text")

    assert result == _EXPECTED_SHAPE
    assert call_count["n"] == 2


def test_extract_entities_raises_after_exhausting_retries():
    def always_fails(**kwargs):
        raise anthropic.APIConnectionError(request=None)

    with patch("ingestion.entity_extraction.llm.call_tool", side_effect=always_fails):
        with pytest.raises(anthropic.APIConnectionError):
            extract_entities("abstract text")
