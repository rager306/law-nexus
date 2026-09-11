#!/usr/bin/env python3
"""Capture and verify a fresh, process-only S07 governor repeat.

The adapter intentionally does not change governor or Review Case state.  Open
findings remain observable inventory; only failures belonging to this exact
check or its status command produce ``blocked_scope``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "prd/migration/rust-evidence/m204-s07-governor-repeat.json"
PREDECESSOR = ROOT / "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json"
PACKET_ID = "RC-2026-09-10-001"
CHECK_ID = "review-case-integrity"
SCHEMA_VERSION = "m204-s07-governor-repeat/v1"
CommandRunner = Callable[[Sequence[str], Path, float], tuple[int, str, str]]


def _run(argv: Sequence[str], cwd: Path, timeout: float = 120.0) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            list(argv), cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", errors="replace")
        return 124, out, f"timeout: {err}".strip()
    except OSError as exc:
        return 127, "", f"exec error: {exc}"


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _parse(stdout: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label}: malformed JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}: report must be a JSON object")
    return value


def _governor_summary(report: dict[str, Any], exit_code: int) -> dict[str, Any]:
    if report.get("schema_version") != "law-nexus-governor-report/v1":
        raise ValueError("governor report has unexpected schema_version")
    findings = report.get("findings")
    if not isinstance(findings, list) or not all(isinstance(x, dict) for x in findings):
        raise ValueError("governor report missing findings list")
    selected = [x for x in findings if x.get("check_id") == CHECK_ID]
    if not selected:
        raise ValueError(f"governor report has no exact {CHECK_ID} finding")

    def integer(name: str) -> int:
        value = report.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"governor report missing non-negative integer {name}")
        return value

    errors, tool_errors = integer("error_count"), integer("tool_error_count")
    pass_finding = any(x.get("status") == "pass" for x in selected)
    blocked = (
        exit_code != 0 or report.get("status") != "ok" or errors or tool_errors or not pass_finding
    )
    return {
        "status": "blocked_scope" if blocked else "governor_pass",
        "check_id": CHECK_ID,
        "observed": {
            "exit_code": exit_code,
            "report_status": report.get("status"),
            "error_count": errors,
            "tool_error_count": tool_errors,
            "pass_finding": pass_finding,
            "finding_count": len(selected),
        },
        "findings": selected,
        "remediation": "Inspect this check's failure; no lifecycle mutation is performed."
        if blocked
        else "none; open findings remain advisory inventory",
    }


def _status_summary(report: dict[str, Any], exit_code: int) -> dict[str, Any]:
    if report.get("schema_version") != "review-case-cli-report/v1":
        raise ValueError("status report has unexpected schema_version")
    result = report.get("result")
    packets = result.get("packets") if isinstance(result, dict) else None
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != "review-case-application-report/v1"
    ):
        raise ValueError("status report missing application result")
    if (
        not isinstance(packets, list)
        or len(packets) != 1
        or not isinstance(packets[0], list)
        or len(packets[0]) != 5
        or packets[0][0] != PACKET_ID
    ):
        raise ValueError("status report packet identity mismatch")
    entries = packets[0][4]
    if not isinstance(entries, list) or not all(
        isinstance(x, list) and len(x) == 2 for x in entries
    ):
        raise ValueError("status report has malformed finding statuses")
    findings = [{"finding_id": x[0], "status": x[1]} for x in entries]
    blocked = exit_code != 0 or report.get("status") != "ok" or bool(result.get("open_blockers"))
    return {
        "status": "blocked_scope" if blocked else "status_observed",
        "packet_id": PACKET_ID,
        "observed": {
            "exit_code": exit_code,
            "report_status": report.get("status"),
            "open_blockers": result.get("open_blockers"),
            "finding_count": len(findings),
            "open_count": sum(x["status"] == "open" for x in findings),
        },
        "findings": findings,
        "remediation": "Inspect status command failure; no lifecycle mutation is performed."
        if blocked
        else "none",
    }


def capture(
    *,
    runner: CommandRunner = _run,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    commands = [
        [
            "uv",
            "run",
            "python",
            "-m",
            "law_nexus_harness",
            "governor",
            "--check",
            CHECK_ID,
            "--format",
            "json",
        ],
        [
            "uv",
            "run",
            "python",
            "-m",
            "law_nexus_harness",
            "review-case",
            "status",
            "--packet-id",
            PACKET_ID,
        ],
    ]
    started_clock = clock()
    captured = []
    for argv in commands:
        started = now().astimezone(UTC).isoformat().replace("+00:00", "Z")
        exit_code, stdout, stderr = runner(argv, ROOT, 120.0)
        captured.append(
            {
                "argv": list(argv),
                "started_at_utc": started,
                "finished_at_utc": now().astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
    parsed: list[dict[str, Any] | None] = []
    summaries: list[dict[str, Any]] = []
    for index, (label, item, fn) in enumerate(
        (
            ("governor", captured[0], _governor_summary),
            ("review-case status", captured[1], _status_summary),
        )
    ):
        try:
            report = _parse(item["stdout"], label)
            parsed.append(report)
            summaries.append(fn(report, item["exit_code"]))
        except ValueError as exc:
            parsed.append(None)
            summaries.append(
                {
                    "status": "blocked_scope",
                    "error": str(exc),
                    "check_id": CHECK_ID if index == 0 else None,
                    "packet_id": PACKET_ID if index == 1 else None,
                }
            )
    gov, status = summaries
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at_utc": now().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "duration_ms": max(0, round((clock() - started_clock) * 1000)),
        "scope": "fresh live repeat of review-case-integrity and RC-2026-09-10-001 status",
        "predecessor": {"path": str(PREDECESSOR.relative_to(ROOT)), "sha256": sha256(PREDECESSOR)},
        "non_claims": [
            "Supporting evidence only; no requirement closure",
            "Open findings remain advisory inventory and are not accepted",
            "No findings, packet, ledger, requirement, or lifecycle mutation",
        ],
        "commands": captured,
        "parsed_reports": parsed,
        "governor": {"summary": gov},
        "review_case_status": {"summary": status},
        "overall": "blocked_scope"
        if gov["status"] == "blocked_scope" or status["status"] == "blocked_scope"
        else "sanctioned_outcome",
    }


def validate_artifact(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("artifact schema_version mismatch")
    if payload.get("overall") not in {"sanctioned_outcome", "blocked_scope"}:
        raise ValueError("artifact outcome missing")
    if payload.get("predecessor", {}).get("sha256") != sha256(PREDECESSOR):
        raise ValueError("predecessor hash mismatch")
    commands = payload.get("commands")
    if not isinstance(commands, list) or len(commands) != 2:
        raise ValueError("exactly two command captures required")
    expected = [
        [
            "uv",
            "run",
            "python",
            "-m",
            "law_nexus_harness",
            "governor",
            "--check",
            CHECK_ID,
            "--format",
            "json",
        ],
        [
            "uv",
            "run",
            "python",
            "-m",
            "law_nexus_harness",
            "review-case",
            "status",
            "--packet-id",
            PACKET_ID,
        ],
    ]
    if [x.get("argv") for x in commands] != expected:
        raise ValueError("fixed argv mismatch")
    gov = payload.get("governor", {}).get("summary", {})
    if gov.get("check_id") != CHECK_ID:
        raise ValueError("exact check_id missing")
    observed = gov.get("observed", {})
    if payload["overall"] == "sanctioned_outcome" and (
        observed.get("exit_code") != 0
        or observed.get("error_count") != 0
        or observed.get("tool_error_count") != 0
        or not observed.get("pass_finding")
    ):
        raise ValueError("success artifact has invalid governor outcome")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        if args.check:
            value = json.loads(args.output.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("durable artifact must be a JSON object")
            validate_artifact(value)
        else:
            value = capture()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(
            json.dumps(
                {"status": "pass", "artifact": str(args.output), "overall": value["overall"]}
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
