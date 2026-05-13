from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "scripts" / "verify-real-artifact-retrieval-proof.py"
FIXTURE_PATH = ROOT / "prd" / "retrieval" / "fixtures" / "real_artifact_retrieval_cases.json"

EXPECTED_CODES = {
    "ambiguous_citation_key",
    "id_path_mismatch",
    "missing_required_field",
    "orphaned_source_path",
    "scoped_no_answer",
    "unsafe_no_answer_shape",
    "wrong_edition",
}

FORBIDDEN_SNIPPETS = {
    "Федеральный закон",
    "Статья 1.",
    "raw_legal_text",
    "source_excerpt",
    "prompt",
    "provider_payload",
    "provider_response_body",
    "BEGIN PRIVATE KEY",
    "embedding_vector",
    "falkordb_row",
    "generated_answer_prose",
    "legal_advice",
}


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def parse_stdout(completed: subprocess.CompletedProcess[str]) -> dict:
    assert completed.stdout
    return json.loads(completed.stdout)


def assert_safe_summary(summary: dict) -> None:
    serialized = json.dumps(summary, ensure_ascii=False)
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in serialized
    assert summary["schema_version"] == "real-artifact-retrieval-proof/v1"
    assert summary["fixture_path"] == "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
    assert summary["namespace_strategy"] == "safe_namespace_extension_selected"
    assert isinstance(summary["total_cases"], int)
    assert isinstance(summary["accepted_count"], int)
    assert isinstance(summary["rejected_count"], int)
    assert isinstance(summary["mismatch_count"], int)
    assert set(summary["diagnostic_code_inventory"]) == EXPECTED_CODES
    for mismatch in summary.get("mismatches", []):
        assert set(mismatch) <= {
            "phase",
            "case_id",
            "code",
            "field_path",
            "actual_result",
            "expected_result",
            "actual_codes",
            "expected_codes",
            "fixture_path",
            "detail",
        }
        for value in mismatch.values():
            if isinstance(value, str):
                assert len(value) <= 160


def test_cli_succeeds_on_tracked_real_artifact_fixture() -> None:
    completed = run_cli()
    summary = parse_stdout(completed)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert summary["total_cases"] == 7
    assert summary["accepted_count"] == 2
    assert summary["rejected_count"] == 5
    assert summary["mismatch_count"] == 0
    assert "mismatches" not in summary
    assert_safe_summary(summary)


def test_cli_is_deterministic_for_tracked_fixture() -> None:
    first = run_cli()
    second = run_cli()

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout == second.stdout


def test_cli_fails_closed_on_expected_result_mismatch(tmp_path: Path) -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data["cases"][0]["expected_result"] = "rejected"
    bad_fixture = tmp_path / "bad-real-artifact-cases.json"
    bad_fixture.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    completed = run_cli("--fixtures", str(bad_fixture))
    summary = parse_stdout(completed)

    assert completed.returncode == 1
    assert summary["mismatch_count"] == 1
    assert summary["mismatches"][0]["phase"] == "case_expectation"
    assert summary["mismatches"][0]["case_id"] == "CASE-M013-VALID-REAL-ARTIFACT"
    assert summary["mismatches"][0]["expected_result"] == "rejected"
    assert summary["mismatches"][0]["actual_result"] == "accepted"
    assert summary["fixture_path"].endswith("bad-real-artifact-cases.json")


def test_cli_fails_closed_on_missing_fixture(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    completed = run_cli("--fixtures", str(missing))
    summary = parse_stdout(completed)

    assert completed.returncode == 2
    assert summary["schema_version"] == "real-artifact-retrieval-proof/v1"
    assert summary["total_cases"] == 0
    assert summary["mismatch_count"] == 1
    assert summary["mismatches"][0]["phase"] == "fixture_load"
    assert summary["mismatches"][0]["code"] == "fixture_not_found"
