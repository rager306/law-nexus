from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/check-gsd-sync-drift.py"
EXPECTED_DIAGNOSTIC_IDS = {
    "DRIFT-R035-ACTIVE-UNOWNED",
    "DRIFT-R035-REGISTRY-MAPPING-ABSENT",
    "DRIFT-R035-MISSING-PROOF-GATE",
    "DRIFT-R035-STALE-GATE-VIEW",
    "DRIFT-R035-POLICY-ENDPOINT-MISSING",
    "DRIFT-R035-CANDIDATE-CURRENT-MISMATCH",
    "DRIFT-R035-GATE-ID-DRIFT",
    "DRIFT-R035-UNSAFE-LIFECYCLE-LANGUAGE",
}
EXPECTED_CURRENT_FAILURES = EXPECTED_DIAGNOSTIC_IDS - {"DRIFT-R035-UNSAFE-LIFECYCLE-LANGUAGE"}


def load_check_module():
    spec = importlib.util.spec_from_file_location("check_gsd_sync_drift", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_diagnostics_emits_expected_current_r035_drift_ids():
    module = load_check_module()

    diagnostics = module.build_diagnostics()
    by_id = {diagnostic.diagnostic_id: diagnostic for diagnostic in diagnostics}

    assert set(by_id) == EXPECTED_DIAGNOSTIC_IDS
    assert {diagnostic.diagnostic_id for diagnostic in diagnostics if diagnostic.failed} == EXPECTED_CURRENT_FAILURES
    for diagnostic_id in EXPECTED_CURRENT_FAILURES:
        diagnostic = by_id[diagnostic_id]
        assert diagnostic.status == "ERROR"
        assert diagnostic.message.startswith(f"{diagnostic_id}:")
        assert diagnostic.evidence_path
        assert diagnostic.remediation_owner
        assert diagnostic.non_claim_boundary


def test_drift_check_keeps_r035_validation_as_non_claim():
    module = load_check_module()

    diagnostics = module.build_diagnostics()
    unsafe_language = next(
        diagnostic for diagnostic in diagnostics if diagnostic.diagnostic_id == "DRIFT-R035-UNSAFE-LIFECYCLE-LANGUAGE"
    )

    assert unsafe_language.status == "OK"
    assert unsafe_language.observed == "safe wording only in checked artifacts"
    checked_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (module.AUDIT_PATH, module.CONTRACT_PATH, module.CLAIMS_LEDGER_PATH)
    )
    assert module.unsafe_lifecycle_lines(((SCRIPT_PATH, SCRIPT_PATH.read_text(encoding="utf-8")),)) == []
    assert module.unsafe_lifecycle_lines(((module.CONTRACT_PATH, checked_text),)) == []


def test_command_json_smoke_reports_drift_without_validating_r035():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--format", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["check"] == "gsd-sync-drift-r035"
    assert payload["status"] == "DRIFT"
    assert payload["failed_count"] == len(EXPECTED_CURRENT_FAILURES)
    assert "does not validate" in payload["non_claim"]
    assert {diagnostic["diagnostic_id"] for diagnostic in payload["diagnostics"]} == EXPECTED_DIAGNOSTIC_IDS


def test_strict_exit_code_is_available_for_fail_fast_callers():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--format", "text", "--strict-exit-code"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "status=DRIFT" in completed.stdout
    assert "DRIFT-R035-REGISTRY-MAPPING-ABSENT status=ERROR" in completed.stdout
