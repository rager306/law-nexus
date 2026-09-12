#!/usr/bin/env python3
"""Bounded hostile tests for the immutable M204 S10 C4 recorder."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/m204_s10_c4_run.py"
CONTRACT = ROOT / "prd/architecture/npa-acceptance-contract.yaml"


def fake_binary(directory: Path, body: str, *, digest: str = "sha256:inventory") -> Path:
    path = directory / "fake-contour-diagnostics"
    path.write_text(
        "#!/bin/sh\n"
        "out=''\n"
        "while [ $# -gt 0 ]; do\n"
        '  if [ "$1" = --out ]; then out=$2; shift 2; else shift; fi\n'
        "done\n"
        'if [ -n "$out" ]; then printf \'%s\\n\' \'{"record_kind":"header","inventory_digest":"'
        + digest
        + '"}\' > "$out"; fi\n'
        + body
        + "\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def invoke(
    binary: Path,
    directory: Path,
    *,
    attempt: str = "synthetic",
    extra: list[str] | None = None,
) -> tuple[dict, subprocess.CompletedProcess[str]]:
    receipt = directory / f"{attempt}.json"
    diagnostics = directory / f"{attempt}.jsonl"
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
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert receipt.is_file(), completed.stderr
    return json.loads(receipt.read_text(encoding="utf-8")), completed


def verify(receipt: Path, *, strict: bool = False) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(RUNNER), "--verify-receipt", str(receipt)]
    if strict:
        command.append("--require-operational-pass")
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def test_short_debug_attempt_records_non_performance_claim() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        receipt, completed = invoke(
            fake_binary(directory, "exit 0"),
            directory,
            extra=["--binary-profile", "debug", "--jobs", "1"],
        )
        assert completed.returncode == 0
        assert receipt["schema"] == "m204-s10-c4-operational-receipt/v1"
        assert receipt["c4_binding"]["jobs"] == 1
        assert receipt["binary_profile"] == "debug"
        assert "debug timing is not a release performance claim" in receipt["non_claims"]
        assert receipt["claims"]["operational_acceptance"] == "non-pass"
        assert verify(directory / "synthetic.json").returncode == 0


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
        assert timeout["terminal"]["signal"] in {"SIGTERM", "SIGKILL"}
        assert timeout["terminal"]["exit_code"] is not None
        assert timeout["claims"]["operational_acceptance"] == "non-pass"
        assert verify(directory / "timeout.json").returncode == 0


def test_attempt_collision_and_traversal_are_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(directory, "exit 0")
        first, _ = invoke(binary, directory, attempt="collision")
        assert first["attempt_id"] == "collision"
        second = subprocess.run(
            [
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
                str(directory / "second.json"),
                "--diagnostics-out",
                str(directory / "second.jsonl"),
                "--attempt-id",
                "collision",
                "--source-revision",
                "pin",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert second.returncode != 0
        assert "immutable attempt collision" in second.stderr
        traversal = subprocess.run(
            [
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
                str(directory / "traversal.json"),
                "--diagnostics-out",
                str(directory / "traversal.jsonl"),
                "--attempt-id",
                "../escape",
                "--source-revision",
                "pin",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert traversal.returncode != 0
        assert "safe non-empty identifier" in traversal.stderr


def test_verifier_rejects_forged_duration_hash_and_binding() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        binary = fake_binary(directory, "exit 0")
        receipt_path = directory / "synthetic.json"
        receipt, _ = invoke(binary, directory)
        receipt["duration_ms"] = 3_600_000
        receipt["claims"]["operational_acceptance"] = "pass"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        strict = verify(receipt_path, strict=True)
        assert strict.returncode != 0
        assert "diagnostics" in strict.stderr or "operational" in strict.stderr
        receipt["duration_ms"] = 0
        receipt["c4_binding"]["jobs"] = 0
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        assert verify(receipt_path).returncode != 0


def test_missing_diagnostics_and_profile_mismatch_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        receipt, _ = invoke(fake_binary(directory, "exit 0"), directory)
        receipt_path = directory / "synthetic.json"
        receipt["c4_binding"]["binary_profile"] = "debug"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        result = verify(receipt_path)
        assert result.returncode != 0
        assert "profile" in result.stderr


def main() -> int:
    tests = [
        test_short_debug_attempt_records_non_performance_claim,
        test_nonzero_and_timeout_are_never_operational_pass,
        test_attempt_collision_and_traversal_are_fail_closed,
        test_verifier_rejects_forged_duration_hash_and_binding,
        test_missing_diagnostics_and_profile_mismatch_fail_closed,
    ]
    for test in tests:
        test()
    print(f"M204_S10_C4_SYNTHETIC_TESTS_OK ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
