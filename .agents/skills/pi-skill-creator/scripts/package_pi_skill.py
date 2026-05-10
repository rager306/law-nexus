#!/usr/bin/env python3
"""Package a PI/GSD skill into a portable tar.gz archive."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path

from validate_pi_skill import validate_skill

EXCLUDE_PARTS = {"__pycache__", ".pytest_cache"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_NAMES = {"quality-report.json", "quality-report.md"}


def include(path: Path) -> bool:
    if any(part in EXCLUDE_PARTS for part in path.parts):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    if "-workspace" in path.name:
        return False
    return True


def package(skill_dir: Path, output: Path, require_evals: bool) -> Path:
    validate_skill(skill_dir, require_evals=require_evals)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file() and include(path.relative_to(skill_dir)):
                archive.add(path, arcname=str(skill_dir.name / path.relative_to(skill_dir)) if isinstance(skill_dir.name, Path) else f"{skill_dir.name}/{path.relative_to(skill_dir)}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Package PI/GSD skill")
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--require-evals", action="store_true")
    args = parser.parse_args()
    output = args.output or Path("dist") / f"{args.skill_dir.name}.tar.gz"
    result = package(args.skill_dir, output, args.require_evals)
    print(f"Packaged skill: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
