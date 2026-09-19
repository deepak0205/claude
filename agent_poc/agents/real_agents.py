"""Module-level singletons for the real (retrieval-backed) sub-agents.

Each is built from the shared `make_agent_node` factory + a
`RetrievalToolProvider` differentiated only by `entity_bias`. Literature/
Disease/Target query the PubMed-derived portion of the graph broadly or
biased toward Disease/Target mentions; Molecule and Clinical Trial
(promoted from stubs in Addendum 3, now that `rag/retriever.py` supports
their entity biases) are biased toward Molecule mentions and Trial
involvement respectively — same `rag.retriever.hybrid_search` call, same
`agents.tools.RetrievalToolProvider`/`agents.base_subagent.make_agent_node`
pattern, just a different `entity_bias`.
"""

from agents.base_subagent import make_agent_node
from agents.tools import RetrievalToolProvider

literature_agent = make_agent_node("literature", RetrievalToolProvider(entity_bias=None), model="claude-sonnet-5")
disease_agent = make_agent_node("disease", RetrievalToolProvider(entity_bias="disease"), model="claude-sonnet-5")
target_agent = make_agent_node("target", RetrievalToolProvider(entity_bias="target"), model="claude-sonnet-5")
molecule_agent = make_agent_node("molecule", RetrievalToolProvider(entity_bias="molecule"), model="claude-sonnet-5")
clinical_trial_agent = make_agent_node(
    "clinical_trial", RetrievalToolProvider(entity_bias="clinical_trial"), model="claude-sonnet-5"
)
