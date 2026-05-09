#!/usr/bin/env python3
"""Verify and finalize M001/S09 local embedding recommendation artifacts.

The verifier is deliberately conservative: it accepts blocked local runtimes only
when diagnostics, owners, raw logs, and resolution criteria are explicit. It writes
a bounded downstream recommendation that distinguishes practical baseline,
quality challenger, environment blockers, and deferred real-document proof without
claiming production Russian legal retrieval quality from synthetic fixtures.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / ".gsd/milestones/M001/slices/S09"
DEFAULT_CONTRACT = DEFAULT_OUTPUT_DIR / "S09-LOCAL-EMBEDDING-EVALUATION.json"
DEFAULT_MARKDOWN = DEFAULT_OUTPUT_DIR / "S09-LOCAL-EMBEDDING-EVALUATION.md"
DEFAULT_SMOKE = DEFAULT_OUTPUT_DIR / "S09-LOCAL-EMBEDDING-SMOKE.json"
DEFAULT_RETRIEVAL = DEFAULT_OUTPUT_DIR / "S09-LOCAL-EMBEDDING-RETRIEVAL-EVAL.json"

PRIMARY_MODEL_IDS = {
    "ai-sage/Giga-Embeddings-instruct",
    "deepvk/USER-bge-m3",
}
OPTIONAL_MODEL_IDS = {"BAAI/bge-m3"}
ALLOWED_MODEL_IDS = PRIMARY_MODEL_IDS | OPTIONAL_MODEL_IDS
REQUIRED_PER_MODEL_FIELDS = (
    "package_status",
    "cache_status",
    "download_status",
    "runtime_status",
    "vector_dimension",
    "max_token_limit",
    "encode_duration_ms",
    "resource_metadata",
    "falkordb_vector_compatibility",
    "benchmark_result_status",
    "blocked_root_cause",
    "raw_log_paths",
)
FORBIDDEN_SECRET_TERMS = ("GIGACHAT" + "_AUTH_DATA", "Bearer ", "sk-", "api_key")
FINAL_SECTION_START = "<!-- S09-final-recommendation:start -->"
FINAL_SECTION_END = "<!-- S09-final-recommendation:end -->"

TerminalStatus = Literal[
    "confirmed-runtime",
    "blocked-environment",
    "failed-runtime",
    "bounded-not-product-proven",
]
TERMINAL_RUNTIME_STATUSES: frozenset[str] = frozenset(
    {"confirmed-runtime", "blocked-environment", "failed-runtime", "bounded-not-product-proven"}
)


@dataclass
class VerificationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def read_json(path: Path, result: VerificationResult, label: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        result.add(f"{label} missing: {path}")
        return None
    except json.JSONDecodeError as exc:
        result.add(f"{label} invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return None
    if not isinstance(parsed, dict):
        result.add(f"{label} root must be an object: {path}")
        return None
    return cast("dict[str, Any]", parsed)


def read_text(path: Path, result: VerificationResult, label: str) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        result.add(f"{label} missing: {path}")
        return None


def check_forbidden_terms(text: str, result: VerificationResult, label: str) -> None:
    for term in FORBIDDEN_SECRET_TERMS:
        if term in text:
            result.add(f"{label} contains forbidden secret/API term: {term}")


def as_candidate_map(contract: dict[str, Any], result: VerificationResult) -> dict[str, dict[str, Any]]:
    candidates = contract.get("candidates")
    if not isinstance(candidates, list):
        result.add("Contract must contain candidates list")
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            result.add(f"Contract candidates[{index}] must be an object")
            continue
        candidate_map = cast("dict[str, Any]", candidate)
        model_id = candidate_map.get("id")
        if not isinstance(model_id, str) or not model_id:
            result.add(f"Contract candidates[{index}] missing non-empty id")
            continue
        if model_id not in ALLOWED_MODEL_IDS:
            continue
        mapped[model_id] = candidate_map
    missing = PRIMARY_MODEL_IDS - set(mapped)
    for model_id in sorted(missing):
        result.add(f"Contract missing required primary candidate: {model_id}")
    return mapped


def validate_contract(contract: dict[str, Any], result: VerificationResult) -> dict[str, dict[str, Any]]:
    policy = contract.get("policy")
    if not isinstance(policy, dict):
        result.add("Contract missing policy object")
    else:
        if policy.get("managed_gigachat_api") != "excluded":
            result.add("Contract policy.managed_gigachat_api must be excluded")
        if policy.get("external_embedding_api_dependency") != "excluded":
            result.add("Contract policy.external_embedding_api_dependency must be excluded")
        if policy.get("local_open_weight_models_only") is not True:
            result.add("Contract policy.local_open_weight_models_only must be true")

    mapped = as_candidate_map(contract, result)
    for model_id, candidate in mapped.items():
        for field_name in ("owner", "resolution_path", "verification_criteria", "roadmap_impact"):
            value = candidate.get(field_name)
            if not isinstance(value, str) or not value.strip():
                result.add(f"Candidate {model_id} missing non-empty {field_name}")
        dimension = candidate.get("vector_dimension")
        if model_id == "deepvk/USER-bge-m3" and dimension != 1024:
            result.add("deepvk/USER-bge-m3 must remain a 1024-dimensional candidate")
        if model_id == "ai-sage/Giga-Embeddings-instruct" and dimension != 2048:
            result.add("ai-sage/Giga-Embeddings-instruct must remain a 2048-dimensional candidate")
        if not candidate.get("max_token_limit"):
            result.add(f"Candidate {model_id} missing max_token_limit")
    return mapped


def raw_log_exists(path_value: object, result: VerificationResult, label: str, artifact_root: Path) -> None:
    if not isinstance(path_value, str) or not path_value:
        result.add(f"{label} raw log path must be a non-empty string")
        return
    raw_path = Path(path_value)
    if raw_path.is_absolute():
        candidates = [raw_path]
    else:
        candidates = [ROOT / raw_path, artifact_root / raw_path]
    if not any(path.is_file() for path in candidates):
        result.add(f"{label} raw log path does not exist: {path_value}")


def validate_model_result(model: dict[str, Any], result: VerificationResult, source: str, artifact_root: Path) -> None:
    model_id = model.get("id")
    if not isinstance(model_id, str) or model_id not in ALLOWED_MODEL_IDS:
        result.add(f"{source} model has unexpected id: {model_id!r}")
        return
    for field_name in REQUIRED_PER_MODEL_FIELDS:
        if field_name not in model:
            result.add(f"{source} model {model_id} missing required field: {field_name}")
    runtime_status = model.get("runtime_status")
    if runtime_status not in TERMINAL_RUNTIME_STATUSES:
        result.add(f"{source} model {model_id} has non-terminal runtime_status: {runtime_status!r}")
    benchmark_status = model.get("benchmark_result_status")
    if not isinstance(benchmark_status, str) or not benchmark_status:
        result.add(f"{source} model {model_id} missing benchmark_result_status")
    root_cause = model.get("blocked_root_cause")
    if runtime_status != "confirmed-runtime" and (not isinstance(root_cause, str) or not root_cause):
        result.add(f"{source} model {model_id} must include blocked_root_cause when not confirmed-runtime")
    raw_logs = model.get("raw_log_paths")
    if not isinstance(raw_logs, list) or not raw_logs:
        result.add(f"{source} model {model_id} must include non-empty raw_log_paths")
    else:
        for raw_log in raw_logs:
            raw_log_exists(raw_log, result, f"{source} model {model_id}", artifact_root)
    vector = model.get("falkordb_vector_compatibility")
    if not isinstance(vector, dict):
        result.add(f"{source} model {model_id} missing falkordb_vector_compatibility object")
    else:
        if vector.get("dimension") != model.get("vector_dimension"):
            result.add(f"{source} model {model_id} vector compatibility dimension mismatch")
        vector_status = vector.get("status")
        if not isinstance(vector_status, str) or not vector_status:
            result.add(f"{source} model {model_id} vector compatibility missing status")
        vector_logs = vector.get("raw_log_paths")
        if isinstance(vector_logs, list):
            for raw_log in vector_logs:
                raw_log_exists(raw_log, result, f"{source} model {model_id} vector", artifact_root)


def validate_results_artifact(payload: dict[str, Any], result: VerificationResult, source: str, artifact_root: Path) -> dict[str, dict[str, Any]]:
    if payload.get("managed_apis_contacted") is not False:
        result.add(f"{source} must record managed_apis_contacted=false")
    if payload.get("synthetic_fixtures_only") is not True:
        result.add(f"{source} must record synthetic_fixtures_only=true")
    if payload.get("download_mode") not in {"no-download", "allow-download"}:
        result.add(f"{source} has unsupported download_mode: {payload.get('download_mode')!r}")
    models = payload.get("models")
    if not isinstance(models, list):
        result.add(f"{source} missing models list")
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for index, model in enumerate(models):
        if not isinstance(model, dict):
            result.add(f"{source} models[{index}] must be object")
            continue
        model_map = cast("dict[str, Any]", model)
        validate_model_result(model_map, result, source, artifact_root)
        model_id = model_map.get("id")
        if isinstance(model_id, str):
            mapped[model_id] = model_map
    for model_id in sorted(PRIMARY_MODEL_IDS):
        if model_id not in mapped:
            result.add(f"{source} missing primary model result: {model_id}")
    return mapped


def validate_vector_probe_dimensions(retrieval_payload: dict[str, Any], result: VerificationResult, artifact_root: Path) -> None:
    probes = retrieval_payload.get("falkordb_vector_probes")
    if not isinstance(probes, list):
        result.add("Retrieval artifact missing falkordb_vector_probes list")
        return
    dimensions = {probe.get("dimension") for probe in probes if isinstance(probe, dict)}
    if {1024, 2048} - dimensions:
        result.add("Retrieval artifact must include FalkorDB vector probes for 1024 and 2048 dimensions")
    for probe in probes:
        if not isinstance(probe, dict):
            result.add("Retrieval vector probe must be an object")
            continue
        if not probe.get("status"):
            result.add(f"Vector probe {probe.get('dimension')} missing status")
        if probe.get("status") != "confirmed-runtime" and not probe.get("blocked_root_cause"):
            result.add(f"Vector probe {probe.get('dimension')} must include blocked_root_cause unless confirmed")
        for raw_log in probe.get("raw_log_paths", []) if isinstance(probe.get("raw_log_paths"), list) else []:
            raw_log_exists(raw_log, result, f"vector probe {probe.get('dimension')}", artifact_root)


def model_classification(model_id: str, runtime_status: str, blocked_root_cause: str | None) -> str:
    if model_id == "deepvk/USER-bge-m3":
        return "recommended-practical-baseline-blocked" if runtime_status != "confirmed-runtime" else "recommended-practical-baseline-runtime-confirmed"
    if model_id == "ai-sage/Giga-Embeddings-instruct":
        return "quality-challenger-blocked" if runtime_status != "confirmed-runtime" else "quality-challenger-runtime-confirmed"
    if blocked_root_cause:
        return "optional-reference-blocked"
    return "optional-reference"


def merge_model_evidence(
    contract_candidates: dict[str, dict[str, Any]],
    smoke_models: dict[str, dict[str, Any]],
    retrieval_models: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for model_id in sorted(contract_candidates):
        candidate = contract_candidates[model_id]
        retrieval = retrieval_models.get(model_id, {})
        smoke = smoke_models.get(model_id, {})
        runtime_status = str(retrieval.get("runtime_status") or smoke.get("runtime_status") or candidate.get("runtime_status") or "bounded-not-product-proven")
        blocked_root_cause = retrieval.get("blocked_root_cause") or smoke.get("blocked_root_cause") or candidate.get("blocked_root_cause")
        classification = model_classification(model_id, runtime_status, blocked_root_cause if isinstance(blocked_root_cause, str) else None)
        recommendations.append(
            {
                "id": model_id,
                "role": candidate.get("role"),
                "classification": classification,
                "license": candidate.get("license"),
                "vector_dimension": candidate.get("vector_dimension"),
                "max_token_limit": candidate.get("max_token_limit"),
                "runtime_status": runtime_status,
                "benchmark_result_status": retrieval.get("benchmark_result_status") or smoke.get("benchmark_result_status") or candidate.get("benchmark_result_status"),
                "encode_duration_ms": retrieval.get("encode_duration_ms") or smoke.get("encode_duration_ms"),
                "blocked_root_cause": blocked_root_cause,
                "falkordb_vector_compatibility": retrieval.get("falkordb_vector_compatibility") or smoke.get("falkordb_vector_compatibility") or candidate.get("falkordb_vector_compatibility"),
                "raw_log_paths": retrieval.get("raw_log_paths") or smoke.get("raw_log_paths") or [],
                "recommendation": recommendation_text(model_id, runtime_status),
                "required_next_proof": required_next_proof(model_id, runtime_status),
                "roadmap_impact": candidate.get("roadmap_impact"),
                "owner": candidate.get("owner"),
                "resolution_path": candidate.get("resolution_path"),
                "verification_criteria": candidate.get("verification_criteria"),
            }
        )
    return recommendations


def recommendation_text(model_id: str, runtime_status: str) -> str:
    if model_id == "deepvk/USER-bge-m3":
        return "Use as the default practical local baseline only after runtime dependencies/cache are available; current bounded recommendation prefers it on integration risk, not proven legal quality."
    if model_id == "ai-sage/Giga-Embeddings-instruct":
        return "Keep as quality-first challenger; do not default to it until custom-code, flash-attn/GPU posture, 2048-dim storage, and retrieval metrics are proven locally."
    return "Keep as optional upstream reference; do not displace the two primary S09 candidates without a separate runtime budget."


def required_next_proof(model_id: str, runtime_status: str) -> list[str]:
    common = [
        "Run cached or explicit-download local encode without managed APIs.",
        "Evaluate against parser-produced EvidenceSpan/SourceBlock real-document fixtures after S05 parser proof is consumed.",
    ]
    if runtime_status != "confirmed-runtime":
        common.insert(0, "Install optional local embedding dependencies and populate Hugging Face cache or explicitly allow open-weight downloads.")
    if model_id == "ai-sage/Giga-Embeddings-instruct":
        common.append("Verify trust_remote_code boundary, flash-attn/GPU fallback, and 2048-dimensional FalkorDB storage cost.")
    elif model_id == "deepvk/USER-bge-m3":
        common.append("Verify 1024-dimensional FalkorDB storage/query behavior and CPU feasibility for repeated legal retrieval batches.")
    return common


def build_final_recommendation(
    contract_candidates: dict[str, dict[str, Any]],
    smoke_models: dict[str, dict[str, Any]],
    retrieval_models: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidates = merge_model_evidence(contract_candidates, smoke_models, retrieval_models)
    any_confirmed = any(candidate["runtime_status"] == "confirmed-runtime" for candidate in candidates)
    return {
        "status": "bounded-recommendation-runtime-confirmed" if any_confirmed else "bounded-recommendation-blocked-environment",
        "generated_at": utc_now(),
        "selected_practical_baseline": "deepvk/USER-bge-m3",
        "quality_challenger": "ai-sage/Giga-Embeddings-instruct",
        "optional_reference": "BAAI/bge-m3",
        "managed_embedding_apis": "excluded",
        "legal_quality_claim": "not-proven; synthetic fixtures are mechanics-only and cannot prove production Russian legal retrieval quality",
        "falkordb_storage_claim": "bounded by dimension-specific preflight/logs; live 1024/2048 index/query remains blocked unless runtime packages are available",
        "confidence_loop": {
            "question": "Ты на 100% уверен в этой стратегии?",
            "answer": "Уверен только в bounded recommendation and no-overclaim strategy; не уверен в runtime quality/storage until dependencies, cache, and live FalkorDB runtime are available.",
            "holes_found": [
                "Embedding packages/model caches are absent, so encode metrics are blocked.",
                "FalkorDB client/runtime packages are absent, so 1024/2048 live vector index/query is blocked.",
                "Synthetic fixtures do not prove real Russian legal retrieval quality.",
                "GigaEmbeddings custom-code/trust_remote_code and flash-attn/GPU posture remain unproven locally.",
            ],
            "fixes_or_next_proofs": [
                "Close S09 with bounded recommendation only, not runtime quality claim.",
                "Create/follow a later heavy-runtime proof path with optional dependencies, cached/open-weight downloads, and live FalkorDB.",
                "Use S05 parser output to build real EvidenceSpan/SourceBlock retrieval fixtures before product claims.",
            ],
        },
        "candidates": candidates,
        "downstream_guidance": [
            "S06/S07/S08 may cite USER-bge-m3 as the practical baseline candidate by integration posture only.",
            "Do not claim LegalGraph Nexus legal retrieval quality until real-document evaluation exists.",
            "Do not introduce GigaChat/GigaChat managed embedding API or managed embedding credential environment variables.",
            "Treat GigaEmbeddings as challenger until local runtime and storage costs are proven.",
        ],
    }


def render_markdown_recommendation(recommendation: dict[str, Any]) -> str:
    rows = []
    for candidate in recommendation["candidates"]:
        rows.append(
            "| `{id}` | {classification} | {runtime} | {dim} | {benchmark} | `{blocked}` | {recommendation} |".format(
                id=candidate["id"],
                classification=candidate["classification"],
                runtime=candidate["runtime_status"],
                dim=candidate["vector_dimension"],
                benchmark=candidate["benchmark_result_status"],
                blocked=candidate["blocked_root_cause"],
                recommendation=candidate["recommendation"],
            )
        )
    holes = "\n".join(f"- {item}" for item in recommendation["confidence_loop"]["holes_found"])
    fixes = "\n".join(f"- {item}" for item in recommendation["confidence_loop"]["fixes_or_next_proofs"])
    downstream = "\n".join(f"- {item}" for item in recommendation["downstream_guidance"])
    return "\n".join(
        [
            FINAL_SECTION_START,
            "",
            "## Final bounded recommendation for downstream slices",
            "",
            f"Status: `{recommendation['status']}`.",
            "",
            "| Candidate | Classification | Runtime | Dim | Benchmark | Blocked root cause | Recommendation |",
            "|---|---|---|---:|---|---|---|",
            *rows,
            "",
            "### Bounded claims",
            "",
            f"- Practical baseline: `{recommendation['selected_practical_baseline']}`.",
            f"- Quality challenger: `{recommendation['quality_challenger']}`.",
            f"- Managed embedding APIs: `{recommendation['managed_embedding_apis']}`.",
            f"- Legal quality claim: {recommendation['legal_quality_claim']}.",
            f"- FalkorDB storage claim: {recommendation['falkordb_storage_claim']}.",
            "",
            "### Confidence loop",
            "",
            f"Question: {recommendation['confidence_loop']['question']}",
            "",
            f"Answer: {recommendation['confidence_loop']['answer']}",
            "",
            "Holes found:",
            "",
            holes,
            "",
            "Fixes / next proofs:",
            "",
            fixes,
            "",
            "### Downstream guidance",
            "",
            downstream,
            "",
            FINAL_SECTION_END,
            "",
        ]
    )


def upsert_markdown_section(markdown: str, section: str) -> str:
    start = markdown.find(FINAL_SECTION_START)
    end = markdown.find(FINAL_SECTION_END)
    if start != -1 and end != -1 and end > start:
        return markdown[:start].rstrip() + "\n\n" + section.rstrip() + "\n" + markdown[end + len(FINAL_SECTION_END) :].lstrip()
    return markdown.rstrip() + "\n\n" + section.rstrip() + "\n"


def write_final_recommendation(contract_path: Path, markdown_path: Path, recommendation: dict[str, Any], result: VerificationResult) -> None:
    contract = read_json(contract_path, result, "Contract JSON")
    markdown = read_text(markdown_path, result, "Contract markdown")
    if contract is None or markdown is None:
        return
    contract["final_recommendation"] = recommendation
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_section = render_markdown_recommendation(recommendation)
    markdown_path.write_text(upsert_markdown_section(markdown, markdown_section), encoding="utf-8")


def verify(
    *,
    contract_path: Path,
    markdown_path: Path,
    smoke_path: Path,
    retrieval_path: Path,
    require_results: bool,
    write_recommendation: bool,
) -> VerificationResult:
    result = VerificationResult()
    contract = read_json(contract_path, result, "Contract JSON")
    markdown = read_text(markdown_path, result, "Contract markdown")
    smoke = read_json(smoke_path, result, "Smoke JSON") if require_results else None
    retrieval = read_json(retrieval_path, result, "Retrieval JSON") if require_results else None

    if markdown is not None:
        check_forbidden_terms(markdown, result, "Contract markdown")
    if contract_path.is_file():
        check_forbidden_terms(contract_path.read_text(encoding="utf-8"), result, "Contract JSON")
    if retrieval_path.is_file():
        check_forbidden_terms(retrieval_path.read_text(encoding="utf-8"), result, "Retrieval JSON")
    if smoke_path.is_file():
        check_forbidden_terms(smoke_path.read_text(encoding="utf-8"), result, "Smoke JSON")

    contract_candidates: dict[str, dict[str, Any]] = {}
    if contract is not None:
        contract_candidates = validate_contract(contract, result)

    smoke_models: dict[str, dict[str, Any]] = {}
    retrieval_models: dict[str, dict[str, Any]] = {}
    if require_results:
        if smoke is not None:
            smoke_models = validate_results_artifact(smoke, result, "Smoke artifact", contract_path.parent)
        if retrieval is not None:
            retrieval_models = validate_results_artifact(retrieval, result, "Retrieval artifact", contract_path.parent)
            validate_vector_probe_dimensions(retrieval, result, contract_path.parent)

    if result.ok and require_results:
        recommendation = build_final_recommendation(contract_candidates, smoke_models, retrieval_models)
        if write_recommendation:
            write_final_recommendation(contract_path, markdown_path, recommendation, result)

    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--smoke", type=Path, default=DEFAULT_SMOKE)
    parser.add_argument("--retrieval", type=Path, default=DEFAULT_RETRIEVAL)
    parser.add_argument("--require-results", action="store_true", help="Require smoke/evaluation result artifacts and write final bounded recommendation.")
    parser.add_argument("--check-only", action="store_true", help="Validate without updating final recommendation fields.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify(
        contract_path=args.contract,
        markdown_path=args.markdown,
        smoke_path=args.smoke,
        retrieval_path=args.retrieval,
        require_results=bool(args.require_results),
        write_recommendation=bool(args.require_results and not args.check_only),
    )
    if not result.ok:
        print("S09 local embedding verification failed:", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("S09 local embedding verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
