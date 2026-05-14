#!/usr/bin/env python3
"""Check the approved local/open-weight retrieval runtime boundary.

The command emits one compact JSON object to stdout. It never fetches models,
never calls managed APIs, and exits successfully only when the approved local
runtime is confirmed unless --allow-unavailable is supplied for smoke checks.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd/retrieval/local_retrieval_runtime_boundary_contract.md"
S10_PROOF_PATH = ROOT / ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json"
SCHEMA_VERSION = "local-retrieval-runtime-boundary/v1"
MODEL_ID = "deepvk/USER-bge-m3"
EXECUTION_MODE = "local_open_weight"
EXPECTED_VECTOR_DIMENSION = 1024
REQUIRED_PACKAGES = ("sentence-transformers", "transformers", "torch")
PACKAGE_IMPORTS = {
    "sentence-transformers": "sentence_transformers",
    "transformers": "transformers",
    "torch": "torch",
}
SOURCE_ARTIFACTS = (
    "prd/retrieval/local_retrieval_runtime_boundary_contract.md",
    ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
    "pyproject.toml",
)
NON_CLAIMS = (
    "does_not_prove_product_retrieval_quality",
    "does_not_prove_representative_corpus_quality",
    "does_not_prove_parser_completeness",
    "does_not_prove_legal_answer_correctness",
    "does_not_prove_legal_interpretation_authority",
    "does_not_prove_production_falkordb_runtime_behavior",
    "does_not_close_GATE_G011",
    "does_not_authorize_managed_embedding_api_fallback",
    "does_not_authorize_gigachat_or_gigaembeddings_runtime_use",
)
RUNTIME_STATUSES = {
    "confirmed_runtime",
    "blocked_environment",
    "blocked_model_unavailable",
    "blocked_dimension_mismatch",
    "blocked_policy_violation",
    "blocked_unsafe_artifact",
    "not_run_contract_only",
}
FAILURE_CLASSES = {
    "none",
    "environment",
    "model_unavailable",
    "dimension_mismatch",
    "policy_violation",
    "unsafe_artifact",
    "internal_error",
}
FORBIDDEN_OUTPUT_FRAGMENTS = (
    "GIGACHAT" + "_AUTH_DATA",
    "Bearer ",
    "sk-",
    "api_key",
    "api-key",
    "authorization",
    "\"embedding\":[",
    "/root/",
    "/tmp/",
    "\\u005b0.0,",
)


class RuntimeCheckError(RuntimeError):
    """Raised when an injected runtime probe cannot safely complete."""


def redaction_flags() -> dict[str, bool]:
    return {
        "raw_legal_text_excluded": True,
        "raw_query_text_excluded": True,
        "raw_vectors_excluded": True,
        "provider_payloads_excluded": True,
        "secrets_excluded": True,
        "absolute_paths_excluded": True,
        "legal_advice_excluded": True,
    }


def base_payload() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "model_id": MODEL_ID,
        "execution_mode": EXECUTION_MODE,
        "runtime_status": "not_run_contract_only",
        "failure_class": "environment",
        "diagnostic_codes": ["LRR_NOT_RUN_CONTRACT_ONLY"],
        "dependency_versions": {},
        "source_artifacts": list(SOURCE_ARTIFACTS),
        "redaction": redaction_flags(),
        "managed_api_used": False,
        "giga_chat_used": False,
        "network_used": False,
        "raw_vectors_persisted": False,
        "raw_legal_text_persisted": False,
        "provider_payload_persisted": False,
        "expected_vector_dimension": EXPECTED_VECTOR_DIMENSION,
        "non_claims": list(NON_CLAIMS),
    }


def package_import_name(package: str) -> str:
    return PACKAGE_IMPORTS.get(package, package.replace("-", "_"))


def probe_dependency_versions(packages: Sequence[str] = REQUIRED_PACKAGES) -> tuple[dict[str, str], list[str]]:
    versions: dict[str, str] = {}
    missing: list[str] = []
    for package in packages:
        import_name = package_import_name(package)
        if importlib.util.find_spec(import_name) is None:
            missing.append(package)
            continue
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "unknown"
    return versions, missing


def huggingface_cache_roots(env: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    active_env = env or os.environ
    roots: list[Path] = []
    if hub_cache := active_env.get("HUGGINGFACE_HUB_CACHE"):
        roots.append(Path(hub_cache))
    if hf_home := active_env.get("HF_HOME"):
        roots.append(Path(hf_home) / "hub")
    if transformers_cache := active_env.get("TRANSFORMERS_CACHE"):
        roots.append(Path(transformers_cache))
    roots.append(Path.home() / ".cache/huggingface/hub")
    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        expanded = root.expanduser()
        if expanded not in seen:
            seen.add(expanded)
            unique.append(expanded)
    return tuple(unique)


def model_cache_present(model_id: str = MODEL_ID, roots: Sequence[Path] | None = None) -> bool:
    cache_roots = tuple(roots) if roots is not None else huggingface_cache_roots()
    cache_name = "models--" + model_id.replace("/", "--")
    for root in cache_roots:
        snapshots = root / cache_name / "snapshots"
        if snapshots.is_dir() and any(path.is_dir() for path in snapshots.iterdir()):
            return True
    return False


def load_s10_metadata(path: Path = S10_PROOF_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeCheckError("S10 metadata is unavailable")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeCheckError("S10 metadata is malformed") from exc
    if not isinstance(payload, dict):
        raise RuntimeCheckError("S10 metadata root is malformed")
    models = payload.get("models")
    if not isinstance(models, list):
        raise RuntimeCheckError("S10 metadata models are malformed")
    for model in models:
        if isinstance(model, dict) and model.get("id") == MODEL_ID:
            dimension = model.get("observed_vector_dimension") or model.get("vector_dimension")
            if dimension != EXPECTED_VECTOR_DIMENSION:
                raise RuntimeCheckError("S10 metadata dimension does not match boundary")
            return dict(model)
    raise RuntimeCheckError("S10 metadata does not contain approved model")


def encode_dimension(model_id: str = MODEL_ID) -> int:
    sentence_transformers = __import__("sentence_transformers", fromlist=["SentenceTransformer"])
    sentence_transformer = sentence_transformers.SentenceTransformer
    model = sentence_transformer(model_id, local_files_only=True)
    vector = model.encode(["local runtime dimension sentinel"], convert_to_numpy=False)[0]
    return len(vector)


def fail_payload(
    *,
    status: str,
    failure_class: str,
    diagnostic_codes: Sequence[str],
    dependency_versions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    payload = base_payload()
    payload["runtime_status"] = status
    payload["failure_class"] = failure_class
    payload["diagnostic_codes"] = list(diagnostic_codes)
    if dependency_versions is not None:
        payload["dependency_versions"] = dict(sorted(dependency_versions.items()))
    return payload


def confirmed_payload(dependency_versions: Mapping[str, str], vector_dimension: int) -> dict[str, Any]:
    payload = base_payload()
    payload.update(
        {
            "runtime_status": "confirmed_runtime",
            "failure_class": "none",
            "diagnostic_codes": [],
            "dependency_versions": dict(sorted(dependency_versions.items())),
            "vector_dimension": vector_dimension,
        }
    )
    return payload


def policy_violation_codes(env: Mapping[str, str] | None = None) -> list[str]:
    active_env = env or os.environ
    codes: list[str] = []
    if "GIGACHAT_AUTH_DATA" in active_env:
        codes.append("LRR_MANAGED_API_FORBIDDEN")
    return codes


def validate_payload(payload: Mapping[str, Any]) -> None:
    status = payload.get("runtime_status")
    failure_class = payload.get("failure_class")
    if status not in RUNTIME_STATUSES:
        raise RuntimeCheckError("invalid runtime_status")
    if failure_class not in FAILURE_CLASSES:
        raise RuntimeCheckError("invalid failure_class")
    if payload.get("model_id") != MODEL_ID:
        raise RuntimeCheckError("invalid model_id")
    if payload.get("managed_api_used") is not False or payload.get("giga_chat_used") is not False:
        raise RuntimeCheckError("managed API flags must be false")
    if payload.get("network_used") is not False:
        raise RuntimeCheckError("network_used must be false")
    redaction = payload.get("redaction")
    if not isinstance(redaction, dict) or not all(value is True for value in redaction.values()):
        raise RuntimeCheckError("redaction flags must all be true")
    if status == "confirmed_runtime" and payload.get("vector_dimension") != EXPECTED_VECTOR_DIMENSION:
        raise RuntimeCheckError("confirmed runtime requires expected vector dimension")
    if status != "confirmed_runtime" and not payload.get("diagnostic_codes"):
        raise RuntimeCheckError("fail-closed status requires diagnostic codes")
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    lowered = text.lower()
    for fragment in FORBIDDEN_OUTPUT_FRAGMENTS:
        if fragment.lower() in lowered:
            raise RuntimeCheckError("unsafe output fragment detected")


def build_runtime_report(*, run_inference: bool = True) -> dict[str, Any]:
    policy_codes = policy_violation_codes()
    if policy_codes:
        return fail_payload(
            status="blocked_policy_violation",
            failure_class="policy_violation",
            diagnostic_codes=policy_codes,
        )

    dependency_versions, missing = probe_dependency_versions()
    if missing:
        return fail_payload(
            status="blocked_environment",
            failure_class="environment",
            diagnostic_codes=["LRR_DEPENDENCY_MISSING"],
            dependency_versions=dependency_versions,
        )

    try:
        load_s10_metadata()
    except RuntimeCheckError:
        return fail_payload(
            status="blocked_environment",
            failure_class="environment",
            diagnostic_codes=["LRR_S10_METADATA_MALFORMED"],
            dependency_versions=dependency_versions,
        )

    if not model_cache_present():
        return fail_payload(
            status="blocked_model_unavailable",
            failure_class="model_unavailable",
            diagnostic_codes=["LRR_MODEL_CACHE_MISSING"],
            dependency_versions=dependency_versions,
        )

    if not run_inference:
        return fail_payload(
            status="not_run_contract_only",
            failure_class="environment",
            diagnostic_codes=["LRR_NOT_RUN_CONTRACT_ONLY"],
            dependency_versions=dependency_versions,
        )

    try:
        dimension = encode_dimension()
    except Exception:
        return fail_payload(
            status="blocked_environment",
            failure_class="environment",
            diagnostic_codes=["LRR_LOCAL_INFERENCE_FAILED_REDACTED"],
            dependency_versions=dependency_versions,
        )

    if dimension != EXPECTED_VECTOR_DIMENSION:
        payload = fail_payload(
            status="blocked_dimension_mismatch",
            failure_class="dimension_mismatch",
            diagnostic_codes=["LRR_DIMENSION_MISMATCH"],
            dependency_versions=dependency_versions,
        )
        payload["vector_dimension"] = dimension
        return payload

    return confirmed_payload(dependency_versions, dimension)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-unavailable",
        action="store_true",
        help="Return exit 0 for fail-closed unavailable-runtime diagnostics.",
    )
    parser.add_argument(
        "--no-inference",
        action="store_true",
        help="Validate preconditions only and emit a fail-closed not_run_contract_only diagnostic.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = build_runtime_report(run_inference=not args.no_inference)
        validate_payload(payload)
    except Exception:
        payload = fail_payload(
            status="blocked_unsafe_artifact",
            failure_class="unsafe_artifact",
            diagnostic_codes=["LRR_INTERNAL_ERROR_REDACTED"],
        )
        validate_payload(payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if payload["runtime_status"] == "confirmed_runtime" or args.allow_unavailable:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
