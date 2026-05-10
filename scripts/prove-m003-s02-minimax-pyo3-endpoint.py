#!/usr/bin/env python3
"""M003/S02 MiniMax PyO3/genai endpoint-normalization proof harness.

This skeleton is intentionally limited to deterministic endpoint contract
metadata. Later tasks add Rust build/import/provider phases; this task only
proves that the value passed to genai is a normalized MiniMax base endpoint with
a trailing slash and that the effective chat-completions URL preserves /v1.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s02-minimax-pyo3-endpoint/v1"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_ENDPOINT = "https://api.minimax.io/v1"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_API_KEY_ENV = "MINIMAX_API_KEY"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S02"
JSON_ARTIFACT = "S02-MINIMAX-PYO3-ENDPOINT.json"
MARKDOWN_ARTIFACT = "S02-MINIMAX-PYO3-ENDPOINT.md"
SUPPORTED_ENDPOINT_HOST = "api.minimax.io"

STATUS_CATEGORIES = (
    "not-run-local-only",
    "blocked-environment",
    "blocked-credential",
    "failed-runtime",
    "confirmed-runtime",
)
ROOT_CAUSE_CATEGORIES = (
    "local-only-endpoint-contract",
    "invalid-endpoint",
    "provider-not-called-local-only",
)

SECRET_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"RAW_LEGAL_TEXT_SENTINEL[^\n\r\t,;}]*"),
)
FORBIDDEN_TERMS = (
    "Authorization",
    "Bearer",
    "api_key",
    "api-key",
    "sk-",
    "BEGIN PRIVATE KEY",
    "RAW_LEGAL_TEXT_SENTINEL",
)

BOUNDARY_STATEMENT = (
    "This artifact is a focused proof harness for M003/S02 endpoint normalization only. "
    "It shows the MiniMax endpoint input, normalized PyO3/genai base endpoint, and "
    "effective /v1/chat/completions URL. It does not prove Legal KnowQL product "
    "behavior, legal-answer correctness, S03 validation, FalkorDB execution, ODT "
    "parsing, retrieval quality, or production schema quality. Raw provider bodies, "
    "credentials, prompts, raw legal text, and secret-like strings are not persisted."
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_positive_timeout(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("timeout must be >= 1")
    return parsed


def redact(text: str, sensitive_values: list[str] | None = None) -> str:
    redacted = text
    for value in sensitive_values or []:
        if value:
            redacted = redacted.replace(value, "<redacted>")
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("<redacted>", redacted)
    return redacted


def sanitize(value: Any, *, sensitive_values: list[str] | None = None) -> Any:
    if isinstance(value, str):
        return redact(value, sensitive_values=sensitive_values)
    if isinstance(value, list):
        return [sanitize(item, sensitive_values=sensitive_values) for item in value]
    if isinstance(value, tuple):
        return [sanitize(item, sensitive_values=sensitive_values) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in ("authorization", "api_key", "api-key", "token", "secret")):
                sanitized[str(key)] = "<redacted>"
            else:
                sanitized[str(key)] = sanitize(item, sensitive_values=sensitive_values)
        return sanitized
    return value


def assert_safe_payload(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for term in FORBIDDEN_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden term: {term}")


def _invalid_endpoint(endpoint_input: str, reason: str) -> dict[str, Any]:
    return {
        "endpoint_input": endpoint_input,
        "normalized_base_url": None,
        "effective_chat_completions_url": None,
        "preserves_v1": False,
        "normalization_applied": False,
        "normalization_status": "invalid",
        "status": "blocked-environment",
        "root_cause": "invalid-endpoint",
        "invalid_endpoint_reason": reason,
        "endpoint_contract_valid": False,
    }


def normalize_genai_base_endpoint(base_url: str) -> dict[str, Any]:
    """Normalize a MiniMax endpoint into the genai base URL contract.

    The accepted contract is the MiniMax HTTPS host with a path that reaches the
    /v1 API segment, optionally followed by /chat/completions. The returned
    normalized_base_url is always the /v1 base with a trailing slash, which keeps
    URL resolution from dropping the version path when genai appends chat paths.
    Invalid input is represented categorically and never as provider success or
    provider failure.
    """
    endpoint_input = base_url
    stripped = base_url.strip()
    if not stripped:
        return _invalid_endpoint(endpoint_input, "empty")

    parts = urlsplit(stripped)
    if parts.scheme != "https":
        return _invalid_endpoint(endpoint_input, "unsupported-scheme")
    if not parts.netloc:
        return _invalid_endpoint(endpoint_input, "missing-host")
    if parts.hostname != SUPPORTED_ENDPOINT_HOST:
        return _invalid_endpoint(endpoint_input, "unsupported-host")

    segments = [segment for segment in parts.path.split("/") if segment]
    if not segments or segments[0] != "v1":
        return _invalid_endpoint(endpoint_input, "missing-v1-path")

    v1_index = 0
    suffix = segments[v1_index + 1 :]
    if suffix not in ([], ["chat", "completions"]):
        return _invalid_endpoint(endpoint_input, "unsupported-path")

    base_path = "/" + "/".join(segments[: v1_index + 1]) + "/"
    normalized_base_url = urlunsplit(("https", SUPPORTED_ENDPOINT_HOST, base_path, "", ""))
    effective_path = base_path.rstrip("/") + "/chat/completions"
    effective_chat_completions_url = urlunsplit(("https", SUPPORTED_ENDPOINT_HOST, effective_path, "", ""))
    normalization_applied = stripped != normalized_base_url
    return {
        "endpoint_input": endpoint_input,
        "normalized_base_url": normalized_base_url,
        "effective_chat_completions_url": effective_chat_completions_url,
        "preserves_v1": effective_path == "/v1/chat/completions",
        "normalization_applied": normalization_applied,
        "normalization_status": "normalized" if normalization_applied else "already-normalized",
        "status": "not-run-local-only",
        "root_cause": "local-only-endpoint-contract",
        "invalid_endpoint_reason": None,
        "endpoint_contract_valid": True,
    }


def build_local_payload(*, model: str, endpoint: str, timeout: int) -> dict[str, Any]:
    endpoint_contract = normalize_genai_base_endpoint(endpoint)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "status": endpoint_contract["status"],
        "root_cause": endpoint_contract["root_cause"],
        "phase": "endpoint-contract",
        "provider_attempts": 0,
        "model": model,
        "timeout_seconds": timeout,
        "endpoint": endpoint_contract,
        "boundary_statement": BOUNDARY_STATEMENT,
        "safety": {
            "credentials_persisted": False,
            "auth_headers_persisted": False,
            "raw_provider_body_persisted": False,
            "raw_prompt_persisted": False,
            "raw_legal_text_persisted": False,
            "think_content_persisted": False,
        },
        "phases": {
            "endpoint_contract": endpoint_contract["normalization_status"],
            "build": "not-run-in-t01",
            "import": "not-run-in-t01",
            "provider": "not-run-in-t01",
        },
    }
    assert_safe_payload(payload)
    return payload


def write_artifacts(artifact_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    safe_payload = sanitize(payload)
    if not isinstance(safe_payload, dict):
        raise TypeError("payload must sanitize to a dictionary")
    assert_safe_payload(safe_payload)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    json_path = artifact_dir / JSON_ARTIFACT
    markdown_path = artifact_dir / MARKDOWN_ARTIFACT
    json_path.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(
        "# M003/S02 MiniMax PyO3 endpoint normalization\n\n"
        f"Status: `{safe_payload['status']}`\n\n"
        f"Root cause: `{safe_payload['root_cause']}`\n\n"
        f"Boundary: {safe_payload['boundary_statement']}\n",
        encoding="utf-8",
    )
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout", type=parse_positive_timeout, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--write-artifacts", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_local_payload(model=args.model, endpoint=args.endpoint, timeout=args.timeout)
    if args.write_artifacts:
        write_artifacts(args.artifact_dir, payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] != "blocked-environment" else 2


if __name__ == "__main__":
    raise SystemExit(main())
