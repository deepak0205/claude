"""Shared agentic tool-use logic for every real/stub sub-agent node.

`make_agent_node` is a factory, not a class hierarchy: it closes over an
`agent_name`, a `ToolProvider` (real retrieval or stub), and a model name,
and returns a plain `(query, selected) -> AgentResult` callable. `graph.py`
(a later phase) wraps this into a LangGraph node, e.g.:

    lambda state: {"agent_results": {
        "literature": literature_agent(state["contextualized_query"],
                                        "literature" in state["routing_decision"]),
    }}
"""

import re
from typing import Callable

from agents.llm import run_agent_loop
from agents.state import AgentResult
from agents.supervisor import AGENT_DESCRIPTIONS
from config.telemetry import tool_call_counter, tracer

REPORT_FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_citations": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": ["summary", "key_citations", "confidence"],
    "additionalProperties": False,
}


def _build_system_prompt(agent_name: str) -> str:
    """Compose the real system prompt for a sub-agent's tool-use loop.

    Combines the agent's role (shared with the Supervisor's own routing
    prompt via `AGENT_DESCRIPTIONS`, so the two can't drift), an explicit
    grounding rule, tool-use strategy, and confidence-calibration guidance.
    """
    role = AGENT_DESCRIPTIONS[agent_name]
    return (
        f"You are the {agent_name} agent for a biomedical literature review "
        f"and drug-discovery intelligence system. Your role is to gather "
        f"{role}.\n\n"
        "Grounding rule: you may ONLY cite a PMID that literally appeared in "
        "the text of a search_evidence tool result. Never cite a PMID from "
        "your own training knowledge, and never invent a PMID.\n\n"
        "Tool-use strategy: call search_evidence to gather evidence before "
        "calling report_findings to finish. If your first call's results "
        "look thin or irrelevant, reformulate the query and call "
        "search_evidence again. You should typically need only 2-3 calls "
        "total before calling report_findings.\n\n"
        "Confidence calibration: the confidence you report must reflect the "
        "quantity, relevance, and consistency of the evidence you actually "
        "retrieved during this call, not your general topical certainty "
        "about the subject."
    )


def make_agent_node(agent_name: str, tool_provider, model: str) -> Callable[[str, bool], AgentResult]:
    def run(query: str, selected: bool) -> AgentResult:
        with tracer.start_as_current_span(
            f"agent.{agent_name}", attributes={"agent_name": agent_name, "selected": selected}
        ):
            if not selected:
                return AgentResult(
                    agent_name=agent_name,
                    summary=f"{agent_name} agent was not selected for this query.",
                    key_citations=[],
                    confidence=0.0,
                )

            if not tool_provider.tools:
                return AgentResult(
                    agent_name=agent_name,
                    summary=f"{agent_name} agent is not yet wired to a data source in this POC.",
                    key_citations=[],
                    confidence=0.0,
                )

            try:
                seen_pmids: set[str] = set()

                def tracking_executor(name, input):
                    with tracer.start_as_current_span(
                        "agent.tool_call", attributes={"agent_name": agent_name, "tool_name": name}
                    ):
                        tool_call_counter.add(1, {"agent_name": agent_name, "tool_name": name})
                        result_text = tool_provider.execute(name, input)
                        seen_pmids.update(re.findall(r"PMID:\s*(\d+)", result_text))
                        return result_text

                result = run_agent_loop(
                    model=model,
                    system=_build_system_prompt(agent_name),
                    user_content=query,
                    tools=tool_provider.tools,
                    tool_executor=tracking_executor,
                    finish_tool_name="report_findings",
                    finish_tool_schema=REPORT_FINDINGS_SCHEMA,
                )

                key_citations = [c for c in result["key_citations"] if c in seen_pmids]
                confidence = max(0.0, min(1.0, float(result["confidence"])))

                return AgentResult(
                    agent_name=agent_name,
                    summary=result["summary"],
                    key_citations=key_citations,
                    confidence=confidence,
                )
            except Exception as e:
                return AgentResult(
                    agent_name=agent_name,
                    summary=f"{agent_name} agent failed: {e}",
                    key_citations=[],
                    confidence=0.0,
                )

    return run
