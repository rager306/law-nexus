#!/usr/bin/env python3
"""Bounded subprocess tests for the S14 aggregate verifier."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m204_s14_evidence_verify.py"
MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s14-frozen-hashes.json"
BATTERY = ROOT / "prd/migration/rust-evidence/m204-s14-verification-battery.json"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def test_real_aggregate_is_read_only() -> None:
    result = run(str(SCRIPT), "verify")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "S14_VERIFY_OK"


def test_manifest_tamper_and_closed_schema_fail() -> None:
    baseline = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="m204-s14-evidence-") as raw:
        directory = Path(raw)
        for mutation in ("forged-pin", "missing-row", "extra-key", "unsafe-path"):
            value = copy.deepcopy(baseline)
            if mutation == "forged-pin":
                value["files"][0]["sha256"] = "sha256:" + "0" * 64
            elif mutation == "missing-row":
                value["files"].pop()
            elif mutation == "extra-key":
                value["unexpected"] = True
            else:
                value["files"][0]["path"] = "../escape.json"
            artifact = directory / f"{mutation}.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            # The CLI reads the repository manifest, so exercise the pure validator
            # through a tiny subprocess importing the module and the hostile file.
            probe = (
                "import json,sys; import scripts.m204_s14_evidence_verify as v; "
                "v.validate_manifest(json.load(open(sys.argv[1])))"
            )
            result = subprocess.run(
                [sys.executable, "-c", probe, str(artifact)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode != 0, mutation


def test_battery_forged_pass_and_wrong_distinction_fail() -> None:
    baseline = json.loads(BATTERY.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="m204-s14-battery-") as raw:
        directory = Path(raw)
        for mutation in ("pass", "green-integrity-wrong-acceptance", "extra"):
            value = copy.deepcopy(baseline)
            if mutation == "pass":
                value["c4_acceptance"] = "pass"
            elif mutation == "green-integrity-wrong-acceptance":
                value["consumer"]["c4_acceptance"] = "pass"
            else:
                value["extra"] = True
            artifact = directory / f"{mutation}.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            probe = (
                "import json,sys; import scripts.m204_s14_evidence_verify as v; "
                "v.validate_battery(json.load(open(sys.argv[1])))"
            )
            result = subprocess.run(
                [sys.executable, "-c", probe, str(artifact)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode != 0, mutation


if __name__ == "__main__":
    for test in (
        test_real_aggregate_is_read_only,
        test_manifest_tamper_and_closed_schema_fail,
        test_battery_forged_pass_and_wrong_distinction_fail,
    ):
        test()
    print("M204_S14_EVIDENCE_TESTS_OK (3 tests)")
