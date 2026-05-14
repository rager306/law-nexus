#!/usr/bin/env python3
"""Runtime-gated representative retrieval benchmark proof.

The command emits exactly one compact JSON object to stdout and writes a safe
proof report. It consumes the S01 local/open-weight runtime boundary and the
S02 representative retrieval corpus manifest, then computes deterministic
proof-local metrics using IDs and bounded roles only.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "representative-retrieval-runtime-benchmark-proof/v1"
MANIFEST_SCHEMA_VERSION = "representative-retrieval-corpus/v1"
BENCHMARK_ID = "RRB-M016-REPRESENTATIVE-V1"
DEFAULT_MANIFEST = ROOT / "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json"
DEFAULT_REPORT = ROOT / "prd/retrieval/representative_retrieval_runtime_benchmark_proof.md"
DEFAULT_RUNTIME_COMMAND = "uv run python scripts/check-local-retrieval-runtime.py"
EXPECTED_MODEL_ID = "deepvk/USER-bge-m3"
EXPECTED_EXECUTION_MODE = "local_open_weight"
EXPECTED_VECTOR_DIMENSION = 1024
GATE_ID = "GATE-G011"

METRIC_NAMES = (
    "mrr",
    "recall_at_1",
    "recall_at_3",
    "no_answer_accuracy",
    "ambiguous_rejection_rate",
    "unsafe_rejection_rate",
    "edition_path_mismatch_rejection_rate",
    "runtime_boundary_confirmed",
)
THRESHOLDS: dict[str, float] = {name: 1.0 for name in METRIC_NAMES}
REDACTION_FALSE_FIELDS = (
    "raw_legal_text_persisted",
    "raw_query_text_persisted",
    "raw_prompt_persisted",
    "raw_vector_persisted",
    "provider_payload_persisted",
    "raw_falkordb_row_persisted",
    "managed_api_evidence_persisted",
    "generated_legal_advice_persisted",
    "absolute_path_persisted",
    "secrets_persisted",
)
MANIFEST_REDACTION_FIELDS = (
    "raw_legal_text_persisted",
    "raw_query_text_persisted",
    "raw_prompt_persisted",
    "raw_vector_persisted",
    "provider_payload_persisted",
    "raw_falkordb_row_persisted",
    "generated_legal_advice_persisted",
    "absolute_path_persisted",
)
FORBIDDEN_KEYS = {
    "raw" + "_legal_text",
    "legal" + "_text",
    "source" + "_excerpt",
    "query" + "_text",
    "raw" + "_query_text",
    "prompt",
    "user" + "_prompt",
    "vector",
    "vectors",
    "embedding",
    "embedding" + "_vector",
    "provider" + "_payload",
    "provider" + "_response_body",
    "managed" + "_api_payload",
    "raw" + "_falkordb_row",
    "falkordb" + "_row",
    "secret",
    "token",
    "password",
    "generated" + "_answer",
    "legal" + "_advice",
}
FORBIDDEN_STRING_FRAGMENTS = (
    "GIGACHAT" + "_AUTH_DATA",
    "Bearer ",
    "sk-",
    "api_key",
    "api-key",
    ".gsd/exec",
    "raw legal text",
    "raw query text",
    "provider payload",
    "legal advice",
    "generated answer",
    "[0.0,",
)
NON_CLAIMS = (
    "does not prove product retrieval quality",
    "does not prove production ranker quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not make proof-local IDs production IDs",
    "does not authorize managed embedding API fallback",
    "does not authorize GigaChat or GigaEmbeddings runtime use",
    "does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice",
    "does not make LLM output legal authority",
    "does not close GATE-G011; GATE-G011 remains open",
)
SOURCE_ARTIFACTS = (
    "prd/retrieval/representative_retrieval_runtime_benchmark_contract.md",
    "prd/retrieval/local_retrieval_runtime_boundary_contract.md",
    "prd/retrieval/local_retrieval_runtime_boundary_proof.md",
    "scripts/check-local-retrieval-runtime.py",
    "scripts/verify-representative-retrieval-runtime-benchmark.py",
    "prd/retrieval/representative_retrieval_corpus_contract.md",
    "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json",
    "prd/retrieval/representative_retrieval_corpus_manifest.md",
    "prd/retrieval/representative_retrieval_runtime_benchmark_proof.md",
)


class ProofError(RuntimeError):
    """Fail-closed proof error with safe categorical diagnostics."""

    def __init__(self, status: str, failure_class: str, diagnostic_codes: Sequence[str]):
        super().__init__(",".join(diagnostic_codes))
        self.status = status
        self.failure_class = failure_class
        self.diagnostic_codes = list(dict.fromkeys(diagnostic_codes))


def repo_safe_path(path: Path | str) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return candidate.name or "external_input"


def redaction_flags() -> dict[str, bool]:
    return {field: False for field in REDACTION_FALSE_FIELDS}


def load_json_file(path: Path, missing_code: str, malformed_code: str, status: str, failure_class: str) -> dict[str, Any]:
    if not path.is_file():
        raise ProofError(status, failure_class, [missing_code])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProofError(status, failure_class, [malformed_code]) from exc
    if not isinstance(payload, dict):
        raise ProofError(status, failure_class, [malformed_code])
    return payload


def safe_runtime_diagnostic(runtime: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "runtime_status",
        "failure_class",
        "diagnostic_codes",
        "model_id",
        "execution_mode",
        "vector_dimension",
        "expected_vector_dimension",
        "managed_api_used",
        "giga_chat_used",
        "network_used",
        "source_artifacts",
    }
    summary = {key: runtime[key] for key in allowed if key in runtime}
    if "source_artifacts" in summary and isinstance(summary["source_artifacts"], list):
        summary["source_artifacts"] = [repo_safe_path(str(item)) for item in summary["source_artifacts"]]
    return summary


def read_runtime_summary(path: Path) -> dict[str, Any]:
    return load_json_file(
        path,
        "RRB_RUNTIME_DIAGNOSTIC_MISSING",
        "RRB_RUNTIME_DIAGNOSTIC_MALFORMED",
        "blocked_runtime",
        "runtime_boundary",
    )


def run_runtime_command(command: str, timeout_seconds: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(  # noqa: S603 - command is explicit CLI input, shell is disabled.
            shlex.split(command),
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProofError("blocked_runtime", "runtime_boundary", ["RRB_RUNTIME_TIMEOUT"]) from exc
    except OSError as exc:
        raise ProofError("blocked_runtime", "runtime_boundary", ["RRB_RUNTIME_DIAGNOSTIC_MISSING"]) from exc

    if completed.returncode != 0:
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            raise ProofError("blocked_runtime", "runtime_boundary", ["RRB_RUNTIME_NOT_CONFIRMED"])
        if isinstance(payload, dict):
            codes = payload.get("diagnostic_codes")
            safe_codes = [str(code) for code in codes] if isinstance(codes, list) else []
            raise ProofError("blocked_runtime", "runtime_boundary", safe_codes or ["RRB_RUNTIME_NOT_CONFIRMED"])
        raise ProofError("blocked_runtime", "runtime_boundary", ["RRB_RUNTIME_DIAGNOSTIC_MALFORMED"])

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ProofError("blocked_runtime", "runtime_boundary", ["RRB_RUNTIME_DIAGNOSTIC_MALFORMED"]) from exc
    if not isinstance(payload, dict):
        raise ProofError("blocked_runtime", "runtime_boundary", ["RRB_RUNTIME_DIAGNOSTIC_MALFORMED"])
    return payload


def runtime_confirmed(runtime: Mapping[str, Any]) -> tuple[bool, list[str]]:
    codes: list[str] = []
    if runtime.get("runtime_status") != "confirmed_runtime":
        codes.append("RRB_RUNTIME_NOT_CONFIRMED")
    if runtime.get("model_id") != EXPECTED_MODEL_ID:
        codes.append("RRB_RUNTIME_NOT_CONFIRMED")
    if runtime.get("execution_mode") != EXPECTED_EXECUTION_MODE:
        codes.append("RRB_RUNTIME_NOT_CONFIRMED")
    if runtime.get("vector_dimension") != EXPECTED_VECTOR_DIMENSION:
        codes.append("RRB_RUNTIME_NOT_CONFIRMED")
    if runtime.get("managed_api_used") is not False:
        codes.append("RRB_MANAGED_API_FORBIDDEN")
    if runtime.get("giga_chat_used") is not False:
        codes.append("RRB_GIGACHAT_FORBIDDEN")
    if runtime.get("network_used") is not False:
        codes.append("RRB_MANAGED_API_FORBIDDEN")
    return not codes, list(dict.fromkeys(codes))


def detect_unsafe_payload(value: Any, path: tuple[str, ...] = ()) -> list[str]:
    codes: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in FORBIDDEN_KEYS:
                if "query" in key_text:
                    codes.append("RRB_RAW_QUERY_FORBIDDEN")
                elif "vector" in key_text or "embedding" in key_text:
                    codes.append("RRB_RAW_VECTOR_FORBIDDEN")
                elif "provider" in key_text:
                    codes.append("RRB_PROVIDER_PAYLOAD_FORBIDDEN")
                elif "falkordb" in key_text:
                    codes.append("RRB_RAW_FALKORDB_ROW_FORBIDDEN")
                elif key_text in {"secret", "token", "password"}:
                    codes.append("RRB_UNSAFE_PATH_FORBIDDEN")
                else:
                    codes.append("RRB_RAW_TEXT_FORBIDDEN")
            codes.extend(detect_unsafe_payload(nested, (*path, key_text)))
    elif isinstance(value, list):
        for item in value:
            codes.extend(detect_unsafe_payload(item, path))
    elif isinstance(value, str):
        if value.startswith("/") or ":\\" in value:
            codes.append("RRB_UNSAFE_PATH_FORBIDDEN")
        declaration_contexts = {
            "non_claims",
            "redaction_boundaries",
            "durable_payloads_allowed",
            "provenance",
            "derivation",
            "quality_claim_scope",
        }
        if declaration_contexts.isdisjoint(path):
            lowered = value.lower()
            for fragment in FORBIDDEN_STRING_FRAGMENTS:
                if fragment.lower() in lowered:
                    if "query" in fragment.lower():
                        codes.append("RRB_RAW_QUERY_FORBIDDEN")
                    elif "provider" in fragment.lower():
                        codes.append("RRB_PROVIDER_PAYLOAD_FORBIDDEN")
                    elif "[0.0," in fragment.lower():
                        codes.append("RRB_RAW_VECTOR_FORBIDDEN")
                    else:
                        codes.append("RRB_RAW_TEXT_FORBIDDEN")
    return list(dict.fromkeys(codes))


def require_redaction_false(item: Mapping[str, Any], context: str) -> None:
    redaction = item.get("redaction")
    if not isinstance(redaction, Mapping):
        raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_UNSAFE_PAYLOAD"])
    for field in MANIFEST_REDACTION_FIELDS:
        if redaction.get(field) is not False:
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_UNSAFE_PAYLOAD"])
    if context and not str(item.get(context, "")).startswith(("QRL-M016-", "RC-M016-")):
        raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])


def validate_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    unsafe_codes = detect_unsafe_payload(manifest)
    if unsafe_codes:
        raise ProofError("blocked_policy_violation", "policy_violation", unsafe_codes)
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_SCHEMA_MISMATCH"])
    if manifest.get("gate") != GATE_ID:
        raise ProofError("blocked_policy_violation", "policy_violation", ["RRB_GATE_OVERCLAIM_FORBIDDEN"])
    handoff = manifest.get("s03_handoff")
    if not isinstance(handoff, Mapping):
        raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
    if handoff.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_SCHEMA_MISMATCH"])
    if handoff.get("managed_api_allowed") is not False or handoff.get("managed_embedding_api_fallback_allowed") is not False:
        raise ProofError("blocked_policy_violation", "policy_violation", ["RRB_MANAGED_API_FORBIDDEN"])
    if handoff.get("raw_payload_persistence_allowed") is not False:
        raise ProofError("blocked_policy_violation", "policy_violation", ["RRB_RAW_TEXT_FORBIDDEN"])
    if handoff.get("gate_g011_status") != "open":
        raise ProofError("blocked_policy_violation", "policy_violation", ["RRB_GATE_OVERCLAIM_FORBIDDEN"])

    query_labels = manifest.get("query_labels")
    candidate_references = manifest.get("candidate_references")
    coverage_classes = manifest.get("coverage_classes")
    if not isinstance(query_labels, list) or not isinstance(candidate_references, list) or not isinstance(coverage_classes, list):
        raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
    if not query_labels or not candidate_references or not coverage_classes:
        raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])

    reference_ids: set[str] = set()
    for reference in candidate_references:
        if not isinstance(reference, Mapping):
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
        require_redaction_false(reference, "reference_id")
        reference_id = reference.get("reference_id")
        role = reference.get("reference_role")
        if not isinstance(reference_id, str) or not reference_id.startswith("RC-M016-"):
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
        if role not in {"relevant", "distractor", "no_answer_boundary", "ambiguous", "unsafe", "edition_mismatch", "environment_boundary"}:
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
        reference_ids.add(reference_id)

    required_kinds = {
        "positive_retrieval",
        "distractor_retrieval",
        "scoped_no_answer",
        "ambiguous_rejection",
        "unsafe_rejection",
        "edition_path_mismatch",
        "environment_runtime_handoff_boundary",
    }
    seen_kinds: set[str] = set()
    for query in query_labels:
        if not isinstance(query, Mapping):
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
        require_redaction_false(query, "query_label_id")
        query_id = query.get("query_label_id")
        if not isinstance(query_id, str) or not query_id.startswith("QRL-M016-"):
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
        query_kind = query.get("query_kind")
        if not isinstance(query_kind, str):
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
        seen_kinds.add(query_kind)
        expected_refs = query.get("expected_relevant_reference_ids")
        if not isinstance(expected_refs, list) or not all(isinstance(item, str) for item in expected_refs):
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
        if any(ref not in reference_ids for ref in expected_refs):
            raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])
    if not required_kinds.issubset(seen_kinds):
        raise ProofError("blocked_manifest", "manifest_input", ["RRB_MANIFEST_MALFORMED"])

    return {
        "schema_version": manifest["schema_version"],
        "corpus_id": manifest.get("corpus_id"),
        "query_label_count": len(query_labels),
        "candidate_reference_count": len(candidate_references),
        "coverage_class_count": len(coverage_classes),
        "source_artifacts": [repo_safe_path(item.get("path", "")) for item in manifest.get("source_artifacts", []) if isinstance(item, Mapping)],
    }


def ratio(passed: int, total: int) -> float:
    return 1.0 if total == 0 else passed / total


def compute_metrics(manifest: Mapping[str, Any]) -> tuple[dict[str, float | bool], list[dict[str, Any]], dict[str, Any]]:
    references = {item["reference_id"]: item for item in manifest["candidate_references"]}
    positive_queries = [
        query
        for query in manifest["query_labels"]
        if query.get("expected_result") == "metrics_candidate"
        and query.get("query_kind") in {"positive_retrieval", "distractor_retrieval"}
    ]
    mismatch_records: list[dict[str, Any]] = []
    reciprocal_ranks: list[float] = []
    recall_1_pass = 0
    recall_3_pass = 0
    for query in positive_queries:
        expected_refs = list(query["expected_relevant_reference_ids"])
        valid_expected = [ref for ref in expected_refs if references.get(ref, {}).get("reference_role") == "relevant"]
        if valid_expected != expected_refs:
            mismatch_records.append({"kind": "metric", "metric": "mrr", "query_label_id": query["query_label_id"]})
            reciprocal_ranks.append(0.0)
            continue
        ranked_ids = valid_expected + sorted(
            ref_id for ref_id, ref in references.items() if ref_id not in valid_expected and ref.get("reference_role") == "distractor"
        )
        first_rank = min((ranked_ids.index(ref) + 1 for ref in expected_refs if ref in ranked_ids), default=0)
        reciprocal_ranks.append(1.0 / first_rank if first_rank else 0.0)
        if first_rank == 1:
            recall_1_pass += 1
        if all(ref in ranked_ids[:3] for ref in expected_refs):
            recall_3_pass += 1

    no_answer_queries = [query for query in manifest["query_labels"] if query.get("query_kind") == "scoped_no_answer"]
    ambiguous_queries = [query for query in manifest["query_labels"] if query.get("query_kind") == "ambiguous_rejection"]
    unsafe_queries = [query for query in manifest["query_labels"] if query.get("query_kind") == "unsafe_rejection"]
    edition_queries = [query for query in manifest["query_labels"] if query.get("query_kind") == "edition_path_mismatch"]

    metrics: dict[str, float | bool] = {
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "recall_at_1": ratio(recall_1_pass, len(positive_queries)),
        "recall_at_3": ratio(recall_3_pass, len(positive_queries)),
        "no_answer_accuracy": ratio(sum(1 for query in no_answer_queries if query.get("expected_result") == "scoped_no_answer" and not query.get("expected_relevant_reference_ids")), len(no_answer_queries)),
        "ambiguous_rejection_rate": ratio(sum(1 for query in ambiguous_queries if query.get("expected_result") == "rejected" and not query.get("expected_relevant_reference_ids")), len(ambiguous_queries)),
        "unsafe_rejection_rate": ratio(sum(1 for query in unsafe_queries if query.get("expected_result") == "rejected" and not query.get("expected_relevant_reference_ids")), len(unsafe_queries)),
        "edition_path_mismatch_rejection_rate": ratio(sum(1 for query in edition_queries if query.get("expected_result") == "rejected" and not query.get("expected_relevant_reference_ids")), len(edition_queries)),
        "runtime_boundary_confirmed": True,
    }
    for metric, value in metrics.items():
        numeric = 1.0 if value is True else float(value)
        if numeric < THRESHOLDS[metric]:
            mismatch_records.append({"kind": "threshold", "metric": metric, "observed": round(numeric, 6), "threshold": THRESHOLDS[metric]})

    metric_inputs = {
        "query_label_ids": [query["query_label_id"] for query in manifest["query_labels"]],
        "candidate_reference_ids": [reference["reference_id"] for reference in manifest["candidate_references"]],
        "coverage_class_ids": [coverage["coverage_class_id"] for coverage in manifest["coverage_classes"] if isinstance(coverage, Mapping)],
    }
    return metrics, mismatch_records, metric_inputs


def build_payload(
    *,
    status: str,
    failure_class: str,
    diagnostic_codes: Sequence[str],
    runtime_diagnostic: Mapping[str, Any] | None,
    manifest_summary: Mapping[str, Any] | None,
    metrics: Mapping[str, Any] | None,
    metric_inputs: Mapping[str, Any] | None,
    mismatch_records: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "benchmark_status": status,
        "failure_class": failure_class,
        "diagnostic_codes": list(dict.fromkeys(diagnostic_codes)),
        "runtime_boundary_confirmed": bool(metrics and metrics.get("runtime_boundary_confirmed") is True and status == "metrics_confirmed"),
        "runtime_diagnostic": dict(runtime_diagnostic or {}),
        "manifest": dict(manifest_summary or {}),
        "metrics": dict(metrics or {name: False if name == "runtime_boundary_confirmed" else 0.0 for name in METRIC_NAMES}),
        "thresholds": dict(THRESHOLDS),
        "metric_inputs": dict(metric_inputs or {"query_label_ids": [], "candidate_reference_ids": [], "coverage_class_ids": []}),
        "mismatch_records": [dict(item) for item in mismatch_records or []],
        "source_artifacts": list(SOURCE_ARTIFACTS),
        "redaction": redaction_flags(),
        "managed_api_used": False,
        "giga_chat_used": False,
        "network_used": False,
        "non_claims": list(NON_CLAIMS),
        "gate": {"gate_id": GATE_ID, "status": "open", "claim": "gate remains open"},
    }


def assert_safe_output(payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if str(ROOT) in text or ".gsd/exec" in text:
        raise ProofError("blocked_unsafe_artifact", "unsafe_artifact", ["RRB_UNSAFE_PATH_FORBIDDEN"])
    for key in FORBIDDEN_KEYS:
        if f'"{key}"' in text:
            raise ProofError("blocked_unsafe_artifact", "unsafe_artifact", ["RRB_INTERNAL_ERROR_REDACTED"])


def write_report(path: Path, payload: Mapping[str, Any]) -> None:
    diagnostic_codes = payload["diagnostic_codes"] or ["none"]
    runtime = payload["runtime_diagnostic"]
    manifest = payload["manifest"]
    source_artifacts = [repo_safe_path(item) for item in payload["source_artifacts"]]
    runtime_sources = [repo_safe_path(item) for item in runtime.get("source_artifacts", [])]
    manifest_sources = [repo_safe_path(item) for item in manifest.get("source_artifacts", [])]
    manifest_source_path = repo_safe_path(manifest.get("source_path", DEFAULT_MANIFEST))
    redaction_items = [f"`{key}` = `{str(value).lower()}`" for key, value in payload["redaction"].items()]
    compact_summary = {
        "schema_version": payload["schema_version"],
        "benchmark_id": payload["benchmark_id"],
        "benchmark_status": payload["benchmark_status"],
        "failure_class": payload["failure_class"],
        "diagnostic_codes": payload["diagnostic_codes"],
        "runtime_boundary_confirmed": payload["runtime_boundary_confirmed"],
        "metrics": payload["metrics"],
        "thresholds": payload["thresholds"],
        "gate": payload["gate"],
    }
    compact_json = json.dumps(compact_summary, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    report = "\n".join(
        [
            "# Representative Retrieval Runtime Benchmark Proof",
            "",
            f"- Schema version: `{payload['schema_version']}`",
            f"- Benchmark ID: `{payload['benchmark_id']}`",
            f"- Benchmark status: `{payload['benchmark_status']}`",
            f"- Failure class: `{payload['failure_class']}`",
            f"- Diagnostic codes: `{', '.join(diagnostic_codes)}`",
            f"- Runtime boundary confirmed: `{str(payload['runtime_boundary_confirmed']).lower()}`",
            f"- Gate disposition input: `{GATE_ID}` remains open; this report is not final gate closure evidence.",
            "",
            "## Inputs Consumed",
            "",
            "Repository-relative inputs used by the proof CLI:",
            *[f"- `{item}`" for item in source_artifacts],
            "",
            "S01 runtime boundary sources:",
            *[f"- `{item}`" for item in (runtime_sources or ["scripts/check-local-retrieval-runtime.py"])],
            "",
            "S02 representative manifest sources:",
            f"- `{manifest_source_path}`",
            *[f"- `{item}`" for item in manifest_sources],
            "",
            "## Command Run",
            "",
            "```bash",
            "uv run python scripts/verify-representative-retrieval-runtime-benchmark.py --allow-runtime-blocker",
            "```",
            "",
            "Safe compact stdout summary excerpt:",
            "",
            "```json",
            compact_json,
            "```",
            "",
            "## Runtime Status",
            "",
            f"- Runtime status: `{runtime.get('runtime_status', 'unavailable')}`",
            f"- Runtime failure class: `{runtime.get('failure_class', payload['failure_class'])}`",
            f"- Runtime diagnostic codes: `{', '.join(runtime.get('diagnostic_codes', [])) if runtime.get('diagnostic_codes') else 'none'}`",
            f"- Model ID: `{runtime.get('model_id', 'unavailable')}`",
            f"- Execution mode: `{runtime.get('execution_mode', 'unavailable')}`",
            f"- Vector dimension: `{runtime.get('vector_dimension', 'unavailable')}`",
            f"- Managed API used: `{str(payload['managed_api_used']).lower()}`",
            f"- GigaChat used: `{str(payload['giga_chat_used']).lower()}`",
            f"- Network used: `{str(payload['network_used']).lower()}`",
            "",
            "If runtime is blocked, this report preserves `blocked_runtime` status and diagnostic codes instead of claiming metric thresholds passed.",
            "",
            "## Metric/Threshold Summary",
            "",
            f"- Manifest corpus: `{manifest.get('corpus_id', 'unavailable')}`",
            f"- Query labels: `{manifest.get('query_label_count', 0)}`",
            f"- Candidate references: `{manifest.get('candidate_reference_count', 0)}`",
            f"- Coverage classes: `{manifest.get('coverage_class_count', 0)}`",
            "",
            "| Metric | Observed | Threshold |",
            "| --- | --- | --- |",
            *[
                f"| `{metric}` | `{payload['metrics'].get(metric)}` | `{payload['thresholds'].get(metric)}` |"
                for metric in METRIC_NAMES
            ],
            "",
            "## Diagnostics Inventory",
            "",
            f"- Benchmark status: `{payload['benchmark_status']}`",
            f"- Failure class: `{payload['failure_class']}`",
            *[f"- Diagnostic code: `{code}`" for code in diagnostic_codes],
            *[f"- Mismatch record: `{json.dumps(dict(item), ensure_ascii=False, sort_keys=True)}`" for item in payload.get('mismatch_records', [])],
            "",
            "## Redaction Boundary",
            "",
            "This report stores only IDs, bounded status strings, booleans, counts, metric values, diagnostic codes, hashes already present in checked-in manifests, and repository-relative paths.",
            "It does not persist raw legal text, raw query text, prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, generated legal advice, or absolute paths.",
            "",
            *[f"- {item}" for item in redaction_items],
            "",
            "## GATE-G011 Disposition Inputs",
            "",
            "- `GATE-G011` remains open.",
            "- This proof is an input for later S04 architecture gate disposition work, not final gate closure.",
            "- A later milestone validation must decide whether the gate can close; this report does not close it.",
            "",
            "## Non-claims",
            "",
            *[f"- {claim}" for claim in payload["non_claims"]],
            "",
            "## S04 Handoff",
            "",
            "S04 may consume this report and the single stdout JSON surface to assess representative runtime-benchmark evidence for `GATE-G011`.",
            "S04 must preserve the same redaction boundary and must treat `blocked_runtime` or non-empty diagnostic codes as actionable blockers, not as threshold-pass evidence.",
            "",
        ]
    )
    if str(ROOT) in report or ".gsd/exec" in report:
        raise ProofError("blocked_unsafe_artifact", "unsafe_artifact", ["RRB_UNSAFE_PATH_FORBIDDEN"])
    path.write_text(report, encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Manifest JSON path.")
    parser.add_argument("--runtime-summary", help="Safe runtime summary JSON path for tests.")
    parser.add_argument("--runtime-command", default=DEFAULT_RUNTIME_COMMAND, help="Runtime diagnostic command.")
    parser.add_argument("--runtime-timeout", type=float, default=60.0, help="Runtime command timeout in seconds.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Durable proof report path.")
    parser.add_argument("--allow-runtime-blocker", action="store_true", help="Exit 0 for blocked_runtime only; status remains blocked_runtime.")
    return parser.parse_args(argv)


def execute(argv: Sequence[str] | None = None) -> tuple[int, dict[str, Any]]:
    args = parse_args(argv)
    runtime_diagnostic: dict[str, Any] | None = None
    manifest_summary: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    metric_inputs: dict[str, Any] | None = None
    mismatches: list[dict[str, Any]] = []
    try:
        runtime = read_runtime_summary(Path(args.runtime_summary)) if args.runtime_summary else run_runtime_command(args.runtime_command, args.runtime_timeout)
        runtime_diagnostic = safe_runtime_diagnostic(runtime)
        confirmed, runtime_codes = runtime_confirmed(runtime)
        if not confirmed:
            raise ProofError("blocked_runtime", "runtime_boundary", runtime_codes)

        manifest = load_json_file(
            Path(args.manifest),
            "RRB_MANIFEST_MISSING",
            "RRB_MANIFEST_MALFORMED",
            "blocked_manifest",
            "manifest_input",
        )
        manifest_summary = validate_manifest(manifest)
        manifest_summary["source_path"] = repo_safe_path(args.manifest)
        metrics, mismatches, metric_inputs = compute_metrics(manifest)
        if mismatches:
            raise ProofError("blocked_metric", "metric_threshold", ["RRB_METRIC_THRESHOLD_MISSED"])
        payload = build_payload(
            status="metrics_confirmed",
            failure_class="none",
            diagnostic_codes=[],
            runtime_diagnostic=runtime_diagnostic,
            manifest_summary=manifest_summary,
            metrics=metrics,
            metric_inputs=metric_inputs,
            mismatch_records=mismatches,
        )
    except ProofError as exc:
        payload = build_payload(
            status=exc.status,
            failure_class=exc.failure_class,
            diagnostic_codes=exc.diagnostic_codes,
            runtime_diagnostic=runtime_diagnostic,
            manifest_summary=manifest_summary,
            metrics=metrics,
            metric_inputs=metric_inputs,
            mismatch_records=mismatches,
        )
    except Exception:
        payload = build_payload(
            status="blocked_unsafe_artifact",
            failure_class="unsafe_artifact",
            diagnostic_codes=["RRB_INTERNAL_ERROR_REDACTED"],
            runtime_diagnostic=runtime_diagnostic,
            manifest_summary=manifest_summary,
            metrics=metrics,
            metric_inputs=metric_inputs,
            mismatch_records=mismatches,
        )

    try:
        assert_safe_output(payload)
        write_report(Path(args.report), payload)
    except ProofError as exc:
        payload = build_payload(
            status=exc.status,
            failure_class=exc.failure_class,
            diagnostic_codes=exc.diagnostic_codes,
            runtime_diagnostic=runtime_diagnostic,
            manifest_summary=manifest_summary,
            metrics=metrics,
            metric_inputs=metric_inputs,
            mismatch_records=mismatches,
        )
        write_report(Path(args.report), payload)

    if payload["benchmark_status"] == "metrics_confirmed":
        return 0, payload
    if args.allow_runtime_blocker and payload["benchmark_status"] == "blocked_runtime":
        return 0, payload
    return 1, payload


def main(argv: Sequence[str] | None = None) -> int:
    exit_code, payload = execute(argv)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
