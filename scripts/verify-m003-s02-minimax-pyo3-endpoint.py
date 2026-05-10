#!/usr/bin/env python3
"""Verify the M003/S02 MiniMax PyO3 endpoint artifacts are truthful and redacted."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s02-minimax-pyo3-endpoint/v2"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
EXPECTED_ENDPOINT_INPUT = "https://api.minimax.io/v1"
EXPECTED_NORMALIZED_BASE_URL = "https://api.minimax.io/v1/"
EXPECTED_EFFECTIVE_URL = "https://api.minimax.io/v1/chat/completions"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S02"
JSON_ARTIFACT = "S02-MINIMAX-PYO3-ENDPOINT.json"
MARKDOWN_ARTIFACT = "S02-MINIMAX-PYO3-ENDPOINT.md"

STATUS_CATEGORIES = {
    "not-run-local-only",
    "blocked-environment",
    "blocked-credential",
    "failed-runtime",
    "confirmed-runtime",
}
ROOT_CAUSE_CATEGORIES = {
    "local-only-endpoint-contract",
    "invalid-endpoint",
    "uvx-missing",
    "maturin-build-timeout",
    "maturin-build-failed",
    "python-import-timeout",
    "python-import-failed",
    "python-import-resolver-failed",
    "resolver-timeout",
    "resolver-failed",
    "endpoint-contract-lost-v1",
    "resolver-metadata-malformed",
    "minimax-credential-missing",
    "provider-timeout",
    "minimax-auth-failed",
    "minimax-rate-limited",
    "minimax-openai-schema-mismatch",
    "minimax-provider-call-failed",
    "provider-non-cypher-diagnostic",
    "none",
}
REQUIRED_SAFETY_FALSE_FIELDS = {
    "credentials_persisted",
    "auth_headers_persisted",
    "raw_provider_body_persisted",
    "raw_prompt_persisted",
    "raw_legal_text_persisted",
    "raw_falkordb_rows_persisted",
    "think_content_persisted",
}
REQUIRED_NON_CLAIM_PHRASES = {
    "Legal KnowQL product behavior",
    "legal-answer correctness",
    "ODT parsing",
    "retrieval quality",
    "S03 validation",
    "FalkorDB execution",
    "production schema quality",
}
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"RAW_LEGAL_TEXT_SENTINEL[^\n\r\t,;}]*"),
    re.compile(r"(?i)<\s*/?\s*think\s*>"),
)
FORBIDDEN_FIELD_PARTS = {
    "authorization",
    "auth_header",
    "raw_response",
    "raw_provider",
    "raw_body",
    "raw_prompt",
    "prompt",
    "raw_legal_text",
    "raw_falkordb",
    "falkordb_rows",
}
ALLOWED_FALSE_SAFETY_FIELDS = REQUIRED_SAFETY_FALSE_FIELDS | {"raw_body_persisted", "raw_provider_body_persisted"}
OVERCLAIM_PATTERNS = (
    re.compile(r"(?i)Legal KnowQL product behavior\s+(is\s+)?(validated|proven|confirmed|implemented|production[- ]ready)"),
    re.compile(r"(?i)legal-answer correctness\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)ODT parsing.*(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)retrieval quality.*(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)FalkorDB execution\s+(is\s+)?(validated|proven|confirmed)"),
    re.compile(r"(?i)production schema quality\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)S03 validation\s+(is\s+)?(validated|proven|confirmed|complete)"),
)


class VerificationError(ValueError):
    """Raised when an S02 artifact violates the handoff contract."""


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
    markdown = markdown_path.read_text(encoding="utf-8")
    return require_dict(payload, "payload"), markdown


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
            if normalized in ALLOWED_FALSE_SAFETY_FIELDS:
                require(item is False, f"{path}.{key} must be false")
            elif path != "payload.safety" and any(part in normalized for part in FORBIDDEN_FIELD_PARTS):
                fail(f"redaction violation: unsafe field persisted at {path}.{key}")
            assert_no_unsafe_fields(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_unsafe_fields(item, path=f"{path}[{index}]")


def validate_endpoint(payload: dict[str, Any]) -> None:
    endpoint = require_dict(payload.get("endpoint"), "endpoint")
    require(endpoint.get("endpoint_input") == EXPECTED_ENDPOINT_INPUT, "endpoint.endpoint_input mismatch")
    require(
        endpoint.get("normalized_base_url") == EXPECTED_NORMALIZED_BASE_URL,
        "endpoint.normalized_base_url must be https://api.minimax.io/v1/",
    )
    require(
        endpoint.get("effective_chat_completions_url") == EXPECTED_EFFECTIVE_URL,
        "endpoint.effective_chat_completions_url must preserve /v1/chat/completions",
    )
    require(endpoint.get("preserves_v1") is True, "endpoint.preserves_v1 must be true")
    require(endpoint.get("endpoint_contract_valid") is True, "endpoint.endpoint_contract_valid must be true")
    require(endpoint.get("normalization_status") in {"normalized", "already-normalized"}, "endpoint normalization status invalid")
    require(endpoint.get("normalized_base_url", "").endswith("/"), "endpoint.normalized_base_url must end with slash")


def validate_resolver_metadata(payload: dict[str, Any]) -> None:
    metadata = payload.get("resolver_metadata")
    if metadata is None:
        return
    resolver_metadata = require_dict(metadata, "resolver_metadata")
    require(resolver_metadata.get("module") == "m003_s02_minimax_pyo3_endpoint", "resolver_metadata.module mismatch")
    require(resolver_metadata.get("model") == DEFAULT_MODEL, "resolver_metadata.model mismatch")
    require(resolver_metadata.get("adapter_kind") == "OpenAI", "resolver_metadata.adapter_kind mismatch")
    require(
        resolver_metadata.get("normalized_endpoint_base_url") == EXPECTED_NORMALIZED_BASE_URL,
        "resolver_metadata.normalized_endpoint_base_url mismatch",
    )
    require(
        resolver_metadata.get("provider_body_persistence") == "disabled",
        "resolver_metadata.provider_body_persistence must be disabled",
    )


def validate_contract(payload: dict[str, Any]) -> None:
    require(payload.get("schema_version") == SCHEMA_VERSION, "schema_version mismatch")
    status = payload.get("status")
    root_cause = payload.get("root_cause")
    require(isinstance(status, str) and status in STATUS_CATEGORIES, "status must be a known category")
    require(isinstance(root_cause, str) and root_cause in ROOT_CAUSE_CATEGORIES, "root_cause must be a known category")
    require(payload.get("model") == DEFAULT_MODEL, "model mismatch")
    require(isinstance(payload.get("phase"), str) and payload["phase"], "phase must be a non-empty string")
    attempts = payload.get("provider_attempts")
    require(isinstance(attempts, int) and attempts >= 0, "provider_attempts must be a non-negative integer")
    require(isinstance(payload.get("timeout_seconds"), int) and payload["timeout_seconds"] >= 1, "timeout_seconds must be positive")
    validate_endpoint(payload)
    validate_resolver_metadata(payload)

    safety = require_dict(payload.get("safety"), "safety")
    for field in REQUIRED_SAFETY_FALSE_FIELDS:
        require(safety.get(field) is False, f"safety.{field} must be false")

    boundaries = require_dict(payload.get("boundaries"), "boundaries")
    does_not_prove = "\n".join(str(item) for item in require_list(boundaries.get("does_not_prove"), "boundaries.does_not_prove"))
    missing = sorted(phrase for phrase in REQUIRED_NON_CLAIM_PHRASES if phrase not in does_not_prove)
    require(not missing, "boundaries.does_not_prove missing: " + ", ".join(missing))


def validate_status_semantics(payload: dict[str, Any]) -> None:
    status = cast("str", payload["status"])
    root_cause = cast("str", payload["root_cause"])
    provider_attempts = cast("int", payload["provider_attempts"])
    phases = require_dict(payload.get("phases"), "phases")
    provider_phase = require_dict(phases.get("provider"), "phases.provider")

    if status in {"blocked-credential", "blocked-environment", "not-run-local-only"}:
        require(provider_attempts == 0, f"{status} must not claim provider attempts")
    if status == "blocked-credential":
        require(root_cause == "minimax-credential-missing", "blocked-credential root_cause must be minimax-credential-missing")
        require(provider_phase.get("status") == "blocked-credential", "blocked-credential provider phase mismatch")
    if status == "blocked-environment":
        require(root_cause != "none", "blocked-environment requires a real root_cause")
    if status == "failed-runtime":
        require(provider_attempts == 1, "failed-runtime must represent exactly one provider attempt")
        require(provider_phase.get("status") == "failed-runtime", "failed-runtime provider phase mismatch")
    if status == "confirmed-runtime":
        require(root_cause == "none", "confirmed-runtime root_cause must be none")
        require(provider_attempts == 1, "confirmed-runtime requires exactly one provider attempt")
        require(provider_phase.get("status") == "confirmed-runtime", "confirmed-runtime provider phase mismatch")
        require(
            root_cause not in {"endpoint-contract-lost-v1", "minimax-openai-schema-mismatch", "provider-non-cypher-diagnostic"},
            "confirmed-runtime cannot carry endpoint/schema/contamination root causes",
        )


def validate_markdown(payload: dict[str, Any], markdown: str) -> None:
    require(str(payload["status"]) in markdown, "Markdown missing status")
    require(str(payload["model"]) in markdown, "Markdown missing model")
    require(EXPECTED_NORMALIZED_BASE_URL in markdown, "Markdown missing normalized endpoint")
    require(EXPECTED_EFFECTIVE_URL in markdown, "Markdown missing effective URL")
    for non_claim in REQUIRED_NON_CLAIM_PHRASES:
        require(non_claim in markdown, f"Markdown missing boundary non-claim: {non_claim}")
    require("Raw provider body persisted: `False`" in markdown, "Markdown must expose raw_provider_body_persisted=false")
    require("Raw FalkorDB rows persisted: `False`" in markdown, "Markdown must expose raw_falkordb_rows_persisted=false")
    require("Think content persisted: `False`" in markdown, "Markdown must expose think_content_persisted=false")


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
        "provider_attempts": payload["provider_attempts"],
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
