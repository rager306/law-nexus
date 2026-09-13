#!/usr/bin/env python3
"""Record and verify the source-bound M204/S22 bounded C4 control battery."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
BATTERY = EVIDENCE / "m204-s22-operational-battery.json"
STDOUT = EVIDENCE / "m204-s22-c4-control.stdout.txt"
STDERR = EVIDENCE / "m204-s22-c4-control.stderr.txt"
SCHEMA = "law-nexus/m204-s22-operational-battery/v1"
COMMAND = [
    "cargo",
    "test",
    "-p",
    "ln-consultant-parser",
    "--offline",
    "--locked",
    "-j",
    "1",
    "--test",
    "contour_diagnostics_contract",
]
GENERATED = {BATTERY, STDOUT, STDERR}
TEST_RESULT = re.compile(r"test result: (ok|FAILED)\.\s+(\d+) passed;\s+(\d+) failed")


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def json_load(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def source_paths() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = []
    for value in proc.stdout.splitlines():
        path = (ROOT / value).resolve()
        if path in GENERATED or ".gsd" in path.relative_to(ROOT).parts:
            continue
        if (
            value in {"Cargo.toml", "Cargo.lock"}
            or value.startswith("crates/")
            and (value.endswith(".rs") or value.endswith("Cargo.toml"))
        ):
            paths.append(path)
    named = [
        ROOT / "scripts/m204_s22_liveness.py",
        ROOT / "scripts/m204_s22_battery.py",
        ROOT / "scripts/m204_s22_t01_verify.sh",
        ROOT / "scripts/m204_s22_t03_verify.sh",
        ROOT / "scripts/test_m204_s22_liveness.py",
        ROOT / "scripts/m204_s21_loop_note.py",
        ROOT / "scripts/m204_s15_requirement_class.py",
        ROOT / "prd/migration/rust-evidence/m204-s22-external-blocker.json",
        ROOT / "prd/migration/rust-evidence/m204-s22-frozen-hashes.json",
        ROOT / "prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json",
        ROOT / "prd/migration/rust-evidence/m204-s21-frozen-hashes.json",
        ROOT / "prd/migration/rust-evidence/m204-s14-c4-acceptance.json",
        ROOT / "prd/migration/rust-evidence/m204-s14-verification-battery.json",
        ROOT / "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json",
        ROOT / "prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json",
        ROOT / "doc/review/review-28.md",
        ROOT / "doc/gsd-headless-supervisor.md",
    ]
    paths.extend(named)
    unique = {p for p in paths if p.is_file() and p not in GENERATED}
    if any(".gsd" in p.relative_to(ROOT).parts for p in unique):
        raise ValueError("ignored .gsd path entered source binding")
    return sorted(unique, key=rel)


def binding(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {"path": rel(path), "sha256": digest(path), "size_bytes": path.stat().st_size}
        for path in paths
    ]


def run_control(timeout: int) -> dict[str, Any]:
    if any(path.exists() for path in GENERATED):
        raise ValueError("generated battery or control logs already exist")
    started = utc_now()
    monotonic = time.monotonic()
    try:
        proc = subprocess.run(
            COMMAND, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
        outcome = "complete" if proc.returncode == 0 else "nonzero"
        exit_code: int | None = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        proc_stdout = exc.stdout or ""
        proc_stderr = exc.stderr or ""
        outcome, exit_code, timed_out = "timeout", None, True
        proc = subprocess.CompletedProcess(COMMAND, 124, proc_stdout, proc_stderr)
    except OSError as exc:
        outcome, exit_code, timed_out = "launch_error", None, False
        proc = subprocess.CompletedProcess(COMMAND, 127, "", str(exc))
    duration = int((time.monotonic() - monotonic) * 1000)
    STDOUT.write_text(proc.stdout, encoding="utf-8")
    STDERR.write_text(proc.stderr, encoding="utf-8")
    passed = failed = 0
    matches = TEST_RESULT.findall(proc.stdout + proc.stderr)
    if matches:
        _, passed_text, failed_text = matches[-1]
        passed, failed = int(passed_text), int(failed_text)
    paths = source_paths()
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S22",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "generated_at": started,
        "finished_at": utc_now(),
        "working_directory": ".",
        "argv": COMMAND,
        "cwd": ".",
        "timeout_seconds": timeout,
        "duration_ms": duration,
        "terminal": {"outcome": outcome, "exit_code": exit_code, "timeout": timed_out},
        "toolchain": {
            name: subprocess.run(
                [name, "--version"], cwd=ROOT, capture_output=True, text=True, check=False
            ).stdout.strip()
            for name in ("cargo", "rustc")
        },
        "output": {
            "stdout": rel(STDOUT),
            "stderr": rel(STDERR),
            "stdout_sha256": digest(STDOUT),
            "stderr_sha256": digest(STDERR),
        },
        "test_results": {
            "matched": bool(matches),
            "passed": passed,
            "failed": failed,
            "nonzero_tests": passed + failed,
        },
        "source_binding": {"files": binding(paths)},
        "gsd_recovery_liveness": "blocked-external",
        "c4_control": "pass"
        if outcome == "complete" and exit_code == 0 and passed + failed > 0 and failed == 0
        else "non-pass",
        "c4_operational_acceptance": "non-pass",
        "truthful_revalidation_disposition": "needs-remediation",
        "retry_substitute": False,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "law_nexus_fixable": False,
        "non_claims": [
            "not a VALIDATION record",
            "not an engine repair authorization",
            "does not close R035 or R070",
            "does not claim GSD aggregate testedSourceRevision",
        ],
    }
    BATTERY.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check() -> None:
    require(
        BATTERY.is_file() and STDOUT.is_file() and STDERR.is_file(),
        "battery or control log missing",
    )
    doc = json_load(BATTERY)
    require(doc.get("schema") == SCHEMA, "battery schema mismatch")
    require(doc.get("argv") == COMMAND and doc.get("cwd") == ".", "argv or cwd binding mismatch")
    require(
        doc.get("c4_operational_acceptance") == "non-pass", "operational acceptance was promoted"
    )
    require(
        doc.get("classification") == "supporting-only" and doc.get("status_effect") == "unchanged",
        "lifecycle promotion",
    )
    require(
        doc.get("gsd_recovery_liveness") == "blocked-external"
        and doc.get("retry_substitute") is False,
        "recovery conflation",
    )
    terminal, results = doc.get("terminal", {}), doc.get("test_results", {})
    expected_control = (
        terminal.get("outcome") == "complete"
        and terminal.get("exit_code") == 0
        and results.get("nonzero_tests", 0) > 0
        and results.get("failed") == 0
    )
    require(
        doc.get("c4_control") == ("pass" if expected_control else "non-pass"),
        "forged control result",
    )
    require(
        doc["output"]["stdout_sha256"] == digest(STDOUT)
        and doc["output"]["stderr_sha256"] == digest(STDERR),
        "control log drift",
    )
    for row in doc.get("source_binding", {}).get("files", []):
        path = ROOT / row["path"]
        require(
            path.is_file()
            and digest(path) == row["sha256"]
            and path.stat().st_size == row["size_bytes"],
            f"source drift: {row.get('path')}",
        )
    require(
        not any(".gsd" in row["path"].split("/") for row in doc["source_binding"]["files"]),
        "ignored source binding",
    )
    subprocess.run(["bash", "scripts/m204_s22_t01_verify.sh"], cwd=ROOT, check=True)
    subprocess.run(
        [sys.executable, "-m", "unittest", "scripts/test_m204_s22_liveness.py"],
        cwd=ROOT,
        check=True,
    )
    s21 = subprocess.run(
        [
            sys.executable,
            "scripts/m204_s21_loop_note.py",
            "check",
            "--root",
            str(ROOT),
            "--census",
            str(EVIDENCE / "m204-s21-post-s20-validate-loop.json"),
            "--manifest",
            str(EVIDENCE / "m204-s21-frozen-hashes.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    require(
        s21.returncode == 0 and "S21_T01_CENSUS_OK" in s21.stdout, "independent S21 consumer failed"
    )
    s15 = subprocess.run(
        [sys.executable, "scripts/m204_s15_requirement_class.py", "classify"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    require(s15.returncode == 0 and not s15.stderr, "independent S15 consumer failed")
    observed = json.loads(s15.stdout)
    require(
        observed.get("c4_acceptance") == "non-pass" and observed.get("class_matched_ids") == [],
        "S15 polarity drift",
    )
    print("S22_T03_VERIFY_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "check"))
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    try:
        if args.command == "run":
            doc = run_control(args.timeout)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "c4_control": doc["c4_control"],
                        "duration_ms": doc["duration_ms"],
                    },
                    sort_keys=True,
                )
            )
        else:
            check()
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"m204_s22_battery: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
