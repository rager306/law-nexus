from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/evaluate-falkordb-skill-quality.py")
ROOT = Path(".agents/skills/falkordb")
EVALS = ROOT / "evals" / "evals.json"


def run_quality(tmp_path: Path | None = None, *extra: str) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(SCRIPT), "--root", str(ROOT), "--evals", str(EVALS), *extra]
    if tmp_path is not None:
        args.extend([
            "--json-output",
            str(tmp_path / "quality.json"),
            "--markdown-output",
            str(tmp_path / "quality.md"),
        ])
    return subprocess.run(args, text=True, capture_output=True, check=False)


def test_quality_evaluation_passes_all_expectations(tmp_path: Path) -> None:
    result = run_quality(tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "quality.json").read_text(encoding="utf-8"))
    assert report["summary"] == {"passed": 30, "failed": 0, "total": 30, "pass_rate": 1.0}
    assert len(report["results"]) == 6
    assert (tmp_path / "quality.md").read_text(encoding="utf-8").startswith("# FalkorDB Skill Quality Evaluation")


def test_quality_evaluation_fails_when_required_content_missing(tmp_path: Path) -> None:
    skill_copy = tmp_path / "falkordb"
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        target = skill_copy / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    capability = skill_copy / "references" / "capability-evidence.md"
    capability.write_text("claim classes intentionally incomplete", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(skill_copy),
            "--evals",
            str(skill_copy / "evals" / "evals.json"),
            "--json-output",
            str(tmp_path / "quality.json"),
            "--markdown-output",
            str(tmp_path / "quality.md"),
            "--min-pass-rate",
            "1.0",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    report = json.loads((tmp_path / "quality.json").read_text(encoding="utf-8"))
    assert report["summary"]["failed"] > 0
