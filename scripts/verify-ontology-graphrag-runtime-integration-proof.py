#!/usr/bin/env python3
"""Compose the bounded M020 ontology GraphRAG runtime-integration proof contract.

This command is intentionally narrow. It composes the existing fixture-backed
ontology GraphRAG proof, the local/open-weight embedding boundary diagnostic,
and a local FalkorDB runtime diagnostic into one safe payload. It may emit a
blocked-runtime rescope artifact, but it must not claim broad R035 validation,
product retrieval quality, graph-vector behavior, parser completeness,
FalkorDB production readiness, pilot readiness, or legal-answer correctness.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, cast

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json"
DEFAULT_REPORT = ROOT / "prd/research/ontology_architecture_requirements/ontology_graphrag_runtime_integration_proof.json"
DEFAULT_MARKDOWN_REPORT = ROOT / "prd/research/ontology_architecture_requirements/13-r035-runtime-integration-remediation.md"
INTEGRATION_PROOF_PATH = ROOT / "scripts/verify-ontology-graphrag-integration-proof.py"
RUNTIME_CHECK_PATH = ROOT / "scripts/check-local-retrieval-runtime.py"
FALKORDB_PROOF_PATH = ROOT / "scripts/prove-legalgraph-shaped-falkordb.py"

SCHEMA_VERSION = "ontology-graphrag-runtime-integration-proof/v1"
PROOF_ID = "OG-M020-S07-RUNTIME-INTEGRATION-PROOF"
REQUIREMENT_ID = "R035"
MILESTONE_ID = "M020-ujbffl"
S08_CONTRACT_VERSION = "runtime-proof-s08-diagnostics/v1"
REMEDIATION_SLICE_IDS = ["S07", "S08"]

PhaseStatus = Literal["passed", "blocked", "failed_closed", "not_run"]
PHASES: tuple[str, ...] = (
    "embedding_runtime",
    "falkordb_runtime",
    "fixture_materialization",
    "ontology_temporal_query",
    "citation_evidence_validation",
    "query_safety",
    "overclaim_safety",
    "r035_lifecycle_disposition",
)
STATUS_VOCABULARY = frozenset({"passed", "blocked", "failed_closed", "not_run"})

REDACTION_FLAGS = {
    "source_text_excluded": True,
    "query_text_excluded": True,
    "vector_values_excluded": True,
    "managed_provider_details_excluded": True,
    "secrets_excluded": True,
    "absolute_paths_excluded": True,
    "gsd_exec_paths_excluded": True,
    "legal_opinion_excluded": True,
}

NON_CLAIMS = (
    "Does not validate R035 broadly; R035 remains Active.",
    "Does not satisfy broad ontology, product retrieval, graph-vector, parser, legal-answer, FalkorDB production, or pilot-readiness gates.",
    "Does not prove product retrieval quality, representative corpus quality, parser completeness, or legal-answer correctness.",
    "Does not prove generated-query quality, graph-vector behavior, HNSW behavior, hybrid retrieval quality, or LLM authority.",
)

FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "raw_legal_text",
        "raw_text",
        "source_excerpt",
        "source_excerpts",
        "prompt",
        "user_prompt",
        "provider_payload",
        "provider_response_body",
        "secret",
        "secrets",
        "pii",
        "vector",
        "embedding_vector",
        "falkordb_row",
        "runtime_row",
        "generated_query",
        "generated_cypher",
        "generated_answer_prose",
        "legal_advice",
        "llm_reasoning",
    }
)
FORBIDDEN_OUTPUT_FRAGMENTS = (
    "GIGACHAT" + "_AUTH_DATA",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    "api-key",
    "authorization",
    "Федеральный закон",
    "Статья 1.",
    "MATCH (",
    "CREATE (",
    "embedding_vector",
    "provider_payload",
    ".gsd/exec",
    "/root/",
    "/tmp/",
)
FORBIDDEN_OVERCLAIM_PHRASES = frozenset(
    {
        "r035 validated",
        "validates r035",
        "r035 is validated",
        "r035 complete",
        "gate-ontology-graphrag-integration satisfied",
        "product retrieval quality proven",
        "legal correctness proven",
        "parser completeness proven",
        "falkordb production behavior proven",
        "graph-vector behavior proven",
        "pilot readiness proven",
        "llm output is legal authority",
    }
)


class RuntimeIntegrationProofError(RuntimeError):
    """Raised when the runtime proof payload cannot be emitted safely."""


def _load_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeIntegrationProofError(f"unable to import {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bounded_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return "<outside-project>"


def phase(status: PhaseStatus, diagnostic_codes: Sequence[str] = (), **details: Any) -> dict[str, Any]:
    if status not in STATUS_VOCABULARY:
        raise RuntimeIntegrationProofError("invalid phase status")
    payload: dict[str, Any] = {"status": status, "diagnostic_codes": sorted(set(diagnostic_codes))}
    payload.update(details)
    return payload


def _walk_forbidden(value: Any, path: str = "$", hits: list[str] | None = None) -> list[str]:
    found = hits if hits is not None else []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            field_path = f"{path}.{key}" if path != "$" else str(key)
            if str(key).lower() in FORBIDDEN_FIELD_NAMES:
                found.append(field_path)
            _walk_forbidden(nested, field_path, found)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _walk_forbidden(nested, f"{path}[{index}]", found)
    return found


def assert_no_overclaim(claims: Sequence[str]) -> None:
    for claim in claims:
        normalized = " ".join(claim.lower().split())
        if any(phrase in normalized for phrase in FORBIDDEN_OVERCLAIM_PHRASES):
            raise RuntimeIntegrationProofError("overclaim wording detected")


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    forbidden_paths = _walk_forbidden(payload)
    if forbidden_paths:
        raise RuntimeIntegrationProofError("unsafe payload field detected")
    redaction = payload.get("redaction")
    if not isinstance(redaction, Mapping) or any(value is not True for value in redaction.values()):
        raise RuntimeIntegrationProofError("redaction flags must all be true")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    lowered = serialized.lower()
    for fragment in FORBIDDEN_OUTPUT_FRAGMENTS:
        if fragment.lower() in lowered:
            raise RuntimeIntegrationProofError("unsafe output fragment detected")
    claims = payload.get("non_claims")
    if not isinstance(claims, list) or not all(isinstance(claim, str) for claim in claims):
        raise RuntimeIntegrationProofError("non_claims must be string list")
    assert_no_overclaim(claims)


def base_summary(report_output: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "proof_id": PROOF_ID,
        "requirement": REQUIREMENT_ID,
        "source_fixture_path": bounded_path(FIXTURE_PATH),
        "report_path": bounded_path(report_output),
        "source_artifacts": [
            bounded_path(INTEGRATION_PROOF_PATH),
            bounded_path(RUNTIME_CHECK_PATH),
            bounded_path(FALKORDB_PROOF_PATH),
            bounded_path(FIXTURE_PATH),
        ],
        "non_authoritative": True,
        "proof_level": "bounded local runtime integration proof or blocked-runtime rescope",
        "redaction": dict(REDACTION_FLAGS),
        "phase_status_vocabulary": sorted(STATUS_VOCABULARY),
        "milestone_id": MILESTONE_ID,
        "remediation_slice_ids": list(REMEDIATION_SLICE_IDS),
        "s08_contract_version": S08_CONTRACT_VERSION,
        "remediation_scope": "M020 S07/S08 runtime proof persistence for R035 only",
        "phases": {name: phase("not_run", ["RIP_NOT_RUN"]) for name in PHASES},
        "graph_route": {
            "status": "not_run",
            "route_class": "not_run",
            "falkordb_runtime_status": "not_run",
            "real_artifact_graph_querying_proven": False,
            "candidate_query_execution_performed": False,
            "positive_falkordb_validation_claim": False,
            "diagnostic_codes": ["RIP_NOT_RUN"],
        },
        "embedding_candidate_ranking": {
            "status": "not_run",
            "embedding_runtime": "not_run",
            "model_boundary": "local_open_weight_required",
            "managed_provider_used": False,
            "vector_values_excluded": True,
            "raw_text_excluded": True,
            "selected_rank": None,
            "selected_candidate_id": None,
            "candidates": [],
            "diagnostic_codes": ["RIP_NOT_RUN"],
        },
        "deterministic_evidence_id_diagnostics": {
            "status": "not_run",
            "accepted_cases_checked": 0,
            "missing_id_negative_cases_detected": False,
            "raw_text_excluded": True,
            "diagnostic_codes": ["RIP_NOT_RUN"],
        },
        "stale_evidence_diagnostics": {
            "status": "not_run",
            "temporal_excluded_count": 0,
            "inactive_or_wrong_edition_exclusion_present": False,
            "raw_text_excluded": True,
            "diagnostic_codes": ["RIP_NOT_RUN"],
        },
        "runtime_disposition": "not_run",
        "container_runtime": {"mode": "not_requested", "status": "not_run", "cleanup_status": "not_needed"},
        "cleanup_status": "not_needed",
        "r035_lifecycle_disposition": "remains_active_runtime_contract_only",
        "gate_disposition": "gate_remains_open",
        "non_claims": list(NON_CLAIMS),
    }


def _safe_embedding_phase(runtime_report: Mapping[str, Any]) -> dict[str, Any]:
    status = runtime_report.get("runtime_status")
    diagnostic_codes = runtime_report.get("diagnostic_codes") if isinstance(runtime_report.get("diagnostic_codes"), list) else []
    if status == "confirmed_runtime":
        return phase("passed", diagnostic_codes, runtime_status=status, model_id=runtime_report.get("model_id"), execution_mode=runtime_report.get("execution_mode"))
    if status in {"blocked_environment", "blocked_model_unavailable", "not_run_contract_only", "blocked_policy_violation"}:
        return phase("blocked", diagnostic_codes or ["RIP_EMBEDDING_RUNTIME_BLOCKED"], runtime_status=status)
    return phase("failed_closed", diagnostic_codes or ["RIP_EMBEDDING_RUNTIME_FAILED_CLOSED"], runtime_status=status or "<missing>")


def _safe_falkordb_phase(falkordb_report: Mapping[str, Any] | None, *, explicit_blocked_mode: bool) -> dict[str, Any]:
    if falkordb_report is None:
        if explicit_blocked_mode:
            return phase("blocked", ["RIP_FALKORDB_RUNTIME_NOT_AVAILABLE"], evidence_class="blocked_rescope")
        return phase("failed_closed", ["RIP_FALKORDB_RUNTIME_REQUIRED"], evidence_class="missing")
    status = falkordb_report.get("status")
    if status in {"confirmed-runtime", "confirmed_runtime"}:
        return phase("passed", [], evidence_class="synthetic_runtime", runtime_status=status)
    if status in {"blocked-environment", "blocked_environment"} and explicit_blocked_mode:
        return phase("blocked", ["RIP_FALKORDB_RUNTIME_BLOCKED"], evidence_class="blocked_rescope", runtime_status=status)
    return phase("failed_closed", ["RIP_FALKORDB_RUNTIME_FAILED_CLOSED"], runtime_status=status or "<missing>")



def _safe_id(value: Any) -> str:
    if isinstance(value, str) and value and len(value) <= 160:
        return value
    return "<missing>"


def _fixture_cases() -> list[Mapping[str, Any]]:
    try:
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    cases = data.get("cases") if isinstance(data, Mapping) else None
    if not isinstance(cases, list):
        return []
    return [case for case in cases if isinstance(case, Mapping)]


def _s08_graph_route(falkordb_report: Mapping[str, Any] | None, falkordb_phase: Mapping[str, Any]) -> dict[str, Any]:
    phase_status = falkordb_phase.get("status")
    runtime_status = falkordb_phase.get("runtime_status") or (falkordb_report.get("status") if isinstance(falkordb_report, Mapping) else "missing")
    codes = falkordb_phase.get("diagnostic_codes") if isinstance(falkordb_phase.get("diagnostic_codes"), list) else []
    if phase_status == "passed":
        return {
            "status": "confirmed_synthetic_local_route",
            "route_class": "local_falkordb_synthetic_legalgraph_shape",
            "falkordb_runtime_status": _safe_id(runtime_status),
            "real_artifact_graph_querying_proven": False,
            "candidate_query_execution_performed": False,
            "positive_falkordb_validation_claim": False,
            "diagnostic_codes": [],
        }
    if phase_status == "blocked":
        return {
            "status": "blocked_runtime_rescope",
            "route_class": "unavailable_without_falkordb_runtime",
            "falkordb_runtime_status": _safe_id(runtime_status),
            "real_artifact_graph_querying_proven": False,
            "candidate_query_execution_performed": False,
            "positive_falkordb_validation_claim": False,
            "diagnostic_codes": sorted(str(code) for code in codes),
        }
    return {
        "status": "failed_closed",
        "route_class": "unavailable_failed_closed",
        "falkordb_runtime_status": _safe_id(runtime_status),
        "real_artifact_graph_querying_proven": False,
        "candidate_query_execution_performed": False,
        "positive_falkordb_validation_claim": False,
        "diagnostic_codes": sorted(str(code) for code in (codes or ["RIP_FALKORDB_RUNTIME_FAILED_CLOSED"])),
    }


def _s08_embedding_candidate_ranking(embedding_report: Mapping[str, Any], embedding_phase: Mapping[str, Any]) -> dict[str, Any]:
    runtime_status = _safe_id(embedding_report.get("runtime_status"))
    base = {
        "embedding_runtime": runtime_status,
        "model_boundary": "local_open_weight",
        "managed_provider_used": bool(embedding_report.get("managed_api_used", False)),
        "vector_values_excluded": True,
        "raw_text_excluded": True,
    }
    if embedding_phase.get("status") != "passed":
        return {
            "status": "unavailable_blocked_runtime" if embedding_phase.get("status") == "blocked" else "unavailable_failed_closed",
            **base,
            "selected_rank": None,
            "selected_candidate_id": None,
            "candidates": [],
            "diagnostic_codes": list(embedding_phase.get("diagnostic_codes", [])),
        }
    candidates: list[dict[str, Any]] = []
    for case in _fixture_cases():
        if case.get("expected_result") != "accepted":
            continue
        case_candidates = case.get("candidate_set") if isinstance(case.get("candidate_set"), list) else []
        for index, candidate in enumerate(case_candidates, start=1):
            if not isinstance(candidate, Mapping):
                continue
            candidates.append(
                {
                    "rank": len(candidates) + 1,
                    "candidate_id": _safe_id(candidate.get("candidate_id")),
                    "source_record_id": _safe_id(candidate.get("source_record_id")),
                    "citation_key": _safe_id(candidate.get("citation_key")),
                    "evidence_span_id": _safe_id(candidate.get("evidence_span_id")),
                    "act_edition_id": _safe_id(candidate.get("act_edition_id")),
                    "selection_result": "accepted",
                }
            )
    selected = candidates[0] if candidates else None
    return {
        "status": "available_safe_ids_only" if selected else "failed_closed_no_safe_candidates",
        **base,
        "selected_rank": selected["rank"] if selected else None,
        "selected_candidate_id": selected["candidate_id"] if selected else None,
        "candidates": candidates[:5],
        "diagnostic_codes": [] if selected else ["RIP_EMBEDDING_RANKING_SAFE_IDS_MISSING"],
    }


def _s08_deterministic_evidence_id_diagnostics(integration_summary: Mapping[str, Any]) -> dict[str, Any]:
    citation_status = integration_summary.get("citation_validation_status") if isinstance(integration_summary.get("citation_validation_status"), Mapping) else {}
    accepted_cases_checked = int(citation_status.get("validated_count", 0) or 0)
    missing_negative_cases = int(citation_status.get("missing_citation_or_evidence_count", 0) or 0)
    passed = accepted_cases_checked >= 1 and missing_negative_cases >= 1 and citation_status.get("status") == "passed"
    return {
        "status": "passed" if passed else "failed_closed",
        "accepted_cases_checked": accepted_cases_checked,
        "missing_id_negative_cases_detected": missing_negative_cases >= 1,
        "raw_text_excluded": True,
        "diagnostic_codes": [] if passed else ["RIP_DETERMINISTIC_EVIDENCE_IDS_MISSING"],
    }


def _s08_stale_evidence_diagnostics(integration_summary: Mapping[str, Any]) -> dict[str, Any]:
    filter_summary = integration_summary.get("filter_trace_summary") if isinstance(integration_summary.get("filter_trace_summary"), Mapping) else {}
    temporal_excluded = int(filter_summary.get("temporal_excluded_count", 0) or 0)
    passed = temporal_excluded >= 1
    return {
        "status": "passed" if passed else "failed_closed",
        "temporal_excluded_count": temporal_excluded,
        "inactive_or_wrong_edition_exclusion_present": passed,
        "raw_text_excluded": True,
        "diagnostic_codes": [] if passed else ["RIP_STALE_EVIDENCE_EXCLUSION_MISSING"],
    }


def _fixture_phases(integration_summary: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    mismatch_count = integration_summary.get("mismatch_count")
    citation_status = integration_summary.get("citation_validation_status") if isinstance(integration_summary.get("citation_validation_status"), Mapping) else {}
    query_safety = integration_summary.get("query_safety") if isinstance(integration_summary.get("query_safety"), Mapping) else {}
    overclaim = integration_summary.get("overclaim_safety") if isinstance(integration_summary.get("overclaim_safety"), Mapping) else {}
    filter_summary = integration_summary.get("filter_trace_summary") if isinstance(integration_summary.get("filter_trace_summary"), Mapping) else {}

    fixture_ok = mismatch_count == 0 and bool(integration_summary.get("total_cases"))
    citation_ok = citation_status.get("status") == "passed" and citation_status.get("missing_citation_or_evidence_count", 1) >= 1
    temporal_ok = filter_summary.get("temporal_excluded_count", 0) >= 1
    query_ok = query_safety.get("generated_query_execution_avoided") is True and query_safety.get("execution_like_step_performed") is False and query_safety.get("status", "passed") == "passed"
    overclaim_ok = overclaim.get("status") == "passed"

    return {
        "fixture_materialization": phase("passed" if fixture_ok else "failed_closed", [] if fixture_ok else ["RIP_FIXTURE_MISMATCH"], total_cases=integration_summary.get("total_cases", 0)),
        "ontology_temporal_query": phase("passed" if temporal_ok else "failed_closed", [] if temporal_ok else ["RIP_TEMPORAL_NEGATIVE_CASE_MISSING"]),
        "citation_evidence_validation": phase("passed" if citation_ok else "failed_closed", [] if citation_ok else ["RIP_CITATION_EVIDENCE_VALIDATION_FAILED"]),
        "query_safety": phase("passed" if query_ok else "failed_closed", [] if query_ok else ["RIP_QUERY_SAFETY_FAILED"]),
        "overclaim_safety": phase("passed" if overclaim_ok else "failed_closed", [] if overclaim_ok else ["RIP_OVERCLAIM_DETECTED"]),
    }


def build_summary(
    *,
    report_output: Path = DEFAULT_REPORT,
    allow_blocked_runtime: bool = False,
    embedding_report: Mapping[str, Any] | None = None,
    falkordb_report: Mapping[str, Any] | None = None,
    integration_runner: Callable[[Path, Path], tuple[int, dict[str, Any]]] | None = None,
) -> tuple[int, dict[str, Any]]:
    summary = base_summary(report_output)

    if embedding_report is None:
        runtime_module = _load_module(RUNTIME_CHECK_PATH, "local_retrieval_runtime_boundary")
        embedding_report = cast("Mapping[str, Any]", runtime_module.build_runtime_report(run_inference=True))
        runtime_module.validate_payload(embedding_report)
    summary["phases"]["embedding_runtime"] = _safe_embedding_phase(embedding_report)

    if integration_runner is None:
        integration_module = _load_module(INTEGRATION_PROOF_PATH, "ontology_graphrag_integration_proof_for_runtime")
        integration_runner = lambda fixtures, output: integration_module.run_proof(fixtures, output, write_report=False)
    _, integration_summary = integration_runner(FIXTURE_PATH, report_output)
    summary["phases"].update(_fixture_phases(integration_summary))

    summary["phases"]["falkordb_runtime"] = _safe_falkordb_phase(falkordb_report, explicit_blocked_mode=allow_blocked_runtime)
    summary["graph_route"] = _s08_graph_route(falkordb_report, summary["phases"]["falkordb_runtime"])
    summary["embedding_candidate_ranking"] = _s08_embedding_candidate_ranking(embedding_report, summary["phases"]["embedding_runtime"])
    summary["deterministic_evidence_id_diagnostics"] = _s08_deterministic_evidence_id_diagnostics(integration_summary)
    summary["stale_evidence_diagnostics"] = _s08_stale_evidence_diagnostics(integration_summary)

    summary["phases"]["r035_lifecycle_disposition"] = phase(
        "passed",
        [],
        disposition="remains_active",
        evidence_scope="bounded_runtime_integration_or_blocked_rescope_only",
    )

    s08_statuses = [
        summary["deterministic_evidence_id_diagnostics"]["status"],
        summary["stale_evidence_diagnostics"]["status"],
        summary["embedding_candidate_ranking"]["status"],
    ]
    statuses = [summary["phases"][name]["status"] for name in PHASES]
    if any(status == "failed_closed" or str(status).startswith("failed_closed") for status in s08_statuses):
        statuses.append("failed_closed")
    if any(status == "failed_closed" for status in statuses):
        exit_code = 1
        summary["runtime_disposition"] = "failed_closed"
        summary["gate_disposition"] = "gate_remains_open_failed_closed"
    elif any(status == "blocked" for status in statuses):
        exit_code = 0 if allow_blocked_runtime else 1
        summary["runtime_disposition"] = "blocked_runtime_rescope"
        summary["gate_disposition"] = "gate_remains_open_blocked_runtime"
    else:
        exit_code = 0
        summary["runtime_disposition"] = "bounded_runtime_proof_passed"
        summary["gate_disposition"] = "gate_remains_open_bounded_runtime_evidence_only"
    summary["r035_lifecycle_disposition"] = "remains_active_bounded_runtime_evidence_only"
    assert_safe_payload(summary)
    return exit_code, summary


def _falkordb_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(FALKORDB_PROOF_PATH),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--readiness-timeout",
        str(args.readiness_timeout),
    ]


def _load_falkordb_artifact() -> Mapping[str, Any]:
    artifact = ROOT / ".gsd/runtime-smoke/legalgraph-shaped-falkordb/LEGALGRAPH-SHAPED-FALKORDB-PROOF.json"
    if not artifact.is_file():
        return {"status": "failed-runtime", "diagnostic_codes": ["RIP_FALKORDB_ARTIFACT_MISSING"]}
    data = json.loads(artifact.read_text(encoding="utf-8"))
    return data if isinstance(data, Mapping) else {"status": "failed-runtime", "diagnostic_codes": ["RIP_FALKORDB_ARTIFACT_MALFORMED"]}


def _run_falkordb_proof(args: argparse.Namespace) -> Mapping[str, Any]:
    completed = subprocess.run(_falkordb_command(args), cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed local script path and args
    if completed.returncode != 0:
        return {"status": "blocked-environment", "diagnostic_codes": ["RIP_FALKORDB_PROOF_COMMAND_BLOCKED"]}
    return _load_falkordb_artifact()


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _local_image_present(image: str) -> bool:
    if not _docker_available():
        return False
    completed = subprocess.run(["docker", "image", "inspect", image], cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed docker executable and args
    return completed.returncode == 0


def _start_falkordb_container(args: argparse.Namespace) -> tuple[str | None, dict[str, Any]]:
    mode = args.container
    image = args.container_image
    diagnostic = {"mode": mode, "status": "not_started", "cleanup_status": "not_needed", "image_reference": image}
    if mode == "never":
        diagnostic["status"] = "skipped_by_flag"
        return None, diagnostic
    if not _local_image_present(image):
        diagnostic["status"] = "blocked_image_absent"
        diagnostic["diagnostic_codes"] = ["RIP_FALKORDB_CONTAINER_IMAGE_ABSENT"]
        return None, diagnostic
    command = [
        "docker",
        "run",
        "--rm",
        "-d",
        "-p",
        f"127.0.0.1:{args.port}:6379",
        image,
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed docker executable and args
    if completed.returncode != 0:
        diagnostic["status"] = "blocked_start_failed"
        diagnostic["diagnostic_codes"] = ["RIP_FALKORDB_CONTAINER_START_BLOCKED"]
        return None, diagnostic
    container_id = completed.stdout.strip()[:128]
    diagnostic["status"] = "started"
    diagnostic["container_id_hash"] = f"len:{len(container_id)}"
    diagnostic["cleanup_status"] = "pending"
    time.sleep(1)
    return container_id, diagnostic


def _cleanup_container(container_id: str | None, diagnostic: dict[str, Any]) -> None:
    if not container_id:
        return
    completed = subprocess.run(["docker", "rm", "-f", container_id], cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed docker executable and args
    diagnostic["cleanup_status"] = "deleted" if completed.returncode == 0 else "cleanup_failed"
    if completed.returncode != 0:
        diagnostic["diagnostic_codes"] = sorted(set(diagnostic.get("diagnostic_codes", []) + ["RIP_FALKORDB_CONTAINER_CLEANUP_FAILED"]))


def run_falkordb_subprocess(args: argparse.Namespace) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    container_diag = {"mode": args.container, "status": "not_run", "cleanup_status": "not_needed"}
    if args.skip_falkordb_runtime:
        container_diag["status"] = "skipped_falkordb_runtime"
        return None, container_diag

    first_report = _run_falkordb_proof(args)
    if first_report.get("status") in {"confirmed-runtime", "confirmed_runtime"}:
        container_diag["status"] = "not_needed_existing_runtime"
        return first_report, container_diag
    if args.container == "never":
        container_diag["status"] = "skipped_by_flag"
        return first_report, container_diag

    container_id: str | None = None
    try:
        container_id, container_diag = _start_falkordb_container(args)
        if container_id is None:
            return first_report, container_diag
        second_report = _run_falkordb_proof(args)
        return second_report, container_diag
    finally:
        _cleanup_container(container_id, container_diag)


def write_markdown_report(path: Path, summary: Mapping[str, Any]) -> None:
    lines = [
        "# R035 Runtime Integration Remediation",
        "",
        "This is a bounded M020/S07-S08 runtime remediation artifact. R035 remains Active.",
        "It records bounded runtime remediation evidence or blocked prerequisite diagnostics; these do not close the gate and do not move R035 out of Active.",
        "",
        "## Disposition",
        "",
        f"- Runtime disposition: `{summary['runtime_disposition']}`",
        f"- Gate disposition: `{summary['gate_disposition']}`",
        f"- R035 lifecycle: `{summary['r035_lifecycle_disposition']}`",
        f"- Remediation scope: `{summary.get('remediation_scope', 'M020 S07/S08 runtime proof persistence for R035 only')}`",
        f"- Cleanup status: `{summary.get('cleanup_status', 'not_needed')}`",
        "",
        "## Phase statuses",
        "",
    ]
    phases = summary.get("phases", {})
    if isinstance(phases, Mapping):
        for name in PHASES:
            phase_payload = phases.get(name, {})
            status = phase_payload.get("status", "<missing>") if isinstance(phase_payload, Mapping) else "<malformed>"
            codes = phase_payload.get("diagnostic_codes", []) if isinstance(phase_payload, Mapping) else []
            lines.append(f"- `{name}`: `{status}`; diagnostics: `{','.join(codes) if codes else 'none'}`")
    graph_route = summary.get('graph_route', {})
    embedding_ranking = summary.get('embedding_candidate_ranking', {})
    evidence_ids = summary.get('deterministic_evidence_id_diagnostics', {})
    stale_evidence = summary.get('stale_evidence_diagnostics', {})
    lines.extend([
        "",
        "## Container/runtime",
        "",
        f"- Container runtime: `{json.dumps(summary.get('container_runtime', {}), ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Graph route",
        "",
        f"- Route summary: `{json.dumps(graph_route, ensure_ascii=False, sort_keys=True)}`",
        "- Boundary: this is a local synthetic route or blocked-runtime rescope only; real artifact graph querying and positive FalkorDB validation are not claimed.",
        "",
        "## Local/open-weight embedding ranking summary",
        "",
        f"- Ranking summary: `{json.dumps(embedding_ranking, ensure_ascii=False, sort_keys=True)}`",
        "- Boundary: candidate IDs and ranks are safe fixture-derived diagnostics only; vectors, raw legal text, provider payloads, and managed API details are excluded.",
        "",
        "## Deterministic evidence-ID validation",
        "",
        f"- Evidence-ID diagnostics: `{json.dumps(evidence_ids, ensure_ascii=False, sort_keys=True)}`",
        "- Boundary: this checks citation/evidence identifier preservation and missing-ID negative coverage for the M020 proof fixture only.",
        "",
        "## Stale-evidence diagnostics",
        "",
        f"- Stale-evidence diagnostics: `{json.dumps(stale_evidence, ensure_ascii=False, sort_keys=True)}`",
        "- Boundary: this records inactive or wrong-edition exclusion diagnostics without persisting raw legal text.",
        "",
        "## S01-to-S02 handoff clarification",
        "",
        "S01 and S02 remain handoff/source-preparation evidence only. S08 persists the bounded runtime proof or blocked-runtime rescope for R035; it does not reinterpret S01/S02 as legal-answer, parser-completeness, product-retrieval, formal-ontology, graph-vector/HNSW, FalkorDB production, or pilot-readiness validation.",
        "",
        "## Non-claims",
        "",
    ])
    for claim in summary.get("non_claims", []):
        lines.append(f"- {claim}")
    markdown_payload = "\n".join(lines) + "\n"
    for fragment in FORBIDDEN_OUTPUT_FRAGMENTS:
        if fragment.lower() in markdown_payload.lower():
            raise RuntimeIntegrationProofError("unsafe markdown fragment detected")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_payload, encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    parser.add_argument("--allow-blocked", "--allow-blocked-runtime", dest="allow_blocked_runtime", action="store_true", help="Emit exit 0 for a safe blocked-runtime rescope when local prerequisites are unavailable.")
    parser.add_argument("--skip-falkordb-runtime", action="store_true", help="Do not launch FalkorDB proof; requires --allow-blocked for exit 0.")
    parser.add_argument("--host", "--falkordb-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--falkordb-port", dest="port", type=int, default=6380)
    parser.add_argument("--readiness-timeout", "--falkordb-readiness-timeout", dest="readiness_timeout", type=int, default=5)
    parser.add_argument("--container", choices=("auto", "always", "never"), default="auto", help="Use an already-present local FalkorDB container image when needed; never pulls images.")
    parser.add_argument("--container-image", default="falkordb/falkordb:edge")
    parser.add_argument("--use-container", action="store_const", const="always", dest="container", help="Require an already-present local container image if no runtime is listening.")
    parser.add_argument("--no-container", action="store_const", const="never", dest="container", help="Never start an ephemeral container.")
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        falkordb_report, container_diag = run_falkordb_subprocess(args)
        exit_code, summary = build_summary(
            report_output=args.report_output,
            allow_blocked_runtime=args.allow_blocked_runtime,
            falkordb_report=falkordb_report,
        )
        summary["container_runtime"] = container_diag
        summary["cleanup_status"] = container_diag.get("cleanup_status", "not_needed")
        assert_safe_payload(summary)
    except Exception:
        summary = base_summary(args.report_output)
        summary["phases"]["r035_lifecycle_disposition"] = phase("passed", [], disposition="remains_active")
        summary["runtime_disposition"] = "failed_closed"
        summary["gate_disposition"] = "gate_remains_open_failed_closed"
        summary["phases"]["fixture_materialization"] = phase("failed_closed", ["RIP_INTERNAL_ERROR_REDACTED"])
        exit_code = 1
        assert_safe_payload(summary)
    if not args.no_write:
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown_report(args.markdown_output, summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
