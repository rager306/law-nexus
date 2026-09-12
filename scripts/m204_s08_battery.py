#!/usr/bin/env python3
"""Compose the M204 milestone validation battery without running the corpus.

The battery is a durable carrier for validate-milestone.  In particular, the
C4 result is deliberately negative: the eligible S07 attempt completed in
214150 ms, below the mandatory 3600000 ms floor.  This script never invents a
GSD aggregate source revision and never changes that classification.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prd/migration/rust-evidence/m204-validation-battery-20260912.json"
S07_BATTERY = ROOT / "prd/migration/rust-evidence/m204-s07-verification-battery-eligible.json"
S07_RECEIPT = ROOT / "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json"
S07_GOVERNOR = ROOT / "prd/migration/rust-evidence/m204-s07-governor-repeat.json"
PLACEHOLDER = "pending-fill-by-validate-unit"


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


def run_fast(argv: list[str]) -> dict[str, Any]:
    completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=120)
    output = (completed.stdout + completed.stderr).strip().splitlines()
    if completed.returncode == 0:
        stdout_tail = f"{argv[0]} gate passed"
    else:
        stdout_tail = "\n".join(output[-8:])
    return {
        "command": " ".join(argv),
        "exit_code": completed.returncode,
        "observation": "passed" if completed.returncode == 0 else "failed",
        "stdout_tail": stdout_tail,
    }


def compose() -> dict[str, Any]:
    s07_battery = load(S07_BATTERY)
    receipt = load(S07_RECEIPT)
    governor = load(S07_GOVERNOR)
    duration = receipt.get("duration_ms")
    floor = receipt.get("claims", {}).get("duration_floor_ms")
    require(s07_battery.get("operational_acceptance") == "non-pass", "S07 battery is not non-pass")
    require(
        receipt.get("claims", {}).get("operational_acceptance") == "non-pass",
        "S07 receipt claims pass",
    )
    require(
        receipt.get("terminal", {}).get("exit_code") == 0, "S07 receipt terminal exit is not zero"
    )
    require(isinstance(duration, int) and isinstance(floor, int), "C4 duration binding missing")
    require(duration < floor, "C4 duration unexpectedly meets operational floor")
    require(
        governor.get("schema_version") == "m204-s07-governor-repeat/v1",
        "S07 governor schema mismatch",
    )

    checks = [
        {
            "check_id": "integration-s07-evidence",
            "verification_class": "Integration",
            "evidence_class": "artifact",
            "command": "bounded S07 eligible battery, receipt, and governor-repeat artifact checks",
            "exit_code": 0,
            "observation": "passed",
            "stdout_tail": "S07 eligible artifacts are present, structurally bound, and C4 is non-pass",
            "source_ref": str(S07_BATTERY.relative_to(ROOT)),
        },
        {
            "check_id": "operational-c4-acceptance",
            "verification_class": "Operational",
            "evidence_class": "artifact",
            "command": "eligible-run-001 receipt duration check (no corpus execution)",
            "exit_code": 1,
            "observation": "failed",
            "stdout_tail": f"duration_ms={duration} below mandatory duration_floor_ms={floor}; operational_acceptance=non-pass",
            "source_ref": str(S07_RECEIPT.relative_to(ROOT)),
        },
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
    passed = sum(check["exit_code"] == 0 for check in checks)
    failed = len(checks) - passed
    return {
        "schema_version": "law-nexus/milestone-validation-battery/v1",
        "milestone": "M204-w2ktfw",
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "tested_source_revision": PLACEHOLDER,
        "tested_source_revision_role": "Placeholder pending the validate-milestone unit; do not replace it in execute-task.",
        "working_directory": ".",
        "environment": {
            "runner": "pi execute-task M204/S08/T02",
            "python": "uv-managed CPython",
            "cargo": "offline workspace",
        },
        "non_claims": [
            "Battery is process/verification evidence, not product readiness",
            "C4 operational acceptance remains non-pass because the real attempt is below the duration floor",
            "No corpus walk, artificial sleep, guessed hash, or requirement/lifecycle mutation was performed",
        ],
        "checks": checks,
        "summary": {"total": len(checks), "passed": passed, "failed": failed},
        "c4": {
            "observation": "failed",
            "operational_acceptance": "non-pass",
            "duration_ms": duration,
            "duration_floor_ms": floor,
            "receipt": str(S07_RECEIPT.relative_to(ROOT)),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        battery = compose()
        if args.write:
            OUT.write_text(json.dumps(battery, indent=2) + "\n", encoding="utf-8")
        if args.check:
            written = load(OUT)
            comparable = dict(battery)
            comparable["generated_at"] = written.get("generated_at")
            require(written == comparable, "battery on disk differs from composed battery")
            require(
                written["tested_source_revision"] == PLACEHOLDER,
                "battery contains a live or guessed source revision",
            )
            require(written["c4"]["operational_acceptance"] == "non-pass", "forged C4 pass")
        print(
            json.dumps(
                {"ok": True, "path": str(OUT.relative_to(ROOT)), "summary": battery["summary"]},
                sort_keys=True,
            )
        )
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
