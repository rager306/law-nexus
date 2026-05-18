#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json"
DEFAULT_REPORT = ROOT / "prd/research/ontology_architecture_requirements/ontology_graphrag_integration_proof.json"
S02_VERIFIER_PATH = ROOT / "scripts/verify-ontology-graphrag-proof.py"
SUMMARY_SCHEMA_VERSION = "ontology-graphrag-integration-proof/v1"
PROOF_ID = "OG-M020-S03-CITATION-BOUND-INTEGRATION-PROOF"
GATE_ID = "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION"

_SAFE_FIELD_LIMIT = 160
_REDACTED_FIELD_PATH = "<redacted_forbidden_field_path>"
_FORBIDDEN_FIELD_NAMES = frozenset(
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
        "generated_answer_prose",
        "legal_advice",
        "llm_reasoning",
    }
)
_GENERATED_QUERY_WRITE_TOKENS = frozenset({"CREATE", "MERGE", "DELETE", "DETACH", "SET", "REMOVE", "LOAD CSV", "DROP", "CALL DBMS"})
_FORBIDDEN_OVERCLAIM_PHRASES = frozenset(
    {
        "r035 validated",
        "validates r035",
        "r035 is validated",
        "gate-ontology-graphrag-integration satisfied",
        "satisfies gate-ontology-graphrag-integration",
        "product retrieval quality proven",
        "proves product retrieval quality",
        "legal correctness proven",
        "parser completeness proven",
        "falkordb production behavior proven",
        "graph-vector behavior proven",
        "hnsw behavior proven",
        "pilot readiness proven",
        "llm output is legal authority",
    }
)


class IntegrationProofError(Exception):
    pass


def _load_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to import {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _bounded_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)[:_SAFE_FIELD_LIMIT]


def _safe(value: Any) -> str:
    if isinstance(value, str) and value:
        return value[:_SAFE_FIELD_LIMIT]
    return "<missing>"


def _redact_forbidden_field_path(value: str) -> str:
    path_parts = [part.strip("[]0123456789'").lower() for part in value.replace("[", ".").replace("]", "").split(".")]
    if any(part in _FORBIDDEN_FIELD_NAMES for part in path_parts):
        return _REDACTED_FIELD_PATH
    return value[:_SAFE_FIELD_LIMIT]


def _safe_summary_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, nested in value.items():
            if str(key).lower() == "field_path" and isinstance(nested, str):
                safe[str(key)] = _redact_forbidden_field_path(nested)
            else:
                safe[str(key)] = _safe_summary_payload(nested)
        return safe
    if isinstance(value, list):
        return [_safe_summary_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_forbidden_field_path(value)
    return value


def _load_json(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as json_file:
        data = json.load(json_file)
    if not isinstance(data, Mapping):
        raise IntegrationProofError("fixture root must be a JSON object")
    return data


def _validator_codes(result: Any) -> list[str]:
    return [diagnostic.code for diagnostic in result.diagnostics]


def _case_trace(case: Mapping[str, Any], *, s02: ModuleType, validator: ModuleType, validator_fixture: Any) -> dict[str, Any]:
    case_id = _safe(case.get("case_id"))
    output = case.get("output")
    validator_result = validator.validate_case(case, validator_fixture) if output is not None else None
    local_diagnostics = s02._case_local_diagnostics(case, validator_result=validator_result)
    diagnostic_codes = [diagnostic["code"] for diagnostic in local_diagnostics]
    if validator_result is not None:
        diagnostic_codes.extend(_validator_codes(validator_result))
    actual_result = s02._final_result(case, validator_result, local_diagnostics)

    ontology = case.get("ontology_filter") if isinstance(case.get("ontology_filter"), Mapping) else {}
    temporal = case.get("temporal_filter") if isinstance(case.get("temporal_filter"), Mapping) else {}
    candidates = case.get("candidate_set") if isinstance(case.get("candidate_set"), list) else []
    citations = output.get("citations") if isinstance(output, Mapping) and isinstance(output.get("citations"), list) else []

    return {
        "case_id": case_id,
        "case_class": _safe(case.get("case_class")),
        "expected_result": _safe(case.get("expected_result")),
        "actual_result": actual_result,
        "diagnostic_codes": diagnostic_codes,
        "ontology_filter": {
            "filter_id": _safe(ontology.get("filter_id")),
            "filter_kind": _safe(ontology.get("filter_kind")),
            "requested_value": _safe(ontology.get("requested_value")),
            "result": _safe(ontology.get("expected_filter_result")),
        },
        "temporal_filter": {
            "as_of_date": _safe(temporal.get("as_of_date")),
            "mode": _safe(temporal.get("mode")),
            "result": _safe(temporal.get("expected_temporal_result")),
        },
        "candidate_count": len(candidates),
        "citation_count": len(citations),
        "citation_validation_result": validator_result.result if validator_result is not None else "not_applicable",
    }


def _generated_query_diagnostics(data: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    candidates = data.get("generated_query_candidates")
    if not candidates:
        return (
            {
                "generated_query_execution_avoided": True,
                "generated_query_candidates_present": False,
                "execution_like_step_performed": False,
                "future_generated_query_requirement": "Validate through prd/06_m002_cypher_safety_contract.md before any execution-like step.",
            },
            [],
        )
    diagnostics: list[dict[str, str]] = []
    if not isinstance(candidates, list):
        diagnostics.append({"case_id": "<generated_query_candidates>", "code": "E_CANDIDATE_FORMAT", "rule": "generated_query_candidates_list"})
    else:
        for index, candidate in enumerate(candidates):
            case_id = _safe(candidate.get("case_id") if isinstance(candidate, Mapping) else f"<index:{index}>")
            query = candidate.get("query") if isinstance(candidate, Mapping) else None
            requires_as_of = bool(candidate.get("requires_as_of", True)) if isinstance(candidate, Mapping) else True
            query_upper = query.upper() if isinstance(query, str) else ""
            if not isinstance(query, str) or not query.strip() or "```" in query or ";" in query.strip().rstrip(";"):
                diagnostics.append({"case_id": case_id, "code": "E_CANDIDATE_FORMAT", "rule": "single_statement_query_only"})
                continue
            if any(token in query_upper for token in _GENERATED_QUERY_WRITE_TOKENS):
                diagnostics.append({"case_id": case_id, "code": "E_WRITE_OPERATION", "rule": "read_only_generated_query"})
            if "LIMIT" not in query_upper:
                diagnostics.append({"case_id": case_id, "code": "E_LIMIT_REQUIRED", "rule": "bounded_query_results"})
            if not all(token in query for token in ("EvidenceSpan", "SourceBlock")):
                diagnostics.append({"case_id": case_id, "code": "E_EVIDENCE_REQUIRED", "rule": "evidence_span_source_block_path"})
            if requires_as_of and not all(token in query for token in ("valid_from", "valid_to", "$as_of")):
                diagnostics.append({"case_id": case_id, "code": "E_TEMPORAL_REQUIRED", "rule": "as_of_temporal_constraint"})
    status = "passed" if not diagnostics else "failed_closed"
    return (
        {
            "generated_query_execution_avoided": True,
            "generated_query_candidates_present": True,
            "execution_like_step_performed": False,
            "status": status,
            "rejection_codes": sorted({diagnostic["code"] for diagnostic in diagnostics}),
            "future_generated_query_requirement": "Validate through prd/06_m002_cypher_safety_contract.md before any execution-like step.",
        },
        [diagnostic["code"] for diagnostic in diagnostics],
    )


def _overclaim_safety(data: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    claims = data.get("proof_report_claims", [])
    if isinstance(claims, str):
        claims = [claims]
    if not isinstance(claims, list):
        return {"status": "failed_closed", "diagnostic_codes": ["overclaim_wording_detected"]}, False
    hits: list[str] = []
    for claim in claims:
        if not isinstance(claim, str):
            hits.append("non_string_claim")
            continue
        normalized = " ".join(claim.lower().split())
        if any(phrase in normalized for phrase in _FORBIDDEN_OVERCLAIM_PHRASES):
            hits.append("forbidden_positive_claim")
    if hits:
        return {"status": "failed_closed", "diagnostic_codes": ["overclaim_wording_detected"], "claim_count": len(claims)}, False
    return {"status": "passed", "claim_count": len(claims)}, True


def _build_summary(fixtures: Path, report_output: Path) -> tuple[int, dict[str, Any]]:
    s02 = _load_module(S02_VERIFIER_PATH, "ontology_graphrag_s02_verifier")
    validator = s02._load_validator()
    data = _load_json(fixtures)
    s02_exit_code, s02_summary = s02.run_proof(fixtures)

    build_code, validator_fixture, build_error = s02._build_validator_fixture(validator, data, fixtures)
    if build_code != 0:
        assert build_error is not None
        return build_code, build_error

    cases = data.get("cases")
    if not isinstance(cases, list):
        raise IntegrationProofError("cases must be a list")

    traces = [_case_trace(case, s02=s02, validator=validator, validator_fixture=validator_fixture) for case in cases if isinstance(case, Mapping)]
    result_counts: Counter[str] = Counter(trace["actual_result"] for trace in traces)
    diagnostic_inventory: Counter[str] = Counter(code for trace in traces for code in trace["diagnostic_codes"])

    ontology_matched = sum(1 for trace in traces if "ontology_filter_matched" in trace["diagnostic_codes"])
    unsupported_filter = sum(1 for trace in traces if "unsupported_ontology_filter" in trace["diagnostic_codes"])
    temporal_excluded = sum(1 for trace in traces if "temporal_filter_excluded" in trace["diagnostic_codes"] or "wrong_edition" in trace["diagnostic_codes"])
    ambiguous_candidates = sum(1 for trace in traces if "ambiguous_candidate_set" in trace["diagnostic_codes"])
    scoped_no_answer = sum(1 for trace in traces if "scoped_no_answer" in trace["diagnostic_codes"])
    forbidden_payload = sum(1 for trace in traces if "forbidden_payload_field" in trace["diagnostic_codes"])
    missing_citation = sum(1 for trace in traces if "missing_required_field" in trace["diagnostic_codes"])
    validator_failed = sum(1 for trace in traces if trace["citation_validation_result"] == "rejected")
    validator_skipped = sum(1 for trace in traces if trace["citation_validation_result"] == "not_applicable")
    validator_validated = sum(1 for trace in traces if trace["citation_validation_result"] in {"accepted", "accepted_scoped_no_answer"})

    query_safety, query_diagnostic_codes = _generated_query_diagnostics(data)
    overclaim_safety, overclaim_ok = _overclaim_safety(data)
    diagnostic_inventory.update(query_diagnostic_codes)
    if not overclaim_ok:
        diagnostic_inventory.update(overclaim_safety["diagnostic_codes"])

    passed = (
        s02_exit_code == 0
        and bool(traces)
        and s02_summary.get("mismatch_count") == 0
        and s02_summary.get("non_authoritative") is True
        and s02_summary.get("redaction_ok") is True
        and not query_diagnostic_codes
        and overclaim_ok
    )
    gate_disposition = "bounded_fixture_integration_passed_gate_remains_open" if passed else "bounded_fixture_integration_failed_gate_remains_open"

    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "proof_id": PROOF_ID,
        "source_fixture_path": _bounded_path(fixtures),
        "report_path": _bounded_path(report_output),
        "source_verifier_path": _bounded_path(S02_VERIFIER_PATH),
        "gate": GATE_ID,
        "requirement": "R035",
        "non_authoritative": True,
        "proof_level": "fixture-backed integration proof",
        "total_cases": len(traces),
        "accepted_count": result_counts["accepted"] + result_counts["accepted_scoped_no_answer"],
        "rejected_count": result_counts["rejected"],
        "blocked_count": result_counts["blocked_unsupported_filter"],
        "mismatch_count": int(s02_summary.get("mismatch_count", 1)),
        "result_states": {key: result_counts[key] for key in sorted(result_counts)},
        "filter_trace_summary": {
            "ontology_matched_count": ontology_matched,
            "unsupported_ontology_filter_count": unsupported_filter,
            "temporal_excluded_count": temporal_excluded,
            "ambiguous_candidate_count": ambiguous_candidates,
            "scoped_no_answer_count": scoped_no_answer,
            "forbidden_payload_count": forbidden_payload,
        },
        "citation_validation_status": {
            "validated_count": validator_validated,
            "failed_count": validator_failed,
            "skipped_count": validator_skipped,
            "missing_citation_or_evidence_count": missing_citation,
            "status": "passed" if passed and validator_failed >= 1 and validator_validated >= 1 else "check_diagnostics",
        },
        "query_safety": query_safety,
        "overclaim_safety": overclaim_safety,
        "diagnostic_code_inventory": sorted(diagnostic_inventory),
        "redaction_ok": s02_summary.get("redaction_ok") is True,
        "gate_disposition": gate_disposition,
        "r035_lifecycle_disposition": "remains_active_bounded_s03_evidence_only",
        "case_traces": traces,
        "non_claims": [
            "Does not validate R035 broadly.",
            "Does not satisfy the full GATE-ONTOLOGY-GRAPHRAG-INTEGRATION by itself.",
            "Does not prove product retrieval quality or legal-answer correctness.",
            "Does not prove parser completeness or FalkorDB production behavior.",
            "Does not prove graph-vector, HNSW, hybrid retrieval, or generated-Cypher generation quality.",
            "Does not make LLM output legal authority.",
        ],
    }
    if s02_summary.get("mismatches"):
        summary["mismatches"] = _safe_summary_payload(s02_summary["mismatches"])
    return (0 if passed else 1), summary


def run_proof(fixtures: Path = DEFAULT_FIXTURES, report_output: Path = DEFAULT_REPORT, *, write_report: bool = True) -> tuple[int, dict[str, Any]]:
    fixtures = fixtures if fixtures.is_absolute() else ROOT / fixtures
    report_output = report_output if report_output.is_absolute() else ROOT / report_output
    try:
        exit_code, summary = _build_summary(fixtures, report_output)
    except (IntegrationProofError, FileNotFoundError, json.JSONDecodeError, OSError, RuntimeError) as exc:
        summary = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "proof_id": PROOF_ID,
            "source_fixture_path": _bounded_path(fixtures),
            "report_path": _bounded_path(report_output),
            "gate": GATE_ID,
            "requirement": "R035",
            "non_authoritative": True,
            "mismatch_count": 1,
            "gate_disposition": "bounded_fixture_integration_failed_gate_remains_open",
            "error": {"code": "integration_proof_error", "detail": str(exc)[:_SAFE_FIELD_LIMIT]},
        }
        exit_code = 2
    if write_report:
        report_output.parent.mkdir(parents=True, exist_ok=True)
        report_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return exit_code, summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the M020 S03 citation-bound ontology GraphRAG integration proof.")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES, help="Path to S02 ontology GraphRAG proof fixture JSON.")
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT, help="Path for the durable S03 proof report JSON.")
    parser.add_argument("--no-write", action="store_true", help="Print the proof summary without writing the durable report.")
    args = parser.parse_args(argv)
    exit_code, summary = run_proof(args.fixtures, args.report_output, write_report=not args.no_write)
    json.dump(summary, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
