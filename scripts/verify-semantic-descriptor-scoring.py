#!/usr/bin/env python3
"""Run M025 local semantic scoring over safe descriptor inputs."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR_INPUTS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/semantic_descriptor_inputs.json"
FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
REPORT = ROOT / "prd/research/ontology_architecture_requirements/semantic_descriptor_scoring_proof.json"
DESCRIPTOR_VERIFIER = ROOT / "scripts/verify-semantic-descriptor-inputs.py"
RUNTIME_CHECKER = ROOT / "scripts/check-local-retrieval-runtime.py"
MODEL_ID = "deepvk/USER-bge-m3"
EXPECTED_VECTOR_DIMENSION = 1024
SCHEMA_VERSION = "semantic-descriptor-scoring-proof/v1"
SCORING_MODE = "local_user_bge_m3_safe_descriptor_similarity_v1"
M024_BASELINE = {
    "mrr": 0.875,
    "recall_at_1": 0.75,
    "recall_at_3": 1.0,
    "positive_with_distractor_relevant_first": 0.0,
    "runtime_boundary_confirmed": 1.0,
}
THRESHOLDS = {
    "mrr": 1.0,
    "recall_at_1": 1.0,
    "recall_at_3": 1.0,
    "positive_with_distractor_relevant_first": 1.0,
    "runtime_boundary_confirmed": 1.0,
}
FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "source_excerpts",
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
    "expected_label",
    "expected_rank",
    "rank",
    "expected_candidate_ids",
    "expected_rejected_candidate_ids",
    "expected_diagnostic_codes",
}
FORBIDDEN_STRING_FRAGMENTS = (
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "expected_label",
    "expected_candidate_ids",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
)


class DescriptorScoringError(RuntimeError):
    """Raised when descriptor scoring cannot safely produce a proof."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DescriptorScoringError(f"input_missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DescriptorScoringError(f"malformed JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise DescriptorScoringError(f"JSON root must be object: {path}")
    return payload


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise DescriptorScoringError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise DescriptorScoringError(f"unsafe payload fragment: {fragment}")


def run_json_command(command: Sequence[str], timeout_seconds: int) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(list(command), cwd=ROOT, check=False, text=True, capture_output=True, timeout=timeout_seconds)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DescriptorScoringError(f"command returned non-JSON output: {command[0]}") from exc
    if not isinstance(payload, dict):
        raise DescriptorScoringError("command returned non-object JSON")
    return completed.returncode, payload


def verify_descriptor_inputs(timeout_seconds: int) -> dict[str, Any]:
    exit_code, payload = run_json_command([sys.executable, str(DESCRIPTOR_VERIFIER)], timeout_seconds)
    if exit_code != 0 or payload.get("status") != "ok":
        raise DescriptorScoringError("descriptor_input_verifier_failed")
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


def descriptor_text(tokens: Sequence[str]) -> str:
    return " ".join(tokens)


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def encode_texts(texts: Sequence[str]) -> list[list[float]]:
    sentence_transformers = __import__("sentence_transformers", fromlist=["SentenceTransformer"])
    model = sentence_transformers.SentenceTransformer(MODEL_ID, local_files_only=True)
    vectors = model.encode(list(texts), convert_to_numpy=False)
    return [[float(value) for value in vector] for vector in vectors]


def scores_from_model(inputs: Mapping[str, Any]) -> list[dict[str, Any]]:
    query_descriptors = inputs.get("query_descriptors")
    candidate_descriptors = inputs.get("candidate_descriptors")
    if not isinstance(query_descriptors, list) or not isinstance(candidate_descriptors, list):
        raise DescriptorScoringError("descriptor inputs missing")
    all_texts = [descriptor_text(item["descriptor_tokens"]) for item in query_descriptors + candidate_descriptors]
    vectors = encode_texts(all_texts)
    query_vectors = vectors[: len(query_descriptors)]
    candidate_vectors = vectors[len(query_descriptors) :]
    query_by_case = {item["case_id"]: (item, query_vectors[index]) for index, item in enumerate(query_descriptors)}
    candidate_rows: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidate_descriptors):
        case_id = candidate["case_id"]
        query, query_vector = query_by_case[case_id]
        score = cosine(query_vector, candidate_vectors[index])
        candidate_rows.append(
            {
                "case_id": case_id,
                "query_id": query["query_id"],
                "candidate_id": candidate["candidate_id"],
                "descriptor_input_ref": candidate["descriptor_input_id"],
                "scoring_mode": SCORING_MODE,
                "observed_similarity_score": round(score, 6),
                "observation_status": "scored",
                "diagnostic_codes": [],
                "non_authoritative": True,
            }
        )
    ranked: list[dict[str, Any]] = []
    for case_id in sorted({row["case_id"] for row in candidate_rows}):
        rows = [row for row in candidate_rows if row["case_id"] == case_id]
        rows.sort(key=lambda row: (-row["observed_similarity_score"], row["candidate_id"]))
        for observed_rank, row in enumerate(rows, start=1):
            ranked.append({**row, "observed_rank": observed_rank})
    return ranked


def scores_from_json(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    scores = payload.get("scores")
    if not isinstance(scores, list):
        raise DescriptorScoringError("observed scores missing")
    return [dict(row) for row in scores if isinstance(row, Mapping)]


def fixture_cases() -> list[Mapping[str, Any]]:
    fixture = load_json(FIXTURE)
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        raise DescriptorScoringError("fixture cases missing")
    return [case for case in cases if isinstance(case, Mapping)]


def reciprocal_rank(expected: set[str], ranked_ids: Sequence[str]) -> float:
    for index, candidate_id in enumerate(ranked_ids, start=1):
        if candidate_id in expected:
            return round(1 / index, 6)
    return 0.0


def fraction(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 6)


def compute_metrics(scores: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    cases = fixture_cases()
    scores_by_case: dict[str, list[Mapping[str, Any]]] = {}
    for row in scores:
        if set(row).intersection(FORBIDDEN_FIELD_NAMES):
            raise DescriptorScoringError(f"expected_answer_leakage: {row.get('case_id')}")
        if row.get("scoring_mode") != SCORING_MODE:
            raise DescriptorScoringError(f"scoring mode mismatch: {row.get('case_id')}")
        if not isinstance(row.get("observed_similarity_score"), int | float):
            raise DescriptorScoringError(f"observed score missing: {row.get('case_id')}")
        scores_by_case.setdefault(str(row.get("case_id")), []).append(row)
    positives = [case for case in cases if case["query"]["expected_result"] == "selected"]
    rr_values: list[float] = []
    top1 = 0
    top3 = 0
    distractor_first = 0
    for case in positives:
        rows = sorted(scores_by_case.get(str(case["case_id"]), []), key=lambda row: int(row.get("observed_rank", 999)))
        ranked_ids = [str(row["candidate_id"]) for row in rows]
        if not ranked_ids:
            raise DescriptorScoringError(f"observed scores missing for positive case: {case['case_id']}")
        expected = set(case.get("expected_candidate_ids", []))
        rr = reciprocal_rank(expected, ranked_ids)
        rr_values.append(rr)
        top1 += int(rr == 1.0)
        top3 += int(rr >= round(1 / 3, 6))
        if case["case_class"] == "positive_with_distractor":
            distractor_first = int(ranked_ids[0] in expected)
    return {
        "mrr": round(sum(rr_values) / len(rr_values), 6),
        "recall_at_1": fraction(top1, len(positives)),
        "recall_at_3": fraction(top3, len(positives)),
        "positive_with_distractor_relevant_first": float(distractor_first),
    }


def metric_deltas(metrics: Mapping[str, float]) -> dict[str, float]:
    return {f"delta_{name}": round(float(metrics.get(name, 0.0)) - baseline, 6) for name, baseline in M024_BASELINE.items()}


def disposition_hint(metrics: Mapping[str, float], deltas: Mapping[str, float], threshold_failures: Sequence[str], runtime_confirmed: bool) -> str:
    if not runtime_confirmed:
        return "blocked"
    if "recall_at_3" in threshold_failures and metrics.get("recall_at_3", 0.0) < M024_BASELINE["recall_at_3"]:
        return "reject"
    if deltas.get("delta_positive_with_distractor_relevant_first", 0.0) > 0 and deltas.get("delta_mrr", 0.0) >= 0 and deltas.get("delta_recall_at_1", 0.0) >= 0:
        return "accept_candidate_pending_review"
    if any(value > 0 for key, value in deltas.items() if key != "delta_runtime_boundary_confirmed"):
        return "revise_candidate_pending_review"
    return "reject_candidate_pending_review"


def build_report(
    runtime_json: Path | None,
    scores_json: Path | None,
    timeout_seconds: int,
    *,
    allow_injected_test_inputs: bool = False,
) -> dict[str, Any]:
    if (runtime_json is not None or scores_json is not None) and not allow_injected_test_inputs:
        raise DescriptorScoringError("injected runtime/scores JSON forbidden for acceptance proof")
    descriptor_summary = verify_descriptor_inputs(timeout_seconds)
    inputs = load_json(DESCRIPTOR_INPUTS)
    assert_safe_payload(inputs)
    runtime = runtime_boundary(timeout_seconds, runtime_json)
    if not runtime["confirmed"]:
        scores: list[dict[str, Any]] = []
        metrics = {"mrr": 0.0, "recall_at_1": 0.0, "recall_at_3": 0.0, "positive_with_distractor_relevant_first": 0.0}
        scoring_status = "blocked"
    else:
        scores = scores_from_json(scores_json) if scores_json is not None else scores_from_model(inputs)
        assert_safe_payload({"scores": scores})
        metrics = compute_metrics(scores)
        scoring_status = "completed"
    metrics["runtime_boundary_confirmed"] = 1.0 if runtime["confirmed"] else 0.0
    deltas = metric_deltas(metrics)
    threshold_failures = [name for name, minimum in THRESHOLDS.items() if metrics.get(name, 0.0) < minimum]
    diagnostics = set(descriptor_summary.get("diagnostic_codes", [])) | set(runtime.get("diagnostic_codes", []))
    diagnostics.add("descriptor_scoring_completed" if scoring_status == "completed" else "descriptor_scoring_blocked")
    if threshold_failures:
        diagnostics.add("metric_mismatch")
    if any(value > 0 for key, value in deltas.items() if key != "delta_runtime_boundary_confirmed"):
        diagnostics.add("baseline_delta_positive")
    if any(value < 0 for key, value in deltas.items() if key != "delta_runtime_boundary_confirmed"):
        diagnostics.add("baseline_delta_negative")
    disposition = disposition_hint(metrics, deltas, threshold_failures, runtime["confirmed"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M025-50be7n",
        "slice_id": "S03",
        "status": scoring_status,
        "scoring_mode": SCORING_MODE,
        "descriptor_input_summary": descriptor_summary,
        "runtime_boundary": runtime,
        "score_count": len(scores),
        "scores": scores,
        "m024_baseline_metrics": M024_BASELINE,
        "metrics": metrics,
        "metric_deltas": deltas,
        "thresholds": THRESHOLDS,
        "threshold_failures": threshold_failures,
        "disposition_hint": disposition,
        "diagnostic_codes": sorted(diagnostics),
        "redaction": {
            "source_text_excluded": True,
            "query_text_excluded": True,
            "raw_vectors_excluded": True,
            "external_payloads_excluded": True,
            "generated_answer_prose_excluded": True,
            "generated_query_excluded": True,
            "absolute_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
        },
        "non_authoritative": True,
        "non_claims": [
            "Does not validate R035.",
            "Does not prove product retrieval quality.",
            "Does not prove legal-answer correctness.",
            "Does not prove graph-vector or HNSW behavior.",
            "Does not persist raw vectors.",
        ],
    }
    assert_safe_payload(report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-json", type=Path, help="Test-only injected runtime payload; rejected unless --allow-injected-test-inputs is set.")
    parser.add_argument("--scores-json", type=Path, help="Test-only injected scores payload; rejected unless --allow-injected-test-inputs is set.")
    parser.add_argument("--allow-injected-test-inputs", action="store_true", help="Allow injected runtime/scores only for unit tests. This mode cannot write the acceptance proof artifact.")
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.allow_injected_test_inputs and not args.no_write:
            raise DescriptorScoringError("test-only injected inputs cannot write acceptance proof")
        report = build_report(
            args.runtime_json,
            args.scores_json,
            args.timeout_seconds,
            allow_injected_test_inputs=args.allow_injected_test_inputs,
        )
        if not args.no_write:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except DescriptorScoringError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "scoring_mode": report["scoring_mode"],
                "metrics": report["metrics"],
                "metric_deltas": report["metric_deltas"],
                "threshold_failures": report["threshold_failures"],
                "disposition_hint": report["disposition_hint"],
                "diagnostic_codes": report["diagnostic_codes"],
                "non_authoritative": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
