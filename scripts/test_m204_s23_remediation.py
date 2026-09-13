#!/usr/bin/env python3
"""Bounded subprocess checks for the immutable S23 remediation controller."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m204_s23_remediation.py"
EVIDENCE = ROOT / "prd/migration/rust-evidence"
RECEIPT = EVIDENCE / "m204-s23-remediation-v2-c4-receipt.json"
BATTERY = EVIDENCE / "m204-s23-remediation-v2-battery.json"
OWNER = EVIDENCE / "m204-s23-remediation-v2-owner-resolution.json"
MANIFEST = EVIDENCE / "m204-s23-remediation-v2-frozen-hashes.json"


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def test_unsafe_attempt_is_rejected() -> None:
    result = invoke("start", "--attempt-id", "../escape")
    assert result.returncode != 0
    assert not (EVIDENCE / "m204-s23-remediation-v2-attempts" / "escape").exists()


def test_poll_is_bounded() -> None:
    result = invoke("poll")
    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert state["status"] in {"idle", "running", "terminal"}


def test_compose_is_immutable_and_owner_stays_blocked() -> None:
    if not OWNER.exists():
        result = invoke("compose")
        assert result.returncode == 0, result.stderr
    result = invoke("compose")
    assert result.returncode != 0
    owner = json.loads(OWNER.read_text(encoding="utf-8"))
    assert owner["decision"] == "D453"
    assert owner["gsd_recovery_liveness"] == "blocked-external"
    assert owner["disposition"] == "needs-remediation"
    assert owner["classification"] == "supporting-only"


def test_no_historical_outputs_are_overwritten() -> None:
    historical = EVIDENCE / "m204-s23-c4-operational-receipt.json"
    before = historical.read_bytes()
    result = invoke("start", "--attempt-id", "m204-s23-remediation-replay")
    if RECEIPT.exists():
        assert result.returncode != 0
    assert historical.read_bytes() == before


def main() -> int:
    tests = [
        test_unsafe_attempt_is_rejected,
        test_poll_is_bounded,
        test_compose_is_immutable_and_owner_stays_blocked,
        test_no_historical_outputs_are_overwritten,
    ]
    for test in tests:
        test()
    print(f"M204_S23_REMEDIATION_FIXTURES_OK ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
