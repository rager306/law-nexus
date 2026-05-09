#!/usr/bin/env python3
"""Verify M001/S10 real local embedding runtime proof artifacts.

S10 is allowed to end in terminal blockers, but it is not allowed to overclaim.
A model or vector dimension is only proven when the artifact contains real encode
or live vector evidence with durations, dimensions, resource metadata, and raw
logs. Blocked and not-safe statuses must name the root cause and next proof step.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json"

PRIMARY_MODEL_IDS = ("deepvk/USER-bge-m3", "ai-sage/Giga-Embeddings-instruct")
USER_MODEL_ID = "deepvk/USER-bge-m3"
GIGA_MODEL_ID = "ai-sage/Giga-Embeddings-instruct"
FORBIDDEN_TERMS = ("GIGACHAT" + "_AUTH_DATA", "Bearer ", "sk-", "api_key")

TERMINAL_STATUSES = frozenset(
    {
        "confirmed-runtime",
        "failed-runtime",
        "blocked-environment",
        "not-safe-to-run",
        "not-attempted-by-policy",
    }
)
PROVEN_STATUSES = frozenset({"confirmed-runtime"})
BLOCKED_STATUSES = frozenset(
    {"failed-runtime", "blocked-environment", "not-safe-to-run", "not-attempted-by-policy"}
)
ALLOWED_VERDICTS = frozenset(
    {
        "proven-baseline",
        "blocked-baseline",
        "not-safe-challenger",
        "proven-challenger",
        "rejected",
        "deferred",
        "pending",
    }
)
REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "generated_at",
    "policy",
    "environment",
    "models",
    "vector_proofs",
    "fixture_policy",
    "confidence_loop",
    "raw_log_paths",
)
REQUIRED_MODEL_FIELDS = (
    "id",
    "role",
    "status",
    "verdict",
    "vector_dimension",
    "max_token_limit",
    "package_status",
    "cache_status",
    "download_status",
    "runtime_status",
    "encode_duration_ms",
    "observed_vector_dimension",
    "resource_metadata",
    "retrieval_metrics",
    "blocked_root_cause",
    "next_proof_step",
    "raw_log_paths",
)
REQUIRED_VECTOR_FIELDS = (
    "dimension",
    "model_id",
    "status",
    "index_created",
    "query_executed",
    "duration_ms",
    "blocked_root_cause",
    "next_proof_step",
    "raw_log_paths",
)


class VerificationMode(StrEnum):
    ALLOW_BLOCKED = "allow-blocked"
    REQUIRE_USER_PROOF = "require-user-proof"
    ALLOW_GIGA_BLOCKED_WITH_GATE = "allow-giga-blocked-with-gate"
    REQUIRE_FINAL = "require-final"


@dataclass
class VerificationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


def read_json(path: Path, result: VerificationResult) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        result.add(f"Artifact missing: {path}")
        return None
    except json.JSONDecodeError as exc:
        result.add(f"Artifact invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return None
    if not isinstance(parsed, dict):
        result.add("Artifact root must be an object")
        return None
    return cast("dict[str, Any]", parsed)


def check_forbidden_terms(path: Path, result: VerificationResult) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    for term in FORBIDDEN_TERMS:
        if term in text:
            result.add(f"Artifact contains forbidden managed credential/API literal: {term}")


def raw_log_exists(path_value: object, result: VerificationResult, label: str, artifact_root: Path) -> None:
    if not isinstance(path_value, str) or not path_value.strip():
        result.add(f"{label} raw log path must be a non-empty string")
        return
    path = Path(path_value)
    candidates = [path] if path.is_absolute() else [ROOT / path, artifact_root / path]
    if not any(candidate.is_file() for candidate in candidates):
        result.add(f"{label} raw log path does not exist: {path_value}")


def require_non_empty_string(value: object, result: VerificationResult, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        result.add(f"{path} must be a non-empty string")


def require_number(value: object, result: VerificationResult, path: str) -> None:
    if not isinstance(value, int | float):
        result.add(f"{path} must be numeric")


def validate_policy(payload: dict[str, Any], result: VerificationResult) -> None:
    policy = payload.get("policy")
    if not isinstance(policy, dict):
        result.add("policy must be an object")
        return
    if policy.get("managed_embedding_apis") != "excluded":
        result.add("policy.managed_embedding_apis must be excluded")
    if policy.get("local_open_weight_only") is not True:
        result.add("policy.local_open_weight_only must be true")
    if policy.get("downloads") not in {"disabled", "explicit-open-weight-only", "cache-only"}:
        result.add("policy.downloads must be disabled, cache-only, or explicit-open-weight-only")


def validate_environment(payload: dict[str, Any], result: VerificationResult) -> None:
    environment = payload.get("environment")
    if not isinstance(environment, dict):
        result.add("environment must be an object")
        return
    for field_name in ("python", "platform", "cpu_count", "memory_mib", "package_status", "cache_status"):
        if field_name not in environment:
            result.add(f"environment missing required field: {field_name}")
    logs = environment.get("raw_log_paths")
    if not isinstance(logs, list) or not logs:
        result.add("environment.raw_log_paths must be a non-empty list")


def model_map(payload: dict[str, Any], result: VerificationResult) -> dict[str, dict[str, Any]]:
    models = payload.get("models")
    if not isinstance(models, list):
        result.add("models must be a list")
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for index, model in enumerate(models):
        if not isinstance(model, dict):
            result.add(f"models[{index}] must be an object")
            continue
        model_obj = cast("dict[str, Any]", model)
        model_id = model_obj.get("id")
        if not isinstance(model_id, str):
            result.add(f"models[{index}].id must be a string")
            continue
        mapped[model_id] = model_obj
    for model_id in PRIMARY_MODEL_IDS:
        if model_id not in mapped:
            result.add(f"models missing required primary model: {model_id}")
    return mapped


def is_model_proven(model: dict[str, Any]) -> bool:
    return model.get("runtime_status") in PROVEN_STATUSES or model.get("status") in PROVEN_STATUSES


def validate_model(model: dict[str, Any], result: VerificationResult, artifact_root: Path) -> None:
    model_id = str(model.get("id"))
    for field_name in REQUIRED_MODEL_FIELDS:
        if field_name not in model:
            result.add(f"model {model_id} missing required field: {field_name}")
    status = model.get("status")
    runtime_status = model.get("runtime_status")
    if status not in TERMINAL_STATUSES:
        result.add(f"model {model_id} has non-terminal status: {status!r}")
    if runtime_status not in TERMINAL_STATUSES:
        result.add(f"model {model_id} has non-terminal runtime_status: {runtime_status!r}")
    verdict = model.get("verdict")
    if verdict not in ALLOWED_VERDICTS:
        result.add(f"model {model_id} has unsupported verdict: {verdict!r}")
    if verdict in {"proven-baseline", "proven-challenger"} and not is_model_proven(model):
        result.add(f"model {model_id} verdict {verdict} requires confirmed-runtime status")
    if is_model_proven(model):
        require_number(model.get("encode_duration_ms"), result, f"model {model_id}.encode_duration_ms")
        observed = model.get("observed_vector_dimension")
        expected = model.get("vector_dimension")
        if observed != expected:
            result.add(f"model {model_id} observed_vector_dimension must equal vector_dimension when proven")
        metrics = model.get("retrieval_metrics")
        if not isinstance(metrics, dict) or not metrics:
            result.add(f"model {model_id} requires retrieval_metrics when proven")
        if model.get("blocked_root_cause") not in {None, ""}:
            result.add(f"model {model_id} cannot be proven while blocked_root_cause is set")
    else:
        require_non_empty_string(model.get("blocked_root_cause"), result, f"model {model_id}.blocked_root_cause")
        require_non_empty_string(model.get("next_proof_step"), result, f"model {model_id}.next_proof_step")
    resources = model.get("resource_metadata")
    if not isinstance(resources, dict) or not resources:
        result.add(f"model {model_id}.resource_metadata must be a non-empty object")
    raw_logs = model.get("raw_log_paths")
    if not isinstance(raw_logs, list) or not raw_logs:
        result.add(f"model {model_id}.raw_log_paths must be a non-empty list")
    else:
        for raw_log in raw_logs:
            raw_log_exists(raw_log, result, f"model {model_id}", artifact_root)
    if model_id == GIGA_MODEL_ID:
        gate = model.get("safety_gate")
        if not isinstance(gate, dict):
            result.add("GigaEmbeddings model must include safety_gate object")
        else:
            if gate.get("status") not in TERMINAL_STATUSES | {"safe-to-run"}:
                result.add("GigaEmbeddings safety_gate.status must be terminal or safe-to-run")
            reasons = gate.get("reasons")
            if gate.get("status") != "safe-to-run" and (not isinstance(reasons, list) or not reasons):
                result.add("GigaEmbeddings blocked/not-safe safety_gate must include reasons")
    instruction = model.get("instruction_handling")
    if model_id == GIGA_MODEL_ID:
        if not isinstance(instruction, dict) or instruction.get("query_instruction_applied") is not True:
            result.add("GigaEmbeddings proof must record query_instruction_applied=true")
    if model_id == USER_MODEL_ID:
        if isinstance(instruction, dict) and instruction.get("query_instruction_applied") is True:
            result.add("USER-bge-m3 proof must not require query instruction")


def vector_map(payload: dict[str, Any], result: VerificationResult) -> dict[int, dict[str, Any]]:
    vector_proofs = payload.get("vector_proofs")
    if not isinstance(vector_proofs, list):
        result.add("vector_proofs must be a list")
        return {}
    mapped: dict[int, dict[str, Any]] = {}
    for index, proof in enumerate(vector_proofs):
        if not isinstance(proof, dict):
            result.add(f"vector_proofs[{index}] must be an object")
            continue
        proof_obj = cast("dict[str, Any]", proof)
        dimension = proof_obj.get("dimension")
        if not isinstance(dimension, int):
            result.add(f"vector_proofs[{index}].dimension must be an integer")
            continue
        mapped[dimension] = proof_obj
    for dimension in (1024, 2048):
        if dimension not in mapped:
            result.add(f"vector_proofs missing required dimension: {dimension}")
    return mapped


def validate_vector_proof(proof: dict[str, Any], result: VerificationResult, artifact_root: Path) -> None:
    dimension = proof.get("dimension")
    for field_name in REQUIRED_VECTOR_FIELDS:
        if field_name not in proof:
            result.add(f"vector proof {dimension} missing required field: {field_name}")
    status = proof.get("status")
    if status not in TERMINAL_STATUSES:
        result.add(f"vector proof {dimension} has non-terminal status: {status!r}")
    if status in PROVEN_STATUSES:
        if proof.get("index_created") is not True:
            result.add(f"vector proof {dimension} confirmed-runtime requires index_created=true")
        if proof.get("query_executed") is not True:
            result.add(f"vector proof {dimension} confirmed-runtime requires query_executed=true")
        require_number(proof.get("duration_ms"), result, f"vector proof {dimension}.duration_ms")
        if proof.get("blocked_root_cause") not in {None, ""}:
            result.add(f"vector proof {dimension} cannot be proven while blocked_root_cause is set")
    else:
        require_non_empty_string(proof.get("blocked_root_cause"), result, f"vector proof {dimension}.blocked_root_cause")
        require_non_empty_string(proof.get("next_proof_step"), result, f"vector proof {dimension}.next_proof_step")
    logs = proof.get("raw_log_paths")
    if not isinstance(logs, list) or not logs:
        result.add(f"vector proof {dimension}.raw_log_paths must be a non-empty list")
    else:
        for raw_log in logs:
            raw_log_exists(raw_log, result, f"vector proof {dimension}", artifact_root)


def validate_fixture_policy(payload: dict[str, Any], result: VerificationResult) -> None:
    fixture_policy = payload.get("fixture_policy")
    if not isinstance(fixture_policy, dict):
        result.add("fixture_policy must be an object")
        return
    if fixture_policy.get("raw_legal_text_logged") is not False:
        result.add("fixture_policy.raw_legal_text_logged must be false")
    if fixture_policy.get("raw_vectors_logged") is not False:
        result.add("fixture_policy.raw_vectors_logged must be false")
    source = fixture_policy.get("source")
    if source not in {"synthetic-only", "s05-evidence-span-ids", "synthetic-and-s05-evidence-span-ids"}:
        result.add("fixture_policy.source must describe synthetic/S05 span-ID fixture source")
    if fixture_policy.get("production_legal_quality_claim") not in {False, "not-proven"}:
        result.add("fixture_policy.production_legal_quality_claim must remain false/not-proven")


def validate_confidence_loop(payload: dict[str, Any], result: VerificationResult, mode: VerificationMode) -> None:
    loop = payload.get("confidence_loop")
    if not isinstance(loop, dict):
        result.add("confidence_loop must be an object")
        return
    question = loop.get("question")
    if question != "Ты на 100% уверен в этой стратегии?":
        result.add("confidence_loop.question must be the required 100% confidence question")
    for field_name in ("answer", "holes_found", "fixes_or_next_proofs"):
        if field_name not in loop:
            result.add(f"confidence_loop missing required field: {field_name}")
    holes = loop.get("holes_found")
    fixes = loop.get("fixes_or_next_proofs")
    if not isinstance(holes, list) or not holes:
        result.add("confidence_loop.holes_found must be a non-empty list")
    if not isinstance(fixes, list) or not fixes:
        result.add("confidence_loop.fixes_or_next_proofs must be a non-empty list")
    if mode == VerificationMode.REQUIRE_FINAL and loop.get("closed") is not True:
        result.add("require-final mode requires confidence_loop.closed=true")


def validate_mode_requirements(
    models: dict[str, dict[str, Any]],
    vectors: dict[int, dict[str, Any]],
    result: VerificationResult,
    mode: VerificationMode,
) -> None:
    user = models.get(USER_MODEL_ID, {})
    giga = models.get(GIGA_MODEL_ID, {})
    if mode == VerificationMode.REQUIRE_USER_PROOF:
        if not is_model_proven(user):
            result.add("require-user-proof mode requires USER-bge-m3 confirmed-runtime encode proof")
        vector_1024 = vectors.get(1024, {})
        if vector_1024.get("status") not in PROVEN_STATUSES:
            result.add("require-user-proof mode requires confirmed-runtime 1024-dim vector proof")
    if mode == VerificationMode.ALLOW_GIGA_BLOCKED_WITH_GATE:
        gate = giga.get("safety_gate") if isinstance(giga, dict) else None
        if not is_model_proven(giga):
            if not isinstance(gate, dict) or gate.get("status") not in {"not-safe-to-run", "blocked-environment", "not-attempted-by-policy"}:
                result.add("allow-giga-blocked-with-gate mode requires Giga safety_gate terminal no-go status when not proven")
    if mode == VerificationMode.REQUIRE_FINAL:
        final = any(model.get("verdict") in {"proven-baseline", "blocked-baseline"} for model in models.values())
        if not final:
            result.add("require-final mode requires at least one baseline verdict")
        for dimension in (1024, 2048):
            if dimension not in vectors:
                result.add(f"require-final mode missing vector verdict for dimension {dimension}")


def validate_payload(payload: dict[str, Any], result: VerificationResult, artifact_root: Path, mode: VerificationMode) -> None:
    for field_name in REQUIRED_TOP_LEVEL_FIELDS:
        if field_name not in payload:
            result.add(f"artifact missing top-level field: {field_name}")
    validate_policy(payload, result)
    validate_environment(payload, result)
    validate_fixture_policy(payload, result)
    validate_confidence_loop(payload, result, mode)

    logs = payload.get("raw_log_paths")
    if not isinstance(logs, list) or not logs:
        result.add("raw_log_paths must be a non-empty list")
    else:
        for raw_log in logs:
            raw_log_exists(raw_log, result, "artifact", artifact_root)

    models = model_map(payload, result)
    for model in models.values():
        validate_model(model, result, artifact_root)
    vectors = vector_map(payload, result)
    for vector in vectors.values():
        validate_vector_proof(vector, result, artifact_root)
    validate_mode_requirements(models, vectors, result, mode)


def verify_artifact(path: Path, mode: VerificationMode) -> VerificationResult:
    result = VerificationResult()
    check_forbidden_terms(path, result)
    payload = read_json(path, result)
    if payload is None:
        return result
    validate_payload(payload, result, path.parent, mode)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--allow-blocked", action="store_true")
    mode.add_argument("--require-user-proof", action="store_true")
    mode.add_argument("--allow-giga-blocked-with-gate", action="store_true")
    mode.add_argument("--require-final", action="store_true")
    return parser.parse_args(argv)


def selected_mode(args: argparse.Namespace) -> VerificationMode:
    if args.require_user_proof:
        return VerificationMode.REQUIRE_USER_PROOF
    if args.allow_giga_blocked_with_gate:
        return VerificationMode.ALLOW_GIGA_BLOCKED_WITH_GATE
    if args.require_final:
        return VerificationMode.REQUIRE_FINAL
    return VerificationMode.ALLOW_BLOCKED


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = selected_mode(args)
    result = verify_artifact(args.artifact, mode)
    if not result.ok:
        print(f"S10 embedding runtime proof verification failed ({mode.value}):", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"S10 embedding runtime proof verification passed ({mode.value}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
