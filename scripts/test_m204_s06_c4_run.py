#!/usr/bin/env python3
"""Bounded synthetic tests for the M204 S06 process-only recorder."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/m204_s06_c4_run.py"
CONTRACT = ROOT / "prd/architecture/npa-acceptance-contract.yaml"


def fake_binary(directory: Path, body: str) -> Path:
    path = directory / "fake contour diagnostic"
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def invoke(binary: Path, out: Path, extra: list[str]) -> dict:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--binary",
        str(binary),
        "--root",
        str(binary.parent),
        "--contract",
        str(CONTRACT),
        "--out",
        str(out),
        "--budget-seconds",
        "3600",
        "--timeout-seconds",
        "2",
        "--attempt-id",
        "synthetic",
    ] + extra
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    assert completed.stdout.strip()
    return json.loads(out.read_text(encoding="utf-8"))


def test_success_uses_argv_array_and_records_binding() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(
            directory, 'printf \'{"inventory_digest":"sha256:inventory"}\\n\'\nexit 0'
        )
        receipt = invoke(binary, directory / "success.json", ["--source-revision", "caller-pin"])
        assert receipt["terminal"] == {
            "outcome": "complete",
            "exit_code": 0,
            "signal": None,
            "timeout": False,
        }
        assert receipt["source_revision"] == "caller-pin"
        assert receipt["argv"][0] == str(binary.resolve())
        assert receipt["observed_output"]["inventory_digest"] == "sha256:inventory"
        assert receipt["claims"]["operational_acceptance"] == "non-pass"
        assert receipt["contract"]["check_id"] == "c4-live-check"


def test_nonzero_is_not_complete() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(directory, "exit 5")
        receipt = invoke(binary, directory / "nonzero.json", [])
        assert receipt["terminal"]["outcome"] == "nonzero"
        assert receipt["terminal"]["exit_code"] == 5
        assert receipt["claims"]["operational_acceptance"] == "non-pass"


def test_timeout_is_terminal_and_owned_process_is_reaped() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(directory, "trap '' TERM\nsleep 30")
        receipt = invoke(binary, directory / "timeout.json", [])
        assert receipt["terminal"]["outcome"] == "timeout"
        assert receipt["terminal"]["timeout"] is True
        assert receipt["terminal"]["signal"] == "SIGTERM"


def test_verifier_rejects_complete_nonzero_receipt() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(directory, "exit 0")
        receipt_path = directory / "receipt.json"
        receipt = invoke(binary, receipt_path, [])
        receipt["terminal"] = {
            "outcome": "complete",
            "exit_code": 7,
            "signal": None,
            "timeout": False,
        }
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        checked = subprocess.run(
            [sys.executable, str(RUNNER), "--verify-receipt", str(receipt_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert checked.returncode != 0


def main() -> int:
    test_success_uses_argv_array_and_records_binding()
    test_nonzero_is_not_complete()
    test_timeout_is_terminal_and_owned_process_is_reaped()
    test_verifier_rejects_complete_nonzero_receipt()
    print("M204_S06_C4_SYNTHETIC_TESTS_OK (4 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
