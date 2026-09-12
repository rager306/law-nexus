from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import m204_s13_evidence_verify as verifier


def manifest() -> dict:
    return verifier.load()


def test_frozen_manifest_verifies() -> None:
    verifier.validate(manifest())


def test_rejects_missing_duplicate_and_extra_pin() -> None:
    baseline = manifest()
    mutations = (
        lambda rows: rows.pop(),
        lambda rows: rows.append(copy.deepcopy(rows[0])),
        lambda rows: rows.__setitem__(0, {**rows[0], "path": "extra.json"}),
    )
    for mutate in mutations:
        value = copy.deepcopy(baseline)
        mutate(value["files"])
        with pytest.raises(ValueError, match="pin|required"):
            verifier.validate(value)


def test_rejects_forged_hash_path_and_extra_key() -> None:
    baseline = manifest()
    cases = []
    forged = copy.deepcopy(baseline)
    forged["files"][0]["sha256"] = "sha256:" + "0" * 64
    cases.append(forged)
    escaped = copy.deepcopy(baseline)
    escaped["files"][0]["path"] = "../escape"
    cases.append(escaped)
    extra = copy.deepcopy(baseline)
    extra["unexpected"] = True
    cases.append(extra)
    for value in cases:
        with pytest.raises(ValueError):
            verifier.validate(value)


def test_rejects_promoted_battery(tmp_path: Path) -> None:
    baseline = manifest()
    battery_path = tmp_path / "battery.json"
    battery = json.loads(verifier.S13_BATTERY.read_text(encoding="utf-8"))
    battery["operational_acceptance"] = "pass"
    battery_path.write_text(json.dumps(battery), encoding="utf-8")
    original = verifier.S13_BATTERY
    verifier.S13_BATTERY = battery_path
    try:
        with pytest.raises(ValueError, match="promotes"):
            verifier.validate(baseline)
    finally:
        verifier.S13_BATTERY = original


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
