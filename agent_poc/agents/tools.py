"""Plugin layer for sub-agent tool-use.

`ToolProvider` is the shared interface that lets `agents/base_subagent.py`
drive a genuine agentic tool-use loop (via `agents/llm.py:run_agent_loop`)
without caring whether the underlying source is real retrieval
(`RetrievalToolProvider`) or not-yet-built (`StubToolProvider`). Swapping a
stub for a real agent later is purely a matter of constructing a different
`ToolProvider` — no changes to orchestration code.
"""

from typing import Protocol


class ToolProvider(Protocol):
    tools: list[dict]

    def execute(self, name: str, input: dict) -> str: ...


class RetrievalToolProvider:
    """Wraps `rag.retriever.hybrid_search` (or an injected `search_fn`) as a
    single `search_evidence` tool the model can call repeatedly.

    Stateless and safe to hold as a long-lived module-level singleton reused
    across concurrent requests — no per-call data is ever stored on `self`.
    """

    def __init__(self, entity_bias: str | None, search_fn=None):
        self.entity_bias = entity_bias
        self.search_fn = search_fn
        self.tools = [
            {
                "name": "search_evidence",
                "description": (
                    "Search the biomedical literature graph for evidence relevant to a "
                    "query. Returns a numbered list of paper snippets with PMIDs."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        ]

    def execute(self, name: str, input: dict) -> str:
        top_k = max(1, min(20, input.get("top_k", 5)))

        if self.search_fn is not None:
            search_fn = self.search_fn
        else:
            from rag.retriever import hybrid_search

            search_fn = hybrid_search

        results = search_fn(input["query"], self.entity_bias, top_k)

        blocks = []
        for i, item in enumerate(results, start=1):
            blocks.append(
                f"{i}. PMID: {item.pmid}\n"
                f"Title: {item.title}\n"
                f"Journal: {item.journal}\n"
                f"Year: {item.year}\n"
                f"Snippet: {item.snippet}"
            )
        return "\n\n".join(blocks)


class StubToolProvider:
    """No-op provider for sub-agents with no data source yet. `.tools` being
    empty is what tells `base_subagent.make_agent_node` to skip the loop
    entirely — `.execute` is never actually called."""

    tools: list[dict] = []

    def execute(self, name: str, input: dict) -> str:
        raise NotImplementedError("StubToolProvider has no tools to execute")
