from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/evaluate-falkordb-trigger-proxy.py")
SKILLS_DIR = Path(".agents/skills")


def run_proxy(tmp_path: Path, skills_dir: Path = SKILLS_DIR, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--skills-dir",
            str(skills_dir),
            "--report-dir",
            str(tmp_path / "trigger-proxy"),
            "--json-output",
            str(tmp_path / "trigger-proxy-report.json"),
            "--markdown-output",
            str(tmp_path / "trigger-proxy-report.md"),
            *extra,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def copy_falkordb_skills(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for skill_dir in SKILLS_DIR.glob("falkordb*"):
        if skill_dir.is_dir():
            shutil.copytree(skill_dir, dst / skill_dir.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def test_trigger_proxy_passes_for_pack(tmp_path: Path) -> None:
    result = run_proxy(tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "trigger-proxy-report.json").read_text(encoding="utf-8"))
    assert report["summary"]["failed"] == 0
    assert report["summary"]["false_negatives"] == 0
    assert report["summary"]["false_positives"] == 0
    assert report["actual_activation"] == "unavailable"
    assert len(report["skills"]) >= 12
    assert (tmp_path / "trigger-proxy-report.md").read_text(encoding="utf-8").startswith("# FalkorDB Skill Pack Trigger Proxy Evaluation")


def test_trigger_proxy_fails_on_bad_description(tmp_path: Path) -> None:
    skills_copy = tmp_path / "skills"
    copy_falkordb_skills(skills_copy)
    skill_md = skills_copy / "falkordb-cypher" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.startswith("description:"):
            lines.append("description: Use for cooking recipes and kitchen ingredient planning.")
        else:
            lines.append(line)
    skill_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = run_proxy(tmp_path, skills_copy, "--skill", "falkordb-cypher", "--min-pass-rate", "1.0")
    assert result.returncode != 0
    report = json.loads((tmp_path / "trigger-proxy-report.json").read_text(encoding="utf-8"))
    assert report["summary"]["failed"] > 0
    assert report["summary"]["false_negatives"] > 0
