"""Pytest bootstrap for the src-layout package.

CI installs the package into a uv-managed virtualenv (`uv run pytest`), but the
repository-wide verification gate invokes bare `python3 -m pytest` against the
system interpreter, where `law_nexus_harness` is not installed. Exposing `src/`
on ``sys.path`` makes collection and import work in both environments without
requiring an editable install.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
