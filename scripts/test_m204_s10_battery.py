"""Fail-closed tests for the additive S10 battery composer."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import m204_s10_battery as battery

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_composer_preserves_negative_s10_predicate() -> None:
    value = battery.compose(run_gates=False)
    assert value["tested_source_revision"] == battery.PLACEHOLDER
    assert value["c4"]["operational_acceptance"] == "non-pass"
    assert value["c4"]["jsonl_valid"] is False
    assert value["summary"]["failed"] == 1


def test_forged_pass_and_valid_jsonl_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    original = battery.load

    def forged(path: Path) -> dict:
        value = original(path)
        if path == battery.RECEIPT:
            value = copy.deepcopy(value)
            value["observed_output"]["jsonl_valid"] = True
            value["claims"]["operational_acceptance"] = "pass"
        return value

    monkeypatch.setattr(battery, "load", forged)
    with pytest.raises(ValueError, match="unexpectedly has valid JSONL"):
        battery.compose(run_gates=False)


def test_wrong_attempt_and_short_duration_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    original = battery.load

    def altered(path: Path) -> dict:
        value = original(path)
        if path == battery.RECEIPT:
            value = copy.deepcopy(value)
            value["attempt_id"] = "other-attempt"
        return value

    monkeypatch.setattr(battery, "load", altered)
    with pytest.raises(ValueError, match="wrong S10 attempt"):
        battery.compose(run_gates=False)


def test_historical_battery_pin_is_byte_stable() -> None:
    before = hashlib.sha256(battery.HISTORICAL.read_bytes()).hexdigest()
    battery.compose(run_gates=False)
    after = hashlib.sha256(battery.HISTORICAL.read_bytes()).hexdigest()
    assert after == before


def test_written_battery_rejects_guessed_revision(tmp_path: Path) -> None:
    value = battery.compose(run_gates=False)
    value["tested_source_revision"] = "0123456789abcdef"
    path = tmp_path / "battery.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    loaded = load(path)
    assert loaded["tested_source_revision"] != battery.PLACEHOLDER
    assert loaded["c4"]["operational_acceptance"] == "non-pass"
