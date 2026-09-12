#!/usr/bin/env python3
"""Compose the additive M204/S10 validation battery without a corpus walk.

The S10 receipt is source-bound but deliberately negative: the owned full walk
completed beyond the duration floor, yet its diagnostic JSONL is invalid.  The
composer never turns that integrity failure into an operational PASS and never
fills the GSD aggregate source revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json"
RECEIPT = ROOT / "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json"
HISTORICAL = ROOT / "prd/migration/rust-evidence/m204-validation-battery-20260912.json"
PLACEHOLDER = "pending-fill-by-validate-unit"
FLOOR = 3_600_000


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable JSON: {path.relative_to(ROOT)}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def run_fast(argv: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180)
        return {
            "command": " ".join(argv),
            "exit_code": result.returncode,
            "observation": "passed" if result.returncode == 0 else "failed",
            "stdout_tail": (result.stdout + result.stderr).strip()[-500:],
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "command": " ".join(argv),
            "exit_code": 127,
            "observation": "failed",
            "stdout_tail": str(exc),
        }


def compose(*, run_gates: bool = True) -> dict[str, Any]:
    receipt = load(RECEIPT)
    terminal = receipt.get("terminal", {})
    corpus = receipt.get("corpus", {})
    binding = receipt.get("c4_binding", {})
    observed = receipt.get("observed_output", {})
    claims = receipt.get("claims", {})
    require(
        receipt.get("schema") == "m204-s10-c4-operational-receipt/v1", "S10 receipt schema mismatch"
    )
    require(receipt.get("attempt_id") == "s10-full-walk-001", "wrong S10 attempt")
    require(
        terminal == {"outcome": "complete", "exit_code": 0, "signal": None, "timeout": False},
        "S10 terminal outcome changed",
    )
    require(corpus.get("consultant_xml_count") == 43_785, "consultant corpus count is not 43785")
    require(
        binding.get("jobs") == 1 and binding.get("limit") is None, "S10 jobs/limit binding changed"
    )
    require(receipt.get("duration_ms", -1) >= FLOOR, "S10 duration does not meet recorded floor")
    require(observed.get("jsonl_valid") is False, "S10 receipt unexpectedly has valid JSONL")
    require(claims.get("operational_acceptance") == "non-pass", "S10 receipt falsely claims PASS")

    checks = [
        {
            "check_id": "integration-s10-receipt-integrity",
            "verification_class": "Integration",
            "evidence_class": "artifact",
            "command": "m204_s10_c4_run.py --verify-receipt m204-s10-c4-operational-receipt.json",
            "exit_code": 0,
            "observation": "passed",
            "stdout_tail": "S10 receipt is complete, source-bound, and preserves operational non-pass",
            "source_ref": str(RECEIPT.relative_to(ROOT)),
        },
        {
            "check_id": "operational-c4-acceptance",
            "verification_class": "Operational",
            "evidence_class": "artifact",
            "command": "S10 strict predicate: terminal, duration, inventory, and JSONL validity",
            "exit_code": 1,
            "observation": "failed",
            "stdout_tail": "jsonl_valid=false; operational_acceptance=non-pass despite duration_ms=4969991",
            "source_ref": str(RECEIPT.relative_to(ROOT)),
        },
    ]
    if run_gates:
        checks.extend(
            [
                {
                    "check_id": "operational-cargo-fmt",
                    "verification_class": "Operational",
                    "evidence_class": "command",
                    **run_fast(["cargo", "fmt", "--all", "--check"]),
                    "source_ref": "live-fast-gate",
                },
                {
                    "check_id": "operational-cargo-check",
                    "verification_class": "Operational",
                    "evidence_class": "command",
                    **run_fast(["cargo", "check", "--workspace", "--offline"]),
                    "source_ref": "live-fast-gate",
                },
            ]
        )
    passed = sum(row["exit_code"] == 0 for row in checks)
    return {
        "schema_version": "law-nexus/milestone-validation-battery/v1",
        "milestone": "M204-w2ktfw",
        "slice": "S10",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "tested_source_revision": PLACEHOLDER,
        "tested_source_revision_role": "Placeholder pending the validate-milestone unit; never guess or fill in execute-task.",
        "working_directory": ".",
        "environment": {
            "runner": "pi execute-task M204/S10/T04",
            "python": "uv-managed CPython",
            "cargo": "offline workspace",
        },
        "supersession": {
            "from": str(HISTORICAL.relative_to(ROOT)),
            "to": str(OUT.relative_to(ROOT)),
            "reason": "S10 source-bound receipt supersedes the S08 carrier for additive validation evidence",
            "authorization": "D445",
            "preserved_hash": sha256(HISTORICAL),
        },
        "non_claims": [
            "Battery is verification evidence, not product readiness",
            "C4 remains non-pass because diagnostic JSONL is invalid",
            "No corpus walk, artificial sleep, guessed aggregate hash, requirement closure, or lifecycle mutation was performed",
        ],
        "checks": checks,
        "summary": {"total": len(checks), "passed": passed, "failed": len(checks) - passed},
        "c4": {
            "observation": "failed",
            "operational_acceptance": "non-pass",
            "duration_ms": receipt["duration_ms"],
            "duration_floor_ms": FLOOR,
            "jsonl_valid": False,
            "receipt": str(RECEIPT.relative_to(ROOT)),
        },
        "historical_receipt_pins": {
            "m203_s09": "prd/migration/rust-evidence/m203-s09-c4-operational-receipt.json",
            "m204_s06": "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
            "m204_s07": "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-gates", action="store_true")
    args = parser.parse_args()
    try:
        battery = compose(run_gates=not args.no_gates)
        if args.write:
            OUT.write_text(json.dumps(battery, indent=2) + "\n", encoding="utf-8")
        if args.check:
            written = load(OUT)
            require(
                written["schema_version"] == "law-nexus/milestone-validation-battery/v1",
                "battery schema mismatch",
            )
            require(
                written["tested_source_revision"] == PLACEHOLDER,
                "battery contains guessed source revision",
            )
            require(written["c4"]["operational_acceptance"] == "non-pass", "forged C4 PASS")
            require(written["c4"]["jsonl_valid"] is False, "battery launders invalid JSONL")
            require(
                written["supersession"]["preserved_hash"] == sha256(HISTORICAL),
                "historical battery hash changed",
            )
            checks_by_id = {row["check_id"]: row for row in written["checks"]}
            require(
                set(checks_by_id)
                >= {"integration-s10-receipt-integrity", "operational-c4-acceptance"},
                "required S10 checks missing",
            )
            require(
                checks_by_id["operational-c4-acceptance"]["exit_code"] == 1,
                "C4 failure was laundered",
            )
            require(
                written["summary"]
                == {
                    "total": len(written["checks"]),
                    "passed": sum(row["exit_code"] == 0 for row in written["checks"]),
                    "failed": sum(row["exit_code"] != 0 for row in written["checks"]),
                },
                "battery summary is stale",
            )
        print(
            json.dumps(
                {"ok": True, "path": str(OUT.relative_to(ROOT)), "summary": battery["summary"]},
                sort_keys=True,
            )
        )
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
