from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/verify-falkordb-skill.py")
ROOT = Path(".agents/skills/falkordb")


def run_verifier(root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_falkordb_skill_verifier_passes() -> None:
    result = run_verifier()
    assert result.returncode == 0, result.stderr + result.stdout
    assert "FalkorDB skill pack verification passed" in result.stdout


def test_verifier_rejects_project_specific_terms(tmp_path: Path) -> None:
    skill_copy = tmp_path / "falkordb"
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        target = skill_copy / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    notes = skill_copy / "references" / "capability-evidence.md"
    notes.write_text(notes.read_text(encoding="utf-8") + "\nLegalGraph Nexus\n", encoding="utf-8")

    result = run_verifier(skill_copy)
    assert result.returncode != 0
    assert "project-specific term" in result.stderr or "project-specific term" in result.stdout


def test_verifier_rejects_missing_referenced_file(tmp_path: Path) -> None:
    skill_copy = tmp_path / "falkordb"
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        target = skill_copy / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    (skill_copy / "workflows" / "check-capability.md").unlink()
    result = run_verifier(skill_copy)
    assert result.returncode != 0
    assert "missing required file" in result.stderr or "missing required file" in result.stdout
