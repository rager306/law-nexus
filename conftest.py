"""Pytest bootstrap for the src-layout package.

CI installs the package into a uv-managed virtualenv (`uv run pytest`), but the
repository-wide verification gate invokes bare `python3 -m pytest` against the
system interpreter, where `law_nexus_harness` is not installed. Exposing `src/`
on ``sys.path`` makes collection and import work in both environments without
requiring an editable install.

Temp isolation: every run stays inside the repository. All ``tmp_path``
fixtures, cache files and worker scratch land under ``tmp/pytest/``
(gitignored) instead of the shared ``/tmp``. This keeps parallel runs,
disposable clones and repeated batteries hermetic: nothing leaks into the
machine-wide temp, and ``git clean -fdx tmp/`` restores a pristine tree
without touching the OS.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

REPO_TMP = Path(__file__).resolve().parent / "tmp" / "pytest"
REPO_TMP.mkdir(parents=True, exist_ok=True)


def pytest_configure(config: object) -> None:
    """Point pytest's base temp dir at ``tmp/pytest`` (see module docstring)."""
    basetemp = config.option.basetemp  # type: ignore[attr-defined]
    if basetemp is None:
        config.option.basetemp = str(REPO_TMP / "pytest-of-root")  # type: ignore[attr-defined]
