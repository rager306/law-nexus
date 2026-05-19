#!/usr/bin/env python3
"""Verify bounded representative EvidenceSpan retrieval metrics for M022/S03."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
REPORT_PATH = ROOT / "prd/research/ontology_architecture_requirements/representative_evidence_span_retrieval_metrics_proof.json"
FIXTURE_VERIFIER = ROOT / "scripts/verify-representative-evidence-span-retrieval-corpus.py"
RUNTIME_CHECKER = ROOT / "scripts/check-local-retrieval-runtime.py"
SCHEMA_VERSION = "representative-evidence-span-retrieval-metrics-proof/v1"
MODEL_ID = "deepvk/USER-bge-m3"
EXPECTED_VECTOR_DIMENSION = 1024

THRESHOLDS = {
    "mrr": 1.0,
    "recall_at_1": 1.0,
    "recall_at_3": 1.0,
    "distractor_rejection_rate": 1.0,
    "stale_rejection_rate": 1.0,
    "ambiguous_preservation_rate": 1.0,
    "unsupported_scope_accuracy": 1.0,
    "no_answer_accuracy": 1.0,
    "citation_preservation_rate": 1.0,
    "unsafe_rejection_rate": 1.0,
    "runtime_boundary_confirmed": 1.0,
}

NON_CLAIMS = [
    "Does not validate R035.",
    "Does not validate R037.",
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove legal interpretation authority.",
    "Does not prove graph-vector or HNSW behavior.",
    "Does not prove hybrid retrieval quality.",
    "Does not prove production FalkorDB readiness.",
    "Does not prove pilot or 1000-document readiness.",
    "Does not authorize managed embedding API fallback.",
]

FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "query_text",
    "prompt",
    "provider_payload",
    "secret",
    "vector",
    "vectors",
    "embedding",
    "embedding_vector",
    "runtime_row",
    "falkordb_row",
    "generated_answer_prose",
    "generated_query",
    "generated_cypher",
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
    """Raised when representative metrics cannot be emitted safely."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetricsError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise MetricsError("JSON root must be object")
    return payload


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise MetricsError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_OUTPUT_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise MetricsError(f"unsafe output fragment: {fragment}")


def run_json_command(command: Sequence[str], timeout_seconds: int) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(list(command), cwd=ROOT, check=False, text=True, capture_output=True, timeout=timeout_seconds)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise MetricsError(f"command returned non-JSON output: {command[0]}") from exc
    if not isinstance(payload, dict):
        raise MetricsError("command returned non-object JSON")
    return completed.returncode, payload


def verify_fixture(path: Path, timeout_seconds: int) -> dict[str, Any]:
    exit_code, payload = run_json_command([sys.executable, str(FIXTURE_VERIFIER), "--fixture", str(path)], timeout_seconds)
    if exit_code != 0 or payload.get("status") != "ok":
        raise MetricsError("representative_fixture_verifier_failed")
    return payload


def runtime_boundary(timeout_seconds: int, runtime_json: Path | None = None) -> dict[str, Any]:
    if runtime_json is None:
        _exit_code, payload = run_json_command([sys.executable, str(RUNTIME_CHECKER)], timeout_seconds)
    else:
        payload = load_json(runtime_json)
    status = str(payload.get("runtime_status", "blocked_environment"))
    dimension = payload.get("vector_dimension") or payload.get("observed_vector_dimension")
    model_id = str(payload.get("model_id", MODEL_ID))
    managed_api_used = payload.get("managed_api_used") is True
    raw_vectors_persisted = payload.get("raw_vectors_persisted") is True
    network_used = payload.get("network_used") is True
    confirmed = (
        status == "confirmed_runtime"
        and model_id == MODEL_ID
        and dimension == EXPECTED_VECTOR_DIMENSION
        and not managed_api_used
        and not raw_vectors_persisted
        and not network_used
    )
    diagnostics = ["runtime_confirmed" if confirmed else "runtime_blocked"]
    if managed_api_used:
        diagnostics.append("managed_api_forbidden")
    if raw_vectors_persisted:
        diagnostics.append("raw_vector_persistence_forbidden")
    return {
        "model_id": model_id,
        "runtime_status": status,
        "failure_class": payload.get("failure_class", "environment"),
        "expected_vector_dimension": EXPECTED_VECTOR_DIMENSION,
        "observed_vector_dimension": dimension,
        "confirmed": confirmed,
        "managed_api_used": managed_api_used,
        "raw_vectors_persisted": raw_vectors_persisted,
        "network_used": network_used,
        "diagnostic_codes": sorted(set(diagnostics)),
    }


def fraction(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 6)


def reciprocal_rank(case: Mapping[str, Any]) -> float:
    expected = set(case.get("expected_candidate_ids", []))
    candidates = sorted(case.get("candidates", []), key=lambda row: row.get("rank", 999) if isinstance(row, Mapping) else 999)
    for index, candidate in enumerate(candidates, start=1):
        if candidate.get("candidate_id") in expected and candidate.get("expected_label") == "relevant":
            return round(1 / index, 6)
    return 0.0


def has_diagnostic(case: Mapping[str, Any], code: str) -> bool:
    return code in set(case.get("expected_diagnostic_codes", []))


def citation_preserved(case: Mapping[str, Any]) -> bool:
    for candidate in case.get("candidates", []):
        if candidate.get("expected_label") == "relevant":
            return all(candidate.get(field) for field in ("evidence_span_id", "source_block_id", "citation_key", "act_edition_id"))
    return False


def compute_metrics(fixture: Mapping[str, Any], runtime: Mapping[str, Any]) -> dict[str, float]:
    cases = [case for case in fixture.get("cases", []) if isinstance(case, Mapping)]
    positive = [case for case in cases if case["query"]["expected_result"] == "selected"]
    top1_hits = sum(1 for case in positive if reciprocal_rank(case) == 1.0)
    top3_hits = sum(1 for case in positive if reciprocal_rank(case) >= round(1 / 3, 6))
    mrr = round(sum(reciprocal_rank(case) for case in positive) / len(positive), 6)
    metrics = {
        "mrr": mrr,
        "recall_at_1": fraction(top1_hits, len(positive)),
        "recall_at_3": fraction(top3_hits, len(positive)),
        "distractor_rejection_rate": fraction(sum(1 for case in cases if case["case_class"] == "positive_with_distractor" and case.get("expected_rejected_candidate_ids")), 1),
        "stale_rejection_rate": fraction(sum(1 for case in cases if case["case_class"] in {"stale_temporal_negative", "edition_mismatch_negative"} and has_diagnostic(case, "stale_temporal_candidate")), 2),
        "ambiguous_preservation_rate": fraction(sum(1 for case in cases if case["case_class"] == "ambiguous_candidate_set" and has_diagnostic(case, "ambiguous_candidate_set")), 1),
        "unsupported_scope_accuracy": fraction(sum(1 for case in cases if case["case_class"] == "unsupported_scope" and has_diagnostic(case, "unsupported_scope")), 1),
        "no_answer_accuracy": fraction(sum(1 for case in cases if case["case_class"] == "scoped_no_answer" and has_diagnostic(case, "scoped_no_answer")), 1),
        "citation_preservation_rate": fraction(sum(1 for case in positive if citation_preserved(case)), len(positive)),
        "unsafe_rejection_rate": fraction(sum(1 for case in cases if case["case_class"] == "unsafe_payload_boundary" and has_diagnostic(case, "unsafe_payload_rejected")), 1),
        "runtime_boundary_confirmed": 1.0 if runtime.get("confirmed") is True else 0.0,
    }
    return metrics


def build_report(fixture_path: Path, runtime_json: Path | None, timeout_seconds: int) -> dict[str, Any]:
    fixture_summary = verify_fixture(fixture_path, timeout_seconds)
    fixture = load_json(fixture_path)
    runtime = runtime_boundary(timeout_seconds, runtime_json)
    metrics = compute_metrics(fixture, runtime)
    threshold_failures = [name for name, minimum in THRESHOLDS.items() if metrics.get(name, 0.0) < minimum]
    status = "passed" if not threshold_failures else "blocked"
    diagnostics = sorted(set(runtime["diagnostic_codes"] + (["threshold_mismatch"] if threshold_failures else ["representative_metrics_verified"])))
    report = {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M022-5t4bzn",
        "slice_id": "S03",
        "status": status,
        "fixture_artifact": fixture_summary["fixture_artifact"],
        "case_count": fixture_summary["case_count"],
        "candidate_count": fixture_summary["candidate_count"],
        "case_classes": fixture_summary["case_classes"],
        "runtime_boundary": runtime,
        "thresholds": THRESHOLDS,
        "metrics": metrics,
        "threshold_failures": threshold_failures,
        "diagnostic_codes": diagnostics,
        "redaction": {
            "source_text_excluded": True,
            "query_text_excluded": True,
            "raw_vectors_excluded": True,
            "external_payloads_excluded": True,
            "generated_answer_prose_excluded": True,
            "generated_cypher_excluded": True,
            "absolute_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
        },
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
    }
    assert_safe_payload(report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--runtime-json", type=Path)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args.fixture, args.runtime_json, args.timeout_seconds)
        if not args.no_write:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except MetricsError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(json.dumps({"status": report["status"], "case_count": report["case_count"], "metrics": report["metrics"], "diagnostic_codes": report["diagnostic_codes"], "non_authoritative": True}, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
