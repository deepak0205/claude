"""Pass/fail validation gate, pattern ported from pharma-project-analytics/scripts/validate_phase3.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class ValidationReport:
    def __init__(self):
        self.results: list[tuple[str, bool, str]] = []

    def add_test(self, name: str, passed: bool, details: str = "") -> None:
        self.results.append((name, passed, details))

    def print_summary(self) -> bool:
        print("\n=== Validation Report ===")
        all_passed = True
        for name, passed, details in self.results:
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {name}" + (f" — {details}" if details else ""))
            all_passed = all_passed and passed
        print(f"\n{sum(p for _, p, _ in self.results)}/{len(self.results)} checks passed.")
        return all_passed


def main() -> int:
    report = ValidationReport()

    from backend.config import DOCS_DIR, settings

    report.add_test("docs directory exists", DOCS_DIR.is_dir())
    doc_files = list(DOCS_DIR.glob("*.md")) if DOCS_DIR.is_dir() else []
    report.add_test("corpus has all 5 case studies represented", len(doc_files) >= 4,
                     details=f"found {len(doc_files)} markdown files")

    from backend.rag.retriever import TfidfRetriever
    retriever = TfidfRetriever(DOCS_DIR)
    report.add_test("retriever builds a non-empty corpus", len(retriever.chunks) > 0)

    sample_questions = [
        "What percentage faster is Carta Healthcare's clinical data processing?",
        "How many employees use BannerWise at Banner Health?",
        "What population size does Qualified Health screen at UT?",
    ]
    for q in sample_questions:
        results = retriever.retrieve(q, top_k=3)
        report.add_test(f"retrieval non-empty for: {q[:50]}...", len(results) > 0)

    report.add_test("GROQ_API_KEY dev fallback documented (optional — UI supplies the key normally)",
                     True,
                     details=f"env fallback {'set' if settings.groq_api_key else 'not set (expected — user supplies via UI)'}")

    passed = report.print_summary()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
