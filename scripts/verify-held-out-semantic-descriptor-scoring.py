#!/usr/bin/env python3
"""Run M026 local semantic scoring over held-out safe descriptor inputs."""

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
DESCRIPTOR_INPUTS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json"
EVALUATION_LABELS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_evaluation_labels.json"
REPORT = ROOT / "prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_scoring_proof.json"
DESCRIPTOR_VERIFIER = ROOT / "scripts/verify-held-out-semantic-descriptor-inputs.py"
RUNTIME_CHECKER = ROOT / "scripts/check-local-retrieval-runtime.py"
MODEL_ID = "deepvk/USER-bge-m3"
EXPECTED_VECTOR_DIMENSION = 1024
SCHEMA_VERSION = "held-out-semantic-descriptor-scoring-proof/v1"
SCORING_MODE = "local_user_bge_m3_held_out_descriptor_similarity_v1"
M024_BASELINE = {
    "mrr": 0.875,
    "recall_at_1": 0.75,
    "recall_at_3": 1.0,
    "runtime_boundary_confirmed": 1.0,
}
M025_BOUNDED_RESULT = {
    "mrr": 1.0,
    "recall_at_1": 1.0,
    "recall_at_3": 1.0,
    "runtime_boundary_confirmed": 1.0,
}
FORBIDDEN_SCORING_INPUT_FIELD_NAMES = {
    "expected_label",
    "expected_rank",
    "rank",
    "expected_candidate_ids",
    "expected_rejected_candidate_ids",
    "expected_diagnostic_codes",
    "selection_reason",
    "expected_result",
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
} | FORBIDDEN_SCORING_INPUT_FIELD_NAMES
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


class HeldOutDescriptorScoringError(RuntimeError):
    """Raised when held-out descriptor scoring cannot safely produce a proof."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HeldOutDescriptorScoringError(f"input_missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HeldOutDescriptorScoringError(f"malformed JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise HeldOutDescriptorScoringError(f"JSON root must be object: {path}")
    return payload


def assert_safe_payload(payload: Mapping[str, Any], *, allow_labels: bool = False) -> None:
    forbidden = FORBIDDEN_FIELD_NAMES - (FORBIDDEN_SCORING_INPUT_FIELD_NAMES if allow_labels else set())

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in forbidden:
                    raise HeldOutDescriptorScoringError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    allowed_label_fragments = {"expected_candidate_ids"} if allow_labels else set()
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment in allowed_label_fragments:
            continue
        if fragment.lower() in serialized.lower():
            raise HeldOutDescriptorScoringError(f"unsafe payload fragment: {fragment}")
    if "provider_payloads_excluded" in serialized:
        raise HeldOutDescriptorScoringError("unsafe durable vocabulary")


def run_json_command(command: Sequence[str], timeout_seconds: int) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(list(command), cwd=ROOT, check=False, text=True, capture_output=True, timeout=timeout_seconds)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise HeldOutDescriptorScoringError(f"command returned non-JSON output: {command[0]}") from exc
    if not isinstance(payload, dict):
        raise HeldOutDescriptorScoringError("command returned non-object JSON")
    return completed.returncode, payload


def verify_descriptor_inputs(timeout_seconds: int) -> dict[str, Any]:
    exit_code, payload = run_json_command([sys.executable, str(DESCRIPTOR_VERIFIER)], timeout_seconds)
    if exit_code != 0 or payload.get("status") != "ok":
        raise HeldOutDescriptorScoringError("descriptor_input_verifier_failed")
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
    right_norm = math.sqrt(sum(a * a for a in right))
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
        raise HeldOutDescriptorScoringError("descriptor inputs missing")
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
        raise HeldOutDescriptorScoringError("observed scores missing")
    return [dict(row) for row in scores if isinstance(row, Mapping)]


def load_evaluation_labels(path: Path = EVALUATION_LABELS) -> dict[str, set[str]]:
    payload = load_json(path)
    assert_safe_payload(payload, allow_labels=True)
    if payload.get("schema_version") != "held-out-semantic-descriptor-evaluation-labels/v1":
        raise HeldOutDescriptorScoringError("evaluation label schema mismatch")
    if payload.get("post_scoring_only") is not True or payload.get("forbidden_as_descriptor_input") is not True:
        raise HeldOutDescriptorScoringError("evaluation label boundary missing")
    labels = payload.get("labels")
    if not isinstance(labels, list) or not labels:
        raise HeldOutDescriptorScoringError("evaluation labels missing")
    expected_by_case: dict[str, set[str]] = {}
    for row in labels:
        if not isinstance(row, Mapping):
            raise HeldOutDescriptorScoringError("evaluation label row must be object")
        if row.get("metric_scope") != "post_scoring_only" or row.get("non_authoritative") is not True:
            raise HeldOutDescriptorScoringError("evaluation label row boundary missing")
        expected = row.get("expected_candidate_ids")
        if not isinstance(expected, list) or not expected:
            raise HeldOutDescriptorScoringError("expected candidates missing")
        expected_by_case[str(row.get("case_id"))] = {str(candidate_id) for candidate_id in expected}
    return expected_by_case


def reciprocal_rank(expected: set[str], ranked_ids: Sequence[str]) -> float:
    for index, candidate_id in enumerate(ranked_ids, start=1):
        if candidate_id in expected:
            return round(1 / index, 6)
    return 0.0


def fraction(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 6)


def compute_metrics(scores: Sequence[Mapping[str, Any]], expected_by_case: Mapping[str, set[str]]) -> dict[str, float]:
    scores_by_case: dict[str, list[Mapping[str, Any]]] = {}
    for row in scores:
        if set(row).intersection(FORBIDDEN_SCORING_INPUT_FIELD_NAMES):
            raise HeldOutDescriptorScoringError(f"expected_answer_leakage: {row.get('case_id')}")
        if row.get("scoring_mode") != SCORING_MODE:
            raise HeldOutDescriptorScoringError(f"scoring mode mismatch: {row.get('case_id')}")
        if not isinstance(row.get("observed_similarity_score"), int | float):
            raise HeldOutDescriptorScoringError(f"observed score missing: {row.get('case_id')}")
        scores_by_case.setdefault(str(row.get("case_id")), []).append(row)
    rr_values: list[float] = []
    top1 = 0
    top3 = 0
    for case_id, expected in expected_by_case.items():
        rows = sorted(scores_by_case.get(case_id, []), key=lambda row: int(row.get("observed_rank", 999)))
        ranked_ids = [str(row["candidate_id"]) for row in rows]
        if not ranked_ids:
            raise HeldOutDescriptorScoringError(f"observed scores missing for held-out case: {case_id}")
        rr = reciprocal_rank(expected, ranked_ids)
        rr_values.append(rr)
        top1 += int(rr == 1.0)
        top3 += int(rr >= round(1 / 3, 6))
    return {"mrr": round(sum(rr_values) / len(rr_values), 6), "recall_at_1": fraction(top1, len(rr_values)), "recall_at_3": fraction(top3, len(rr_values))}


def metric_deltas(metrics: Mapping[str, float], baseline: Mapping[str, float], prefix: str) -> dict[str, float]:
    return {f"{prefix}_{name}": round(float(metrics.get(name, 0.0)) - value, 6) for name, value in baseline.items()}


def build_report(
    runtime_json: Path | None,
    scores_json: Path | None,
    timeout_seconds: int,
    *,
    allow_injected_test_inputs: bool = False,
) -> dict[str, Any]:
    if (runtime_json is not None or scores_json is not None) and not allow_injected_test_inputs:
        raise HeldOutDescriptorScoringError("injected runtime/scores JSON forbidden for acceptance proof")
    descriptor_summary = verify_descriptor_inputs(timeout_seconds)
    inputs = load_json(DESCRIPTOR_INPUTS)
    assert_safe_payload(inputs)
    runtime = runtime_boundary(timeout_seconds, runtime_json)
    if not runtime["confirmed"]:
        scores: list[dict[str, Any]] = []
        metrics = {"mrr": 0.0, "recall_at_1": 0.0, "recall_at_3": 0.0}
        scoring_status = "blocked"
    else:
        scores = scores_from_json(scores_json) if scores_json is not None else scores_from_model(inputs)
        assert_safe_payload({"scores": scores})
        labels = load_evaluation_labels()
        metrics = compute_metrics(scores, labels)
        scoring_status = "completed"
    metrics["runtime_boundary_confirmed"] = 1.0 if runtime["confirmed"] else 0.0
    diagnostics = set(descriptor_summary.get("diagnostic_codes", [])) | set(runtime.get("diagnostic_codes", []))
    diagnostics.add("held_out_descriptor_scoring_completed" if scoring_status == "completed" else "held_out_descriptor_scoring_blocked")
    report = {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M026-1uqmzc",
        "slice_id": "S03",
        "status": scoring_status,
        "scoring_mode": SCORING_MODE,
        "descriptor_input_summary": descriptor_summary,
        "evaluation_label_boundary": {
            "labels_artifact": "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_evaluation_labels.json",
            "post_scoring_only": True,
            "forbidden_as_descriptor_input": True,
        },
        "runtime_boundary": runtime,
        "score_count": len(scores),
        "scores": scores,
        "m024_baseline_metrics": M024_BASELINE,
        "m025_bounded_result_metrics": M025_BOUNDED_RESULT,
        "metrics": metrics,
        "metric_deltas_vs_m024": metric_deltas(metrics, M024_BASELINE, "delta_vs_m024"),
        "metric_deltas_vs_m025": metric_deltas(metrics, M025_BOUNDED_RESULT, "delta_vs_m025"),
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
            "Does not prove held-out semantic retrieval quality.",
            "Does not prove product retrieval quality.",
            "Does not prove legal-answer correctness.",
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
            raise HeldOutDescriptorScoringError("test-only injected inputs cannot write acceptance proof")
        report = build_report(args.runtime_json, args.scores_json, args.timeout_seconds, allow_injected_test_inputs=args.allow_injected_test_inputs)
        if not args.no_write:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except HeldOutDescriptorScoringError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "scoring_mode": report["scoring_mode"],
                "metrics": report["metrics"],
                "metric_deltas_vs_m024": report["metric_deltas_vs_m024"],
                "metric_deltas_vs_m025": report["metric_deltas_vs_m025"],
                "diagnostic_codes": report["diagnostic_codes"],
                "non_authoritative": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
