#!/usr/bin/env python3
"""Capture and verify the sanctioned M204 review-case governor outcome.

This is deliberately a process-only evidence adapter. It does not interpret or
mutate findings, packets, requirements, or lifecycle state.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json"
PACKET_ID = "RC-2026-09-10-001"
CHECK_ID = "review-case-integrity"
SCHEMA_VERSION = "m204-s06-governor-sanctioned-outcome/v1"

CommandRunner = Callable[[Sequence[str], Path, float], tuple[int, str, str]]


def _run(argv: Sequence[str], cwd: Path, timeout: float = 120.0) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            list(argv), cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return 124, stdout, f"timeout: {stderr}".strip()
    except OSError as exc:
        return 127, "", f"exec error: {exc}"


def _json_report(stdout: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label}: malformed JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}: report must be a JSON object")
    return value


def _int_field(report: dict[str, Any], name: str) -> int:
    value = report.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"governor report missing non-negative integer {name}")
    return value


def _open_count_from_findings(findings: list[dict[str, Any]]) -> int:
    # Open is an observed inventory value, not an advisory/error conversion.
    # Prefer the machine-readable observed field supplied by the report.
    for finding in findings:
        match = re.search(r"(?:^|[, ])open_count=(\d+)", str(finding.get("observed", "")))
        if match:
            return int(match.group(1))
    raise ValueError("governor report has no machine-readable open_count")


def summarize_governor(report: dict[str, Any], exit_code: int) -> dict[str, Any]:
    if report.get("schema_version") != "law-nexus-governor-report/v1":
        raise ValueError("governor report has unexpected schema_version")
    findings = report.get("findings")
    if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
        raise ValueError("governor report missing findings list")
    selected = [item for item in findings if item.get("check_id", "").startswith(CHECK_ID)]
    if not selected:
        raise ValueError(f"governor report has no {CHECK_ID} findings")
    errors = _int_field(report, "error_count")
    passes = _int_field(report, "pass_count")
    warns = _int_field(report, "warn_count")
    open_count = _open_count_from_findings(selected)
    blocked = exit_code != 0 or errors > 0 or report.get("status") != "ok"
    return {
        "status": "blocked_scope" if blocked else "sanctioned_integrity_pass",
        "check_id": CHECK_ID,
        "observed": {
            "exit_code": exit_code,
            "report_status": report["status"],
            "error_count": errors,
            "pass_count": passes,
            "warn_count": warns,
            "open_count": open_count,
            "finding_count": len(selected),
        },
        "findings": [
            {
                "check_id": item.get("check_id"),
                "status": item.get("status"),
                "severity": item.get("severity"),
                "message": item.get("message"),
                "observed": item.get("observed"),
                "remediation": item.get("remediation"),
                "rule_id": item.get("rule_id"),
            }
            for item in selected
        ],
        "remediation": (
            "Inspect the exact governor error findings and rerun the bounded check; "
            "do not infer acceptance from open findings."
            if blocked
            else "none; open findings remain advisory inventory and require human disposition"
        ),
    }


def summarize_status(report: dict[str, Any], exit_code: int) -> dict[str, Any]:
    if report.get("schema_version") != "review-case-cli-report/v1":
        raise ValueError("status report has unexpected schema_version")
    result = report.get("result")
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != "review-case-application-report/v1"
    ):
        raise ValueError("status report missing application result")
    packets = result.get("packets")
    if not isinstance(packets, list) or len(packets) != 1:
        raise ValueError("status report must contain exactly one packet")
    packet = packets[0]
    if not isinstance(packet, list) or len(packet) != 5 or packet[0] != PACKET_ID:
        raise ValueError("status report packet identity mismatch")
    entries = packet[4]
    if not isinstance(entries, list) or not all(
        isinstance(item, list) and len(item) == 2 for item in entries
    ):
        raise ValueError("status report has malformed finding statuses")
    findings = [{"finding_id": item[0], "status": item[1]} for item in entries]
    blocked = exit_code != 0 or report.get("status") != "ok" or bool(result.get("open_blockers"))
    return {
        "status": "blocked_scope" if blocked else "status_observed",
        "packet_id": PACKET_ID,
        "observed": {
            "exit_code": exit_code,
            "report_status": report["status"],
            "open_blockers": result.get("open_blockers"),
            "finding_count": len(findings),
            "open_count": sum(item["status"] == "open" for item in findings),
        },
        "findings": findings,
        "remediation": "Inspect packet/status command failure; no lifecycle mutation is performed."
        if blocked
        else "none",
    }


def capture(
    *, runner: CommandRunner = _run, now: Callable[[], datetime] = lambda: datetime.now(UTC)
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
    captured: list[dict[str, Any]] = []
    for argv in commands:
        exit_code, stdout, stderr = runner(argv, ROOT, 120.0)
        captured.append(
            {"argv": list(argv), "exit_code": exit_code, "stdout": stdout, "stderr": stderr}
        )
    governor = _json_report(captured[0]["stdout"], "governor")
    status = _json_report(captured[1]["stdout"], "review-case status")
    outcome = summarize_governor(governor, captured[0]["exit_code"])
    status_summary = summarize_status(status, captured[1]["exit_code"])
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at_utc": now().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "scope": "review-case integrity and RC-2026-09-10-001 status only",
        "non_claims": [
            "Supporting evidence for R081 only; no requirement closure",
            "Open findings are not automatically advisory or accepted; severity/check semantics are retained",
            "No findings, packet, ledger, requirement, or lifecycle mutation",
        ],
        "commands": captured,
        "governor": {"summary": outcome, "raw_report": governor},
        "review_case_status": {"summary": status_summary, "raw_report": status},
        "overall": "blocked_scope"
        if outcome["status"] == "blocked_scope" or status_summary["status"] == "blocked_scope"
        else "sanctioned_outcome",
    }


def validate_artifact(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("artifact schema_version mismatch")
    if payload.get("overall") not in {"sanctioned_outcome", "blocked_scope"}:
        raise ValueError("artifact missing valid overall outcome")
    governor = payload.get("governor", {}).get("summary", {})
    status = payload.get("review_case_status", {}).get("summary", {})
    if governor.get("check_id") != CHECK_ID or status.get("packet_id") != PACKET_ID:
        raise ValueError("artifact scope identity mismatch")
    if (
        payload["overall"] == "sanctioned_outcome"
        and governor.get("observed", {}).get("error_count", 1) > 0
    ):
        raise ValueError("success artifact cannot contain governor errors")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the existing durable artifact without running commands or writing files",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        if args.check:
            # Check mode is intentionally read-only.  The host source-integrity
            # verifier may run concurrently, so recapturing reports or rewriting
            # the tracked artifact here would create a false source change.
            payload = json.loads(args.output.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("durable artifact must be a JSON object")
            validate_artifact(payload)
        else:
            payload = capture()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(
            json.dumps(
                {"status": "pass", "artifact": str(args.output), "overall": payload["overall"]}
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
