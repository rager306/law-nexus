#!/usr/bin/env python3
"""Verify the M003/S03 reasoning-safe candidate artifacts are truthful and redacted."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s03-reasoning-safe-candidate/v2"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
EXPECTED_ENDPOINT_INPUT = "https://api.minimax.io/v1"
EXPECTED_NORMALIZED_BASE_URL = "https://api.minimax.io/v1/"
EXPECTED_EFFECTIVE_URL = "https://api.minimax.io/v1/chat/completions"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S03"
JSON_ARTIFACT = "S03-REASONING-SAFE-CANDIDATE.json"
MARKDOWN_ARTIFACT = "S03-REASONING-SAFE-CANDIDATE.md"

STATUS_CATEGORIES = {
    "blocked-credential",
    "blocked-environment",
    "failed-runtime",
    "confirmed-runtime",
}
ROOT_CAUSE_CATEGORIES = {
    "none",
    "invalid-endpoint",
    "minimax-credential-missing",
    "uvx-missing",
    "maturin-build-timeout",
    "maturin-build-failed",
    "python-import-timeout",
    "python-import-failed",
    "resolver-failed",
    "resolver-metadata-malformed",
    "endpoint-contract-lost-v1",
    "provider-http-error",
    "provider-timeout",
    "provider-schema-mismatch",
    "provider-malformed-response",
    "empty-content",
    "non-cypher-output",
    "reasoning-contamination",
    "markdown-contamination",
    "prose-contamination",
    "candidate-comment-contamination",
    "candidate-multi-statement",
    "redaction-violation",
}
PHASE_CATEGORIES = {
    "credential-check",
    "endpoint-contract",
    "build",
    "import",
    "resolver",
    "provider-response",
    "candidate-classification",
    "artifact-redaction",
}
REQUIRED_SAFETY_FALSE_FIELDS = {
    "raw_provider_body_persisted",
    "credential_persisted",
    "auth_header_persisted",
    "request_text_persisted",
    "raw_reasoning_text_persisted",
    "raw_legal_text_persisted",
    "raw_graph_rows_persisted",
}
REQUIRED_CANDIDATE_BOOL_FIELDS = {
    "accepted",
    "has_think_tag",
    "has_markdown_fence",
    "has_prose_prefix",
    "has_prose_suffix",
    "has_comment",
    "has_multi_statement",
    "raw_provider_body_persisted",
}
REQUIRED_NON_CLAIM_PHRASES = {
    "provider generation quality",
    "Legal KnowQL product behavior",
    "legal-answer correctness",
    "M002 validation acceptance",
    "graph execution",
    "ODT parsing",
    "retrieval quality",
    "production graph schema fitness",
}
REQUIRED_MARKDOWN_LINES = {
    "Prompt text persisted: `False`",
    "Raw body persisted: `False`",
    "Reasoning raw text persisted: `False`",
}
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"RAW_LEGAL_TEXT_SENTINEL[^\n\r\t,;}]*"),
    re.compile(r"(?i)<\s*/?\s*think\s*>"),
    re.compile(r"raw_provider_body_value"),
    re.compile(r"reasoning_text_value"),
    re.compile(r"raw_legal_text_value"),
    re.compile(r"falkordb_rows_value"),
    re.compile(r"request_prompt"),
)
FORBIDDEN_FIELD_PARTS = {
    "authorization",
    "raw_response",
    "request_prompt",
    "raw_legal_text",
    "falkordb_rows",
    "raw_falkordb",
}
ALLOWED_FALSE_FIELD_NAMES = REQUIRED_SAFETY_FALSE_FIELDS | {
    "raw_provider_body_persisted",
    "raw_body_persisted",
    "raw_text_persisted",
    "prompt_text_persisted",
    "credential_persisted",
    "auth_header_persisted",
}
OVERCLAIM_PATTERNS = (
    re.compile(r"(?i)Legal KnowQL product behavior\s+(is\s+)?(validated|proven|confirmed|implemented|production[- ]ready)"),
    re.compile(r"(?i)legal-answer correctness\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)M002 validation\s+(is\s+)?(validated|proven|confirmed|accepted|complete)"),
    re.compile(r"(?i)deterministic validation\s+(is\s+)?(validated|proven|confirmed|performed|complete)"),
    re.compile(r"(?i)(S03\s+)?performed\s+graph execution"),
    re.compile(r"(?i)graph execution\s+(is\s+)?(validated|proven|confirmed|performed|complete)"),
    re.compile(r"(?i)ODT parsing.*(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)retrieval quality.*(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)production graph schema fitness\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
)


class VerificationError(ValueError):
    """Raised when an S03 artifact violates the handoff contract."""


def fail(message: str) -> NoReturn:
    raise VerificationError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{path} must be an object")
    return cast("dict[str, Any]", value)


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        fail(f"{path} must be an array")
    return cast("list[Any]", value)


def load_artifacts(artifact_dir: Path) -> tuple[dict[str, Any], str]:
    json_path = artifact_dir / JSON_ARTIFACT
    markdown_path = artifact_dir / MARKDOWN_ARTIFACT
    if not json_path.exists():
        fail(f"missing JSON artifact: {json_path}")
    if not markdown_path.exists():
        fail(f"missing Markdown artifact: {markdown_path}")
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON artifact: {exc.msg} at line {exc.lineno} column {exc.colno}")
    return require_dict(payload, "payload"), markdown_path.read_text(encoding="utf-8")


def assert_no_forbidden_text(text: str, *, path: str, check_overclaims: bool = True) -> None:
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            fail(f"redaction violation in {path}: matched {pattern.pattern}")
    if check_overclaims:
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(text):
                fail(f"boundary overclaim in {path}: matched {pattern.pattern}")


def assert_no_unsafe_fields(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, dict):
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = key.lower().replace("-", "_")
            if normalized in ALLOWED_FALSE_FIELD_NAMES:
                require(item is False, f"{path}.{key} must be false")
            elif any(part in normalized for part in FORBIDDEN_FIELD_PARTS):
                fail(f"redaction violation: unsafe field persisted at {path}.{key}")
            elif normalized == "prompt" or normalized.endswith("_prompt"):
                fail(f"redaction violation: prompt field persisted at {path}.{key}")
            assert_no_unsafe_fields(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_unsafe_fields(item, path=f"{path}[{index}]")


def validate_endpoint(payload: dict[str, Any]) -> None:
    endpoint = require_dict(payload.get("endpoint"), "endpoint")
    require(endpoint.get("endpoint_input") == EXPECTED_ENDPOINT_INPUT, "endpoint.endpoint_input mismatch")
    require(endpoint.get("normalized_base_url") == EXPECTED_NORMALIZED_BASE_URL, "endpoint.normalized_base_url mismatch")
    require(endpoint.get("effective_chat_completions_url") == EXPECTED_EFFECTIVE_URL, "endpoint effective URL mismatch")
    require(endpoint.get("preserves_v1") is True, "endpoint.preserves_v1 must be true")
    require(endpoint.get("endpoint_contract_valid") is True, "endpoint.endpoint_contract_valid must be true")
    require(endpoint.get("normalization_status") in {"normalized", "already-normalized"}, "endpoint normalization status invalid")


def validate_request(payload: dict[str, Any]) -> None:
    request = require_dict(payload.get("request"), "request")
    require(request.get("model") == DEFAULT_MODEL, "request.model mismatch")
    require(request.get("stream") is False, "request.stream must be false")
    require(request.get("reasoning_split") is True, "request.reasoning_split must be true")
    require(request.get("message_count") == 2, "request.message_count must be 2")
    require(request.get("prompt_text_persisted") is False, "request.prompt_text_persisted must be false")


def validate_resolver(payload: dict[str, Any]) -> None:
    resolver = require_dict(payload.get("resolver"), "resolver")
    adapter_kind = resolver.get("adapter_kind")
    require(adapter_kind == "OpenAI", "resolver.adapter_kind must be OpenAI")
    if "module" in resolver:
        require(resolver.get("module") == "m003_s03_reasoning_safe_candidate", "resolver.module mismatch")
    if "model" in resolver:
        require(resolver.get("model") == DEFAULT_MODEL, "resolver.model mismatch")
    if "normalized_endpoint_base_url" in resolver:
        require(resolver.get("normalized_endpoint_base_url") == EXPECTED_NORMALIZED_BASE_URL, "resolver normalized endpoint mismatch")
    if "effective_chat_completions_url" in resolver:
        require(resolver.get("effective_chat_completions_url") == EXPECTED_EFFECTIVE_URL, "resolver effective URL mismatch")
    if "request_body_reasoning_split" in resolver:
        require(resolver.get("request_body_reasoning_split") is True, "resolver.request_body_reasoning_split must be true")
    if "provider_body_persistence" in resolver:
        require(resolver.get("provider_body_persistence") == "disabled", "resolver.provider_body_persistence must be disabled")


def validate_safety(payload: dict[str, Any]) -> None:
    safety = require_dict(payload.get("safety"), "safety")
    for field in REQUIRED_SAFETY_FALSE_FIELDS:
        require(safety.get(field) is False, f"safety.{field} must be false")


def validate_boundaries(payload: dict[str, Any]) -> None:
    boundaries = require_dict(payload.get("boundaries"), "boundaries")
    proves = "\n".join(str(item) for item in require_list(boundaries.get("proves"), "boundaries.proves"))
    does_not_prove_items = require_list(boundaries.get("does_not_prove"), "boundaries.does_not_prove")
    does_not_prove = "\n".join(str(item) for item in does_not_prove_items)
    safety = "\n".join(str(item) for item in require_list(boundaries.get("safety"), "boundaries.safety"))
    missing = sorted(phrase for phrase in REQUIRED_NON_CLAIM_PHRASES if phrase not in does_not_prove)
    require(not missing, "boundaries.does_not_prove missing: " + ", ".join(missing))
    require("classification" in proves, "boundaries.proves must mention classification, not validation or execution")
    require("not persisted" in safety, "boundaries.safety must state non-persistence")
    non_claims = require_list(payload.get("non_claims"), "non_claims")
    require(set(map(str, non_claims)) == set(map(str, does_not_prove_items)), "non_claims must mirror boundaries.does_not_prove")


def validate_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = require_dict(payload.get("candidate"), "candidate")
    for field in REQUIRED_CANDIDATE_BOOL_FIELDS:
        require(isinstance(candidate.get(field), bool), f"candidate.{field} must be boolean")
    require(isinstance(candidate.get("categories"), list), "candidate.categories must be an array")
    require(isinstance(candidate.get("text_length"), int) and candidate["text_length"] >= 0, "candidate.text_length invalid")
    require(isinstance(candidate.get("trimmed_length"), int) and candidate["trimmed_length"] >= 0, "candidate.trimmed_length invalid")
    require(candidate.get("root_cause") in ROOT_CAUSE_CATEGORIES, "candidate.root_cause must be known")
    require(candidate.get("status") in STATUS_CATEGORIES, "candidate.status must be known")
    starts_with = candidate.get("starts_with")
    require(starts_with in {"MATCH", "CALL", "OTHER", None}, "candidate.starts_with invalid")
    sha = candidate.get("sha256_12")
    require(sha is None or (isinstance(sha, str) and len(sha) == 12), "candidate.sha256_12 invalid")
    return candidate


def validate_reasoning(payload: dict[str, Any]) -> dict[str, Any]:
    reasoning = require_dict(payload.get("reasoning"), "reasoning")
    require(isinstance(reasoning.get("present"), bool), "reasoning.present must be boolean")
    require(isinstance(reasoning.get("separated"), bool), "reasoning.separated must be boolean")
    require(isinstance(reasoning.get("detail_count"), int) and reasoning["detail_count"] >= 0, "reasoning.detail_count invalid")
    require(isinstance(reasoning.get("detail_types"), list), "reasoning.detail_types must be an array")
    require(reasoning.get("raw_text_persisted") is False, "reasoning.raw_text_persisted must be false")
    if reasoning["present"]:
        require(reasoning["separated"] is True, "present reasoning must be separated")
        require(reasoning["detail_count"] >= 1, "present reasoning requires detail_count >= 1")
    return reasoning


def validate_contract(payload: dict[str, Any]) -> None:
    require(payload.get("schema_version") == SCHEMA_VERSION, "schema_version mismatch")
    status = payload.get("status")
    root_cause = payload.get("root_cause")
    phase = payload.get("phase")
    require(isinstance(status, str) and status in STATUS_CATEGORIES, "status must be a known category")
    require(isinstance(root_cause, str) and root_cause in ROOT_CAUSE_CATEGORIES, "root_cause must be a known category")
    require(isinstance(phase, str) and phase in PHASE_CATEGORIES, "phase must be a known category")
    require(payload.get("model") == DEFAULT_MODEL, "model mismatch")
    attempts = payload.get("provider_attempts")
    require(isinstance(attempts, int) and attempts >= 0, "provider_attempts must be a non-negative integer")
    require(isinstance(payload.get("timeout_seconds"), int) and payload["timeout_seconds"] >= 1, "timeout_seconds must be positive")
    validate_endpoint(payload)
    validate_request(payload)
    validate_resolver(payload)
    validate_safety(payload)
    validate_boundaries(payload)
    validate_candidate(payload)
    validate_reasoning(payload)


def validate_status_semantics(payload: dict[str, Any]) -> None:
    status = cast("str", payload["status"])
    root_cause = cast("str", payload["root_cause"])
    phase = cast("str", payload["phase"])
    provider_attempts = cast("int", payload["provider_attempts"])
    candidate = validate_candidate(payload)
    reasoning = validate_reasoning(payload)

    if status == "blocked-credential":
        require(root_cause == "minimax-credential-missing", "blocked-credential root_cause must be minimax-credential-missing")
        require(phase == "credential-check", "blocked-credential phase must be credential-check")
        require(provider_attempts == 0, "blocked-credential must not claim provider attempts")
        require(candidate.get("accepted") is False, "blocked-credential candidate must not be accepted")
        require("normalized_text" not in candidate, "rejected artifacts must not persist accepted candidate text")
        require(candidate.get("categories") == ["not-run"], "blocked-credential candidate categories must be ['not-run']")
        return

    if status == "blocked-environment":
        require(root_cause != "none", "blocked-environment requires a real root_cause")
        require(provider_attempts == 0, "blocked-environment must not claim provider attempts")
        require(candidate.get("accepted") is False, "blocked-environment candidate must not be accepted")
        require("normalized_text" not in candidate, "rejected artifacts must not persist accepted candidate text")
        return

    if status == "failed-runtime":
        require(root_cause != "none", "failed-runtime requires a real root_cause")
        require(provider_attempts == 1, "failed-runtime must represent exactly one provider attempt")
        require(candidate.get("accepted") is False, "failed-runtime candidate must not be accepted")
        require(candidate.get("status") == "failed-runtime", "failed-runtime candidate.status mismatch")
        require(candidate.get("root_cause") == root_cause, "failed-runtime candidate.root_cause mismatch")
        require("normalized_text" not in candidate, "rejected artifacts must not persist accepted candidate text")
        return

    require(status == "confirmed-runtime", "unexpected status after category validation")
    require(root_cause == "none", "confirmed-runtime root_cause must be none")
    require(phase == "candidate-classification", "confirmed-runtime phase must be candidate-classification")
    require(provider_attempts == 1, "confirmed-runtime requires exactly one provider attempt")
    require(candidate.get("accepted") is True, "confirmed-runtime candidate must be accepted")
    require(candidate.get("status") == "confirmed-runtime", "confirmed-runtime candidate.status mismatch")
    require(candidate.get("root_cause") == "none", "confirmed-runtime candidate.root_cause must be none")
    require(candidate.get("starts_with") in {"MATCH", "CALL"}, "confirmed-runtime candidate must start with MATCH or CALL")
    require(isinstance(candidate.get("normalized_text"), str) and candidate["normalized_text"].strip(), "confirmed-runtime requires accepted candidate text")
    normalized = cast("str", candidate["normalized_text"]).lstrip().upper()
    require(normalized.startswith(("MATCH", "CALL")), "confirmed-runtime accepted candidate must start with MATCH or CALL")
    clean_flags = [
        candidate.get("has_think_tag"),
        candidate.get("has_markdown_fence"),
        candidate.get("has_prose_prefix"),
        candidate.get("has_prose_suffix"),
        candidate.get("has_comment"),
        candidate.get("has_multi_statement"),
        bool(candidate.get("categories")),
    ]
    require(not any(clean_flags), "confirmed-runtime requires clean candidate diagnostics")
    require(candidate.get("raw_provider_body_persisted") is False, "confirmed-runtime raw provider body must not persist")
    require(reasoning.get("raw_text_persisted") is False, "confirmed-runtime raw reasoning text must not persist")


def validate_markdown(payload: dict[str, Any], markdown: str) -> None:
    require(str(payload["status"]) in markdown, "Markdown missing status")
    require(str(payload["root_cause"]) in markdown, "Markdown missing root cause")
    require(str(payload["phase"]) in markdown, "Markdown missing phase")
    require(EXPECTED_EFFECTIVE_URL in markdown, "Markdown missing effective URL")
    require("Request reasoning split: `True`" in markdown, "Markdown missing reasoning_split=true")
    for line in REQUIRED_MARKDOWN_LINES:
        require(line in markdown, f"Markdown missing safety line: {line}")
    for non_claim in REQUIRED_NON_CLAIM_PHRASES:
        require(non_claim in markdown, f"Markdown missing boundary non-claim: {non_claim}")


def verify_artifacts(artifact_dir: Path = DEFAULT_ARTIFACT_DIR) -> dict[str, Any]:
    payload, markdown = load_artifacts(artifact_dir)
    serialized_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert_no_forbidden_text(serialized_payload, path="JSON artifact", check_overclaims=False)
    assert_no_forbidden_text(markdown, path="Markdown artifact")
    assert_no_unsafe_fields(payload)
    validate_contract(payload)
    validate_status_semantics(payload)
    validate_markdown(payload, markdown)
    return {
        "status": payload["status"],
        "root_cause": payload["root_cause"],
        "phase": payload["phase"],
        "provider_attempts": payload["provider_attempts"],
        "candidate_accepted": payload["candidate"]["accepted"],
        "reasoning_present": payload["reasoning"]["present"],
        "json_artifact": str(artifact_dir / JSON_ARTIFACT),
        "markdown_artifact": str(artifact_dir / MARKDOWN_ARTIFACT),
        "verdict": "pass",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = verify_artifacts(args.artifact_dir)
    except VerificationError as exc:
        print(json.dumps({"verdict": "fail", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
