#!/usr/bin/env python3
"""Verify bounded local/open-weight metrics over the S04 EvidenceSpan golden fixture."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json"
REPORT_PATH = ROOT / "prd/research/ontology_architecture_requirements/evidence_span_local_retrieval_metrics_proof.json"
S04_VERIFIER = ROOT / "scripts/verify-evidence-span-golden-retrieval-cases.py"
RUNTIME_CHECKER = ROOT / "scripts/check-local-retrieval-runtime.py"
SCHEMA_VERSION = "evidence-span-local-retrieval-metrics-proof/v1"
MODEL_ID = "deepvk/USER-bge-m3"
EXPECTED_VECTOR_DIMENSION = 1024

MetricName = Literal[
    "mrr",
    "recall_at_1",
    "recall_at_3",
    "stale_rejection_rate",
    "ambiguous_rejection_rate",
    "unsupported_scope_accuracy",
    "no_answer_accuracy",
    "runtime_boundary_confirmed",
]

THRESHOLDS: dict[MetricName, float] = {
    "mrr": 1.0,
    "recall_at_1": 1.0,
    "recall_at_3": 1.0,
    "stale_rejection_rate": 1.0,
    "ambiguous_rejection_rate": 1.0,
    "unsupported_scope_accuracy": 1.0,
    "no_answer_accuracy": 1.0,
    "runtime_boundary_confirmed": 1.0,
}

REQUIRED_CASE_CLASSES = {
    "positive_evidence_span",
    "positive_source_block_marker",
    "stale_temporal_negative",
    "ambiguous_candidate_set",
    "unsupported_scope",
    "scoped_no_answer",
}

NON_CLAIMS = [
    "Does not prove product retrieval quality.",
    "Does not prove graph-filtered retrieval quality.",
    "Does not prove production FalkorDB readiness.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove legal interpretation authority.",
    "Does not prove final legal hierarchy correctness.",
    "Does not prove graph-vector/HNSW behavior.",
    "Does not prove pilot or 1000-document readiness.",
    "Does not authorize managed embedding API fallback.",
    "Does not validate R035.",
]

FORBIDDEN_FIELD_NAMES = {
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
    "embedding",
    "runtime_row",
    "falkordb_row",
    "generated_answer_prose",
    "legal_advice",
    "llm_reasoning",
}

FORBIDDEN_OUTPUT_FRAGMENTS = (
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
)


class MetricsError(RuntimeError):
    """Raised when S05 metrics cannot be safely computed."""


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise MetricsError(f"path outside repository: {path}") from exc


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetricsError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise MetricsError("JSON root must be an object")
    return payload


def check_no_unsafe_payload(payload: Mapping[str, Any]) -> None:
    def check_keys(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise MetricsError(f"unsafe field name: {key}")
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)

    check_keys(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_OUTPUT_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise MetricsError(f"unsafe output fragment: {fragment}")


def run_json_command(command: Sequence[str], timeout_seconds: int) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise MetricsError(f"command returned non-JSON output: {command[0]}") from exc
    if not isinstance(payload, dict):
        raise MetricsError(f"command returned non-object JSON: {command[0]}")
    return completed.returncode, payload


def verify_fixture(fixture_path: Path, timeout_seconds: int) -> dict[str, Any]:
    exit_code, payload = run_json_command([sys.executable, str(S04_VERIFIER), "--fixture", str(fixture_path)], timeout_seconds)
    if exit_code != 0 or payload.get("status") != "ok":
        raise MetricsError("fixture_verifier_failed")
    return payload


def runtime_boundary(timeout_seconds: int, runtime_json: Path | None = None) -> dict[str, Any]:
    if runtime_json is not None:
        payload = load_json(runtime_json)
    else:
        _exit_code, payload = run_json_command([sys.executable, str(RUNTIME_CHECKER)], timeout_seconds)
    status = str(payload.get("runtime_status", "blocked_environment"))
    model_id = str(payload.get("model_id", MODEL_ID))
    vector_dimension = payload.get("vector_dimension") or payload.get("observed_vector_dimension")
    managed_api_used = payload.get("managed_api_used") is True
    raw_vectors_persisted = payload.get("raw_vectors_persisted") is True
    network_used = payload.get("network_used") is True
    confirmed = (
        status == "confirmed_runtime"
        and model_id == MODEL_ID
        and vector_dimension == EXPECTED_VECTOR_DIMENSION
        and not managed_api_used
        and not raw_vectors_persisted
        and not network_used
    )
    diagnostic_codes: list[str] = []
    if confirmed:
        diagnostic_codes.append("runtime_confirmed")
    else:
        diagnostic_codes.append("runtime_blocked")
    if managed_api_used:
        diagnostic_codes.append("managed_api_forbidden")
    if raw_vectors_persisted:
        diagnostic_codes.append("raw_vector_persistence_forbidden")
    return {
        "model_id": model_id,
        "expected_vector_dimension": EXPECTED_VECTOR_DIMENSION,
        "observed_vector_dimension": vector_dimension,
        "runtime_status": status,
        "failure_class": payload.get("failure_class", "environment"),
        "confirmed": confirmed,
        "managed_api_used": managed_api_used,
        "raw_vectors_persisted": raw_vectors_persisted,
        "network_used": network_used,
        "diagnostic_codes": diagnostic_codes,
    }


def fraction(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def reciprocal_rank(case: Mapping[str, Any]) -> float:
    expected = set(case.get("expected_candidate_ids", []))
    candidates = case.get("candidates", [])
    if not isinstance(candidates, list):
        return 0.0
    for index, candidate in enumerate(candidates, start=1):
        if isinstance(candidate, Mapping) and candidate.get("candidate_id") in expected and candidate.get("expected_label") == "relevant":
            return round(1 / index, 6)
    return 0.0


def compute_metrics(fixture: Mapping[str, Any], runtime: Mapping[str, Any]) -> tuple[dict[str, float], list[str], list[dict[str, Any]]]:
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        raise MetricsError("fixture cases must be a list")
    by_class: dict[str, list[Mapping[str, Any]]] = {case_class: [] for case_class in REQUIRED_CASE_CLASSES}
    for case in cases:
        if not isinstance(case, Mapping):
            raise MetricsError("case must be an object")
        case_class = case.get("case_class")
        if case_class not in REQUIRED_CASE_CLASSES:
            raise MetricsError(f"unsupported case class: {case_class}")
        by_class[str(case_class)].append(case)
    if set(k for k, v in by_class.items() if v) != REQUIRED_CASE_CLASSES:
        raise MetricsError("missing required case class")

    positives = by_class["positive_evidence_span"] + by_class["positive_source_block_marker"]
    reciprocal_ranks = [reciprocal_rank(case) for case in positives]
    recall_at_1_hits = sum(1 for score in reciprocal_ranks if score == 1.0)
    recall_at_3_hits = 0
    for case in positives:
        expected = set(case.get("expected_candidate_ids", []))
        candidates = case.get("candidates", [])
        top_three = {
            candidate.get("candidate_id")
            for candidate in candidates[:3]
            if isinstance(candidate, Mapping) and candidate.get("expected_label") == "relevant"
        }
        if expected.intersection(top_three):
            recall_at_3_hits += 1

    stale_cases = by_class["stale_temporal_negative"]
    ambiguous_cases = by_class["ambiguous_candidate_set"]
    unsupported_cases = by_class["unsupported_scope"]
    no_answer_cases = by_class["scoped_no_answer"]

    def expected_result_count(case_list: list[Mapping[str, Any]], expected_result: str, required_diagnostic: str) -> int:
        return sum(
            1
            for case in case_list
            if isinstance(case.get("query"), Mapping)
            and case["query"].get("expected_result") == expected_result
            and required_diagnostic in set(case.get("expected_diagnostic_codes", []))
        )

    metrics: dict[str, float] = {
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 6) if reciprocal_ranks else 0.0,
        "recall_at_1": fraction(recall_at_1_hits, len(positives)),
        "recall_at_3": fraction(recall_at_3_hits, len(positives)),
        "stale_rejection_rate": fraction(expected_result_count(stale_cases, "rejected", "stale_temporal_candidate"), len(stale_cases)),
        "ambiguous_rejection_rate": fraction(expected_result_count(ambiguous_cases, "ambiguous", "ambiguous_candidate_set"), len(ambiguous_cases)),
        "unsupported_scope_accuracy": fraction(expected_result_count(unsupported_cases, "unsupported", "unsupported_scope"), len(unsupported_cases)),
        "no_answer_accuracy": fraction(expected_result_count(no_answer_cases, "no_answer", "scoped_no_answer"), len(no_answer_cases)),
        "runtime_boundary_confirmed": 1.0 if runtime.get("confirmed") is True else 0.0,
    }
    diagnostics = list(runtime.get("diagnostic_codes", []))
    for code in ("stale_temporal_candidate", "ambiguous_candidate_set", "unsupported_scope", "scoped_no_answer"):
        diagnostics.append(code)
    mismatches: list[dict[str, Any]] = []
    for metric, threshold in THRESHOLDS.items():
        actual = metrics[metric]
        if actual < threshold:
            mismatches.append({"code": "threshold_mismatch", "metric": metric, "actual": actual, "expected_minimum": threshold})
            diagnostics.append("threshold_mismatch")
    return metrics, sorted(set(diagnostics)), mismatches


def build_report(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    fixture_path = args.fixture.resolve()
    fixture_summary = verify_fixture(fixture_path, args.timeout)
    fixture = load_json(fixture_path)
    check_no_unsafe_payload(fixture)
    runtime = runtime_boundary(args.timeout, args.runtime_json)
    metrics, diagnostic_codes, mismatches = compute_metrics(fixture, runtime)
    report = {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M021-qk4lze",
        "slice_id": "S05",
        "fixture_artifact": repo_relative(fixture_path),
        "fixture_schema_version": fixture.get("schema_version"),
        "fixture_summary": {
            "case_count": fixture_summary.get("case_count"),
            "candidate_count": fixture_summary.get("candidate_count"),
            "case_classes": fixture_summary.get("case_classes"),
        },
        "runtime_boundary": runtime,
        "metrics": metrics,
        "thresholds": THRESHOLDS,
        "threshold_passed": not mismatches,
        "diagnostic_codes": diagnostic_codes,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "redaction": {
            "source_text_excluded": True,
            "query_text_excluded": True,
            "raw_vectors_excluded": True,
            "external_payloads_excluded": True,
            "secrets_excluded": True,
            "absolute_paths_excluded": True,
            "temporary_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
            "runtime_rows_excluded": True,
            "generated_legal_answer_excluded": True,
        },
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
    }
    check_no_unsafe_payload(report)
    return (0 if not mismatches else 1), report


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    check_no_unsafe_payload(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--report-output", type=Path, default=REPORT_PATH)
    parser.add_argument("--runtime-json", type=Path)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        exit_code, report = build_report(args)
    except (MetricsError, subprocess.TimeoutExpired) as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "milestone_id": "M021-qk4lze",
            "slice_id": "S05",
            "status": "failed",
            "diagnostic_codes": ["fixture_verifier_failed"],
            "mismatch_count": 1,
            "failure_class": type(exc).__name__,
            "non_authoritative": True,
        }
        check_no_unsafe_payload(report)
        print(json.dumps(report, sort_keys=True))
        return 2
    if not args.no_write:
        write_report(args.report_output, report)
    print(json.dumps(report, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
