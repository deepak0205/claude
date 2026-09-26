"""Evidence Synthesis Agent: merges every sub-agent's `AgentResult` into one
final, cited answer.

One forced tool-use call on `settings.SYNTHESIS_MODEL`. Grounding mirrors
`agents/base_subagent.py`'s `seen_pmids` pattern: the only PMIDs the model
(and the post-call defensive filter) may cite are those actually present in
some agent's `key_citations` — never invented, never pulled from model
knowledge. Stub agents' "not yet wired" results are included in the prompt
explicitly, as gaps to surface, never omitted.
"""

from agents.state import AgentResult
from agents import llm
from config.settings import settings
from config.telemetry import traced

SYNTHESIZE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pmid": {"type": "string"},
                    "agent_source": {"type": "string"},
                },
                "required": ["pmid", "agent_source"],
            },
        },
    },
    "required": ["answer", "citations"],
}


def _build_system_prompt(agent_results: dict[str, AgentResult], allowed_pmids: set[str]) -> str:
    agent_sections = []
    for agent_name, result in agent_results.items():
        agent_sections.append(
            f"### {agent_name} agent (confidence={result.confidence})\n"
            f"Summary: {result.summary}\n"
            f"Cited PMIDs: {', '.join(result.key_citations) if result.key_citations else '(none)'}"
        )
    agents_block = "\n\n".join(agent_sections)

    return (
        "You are the Evidence Synthesis Agent for a biomedical literature review "
        "and drug-discovery intelligence system. You are given the findings of "
        "every sub-agent that was consulted for a user's query, INCLUDING agents "
        "that are not yet wired to a data source in this POC (their 'not yet wired' "
        "results are gaps you must surface explicitly, not silently omit).\n\n"
        f"Sub-agent findings:\n\n{agents_block}\n\n"
        "Write one final, cited answer to the user's query. Rules:\n"
        "- Lead the answer with the direct answer to the user's query; "
        "citations, caveats, and gaps should follow, not be buried under "
        "agent-by-agent commentary first.\n"
        f"- You may ONLY cite PMIDs from this exact allowed set: "
        f"{sorted(allowed_pmids) if allowed_pmids else '(none — no real evidence was retrieved)'}. "
        "Never cite a PMID outside this set, and never cite a PMID from your own "
        "training knowledge.\n"
        "- Use inline `[PMID: <id>]` markers immediately after the claim they support.\n"
        "- If sub-agents disagree or present conflicting evidence, surface that "
        "conflict explicitly in the answer rather than silently resolving it.\n"
        "- Explicitly note any sub-agent that was not selected or is not yet wired "
        "to a data source, rather than ignoring it.\n"
        "Return your result via the synthesize tool."
    )


@traced("synthesis.synthesize")
def synthesize(query: str, agent_results: dict[str, AgentResult], memory_context: str = "") -> dict:
    """Merge `agent_results` into `{"answer": str, "citations": [{"pmid", "agent_source"}]}`.

    Only PMIDs present in some agent's `key_citations` may end up in the
    returned citations — enforced both via the system prompt and, since
    schema constraints don't stop a model from inventing a value, a
    defensive post-call filter.
    """
    allowed_pmids: set[str] = set()
    for result in agent_results.values():
        allowed_pmids.update(result.key_citations)

    system = _build_system_prompt(agent_results, allowed_pmids)
    user_content = query
    if memory_context:
        user_content = f"{memory_context}\n\nCurrent query: {query}"

    result = llm.call_tool(
        model=settings.SYNTHESIS_MODEL,
        system=system,
        user_content=user_content,
        tool_name="synthesize",
        tool_schema=SYNTHESIZE_SCHEMA,
    )

    answer = result.get("answer", "")
    raw_citations = result.get("citations", [])
    citations = [c for c in raw_citations if c.get("pmid") in allowed_pmids]

    return {"answer": answer, "citations": citations}
