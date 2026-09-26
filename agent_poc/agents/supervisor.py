"""Supervisor Agent: routes a (contextualized) user query to the relevant
sub-agents.

One forced tool-use call on `settings.SUPERVISOR_MODEL`, same primitive
(`agents.llm.call_tool`) `agents/memory.py`'s `_fold_into_summary`/
`contextualize_query` already use. Never raises — a routing failure falls
back to selecting all 7 agents, which keeps the graph's static fan-out
demoable even when the Supervisor call itself fails (same posture as
`contextualize_query`'s exception fallback).
"""

from agents import llm
from config.settings import settings
from config.telemetry import traced

AGENT_NAMES = ["literature", "disease", "target", "molecule", "clinical_trial", "safety", "competitive"]

SELECT_AGENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "agents": {
            "type": "array",
            "items": {"type": "string", "enum": AGENT_NAMES},
        },
    },
    "required": ["agents"],
}

AGENT_DESCRIPTIONS: dict[str, str] = {
    "literature": "general biomedical literature evidence",
    "disease": "disease-focused evidence (epidemiology, mechanisms, etc.)",
    "target": "drug target / gene / protein focused evidence",
    "molecule": "drug / compound focused evidence",
    "clinical_trial": "clinical trial focused evidence",
    "safety": "drug safety / adverse event focused evidence",
    "competitive": "competitive landscape / market focused evidence",
}

_AGENT_LIST = "\n".join(f"- {name}: {desc}" for name, desc in AGENT_DESCRIPTIONS.items())

SYSTEM_PROMPT = (
    "You are the Supervisor Agent for a biomedical literature review and "
    "drug-discovery intelligence system. Given a user's query, decide which "
    "of the following sub-agents should be invoked to gather evidence:\n\n"
    f"{_AGENT_LIST}\n\n"
    "Queries typically need 2-4 agents, not just 1 and not all 7. When a "
    "query spans multiple angles (for example, a target and its trial "
    "status), select every genuinely relevant agent rather than the single "
    "closest match. When you are uncertain whether an agent applies, prefer "
    "including it over omitting it.\n\n"
    "Select only the agents genuinely relevant to the query's intent. Return "
    "your selection via the select_agents tool."
)


@traced("supervisor.select_agents")
def select_agents(query: str) -> list[str]:
    """Return the list of agent names the Supervisor selects for `query`.

    Falls back to selecting all 7 agents on any exception (invalid schema
    response, API error, etc.) — a routing failure must never break the
    main query path.
    """
    try:
        result = llm.call_tool(
            model=settings.SUPERVISOR_MODEL,
            system=SYSTEM_PROMPT,
            user_content=query,
            tool_name="select_agents",
            tool_schema=SELECT_AGENTS_SCHEMA,
        )
        agents = result.get("agents", [])
        selected = [name for name in agents if name in AGENT_NAMES]
        return selected
    except Exception:
        return list(AGENT_NAMES)
