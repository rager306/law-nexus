from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json"
SUMMARY_SCHEMA_VERSION = "local-retrieval-quality-benchmark-proof/v1"
_MAX_SAFE_FIELD_LENGTH = 180
_ALLOWED_DIAGNOSTIC_FIELDS = frozenset(
    {
        "code",
        "severity",
        "benchmark_case_id",
        "benchmark_query_id",
        "candidate_id",
        "metric",
        "field_path",
        "proof_artifact",
    }
)
_ALLOWED_DIAGNOSTIC_CODES = frozenset(
    {
        "scoped_no_answer",
        "ambiguous_rejected",
        "unsafe_payload_rejected",
        "model_runtime_available",
        "threshold_mismatch",
        "metric_mismatch",
        "malformed_fixture_json",
        "malformed_fixture_shape",
        "fixture_not_found",
        "unsafe_payload_field",
        "unsafe_diagnostic_field",
        "unsafe_text_payload",
    }
)
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
        "embedding",
        "falkordb_row",
        "runtime_row",
        "generated_answer_prose",
        "legal_advice",
        "llm_reasoning",
    }
)
_FORBIDDEN_TEXT_SNIPPETS = (
    "/root/",
    ".gsd/exec",
    "BEGIN PRIVATE KEY",
    "provider response body",
    "legal advice:",
    "Настоящий Федеральный закон регулирует отношения",
)
_REQUIRED_THRESHOLD_KEYS = (
    "mrr",
    "recall_at_1",
    "recall_at_3",
    "no_answer_accuracy",
    "ambiguous_rejection_rate",
    "unsafe_rejection_rate",
)


def _bounded_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)[:_MAX_SAFE_FIELD_LENGTH]


def _error_summary(*, fixture: Path, phase: str, code: str, detail: str | None = None) -> dict[str, Any]:
    mismatch: dict[str, Any] = {
        "phase": phase,
        "code": code,
        "fixture_path": _bounded_path(fixture),
    }
    if detail:
        mismatch["detail"] = detail[:_MAX_SAFE_FIELD_LENGTH]
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "fixture_path": _bounded_path(fixture),
        "total_cases": 0,
        "positive_query_count": 0,
        "threshold_passed": False,
        "metrics": {},
        "model_id": None,
        "model_status": None,
        "managed_api_used": None,
        "raw_vectors_persisted": None,
        "mismatch_count": 1,
        "diagnostic_code_inventory": [],
        "mismatches": [mismatch],
    }


def _load_json(path: Path) -> tuple[int, dict[str, Any] | None, dict[str, Any] | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        return 2, None, _error_summary(fixture=path, phase="fixture_load", code="fixture_not_found", detail=str(exc))
    except json.JSONDecodeError as exc:
        return 2, None, _error_summary(fixture=path, phase="fixture_load", code="malformed_fixture_json", detail=exc.msg)
    except OSError as exc:
        return 2, None, _error_summary(fixture=path, phase="fixture_load", code="malformed_fixture_shape", detail=str(exc))
    if not isinstance(data, dict):
        return 2, None, _error_summary(fixture=path, phase="fixture_shape", code="malformed_fixture_shape", detail="fixture root must be an object")
    return 0, data, None


def _walk_payload(value: Any, *, path: str = "") -> list[tuple[str, Any]]:
    found = [(path, value)]
    if isinstance(value, Mapping):
        for key, item in value.items():
            found.extend(_walk_payload(item, path=f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_payload(item, path=f"{path}[{index}]"))
    return found


def _safety_errors(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for path, value in _walk_payload(data):
        if isinstance(value, Mapping):
            for key in sorted(set(value) & _FORBIDDEN_FIELD_NAMES):
                errors.append(
                    {
                        "phase": "payload_safety",
                        "code": "unsafe_payload_field",
                        "field_path": f"{path}.{key}" if path else key,
                    }
                )
        if isinstance(value, str):
            for snippet in _FORBIDDEN_TEXT_SNIPPETS:
                if snippet in value:
                    errors.append(
                        {
                            "phase": "payload_safety",
                            "code": "unsafe_text_payload",
                            "field_path": path,
                        }
                    )
    return errors


def _diagnostics(case: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    diagnostics = case.get("diagnostics")
    if not isinstance(diagnostics, list):
        return []
    return [diagnostic for diagnostic in diagnostics if isinstance(diagnostic, Mapping)]


def _diagnostic_safety_errors(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    case_id = str(case.get("benchmark_case_id", "<missing-case-id>"))[:_MAX_SAFE_FIELD_LENGTH]
    errors: list[dict[str, Any]] = []
    for index, diagnostic in enumerate(_diagnostics(case)):
        extra = sorted(set(diagnostic) - _ALLOWED_DIAGNOSTIC_FIELDS)
        if extra:
            errors.append(
                {
                    "phase": "diagnostic_safety",
                    "case_id": case_id,
                    "code": "unsafe_diagnostic_field",
                    "field_path": f"diagnostics[{index}]",
                    "actual_fields": extra,
                }
            )
        code = diagnostic.get("code")
        if code not in _ALLOWED_DIAGNOSTIC_CODES:
            errors.append(
                {
                    "phase": "diagnostic_safety",
                    "case_id": case_id,
                    "code": "unsafe_diagnostic_field",
                    "field_path": f"diagnostics[{index}].code",
                    "actual_code": str(code)[:_MAX_SAFE_FIELD_LENGTH],
                }
            )
    return errors


def _rank_metrics(case: Mapping[str, Any]) -> dict[str, float]:
    query = case.get("query")
    candidates = case.get("candidates")
    if not isinstance(query, Mapping) or not isinstance(candidates, list):
        return {}
    relevant_ids = query.get("expected_relevant_candidate_ids")
    if not isinstance(relevant_ids, list) or not relevant_ids:
        return {}
    relevant = {candidate_id for candidate_id in relevant_ids if isinstance(candidate_id, str)}
    ranks: list[int] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        if candidate.get("candidate_id") in relevant and isinstance(candidate.get("rank"), int):
            ranks.append(candidate["rank"])
    if not ranks:
        return {"mrr": 0.0, "recall_at_1": 0.0, "recall_at_3": 0.0}
    best_rank = min(ranks)
    return {
        "mrr": round(1.0 / best_rank, 6),
        "recall_at_1": 1.0 if best_rank <= 1 else 0.0,
        "recall_at_3": 1.0 if best_rank <= 3 else 0.0,
    }


def _case_metrics(case: Mapping[str, Any]) -> dict[str, float]:
    case_class = case.get("case_class")
    if case_class in {"positive_exact_relevance", "positive_with_distractor"}:
        return _rank_metrics(case)
    if case_class == "scoped_no_answer_quality":
        query = case.get("query")
        candidates = case.get("candidates")
        is_no_answer = isinstance(query, Mapping) and query.get("expected_result") == "scoped_no_answer" and candidates == []
        return {"no_answer_accuracy": 1.0 if is_no_answer else 0.0}
    if case_class == "ambiguous_retrieval_rejected":
        labels = [candidate.get("relevance_label") for candidate in case.get("candidates", []) if isinstance(candidate, Mapping)]
        query = case.get("query")
        rejected = isinstance(query, Mapping) and query.get("expected_result") == "rejected" and labels.count("ambiguous") >= 2
        return {"ambiguous_rejection_rate": 1.0 if rejected else 0.0}
    if case_class == "unsafe_payload_rejected":
        labels = [candidate.get("relevance_label") for candidate in case.get("candidates", []) if isinstance(candidate, Mapping)]
        query = case.get("query")
        rejected = isinstance(query, Mapping) and query.get("expected_result") == "rejected" and "unsafe" in labels
        return {"unsafe_rejection_rate": 1.0 if rejected else 0.0}
    return {}


def _metric_mismatch(*, case_id: str, expected: Mapping[str, Any], actual: Mapping[str, float]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    if dict(expected) != actual:
        mismatches.append(
            {
                "phase": "case_metrics",
                "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
                "code": "metric_mismatch",
                "expected": dict(expected),
                "actual": actual,
            }
        )
    return mismatches


def _aggregate_metrics(per_case_metrics: list[Mapping[str, float]]) -> dict[str, float]:
    values: dict[str, list[float]] = {key: [] for key in _REQUIRED_THRESHOLD_KEYS}
    for metrics in per_case_metrics:
        for key, value in metrics.items():
            if key in values:
                values[key].append(float(value))
    return {key: round(sum(items) / len(items), 6) if items else 0.0 for key, items in values.items()}


def _threshold_mismatches(metrics: Mapping[str, float], thresholds: Mapping[str, Any]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for key in _REQUIRED_THRESHOLD_KEYS:
        threshold = thresholds.get(key)
        actual = metrics.get(key)
        if not isinstance(threshold, (int, float)) or actual is None or actual < float(threshold):
            mismatches.append(
                {
                    "phase": "thresholds",
                    "code": "threshold_mismatch",
                    "metric": key,
                    "expected_minimum": threshold,
                    "actual": actual,
                }
            )
    return mismatches


def _code_inventory(cases: Sequence[Mapping[str, Any]], mismatches: Sequence[Mapping[str, Any]]) -> list[str]:
    inventory: Counter[str] = Counter()
    for case in cases:
        for diagnostic in _diagnostics(case):
            code = diagnostic.get("code")
            if isinstance(code, str):
                inventory[code] += 1
    for mismatch in mismatches:
        code = mismatch.get("code")
        if isinstance(code, str):
            inventory[code] += 1
    return sorted(inventory)


def run_proof(fixture_path: Path) -> tuple[int, dict[str, Any]]:
    load_code, data, load_error = _load_json(fixture_path)
    if load_code != 0:
        assert load_error is not None
        return load_code, load_error
    assert data is not None

    cases = data.get("cases")
    if not isinstance(cases, list):
        return 2, _error_summary(fixture=fixture_path, phase="fixture_shape", code="malformed_fixture_shape", detail="cases must be a list")
    case_records = [case for case in cases if isinstance(case, Mapping)]
    mismatches: list[dict[str, Any]] = []
    if len(case_records) != len(cases):
        mismatches.append({"phase": "fixture_shape", "code": "malformed_fixture_shape", "field_path": "cases"})

    mismatches.extend(_safety_errors(data))
    per_case: list[Mapping[str, float]] = []
    positive_query_count = 0
    for case in case_records:
        case_id = str(case.get("benchmark_case_id", "<missing-case-id>"))
        metrics = _case_metrics(case)
        per_case.append(metrics)
        query = case.get("query")
        if isinstance(query, Mapping) and query.get("query_kind") in {"positive_retrieval", "distractor_retrieval"} and metrics:
            positive_query_count += 1
        expected_metrics = case.get("expected_metrics")
        if not isinstance(expected_metrics, Mapping):
            mismatches.append({"phase": "fixture_shape", "case_id": case_id, "code": "malformed_fixture_shape", "field_path": "expected_metrics"})
        else:
            mismatches.extend(_metric_mismatch(case_id=case_id, expected=expected_metrics, actual=dict(metrics)))
        expected_codes = case.get("expected_diagnostic_codes")
        actual_codes = [str(diagnostic.get("code")) for diagnostic in _diagnostics(case) if isinstance(diagnostic.get("code"), str)]
        if actual_codes != expected_codes:
            mismatches.append(
                {
                    "phase": "case_diagnostics",
                    "case_id": case_id[:_MAX_SAFE_FIELD_LENGTH],
                    "code": "metric_mismatch",
                    "field_path": "expected_diagnostic_codes",
                    "expected": expected_codes,
                    "actual": actual_codes,
                }
            )
        mismatches.extend(_diagnostic_safety_errors(case))

    aggregate = _aggregate_metrics(per_case)
    thresholds = data.get("thresholds") if isinstance(data.get("thresholds"), Mapping) else {}
    mismatches.extend(_threshold_mismatches(aggregate, thresholds))

    model = data.get("model_boundary") if isinstance(data.get("model_boundary"), Mapping) else {}
    if model.get("managed_api_used") is not False:
        mismatches.append({"phase": "model_boundary", "code": "malformed_fixture_shape", "field_path": "model_boundary.managed_api_used"})
    if model.get("raw_vectors_persisted") is not False:
        mismatches.append({"phase": "model_boundary", "code": "malformed_fixture_shape", "field_path": "model_boundary.raw_vectors_persisted"})

    threshold_passed = not _threshold_mismatches(aggregate, thresholds)
    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "fixture_path": _bounded_path(fixture_path),
        "total_cases": len(cases),
        "positive_query_count": positive_query_count,
        "threshold_passed": threshold_passed,
        "metrics": aggregate,
        "model_id": model.get("model_id"),
        "model_status": model.get("model_status"),
        "observed_vector_dimension": model.get("observed_vector_dimension"),
        "managed_api_used": model.get("managed_api_used"),
        "raw_vectors_persisted": model.get("raw_vectors_persisted"),
        "mismatch_count": len(mismatches),
        "diagnostic_code_inventory": _code_inventory(case_records, mismatches),
        "non_authoritative": data.get("non_authoritative") is True,
    }
    if mismatches:
        summary["mismatches"] = mismatches
    return (0 if not mismatches else 1), summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the M015 local retrieval quality benchmark proof.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE, help="Path to local retrieval quality benchmark fixture JSON.")
    args = parser.parse_args(argv)
    exit_code, summary = run_proof(args.fixture)
    json.dump(summary, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
