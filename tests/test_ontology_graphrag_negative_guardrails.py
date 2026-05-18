from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF_PATH = ROOT / "scripts" / "verify-ontology-graphrag-integration-proof.py"
FIXTURE_PATH = ROOT / "prd" / "research" / "ontology_architecture_requirements" / "ontology_graphrag_proof_cases.json"


def run_proof(*args: str) -> subprocess.CompletedProcess[str]:
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


def write_fixture(tmp_path: Path, **updates: object) -> Path:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    data.update(updates)
    fixture = tmp_path / "negative-ontology-graphrag-proof-cases.json"
    fixture.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return fixture


def test_generated_query_missing_evidence_path_and_temporal_constraint_fails_closed(tmp_path: Path) -> None:
    fixture = write_fixture(
        tmp_path,
        generated_query_candidates=[
            {
                "case_id": "CASE-M020-OG-GENERATED-QUERY-MISSING-PROOF-PATH",
                "requires_as_of": True,
                "query": "MATCH (article:Article {id: $article_id}) RETURN article.id LIMIT 1",
            }
        ],
    )

    completed = run_proof("--fixtures", str(fixture), "--no-write")
    summary = parse_stdout(completed)

    assert completed.returncode == 1
    assert summary["gate_disposition"] == "bounded_fixture_integration_failed_gate_remains_open"
    assert summary["query_safety"] == {
        "generated_query_execution_avoided": True,
        "generated_query_candidates_present": True,
        "execution_like_step_performed": False,
        "status": "failed_closed",
        "rejection_codes": ["E_EVIDENCE_REQUIRED", "E_TEMPORAL_REQUIRED"],
        "future_generated_query_requirement": "Validate through prd/06_m002_cypher_safety_contract.md before any execution-like step.",
    }
    assert "E_EVIDENCE_REQUIRED" in summary["diagnostic_code_inventory"]
    assert "E_TEMPORAL_REQUIRED" in summary["diagnostic_code_inventory"]
    assert "MATCH (article" not in json.dumps(summary, ensure_ascii=False)


def test_generated_query_write_operation_is_rejected_before_execution(tmp_path: Path) -> None:
    fixture = write_fixture(
        tmp_path,
        generated_query_candidates=[
            {
                "case_id": "CASE-M020-OG-GENERATED-QUERY-WRITE",
                "requires_as_of": False,
                "query": "MATCH (article:Article) DETACH DELETE article RETURN article.id LIMIT 1",
            }
        ],
    )

    completed = run_proof("--fixtures", str(fixture), "--no-write")
    summary = parse_stdout(completed)

    assert completed.returncode == 1
    assert summary["query_safety"]["status"] == "failed_closed"
    assert "E_WRITE_OPERATION" in summary["query_safety"]["rejection_codes"]
    assert summary["query_safety"]["execution_like_step_performed"] is False


def test_positive_overclaim_wording_fails_gate_disposition_without_mutating_non_claims(tmp_path: Path) -> None:
    fixture = write_fixture(
        tmp_path,
        proof_report_claims=[
            "The bounded proof is safe to inspect.",
            "R035 validated and product retrieval quality proven.",
        ],
    )

    completed = run_proof("--fixtures", str(fixture), "--no-write")
    summary = parse_stdout(completed)

    assert completed.returncode == 1
    assert summary["gate_disposition"] == "bounded_fixture_integration_failed_gate_remains_open"
    assert summary["overclaim_safety"] == {
        "status": "failed_closed",
        "diagnostic_codes": ["overclaim_wording_detected"],
        "claim_count": 2,
    }
    assert "overclaim_wording_detected" in summary["diagnostic_code_inventory"]
    assert any("Does not validate R035" in non_claim for non_claim in summary["non_claims"])


def test_tracked_report_keeps_negative_guardrail_diagnostics_visible() -> None:
    completed = run_proof("--no-write")
    summary = parse_stdout(completed)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    for code in [
        "temporal_filter_excluded",
        "wrong_edition",
        "missing_required_field",
        "unsupported_ontology_filter",
        "ambiguous_candidate_set",
        "scoped_no_answer",
        "forbidden_payload_field",
    ]:
        assert code in summary["diagnostic_code_inventory"]
    assert summary["query_safety"]["generated_query_execution_avoided"] is True
    assert summary["overclaim_safety"]["status"] == "passed"
