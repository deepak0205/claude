"""Claude-based structured entity extraction for PubMed abstracts.

One `agents.llm.call_tool` call per abstract, forced onto a strict
`record_entities` tool schema, using the cheap ingestion-extraction model
(`claude-haiku-4-5-20251001`, per the plan's "Model / Embedding Choices"
table). The system prompt is identical across every call in a seed run
(~150-300 calls), so it's built once at import time using the Anthropic
`cache_control: ephemeral` block form for prompt caching.
"""

import anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agents import llm
from config.telemetry import traced

# Matches the plan's "Model / Embedding Choices" table entry for ingestion
# entity extraction (bulk structured extraction, run once at seed time).
ENTITY_EXTRACTION_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT_TEXT = (
    "You are a biomedical entity extraction system. Given the title and abstract "
    "of a scientific paper, extract every Disease, Target (gene/protein), and "
    "Molecule (drug/compound) mentioned, plus any disease-target and "
    "molecule-target relationships stated or clearly implied in the text.\n\n"
    "Rules:\n"
    "- Use the most standard/canonical form of each entity's name as `name`; "
    "capture any alternate names/abbreviations used in the text as `aliases`.\n"
    "- Only extract relations that are explicitly supported by the text.\n"
    "- If a category has no entities, return an empty list for it.\n"
    "- Never invent entities or relations not grounded in the provided text."
)

# Identical across every call in a seed run -> cache_control on the last
# (and only) system block, per the plan's prompt-caching convention.
SYSTEM_PROMPT_BLOCKS = [
    {
        "type": "text",
        "text": _SYSTEM_PROMPT_TEXT,
        "cache_control": {"type": "ephemeral"},
    }
]

RECORD_ENTITIES_TOOL_NAME = "record_entities"

_NAME_ALIASES_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "aliases": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "aliases"],
}

RECORD_ENTITIES_SCHEMA = {
    "type": "object",
    "properties": {
        "diseases": {"type": "array", "items": _NAME_ALIASES_SCHEMA},
        "targets": {"type": "array", "items": _NAME_ALIASES_SCHEMA},
        "molecules": {"type": "array", "items": _NAME_ALIASES_SCHEMA},
        "disease_target_relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "disease": {"type": "string"},
                    "target": {"type": "string"},
                },
                "required": ["disease", "target"],
            },
        },
        "molecule_target_relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "molecule": {"type": "string"},
                    "target": {"type": "string"},
                },
                "required": ["molecule", "target"],
            },
        },
    },
    "required": [
        "diseases",
        "targets",
        "molecules",
        "disease_target_relations",
        "molecule_target_relations",
    ],
}

_EMPTY_RESULT = {
    "diseases": [],
    "targets": [],
    "molecules": [],
    "disease_target_relations": [],
    "molecule_target_relations": [],
}


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(anthropic.APIError),
)
def _call_record_entities(abstract_text: str) -> dict:
    return llm.call_tool(
        model=ENTITY_EXTRACTION_MODEL,
        system=SYSTEM_PROMPT_BLOCKS,
        user_content=abstract_text,
        tool_name=RECORD_ENTITIES_TOOL_NAME,
        tool_schema=RECORD_ENTITIES_SCHEMA,
    )


@traced("ingestion.entity_extraction.extract_entities")
def extract_entities(abstract_text: str) -> dict:
    """Extract diseases/targets/molecules + their relations from one abstract.

    Returns a dict shaped like `RECORD_ENTITIES_SCHEMA`. Empty/whitespace-only
    input short-circuits to an all-empty result with zero LLM calls. Once the
    `tenacity` retries around the underlying API call are exhausted, the
    exception propagates rather than being swallowed here - a caller (e.g.
    `scripts/seed_demo.py`) may want to know a specific abstract failed
    extraction rather than silently getting empty entities.
    """
    if not abstract_text or not abstract_text.strip():
        return dict(_EMPTY_RESULT)
    return _call_record_entities(abstract_text)
