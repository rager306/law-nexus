#!/usr/bin/env python3
"""Fail-closed, bounded verifier for M204/S06 evidence artifacts.

This helper validates durable bytes and provenance only. It deliberately does
not execute the corpus walker, mutate findings, or infer runtime acceptance from
budget_seconds or documentation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOVERNOR = ROOT / "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json"
RECEIPT = ROOT / "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json"
REQUIREMENTS = ROOT / "prd/migration/rust-evidence/m204-s06-requirement-evidence.json"
WAIVER = ROOT / "prd/migration/rust-evidence/m204-s05-m073-residue-waiver.json"
BATTERY = ROOT / "prd/migration/rust-evidence/m204-s06-verification-battery.json"


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path.relative_to(ROOT)}: unreadable or malformed JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)}: expected JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def rooted(rel_or_abs: str, label: str) -> Path:
    candidate = Path(rel_or_abs)
    path = candidate if candidate.is_absolute() else ROOT / candidate
    path = path.resolve()
    require(path == ROOT or ROOT in path.parents, f"{label} escapes project root")
    require(path.is_file(), f"{label} missing: {path.relative_to(ROOT)}")
    return path


def parse_time(value: str, label: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} is not an ISO timestamp") from exc


def verify_governor(data: dict[str, Any]) -> None:
    require(
        data.get("schema_version") == "m204-s06-governor-sanctioned-outcome/v1",
        "governor schema mismatch",
    )
    require(
        data.get("overall") in {"sanctioned_outcome", "blocked_scope"},
        "governor outcome is not explicit",
    )
    summary = data.get("governor", {}).get("summary", {})
    observed = summary.get("observed", {})
    require(summary.get("check_id") == "review-case-integrity", "governor check id mismatch")
    require(
        isinstance(observed.get("error_count"), int) and observed["error_count"] >= 0,
        "governor error_count missing",
    )
    require(isinstance(observed.get("pass_count"), int), "governor pass_count missing")
    require(isinstance(observed.get("warn_count"), int), "governor warn_count missing")
    require(isinstance(observed.get("open_count"), int), "governor open_count missing")
    require(
        data.get("review_case_status", {}).get("summary", {}).get("packet_id")
        == "RC-2026-09-10-001",
        "review packet mismatch",
    )
    require(
        any("no requirement closure" in str(item).lower() for item in data.get("non_claims", [])),
        "governor closure non-claim missing",
    )


def verify_receipt(data: dict[str, Any]) -> None:
    require(
        data.get("schema") == "m204-s06-c4-operational-receipt/v1", "C4 receipt schema mismatch"
    )
    require(
        isinstance(data.get("argv"), list)
        and data["argv"]
        and all(isinstance(x, str) and x for x in data["argv"]),
        "complete argv array missing",
    )
    require(data["argv"][0].startswith("/"), "argv does not pin an executable path")
    require(
        data.get("attempt_id") == data.get("immutable_attempt_identity", {}).get("attempt_id"),
        "attempt identity mismatch",
    )
    require(
        data.get("source_revision") and not str(data["source_revision"]).startswith("sha256:"),
        "caller source pin missing or confused with aggregate",
    )
    require(
        data.get("contract", {}).get("check_id") == "c4-live-check"
        and data["contract"].get("mode") == "runtime",
        "runtime C4 contract binding missing",
    )
    require(
        data["contract"].get("version") == "npa-acceptance-contract/v1", "contract version missing"
    )
    require(
        isinstance(data.get("budget_seconds"), int) and data["budget_seconds"] >= 3600,
        "budget is below pinned minimum",
    )
    require(
        isinstance(data.get("duration_ms"), int) and data["duration_ms"] >= 0, "duration missing"
    )
    started = parse_time(data.get("started_at", ""), "started_at")
    finished = parse_time(data.get("finished_at", ""), "finished_at")
    require(finished >= started, "finish precedes start")
    terminal = data.get("terminal", {})
    outcome = terminal.get("outcome")
    require(
        outcome in {"complete", "nonzero", "timeout", "launch_error", "not-run"},
        "unknown terminal outcome",
    )
    if outcome == "complete":
        require(
            terminal.get("exit_code") == 0 and not terminal.get("timeout"),
            "complete has nonzero or timeout state",
        )
    if outcome == "timeout":
        require(
            terminal.get("timeout") is True and terminal.get("signal"),
            "timeout lacks terminal signal",
        )
    require(
        data.get("claims", {}).get("operational_acceptance") in {"pass", "non-pass", "unverified"},
        "operational acceptance missing",
    )
    if outcome != "complete" or data["duration_ms"] < data["budget_seconds"] * 1000:
        require(
            data["claims"]["operational_acceptance"] != "pass",
            "non-terminal or under-budget run cannot claim pass",
        )
    binary = data.get("binary", {})
    build = data.get("build_inputs", {})
    require(binary.get("sha256", "").startswith("sha256:"), "binary hash missing")
    require(build.get("binary_sha256") == binary.get("sha256"), "binary provenance hash mismatch")
    require(
        build.get("contract_sha256") == data["contract"].get("sha256"),
        "contract provenance hash mismatch",
    )
    for name in ("stdout", "stderr"):
        value = data.get("logs", {}).get(name)
        if value is not None:
            rooted(value, f"{name} log")
            require(
                data["logs"].get(name + "_sha256", "").startswith("sha256:"),
                f"{name} log hash missing",
            )
    require(
        data.get("corpus", {}).get("consultant_root") == "consru_export/consru_export/exports",
        "wrong consultant corpus root",
    )
    require(
        data.get("corpus", {}).get("consultant_xml_count") == 43785,
        "pinned consultant corpus count mismatch",
    )
    require(
        data.get("c4_binding", {}).get("limit") is None,
        "full operational receipt must not claim a bounded limit",
    )


def verify_requirements(data: dict[str, Any]) -> None:
    require(
        data.get("schema") == "m204-s06-requirement-evidence/v1",
        "requirement evidence schema mismatch",
    )
    rows = data.get("requirements")
    require(
        isinstance(rows, list)
        and {row.get("requirement_id") for row in rows} == {"R038", "R063", "R064", "R081"},
        "requirement rows mismatch",
    )
    for row in rows:
        require(
            row.get("disposition") == "supporting-only",
            f"{row.get('requirement_id')} is not supporting-only",
        )
        require(
            row.get("status_effect", "").startswith("unchanged-"),
            f"{row.get('requirement_id')} changes lifecycle",
        )
        require(row.get("concrete_paths"), f"{row.get('requirement_id')} has no evidence paths")
        for path in row["concrete_paths"]:
            rooted(path, f"{row['requirement_id']} evidence path")
    require(
        "operational-acceptance-non-pass" in data.get("overall_disposition", ""),
        "requirements do not record non-pass",
    )
    receipt_row = next(row for row in rows if row["requirement_id"] == "R038")
    require(
        receipt_row["observed_outcome"].get("operational_acceptance") != "pass",
        "R038 falsely claims operational pass",
    )


def verify_waiver(data: dict[str, Any]) -> None:
    require(data.get("kind") == "documentation-only-waiver", "historical waiver kind changed")
    disposition = data.get("disposition", {})
    require(
        disposition.get("engine_waiver") is False
        and disposition.get("lifecycle_mutation") is False,
        "historical waiver promoted",
    )


def verify_all() -> dict[str, Any]:
    governor = load(GOVERNOR)
    receipt = load(RECEIPT)
    requirements = load(REQUIREMENTS)
    waiver = load(WAIVER)
    verify_governor(governor)
    verify_receipt(receipt)
    verify_requirements(requirements)
    verify_waiver(waiver)
    return {
        "governor": "pass",
        "c4_receipt": "pass",
        "requirements": "pass",
        "frozen_waiver": "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-battery", action="store_true")
    parser.add_argument("--output", type=Path, default=BATTERY)
    args = parser.parse_args()
    try:
        checks = verify_all()
        if args.write_battery:
            payload = {
                "schema": "m204-s06-verification-battery/v1",
                "verification": "S06_VERIFY_OK",
                "operational_acceptance": load(RECEIPT)["claims"]["operational_acceptance"],
                "checks": checks,
                "bounded": True,
                "corpus_walk_repeated": False,
                "source_artifacts": {
                    p.name: sha256(p) for p in (GOVERNOR, RECEIPT, REQUIREMENTS, WAIVER)
                },
                "non_claims": [
                    "Evidence integrity is not product acceptance",
                    "No requirement or finding lifecycle was changed",
                ],
            }
            args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "pass",
                    "checks": checks,
                    "battery": str(args.output) if args.write_battery else None,
                }
            )
        )
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
