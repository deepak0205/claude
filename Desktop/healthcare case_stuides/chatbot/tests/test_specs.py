import json
from pathlib import Path

from backend.main import app

SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"


def test_openapi_json_paths_match_live_schema():
    committed = json.loads((SPECS_DIR / "openapi.json").read_text(encoding="utf-8"))
    live = app.openapi()
    assert set(committed["paths"].keys()) == set(live["paths"].keys())
