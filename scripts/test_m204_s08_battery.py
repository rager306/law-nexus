#!/usr/bin/env python3
"""Fail-closed fixtures for the M204/S08 validation battery.

These tests deliberately validate the boundary between the tracked battery and
its frozen S07 receipt.  They do not run the corpus or rewrite evidence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
BATTERY_PATH = ROOT / "prd/migration/rust-evidence/m204-validation-battery-20260912.json"
RECEIPT_PATH = ROOT / "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json"
S07_BATTERY_PATH = ROOT / "prd/migration/rust-evidence/m204-s07-verification-battery-eligible.json"
S07_GOVERNOR_PATH = ROOT / "prd/migration/rust-evidence/m204-s07-governor-repeat.json"
S06_RECEIPT_PATH = ROOT / "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json"
M203_RECEIPT_PATH = ROOT / "prd/migration/rust-evidence/m203-s09-c4-operational-receipt.json"
PLACEHOLDER = "pending-fill-by-validate-unit"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing battery: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("battery must be a JSON object")
    return value


def reject_untrusted_battery(battery: dict[str, Any], receipt: dict[str, Any]) -> None:
    """Reject claims that cannot be bound to the frozen, non-pass receipt."""
    if battery.get("schema_version") != "law-nexus/milestone-validation-battery/v1":
        raise ValueError("schema_version mismatch")

    revision = battery.get("tested_source_revision")
    if revision != PLACEHOLDER and not isinstance(revision, str):
        raise ValueError("tested_source_revision has no sha256 shape")
    if revision != PLACEHOLDER and not SHA256.fullmatch(revision or ""):
        raise ValueError("tested_source_revision has no sha256 shape")

    receipt_claim = receipt.get("claims", {}).get("operational_acceptance")
    c4_claim = battery.get("c4", {}).get("operational_acceptance")
    if receipt_claim != "non-pass":
        raise ValueError("receipt is not the frozen non-pass receipt")
    if c4_claim == "pass":
        raise ValueError("forged operational pass over non-pass receipt")
    if c4_claim != receipt_claim:
        raise ValueError("battery C4 claim is not bound to receipt")


def test_forged_operational_pass_is_rejected() -> None:
    battery = load(BATTERY_PATH)
    receipt = load(RECEIPT_PATH)
    forged = copy.deepcopy(battery)
    forged["c4"]["operational_acceptance"] = "pass"
    with pytest.raises(ValueError, match="forged operational pass"):
        reject_untrusted_battery(forged, receipt)


def test_guessed_git_sha_is_rejected() -> None:
    battery = load(BATTERY_PATH)
    receipt = load(RECEIPT_PATH)
    guessed = copy.deepcopy(battery)
    guessed["tested_source_revision"] = "0123456789abcdef0123456789abcdef01234567"
    with pytest.raises(ValueError, match="sha256 shape"):
        reject_untrusted_battery(guessed, receipt)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda value: value.pop("tested_source_revision"), "sha256 shape"),
        (lambda value: value.update(tested_source_revision="sha256:not-a-digest"), "sha256 shape"),
        (lambda value: value.update(schema_version="wrong/v1"), "schema_version mismatch"),
    ],
)
def test_missing_hash_shape_and_schema_are_rejected(mutation, message: str) -> None:
    battery = load(BATTERY_PATH)
    receipt = load(RECEIPT_PATH)
    mutation(battery)
    with pytest.raises(ValueError, match=message):
        reject_untrusted_battery(battery, receipt)


def test_missing_battery_is_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing-battery.json"
    with pytest.raises(ValueError, match="missing battery"):
        load(missing)


def test_frozen_s06_m203_s07_receipts_are_byte_stable() -> None:
    # These are the predecessor evidence inputs; the fixture suite must never
    # normalize or rewrite them while checking the S08 battery.
    paths = (
        S06_RECEIPT_PATH,
        M203_RECEIPT_PATH,
        RECEIPT_PATH,
        S07_BATTERY_PATH,
        S07_GOVERNOR_PATH,
    )
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    battery = load(BATTERY_PATH)
    receipt = load(RECEIPT_PATH)
    reject_untrusted_battery(battery, receipt)
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    assert after == before


def test_tracked_battery_is_honest_and_placeholder_bound() -> None:
    battery = load(BATTERY_PATH)
    receipt = load(RECEIPT_PATH)
    reject_untrusted_battery(battery, receipt)
    assert battery["tested_source_revision"] == PLACEHOLDER
    assert receipt["claims"]["operational_acceptance"] == "non-pass"
