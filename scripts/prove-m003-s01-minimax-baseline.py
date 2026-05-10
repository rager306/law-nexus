#!/usr/bin/env python3
"""Credential-gated M003/S01 MiniMax OpenAI-compatible baseline proof.

The CLI performs at most one direct HTTP POST when a MiniMax credential is
available. It writes only categorical/redacted evidence: no raw provider bodies,
request prompts, credentials, auth headers, raw legal text, or FalkorDB rows are
persisted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast
from urllib import error, request
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s01-minimax-live-baseline/v1"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_BASE_URL = "https://api.minimax.io/v1"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S01"
JSON_ARTIFACT = "S01-MINIMAX-LIVE-BASELINE.json"
MARKDOWN_ARTIFACT = "S01-MINIMAX-LIVE-BASELINE.md"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_API_KEY_ENV = "MINIMAX_API_KEY"
SAFE_CYPHER_PROMPT = (
    "Return one read-only FalkorDB Cypher query only. Use MATCH (n) RETURN n LIMIT 1. "
    "Do not include explanations, legal advice, raw legal text, or markdown."
)

STATUS_CATEGORIES = (
    "confirmed-runtime",
    "blocked-credential",
    "blocked-environment",
    "failed-runtime",
    "not-run-local-only",
)
ROOT_CAUSE_CATEGORIES = (
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
SENSITIVE_KEY_PARTS = (
    "authorization",
    "api_key",
    "api-key",
    "apikey",
    "secret",
    "token",
    "password",
    "raw_response",
    "raw_provider",
    "prompt",
    "raw_legal_text",
)

SYSTEM_PROMPT = (
    "Return only read-only FalkorDB Cypher beginning with MATCH or CALL. "
    "Do not provide legal advice or raw legal text."
)
BOUNDARY_STATEMENT = (
    "This artifact covers a direct MiniMax OpenAI-compatible baseline proof only. "
    "It records documented endpoint, model, reasoning_split=true, stream=false, "
    "and categorical response-shape diagnostics. It does not prove Legal KnowQL "
    "product behavior, legal-answer correctness, production graph schema fitness, "
    "Garant ODT parsing, retrieval quality, PyO3/genai adapter behavior, or provider "
    "generation quality. Raw provider bodies are not persisted."
)


class UrlOpen(Protocol):
    def __call__(self, req: request.Request, *, timeout: int) -> Any: ...


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compose_chat_completions_url(base_url: str) -> dict[str, Any]:
    """Return effective MiniMax chat-completions URL metadata without dropping /v1."""
    stripped = base_url.strip()
    parts = urlsplit(stripped)
    path = parts.path.rstrip("/")
    if path.endswith("/chat/completions"):
        effective_path = path
    else:
        effective_path = f"{path}/chat/completions" if path else "/chat/completions"
    effective_url = urlunsplit((parts.scheme, parts.netloc, effective_path, "", ""))
    return {
        "base_url_input": base_url,
        "effective_url": effective_url,
        "preserves_v1": "v1" in effective_path.split("/chat/completions", maxsplit=1)[0].split("/"),
    }


def build_request_body(*, model: str = DEFAULT_MODEL, user_prompt: str) -> dict[str, Any]:
    """Build the direct MiniMax OpenAI-compatible request body for the live proof."""
    return {
        "model": model,
        "reasoning_split": True,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }


def _message_from_decoded(decoded: object) -> dict[str, Any] | None:
    if not isinstance(decoded, dict):
        return None
    choices = decoded.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    return cast("dict[str, Any]", message)


def _reasoning_detail_summary(reasoning_details: object) -> tuple[bool, int, list[str]]:
    if reasoning_details is None:
        return False, 0, []
    if isinstance(reasoning_details, list):
        detail_types: list[str] = []
        for item in reasoning_details:
            if isinstance(item, dict) and isinstance(item.get("type"), str):
                detail_types.append(item["type"])
            else:
                detail_types.append(type(item).__name__)
        return True, len(reasoning_details), detail_types
    return True, 1, [type(reasoning_details).__name__]


def classify_response_shape(decoded: object) -> dict[str, Any]:
    """Classify an OpenAI-compatible response without returning raw provider content."""
    choices = decoded.get("choices") if isinstance(decoded, dict) else None
    choice_count = len(choices) if isinstance(choices, list) else 0
    message = _message_from_decoded(decoded)
    if message is None:
        return {
            "status": "failed-runtime",
            "root_cause": "provider-schema-mismatch",
            "has_choices": isinstance(choices, list),
            "choice_count": choice_count,
            "has_message": False,
            "has_content": False,
            "content_kind": "missing",
            "candidate_prefix": None,
            "has_think_tag": False,
            "has_reasoning_details": False,
            "reasoning_details_count": 0,
            "reasoning_detail_types": [],
        }

    content = message.get("content")
    has_content = isinstance(content, str) and bool(content.strip())
    if not isinstance(content, str):
        return {
            "status": "failed-runtime",
            "root_cause": "provider-schema-mismatch",
            "has_choices": True,
            "choice_count": choice_count,
            "has_message": True,
            "has_content": False,
            "content_kind": "missing",
            "candidate_prefix": None,
            "has_think_tag": False,
            "has_reasoning_details": False,
            "reasoning_details_count": 0,
            "reasoning_detail_types": [],
        }

    stripped = content.lstrip()
    upper = stripped[:5].upper()
    candidate_prefix = "MATCH" if upper.startswith("MATCH") else "CALL" if upper.startswith("CALL") else "OTHER"
    has_think_tag = "<think" in content.lower() or "</think" in content.lower()
    content_kind = "cypher_like" if candidate_prefix in {"MATCH", "CALL"} else "non_cypher_text"
    has_reasoning_details, reasoning_details_count, reasoning_detail_types = _reasoning_detail_summary(
        message.get("reasoning_details")
    )
    root_cause = None
    status = "confirmed-runtime"
    if has_think_tag:
        root_cause = "reasoning-contamination"
        status = "failed-runtime"
    elif not has_content or content_kind != "cypher_like":
        root_cause = "non-cypher-content"
        status = "failed-runtime"

    return {
        "status": status,
        "root_cause": root_cause,
        "has_choices": True,
        "choice_count": choice_count,
        "has_message": True,
        "has_content": has_content,
        "content_kind": content_kind,
        "candidate_prefix": candidate_prefix,
        "has_think_tag": has_think_tag,
        "has_reasoning_details": has_reasoning_details,
        "reasoning_details_count": reasoning_details_count,
        "reasoning_detail_types": reasoning_detail_types,
    }


def redact(text: str, *, sensitive_values: list[str] | None = None) -> str:
    redacted = text
    for value in sensitive_values or []:
        if value:
            redacted = redacted.replace(value, "<redacted>")
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("<redacted>", redacted)
    return redacted


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_artifact_payload(value: Any, *, sensitive_values: list[str] | None = None) -> Any:
    """Remove or redact values that must not survive in JSON/Markdown artifacts."""
    if isinstance(value, str):
        return redact(value, sensitive_values=sensitive_values)
    if isinstance(value, list):
        return [sanitize_artifact_payload(item, sensitive_values=sensitive_values) for item in value]
    if isinstance(value, tuple):
        return [sanitize_artifact_payload(item, sensitive_values=sensitive_values) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        redacted_field_count = 0
        for raw_key, raw_item in value.items():
            key = str(raw_key)
            if key == "request_body":
                sanitized[key] = "<omitted-request-body>"
            elif key.endswith("_persisted") and isinstance(raw_item, bool):
                sanitized[key] = raw_item
            elif _is_sensitive_key(key):
                redacted_field_count += 1
            else:
                sanitized[key] = sanitize_artifact_payload(raw_item, sensitive_values=sensitive_values)
        if redacted_field_count:
            sanitized["redacted_field_count"] = sanitized.get("redacted_field_count", 0) + redacted_field_count
        return sanitized
    return value


def assert_safe_payload(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for term in FORBIDDEN_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden term: {term}")


def boundary_payload() -> dict[str, list[str]]:
    return {
        "proves": [
            "direct MiniMax OpenAI-compatible baseline proof contract shape",
            "documented model MiniMax-M2.7-highspeed and /v1/chat/completions endpoint composition",
            "request body intent includes reasoning_split=true and stream=false",
            "response diagnostics are categorical booleans/counts/types rather than raw provider bodies",
        ],
        "does_not_prove": [
            "Legal KnowQL product behavior",
            "legal-answer correctness",
            "production graph schema fitness / production schema quality",
            "Garant ODT parsing or retrieval quality",
            "FalkorDB execution",
            "S03 validation",
            "PyO3/genai adapter behavior",
            "provider generation quality",
        ],
        "safety": [
            "raw provider bodies are not persisted",
            "request prompts, credentials, auth headers, raw legal text, and secret-like values are omitted or redacted",
            "candidate content is represented only by safe categories such as MATCH/CALL/non-cypher and contamination booleans",
            "LLM output is non-authoritative and remains untrusted draft text outside deterministic validation",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    endpoint = payload.get("endpoint", {})
    response_shape = payload.get("response_shape", {})
    request_contract = payload.get("request_contract", {})
    provider_diagnostics = payload.get("provider_diagnostics", {})
    lines = [
        "# M003/S01 MiniMax Live Baseline",
        "",
        f"- Schema: `{payload.get('schema_version')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Root cause: `{payload.get('root_cause')}`",
        f"- Model: `{payload.get('model')}`",
        f"- Base URL input: `{endpoint.get('base_url_input') if isinstance(endpoint, dict) else None}`",
        f"- Effective URL: `{endpoint.get('effective_url') if isinstance(endpoint, dict) else None}`",
        f"- Preserves /v1: `{endpoint.get('preserves_v1') if isinstance(endpoint, dict) else None}`",
        f"- Reasoning split requested: `{request_contract.get('reasoning_split_requested') if isinstance(request_contract, dict) else None}`",
        f"- Stream requested: `{request_contract.get('stream_requested') if isinstance(request_contract, dict) else None}`",
        f"- Provider attempts: `{payload.get('provider_attempts', 0)}`",
        f"- HTTP status class: `{provider_diagnostics.get('http_status_class') if isinstance(provider_diagnostics, dict) else None}`",
        f"- Provider category: `{provider_diagnostics.get('category') if isinstance(provider_diagnostics, dict) else None}`",
        f"- Response root cause: `{response_shape.get('root_cause') if isinstance(response_shape, dict) else None}`",
        f"- Response content kind: `{response_shape.get('content_kind') if isinstance(response_shape, dict) else None}`",
        f"- Reasoning details present: `{response_shape.get('has_reasoning_details') if isinstance(response_shape, dict) else False}`",
        f"- Reasoning details count: `{response_shape.get('reasoning_details_count') if isinstance(response_shape, dict) else 0}`",
        f"- Think-tag contamination: `{response_shape.get('has_think_tag') if isinstance(response_shape, dict) else False}`",
        f"- Raw body persisted: `{payload.get('safety', {}).get('raw_body_persisted') if isinstance(payload.get('safety'), dict) else None}`",
        f"- Credential persisted: `{payload.get('safety', {}).get('credential_persisted') if isinstance(payload.get('safety'), dict) else None}`",
        "",
        BOUNDARY_STATEMENT,
        "",
        "## Boundaries",
        "",
        "### Proves",
        *[f"- {item}" for item in payload.get("boundaries", {}).get("proves", [])],
        "",
        "### Does not prove",
        *[f"- {item}" for item in payload.get("boundaries", {}).get("does_not_prove", [])],
        "",
        "### Safety",
        *[f"- {item}" for item in payload.get("boundaries", {}).get("safety", [])],
        "",
    ]
    return "\n".join(lines)


def write_artifacts(
    output_dir: Path,
    payload: dict[str, Any],
    *,
    sensitive_values: list[str] | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_payload = cast("dict[str, Any]", sanitize_artifact_payload(payload, sensitive_values=sensitive_values))
    assert_safe_payload(safe_payload)
    json_path = output_dir / JSON_ARTIFACT
    markdown_path = output_dir / MARKDOWN_ARTIFACT
    json_path.write_text(
        json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_text = render_markdown(safe_payload)
    assert_safe_payload({"markdown": markdown_text})
    markdown_path.write_text(markdown_text, encoding="utf-8")
    return json_path, markdown_path


def base_payload(*, model: str, base_url: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "model": model,
        "endpoint": compose_chat_completions_url(base_url),
        "request_contract": {
            "reasoning_split_requested": True,
            "stream_requested": False,
            "message_count": 2,
            "user_message_persisted": False,
        },
        "status_categories": list(STATUS_CATEGORIES),
        "root_cause_categories": list(ROOT_CAUSE_CATEGORIES),
        "boundaries": boundary_payload(),
        "safety": {
            "raw_body_persisted": False,
            "request_body_persisted": False,
            "credential_persisted": False,
            "auth_header_persisted": False,
            "raw_legal_text_persisted": False,
            "raw_falkordb_rows_persisted": False,
        },
    }


def build_local_only_payload(*, model: str, base_url: str, timeout: int) -> dict[str, Any]:
    _ = timeout
    payload = base_payload(model=model, base_url=base_url)
    payload.update(
        {
            "status": "not-run-local-only",
            "root_cause": "provider-not-called-local-only",
            "provider_attempts": 0,
            "request_body": build_request_body(model=model, user_prompt="<omitted-local-only-placeholder>"),
            "provider_diagnostics": {"category": "not-run-local-only", "http_status_class": None},
            "response_shape": {
                "status": "not-run-local-only",
                "root_cause": "provider-not-called-local-only",
                "has_choices": False,
                "choice_count": 0,
                "has_message": False,
                "has_content": False,
                "content_kind": "not-run",
                "candidate_prefix": None,
                "has_think_tag": False,
                "has_reasoning_details": False,
                "reasoning_details_count": 0,
                "reasoning_detail_types": [],
            },
        }
    )
    return payload


def build_missing_credential_payload(*, model: str, base_url: str, api_key_env: str) -> dict[str, Any]:
    payload = base_payload(model=model, base_url=base_url)
    payload.update(
        {
            "status": "blocked-credential",
            "root_cause": "minimax-credential-missing",
            "provider_attempts": 0,
            "provider_diagnostics": {
                "category": "credential-missing",
                "http_status_class": None,
                "api_key_env": api_key_env,
                "attempted_http": False,
            },
            "response_shape": {
                "status": "blocked-credential",
                "root_cause": "minimax-credential-missing",
                "has_choices": False,
                "choice_count": 0,
                "has_message": False,
                "has_content": False,
                "content_kind": "not-run",
                "candidate_prefix": None,
                "has_think_tag": False,
                "has_reasoning_details": False,
                "reasoning_details_count": 0,
                "reasoning_detail_types": [],
            },
        }
    )
    return payload


def http_status_class(status_code: int | None) -> str | None:
    if status_code is None:
        return None
    return f"{status_code // 100}xx"


def classify_http_error(status_code: int) -> str:
    if status_code in {401, 403}:
        return "minimax-auth-failed"
    if status_code == 429:
        return "minimax-rate-limited"
    if 400 <= status_code < 500:
        return "minimax-http-4xx"
    if 500 <= status_code < 600:
        return "minimax-http-5xx"
    return "minimax-provider-error"


def make_provider_request(
    *,
    url: str,
    api_key: str,
    body: dict[str, Any],
    timeout: int,
    urlopen: UrlOpen = request.urlopen,
) -> dict[str, Any]:
    """POST once to the provider and return categorical diagnostics plus decoded JSON."""
    data = json.dumps(body).encode("utf-8")
    provider_request = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urlopen(provider_request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", getattr(response, "code", 200)))
            raw_body = response.read()
    except error.HTTPError as exc:
        return {
            "ok": False,
            "status_code": exc.code,
            "root_cause": classify_http_error(exc.code),
            "provider_diagnostics": {
                "category": classify_http_error(exc.code),
                "http_status_class": http_status_class(exc.code),
                "attempted_http": True,
            },
            "decoded": None,
        }
    except TimeoutError:
        return timeout_result()
    except socket.timeout:
        return timeout_result()
    except OSError as exc:
        if "timed out" in str(exc).lower():
            return timeout_result()
        return {
            "ok": False,
            "status_code": None,
            "root_cause": "minimax-provider-error",
            "provider_diagnostics": {
                "category": "transport-error",
                "http_status_class": None,
                "attempted_http": True,
            },
            "decoded": None,
        }

    try:
        decoded = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "ok": False,
            "status_code": status_code,
            "root_cause": "provider-schema-mismatch",
            "provider_diagnostics": {
                "category": "invalid-json",
                "http_status_class": http_status_class(status_code),
                "attempted_http": True,
            },
            "decoded": None,
        }

    return {
        "ok": True,
        "status_code": status_code,
        "root_cause": None,
        "provider_diagnostics": {
            "category": "http-success",
            "http_status_class": http_status_class(status_code),
            "attempted_http": True,
        },
        "decoded": decoded,
    }


def timeout_result() -> dict[str, Any]:
    return {
        "ok": False,
        "status_code": None,
        "root_cause": "provider-timeout",
        "provider_diagnostics": {
            "category": "timeout",
            "http_status_class": None,
            "attempted_http": True,
        },
        "decoded": None,
    }


def build_live_payload(
    *,
    model: str,
    base_url: str,
    timeout: int,
    api_key_env: str,
    environ: dict[str, str] | os._Environ[str] = os.environ,
    urlopen: UrlOpen = request.urlopen,
) -> tuple[dict[str, Any], list[str]]:
    api_key = environ.get(api_key_env, "")
    if not api_key:
        return build_missing_credential_payload(model=model, base_url=base_url, api_key_env=api_key_env), []

    payload = base_payload(model=model, base_url=base_url)
    request_body = build_request_body(model=model, user_prompt=SAFE_CYPHER_PROMPT)
    endpoint = cast("dict[str, Any]", payload["endpoint"])
    result = make_provider_request(
        url=cast("str", endpoint["effective_url"]),
        api_key=api_key,
        body=request_body,
        timeout=timeout,
        urlopen=urlopen,
    )

    response_shape = classify_response_shape(result["decoded"]) if result["decoded"] is not None else {
        "status": "failed-runtime",
        "root_cause": result["root_cause"],
        "has_choices": False,
        "choice_count": 0,
        "has_message": False,
        "has_content": False,
        "content_kind": "missing",
        "candidate_prefix": None,
        "has_think_tag": False,
        "has_reasoning_details": False,
        "reasoning_details_count": 0,
        "reasoning_detail_types": [],
    }
    status = response_shape["status"] if result["ok"] else "failed-runtime"
    root_cause = response_shape["root_cause"] if result["ok"] else result["root_cause"]
    if status == "confirmed-runtime" and not all(
        [
            endpoint.get("effective_url"),
            endpoint.get("preserves_v1") is True,
            model,
            request_body.get("reasoning_split") is True,
            result["provider_diagnostics"].get("attempted_http") is True,
            response_shape.get("has_content") is True,
            response_shape.get("candidate_prefix") in {"MATCH", "CALL"},
            response_shape.get("has_think_tag") is False,
        ]
    ):
        status = "failed-runtime"
        root_cause = "provider-schema-mismatch"
        response_shape["status"] = status
        response_shape["root_cause"] = root_cause

    payload.update(
        {
            "status": status,
            "root_cause": root_cause,
            "provider_attempts": 1,
            "request_body": request_body,
            "provider_diagnostics": result["provider_diagnostics"],
            "response_shape": response_shape,
        }
    )
    return payload, [api_key]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--output-dir", type=Path, help="Deprecated alias for --artifact-dir")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifact_dir = args.output_dir if args.output_dir is not None else args.artifact_dir
    payload, sensitive_values = build_live_payload(
        model=args.model,
        base_url=args.base_url,
        timeout=args.timeout,
        api_key_env=args.api_key_env,
    )
    json_path, markdown_path = write_artifacts(artifact_dir, payload, sensitive_values=sensitive_values)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "root_cause": payload["root_cause"],
                "provider_attempts": payload["provider_attempts"],
                "json_artifact": str(json_path),
                "markdown_artifact": str(markdown_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
