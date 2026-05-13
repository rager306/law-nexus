from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd" / "retrieval" / "fixtures" / "offline_citation_retrieval_cases.json"
CLI = ROOT / "scripts" / "verify-offline-citation-retrieval-proof.py"

EXPECTED_INVENTORY = [
    "ambiguous_candidate_set",
    "id_path_mismatch",
    "orphaned_source_path",
    "scoped_no_answer",
    "scoped_no_candidate",
    "unresolved_candidate_evidence",
    "unsafe_payload_rejected",
]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "python", str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def write_fixture(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_cli_passes_for_checked_in_fixture() -> None:
    result = run_cli()

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads(result.stdout)
    assert summary == {
        "diagnostic_code_inventory": EXPECTED_INVENTORY,
        "fixture_path": "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
        "mismatch_count": 0,
        "namespace_strategy": "m014_proof_local_prefixes_allowed_by_shared_validator",
        "non_authoritative": True,
        "rejected_count": 3,
        "schema_version": "offline-citation-retrieval-proof/v1",
        "scoped_no_answer_count": 1,
        "selected_count": 2,
        "total_cases": 6,
        "validator_accepted_count": 3,
        "validator_rejected_count": 1,
    }


def test_cli_reports_missing_fixture_with_bounded_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    result = run_cli("--fixtures", str(missing))

    assert result.returncode == 2
    summary = json.loads(result.stdout)
    assert summary["mismatch_count"] == 1
    assert summary["mismatches"][0]["code"] == "fixture_not_found"
    assert "/root/" not in json.dumps(summary)


def test_cli_rejects_malformed_fixture_json(tmp_path: Path) -> None:
    malformed = tmp_path / "bad.json"
    malformed.write_text("{not-json", encoding="utf-8")

    result = run_cli("--fixtures", str(malformed))

    assert result.returncode == 2
    summary = json.loads(result.stdout)
    assert summary["mismatch_count"] == 1
    assert summary["mismatches"][0]["phase"] == "fixture_load"
    assert summary["mismatches"][0]["code"] == "malformed_fixture_json"


def test_cli_detects_case_expectation_mismatch(tmp_path: Path) -> None:
    fixture = load_fixture()
    fixture["cases"][0]["expected_validator_result"] = "rejected"
    mutated = tmp_path / "mismatch.json"
    write_fixture(mutated, fixture)

    result = run_cli("--fixtures", str(mutated))

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["mismatch_count"] >= 1
    assert any(
        mismatch["code"] == "expectation_mismatch"
        and mismatch["case_id"] == "CASE-M014-VALID-EXACT-RECORD-CANDIDATE"
        and mismatch["field_path"] == "expected_validator_result"
        for mismatch in summary["mismatches"]
    )


def test_cli_detects_unsafe_offline_diagnostic_fields(tmp_path: Path) -> None:
    fixture = load_fixture()
    ambiguous = next(case for case in fixture["cases"] if case["case_class"] == "ambiguous_candidate_set")
    ambiguous["diagnostics"][0]["raw_text"] = "unsafe raw payload"
    mutated = tmp_path / "unsafe-diagnostic.json"
    write_fixture(mutated, fixture)

    result = run_cli("--fixtures", str(mutated))

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert any(
        mismatch["code"] == "unsafe_diagnostic_field"
        and mismatch["case_id"] == "CASE-M014-AMBIGUOUS-CANDIDATE-SET"
        and "raw_text" in mismatch["actual_fields"]
        for mismatch in summary["mismatches"]
    )


def test_cli_preserves_m014_namespace_and_unknown_namespace_regression(tmp_path: Path) -> None:
    fixture = load_fixture()
    valid_case = fixture["cases"][0]
    assert valid_case["output"]["retrieval_output_id"].startswith("RET-M014-")

    result = run_cli()
    assert result.returncode == 0

    fixture["cases"][0]["output"]["retrieval_output_id"] = "RET-UNKNOWN-001"
    fixture["cases"][0]["output"]["citations"][0]["retrieval_output_id"] = "RET-UNKNOWN-001"
    mutated = tmp_path / "unknown-namespace.json"
    write_fixture(mutated, fixture)

    unknown = run_cli("--fixtures", str(mutated))
    assert unknown.returncode == 1
    summary = json.loads(unknown.stdout)
    assert "unknown_id_namespace" in summary["diagnostic_code_inventory"]
    assert any(
        mismatch["field_path"] == "expected_diagnostic_codes"
        and "unknown_id_namespace" in mismatch["actual"]
        for mismatch in summary["mismatches"]
    )
