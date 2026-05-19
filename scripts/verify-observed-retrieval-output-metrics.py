#!/usr/bin/env python3
"""Verify M023 observed-output retrieval metrics."""

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
QUERY_REGISTRY_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_query_provenance_registry.json"
SOURCE_MANIFEST_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_source_provenance_manifest.json"
OBSERVED_OUTPUT_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_outputs.json"
REPORT_PATH = ROOT / "prd/research/ontology_architecture_requirements/observed_retrieval_output_metrics_proof.json"
PROVENANCE_VERIFIER = ROOT / "scripts/verify-observed-retrieval-provenance.py"
RUNTIME_CHECKER = ROOT / "scripts/check-local-retrieval-runtime.py"
SCHEMA_VERSION = "observed-retrieval-output-metrics-proof/v1"
OBSERVED_SCHEMA = "observed-retrieval-outputs/v1"
MODEL_ID = "deepvk/USER-bge-m3"
EXPECTED_VECTOR_DIMENSION = 1024
RETRIEVAL_MODE = "safe_id_provenance_rule_retrieval_v1"

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
FORBIDDEN_OBSERVED_FIELDS = {
    "expected_label",
    "expected_candidate_ids",
    "expected_rejected_candidate_ids",
    "expected_diagnostic_codes",
    "rank",
}
FORBIDDEN_STRING_FRAGMENTS = (
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


class ObservedMetricsError(RuntimeError):
    """Raised when observed-output metrics cannot be verified safely."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ObservedMetricsError(f"observed_output_missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ObservedMetricsError(f"malformed JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ObservedMetricsError(f"JSON root must be object: {path}")
    return payload


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise ObservedMetricsError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise ObservedMetricsError(f"unsafe payload fragment: {fragment}")


def run_json_command(command: Sequence[str], timeout_seconds: int) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(list(command), cwd=ROOT, check=False, text=True, capture_output=True, timeout=timeout_seconds)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ObservedMetricsError(f"command returned non-JSON output: {command[0]}") from exc
    if not isinstance(payload, dict):
        raise ObservedMetricsError("command returned non-object JSON")
    return completed.returncode, payload


def verify_provenance(timeout_seconds: int) -> dict[str, Any]:
    exit_code, payload = run_json_command(
        [
            sys.executable,
            str(PROVENANCE_VERIFIER),
            "--fixture",
            str(FIXTURE_PATH),
            "--query-registry",
            str(QUERY_REGISTRY_PATH),
            "--source-manifest",
            str(SOURCE_MANIFEST_PATH),
        ],
        timeout_seconds,
    )
    if exit_code != 0 or payload.get("status") != "ok":
        raise ObservedMetricsError("provenance_verifier_failed")
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


def fixture_cases(fixture: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        raise ObservedMetricsError("fixture cases must be list")
    return [case for case in cases if isinstance(case, Mapping)]


def observed_entries(observed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if observed.get("schema_version") != OBSERVED_SCHEMA:
        raise ObservedMetricsError("observed output schema mismatch")
    assert_safe_payload(observed)
    entries = observed.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ObservedMetricsError("observed_output_missing")
    if observed.get("retrieval_mode") != RETRIEVAL_MODE:
        raise ObservedMetricsError("observed_output_self_confirming: retrieval mode missing or unsupported")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ObservedMetricsError("observed entry must be object")
        if set(entry).intersection(FORBIDDEN_OBSERVED_FIELDS):
            raise ObservedMetricsError(f"observed_output_self_confirming: forbidden expected fields in {entry.get('case_id')}")
        if entry.get("retrieval_mode") != RETRIEVAL_MODE:
            raise ObservedMetricsError(f"observed output retrieval mode mismatch: {entry.get('case_id')}")
        if entry.get("derived_from_expected_fixture_fields") is not False:
            raise ObservedMetricsError(f"observed_output_self_confirming: {entry.get('case_id')}")
        if not isinstance(entry.get("observed_ranked_candidate_ids"), list):
            raise ObservedMetricsError(f"observed ranked candidates missing: {entry.get('case_id')}")
        if not isinstance(entry.get("observed_diagnostic_codes"), list):
            raise ObservedMetricsError(f"observed diagnostics missing: {entry.get('case_id')}")
        if not entry.get("query_provenance_ref") or not entry.get("candidate_source_ref"):
            raise ObservedMetricsError(f"observed provenance refs missing: {entry.get('case_id')}")
    if observed.get("entry_count") != len(entries):
        raise ObservedMetricsError("observed output count mismatch")
    return entries


def fraction(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 6)


def reciprocal_rank(expected: set[str], observed_ranked: list[str]) -> float:
    for index, candidate_id in enumerate(observed_ranked, start=1):
        if candidate_id in expected:
            return round(1 / index, 6)
    return 0.0


def citation_preserved(case: Mapping[str, Any], observed_ranked: list[str]) -> bool:
    candidates = {candidate.get("candidate_id"): candidate for candidate in case.get("candidates", []) if isinstance(candidate, Mapping)}
    for candidate_id in observed_ranked:
        if candidate_id in set(case.get("expected_candidate_ids", [])):
            candidate = candidates.get(candidate_id, {})
            return all(candidate.get(field) for field in ("evidence_span_id", "source_block_id", "citation_key", "act_edition_id"))
    return False


def compute_metrics(fixture: Mapping[str, Any], observed: Mapping[str, Any], runtime: Mapping[str, Any]) -> dict[str, float]:
    cases = fixture_cases(fixture)
    observed_by_case = {entry.get("case_id"): entry for entry in observed_entries(observed)}
    if set(observed_by_case) != {case.get("case_id") for case in cases}:
        raise ObservedMetricsError("observed output case coverage mismatch")
    positives = [case for case in cases if case["query"]["expected_result"] == "selected"]
    rr_values: list[float] = []
    top1 = 0
    top3 = 0
    citation_hits = 0
    for case in positives:
        observed_ranked = list(observed_by_case[case["case_id"]]["observed_ranked_candidate_ids"])
        if not observed_ranked:
            raise ObservedMetricsError(f"observed ranked candidates missing: {case['case_id']}")
        expected = set(case.get("expected_candidate_ids", []))
        rr = reciprocal_rank(expected, observed_ranked)
        rr_values.append(rr)
        top1 += int(rr == 1.0)
        top3 += int(rr >= round(1 / 3, 6))
        citation_hits += int(citation_preserved(case, observed_ranked))
    cases_by_class = {case["case_class"]: case for case in cases}

    def observed_for(case_class: str) -> Mapping[str, Any]:
        case = cases_by_class[case_class]
        return observed_by_case[case["case_id"]]

    metrics = {
        "mrr": round(sum(rr_values) / len(rr_values), 6),
        "recall_at_1": fraction(top1, len(positives)),
        "recall_at_3": fraction(top3, len(positives)),
        "distractor_rejection_rate": fraction(
            int(set(cases_by_class["positive_with_distractor"].get("expected_rejected_candidate_ids", [])).issubset(set(observed_for("positive_with_distractor").get("observed_rejected_candidate_ids", [])))),
            1,
        ),
        "stale_rejection_rate": fraction(
            sum(
                int("stale_temporal_candidate" in set(observed_for(case_class).get("observed_diagnostic_codes", [])))
                for case_class in ("stale_temporal_negative", "edition_mismatch_negative")
            ),
            2,
        ),
        "ambiguous_preservation_rate": fraction(int("ambiguous_candidate_set" in set(observed_for("ambiguous_candidate_set").get("observed_diagnostic_codes", []))), 1),
        "unsupported_scope_accuracy": fraction(int("unsupported_scope" in set(observed_for("unsupported_scope").get("observed_diagnostic_codes", []))), 1),
        "no_answer_accuracy": fraction(int("scoped_no_answer" in set(observed_for("scoped_no_answer").get("observed_diagnostic_codes", []))), 1),
        "citation_preservation_rate": fraction(citation_hits, len(positives)),
        "unsafe_rejection_rate": fraction(int("unsafe_payload_rejected" in set(observed_for("unsafe_payload_boundary").get("observed_diagnostic_codes", []))), 1),
        "runtime_boundary_confirmed": 1.0 if runtime.get("confirmed") is True else 0.0,
    }
    return metrics


def build_report(observed_path: Path, runtime_json: Path | None, timeout_seconds: int) -> dict[str, Any]:
    provenance = verify_provenance(timeout_seconds)
    fixture = load_json(FIXTURE_PATH)
    observed = load_json(observed_path)
    runtime = runtime_boundary(timeout_seconds, runtime_json)
    metrics = compute_metrics(fixture, observed, runtime)
    threshold_failures = [name for name, minimum in THRESHOLDS.items() if metrics.get(name, 0.0) < minimum]
    status = "passed" if not threshold_failures else "blocked"
    diagnostics = set(provenance.get("diagnostic_codes", [])) | set(runtime.get("diagnostic_codes", []))
    diagnostics.add("metric_comparison_verified" if not threshold_failures else "metric_mismatch")
    report = {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M023-9rfkrs",
        "slice_id": "S03",
        "status": status,
        "retrieval_mode": RETRIEVAL_MODE,
        "observed_output_artifact": "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_outputs.json",
        "provenance_summary": provenance,
        "runtime_boundary": runtime,
        "thresholds": THRESHOLDS,
        "metrics": metrics,
        "threshold_failures": threshold_failures,
        "diagnostic_codes": sorted(diagnostics),
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
        "non_claims": [
            "Does not validate R035.",
            "Does not validate R037.",
            "Does not prove product retrieval quality.",
            "Does not prove legal-answer correctness.",
            "Does not prove graph-vector or HNSW behavior.",
            "Does not prove model semantic retrieval quality; observed outputs are safe-ID rule retrieval outputs.",
        ],
    }
    assert_safe_payload(report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-output", type=Path, default=OBSERVED_OUTPUT_PATH)
    parser.add_argument("--runtime-json", type=Path)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args.observed_output, args.runtime_json, args.timeout_seconds)
        if not args.no_write:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except ObservedMetricsError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(json.dumps({"status": report["status"], "retrieval_mode": report["retrieval_mode"], "metrics": report["metrics"], "diagnostic_codes": report["diagnostic_codes"], "non_authoritative": True}, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
