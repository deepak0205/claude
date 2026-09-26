from backend.config import DOCS_DIR
from backend.rag.retriever import TfidfRetriever


def test_retriever_builds_corpus_from_docs():
    retriever = TfidfRetriever(DOCS_DIR)
    assert len(retriever.chunks) > 0


def test_retriever_surfaces_relevant_doc_for_known_question():
    retriever = TfidfRetriever(DOCS_DIR)
    results = retriever.retrieve("What percentage faster is Carta Healthcare's clinical data processing?", top_k=3)
    assert results, "expected at least one retrieved chunk"
    assert any(r.doc_id == "claude-healthcare-case-studies.md" for r in results)
    assert any("66%" in r.text for r in results)


def test_retriever_returns_nothing_for_unrelated_query():
    retriever = TfidfRetriever(DOCS_DIR)
    results = retriever.retrieve("zzzxq flibbertigibbet wingdoodle qbrx", top_k=3)
    assert results == []
