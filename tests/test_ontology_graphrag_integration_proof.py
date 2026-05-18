from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PROOF_PATH = ROOT / "scripts" / "verify-ontology-graphrag-integration-proof.py"
FIXTURE_PATH = ROOT / "prd" / "research" / "ontology_architecture_requirements" / "ontology_graphrag_proof_cases.json"
REPORT_PATH = ROOT / "prd" / "research" / "ontology_architecture_requirements" / "ontology_graphrag_integration_proof.json"
SAFETY_CONTRACT_PATH = ROOT / "prd" / "06_m002_cypher_safety_contract.md"

EXPECTED_TRACE_RESULTS = {
    "CASE-M020-OG-VALID-ONTOLOGY-TEMPORAL-CITATION": "accepted",
    "CASE-M020-OG-INACTIVE-OR-WRONG-EDITION-EXCLUDED": "rejected",
    "CASE-M020-OG-UNSUPPORTED-ONTOLOGY-FILTER": "blocked_unsupported_filter",
    "CASE-M020-OG-MISSING-CITATION-OR-EVIDENCE-ID": "rejected",
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
    "llm_reasoning",
    ".gsd/exec",
}


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROOF_PATH), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def parse_stdout(completed: subprocess.CompletedProcess[str]) -> dict:
    assert completed.stdout
    return json.loads(completed.stdout)


def traces_by_case(summary: dict) -> dict[str, dict]:
    traces = summary["case_traces"]
    assert len(traces) == summary["total_cases"]
    return {trace["case_id"]: trace for trace in traces}


def assert_safe_integration_summary(summary: dict) -> None:
    serialized = json.dumps(summary, ensure_ascii=False)
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in serialized

    assert summary["schema_version"] == "ontology-graphrag-integration-proof/v1"
    assert summary["proof_id"] == "OG-M020-S03-CITATION-BOUND-INTEGRATION-PROOF"
    assert summary["source_fixture_path"] == "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json"
    assert summary["report_path"]
    assert summary["source_verifier_path"] == "scripts/verify-ontology-graphrag-proof.py"
    assert summary["gate"] == "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION"
    assert summary["requirement"] == "R035"
    assert summary["non_authoritative"] is True
    assert summary["proof_level"] == "fixture-backed integration proof"
    assert summary["redaction_ok"] is True
    assert summary["gate_disposition"] == "bounded_fixture_integration_passed_gate_remains_open"
    assert summary["r035_lifecycle_disposition"] == "remains_active_bounded_s03_evidence_only"
    assert any("generated-Cypher generation quality" in non_claim for non_claim in summary["non_claims"])


def test_cli_succeeds_and_persists_safe_report(tmp_path: Path) -> None:
    report = tmp_path / "s03-integration-proof.json"
    completed = run_cli("--report-output", str(report))
    summary = parse_stdout(completed)
    persisted = json.loads(report.read_text(encoding="utf-8"))

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert persisted == summary
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
    assert_safe_integration_summary(summary)


def test_case_traces_pin_accepted_filtered_and_temporal_exclusion_behavior() -> None:
    proof = load_module(PROOF_PATH, "ontology_graphrag_integration_proof_cases")
    exit_code, summary = proof.run_proof(FIXTURE_PATH, REPORT_PATH, write_report=False)
    by_case = traces_by_case(summary)

    assert exit_code == 0
    for case_id, expected_result in EXPECTED_TRACE_RESULTS.items():
        assert by_case[case_id]["actual_result"] == expected_result

    accepted = by_case["CASE-M020-OG-VALID-ONTOLOGY-TEMPORAL-CITATION"]
    assert accepted["ontology_filter"] == {
        "filter_id": "OF-M020-LEGAL-EVIDENCE-CORE",
        "filter_kind": "legal_evidence_core",
        "requested_value": "DATA-LEGAL-EVIDENCE-CORE",
        "result": "matched",
    }
    assert accepted["temporal_filter"]["as_of_date"] == "2026-01-01"
    assert accepted["temporal_filter"]["result"] == "included"
    assert accepted["candidate_count"] == 1
    assert accepted["citation_count"] == 1
    assert accepted["citation_validation_result"] == "accepted"
    assert accepted["diagnostic_codes"] == ["ontology_filter_matched"]

    temporal = by_case["CASE-M020-OG-INACTIVE-OR-WRONG-EDITION-EXCLUDED"]
    assert temporal["temporal_filter"]["result"] == "wrong_edition"
    assert temporal["actual_result"] == "rejected"
    assert "temporal_filter_excluded" in temporal["diagnostic_codes"]
    assert "wrong_edition" in temporal["diagnostic_codes"]


def test_case_traces_pin_missing_citation_and_unsupported_filter_failures() -> None:
    proof = load_module(PROOF_PATH, "ontology_graphrag_integration_proof_failures")
    exit_code, summary = proof.run_proof(FIXTURE_PATH, REPORT_PATH, write_report=False)
    by_case = traces_by_case(summary)

    assert exit_code == 0
    missing = by_case["CASE-M020-OG-MISSING-CITATION-OR-EVIDENCE-ID"]
    assert missing["actual_result"] == "rejected"
    assert missing["citation_count"] == 1
    assert missing["citation_validation_result"] == "rejected"
    assert "missing_required_field" in missing["diagnostic_codes"]
    assert summary["citation_validation_status"] == {
        "validated_count": 2,
        "failed_count": 2,
        "skipped_count": 3,
        "missing_citation_or_evidence_count": 1,
        "status": "passed",
    }

    unsupported = by_case["CASE-M020-OG-UNSUPPORTED-ONTOLOGY-FILTER"]
    assert unsupported["actual_result"] == "blocked_unsupported_filter"
    assert unsupported["ontology_filter"]["requested_value"] == "UNSUPPORTED-ONTOLOGY-GATE"
    assert unsupported["ontology_filter"]["result"] == "unsupported"
    assert unsupported["citation_validation_result"] == "not_applicable"
    assert "unsupported_ontology_filter" in unsupported["diagnostic_codes"]
    assert summary["filter_trace_summary"]["unsupported_ontology_filter_count"] == 1


def test_query_safety_boundary_avoids_generated_query_execution_and_points_to_contract() -> None:
    proof = load_module(PROOF_PATH, "ontology_graphrag_integration_proof_query_safety")
    exit_code, summary = proof.run_proof(FIXTURE_PATH, REPORT_PATH, write_report=False)
    contract = SAFETY_CONTRACT_PATH.read_text(encoding="utf-8")

    assert exit_code == 0
    assert "execute_validated" in contract
    assert "Graph.ro_query" in contract
    assert "generated Cypher is never legal authority" in contract
    assert summary["query_safety"] == {
        "generated_query_execution_avoided": True,
        "generated_query_candidates_present": False,
        "execution_like_step_performed": False,
        "future_generated_query_requirement": "Validate through prd/06_m002_cypher_safety_contract.md before any execution-like step.",
    }
    serialized_traces = json.dumps(summary["case_traces"], ensure_ascii=False)
    assert "generated_cypher" not in serialized_traces
    assert "MATCH (" not in serialized_traces


def test_integration_proof_fails_closed_when_s02_verifier_finds_mismatch(tmp_path: Path) -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    accepted = next(case for case in data["cases"] if case["case_class"] == "valid_ontology_temporal_citation")
    accepted["expected_result"] = "rejected"
    bad_fixture = tmp_path / "bad-ontology-integration-proof-cases.json"
    bad_fixture.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    completed = run_cli("--fixtures", str(bad_fixture), "--no-write")
    summary = parse_stdout(completed)

    assert completed.returncode == 1
    assert summary["mismatch_count"] == 1
    assert summary["gate_disposition"] == "bounded_fixture_integration_failed_gate_remains_open"
    assert summary["case_traces"][0]["actual_result"] == "accepted"


def test_report_redaction_rejects_forbidden_payload_keys(tmp_path: Path) -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    accepted = next(case for case in data["cases"] if case["case_class"] == "valid_ontology_temporal_citation")
    accepted["output"]["provider_payload"] = {"unsafe": "redacted but forbidden key"}
    bad_fixture = tmp_path / "unsafe-ontology-integration-proof-cases.json"
    bad_fixture.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    completed = run_cli("--fixtures", str(bad_fixture), "--no-write")
    summary = parse_stdout(completed)
    serialized = json.dumps(summary, ensure_ascii=False)

    assert completed.returncode == 1
    assert summary["redaction_ok"] is False
    assert summary["gate_disposition"] == "bounded_fixture_integration_failed_gate_remains_open"
    assert "provider_payload" not in serialized
    assert any(code == "forbidden_payload_field" for code in summary["diagnostic_code_inventory"])
