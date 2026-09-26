"""Module-level singletons for the stub (not-yet-wired) sub-agents.

Each uses `StubToolProvider` (empty `.tools`), so `make_agent_node` returns
the fixed "not yet wired to a data source in this POC" placeholder with
`confidence=0.0` and never calls retrieval or the LLM.

Molecule and Clinical Trial were promoted to real agents in Addendum 3 (see
`agents/real_agents.py`) now that ChEMBL/DrugBank and ClinicalTrials.gov
data feed the graph — only Safety and Competitive remain stubs here, since
none of the five ingested sources map to them.
"""

from agents.base_subagent import make_agent_node
from agents.tools import StubToolProvider

safety_agent = make_agent_node("safety", StubToolProvider(), model="claude-sonnet-5")
competitive_agent = make_agent_node("competitive", StubToolProvider(), model="claude-sonnet-5")
