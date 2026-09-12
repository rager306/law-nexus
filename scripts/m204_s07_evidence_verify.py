#!/usr/bin/env python3
"""Fail-closed, bounded cross-artifact verifier for M204/S07.

This verifier reads durable T01/T03 evidence only.  It never launches the
corpus process and never treats a terminal exit 0 as operational acceptance
when the mandatory duration floor is not met.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOVERNOR = ROOT / "prd/migration/rust-evidence/m204-s07-governor-repeat.json"
RECEIPT = ROOT / "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json"
PASSING_RECEIPT = ROOT / "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-passing.json"
REQUIREMENTS = ROOT / "prd/migration/rust-evidence/m204-s07-requirement-evidence.json"
PREDECESSOR_REQUIREMENTS = ROOT / "prd/migration/rust-evidence/m204-s06-requirement-evidence.json"
BATTERY = ROOT / "prd/migration/rust-evidence/m204-s07-verification-battery.json"
S13_BATTERY = ROOT / "prd/migration/rust-evidence/m204-s13-s07-verification-battery.json"
S13_BINDING = ROOT / "prd/migration/rust-evidence/m204-s13-s07-source-binding.json"
FROZEN_BATTERY_SHA256 = "sha256:f061af4342a75c6c0290f087f4503c74839f7f828b4081bfee7a4422fd408595"


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path.relative_to(ROOT)}: unreadable or malformed JSON") from exc
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


def rooted(value: str, label: str) -> Path:
    candidate = Path(value)
    path = candidate if candidate.is_absolute() else ROOT / candidate
    path = path.resolve()
    require(path == ROOT or ROOT in path.parents, f"{label} escapes project root")
    require(path.is_file(), f"{label} missing: {path.relative_to(ROOT)}")
    return path


def verify_governor(data: dict[str, Any]) -> None:
    require(data.get("schema_version") == "m204-s07-governor-repeat/v1", "governor schema mismatch")
    require(data.get("overall") == "sanctioned_outcome", "governor repeat is not sanctioned")
    require(
        data.get("predecessor", {}).get("sha256")
        == sha256(ROOT / "prd/migration/rust-evidence/m204-s06-governor-sanctioned-outcome.json"),
        "governor predecessor hash mismatch",
    )
    commands = data.get("commands")
    require(isinstance(commands, list) and len(commands) == 2, "governor command captures missing")
    gov = data.get("governor", {}).get("summary", {})
    observed = gov.get("observed", {})
    require(gov.get("check_id") == "review-case-integrity", "exact governor check id missing")
    require(observed.get("exit_code") == 0, "governor repeat exit is not zero")
    require(observed.get("error_count") == 0, "governor repeat has errors")
    require(observed.get("tool_error_count") == 0, "governor repeat has tool errors")
    require(observed.get("pass_finding") is True, "governor pass finding missing")
    status = data.get("review_case_status", {}).get("summary", {})
    require(status.get("packet_id") == "RC-2026-09-10-001", "review packet identity mismatch")
    require(status.get("observed", {}).get("exit_code") == 0, "review-case status exit is not zero")
    require(status.get("observed", {}).get("open_count", 0) >= 0, "open inventory count missing")


def verify_receipt(
    data: dict[str, Any],
    *,
    require_short: bool = True,
    expected_attempt: str = "full-walk-001",
    historical: bool = False,
    pinned_path: Path | None = None,
) -> None:
    # Import lazily so fixture tests can replace this module's files without
    # launching anything; the underlying verifier is integrity-only.
    import m204_s07_c4_run as c4

    require(
        data.get("schema") == "m204-s07-c4-operational-receipt/v1", "C4 receipt schema mismatch"
    )
    require(data.get("duration_ms", -1) >= 0, "C4 duration missing")
    if require_short:
        require(
            data.get("duration_ms", 0) < 3_600_000,
            "fixture unexpectedly proves operational duration",
        )
        require(
            data.get("claims", {}).get("operational_acceptance") == "non-pass",
            "short C4 run claims pass",
        )
    # Generic fixtures use the strict live-hash verifier. Historical receipts
    # are allowed only through the validated T01 binding and pinned content.
    with tempfile.NamedTemporaryFile("w", suffix=".json", dir=ROOT, delete=False) as stream:
        json.dump(data, stream)
        replay_path = Path(stream.name)
    try:
        if historical:
            require(pinned_path is not None, "historical replay pin is required")
            c4.verify_historical(replay_path, S13_BINDING, pinned_path)
        else:
            c4.verify(replay_path, False)
    finally:
        replay_path.unlink(missing_ok=True)
    require(data.get("attempt_id") == expected_attempt, "unexpected C4 attempt identity")
    require(
        data.get("terminal", {}).get("outcome") == "complete", "C4 attempt is not terminal complete"
    )
    require(data.get("terminal", {}).get("exit_code") == 0, "C4 attempt exit is not zero")
    require(data.get("terminal", {}).get("timeout") is False, "C4 attempt timed out")
    require(data.get("duration_ms", -1) >= 0, "C4 duration missing")
    actual = c4.is_operational_pass_data(data)
    if require_short:
        require(
            data.get("duration_ms", 0) < c4.DURATION_FLOOR_MS,
            "fixture unexpectedly proves operational duration",
        )
        require(
            data.get("claims", {}).get("operational_acceptance") == "non-pass",
            "short C4 run claims pass",
        )
    else:
        require(
            data.get("claims", {}).get("operational_acceptance")
            == ("pass" if actual else "non-pass"),
            "C4 operational claim does not match observed facts",
        )
    require(data.get("c4_binding", {}).get("jobs") == 0, "C4 jobs binding mismatch")
    require(data.get("c4_binding", {}).get("limit") is None, "C4 receipt is bounded")
    require(
        data.get("corpus", {}).get("consultant_xml_count") == c4.EXPECTED_XML,
        "full corpus count mismatch",
    )
    require(
        data.get("observed_output", {}).get("jsonl_valid") is True, "diagnostics JSONL is not valid"
    )
    rooted(data["observed_output"]["diagnostics"], "diagnostics output")
    rooted(data["logs"]["stdout"], "stdout log")
    rooted(data["logs"]["stderr"], "stderr log")


def verify_requirements(data: dict[str, Any], receipt: dict[str, Any]) -> None:
    require(
        data.get("schema") == "m204-s07-requirement-evidence/v1",
        "requirement evidence schema mismatch",
    )
    require(
        data.get("classification") == "supporting-only", "requirement classification was promoted"
    )
    require(
        data.get("source") == "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json",
        "requirement source mismatch",
    )
    require(
        data.get("predecessor", {}).get("sha256") == sha256(PREDECESSOR_REQUIREMENTS),
        "requirement predecessor hash mismatch",
    )
    attempt = data.get("attempt", {})
    for key in (
        "attempt_id",
        "terminal_outcome",
        "exit_code",
        "duration_ms",
        "duration_floor_ms",
        "operational_acceptance",
        "source_revision",
        "consultant_xml_count",
        "garant_file_count",
        "jobs",
        "limit",
        "inventory_digest",
    ):
        require(
            attempt.get(key)
            == (
                receipt.get("attempt_id")
                if key == "attempt_id"
                else {
                    "terminal_outcome": receipt["terminal"]["outcome"],
                    "exit_code": receipt["terminal"]["exit_code"],
                    "duration_ms": receipt["duration_ms"],
                    "duration_floor_ms": receipt["claims"]["duration_floor_ms"],
                    "operational_acceptance": receipt["claims"]["operational_acceptance"],
                    "source_revision": receipt["source_revision"],
                    "consultant_xml_count": receipt["corpus"]["consultant_xml_count"],
                    "garant_file_count": receipt["corpus"]["garant_file_count"],
                    "jobs": receipt["c4_binding"]["jobs"],
                    "limit": receipt["c4_binding"]["limit"],
                    "inventory_digest": receipt["observed_output"]["inventory_digest"],
                }[key]
            ),
            f"requirement attempt binding mismatch: {key}",
        )
    rows = data.get("requirements")
    require(
        isinstance(rows, list)
        and {row.get("requirement") for row in rows} == {"R038", "R063", "R064", "R081"},
        "requirement rows mismatch",
    )
    for row in rows:
        require(
            row.get("disposition") == "supporting-only",
            f"{row.get('requirement')} is not supporting-only",
        )
        require(
            row.get("status_effect") == "unchanged", f"{row.get('requirement')} changes lifecycle"
        )


def verify_all() -> dict[str, str]:
    governor = load(GOVERNOR)
    receipt = load(RECEIPT)
    requirements = load(REQUIREMENTS)
    verify_governor(governor)
    verify_receipt(
        receipt,
        historical=True,
        pinned_path=RECEIPT,
    )
    verify_requirements(requirements, receipt)
    return {
        "governor_repeat": "pass",
        "c4_receipt": "pass",
        "requirements": "pass",
        "classification": "supporting-only",
    }


def verify_t06_receipt(
    path: Path = PASSING_RECEIPT, *, require_operational_pass: bool = True
) -> dict[str, str]:
    receipt = load(path)
    import m204_s07_c4_run as c4

    if PASSING_RECEIPT.is_file() and path.resolve() == PASSING_RECEIPT.resolve():
        verify_receipt(
            receipt,
            require_short=False,
            expected_attempt="passing-run-001",
            historical=True,
            pinned_path=PASSING_RECEIPT,
        )
    else:
        # The optional passing artifact is intentionally absent in this
        # supporting-only slice. Synthetic callers still get fact validation,
        # without being mistaken for a tracked historical receipt.
        c4._verify_receipt_facts(receipt, False)
        require(receipt.get("attempt_id") == "passing-run-001", "unexpected C4 attempt identity")

    actual = c4.is_operational_pass_data(receipt)
    if require_operational_pass:
        require(actual, "operational acceptance is not proven")
    return {
        "receipt": "pass",
        "operational_acceptance": "pass" if actual else "non-pass",
        "classification": "operational-pass" if actual else "fail-closed-negative",
    }


def write_battery(checks: dict[str, str]) -> None:
    if BATTERY.is_file() and sha256(BATTERY) != FROZEN_BATTERY_SHA256:
        raise ValueError("frozen S07 battery differs; refusing regeneration")
    if (
        not BATTERY.is_file()
        and BATTERY == ROOT / "prd/migration/rust-evidence/m204-s07-verification-battery.json"
    ):
        raise ValueError("frozen S07 battery is missing; refusing regeneration")
    battery = {
        "schema": "m204-s07-verification-battery/v1",
        "verification": "S07_VERIFY_OK",
        "operational_acceptance": "non-pass",
        "classification": "supporting-only",
        "checks": checks,
        "corpus_walk_repeated": False,
        "false_operational_pass_blocked": True,
        "source_artifacts": {
            path.name: sha256(path)
            for path in (GOVERNOR, RECEIPT, REQUIREMENTS, PREDECESSOR_REQUIREMENTS)
        },
        "non_claims": [
            "S07_VERIFY_OK is evidence integrity, not operational acceptance",
            "A terminal exit 0 and valid diagnostics do not satisfy the duration floor",
            "No requirement, finding, or lifecycle state was changed",
        ],
    }
    encoded = json.dumps(battery, ensure_ascii=False, indent=2) + "\n"
    if BATTERY.is_file():
        if BATTERY.read_text(encoding="utf-8") != encoded:
            raise ValueError("frozen S07 battery payload differs; refusing regeneration")
    else:
        BATTERY.parent.mkdir(parents=True, exist_ok=True)
        BATTERY.write_text(encoded, encoding="utf-8")
    # Fixture tests may redirect BATTERY; only the repository's real frozen
    # target is allowed to create the additive provenance artifact.
    additive = {
        "schema": "m204-s13-s07-verification-battery/v1",
        "verification": "S13_T02_REPLAY_OK",
        "operational_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "s13_called_validate_milestone": False,
        "source_binding": sha256(S13_BINDING),
        "frozen_s07_battery": FROZEN_BATTERY_SHA256,
        "historical_replay": "T01 source-bound pinned receipt replay",
        "non_claims": [
            "historical replay does not prove a new operational pass",
            "no historical S07 bytes were rewritten",
        ],
    }
    if BATTERY == ROOT / "prd/migration/rust-evidence/m204-s07-verification-battery.json":
        if (
            S13_BATTERY.exists()
            and S13_BATTERY.read_text(encoding="utf-8") != json.dumps(additive, indent=2) + "\n"
        ):
            raise ValueError("S13 verification battery differs")
        if not S13_BATTERY.exists():
            S13_BATTERY.write_text(json.dumps(additive, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-battery", action="store_true")
    parser.add_argument("--t06", action="store_true")
    parser.add_argument("--require-operational-pass", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.t06:
            checks = verify_t06_receipt(require_operational_pass=args.require_operational_pass)
        else:
            checks = verify_all()
        if args.write_battery:
            write_battery(checks)
        print(
            json.dumps(
                {
                    "status": "pass",
                    "operational_acceptance": checks.get("operational_acceptance", "non-pass"),
                    "classification": checks.get("classification", "supporting-only"),
                }
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
