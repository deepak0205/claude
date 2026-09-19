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


def make_agent_node(agent_name: str, tool_provider, model: str) -> Callable[[str, bool], AgentResult]:
    def run(query: str, selected: bool) -> AgentResult:
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
                result_text = tool_provider.execute(name, input)
                seen_pmids.update(re.findall(r"PMID:\s*(\d+)", result_text))
                return result_text

            result = run_agent_loop(
                model=model,
                system=f"You are the {agent_name} agent...",
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
