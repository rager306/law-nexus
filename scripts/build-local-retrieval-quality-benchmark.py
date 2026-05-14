#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd/retrieval/local_retrieval_quality_benchmark_contract.md"
OFFLINE_CASES_PATH = ROOT / "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
S10_PROOF_PATH = ROOT / ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json"
OUTPUT_PATH = ROOT / "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json"

SCHEMA_VERSION = "local-retrieval-quality-benchmark/v1"
GENERATED_BY = "scripts/build-local-retrieval-quality-benchmark.py"
FIXTURE_ARTIFACT = "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json"
MODEL_ID = "deepvk/USER-bge-m3"
EXPECTED_DIMENSION = 1024

NON_CLAIMS = [
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove legal interpretation authority.",
    "Does not prove production FalkorDB runtime behavior.",
    "Does not prove production graph schema readiness.",
    "Does not allow managed embedding API fallback.",
    "Does not promote GigaEmbeddings.",
    "Does not close GATE-G011 unless final milestone validation explicitly confirms full gate criteria.",
    "Does not close GATE-G008.",
    "Does not make LLM output legal authority.",
]

THRESHOLDS = {
    "mrr": 1.0,
    "recall_at_1": 1.0,
    "recall_at_3": 1.0,
    "no_answer_accuracy": 1.0,
    "ambiguous_rejection_rate": 1.0,
    "unsafe_rejection_rate": 1.0,
}

FORBIDDEN_PAYLOAD_FIELDS = [
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
    "falkordb_row",
    "runtime_row",
    "generated_answer_prose",
    "legal_advice",
    "llm_reasoning",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def source_artifacts() -> list[dict[str, str]]:
    return [
        {"path": relative(path), "sha256": sha256_path(path)}
        for path in [CONTRACT_PATH, OFFLINE_CASES_PATH, S10_PROOF_PATH]
    ]


def case_by_class(offline: dict[str, Any], case_class: str) -> dict[str, Any]:
    return next(case for case in offline["cases"] if case["case_class"] == case_class)


def model_boundary(s10: dict[str, Any]) -> dict[str, Any]:
    model = next(row for row in s10["models"] if row["id"] == MODEL_ID)
    return {
        "model_id": MODEL_ID,
        "model_status": "available" if model.get("package_status") == "available" and model.get("cache_status") == "available" else "blocked_environment",
        "observed_vector_dimension": model.get("observed_vector_dimension"),
        "runtime_evidence_source": relative(S10_PROOF_PATH),
        "managed_api_used": False,
        "raw_vectors_persisted": False,
        "quality_boundary": s10["fixture_policy"]["quality_boundary"],
        "cache_status": model.get("cache_status"),
        "package_status": model.get("package_status"),
    }


def query(query_id: str, kind: str, label: str, relevant: list[str], expected: str) -> dict[str, Any]:
    return {
        "benchmark_query_id": query_id,
        "query_kind": kind,
        "query_text_sha256": sha256_text(label),
        "scope_id": "SCOPE-M015-LOCAL-RETRIEVAL-QUALITY-001",
        "expected_relevant_candidate_ids": relevant,
        "expected_result": expected,
    }


def candidate(
    *,
    candidate_id: str,
    source_case: dict[str, Any],
    relevance_label: str,
    rank: int | None,
    deterministic_score: float | None,
) -> dict[str, Any]:
    source_record_ids = source_case.get("source_record_ids") or []
    return {
        "candidate_id": candidate_id,
        "source_case_id": source_case["case_id"],
        "source_record_ids": source_record_ids,
        "relevance_label": relevance_label,
        "score_input_id": f"SCORE-M015-{candidate_id.removeprefix('BQ-M015-')}",
        "source_artifact": relative(OFFLINE_CASES_PATH),
        "rank": rank,
        "deterministic_score": deterministic_score,
    }


def diagnostic(code: str, *, case_id: str, query_id: str, severity: str = "info", candidate_id: str | None = None, metric: str | None = None, field_path: str | None = None) -> dict[str, str]:
    payload = {
        "code": code,
        "severity": severity,
        "benchmark_case_id": case_id,
        "benchmark_query_id": query_id,
        "proof_artifact": FIXTURE_ARTIFACT,
    }
    if candidate_id:
        payload["candidate_id"] = candidate_id
    if metric:
        payload["metric"] = metric
    if field_path:
        payload["field_path"] = field_path
    return payload


def benchmark_case(case_id: str, case_class: str, query_obj: dict[str, Any], candidates: list[dict[str, Any]], expected_metrics: dict[str, float], expected_diagnostics: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "benchmark_case_id": case_id,
        "case_class": case_class,
        "query": query_obj,
        "candidates": candidates,
        "expected_metrics": expected_metrics,
        "expected_diagnostic_codes": [item["code"] for item in expected_diagnostics],
        "diagnostics": expected_diagnostics,
        "non_authoritative": True,
    }


def build_payload() -> dict[str, Any]:
    offline = load_json(OFFLINE_CASES_PATH)
    s10 = load_json(S10_PROOF_PATH)
    exact = case_by_class(offline, "valid_exact_record_candidate")
    marker = case_by_class(offline, "valid_marker_level_candidate")
    ambiguous = case_by_class(offline, "ambiguous_candidate_set")
    unsafe = case_by_class(offline, "unsafe_candidate_payload")

    positive_candidate = candidate(
        candidate_id="BQ-M015-ARTICLE-0001-EXACT",
        source_case=exact,
        relevance_label="relevant",
        rank=1,
        deterministic_score=1.0,
    )
    relevant_with_distractor = candidate(
        candidate_id="BQ-M015-ARTICLE-0001-MARKER",
        source_case=marker,
        relevance_label="relevant",
        rank=1,
        deterministic_score=0.95,
    )
    distractor_candidate = candidate(
        candidate_id="BQ-M015-ARTICLE-0001-DISTRACTOR",
        source_case=exact,
        relevance_label="distractor",
        rank=2,
        deterministic_score=0.15,
    )

    cases = [
        benchmark_case(
            "CASE-M015-POSITIVE-EXACT-RELEVANCE",
            "positive_exact_relevance",
            query("QR-M015-POSITIVE-EXACT-001", "positive_retrieval", "m015 positive exact article benchmark", [positive_candidate["candidate_id"]], "metrics_pass"),
            [positive_candidate],
            {"mrr": 1.0, "recall_at_1": 1.0, "recall_at_3": 1.0},
            [],
        ),
        benchmark_case(
            "CASE-M015-POSITIVE-WITH-DISTRACTOR",
            "positive_with_distractor",
            query("QR-M015-POSITIVE-DISTRACTOR-001", "distractor_retrieval", "m015 positive with distractor benchmark", [relevant_with_distractor["candidate_id"]], "metrics_pass"),
            [relevant_with_distractor, distractor_candidate],
            {"mrr": 1.0, "recall_at_1": 1.0, "recall_at_3": 1.0},
            [],
        ),
        benchmark_case(
            "CASE-M015-SCOPED-NO-ANSWER-QUALITY",
            "scoped_no_answer_quality",
            query("QR-M015-SCOPED-NO-ANSWER-001", "scoped_no_answer", "m015 scoped no answer benchmark", [], "scoped_no_answer"),
            [],
            {"no_answer_accuracy": 1.0},
            [diagnostic("scoped_no_answer", case_id="CASE-M015-SCOPED-NO-ANSWER-QUALITY", query_id="QR-M015-SCOPED-NO-ANSWER-001", metric="no_answer_accuracy")],
        ),
        benchmark_case(
            "CASE-M015-AMBIGUOUS-RETRIEVAL-REJECTED",
            "ambiguous_retrieval_rejected",
            query("QR-M015-AMBIGUOUS-001", "ambiguous_retrieval", "m015 ambiguous retrieval benchmark", [], "rejected"),
            [
                candidate(candidate_id="BQ-M015-AMBIGUOUS-0001", source_case=ambiguous, relevance_label="ambiguous", rank=None, deterministic_score=None),
                candidate(candidate_id="BQ-M015-AMBIGUOUS-0002", source_case=ambiguous, relevance_label="ambiguous", rank=None, deterministic_score=None),
            ],
            {"ambiguous_rejection_rate": 1.0},
            [diagnostic("ambiguous_rejected", case_id="CASE-M015-AMBIGUOUS-RETRIEVAL-REJECTED", query_id="QR-M015-AMBIGUOUS-001", severity="warning", metric="ambiguous_rejection_rate")],
        ),
        benchmark_case(
            "CASE-M015-UNSAFE-PAYLOAD-REJECTED",
            "unsafe_payload_rejected",
            query("QR-M015-UNSAFE-001", "unsafe_payload", "m015 unsafe payload benchmark", [], "rejected"),
            [candidate(candidate_id="BQ-M015-UNSAFE-0001", source_case=unsafe, relevance_label="unsafe", rank=None, deterministic_score=None)],
            {"unsafe_rejection_rate": 1.0},
            [diagnostic("unsafe_payload_rejected", case_id="CASE-M015-UNSAFE-PAYLOAD-REJECTED", query_id="QR-M015-UNSAFE-001", severity="error", candidate_id="BQ-M015-UNSAFE-0001", metric="unsafe_rejection_rate")],
        ),
        benchmark_case(
            "CASE-M015-ENVIRONMENT-BOUNDARY",
            "environment_boundary",
            query("QR-M015-ENVIRONMENT-001", "positive_retrieval", "m015 environment boundary benchmark", [], "metrics_pass"),
            [],
            {},
            [diagnostic("model_runtime_available", case_id="CASE-M015-ENVIRONMENT-BOUNDARY", query_id="QR-M015-ENVIRONMENT-001", metric="environment")],
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_artifact": FIXTURE_ARTIFACT,
        "generated_by": GENERATED_BY,
        "contract": relative(CONTRACT_PATH),
        "gate": "GATE-G011",
        "non_authoritative": True,
        "source_artifacts": source_artifacts(),
        "model_boundary": model_boundary(s10),
        "thresholds": THRESHOLDS,
        "allowed_relevance_labels": ["relevant", "distractor", "ambiguous", "no_answer", "unsafe"],
        "forbidden_payload_fields": FORBIDDEN_PAYLOAD_FIELDS,
        "cases": cases,
        "non_claims": NON_CLAIMS,
    }


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic M015 local retrieval quality benchmark fixture.")
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in fixture is stale.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Fixture output path.")
    args = parser.parse_args(argv)

    payload = build_payload()
    rendered = stable_json(payload)
    output_path = args.output
    if args.check:
        try:
            current = output_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(json.dumps({"status": "fail", "reason": "missing_output", "path": relative(output_path)}, sort_keys=True))
            return 1
        if current != rendered:
            print(json.dumps({"status": "fail", "reason": "stale_output", "path": relative(output_path)}, sort_keys=True))
            return 1
        print(json.dumps({"status": "pass", "case_count": len(payload["cases"]), "model_id": payload["model_boundary"]["model_id"], "path": relative(output_path)}, sort_keys=True))
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(json.dumps({"status": "written", "case_count": len(payload["cases"]), "model_id": payload["model_boundary"]["model_id"], "path": relative(output_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
