from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/verify-falkordb-pack.py")
SKILLS_DIR = Path(".agents/skills")


def run_pack(tmp_path: Path, skills_dir: Path = SKILLS_DIR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--skills-dir",
            str(skills_dir),
            "--json-output",
            str(tmp_path / "verification-report.json"),
            "--markdown-output",
            str(tmp_path / "verification-report.md"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def copy_required_tree(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for skill_dir in SKILLS_DIR.glob("falkordb*"):
        if skill_dir.is_dir():
            shutil.copytree(skill_dir, dst / skill_dir.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(SKILLS_DIR / "pi-skill-creator", dst / "pi-skill-creator", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def test_verify_falkordb_pack_passes(tmp_path: Path) -> None:
    result = run_pack(tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "verification-report.json").read_text(encoding="utf-8"))
    assert report["summary"]["failed"] == 0
    assert report["summary"]["total"] >= 16
    assert (tmp_path / "verification-report.md").read_text(encoding="utf-8").startswith("# FalkorDB Skill Pack Verification Report")


def test_verify_falkordb_pack_fails_when_focused_skill_missing(tmp_path: Path) -> None:
    skills_copy = tmp_path / "skills"
    copy_required_tree(skills_copy)
    shutil.rmtree(skills_copy / "falkordb-index-search")
    result = run_pack(tmp_path, skills_copy)
    assert result.returncode != 0
    report = json.loads((tmp_path / "verification-report.json").read_text(encoding="utf-8"))
    assert report["summary"]["failed"] > 0
    assert any(not item["passed"] for item in report["results"])
