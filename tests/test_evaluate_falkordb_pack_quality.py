from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/evaluate-falkordb-pack-quality.py")
SKILLS_DIR = Path(".agents/skills")


def run_quality(tmp_path: Path | None = None, skills_dir: Path = SKILLS_DIR, *extra: str) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(SCRIPT), "--skills-dir", str(skills_dir), *extra]
    if tmp_path is not None:
        args.extend([
            "--json-output",
            str(tmp_path / "pack-quality.json"),
            "--markdown-output",
            str(tmp_path / "pack-quality.md"),
        ])
    return subprocess.run(args, text=True, capture_output=True, check=False)


def copy_falkordb_skills(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for skill_dir in SKILLS_DIR.glob("falkordb*"):
        if skill_dir.is_dir():
            shutil.copytree(skill_dir, dst / skill_dir.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def test_pack_quality_passes_all_checks(tmp_path: Path) -> None:
    result = run_quality(tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "pack-quality.json").read_text(encoding="utf-8"))
    assert report["summary"]["failed"] == 0
    assert report["summary"]["pass_rate"] == 1.0
    assert report["summary"]["total"] >= 70
    assert (tmp_path / "pack-quality.md").read_text(encoding="utf-8").startswith("# FalkorDB Focused Skill Pack Quality Evaluation")


def test_pack_quality_fails_when_focused_reference_is_thin(tmp_path: Path) -> None:
    skills_copy = tmp_path / "skills"
    copy_falkordb_skills(skills_copy)
    reference = skills_copy / "falkordb-genai-mcp-graphrag" / "references" / "main.md"
    reference.write_text("# Thin\n\nGraphRAG MCP LangChain LlamaIndex only.\n", encoding="utf-8")
    result = run_quality(tmp_path, skills_copy, "--min-pass-rate", "1.0")
    assert result.returncode != 0
    report = json.loads((tmp_path / "pack-quality.json").read_text(encoding="utf-8"))
    assert report["summary"]["failed"] > 0
    assert any(item["skill"] == "falkordb-genai-mcp-graphrag" and not item["passed"] for item in report["results"])


def test_pack_quality_detects_project_specific_leakage(tmp_path: Path) -> None:
    skills_copy = tmp_path / "skills"
    copy_falkordb_skills(skills_copy)
    reference = skills_copy / "falkordb-cypher" / "references" / "main.md"
    reference.write_text(reference.read_text(encoding="utf-8") + "\nLegalGraph Nexus\n", encoding="utf-8")
    result = run_quality(tmp_path, skills_copy, "--min-pass-rate", "1.0")
    assert result.returncode != 0
    report = json.loads((tmp_path / "pack-quality.json").read_text(encoding="utf-8"))
    assert any("LegalGraph Nexus" in item["description"] and not item["passed"] for item in report["results"])
