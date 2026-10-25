"""Guard for the M221/S05 re-acceptance readiness battery.

``prd/migration/rust-evidence/m221-s05-readiness-battery.json`` is the tracked
count/hash-only receipt of the S05 re-acceptance: it re-runs the relevant
S01-S04 suites, recaps the three S04 verdicts, states the downstream/parked
readiness posture, and pins the source artifacts it was derived from.

A green battery is **not** requirement closure and **not** a readiness
percentage (MEM1859). The invariants enforced here keep that honest:

* ``count_only`` / ``ascii_only`` stay true and ``promotion`` stays false;
* ``verdict_recap`` matches ``m221-s04-acceptance.json["verdicts"]`` exactly;
* ``f_findings`` covers F01-F06 and F06 is ``closed-bounded-under-S05``;
* every re-run recorded in ``re_test_set`` exited 0;
* every ``source_bindings`` sha256 still resolves to a local tracked file;
* no absolute path or parent traversal appears anywhere in the battery;
* ``non_claims`` is present and non-empty.

The test reads only local tracked files under ``prd/migration/rust-evidence``
and ``prd/architecture``; there is no network access and no subprocess.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BATTERY_PATH = REPO_ROOT / "prd" / "migration" / "rust-evidence" / "m221-s05-readiness-battery.json"
RECEIPT_PATH = REPO_ROOT / "prd" / "migration" / "rust-evidence" / "m221-s04-acceptance.json"

SCHEMA = "law-nexus/m221-s05-readiness-battery/v1"
EXPECTED_FINDINGS = frozenset({"F01", "F02", "F03", "F04", "F05", "F06"})
EXPECTED_VERDICT_RECAP = {
    "transport_integrity": "pass",
    "analysis_completion": "incomplete",
    "semantic_acceptance": "not_attempted",
}
EXPECTED_READINESS = {
    "m208": "parked",
    "m215_m220": "parked",
    "r1000": "active_unclosed",
}
EXPECTED_RETEST_COUNT = 8


class BatteryContractError(AssertionError):
    """Raised when the readiness battery violates its contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BatteryContractError(message)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Any:
    _require(path.is_file(), f"missing artifact: {path.relative_to(REPO_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_battery() -> dict[str, Any]:
    loaded = _load_json(BATTERY_PATH)
    _require(isinstance(loaded, dict), "battery must load as a mapping")
    return loaded


def _load_receipt() -> dict[str, Any]:
    loaded = _load_json(RECEIPT_PATH)
    _require(isinstance(loaded, dict), "S04 receipt must load as a mapping")
    return loaded


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def validate_battery(battery: dict[str, Any], receipt: dict[str, Any]) -> None:
    """Validate the battery contract in memory (raises BatteryContractError)."""
    _require(battery.get("schema") == SCHEMA, "unexpected battery schema")
    _require(battery.get("milestone") == "M221-wbslul", "battery milestone must be M221-wbslul")
    _require(battery.get("slice") == "S05", "battery slice must be S05")
    _require(battery.get("count_only") is True, "count_only must stay true")
    _require(battery.get("ascii_only") is True, "ascii_only must stay true")
    _require(battery.get("promotion") is False, "promotion must stay false")
    _require(bool(battery.get("recordedAt")), "battery must record recordedAt")

    # F01-F06 coverage and the bounded F06 disposition.
    findings = battery.get("f_findings") or []
    _require(isinstance(findings, list), "f_findings must be a list")
    ids = {finding.get("id") for finding in findings if isinstance(finding, dict)}
    _require(
        ids == EXPECTED_FINDINGS,
        f"f_findings must cover F01-F06; got {sorted(i for i in ids if i)}",
    )
    f06 = next(
        finding for finding in findings if isinstance(finding, dict) and finding.get("id") == "F06"
    )
    _require(
        f06.get("status") == "closed-bounded-under-S05",
        "F06 must be closed-bounded-under-S05",
    )

    # verdict_recap must match the frozen S04 receipt exactly.
    recap = battery.get("verdict_recap")
    _require(
        recap == receipt.get("verdicts"), "verdict_recap must match m221-s04-acceptance verdicts"
    )
    _require(recap == EXPECTED_VERDICT_RECAP, "verdict_recap must keep the three S04 verdicts")

    _require(battery.get("readiness") == EXPECTED_READINESS, "readiness posture drifted")

    tests = battery.get("re_test_set") or []
    _require(isinstance(tests, list), "re_test_set must be a list")
    _require(
        len(tests) == EXPECTED_RETEST_COUNT,
        f"re_test_set must record {EXPECTED_RETEST_COUNT} suites, got {len(tests)}",
    )
    for entry in tests:
        _require(isinstance(entry, dict), "re_test_set entries must be mappings")
        _require(bool(entry.get("command")), "re_test_set entry needs a command")
        _require(entry.get("exitCode") == 0, f"re_test_set exit was not 0: {entry.get('command')}")

    # Every binding must resolve to a local tracked file with a matching hash.
    bindings = battery.get("source_bindings") or []
    _require(isinstance(bindings, list) and bindings, "source_bindings must be non-empty")
    for binding in bindings:
        _require(isinstance(binding, dict), "source_bindings entries must be mappings")
        rel = binding.get("path")
        _require(isinstance(rel, str) and rel, "source_bindings entry needs a path")
        _require(not rel.startswith("/"), f"absolute path in source binding: {rel}")
        _require(".." not in Path(rel).parts, f"parent traversal in source binding: {rel}")
        target = REPO_ROOT / rel
        _require(target.is_file(), f"missing source binding: {rel}")
        _require(
            binding.get("sha256") == _sha256_file(target),
            f"sha256 drift for source binding: {rel}",
        )

    # No absolute path or parent traversal anywhere in the battery payload.
    for text in _iter_strings(battery):
        _require(not text.startswith("/"), f"absolute path in battery payload: {text!r}")
        _require(".." not in text, f"parent traversal in battery payload: {text!r}")

    _require(bool(battery.get("non_claims")), "non_claims must be non-empty")


# --- positive contract ------------------------------------------------------


def test_battery_contract() -> None:
    validate_battery(_load_battery(), _load_receipt())


def test_battery_file_is_ascii() -> None:
    raw = BATTERY_PATH.read_bytes()
    _require(all(byte < 128 for byte in raw), "battery file must be ASCII-only")


def test_source_bindings_resolve_and_match_disk() -> None:
    battery = _load_battery()
    for binding in battery.get("source_bindings") or []:
        target = REPO_ROOT / binding["path"]
        _require(
            binding["sha256"] == _sha256_file(target),
            f"sha256 drift for source binding: {binding['path']}",
        )


def test_verdict_recap_matches_frozen_s04_receipt() -> None:
    battery = _load_battery()
    receipt = _load_receipt()
    _require(
        battery.get("verdict_recap") == receipt.get("verdicts"),
        "verdict_recap must match m221-s04-acceptance verdicts",
    )


# --- hostile / fail-closed coverage -----------------------------------------


def test_corrupted_binding_hash_is_rejected() -> None:
    battery = _load_battery()
    battery["source_bindings"][0]["sha256"] = "0" * 64
    with pytest.raises(BatteryContractError, match="sha256 drift"):
        validate_battery(battery, _load_receipt())


def test_count_only_false_is_rejected() -> None:
    battery = _load_battery()
    battery["count_only"] = False
    with pytest.raises(BatteryContractError, match="count_only"):
        validate_battery(battery, _load_receipt())


def test_verdict_recap_drift_is_rejected() -> None:
    battery = _load_battery()
    battery["verdict_recap"]["analysis_completion"] = "pass"
    with pytest.raises(BatteryContractError, match="verdict_recap"):
        validate_battery(battery, _load_receipt())


def test_missing_finding_is_rejected() -> None:
    battery = _load_battery()
    battery["f_findings"] = [f for f in battery["f_findings"] if f["id"] != "F06"]
    with pytest.raises(BatteryContractError, match="F01-F06"):
        validate_battery(battery, _load_receipt())


def test_f06_not_bounded_closed_is_rejected() -> None:
    battery = _load_battery()
    for finding in battery["f_findings"]:
        if finding["id"] == "F06":
            finding["status"] = "open"
    with pytest.raises(BatteryContractError, match="closed-bounded-under-S05"):
        validate_battery(battery, _load_receipt())


def test_absolute_binding_path_is_rejected() -> None:
    battery = _load_battery()
    battery["source_bindings"][0]["path"] = "/etc/passwd"
    with pytest.raises(BatteryContractError, match="absolute path in source binding"):
        validate_battery(battery, _load_receipt())


def test_nonzero_retest_exit_is_rejected() -> None:
    battery = _load_battery()
    battery["re_test_set"][0]["exitCode"] = 1
    with pytest.raises(BatteryContractError, match="exitCode|exit was not 0"):
        validate_battery(battery, _load_receipt())


def test_readiness_promotion_is_rejected() -> None:
    battery = _load_battery()
    battery["readiness"]["m215_m220"] = "released"
    with pytest.raises(BatteryContractError, match="readiness"):
        validate_battery(battery, _load_receipt())


def test_empty_non_claims_is_rejected() -> None:
    battery = _load_battery()
    battery["non_claims"] = []
    with pytest.raises(BatteryContractError, match="non_claims"):
        validate_battery(battery, _load_receipt())
