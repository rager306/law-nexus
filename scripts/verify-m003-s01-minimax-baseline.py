#!/usr/bin/env python3
"""Verify the M003/S01 MiniMax baseline artifacts are truthful and redacted."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s01-minimax-live-baseline/v1"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_BASE_URL = "https://api.minimax.io/v1"
EXPECTED_EFFECTIVE_URL = "https://api.minimax.io/v1/chat/completions"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S01"
JSON_ARTIFACT = "S01-MINIMAX-LIVE-BASELINE.json"
MARKDOWN_ARTIFACT = "S01-MINIMAX-LIVE-BASELINE.md"

STATUS_CATEGORIES = {
    "confirmed-runtime",
    "blocked-credential",
    "blocked-environment",
    "failed-runtime",
    "not-run-local-only",
}
ROOT_CAUSE_CATEGORIES = {
    "provider-not-called-local-only",
    "minimax-credential-missing",
    "minimax-auth-failed",
    "minimax-rate-limited",
    "minimax-http-4xx",
    "minimax-http-5xx",
    "minimax-provider-error",
    "provider-timeout",
    "provider-schema-mismatch",
    "reasoning-contamination",
    "non-cypher-content",
    "redaction-violation",
}
RESPONSE_SHAPE_FIELDS = {
    "status": str,
    "root_cause": (str, type(None)),
    "has_choices": bool,
    "choice_count": int,
    "has_message": bool,
    "has_content": bool,
    "content_kind": str,
    "candidate_prefix": (str, type(None)),
    "has_think_tag": bool,
    "has_reasoning_details": bool,
    "reasoning_details_count": int,
    "reasoning_detail_types": list,
}
REQUIRED_SAFETY_FALSE_FIELDS = {
    "raw_body_persisted",
    "request_body_persisted",
    "credential_persisted",
    "auth_header_persisted",
    "raw_legal_text_persisted",
    "raw_falkordb_rows_persisted",
}
REQUIRED_NON_CLAIM_PHRASES = {
    "PyO3/genai adapter behavior",
    "S03 validation",
    "FalkorDB execution",
    "Legal KnowQL product behavior",
    "legal-answer correctness",
    "Garant ODT parsing or retrieval quality",
    "production schema quality",
}
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"RAW_LEGAL_TEXT_SENTINEL[^\n\r\t,;}]*"),
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


class VerificationError(ValueError):
    """Raised when an S01 baseline artifact violates the handoff contract."""


def fail(message: str) -> NoReturn:
    raise VerificationError(message)


def _type_name(expected: object) -> str:
    if isinstance(expected, tuple):
        return " or ".join(item.__name__ for item in expected)
    if isinstance(expected, type):
        return expected.__name__
    return str(expected)


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


def assert_no_forbidden_text(text: str, *, path: str) -> None:
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            fail(f"redaction violation in {path}: matched {pattern.pattern}")


def assert_no_unsafe_fields(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, dict):
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = key.lower().replace("-", "_")
            if normalized == "request_body":
                require(item == "<omitted-request-body>", "request_body must be omitted, not persisted")
            elif path != "payload.safety" and any(part in normalized for part in FORBIDDEN_FIELD_PARTS):
                fail(f"redaction violation: unsafe field persisted at {path}.{key}")
            assert_no_unsafe_fields(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_unsafe_fields(item, path=f"{path}[{index}]")


def validate_contract(payload: dict[str, Any]) -> None:
    require(payload.get("schema_version") == SCHEMA_VERSION, "schema_version mismatch")
    status = payload.get("status")
    root_cause = payload.get("root_cause")
    require(isinstance(status, str) and status in STATUS_CATEGORIES, "status must be a known category")
    require(root_cause is None or root_cause in ROOT_CAUSE_CATEGORIES, "root_cause must be null or a known category")

    endpoint = require_dict(payload.get("endpoint"), "endpoint")
    require(endpoint.get("base_url_input") == DEFAULT_BASE_URL, "endpoint.base_url_input must preserve https://api.minimax.io/v1")
    require(endpoint.get("effective_url") == EXPECTED_EFFECTIVE_URL, "endpoint.effective_url must be /v1/chat/completions")
    require(endpoint.get("preserves_v1") is True, "endpoint.preserves_v1 must be true")
    require(payload.get("model") == DEFAULT_MODEL, "model mismatch")

    request_contract = require_dict(payload.get("request_contract"), "request_contract")
    require(
        request_contract.get("reasoning_split_requested") is True,
        "request_contract.reasoning_split_requested must be true",
    )
    require(request_contract.get("stream_requested") is False, "request_contract.stream_requested must be false")
    require(request_contract.get("user_message_persisted") is False, "request_contract.user_message_persisted must be false")

    provider_attempts = payload.get("provider_attempts")
    require(isinstance(provider_attempts, int) and provider_attempts >= 0, "provider_attempts must be a non-negative integer")

    provider_diagnostics = require_dict(payload.get("provider_diagnostics"), "provider_diagnostics")
    require("category" in provider_diagnostics, "provider_diagnostics.category is required")
    require("http_status_class" in provider_diagnostics, "provider_diagnostics.http_status_class is required")

    response_shape = require_dict(payload.get("response_shape"), "response_shape")
    for field, expected_type in RESPONSE_SHAPE_FIELDS.items():
        require(field in response_shape, f"response_shape.{field} is required")
        require(
            isinstance(response_shape[field], expected_type),
            f"response_shape.{field} must be {_type_name(expected_type)}",
        )
    require(response_shape["choice_count"] >= 0, "response_shape.choice_count must be non-negative")
    require(response_shape["reasoning_details_count"] >= 0, "response_shape.reasoning_details_count must be non-negative")

    safety = require_dict(payload.get("safety"), "safety")
    for field in REQUIRED_SAFETY_FALSE_FIELDS:
        require(safety.get(field) is False, f"safety.{field} must be false")

    boundaries = require_dict(payload.get("boundaries"), "boundaries")
    does_not_prove = "\n".join(str(item) for item in require_list(boundaries.get("does_not_prove"), "boundaries.does_not_prove"))
    missing_non_claims = sorted(phrase for phrase in REQUIRED_NON_CLAIM_PHRASES if phrase not in does_not_prove)
    require(not missing_non_claims, "boundaries.does_not_prove missing: " + ", ".join(missing_non_claims))


def validate_status_semantics(payload: dict[str, Any]) -> None:
    status = cast("str", payload["status"])
    root_cause = payload.get("root_cause")
    provider_attempts = cast("int", payload["provider_attempts"])
    response_shape = cast("dict[str, Any]", payload["response_shape"])

    if status == "confirmed-runtime":
        require(root_cause is None, "confirmed-runtime root_cause must be null")
        require(provider_attempts >= 1, "confirmed-runtime requires provider_attempts >= 1")
        require(response_shape["status"] == "confirmed-runtime", "confirmed-runtime response_shape.status mismatch")
        require(response_shape["has_choices"] is True, "confirmed-runtime requires choices")
        require(response_shape["choice_count"] >= 1, "confirmed-runtime requires choice_count >= 1")
        require(response_shape["has_message"] is True, "confirmed-runtime requires message")
        require(response_shape["has_content"] is True, "confirmed-runtime requires candidate-like content")
        require(response_shape["content_kind"] == "cypher_like", "confirmed-runtime requires cypher_like content")
        require(response_shape["candidate_prefix"] in {"MATCH", "CALL"}, "confirmed-runtime requires MATCH or CALL prefix")
        require(response_shape["has_think_tag"] is False, "confirmed-runtime must not contain think-tag contamination")
        require(response_shape["root_cause"] is None, "confirmed-runtime response_shape.root_cause must be null")
        return

    require(root_cause in ROOT_CAUSE_CATEGORIES, f"{status} requires a categorical root_cause")
    if status in {"blocked-credential", "blocked-environment", "not-run-local-only"}:
        require(provider_attempts == 0, f"{status} must not claim provider attempts")
    if status == "failed-runtime":
        require(provider_attempts >= 1, "failed-runtime must represent at least one provider attempt")
        require(response_shape["status"] in {"failed-runtime", status}, "failed-runtime response_shape.status mismatch")


def validate_markdown(payload: dict[str, Any], markdown: str) -> None:
    require(str(payload["status"]) in markdown, "Markdown missing status")
    require(str(payload["model"]) in markdown, "Markdown missing model")
    require(EXPECTED_EFFECTIVE_URL in markdown, "Markdown missing effective URL")
    for non_claim in REQUIRED_NON_CLAIM_PHRASES:
        require(non_claim in markdown, f"Markdown missing boundary non-claim: {non_claim}")
    require("Raw body persisted: `False`" in markdown, "Markdown must expose raw_body_persisted=false")


def verify_artifacts(artifact_dir: Path = DEFAULT_ARTIFACT_DIR) -> dict[str, Any]:
    payload, markdown = load_artifacts(artifact_dir)
    serialized_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert_no_forbidden_text(serialized_payload, path="JSON artifact")
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
