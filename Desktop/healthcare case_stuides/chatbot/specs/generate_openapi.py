"""Regenerate specs/openapi.json from the live FastAPI schema.

Run after any change to backend/main.py's routes/models:
    python specs/generate_openapi.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app  # noqa: E402


def main() -> None:
    out = Path(__file__).resolve().parent / "openapi.json"
    out.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
