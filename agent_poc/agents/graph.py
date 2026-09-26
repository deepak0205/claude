"""LangGraph `StateGraph` wiring: the static fan-out/fan-in shape that makes
the full 7-agent architecture demoable regardless of which agents a given
query actually needs (invariant #5 — see the plan's "LangGraph Design"
section).

Contextualization (`agents.memory.contextualize_query`) happens OUTSIDE the
compiled graph, in `run_query`, since it needs a `ConversationMemory`
instance that isn't part of `GraphState` (the graph is compiled once at
import time and reused across every request/session).

Edges: `START -> supervisor -> {7 agent nodes in parallel} -> synthesis -> END`.
Each agent node checks `routing_decision` itself (via the shared
`agent.run(query, selected)` callable from `base_subagent.make_agent_node`).
"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from agents import memory as memory_module
from agents import supervisor, synthesis
from agents.real_agents import clinical_trial_agent, disease_agent, literature_agent, molecule_agent, target_agent
from agents.state import AgentResult
from agents.stub_agents import competitive_agent, safety_agent


class GraphState(TypedDict):
    query: str
    session_id: str
    contextualized_query: str
    routing_decision: list[str]
    agent_results: Annotated[dict[str, AgentResult], operator.or_]
    final_answer: str
    final_citations: list[dict]


def _supervisor_node(state: GraphState) -> dict:
    routing_decision = supervisor.select_agents(state["contextualized_query"])
    return {"routing_decision": routing_decision}


def _synthesis_node(state: GraphState) -> dict:
    result = synthesis.synthesize(state["contextualized_query"], state["agent_results"])
    return {"final_answer": result["answer"], "final_citations": result["citations"]}


# One thin node per agent singleton, each referencing its agent callable by
# module-global *name* (not a value captured in a closure at build time) so
# that tests can `patch("agents.graph.<name>_agent", ...)` and have it take
# effect on the already-compiled graph — Python resolves a bare global name
# against the enclosing module's namespace at call time, not at def time.


def _literature_node(state: GraphState) -> dict:
    selected = "literature" in state["routing_decision"]
    result = literature_agent(state["contextualized_query"], selected)
    return {"agent_results": {"literature": result}}


def _disease_node(state: GraphState) -> dict:
    selected = "disease" in state["routing_decision"]
    result = disease_agent(state["contextualized_query"], selected)
    return {"agent_results": {"disease": result}}


def _target_node(state: GraphState) -> dict:
    selected = "target" in state["routing_decision"]
    result = target_agent(state["contextualized_query"], selected)
    return {"agent_results": {"target": result}}


def _molecule_node(state: GraphState) -> dict:
    selected = "molecule" in state["routing_decision"]
    result = molecule_agent(state["contextualized_query"], selected)
    return {"agent_results": {"molecule": result}}


def _clinical_trial_node(state: GraphState) -> dict:
    selected = "clinical_trial" in state["routing_decision"]
    result = clinical_trial_agent(state["contextualized_query"], selected)
    return {"agent_results": {"clinical_trial": result}}


def _safety_node(state: GraphState) -> dict:
    selected = "safety" in state["routing_decision"]
    result = safety_agent(state["contextualized_query"], selected)
    return {"agent_results": {"safety": result}}


def _competitive_node(state: GraphState) -> dict:
    selected = "competitive" in state["routing_decision"]
    result = competitive_agent(state["contextualized_query"], selected)
    return {"agent_results": {"competitive": result}}


_AGENT_NODES = {
    "literature": _literature_node,
    "disease": _disease_node,
    "target": _target_node,
    "molecule": _molecule_node,
    "clinical_trial": _clinical_trial_node,
    "safety": _safety_node,
    "competitive": _competitive_node,
}


def _build_graph():
    builder = StateGraph(GraphState)
    builder.add_node("supervisor", _supervisor_node)
    for agent_name, node_fn in _AGENT_NODES.items():
        builder.add_node(agent_name, node_fn)
    builder.add_node("synthesis", _synthesis_node)

    builder.add_edge(START, "supervisor")
    for agent_name in _AGENT_NODES:
        builder.add_edge("supervisor", agent_name)
        builder.add_edge(agent_name, "synthesis")
    builder.add_edge("synthesis", END)

    return builder.compile()


# Compiled once at import time, reused across every request — same
# singleton-at-import pattern as `agents/llm.py`'s `client`.
compiled_graph = _build_graph()


def run_query(query: str, memory: "memory_module.ConversationMemory") -> GraphState:
    """Run the full pipeline for one query: contextualize against `memory`,
    then invoke the compiled graph. The one function `api/main.py` calls."""
    contextualized_query = memory_module.contextualize_query(memory, query)

    result = compiled_graph.invoke(
        {
            "query": query,
            "session_id": memory.session_id,
            "contextualized_query": contextualized_query,
            "routing_decision": [],
            "agent_results": {},
            "final_answer": "",
            "final_citations": [],
        }
    )
    return result
