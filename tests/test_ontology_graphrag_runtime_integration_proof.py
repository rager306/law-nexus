from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-ontology-graphrag-runtime-integration-proof.py"

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
    "runtime_row",
    "generated_query",
    "generated_cypher",
    "legal_advice",
    "llm_reasoning",
    ".gsd/exec",
    "/root/",
    "/tmp/",
    "MATCH (",
}


def load_module(name: str = "runtime_integration_proof") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def confirmed_embedding(module: ModuleType) -> dict[str, Any]:
    return {
        "schema_version": "local-retrieval-runtime-boundary/v1",
        "model_id": "deepvk/USER-bge-m3",
        "execution_mode": "local_open_weight",
        "runtime_status": "confirmed_runtime",
        "failure_class": "none",
        "diagnostic_codes": [],
        "managed_api_used": False,
        "giga_chat_used": False,
        "network_used": False,
        "raw_vectors_persisted": False,
        "raw_legal_text_persisted": False,
        "provider_payload_persisted": False,
        "redaction": module.REDACTION_FLAGS,
        "expected_vector_dimension": 1024,
        "vector_dimension": 1024,
    }


def blocked_embedding(module: ModuleType, status: str = "blocked_model_unavailable", codes: list[str] | None = None) -> dict[str, Any]:
    payload = confirmed_embedding(module)
    payload.pop("vector_dimension")
    payload["runtime_status"] = status
    payload["failure_class"] = "model_unavailable" if status == "blocked_model_unavailable" else "policy_violation"
    payload["diagnostic_codes"] = codes or ["LRR_MODEL_CACHE_MISSING"]
    return payload


def good_integration_summary() -> dict[str, Any]:
    return {
        "mismatch_count": 0,
        "total_cases": 7,
        "filter_trace_summary": {"temporal_excluded_count": 1},
        "citation_validation_status": {
            "validated_count": 2,
            "failed_count": 2,
            "skipped_count": 3,
            "missing_citation_or_evidence_count": 1,
            "status": "passed",
        },
        "query_safety": {
            "generated_query_execution_avoided": True,
            "generated_query_candidates_present": False,
            "execution_like_step_performed": False,
        },
        "overclaim_safety": {"status": "passed", "claim_count": 4},
    }


def runner_for(summary: dict[str, Any]):
    def run(_fixtures: Path, _output: Path) -> tuple[int, dict[str, Any]]:
        return (0 if summary.get("mismatch_count") == 0 else 1), summary

    return run


def assert_runtime_summary_is_safe(module: ModuleType, summary: dict[str, Any]) -> None:
    module.assert_safe_payload(summary)
    serialized = json.dumps(summary, ensure_ascii=False)
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in serialized
    assert summary["schema_version"] == "ontology-graphrag-runtime-integration-proof/v1"
    assert summary["proof_id"] == "OG-M020-S07-RUNTIME-INTEGRATION-PROOF"
    assert summary["requirement"] == "R035"
    assert summary["non_authoritative"] is True
    assert summary["r035_lifecycle_disposition"] == "remains_active_bounded_runtime_evidence_only"
    assert summary["gate_disposition"].startswith("gate_remains_open")
    assert set(summary["phases"]) == set(module.PHASES)
    assert set(summary["phase_status_vocabulary"]) == {"passed", "blocked", "failed_closed", "not_run"}
    assert all(summary["redaction"].values())
    assert any("R035 remains Active" in claim for claim in summary["non_claims"])
    assert any("Does not satisfy broad ontology" in claim for claim in summary["non_claims"])


def test_confirmed_runtime_contract_pins_all_phase_statuses(tmp_path: Path) -> None:
    module = load_module("runtime_integration_confirmed")

    exit_code, summary = module.build_summary(
        report_output=tmp_path / "runtime-proof.json",
        allow_blocked_runtime=False,
        embedding_report=confirmed_embedding(module),
        falkordb_report={"status": "confirmed-runtime", "query_proofs": []},
        integration_runner=runner_for(good_integration_summary()),
    )

    assert exit_code == 0
    assert summary["runtime_disposition"] == "bounded_runtime_proof_passed"
    assert {phase["status"] for phase in summary["phases"].values()} == {"passed"}
    assert summary["phases"]["embedding_runtime"] == {
        "status": "passed",
        "diagnostic_codes": [],
        "runtime_status": "confirmed_runtime",
        "model_id": "deepvk/USER-bge-m3",
        "execution_mode": "local_open_weight",
    }
    assert_runtime_summary_is_safe(module, summary)


def test_blocked_runtime_rescope_is_explicit_and_keeps_r035_active(tmp_path: Path) -> None:
    module = load_module("runtime_integration_blocked")

    exit_code, summary = module.build_summary(
        report_output=tmp_path / "blocked-runtime-proof.json",
        allow_blocked_runtime=True,
        embedding_report=blocked_embedding(module),
        falkordb_report=None,
        integration_runner=runner_for(good_integration_summary()),
    )

    assert exit_code == 0
    assert summary["runtime_disposition"] == "blocked_runtime_rescope"
    assert summary["phases"]["embedding_runtime"]["status"] == "blocked"
    assert summary["phases"]["embedding_runtime"]["diagnostic_codes"] == ["LRR_MODEL_CACHE_MISSING"]
    assert summary["phases"]["falkordb_runtime"] == {
        "status": "blocked",
        "diagnostic_codes": ["RIP_FALKORDB_RUNTIME_NOT_AVAILABLE"],
        "evidence_class": "blocked_rescope",
    }
    assert summary["phases"]["r035_lifecycle_disposition"]["disposition"] == "remains_active"
    assert_runtime_summary_is_safe(module, summary)




def test_s08_contract_exposes_metadata_graph_route_ranking_and_diagnostics(tmp_path: Path) -> None:
    module = load_module("runtime_integration_s08_contract")

    exit_code, summary = module.build_summary(
        report_output=tmp_path / "runtime-proof.json",
        allow_blocked_runtime=False,
        embedding_report=confirmed_embedding(module),
        falkordb_report={"status": "confirmed-runtime", "query_proofs": [{"query_class": "synthetic_traversal"}]},
        integration_runner=runner_for(good_integration_summary()),
    )

    assert exit_code == 0
    assert summary["milestone_id"] == "M020-ujbffl"
    assert summary["remediation_slice_ids"] == ["S07", "S08"]
    assert summary["s08_contract_version"] == "runtime-proof-s08-diagnostics/v1"

    assert summary["graph_route"] == {
        "status": "confirmed_synthetic_local_route",
        "route_class": "local_falkordb_synthetic_legalgraph_shape",
        "falkordb_runtime_status": "confirmed-runtime",
        "real_artifact_graph_querying_proven": False,
        "candidate_query_execution_performed": False,
        "positive_falkordb_validation_claim": False,
        "diagnostic_codes": [],
    }

    ranking = summary["embedding_candidate_ranking"]
    assert ranking["status"] == "available_safe_ids_only"
    assert ranking["embedding_runtime"] == "confirmed_runtime"
    assert ranking["model_boundary"] == "local_open_weight"
    assert ranking["managed_provider_used"] is False
    assert ranking["vector_values_excluded"] is True
    assert ranking["raw_text_excluded"] is True
    assert ranking["selected_rank"] == 1
    assert ranking["selected_candidate_id"].startswith("CAND-")
    assert ranking["candidates"][0] == {
        "rank": 1,
        "candidate_id": "CAND-M020-OG-VALID-CURRENT-001",
        "source_record_id": "HIER-CONS-ARTICLE-0001",
        "citation_key": "CIT-M014-HIER-CONS-ARTICLE-0001",
        "evidence_span_id": "EV-M014-HIER-CONS-ARTICLE-0001",
        "act_edition_id": "ED-M014-44FZ-2026-01-01",
        "selection_result": "accepted",
    }

    evidence = summary["deterministic_evidence_id_diagnostics"]
    assert evidence["status"] == "passed"
    assert evidence["accepted_cases_checked"] >= 1
    assert evidence["missing_id_negative_cases_detected"] is True
    assert evidence["raw_text_excluded"] is True

    stale = summary["stale_evidence_diagnostics"]
    assert stale == {
        "status": "passed",
        "temporal_excluded_count": 1,
        "inactive_or_wrong_edition_exclusion_present": True,
        "raw_text_excluded": True,
        "diagnostic_codes": [],
    }
    assert_runtime_summary_is_safe(module, summary)


def test_s08_blocked_mode_preserves_diagnostic_slots_without_positive_runtime_claim(tmp_path: Path) -> None:
    module = load_module("runtime_integration_s08_blocked_slots")

    exit_code, summary = module.build_summary(
        report_output=tmp_path / "blocked-runtime-proof.json",
        allow_blocked_runtime=True,
        embedding_report=blocked_embedding(module),
        falkordb_report=None,
        integration_runner=runner_for(good_integration_summary()),
    )

    assert exit_code == 0
    assert summary["runtime_disposition"] == "blocked_runtime_rescope"
    assert summary["graph_route"] == {
        "status": "blocked_runtime_rescope",
        "route_class": "unavailable_without_falkordb_runtime",
        "falkordb_runtime_status": "missing",
        "real_artifact_graph_querying_proven": False,
        "candidate_query_execution_performed": False,
        "positive_falkordb_validation_claim": False,
        "diagnostic_codes": ["RIP_FALKORDB_RUNTIME_NOT_AVAILABLE"],
    }
    ranking = summary["embedding_candidate_ranking"]
    assert ranking["status"] == "unavailable_blocked_runtime"
    assert ranking["embedding_runtime"] == "blocked_model_unavailable"
    assert ranking["selected_rank"] is None
    assert ranking["candidates"] == []
    assert ranking["vector_values_excluded"] is True
    assert summary["deterministic_evidence_id_diagnostics"]["status"] == "passed"
    assert summary["stale_evidence_diagnostics"]["status"] == "passed"
    assert_runtime_summary_is_safe(module, summary)


def test_s08_deterministic_evidence_ids_fail_closed_when_accepted_ids_are_missing(tmp_path: Path) -> None:
    module = load_module("runtime_integration_s08_missing_ids")
    bad_summary = good_integration_summary()
    bad_summary["citation_validation_status"] = {
        "validated_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "missing_citation_or_evidence_count": 0,
        "status": "check_diagnostics",
    }

    exit_code, summary = module.build_summary(
        report_output=tmp_path / "missing-ids.json",
        allow_blocked_runtime=True,
        embedding_report=confirmed_embedding(module),
        falkordb_report={"status": "confirmed-runtime"},
        integration_runner=runner_for(bad_summary),
    )

    assert exit_code == 1
    assert summary["deterministic_evidence_id_diagnostics"] == {
        "status": "failed_closed",
        "accepted_cases_checked": 0,
        "missing_id_negative_cases_detected": False,
        "raw_text_excluded": True,
        "diagnostic_codes": ["RIP_DETERMINISTIC_EVIDENCE_IDS_MISSING"],
    }
    assert summary["phases"]["citation_evidence_validation"]["status"] == "failed_closed"
    assert_runtime_summary_is_safe(module, summary)

def test_falkordb_unavailable_without_explicit_blocked_mode_fails_closed(tmp_path: Path) -> None:
    module = load_module("runtime_integration_falkordb_required")

    exit_code, summary = module.build_summary(
        report_output=tmp_path / "missing-falkordb.json",
        allow_blocked_runtime=False,
        embedding_report=confirmed_embedding(module),
        falkordb_report=None,
        integration_runner=runner_for(good_integration_summary()),
    )

    assert exit_code == 1
    assert summary["runtime_disposition"] == "failed_closed"
    assert summary["phases"]["falkordb_runtime"] == {
        "status": "failed_closed",
        "diagnostic_codes": ["RIP_FALKORDB_RUNTIME_REQUIRED"],
        "evidence_class": "missing",
    }
    assert_runtime_summary_is_safe(module, summary)


def test_managed_api_embedding_signal_is_blocked_without_provider_payload(tmp_path: Path) -> None:
    module = load_module("runtime_integration_managed_api")

    exit_code, summary = module.build_summary(
        report_output=tmp_path / "managed-api-blocked.json",
        allow_blocked_runtime=True,
        embedding_report=blocked_embedding(module, "blocked_policy_violation", ["LRR_MANAGED_API_FORBIDDEN"]),
        falkordb_report={"status": "blocked-environment"},
        integration_runner=runner_for(good_integration_summary()),
    )

    assert exit_code == 0
    assert summary["phases"]["embedding_runtime"] == {
        "status": "blocked",
        "diagnostic_codes": ["LRR_MANAGED_API_FORBIDDEN"],
        "runtime_status": "blocked_policy_violation",
    }
    serialized = json.dumps(summary, ensure_ascii=False)
    assert "redacted-test-value" not in serialized
    assert "GIGACHAT_AUTH_DATA" not in serialized
    assert_runtime_summary_is_safe(module, summary)


def test_fixture_contract_requires_inactive_temporal_and_missing_evidence_negative_cases(tmp_path: Path) -> None:
    module = load_module("runtime_integration_negative_cases")
    bad_summary = good_integration_summary()
    bad_summary["filter_trace_summary"] = {"temporal_excluded_count": 0}
    bad_summary["citation_validation_status"] = {
        "validated_count": 1,
        "failed_count": 0,
        "skipped_count": 0,
        "missing_citation_or_evidence_count": 0,
        "status": "check_diagnostics",
    }

    exit_code, summary = module.build_summary(
        report_output=tmp_path / "negative-case-failure.json",
        allow_blocked_runtime=True,
        embedding_report=confirmed_embedding(module),
        falkordb_report={"status": "confirmed-runtime"},
        integration_runner=runner_for(bad_summary),
    )

    assert exit_code == 1
    assert summary["phases"]["ontology_temporal_query"] == {
        "status": "failed_closed",
        "diagnostic_codes": ["RIP_TEMPORAL_NEGATIVE_CASE_MISSING"],
    }
    assert summary["phases"]["citation_evidence_validation"] == {
        "status": "failed_closed",
        "diagnostic_codes": ["RIP_CITATION_EVIDENCE_VALIDATION_FAILED"],
    }
    assert_runtime_summary_is_safe(module, summary)


def test_unsafe_payload_fields_and_generated_query_text_are_rejected() -> None:
    module = load_module("runtime_integration_unsafe_payload")
    payload = module.base_summary(ROOT / "runtime-proof.json")
    payload["phases"]["query_safety"] = {
        "status": "failed_closed",
        "diagnostic_codes": ["RIP_QUERY_SAFETY_FAILED"],
        "generated_query": "MATCH (n) RETURN n",
    }

    try:
        module.assert_safe_payload(payload)
    except module.RuntimeIntegrationProofError as exc:
        assert "unsafe payload" in str(exc)
    else:
        raise AssertionError("unsafe generated-query payload must be rejected")


def test_overclaim_wording_fails_closed_before_artifact_write() -> None:
    module = load_module("runtime_integration_overclaim")
    payload = module.base_summary(ROOT / "runtime-proof.json")
    payload["non_claims"] = ["R035 validated by local runtime proof"]

    try:
        module.assert_safe_payload(payload)
    except module.RuntimeIntegrationProofError as exc:
        assert "overclaim" in str(exc)
    else:
        raise AssertionError("overclaim wording must be rejected")


def test_cli_blocked_mode_writes_safe_rescope_artifact(tmp_path: Path) -> None:
    report = tmp_path / "cli-blocked-runtime.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--allow-blocked-runtime",
            "--skip-falkordb-runtime",
            "--report-output",
            str(report),
        ],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    summary = json.loads(completed.stdout)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert persisted == summary
    assert summary["runtime_disposition"] in {"blocked_runtime_rescope", "bounded_runtime_proof_passed"}
    assert summary["r035_lifecycle_disposition"] == "remains_active_bounded_runtime_evidence_only"
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in completed.stdout


def test_cli_accepts_required_t02_flag_aliases() -> None:
    module = load_module("runtime_integration_cli_flags")

    args = module.parse_args([
        "--allow-blocked",
        "--host",
        "127.0.0.1",
        "--port",
        "6391",
        "--readiness-timeout",
        "2",
        "--no-container",
        "--no-write",
    ])

    assert args.allow_blocked_runtime is True
    assert args.host == "127.0.0.1"
    assert args.port == 6391
    assert args.readiness_timeout == 2
    assert args.container == "never"
    assert args.no_write is True


def test_markdown_report_is_safe_and_keeps_r035_active(tmp_path: Path) -> None:
    module = load_module("runtime_integration_markdown")
    _, summary = module.build_summary(
        report_output=tmp_path / "runtime-proof.json",
        allow_blocked_runtime=False,
        embedding_report=confirmed_embedding(module),
        falkordb_report={"status": "confirmed-runtime", "query_proofs": []},
        integration_runner=runner_for(good_integration_summary()),
    )
    summary["container_runtime"] = {"mode": "never", "status": "skipped_by_flag", "cleanup_status": "not_needed"}
    summary["cleanup_status"] = "not_needed"
    report = tmp_path / "13-r035-runtime-integration-remediation.md"

    module.write_markdown_report(report, summary)

    text = report.read_text(encoding="utf-8")
    assert "R035 remains Active" in text
    assert "bounded_runtime_proof_passed" in text
    assert "## Graph route" in text
    assert "## Local/open-weight embedding ranking summary" in text
    assert "## Deterministic evidence-ID validation" in text
    assert "## Stale-evidence diagnostics" in text
    assert "## S01-to-S02 handoff clarification" in text
    assert "does not reinterpret S01/S02 as legal-answer" in text
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in text
