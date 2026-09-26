"""Conversation memory: turn trimming, rolling summary under a per-model
token budget, and query contextualization for follow-up turns.

One *turn* = one full user query -> final synthesized answer (not per-LLM
call). See the "Addendum: Conversation Memory & Context Trimming" section of
the plan for the full design rationale.
"""

import math

from pydantic import BaseModel

from agents import llm
from config.settings import settings
from config.telemetry import memory_fold_counter, traced


class Turn(BaseModel):
    query: str
    answer: str
    citations: list[str]


class ConversationMemory(BaseModel):
    session_id: str
    turns: list[Turn] = []
    summary: str = ""


def _summary_token_budget() -> int:
    """The binding token budget for the rolling summary.

    Computed once against the smallest model context window across every
    consumer (Supervisor, Synthesis, the query-contextualizer), so the same
    summary text is guaranteed valid everywhere it's read.
    """
    return math.floor(settings.MEMORY_SUMMARY_BUDGET_FRACTION * min(settings.MODEL_MAX_CONTEXT.values()))


def _render_turns(turns: list[Turn]) -> str:
    return "\n\n".join(f"Q: {t.query}\nA: {t.answer}" for t in turns)


@traced("memory.fold_into_summary")
def _fold_into_summary(existing_summary: str, overflow_turns: list[Turn]) -> str:
    """Merge `existing_summary` with `overflow_turns` into one updated summary.

    One forced tool-use call on the cheap summarizer model. If the result is
    still over the token budget, one compression retry with an explicit
    "shorter" instruction; if still over budget after that, hard-truncate as
    a documented last resort.
    """
    budget = _summary_token_budget()
    overflow_text = _render_turns(overflow_turns)

    tool_schema = {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    }
    system = (
        "You maintain a rolling summary of an ongoing conversation between a user "
        "and a biomedical literature research assistant. Merge the existing summary "
        "with the new exchanges into one updated, concise summary that preserves the "
        "facts, entities, and open threads a future turn might need."
    )
    user_content = (
        f"Existing summary:\n{existing_summary or '(none yet)'}\n\n"
        f"New exchanges to fold in:\n{overflow_text}\n\n"
        "Produce one updated summary that merges both."
    )

    result = llm.call_tool(
        model=settings.MEMORY_SUMMARIZER_MODEL,
        system=system,
        user_content=user_content,
        tool_name="update_summary",
        tool_schema=tool_schema,
    )
    new_summary = result.get("summary", "")

    if llm.count_tokens(settings.MEMORY_SUMMARIZER_MODEL, new_summary) > budget:
        retry_user_content = (
            user_content
            + "\n\nYour previous attempt was too long. Compress further — the result "
            "MUST be shorter and must fit within the allotted budget."
        )
        result = llm.call_tool(
            model=settings.MEMORY_SUMMARIZER_MODEL,
            system=system,
            user_content=retry_user_content,
            tool_name="update_summary",
            tool_schema=tool_schema,
        )
        new_summary = result.get("summary", new_summary)

        if llm.count_tokens(settings.MEMORY_SUMMARIZER_MODEL, new_summary) > budget:
            # POC fallback: character-based hard truncation (not token-exact,
            # but guarantees we never exceed the budget even if the model
            # ignores the compression instruction).
            new_summary = new_summary[: budget * 4]

    return new_summary


def add_turn(memory: ConversationMemory, query: str, answer: str, citations: list[str]) -> ConversationMemory:
    """Append a turn; fold the oldest overflow turns into the summary once
    more than `settings.MEMORY_ACTIVE_TURNS` turns are held."""
    turns = memory.turns + [Turn(query=query, answer=answer, citations=citations)]
    summary = memory.summary

    if len(turns) > settings.MEMORY_ACTIVE_TURNS:
        overflow_count = len(turns) - settings.MEMORY_ACTIVE_TURNS
        overflow_turns = turns[:overflow_count]
        turns = turns[overflow_count:]
        memory_fold_counter.add(1)
        summary = _fold_into_summary(summary, overflow_turns)

    return ConversationMemory(session_id=memory.session_id, turns=turns, summary=summary)


def build_context(memory: ConversationMemory, model: str) -> str:
    """Render the summary + active turns for use in a prompt."""
    budget = _summary_token_budget()
    summary = memory.summary
    if summary and llm.count_tokens(model, summary) > budget:
        # Belt-and-suspenders vs. add_turn already enforcing the budget;
        # same char-based POC fallback as _fold_into_summary.
        summary = summary[: budget * 4]

    active_text = _render_turns(memory.turns)
    return f"Summary of earlier conversation:\n{summary}\n\nRecent exchanges:\n{active_text}"


@traced("memory.contextualize_query")
def contextualize_query(memory: ConversationMemory, query: str) -> str:
    """Resolve pronouns/references from history into one self-contained
    query, so the Supervisor and sub-agents can stay unaware of history."""
    if not memory.turns:
        return query

    tool_schema = {
        "type": "object",
        "properties": {"contextualized_query": {"type": "string"}},
        "required": ["contextualized_query"],
    }
    system = (
        "You rewrite a user's follow-up query into one fully self-contained query by "
        "resolving pronouns and references against the conversation history. Do not "
        "answer the query — only rewrite it."
    )
    context = build_context(memory, settings.MEMORY_SUMMARIZER_MODEL)
    user_content = f"{context}\n\nFollow-up query: {query}\n\nRewrite it as one self-contained query."

    try:
        result = llm.call_tool(
            model=settings.MEMORY_SUMMARIZER_MODEL,
            system=system,
            user_content=user_content,
            tool_name="rewrite_query",
            tool_schema=tool_schema,
        )
        contextualized = result.get("contextualized_query")
        return contextualized if contextualized else query
    except Exception:
        # A memory-layer failure must never break the main query path.
        return query
