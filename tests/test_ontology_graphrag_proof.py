from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build-ontology-graphrag-proof-cases.py"
VERIFIER_PATH = ROOT / "scripts" / "verify-ontology-graphrag-proof.py"
FIXTURE_PATH = ROOT / "prd" / "research" / "ontology_architecture_requirements" / "ontology_graphrag_proof_cases.json"

EXPECTED_CODES = {
    "ambiguous_candidate_set",
    "forbidden_payload_field",
    "missing_required_field",
    "ontology_filter_matched",
    "scoped_no_answer",
    "temporal_filter_excluded",
    "unsupported_ontology_filter",
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

REQUIRED_CASE_CLASSES = {
    "valid_ontology_temporal_citation",
    "inactive_or_wrong_edition_excluded",
    "unsupported_ontology_filter",
    "missing_citation_or_evidence_id",
    "ambiguous_candidate_set",
    "scoped_no_answer",
    "forbidden_payload_field",
}


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_cli(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(path), *args],
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
    assert summary["schema_version"] == "ontology-graphrag-proof/v1"
    assert summary["fixture_path"] == "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json"
    assert summary["proof_id"] == "OG-M020-S02-FIXTURE-PROOF"
    assert summary["non_authoritative"] is True
    assert summary["redaction_ok"] is True
    assert isinstance(summary["total_cases"], int)
    assert isinstance(summary["accepted_count"], int)
    assert isinstance(summary["rejected_count"], int)
    assert isinstance(summary["blocked_count"], int)
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


def test_tracked_fixture_shape_covers_happy_path_and_fail_closed_cases() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert data["schema_version"] == "ontology-graphrag-proof-cases/v1"
    assert data["proof_id"] == "OG-M020-S02-FIXTURE-PROOF"
    assert data["non_authoritative"] is True
    assert data["redaction"]["forbidden_payload_classes_absent"] is True
    assert {case["case_class"] for case in data["cases"]} == REQUIRED_CASE_CLASSES
    assert all(case["non_authoritative"] is True for case in data["cases"])
    assert all(case["case_id"].startswith("CASE-M020-OG-") for case in data["cases"])

    accepted = next(case for case in data["cases"] if case["case_class"] == "valid_ontology_temporal_citation")
    assert accepted["expected_result"] == "accepted"
    assert accepted["ontology_filter"]["expected_filter_result"] == "matched"
    assert accepted["temporal_filter"]["expected_temporal_result"] == "included"
    assert accepted["candidate_set"][0]["evidence_span_id"] == "EV-M014-HIER-CONS-ARTICLE-0001"
    assert accepted["output"]["citations"][0]["evidence_span_id"] == "EV-M014-HIER-CONS-ARTICLE-0001"

    by_class = {case["case_class"]: case for case in data["cases"]}
    assert by_class["inactive_or_wrong_edition_excluded"]["expected_diagnostic_codes"] == ["temporal_filter_excluded", "wrong_edition"]
    assert by_class["unsupported_ontology_filter"]["expected_result"] == "blocked_unsupported_filter"
    assert by_class["missing_citation_or_evidence_id"]["expected_diagnostic_codes"] == ["missing_required_field"]
    assert by_class["ambiguous_candidate_set"]["expected_diagnostic_codes"] == ["ambiguous_candidate_set"]
    assert by_class["scoped_no_answer"]["expected_result"] == "accepted_scoped_no_answer"
    assert by_class["forbidden_payload_field"]["expected_diagnostic_codes"] == ["forbidden_payload_field"]

    case_payload = json.dumps(
        [
            {
                "query": case["query"],
                "candidate_set": case["candidate_set"],
                "output": case.get("output", {}),
            }
            for case in data["cases"]
        ],
        ensure_ascii=False,
    )
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in case_payload


def test_builder_check_succeeds_for_tracked_fixture() -> None:
    completed = run_cli(BUILDER_PATH, "--check")
    summary = parse_stdout(completed)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert summary == {
        "case_count": 7,
        "fixture_path": "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json",
        "non_authoritative": True,
        "schema_version": "ontology-graphrag-proof-builder/v1",
        "status": "ok",
    }


def test_verifier_succeeds_on_tracked_fixture_with_stable_counts() -> None:
    completed = run_cli(VERIFIER_PATH)
    summary = parse_stdout(completed)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert summary["total_cases"] == 7
    assert summary["accepted_count"] == 2
    assert summary["rejected_count"] == 4
    assert summary["blocked_count"] == 1
    assert summary["mismatch_count"] == 0
    assert summary["result_states"] == {
        "accepted": 1,
        "accepted_scoped_no_answer": 1,
        "blocked_unsupported_filter": 1,
        "rejected": 4,
    }
    assert "mismatches" not in summary
    assert_safe_summary(summary)


def test_verifier_is_deterministic_for_tracked_fixture() -> None:
    first = run_cli(VERIFIER_PATH)
    second = run_cli(VERIFIER_PATH)

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout == second.stdout


def test_verifier_fails_closed_on_unsupported_filter_expectation_mismatch(tmp_path: Path) -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    unsupported = next(case for case in data["cases"] if case["case_class"] == "unsupported_ontology_filter")
    unsupported["expected_result"] = "accepted"
    bad_fixture = tmp_path / "bad-ontology-proof-cases.json"
    bad_fixture.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    completed = run_cli(VERIFIER_PATH, "--fixtures", str(bad_fixture))
    summary = parse_stdout(completed)

    assert completed.returncode == 1
    assert summary["mismatch_count"] == 1
    assert summary["mismatches"][0]["phase"] == "case_expectation"
    assert summary["mismatches"][0]["case_id"] == "CASE-M020-OG-UNSUPPORTED-ONTOLOGY-FILTER"
    assert summary["mismatches"][0]["expected_result"] == "accepted"
    assert summary["mismatches"][0]["actual_result"] == "blocked_unsupported_filter"
    assert summary["fixture_path"].endswith("bad-ontology-proof-cases.json")


def test_verifier_fails_closed_on_forbidden_payload_key(tmp_path: Path) -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    accepted = next(case for case in data["cases"] if case["case_class"] == "valid_ontology_temporal_citation")
    accepted["output"]["raw_legal_text"] = "redacted"
    bad_fixture = tmp_path / "unsafe-ontology-proof-cases.json"
    bad_fixture.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    completed = run_cli(VERIFIER_PATH, "--fixtures", str(bad_fixture))
    summary = parse_stdout(completed)

    assert completed.returncode == 1
    assert summary["mismatch_count"] >= 1
    assert any(mismatch["phase"] == "redaction_boundary" for mismatch in summary["mismatches"])
    assert summary["redaction_ok"] is False


def test_run_proof_api_matches_cli_summary() -> None:
    verifier = load_module(VERIFIER_PATH, "ontology_graphrag_verifier")
    exit_code, summary = verifier.run_proof(FIXTURE_PATH)

    assert exit_code == 0
    assert summary["mismatch_count"] == 0
    assert summary["diagnostic_code_inventory"] == sorted(EXPECTED_CODES)
