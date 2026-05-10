from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(".agents/skills/pi-skill-creator/scripts/validate_pi_skill.py")
PI_SKILL = Path(".agents/skills/pi-skill-creator")
FALKORDB_SKILL = Path(".agents/skills/falkordb")


def run_validator(skill_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(skill_dir), *extra],
        text=True,
        capture_output=True,
        check=False,
    )


def copy_tree(src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        if path.is_dir() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        target = dst / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def test_pi_skill_creator_validates_with_required_evals() -> None:
    result = run_validator(PI_SKILL, "--require-evals")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "PI skill validation passed" in result.stdout


def test_validator_accepts_falkordb_structure_with_evals() -> None:
    result = run_validator(FALKORDB_SKILL, "--require-evals")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "PI skill validation passed" in result.stdout


def test_validator_rejects_missing_referenced_file(tmp_path: Path) -> None:
    skill_copy = tmp_path / "pi-skill-creator"
    copy_tree(PI_SKILL, skill_copy)
    (skill_copy / "workflows" / "validate-skill.md").unlink()

    result = run_validator(skill_copy, "--require-evals")
    assert result.returncode != 0
    assert "references missing file" in result.stderr


def test_validator_rejects_invalid_eval_schema(tmp_path: Path) -> None:
    skill_copy = tmp_path / "pi-skill-creator"
    copy_tree(PI_SKILL, skill_copy)
    (skill_copy / "evals" / "evals.json").write_text(
        '{"skill_name":"pi-skill-creator","evals":[{"id":1,"prompt":"x","expected_output":"y","expectations":[]}]}'
    )

    result = run_validator(skill_copy, "--require-evals")
    assert result.returncode != 0
    assert "expectations must be a non-empty list" in result.stderr


def test_validator_rejects_description_without_trigger(tmp_path: Path) -> None:
    skill_copy = tmp_path / "pi-skill-creator"
    copy_tree(PI_SKILL, skill_copy)
    skill_md = skill_copy / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    start = text.index("description:")
    end = text.index("\n---", start)
    text = text[:start] + "description: Skill creation helper.\n" + text[end:]
    skill_md.write_text(text, encoding="utf-8")

    result = run_validator(skill_copy, "--require-evals")
    assert result.returncode != 0
    assert "when to use" in result.stderr
