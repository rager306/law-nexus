from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import m204_s07_evidence_verify as verifier

ROOT = Path(__file__).resolve().parents[1]


def artifacts() -> dict[str, dict]:
    return {
        "governor": verifier.load(verifier.GOVERNOR),
        "receipt": verifier.load(verifier.RECEIPT),
        "requirements": verifier.load(verifier.REQUIREMENTS),
    }


def test_live_s07_artifacts_are_bound_and_supporting_only() -> None:
    checks = verifier.verify_all()
    assert checks["classification"] == "supporting-only"
    assert artifacts()["receipt"]["claims"]["operational_acceptance"] == "non-pass"
    assert artifacts()["receipt"]["duration_ms"] < 3_600_000


def test_governor_repeat_rejects_wrong_check_identity() -> None:
    governor = copy.deepcopy(artifacts()["governor"])
    governor["governor"]["summary"]["check_id"] = "other-check"
    with pytest.raises(ValueError, match="exact governor check id"):
        verifier.verify_governor(governor)


def test_governor_repeat_rejects_missing_pass_finding() -> None:
    governor = copy.deepcopy(artifacts()["governor"])
    governor["governor"]["summary"]["observed"]["pass_finding"] = False
    with pytest.raises(ValueError, match="pass finding"):
        verifier.verify_governor(governor)


def test_short_complete_receipt_cannot_be_promoted() -> None:
    receipt = copy.deepcopy(artifacts()["receipt"])
    receipt["claims"]["operational_acceptance"] = "pass"
    assert verifier.load(verifier.RECEIPT)["claims"]["operational_acceptance"] == "non-pass"
    with pytest.raises(ValueError, match="short C4 run claims pass"):
        verifier.verify_receipt(receipt)


def test_receipt_binding_rejects_forged_duration() -> None:
    receipt = copy.deepcopy(artifacts()["receipt"])
    receipt["duration_ms"] = 3_600_000
    with pytest.raises(ValueError, match="fixture unexpectedly proves operational duration"):
        verifier.verify_receipt(receipt)


def test_requirements_reject_lifecycle_promotion() -> None:
    requirements = copy.deepcopy(artifacts()["requirements"])
    requirements["classification"] = "accepted"
    with pytest.raises(ValueError, match="classification"):
        verifier.verify_requirements(requirements, artifacts()["receipt"])


def test_battery_proves_integrity_not_operational_acceptance(tmp_path: Path) -> None:
    original = verifier.BATTERY
    verifier.BATTERY = tmp_path / "battery.json"
    try:
        verifier.write_battery(verifier.verify_all())
        battery = json.loads(verifier.BATTERY.read_text())
    finally:
        verifier.BATTERY = original
    assert battery["verification"] == "S07_VERIFY_OK"
    assert battery["operational_acceptance"] == "non-pass"
    assert battery["false_operational_pass_blocked"] is True
    assert battery["corpus_walk_repeated"] is False


def test_t06_requires_passing_receipt(tmp_path: Path) -> None:
    receipt = copy.deepcopy(artifacts()["receipt"])
    receipt["attempt_id"] = "passing-run-001"
    receipt["immutable_attempt_identity"]["attempt_id"] = "passing-run-001"
    path = tmp_path / "passing.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="operational acceptance is not proven"):
        verifier.verify_t06_receipt(path)


def test_t06_rejects_forged_pass_claim(tmp_path: Path) -> None:
    receipt = copy.deepcopy(artifacts()["receipt"])
    receipt["attempt_id"] = "passing-run-001"
    receipt["immutable_attempt_identity"]["attempt_id"] = "passing-run-001"
    receipt["claims"]["operational_acceptance"] = "pass"
    path = tmp_path / "forged.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="operational claim does not match observed facts"):
        verifier.verify_t06_receipt(path, require_operational_pass=False)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
