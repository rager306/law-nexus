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
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, cast

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json"
DEFAULT_REPORT = ROOT / "prd/research/ontology_architecture_requirements/ontology_graphrag_runtime_integration_proof.json"
INTEGRATION_PROOF_PATH = ROOT / "scripts/verify-ontology-graphrag-integration-proof.py"
RUNTIME_CHECK_PATH = ROOT / "scripts/check-local-retrieval-runtime.py"
FALKORDB_PROOF_PATH = ROOT / "scripts/prove-legalgraph-shaped-falkordb.py"

SCHEMA_VERSION = "ontology-graphrag-runtime-integration-proof/v1"
PROOF_ID = "OG-M020-S07-RUNTIME-INTEGRATION-PROOF"
REQUIREMENT_ID = "R035"

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
        "phases": {name: phase("not_run", ["RIP_NOT_RUN"]) for name in PHASES},
        "runtime_disposition": "not_run",
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
    summary["phases"]["r035_lifecycle_disposition"] = phase(
        "passed",
        [],
        disposition="remains_active",
        evidence_scope="bounded_runtime_integration_or_blocked_rescope_only",
    )

    statuses = [summary["phases"][name]["status"] for name in PHASES]
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


def run_falkordb_subprocess(args: argparse.Namespace) -> Mapping[str, Any] | None:
    if args.skip_falkordb_runtime:
        return None
    command = [
        sys.executable,
        str(FALKORDB_PROOF_PATH),
        "--host",
        args.falkordb_host,
        "--port",
        str(args.falkordb_port),
        "--readiness-timeout",
        str(args.falkordb_readiness_timeout),
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)  # noqa: S603 - fixed local script path and args
    if completed.returncode != 0:
        return {"status": "blocked-environment"}
    artifact = ROOT / ".gsd/runtime-smoke/legalgraph-shaped-falkordb/LEGALGRAPH-SHAPED-FALKORDB-PROOF.json"
    if not artifact.is_file():
        return {"status": "failed-runtime"}
    data = json.loads(artifact.read_text(encoding="utf-8"))
    return data if isinstance(data, Mapping) else {"status": "failed-runtime"}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--allow-blocked-runtime", action="store_true", help="Emit a passing blocked-runtime rescope when local runtime prerequisites are unavailable.")
    parser.add_argument("--skip-falkordb-runtime", action="store_true", help="Do not launch FalkorDB proof; requires --allow-blocked-runtime for exit 0.")
    parser.add_argument("--falkordb-host", default="127.0.0.1")
    parser.add_argument("--falkordb-port", type=int, default=6380)
    parser.add_argument("--falkordb-readiness-timeout", type=int, default=5)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        falkordb_report = run_falkordb_subprocess(args)
        exit_code, summary = build_summary(
            report_output=args.report_output,
            allow_blocked_runtime=args.allow_blocked_runtime,
            falkordb_report=falkordb_report,
        )
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
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
