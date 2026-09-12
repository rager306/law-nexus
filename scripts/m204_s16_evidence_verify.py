#!/usr/bin/env python3
"""Fail-closed aggregate verifier for the M204/S16 deadlock census.

This is a bounded evidence consumer. It invokes the public T01/T02 subprocess
contracts, independently invokes the S15 classifier, and never reads GSD,
the live journal, a database, or the corpus.
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
CENSUS = ROOT / "prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json"
MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s16-frozen-hashes.json"
PREDECESSORS = (
    "prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json",
    "prd/migration/rust-evidence/m204-s09-trigger-sql.json",
    "prd/migration/rust-evidence/m204-s12-validate-hard-block.json",
    "prd/migration/rust-evidence/m204-s12-frozen-hashes.json",
    "prd/migration/rust-evidence/m204-s15-requirement-class.json",
    "prd/migration/rust-evidence/m204-s15-frozen-hashes.json",
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


def run_marker(command: list[str], marker: str, label: str, timeout: int = 180) -> None:
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{label} timed out") from exc
    if result.returncode != 0:
        raise ValueError(f"{label} failed: {result.stderr.strip() or result.returncode}")
    if not any(line == marker for line in result.stdout.splitlines()):
        raise ValueError(f"{label} missing marker {marker}")


def run_json(command: list[str], label: str, timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{label} timed out") from exc
    if result.returncode != 0:
        raise ValueError(f"{label} failed: {result.stderr.strip() or result.returncode}")
    if result.stderr or not result.stdout.strip():
        raise ValueError(f"{label} did not emit strict JSON")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} emitted invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} emitted non-object JSON")
    return value


def verify_census() -> None:
    run_marker(
        ["uv", "run", "python", "scripts/m204_s16_loop_note.py", "check"],
        "S16_T01_CENSUS_OK",
        "S16 census",
    )
    value = load(CENSUS)
    if value.get("abort_count") != 3 or value.get("law_nexus_fixable") is not False:
        raise ValueError("S16 census count or fixability polarity drift")
    if value.get("engine_fix") != "not_fixed" or value.get("upstream_issue") != "not_filed":
        raise ValueError("S16 census engine status drift")
    if value.get("c4_acceptance") != "non-pass" or value.get("status_effect") != "unchanged":
        raise ValueError("S16 census acceptance polarity drift")
    if value.get("s16_called_validate_milestone") is not False:
        raise ValueError("S16 census claims validate-milestone was called")
    s09 = load(ROOT / PREDECESSORS[0])
    s12 = load(ROOT / PREDECESSORS[2])
    if (
        s09.get("abort_message")
        != "technical verdict requires the current criterion and matching settled attempt"
    ):
        raise ValueError("S09 exact abort message drift")
    if s09.get("trigger_name") != "trg_workflow_technical_verdict_scope":
        raise ValueError("S09 trigger drift")
    if (
        s12.get("s12_called_validate_milestone") is not False
        or s12.get("status_effect") != "unchanged"
    ):
        raise ValueError("S12 hard-block polarity drift")


def verify_predecessors() -> list[str]:
    before = [digest(ROOT / path) for path in PREDECESSORS]
    run_marker(["bash", "scripts/m204_s16_t01_verify.sh"], "S16_T01_CENSUS_OK", "T01 host")
    after = [digest(ROOT / path) for path in PREDECESSORS]
    if before != after:
        raise ValueError("T01 host rewrote a pinned predecessor")
    return before


def verify_s15() -> None:
    result = run_json(
        ["uv", "run", "python", "scripts/m204_s15_requirement_class.py", "classify"],
        "S15 classify",
    )
    if result != S15_RESULT:
        raise ValueError("S15 classify result is not non-pass/supporting-only")


def verify_documents() -> None:
    runbook = (ROOT / "doc/gsd-headless-supervisor.md").read_text(encoding="utf-8")
    rc28 = (ROOT / "prd/architecture/review-cases/rc28-remediation-program.md").read_text(
        encoding="utf-8"
    )
    required = (
        "Post-S15 no-artifact validate ×3 is the same S09 engine deadlock",
        "do not re-dispatch validate-milestone as a settled-attempt substitute",
    )
    if any(text not in runbook for text in required):
        raise ValueError("runbook is missing the S16 operator hard-block paragraph")
    for text in (
        "## M204 S16 post-S15 validate deadlock census",
        "law_nexus_fixable=false",
        "engine_fix=not_fixed",
        "upstream_issue=not_filed",
        "F19",
        "all 19 findings remain open",
        "S16_T03_VERIFY_OK",
    ):
        if text not in rc28:
            raise ValueError(f"RC28 missing S16 non-claim: {text}")
    if "validated/closed/advanced" in rc28:
        raise ValueError("RC28 contains a forbidden lifecycle promotion")


def verify() -> None:
    verify_documents()
    before = [digest(ROOT / path) for path in PREDECESSORS]
    verify_predecessors()
    verify_census()
    run_marker(["bash", "scripts/m204_s16_t02_verify.sh"], "S16_T02_NEGATIVES_OK", "T02 host")
    verify_s15()
    after = [digest(ROOT / path) for path in PREDECESSORS]
    if before != after:
        raise ValueError("S16 aggregate rewrote a pinned predecessor")
    print("S16_VERIFY_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify",))
    parser.parse_args()
    try:
        verify()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s16_evidence_verify: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
