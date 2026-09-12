#!/usr/bin/env python3
"""Fail-closed aggregate verifier for the M204/S17 validate-loop evidence.

This consumer uses only bounded predecessor files and public subprocess entrypoints.
It never opens GSD, the live journal, a database, a supervisor log, or the corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CENSUS_REL = "prd/migration/rust-evidence/m204-s17-post-s16-validate-loop.json"
MANIFEST_REL = "prd/migration/rust-evidence/m204-s17-frozen-hashes.json"
PREDECESSORS = (
    "prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json",
    "prd/migration/rust-evidence/m204-s09-trigger-sql.json",
    "prd/migration/rust-evidence/m204-s12-validate-hard-block.json",
    "prd/migration/rust-evidence/m204-s12-frozen-hashes.json",
    "prd/migration/rust-evidence/m204-s15-requirement-class.json",
    "prd/migration/rust-evidence/m204-s15-frozen-hashes.json",
    "prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json",
    "prd/migration/rust-evidence/m204-s16-frozen-hashes.json",
)
S15_RESULT = {
    "c4_acceptance": "non-pass",
    "classification": "supporting-only",
    "class_matched_ids": [],
    "status_effect": "unchanged",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    command: list[str], cwd: Path, label: str, timeout: int = 180
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{label} timed out") from exc
    if result.returncode != 0:
        raise ValueError(f"{label} failed: {result.stderr.strip() or result.returncode}")
    return result


def marker(command: list[str], cwd: Path, expected: str, label: str) -> None:
    result = run(command, cwd, label)
    if expected not in result.stdout.splitlines():
        raise ValueError(f"{label} missing marker {expected}")


def strict_json(command: list[str], cwd: Path, label: str) -> dict[str, Any]:
    result = run(command, cwd, label, timeout=30)
    if result.stderr or not result.stdout.strip():
        raise ValueError(f"{label} did not emit strict JSON")
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError(f"{label} emitted non-object JSON")
    return value


def verify_census(root: Path, census: Path, manifest: Path) -> None:
    manifest_doc = load(manifest)
    rows = {row["path"]: row for row in manifest_doc["files"]}
    for path in PREDECESSORS:
        source = root / path
        row = rows.get(path)
        if (
            row is None
            or row["sha256"] != "sha256:" + digest(source)
            or row["size_bytes"] != source.stat().st_size
        ):
            raise ValueError(f"frozen predecessor drift: {path}")
    marker(
        [
            "uv",
            "run",
            "python",
            "scripts/m204_s17_loop_note.py",
            "check",
            "--root",
            str(root),
            "--census",
            str(census),
            "--manifest",
            str(manifest),
        ],
        root,
        "S17_T01_CENSUS_OK",
        "S17 census",
    )
    value = load(census)
    if value["abort_count"] != 2 or value["law_nexus_fixable"] is not False:
        raise ValueError("S17 census count or fixability polarity drift")
    if value["engine_fix"] != "not_fixed" or value["upstream_issue"] != "not_filed":
        raise ValueError("S17 census engine status drift")
    if value["c4_acceptance"] != "non-pass" or value["status_effect"] != "unchanged":
        raise ValueError("S17 census acceptance polarity drift")
    if (
        value["s17_called_validate_milestone"] is not False
        or value["validation_projection_present"] is not False
    ):
        raise ValueError("S17 census claims validation lifecycle progress")
    intercept = value["intercept"]
    if (
        intercept["classify_status"] != "cancelled"
        or intercept["interrupted"] is not True
        or intercept["tool_calls"] != 0
    ):
        raise ValueError("S17 intercept polarity drift")
    if intercept["journal_unit_start_present"] is not False or not isinstance(
        intercept["headless_pid"], str
    ):
        raise ValueError("S17 intercept provenance drift")


def verify_predecessors(root: Path) -> list[str]:
    before = [digest(root / path) for path in PREDECESSORS]
    marker(["bash", "scripts/m204_s17_t01_verify.sh"], root, "S17_T01_CENSUS_OK", "T01 host")
    after = [digest(root / path) for path in PREDECESSORS]
    if before != after:
        raise ValueError("T01 host rewrote a pinned predecessor")
    return before


def verify_s16_and_s15(root: Path) -> None:
    marker(
        ["uv", "run", "python", "scripts/m204_s16_loop_note.py", "check"],
        root,
        "S16_T01_CENSUS_OK",
        "S16 census",
    )
    result = strict_json(
        ["uv", "run", "python", "scripts/m204_s15_requirement_class.py", "classify"],
        root,
        "S15 classify",
    )
    if result != S15_RESULT:
        raise ValueError("S15 classify result was promoted or changed")
    s09 = load(root / PREDECESSORS[0])
    s12 = load(root / PREDECESSORS[2])
    if (
        s09["trigger_name"] != "trg_workflow_technical_verdict_scope"
        or s12["s12_called_validate_milestone"] is not False
    ):
        raise ValueError("S09/S12 deadlock polarity drift")


def verify_documents(root: Path) -> None:
    runbook = (root / "doc/gsd-headless-supervisor.md").read_text(encoding="utf-8")
    rc28 = (root / "prd/architecture/review-cases/rc28-remediation-program.md").read_text(
        encoding="utf-8"
    )
    for text in (
        "Post-S16 no-artifact validate ×2 plus intercepted predispatch",
        "do not re-dispatch validate-milestone as a settled-attempt substitute",
    ):
        if text not in runbook:
            raise ValueError(f"runbook missing S17 operator instruction: {text}")
    for text in (
        "## M204 S17 post-S16 validate deadlock evidence",
        "2026-09-12T17:02:09.344Z",
        "348f1061-7c45-42ec-a4f3-49d75280035b",
        "engine_fix=not_fixed",
        "19 findings remain open",
        "C4 `non-pass`",
        "supporting-only",
        "S17_T03_VERIFY_OK",
    ):
        if text not in rc28:
            raise ValueError(f"RC28 missing S17 non-claim: {text}")
    if "class_matched_ids=[" in rc28 and "class_matched_ids=[]" not in rc28:
        raise ValueError("RC28 contains promoted requirement classification")


def verify(root: Path, census: Path, manifest: Path) -> None:
    verify_documents(root)
    before = [digest(root / path) for path in PREDECESSORS]
    verify_census(root, census, manifest)
    verify_s16_and_s15(root)
    marker(["bash", "scripts/m204_s17_t02_verify.sh"], root, "S17_T02_NEGATIVES_OK", "T02 host")
    verify_predecessors(root)
    after = [digest(root / path) for path in PREDECESSORS]
    if before != after:
        raise ValueError("aggregate rewrote a pinned predecessor")
    print("S17_VERIFY_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--census", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    census = (args.census or root / CENSUS_REL).resolve()
    manifest = (args.manifest or root / MANIFEST_REL).resolve()
    try:
        verify(root, census, manifest)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s17_evidence_verify: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
