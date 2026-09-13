#!/usr/bin/env python3
"""Bounded subprocess checks for the S23 detached battery controller."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m204_s23_battery.py"
EVIDENCE = ROOT / "prd/migration/rust-evidence"
ATTEMPTS = EVIDENCE / "m204-s23-c4-operational-receipt-attempts"


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def test_poll_is_bounded_and_reports_idle_without_receipt() -> None:
    result = invoke("poll")
    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert state["status"] in {"idle", "running", "terminal"}
    if not (EVIDENCE / "m204-s23-c4-operational-receipt.json").exists():
        assert state["status"] in {"idle", "running"}


def test_frozen_manifest_has_no_self_hash_or_unsafe_path() -> None:
    manifest = json.loads((EVIDENCE / "m204-s23-frozen-hashes.json").read_text())
    paths = [row["path"] for row in manifest["files"]]
    assert "prd/migration/rust-evidence/m204-s23-frozen-hashes.json" not in paths
    assert all(not Path(path).is_absolute() and ".." not in Path(path).parts for path in paths)
    assert all(".git" not in Path(path).parts and ".gsd" not in Path(path).parts for path in paths)


def test_start_rejects_unsafe_attempt_without_creating_process() -> None:
    result = invoke("start", "--attempt-id", "../escape")
    assert result.returncode != 0
    assert not (ATTEMPTS / "escape").exists()


def test_start_rejects_replay_without_touching_existing_outputs() -> None:
    receipt = EVIDENCE / "m204-s23-c4-operational-receipt.json"
    diagnostics = EVIDENCE / "m204-s23-c4-diagnostics.jsonl"
    if receipt.exists() or diagnostics.exists():
        result = invoke("start", "--attempt-id", "s23-replay")
        assert result.returncode != 0
        assert "single-use" in result.stderr or "immutable" in result.stderr


def test_malformed_lock_fails_closed() -> None:
    ATTEMPTS.mkdir(parents=True, exist_ok=True)
    lock = ATTEMPTS / ".active-lock"
    if lock.exists():
        return
    lock.write_text('{"pid":"not-an-int","attempt_id":"fixture"}\n')
    try:
        result = invoke("poll")
        assert result.returncode != 0
        assert "active lock" in result.stderr
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__]))
