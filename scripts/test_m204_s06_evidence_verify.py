from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

import m204_s06_evidence_verify as verifier

ROOT = Path(__file__).resolve().parents[1]


def artifacts() -> dict:
    return {
        name: verifier.load(path)
        for name, path in {
            "governor": verifier.GOVERNOR,
            "receipt": verifier.RECEIPT,
            "requirements": verifier.REQUIREMENTS,
            "waiver": verifier.WAIVER,
        }.items()
    }


def test_live_artifacts_are_bounded_and_fail_closed() -> None:
    checks = verifier.verify_all()
    assert checks == {
        "governor": "pass",
        "c4_receipt": "pass",
        "requirements": "pass",
        "frozen_waiver": "pass",
    }
    receipt = artifacts()["receipt"]
    assert receipt["terminal"]["outcome"] == "timeout"
    assert receipt["claims"]["operational_acceptance"] == "non-pass"


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda d: d["terminal"].update(outcome="complete", exit_code=7, timeout=False),
            "complete has nonzero",
        ),
        (lambda d: d["claims"].update(operational_acceptance="pass"), "cannot claim pass"),
        (lambda d: d["c4_binding"].update(limit=1000), "full operational receipt"),
        (lambda d: d["corpus"].update(consultant_xml_count=12), "corpus count"),
    ],
)
def test_receipt_negative_fixtures_fail_closed(mutation, message: str) -> None:
    receipt = copy.deepcopy(artifacts()["receipt"])
    mutation(receipt)
    with pytest.raises(ValueError, match=message):
        verifier.verify_receipt(receipt)


def test_requirements_reject_lifecycle_promotion() -> None:
    requirements = copy.deepcopy(artifacts()["requirements"])
    requirements["requirements"][0]["disposition"] = "accepted"
    with pytest.raises(ValueError, match="supporting-only"):
        verifier.verify_requirements(requirements)


def test_governor_rejects_missing_machine_count() -> None:
    governor = copy.deepcopy(artifacts()["governor"])
    del governor["governor"]["summary"]["observed"]["open_count"]
    with pytest.raises(ValueError, match="open_count"):
        verifier.verify_governor(governor)


def test_cli_writes_battery_without_rewalking_corpus(tmp_path: Path) -> None:
    output = tmp_path / "battery.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/m204_s06_evidence_verify.py"),
            "--check",
            "--write-battery",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert '"status": "pass"' in completed.stdout
    battery = json.loads(output.read_text(encoding="utf-8"))
    assert battery["verification"] == "S06_VERIFY_OK"
    assert battery["bounded"] is True
    assert battery["corpus_walk_repeated"] is False
    assert battery["operational_acceptance"] == "non-pass"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
