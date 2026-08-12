from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
LOCAL_OR_HISTORICAL_MARKERS = (
    ".gsd/",
    ".agents/",
    "Old_project/",
    ".lex/",
    ".commandcode/",
    "archive/",
    "python_archive/",
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK_RE = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)")


def _tracked_markdown() -> list[Path]:
    relative_paths = subprocess.check_output(
        ["git", "ls-files", "--", "*.md"], cwd=ROOT, text=True
    ).splitlines()
    return [ROOT / relative for relative in relative_paths]


def test_root_readme_maps_only_tracked_active_surfaces() -> None:
    text = README.read_text(encoding="utf-8")
    assert "Historical and local-only surfaces" not in text
    for marker in LOCAL_OR_HISTORICAL_MARKERS:
        assert marker not in text, f"README exposes local/historical path {marker!r}"


def test_tracked_markdown_has_no_links_to_local_or_historical_surfaces() -> None:
    findings: list[str] = []
    for path in _tracked_markdown():
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            targets = [match.group(1) for match in MARKDOWN_LINK_RE.finditer(line)]
            reference_match = REFERENCE_LINK_RE.match(line)
            if reference_match is not None:
                targets.append(reference_match.group(1))
            for raw_target in targets:
                target = raw_target.split("#", 1)[0]
                if any(marker in target for marker in LOCAL_OR_HISTORICAL_MARKERS):
                    relative = path.relative_to(ROOT).as_posix()
                    findings.append(f"{relative}:{line_number} -> {target}")
    assert findings == []
