"""Pytest bootstrap: make the repo root importable so bare `pytest tests/`
(run from `/home/labuser/agent_poc`) resolves top-level packages
(`agents`, `rag`, `ingestion`, `config`, `api`) exactly like `python -m
pytest` already does.

Without this, plain `pytest` (invoked from the repo root, no `-m`) never
puts the repo root on `sys.path` — only `python -m pytest` does that via
`-m`'s implicit `sys.path.insert(0, cwd)`. Since there's no root-level
`pytest.ini`/`pyproject.toml`/`setup.cfg` in this repo (backend subagent
write-scope is limited to `ingestion/, rag/, agents/, api/, config/,
scripts/, tests/` plus three named root files, none of which are pytest
config files), the fix lives here instead: `conftest.py` is imported by
pytest before test collection regardless of invocation style, so inserting
the repo root here is sufficient and requires no root-level file at all.
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
