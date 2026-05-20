# pyright: reportMissingImports=false
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from source_lifecycle import (  # noqa: E402
    GRAPH_CONTEXT_DIAGNOSTIC_SCHEMA_VERSION,
    GRAPH_CONTEXT_RECORD_KINDS,
    GRAPH_CONTEXT_STAGING_SCHEMA_VERSION,
    export_graph_context_staging,
    graph_context_candidate_to_record,
)


def accepted_candidate() -> dict[str, object]:
    return {
        "candidate_id": "CAND-abc123def456",
        "candidate_kind": "relationship_candidate",
        "candidate_summary": "Repeated amendment-reference structure suggests a bounded relationship candidate.",
        "confidence_bucket": "medium",
        "trajectory_refs": ["trajectory:STEP-abc123def456"],
        "attempt_refs": ["attempt:ATTEMPT-abc123def456"],
        "source_refs": ["processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"],
    }


def accepted_decision() -> dict[str, object]:
    return {
        "decision_id": "DECISION-abc123def456",
        "candidate_id": "CAND-abc123def456",
        "verifier_status": "accepted",
        "checked_refs": ["processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"],
        "acceptance_evidence_refs": ["processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"],
    }


def test_graph_context_staging_record_contains_required_provenance_and_non_claims() -> None:
    result = graph_context_candidate_to_record(
        accepted_candidate(),
        accepted_decision(),
        run_id="RUN-abc123def456",
    )

    assert result["schema_version"] == GRAPH_CONTEXT_STAGING_SCHEMA_VERSION
    assert result["staging_status"] == "staged"
    assert result["record_kind"] == "relationship_candidate"
    assert result["candidate_refs"] == ["candidate:CAND-abc123def456"]
    assert result["verifier_refs"] == ["decision:DECISION-abc123def456"]
    assert result["trajectory_refs"] == ["trajectory:STEP-abc123def456"]
    assert result["source_refs"] == ["processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"]
    assert result["non_authoritative"] is True
    assert "graph_context staging does not validate R035" in result["non_claims"]
    assert "graph_context staging does not validate R037" in result["non_claims"]
    assert "graph_context staging does not validate R038" in result["non_claims"]


def test_graph_context_staging_rejects_non_accepted_verifier_status_as_diagnostic() -> None:
    decision = accepted_decision()
    decision["verifier_status"] = "needs_review"

    result = graph_context_candidate_to_record(
        accepted_candidate(),
        decision,
        run_id="RUN-abc123def456",
    )

    assert result["schema_version"] == GRAPH_CONTEXT_DIAGNOSTIC_SCHEMA_VERSION
    assert result["diagnostic_status"] == "skipped"
    assert "verifier-status-not-accepted" in result["reason_codes"]
    assert result["candidate_id"] == "CAND-abc123def456"
    assert result["decision_id"] == "DECISION-abc123def456"
    assert result["non_authoritative"] is True


def test_graph_context_staging_requires_safe_source_refs() -> None:
    candidate = accepted_candidate()
    candidate["source_refs"] = ["/absolute/local/path.xml"]

    result = graph_context_candidate_to_record(
        candidate,
        accepted_decision(),
        run_id="RUN-abc123def456",
    )

    assert result["schema_version"] == GRAPH_CONTEXT_DIAGNOSTIC_SCHEMA_VERSION
    assert result["diagnostic_status"] == "skipped"
    assert "unsafe-source-ref" in result["reason_codes"]
    assert "/absolute/local/path.xml" not in str(result)


def test_graph_context_record_kinds_are_bounded_to_source_discovery_candidates() -> None:
    assert GRAPH_CONTEXT_RECORD_KINDS == {
        "source_pattern_observation",
        "artifact_candidate",
        "structure_candidate",
        "relationship_candidate",
        "graph_context_signal",
    }

    candidate = accepted_candidate()
    candidate["candidate_kind"] = "legal_truth_claim"
    result = graph_context_candidate_to_record(
        candidate,
        accepted_decision(),
        run_id="RUN-abc123def456",
    )

    assert result["schema_version"] == GRAPH_CONTEXT_DIAGNOSTIC_SCHEMA_VERSION
    assert "unsupported-record-kind" in result["reason_codes"]


def test_cli_graph_context_stage_smoke(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    mock_response = tmp_path / "mock-response.json"
    response = {
        "candidates": [
            {
                "candidate_kind": "relationship_candidate",
                "candidate_summary": "Repeated amendment-reference structure suggests a bounded relationship candidate.",
                "supporting_context": "Open legal/source context explains the repeated structure.",
                "confidence_bucket": "medium",
            }
        ]
    }
    mock_response.write_text(
        json.dumps({"response_summary": json.dumps(response, ensure_ascii=False)}, ensure_ascii=False),
        encoding="utf-8",
    )
    run_id = "RUN-abc123def456"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "source_cli.py"),
            "--workspace",
            str(workspace),
            "discover",
            "--run-id",
            run_id,
            "--source-ref",
            "processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl",
            "--prompt-summary",
            "Use open legal/source context to discover graph-context structures.",
            "--mock-response",
            str(mock_response),
            "--verify-candidates",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "source_cli.py"),
            "--workspace",
            str(workspace),
            "graph-context-stage",
            run_id,
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "graph_context_staging_exported"
    assert payload["staged"] == 1
    assert payload["skipped"] == 0
    assert payload["staging_ref"] == "runtime/graph-context/RUN-abc123def456/graph_context_staging.jsonl"
    assert (workspace / payload["staging_ref"]).is_file()
    assert (workspace / payload["diagnostics_ref"]).is_file()
    assert (workspace / payload["summary_ref"]).is_file()
    staging_rows = [
        json.loads(line)
        for line in (workspace / payload["staging_ref"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert staging_rows[0]["schema_version"] == GRAPH_CONTEXT_STAGING_SCHEMA_VERSION
    assert staging_rows[0]["non_authoritative"] is True
    assert "graph_context staging does not validate R037" in staging_rows[0]["non_claims"]


def test_export_graph_context_staging_writes_staging_diagnostics_and_summary(tmp_path: Path) -> None:
    skipped_decision = accepted_decision()
    skipped_decision["decision_id"] = "DECISION-def456abc123"
    skipped_decision["verifier_status"] = "needs_review"
    skipped_decision["candidate_id"] = "CAND-def456abc123"
    skipped_candidate = accepted_candidate()
    skipped_candidate["candidate_id"] = "CAND-def456abc123"

    result = export_graph_context_staging(
        tmp_path,
        run_id="RUN-abc123def456",
        candidate_rows=[accepted_candidate(), skipped_candidate],
        decision_rows=[accepted_decision(), skipped_decision],
        review_pack_refs=["runtime/external-review/RUN-abc123def456/review_pack.json"],
    )

    assert result["status"] == "graph_context_staging_exported"
    assert result["staged"] == 1
    assert result["skipped"] == 1
    assert result["diagnostics"] == 1
    assert result["staging_ref"] == "runtime/graph-context/RUN-abc123def456/graph_context_staging.jsonl"
    assert result["diagnostics_ref"] == "runtime/graph-context/RUN-abc123def456/graph_context_diagnostics.jsonl"
    assert result["summary_ref"] == "runtime/graph-context/RUN-abc123def456/graph_context_summary.json"

    staging_rows = [
        json.loads(line)
        for line in (tmp_path / result["staging_ref"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    diagnostic_rows = [
        json.loads(line)
        for line in (tmp_path / result["diagnostics_ref"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    summary = json.loads((tmp_path / result["summary_ref"]).read_text(encoding="utf-8"))

    assert len(staging_rows) == 1
    assert staging_rows[0]["schema_version"] == GRAPH_CONTEXT_STAGING_SCHEMA_VERSION
    assert staging_rows[0]["review_pack_refs"] == ["runtime/external-review/RUN-abc123def456/review_pack.json"]
    assert len(diagnostic_rows) == 1
    assert diagnostic_rows[0]["schema_version"] == GRAPH_CONTEXT_DIAGNOSTIC_SCHEMA_VERSION
    assert "verifier-status-not-accepted" in diagnostic_rows[0]["reason_codes"]
    assert summary["status"] == "graph_context_staging_exported"
    assert summary["accepted"] == 1
    assert summary["staged"] == 1
    assert summary["skipped"] == 1
    assert summary["diagnostics"] == 1
    assert summary["non_authoritative"] is True


def test_export_graph_context_staging_diagnoses_unmatched_candidates(tmp_path: Path) -> None:
    result = export_graph_context_staging(
        tmp_path,
        run_id="RUN-abc123def456",
        candidate_rows=[accepted_candidate()],
        decision_rows=[],
    )

    assert result["staged"] == 0
    assert result["skipped"] == 1
    diagnostics = [
        json.loads(line)
        for line in (tmp_path / result["diagnostics_ref"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert diagnostics[0]["candidate_id"] == "CAND-abc123def456"
    assert "missing-verifier-decision" in diagnostics[0]["reason_codes"]
