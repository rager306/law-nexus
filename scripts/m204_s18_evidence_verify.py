#!/usr/bin/env python3
"""Fail-closed aggregate consumer for M204/S18 supporting evidence.

Only bounded evidence files and public subprocess entrypoints are used.  This
verifier never reads GSD state, journals, supervisor logs, or the corpus.
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
CENSUS = "prd/migration/rust-evidence/m204-s18-post-s17-validate-loop.json"
MANIFEST = "prd/migration/rust-evidence/m204-s18-frozen-hashes.json"
PINS = tuple(
    f"prd/migration/rust-evidence/m204-s{n}-{name}.json"
    for n, name in (
        ("09", "gsd-validate-deadlock"),
        ("09", "trigger-sql"),
        ("12", "validate-hard-block"),
        ("12", "frozen-hashes"),
        ("15", "requirement-class"),
        ("15", "frozen-hashes"),
        ("16", "post-s15-validate-loop"),
        ("16", "frozen-hashes"),
        ("17", "post-s16-validate-loop"),
        ("17", "frozen-hashes"),
    )
)
S15 = {
    "c4_acceptance": "non-pass",
    "classification": "supporting-only",
    "class_matched_ids": [],
    "status_effect": "unchanged",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    command: list[str], root: Path, label: str, timeout: int = 180
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{label} timed out") from exc
    if result.returncode:
        raise ValueError(f"{label} failed: {result.stderr.strip() or result.returncode}")
    return result


def marker(command: list[str], root: Path, expected: str, label: str, timeout: int = 180) -> None:
    result = run(command, root, label, timeout)
    if expected not in result.stdout.splitlines():
        raise ValueError(f"{label} missing marker {expected}")


def strict_classifier(root: Path) -> None:
    result = run(
        ["uv", "run", "python", "scripts/m204_s15_requirement_class.py", "classify"],
        root,
        "S15 classifier",
        30,
    )
    if result.stderr or not result.stdout.strip():
        raise ValueError("S15 classifier did not emit strict JSON")
    if json.loads(result.stdout) != S15:
        raise ValueError("S15 classifier was malformed or promoted")


def verify(root: Path) -> None:
    paths = [root / path for path in PINS]
    before = [digest(path) for path in paths]
    census = root / CENSUS
    # T01 is the public compose/check boundary. Do not compose here: rewriting
    # the census would turn a tampered integration fixture into a false pass.
    marker(["bash", "scripts/m204_s18_t01_verify.sh"], root, "S18_T01_CENSUS_OK", "T01 host", 180)
    value: dict[str, Any] = json.loads(census.read_text(encoding="utf-8"))
    if value.get("abort_count") != 2 or len(value.get("aborts", [])) != 2:
        raise ValueError("S18 census count drift")
    if value.get("law_nexus_fixable") is not False or value.get("engine_fix") != "not_fixed":
        raise ValueError("S18 engine-fix polarity drift")
    if value.get("c4_acceptance") != "non-pass" or value.get("status_effect") != "unchanged":
        raise ValueError("S18 acceptance polarity drift")
    if (
        value.get("s18_called_validate_milestone") is not False
        or value.get("validation_projection_present") is not False
    ):
        raise ValueError("S18 claims lifecycle promotion")
    intercept = value.get("intercept", {})
    if not (
        intercept.get("classify_status") == "cancelled"
        and intercept.get("interrupted") is True
        and intercept.get("tool_calls") == 0
        and intercept.get("journal_unit_start_present") is False
    ):
        raise ValueError("S18 intercept polarity drift")
    runbook = (root / "doc/gsd-headless-supervisor.md").read_text(encoding="utf-8")
    rc28 = (root / "prd/architecture/review-cases/rc28-remediation-program.md").read_text(
        encoding="utf-8"
    )
    for text in (
        "Post-S17 no-artifact validate ×2 plus intercepted predispatch",
        "do not re-dispatch validate-milestone as a settled-attempt substitute",
    ):
        if text not in runbook:
            raise ValueError(f"runbook missing S18 operator instruction: {text}")
    for text in (
        "## M204 S18 post-S17 validate deadlock evidence",
        "2026-09-12T18:15:23.617Z",
        "f76ce443-afce-43bb-9342-0b0484260951",
        "F19 remains open",
        "C4 `non-pass`",
        "supporting-only",
        "no SIGTERM claim",
        "S18_T03_VERIFY_OK",
    ):
        if text not in rc28:
            raise ValueError(f"RC28 missing S18 non-claim: {text}")
    if "class_matched_ids=[" in rc28 and "class_matched_ids=[]" not in rc28:
        raise ValueError("RC28 contains promoted requirement classification")
    # Independent predecessor consumers; deliberately do not run the recursive S17 host.
    run(["uv", "run", "python", "scripts/m204_s17_loop_note.py", "check"], root, "S17 census", 30)
    strict_classifier(root)
    s09 = json.loads(paths[0].read_text(encoding="utf-8"))
    s12 = json.loads(paths[2].read_text(encoding="utf-8"))
    if (
        s09.get("trigger_name") != "trg_workflow_technical_verdict_scope"
        or s12.get("s12_called_validate_milestone") is not False
    ):
        raise ValueError("S09/S12 predecessor polarity drift")
    run(
        ["uv", "run", "python", "scripts/test_m204_s18_validate_loop.py"],
        root,
        "S18 negatives",
        180,
    )
    after = [digest(path) for path in paths]
    if before != after:
        raise ValueError("aggregate rewrote a frozen predecessor")
    print("S18_VERIFY_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        verify(args.root.resolve())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s18_evidence_verify: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
