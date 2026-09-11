#!/usr/bin/env python3
"""Bounded synthetic tests for the immutable M204 S07 C4 recorder."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/m204_s07_c4_run.py"
CONTRACT = ROOT / "prd/architecture/npa-acceptance-contract.yaml"


def fake_binary(directory: Path, body: str) -> Path:
    path = directory / "fake-contour-diagnostics"
    path.write_text(
        "#!/bin/sh\n"
        "out=''\n"
        "while [ $# -gt 0 ]; do\n"
        '  if [ "$1" = --out ]; then out=$2; shift 2; else shift; fi\n'
        "done\n"
        'if [ -n "$out" ]; then\n'
        '  printf \'%s\\n\' \'{"record_kind":"header","inventory_digest":"sha256:inventory"}\' > "$out"\n'
        "fi\n" + body + "\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def invoke(
    binary: Path, directory: Path, *, attempt: str = "synthetic", extra: list[str] | None = None
) -> tuple[dict, subprocess.CompletedProcess[str]]:
    receipt = directory / f"{attempt}.json"
    diagnostics = directory / f"{attempt}.jsonl"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--binary",
        str(binary),
        "--root",
        str(directory),
        "--garant-root",
        str(directory),
        "--contract",
        str(CONTRACT),
        "--out",
        str(receipt),
        "--diagnostics-out",
        str(diagnostics),
        "--budget-seconds",
        "3600",
        "--timeout-seconds",
        "2",
        "--attempt-id",
        attempt,
        "--source-revision",
        "synthetic-caller-pin",
    ] + (extra or [])
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    assert receipt.is_file(), completed.stderr
    return json.loads(receipt.read_text(encoding="utf-8")), completed


def test_success_records_atomic_diagnostics_argv_and_hashes() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(directory, "exit 0")
        receipt, completed = invoke(binary, directory)
        assert completed.returncode == 0
        assert receipt["terminal"]["outcome"] == "complete"
        assert receipt["terminal"]["exit_code"] == 0
        assert receipt["claims"]["operational_acceptance"] == "non-pass"
        assert receipt["c4_binding"]["limit"] is None
        assert receipt["observed_output"]["jsonl_valid"] is True
        assert receipt["argv"][-2] == "--out"
        assert receipt["argv"][-1].endswith("synthetic.jsonl")
        assert receipt["logs"]["diagnostics_sha256"].startswith("sha256:")


def test_nonzero_and_timeout_are_never_operational_pass() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        nonzero, _ = invoke(fake_binary(directory, "exit 5"), directory, attempt="nonzero")
        assert nonzero["terminal"]["outcome"] == "nonzero"
        assert nonzero["claims"]["operational_acceptance"] == "non-pass"
        timeout, _ = invoke(
            fake_binary(directory, "trap '' TERM\nsleep 30"), directory, attempt="timeout"
        )
        assert timeout["terminal"]["outcome"] == "timeout"
        assert timeout["terminal"]["signal"] == "SIGTERM"
        assert timeout["claims"]["operational_acceptance"] == "non-pass"


def test_attempt_collision_is_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(directory, "exit 0")
        first, _ = invoke(binary, directory, attempt="collision")
        assert first["attempt_id"] == "collision"
        second_receipt = directory / "second.json"
        second_diag = directory / "second.jsonl"
        command = [
            sys.executable,
            str(RUNNER),
            "--binary",
            str(binary),
            "--root",
            str(directory),
            "--garant-root",
            str(directory),
            "--contract",
            str(CONTRACT),
            "--out",
            str(second_receipt),
            "--diagnostics-out",
            str(second_diag),
            "--attempt-id",
            "collision",
            "--source-revision",
            "pin",
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        assert result.returncode != 0
        assert "immutable attempt collision" in result.stderr
        assert not second_receipt.exists()


def test_verifier_rejects_forged_duration_and_bad_diagnostics_hash() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(directory, "exit 0")
        receipt_path = directory / "synthetic.json"
        receipt, _ = invoke(binary, directory)
        receipt["duration_ms"] = 3_600_000
        receipt["claims"]["operational_acceptance"] = "pass"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--verify-receipt",
                str(receipt_path),
                "--require-operational-pass",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "diagnostics" in result.stderr or "operational" in result.stderr


def main() -> int:
    tests = [
        test_success_records_atomic_diagnostics_argv_and_hashes,
        test_nonzero_and_timeout_are_never_operational_pass,
        test_attempt_collision_is_fail_closed,
        test_verifier_rejects_forged_duration_and_bad_diagnostics_hash,
    ]
    for test in tests:
        test()
    print(f"M204_S07_C4_SYNTHETIC_TESTS_OK ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
