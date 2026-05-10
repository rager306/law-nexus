#!/usr/bin/env python3
"""M003/S03 live MiniMax reasoning-safe generated-Cypher candidate proof harness.

The harness builds a generated PyO3/Rust module that exposes endpoint resolver
metadata and, when credentials are present, performs exactly one MiniMax
OpenAI-compatible chat completion request with top-level ``reasoning_split=true``.
Only the in-memory safe provider summary is routed into the local classifier.
Durable artifacts keep endpoint/build/import/provider phases, attempt counts,
classification diagnostics, and redaction booleans; they never persist prompts,
credentials, auth headers, raw provider bodies, raw reasoning text, raw legal
text, or raw graph rows. This slice does not validate or execute Cypher.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s03-reasoning-safe-candidate/v2"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_ENDPOINT = "https://api.minimax.io/v1"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_CREDENTIAL_ENV = "MINIMAX_API_KEY"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S03"
DEFAULT_RUNTIME_DIR = ROOT / ".gsd/runtime-smoke/reasoning-safe-candidate"
MODULE_NAME = "m003_s03_reasoning_safe_candidate"
JSON_ARTIFACT = "S03-REASONING-SAFE-CANDIDATE.json"
MARKDOWN_ARTIFACT = "S03-REASONING-SAFE-CANDIDATE.md"
SUPPORTED_ENDPOINT_HOST = "api.minimax.io"

Status = Literal["blocked-credential", "blocked-environment", "failed-runtime", "confirmed-runtime"]

STATUS_CATEGORIES = (
    "blocked-credential",
    "blocked-environment",
    "failed-runtime",
    "confirmed-runtime",
)
ROOT_CAUSE_CATEGORIES = (
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
)
PHASE_CATEGORIES = (
    "credential-check",
    "endpoint-contract",
    "build",
    "import",
    "resolver",
    "provider-response",
    "candidate-classification",
    "artifact-redaction",
)

FORBIDDEN_ARTIFACT_TERMS = (
    "Authorization",
    "Bearer",
    "api_key",
    "api-key",
    "sk-",
    "BEGIN PRIVATE KEY",
    "RAW_LEGAL_TEXT_SENTINEL",
    "raw_provider_body_value",
    "raw_response",
    "request_prompt",
    "reasoning_text_value",
    "raw_legal_text_value",
    "falkordb_rows_value",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"RAW_LEGAL_TEXT_SENTINEL[^\n\r\t,;}]*"),
)

BOUNDARY_STATEMENT = (
    "This artifact proves only S03 endpoint/request wiring and reasoning-safe candidate "
    "classification for MiniMax-shaped output. It does not prove provider generation quality, "
    "Legal KnowQL product behavior, legal-answer correctness, M002 validation, graph execution, "
    "ODT parsing, retrieval quality, or production graph schema fitness. Raw provider bodies, "
    "credentials, prompts, raw reasoning, raw legal text, and raw graph rows are not persisted."
)
PROSE_SUFFIX_MARKERS = (
    "this ",
    "these ",
    "the query ",
    "it ",
    "here ",
    "explanation",
    "because ",
    "note:",
)


@dataclass(frozen=True)
class StreamSummary:
    line_count: int
    char_count: int
    redacted_tail: str
    contains_secret_pattern: bool


@dataclass(frozen=True)
class CommandResult:
    phase: str
    command: list[str]
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout_summary: StreamSummary
    stderr_summary: StreamSummary
    log_path: str | None


@dataclass
class ProofState:
    runtime_dir: Path
    workspace_dir: Path
    log_dir: Path
    timeout_seconds: int
    sensitive_values: list[str] = field(default_factory=list)
    commands: list[CommandResult] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


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


def summarize_stream(text: str, *, sensitive_values: list[str] | None = None) -> StreamSummary:
    contains_secret = any(pattern.search(text) for pattern in SECRET_PATTERNS)
    redacted = redact(text, sensitive_values=sensitive_values)
    return StreamSummary(
        line_count=0 if not text else len(text.splitlines()),
        char_count=len(text),
        redacted_tail=redacted[-500:],
        contains_secret_pattern=contains_secret,
    )


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
            if lowered in {"authorization", "api_key", "api-key", "token", "secret", "password"}:
                sanitized[str(key)] = "<redacted>"
            else:
                sanitized[str(key)] = sanitize(item, sensitive_values=sensitive_values)
        return sanitized
    return value


def _invalid_endpoint(endpoint_input: str, reason: str) -> dict[str, Any]:
    return {
        "endpoint_input": endpoint_input,
        "normalized_base_url": None,
        "effective_chat_completions_url": None,
        "preserves_v1": False,
        "normalization_applied": False,
        "normalization_status": "invalid",
        "root_cause": "invalid-endpoint",
        "invalid_endpoint_reason": reason,
        "endpoint_contract_valid": False,
        "model": DEFAULT_MODEL,
    }


def normalize_minimax_endpoint(endpoint: str) -> dict[str, Any]:
    endpoint_input = endpoint
    stripped = endpoint.strip()
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
    suffix = segments[1:]
    if suffix not in ([], ["chat", "completions"]):
        return _invalid_endpoint(endpoint_input, "unsupported-path")
    normalized_base_url = urlunsplit(("https", SUPPORTED_ENDPOINT_HOST, "/v1/", "", ""))
    effective_url = urlunsplit(("https", SUPPORTED_ENDPOINT_HOST, "/v1/chat/completions", "", ""))
    return {
        "endpoint_input": endpoint_input,
        "normalized_base_url": normalized_base_url,
        "effective_chat_completions_url": effective_url,
        "preserves_v1": True,
        "normalization_applied": stripped != normalized_base_url,
        "normalization_status": "normalized" if stripped != normalized_base_url else "already-normalized",
        "root_cause": "none",
        "invalid_endpoint_reason": None,
        "endpoint_contract_valid": True,
        "model": DEFAULT_MODEL,
    }


# Backward-compatible T01 name.
def compose_endpoint_metadata(endpoint: str) -> dict[str, Any]:
    return normalize_minimax_endpoint(endpoint)


def build_minimax_chat_request(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "stream": False,
        "reasoning_split": True,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return exactly one read-only Cypher candidate and no prose, markdown fences, "
                    "comments, examples, or raw legal text. Keep reasoning separated by the provider."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Generate one synthetic LegalGraph-shaped read-only query using EvidenceSpan, "
                    "Article, SourceBlock, SUPPORTS, SUPPORTED_BY, IN_BLOCK, $article_id, $as_of, "
                    "and LIMIT 5. Return only the Cypher text."
                ),
            },
        ],
    }


def request_diagnostics(model: str) -> dict[str, Any]:
    body = build_minimax_chat_request(model)
    return {
        "model": model,
        "stream": body["stream"],
        "reasoning_split": body["reasoning_split"],
        "message_count": len(body["messages"]),
        "prompt_text_persisted": False,
    }


def _message_from_provider_shape(decoded: object) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    choices = decoded.get("choices") if isinstance(decoded, dict) else None
    shape = {
        "has_choices": isinstance(choices, list),
        "choice_count": len(choices) if isinstance(choices, list) else 0,
        "has_message": False,
    }
    if not isinstance(choices, list) or not choices:
        return None, shape
    first = choices[0]
    if not isinstance(first, dict):
        return None, shape
    message = first.get("message")
    if not isinstance(message, dict):
        return None, shape
    shape["has_message"] = True
    return cast("dict[str, Any]", message), shape


def _reasoning_summary(message: dict[str, Any] | None) -> dict[str, Any]:
    if message is None:
        return {
            "present": False,
            "separated": False,
            "detail_count": 0,
            "detail_types": [],
            "raw_text_persisted": False,
        }
    details = message.get("reasoning_details")
    content = message.get("reasoning_content")
    present = details is not None or content is not None
    detail_types: list[str] = []
    detail_count = 0
    if isinstance(details, list):
        detail_count = len(details)
        for item in details:
            if isinstance(item, dict) and isinstance(item.get("type"), str):
                detail_types.append(item["type"])
            else:
                detail_types.append(type(item).__name__)
    elif details is not None:
        detail_count = 1
        detail_types.append(type(details).__name__)
    elif content is not None:
        detail_count = 1
        detail_types.append("reasoning_content")
    return {
        "present": present,
        "separated": present,
        "detail_count": detail_count,
        "detail_types": detail_types,
        "raw_text_persisted": False,
    }


def _safe_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _has_comment(text: str) -> bool:
    return "//" in text or "/*" in text or "*/" in text or any(line.lstrip().startswith("--") for line in text.splitlines())


def _has_multi_statement(text: str) -> bool:
    stripped = text.strip()
    if ";" not in stripped:
        return False
    without_final = stripped[:-1] if stripped.endswith(";") else stripped
    return ";" in without_final or not stripped.endswith(";")


def _has_prose_suffix(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    for line in lines[1:]:
        lowered = line.lower()
        if lowered.startswith(PROSE_SUFFIX_MARKERS):
            return True
        if not lowered.startswith(("match ", "call ", "where ", "return ", "with ", "yield ", "limit ", "order ", "and ", "or ", ",", "(")):
            return True
    return False


def classify_candidate_text(content: object) -> dict[str, Any]:
    """Classify candidate text using only whitespace trim before acceptance."""
    if not isinstance(content, str):
        return {
            "accepted": False,
            "root_cause": "provider-schema-mismatch",
            "status": "failed-runtime",
            "starts_with": None,
            "categories": ["malformed-provider-shape"],
            "text_length": 0,
            "trimmed_length": 0,
            "sha256_12": None,
            "has_think_tag": False,
            "has_markdown_fence": False,
            "has_prose_prefix": False,
            "has_prose_suffix": False,
            "has_comment": False,
            "has_multi_statement": False,
            "raw_provider_body_persisted": False,
        }

    stripped = content.strip()
    lowered = stripped.lower()
    starts_with = "MATCH" if stripped.upper().startswith("MATCH") else "CALL" if stripped.upper().startswith("CALL") else "OTHER"
    has_think_tag = "<think" in lowered or "</think" in lowered
    has_markdown_fence = "```" in stripped
    has_prose_prefix = (
        bool(stripped)
        and starts_with == "OTHER"
        and not has_markdown_fence
        and not has_think_tag
        and ("match" in lowered or "call" in lowered or ":" in stripped or len(stripped.split()) > 1)
    )
    has_prose_suffix = starts_with in {"MATCH", "CALL"} and _has_prose_suffix(stripped)
    has_comment = _has_comment(stripped)
    has_multi_statement = _has_multi_statement(stripped)

    categories: list[str] = []
    root_cause = "none"
    if not stripped:
        root_cause = "empty-content"
        categories.append("malformed-content")
    elif has_think_tag:
        root_cause = "reasoning-contamination"
        categories.append("reasoning-tag-contamination")
    elif has_markdown_fence:
        root_cause = "markdown-contamination"
        categories.append("markdown-fence-contamination")
    elif starts_with == "OTHER":
        root_cause = "non-cypher-output"
        categories.append("prose-prefix" if has_prose_prefix else "non-cypher")
    elif has_prose_suffix:
        root_cause = "prose-contamination"
        categories.append("prose-suffix")
    elif has_comment:
        root_cause = "candidate-comment-contamination"
        categories.append("comment-contamination")
    elif has_multi_statement:
        root_cause = "candidate-multi-statement"
        categories.append("multi-statement")

    accepted = root_cause == "none"
    diagnostics: dict[str, Any] = {
        "accepted": accepted,
        "root_cause": root_cause,
        "status": "confirmed-runtime" if accepted else "failed-runtime",
        "starts_with": starts_with if starts_with in {"MATCH", "CALL"} else "OTHER",
        "categories": categories,
        "text_length": len(content),
        "trimmed_length": len(stripped),
        "sha256_12": _safe_hash(stripped) if stripped else None,
        "has_think_tag": has_think_tag,
        "has_markdown_fence": has_markdown_fence,
        "has_prose_prefix": has_prose_prefix,
        "has_prose_suffix": has_prose_suffix,
        "has_comment": has_comment,
        "has_multi_statement": has_multi_statement,
        "raw_provider_body_persisted": False,
    }
    if accepted:
        diagnostics["normalized_text"] = stripped
    return diagnostics


def classify_provider_response(decoded: object) -> dict[str, Any]:
    """Classify an OpenAI-compatible provider-shaped object without persisting raw bodies."""
    message, shape = _message_from_provider_shape(decoded)
    reasoning = _reasoning_summary(message)
    if message is None:
        candidate = classify_candidate_text(None)
        candidate["categories"] = ["malformed-provider-shape"]
        return {
            "accepted": False,
            "status": "failed-runtime",
            "root_cause": "provider-schema-mismatch",
            "phase": "provider-response",
            "provider_shape": shape,
            "candidate": candidate,
            "reasoning": reasoning,
        }

    content = message.get("content")
    candidate = classify_candidate_text(content)
    if not isinstance(content, str):
        candidate["categories"] = ["malformed-provider-shape"]
    return {
        "accepted": bool(candidate["accepted"]),
        "status": candidate["status"],
        "root_cause": candidate["root_cause"],
        "phase": "candidate-classification" if candidate["accepted"] else "provider-response",
        "provider_shape": {**shape, "has_content": isinstance(content, str), "content_kind": "string" if isinstance(content, str) else type(content).__name__},
        "candidate": candidate,
        "reasoning": reasoning,
    }


def classify_safe_provider_summary(summary: object) -> dict[str, Any]:
    """Route a generated Rust safe summary into the T01 provider classifier."""
    if not isinstance(summary, dict):
        return classify_provider_response({})
    if summary.get("status") == "timeout":
        classification = classify_provider_response({})
        classification["root_cause"] = "provider-timeout"
        classification["candidate"]["root_cause"] = "provider-timeout"
        return classification
    message = summary.get("message")
    if not isinstance(message, dict):
        return classify_provider_response({})
    safe_diagnostics = summary.get("safe_diagnostics") if isinstance(summary.get("safe_diagnostics"), dict) else {}
    if safe_diagnostics.get("raw_provider_body_persisted") is not False:
        classification = classify_provider_response({})
        classification["root_cause"] = "redaction-violation"
        classification["candidate"]["root_cause"] = "redaction-violation"
        return classification
    return classify_provider_response({"choices": [{"message": message}]})


def boundary_payload() -> dict[str, list[str]]:
    return {
        "proves": [
            "generated PyO3/Rust route exposes endpoint and resolver metadata",
            "live provider request body uses top-level reasoning_split=true",
            "local classification separates reasoning metadata from candidate text",
            "accepted candidate text starts with MATCH or CALL after whitespace trim only",
            "contamination categories are emitted before downstream validation or execution",
        ],
        "does_not_prove": [
            "provider generation quality",
            "Legal KnowQL product behavior",
            "legal-answer correctness",
            "M002 validation acceptance",
            "graph execution",
            "ODT parsing",
            "retrieval quality",
            "production graph schema fitness",
        ],
        "safety": [
            "raw provider bodies are not persisted",
            "credential-bearing values and authorization material are not persisted",
            "request text, raw reasoning text, raw legal text, and raw graph rows are not persisted",
            "rejected candidate text is represented only by categories, lengths, booleans, and hashes",
        ],
    }


def base_artifact(
    *,
    status: Status,
    root_cause: str,
    phase: str,
    provider_attempts: int,
    endpoint_metadata: dict[str, Any] | None = None,
    resolver_metadata: dict[str, Any] | None = None,
    commands: list[dict[str, Any]] | None = None,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    runtime_workspace: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": status,
        "root_cause": root_cause,
        "phase": phase,
        "status_categories": list(STATUS_CATEGORIES),
        "root_cause_categories": list(ROOT_CAUSE_CATEGORIES),
        "phase_categories": list(PHASE_CATEGORIES),
        "provider_attempts": provider_attempts,
        "model": model,
        "timeout_seconds": timeout_seconds,
        "endpoint": endpoint_metadata or normalize_minimax_endpoint(DEFAULT_ENDPOINT),
        "resolver": resolver_metadata
        or {
            "route": "generated PyO3/Rust MiniMax OpenAI-compatible route",
            "adapter_kind": "OpenAI",
            "metadata_persisted": "categorical-only",
        },
        "request": request_diagnostics(model),
        "runtime_workspace": runtime_workspace,
        "commands": commands or [],
        "safety": {
            "raw_provider_body_persisted": False,
            "credential_persisted": False,
            "auth_header_persisted": False,
            "request_text_persisted": False,
            "raw_reasoning_text_persisted": False,
            "raw_legal_text_persisted": False,
            "raw_graph_rows_persisted": False,
        },
        "boundaries": boundary_payload(),
        "non_claims": boundary_payload()["does_not_prove"],
    }


def build_blocked_credential_artifact(
    *,
    endpoint_metadata: dict[str, Any] | None = None,
    resolver_metadata: dict[str, Any] | None = None,
    commands: list[dict[str, Any]] | None = None,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    runtime_workspace: str | None = None,
) -> dict[str, Any]:
    artifact = base_artifact(
        status="blocked-credential",
        root_cause="minimax-credential-missing",
        phase="credential-check",
        provider_attempts=0,
        endpoint_metadata=endpoint_metadata,
        resolver_metadata=resolver_metadata,
        commands=commands,
        model=model,
        timeout_seconds=timeout_seconds,
        runtime_workspace=runtime_workspace,
    )
    artifact.update(
        {
            "candidate": classify_candidate_text("") | {"categories": ["not-run"]},
            "reasoning": _reasoning_summary(None),
            "credential": {"present": False, "name_persisted": False},
        }
    )
    assert_safe_artifact(artifact)
    return artifact


def build_failed_runtime_artifact(
    *,
    root_cause: str,
    phase: str,
    classification: dict[str, Any],
    provider_attempts: int,
    commands: list[dict[str, Any]] | None = None,
    endpoint_metadata: dict[str, Any] | None = None,
    resolver_metadata: dict[str, Any] | None = None,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    runtime_workspace: str | None = None,
) -> dict[str, Any]:
    artifact = base_artifact(
        status="failed-runtime",
        root_cause=root_cause,
        phase=phase,
        provider_attempts=provider_attempts,
        endpoint_metadata=endpoint_metadata,
        resolver_metadata=resolver_metadata,
        commands=commands,
        model=model,
        timeout_seconds=timeout_seconds,
        runtime_workspace=runtime_workspace,
    )
    artifact.update(
        {
            "candidate": classification.get("candidate", classify_candidate_text(None)),
            "reasoning": classification.get("reasoning", _reasoning_summary(None)),
            "provider_shape": classification.get("provider_shape", {}),
        }
    )
    artifact["candidate"].pop("normalized_text", None)
    assert_safe_artifact(artifact)
    return artifact


def build_confirmed_runtime_artifact(
    *,
    classification: dict[str, Any],
    provider_attempts: int,
    commands: list[dict[str, Any]] | None = None,
    endpoint_metadata: dict[str, Any] | None = None,
    resolver_metadata: dict[str, Any] | None = None,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    runtime_workspace: str | None = None,
) -> dict[str, Any]:
    if not classification.get("accepted"):
        raise ValueError("confirmed runtime requires an accepted classification")
    artifact = base_artifact(
        status="confirmed-runtime",
        root_cause="none",
        phase="candidate-classification",
        provider_attempts=provider_attempts,
        endpoint_metadata=endpoint_metadata,
        resolver_metadata=resolver_metadata,
        commands=commands,
        model=model,
        timeout_seconds=timeout_seconds,
        runtime_workspace=runtime_workspace,
    )
    artifact.update(
        {
            "candidate": classification["candidate"],
            "reasoning": classification["reasoning"],
            "provider_shape": classification.get("provider_shape", {}),
        }
    )
    assert_safe_artifact(artifact)
    return artifact


def assert_safe_artifact(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError("refusing to write secret-like artifact content")
    for term in FORBIDDEN_ARTIFACT_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden artifact term: {term}")
    if "normalized_text" in payload.get("candidate", {}) and payload.get("status") != "confirmed-runtime":
        raise ValueError("rejected candidates must not persist normalized_text")


def write_log(
    log_dir: Path,
    phase: str,
    stdout: str,
    stderr: str,
    *,
    sensitive_values: list[str],
    persist_raw: bool,
) -> str | None:
    if not persist_raw:
        return None
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{phase}.log"
    content = (
        f"# phase: {phase}\n\n"
        f"## stdout\n{redact(stdout, sensitive_values=sensitive_values)}\n\n"
        f"## stderr\n{redact(stderr, sensitive_values=sensitive_values)}\n"
    )
    path.write_text(content, encoding="utf-8")
    return normalized_path(path)


def run_command(
    command: list[str],
    *,
    cwd: Path,
    state: ProofState,
    phase: str,
    env: dict[str, str] | None = None,
    persist_raw_log: bool = True,
) -> CommandResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=state.timeout_seconds,
            check=False,
            env=env,
        )
        timed_out = False
        exit_code: int | None = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        stderr = f"{stderr}\nTIMEOUT after {state.timeout_seconds}s".strip()
    duration_ms = int((time.monotonic() - started) * 1000)
    log_path = write_log(
        state.log_dir,
        phase,
        stdout,
        stderr,
        sensitive_values=state.sensitive_values,
        persist_raw=persist_raw_log,
    )
    result = CommandResult(
        phase=phase,
        command=command,
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=duration_ms,
        stdout_summary=summarize_stream(stdout, sensitive_values=state.sensitive_values),
        stderr_summary=summarize_stream(stderr, sensitive_values=state.sensitive_values),
        log_path=log_path,
    )
    state.commands.append(result)
    return result


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def command_phase_payload(result: CommandResult, *, include_stream_tails: bool = True) -> dict[str, Any]:
    payload = {
        "phase": result.phase,
        "command": result.command,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "duration_ms": result.duration_ms,
        "log_path": result.log_path,
    }
    if include_stream_tails:
        payload["stdout_summary"] = asdict(result.stdout_summary)
        payload["stderr_summary"] = asdict(result.stderr_summary)
    else:
        payload["stdout_summary"] = {
            "line_count": result.stdout_summary.line_count,
            "char_count": result.stdout_summary.char_count,
            "redacted_tail": "<omitted-provider-output>",
            "contains_secret_pattern": result.stdout_summary.contains_secret_pattern,
        }
        payload["stderr_summary"] = {
            "line_count": result.stderr_summary.line_count,
            "char_count": result.stderr_summary.char_count,
            "redacted_tail": "<omitted-provider-output>",
            "contains_secret_pattern": result.stderr_summary.contains_secret_pattern,
        }
    return payload


def parse_json_tail(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    last_line = stripped.splitlines()[-1]
    try:
        parsed = json.loads(last_line)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def create_proof_project(workspace_dir: Path, endpoint_metadata: dict[str, Any]) -> Path:
    project_dir = workspace_dir / "reasoning_safe_candidate"
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "Cargo.toml").write_text(
        textwrap.dedent(
            f"""
            [package]
            name = "{MODULE_NAME}"
            version = "0.1.0"
            edition = "2024"
            publish = false

            [lib]
            name = "{MODULE_NAME}"
            crate-type = ["cdylib"]

            [dependencies]
            pyo3 = {{ version = "0.27", features = ["extension-module"] }}
            reqwest = {{ version = "0.12", default-features = false, features = ["json", "rustls-tls"] }}
            serde_json = "1"
            tokio = {{ version = "1", features = ["rt-multi-thread", "time"] }}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [build-system]
            requires = ["maturin>=1.0,<2.0"]
            build-backend = "maturin"

            [project]
            name = "m003-s03-reasoning-safe-candidate"
            version = "0.1.0"
            requires-python = ">=3.13"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (src_dir / "lib.rs").write_text(
        rust_source(
            normalized_endpoint=cast(str, endpoint_metadata["normalized_base_url"]),
            effective_endpoint=cast(str, endpoint_metadata["effective_chat_completions_url"]),
        ),
        encoding="utf-8",
    )
    return project_dir


def rust_source(*, normalized_endpoint: str, effective_endpoint: str) -> str:
    request_body = json.dumps(build_minimax_chat_request(DEFAULT_MODEL), ensure_ascii=False)
    return (
        textwrap.dedent(
            f'''
            use pyo3::prelude::*;
            use reqwest::header::{{AUTHORIZATION, CONTENT_TYPE}};
            use serde_json::{{json, Value}};
            use std::env;
            use std::time::Duration;

            const DEFAULT_MINIMAX_MODEL: &str = "{DEFAULT_MODEL}";
            const NORMALIZED_MINIMAX_ENDPOINT: &str = "{normalized_endpoint}";
            const EFFECTIVE_CHAT_COMPLETIONS_URL: &str = "{effective_endpoint}";
            const REQUEST_BODY_JSON: &str = r#"{request_body}"#;

            fn safe_reasoning_details(message: &Value) -> Value {{
                if let Some(details) = message.get("reasoning_details").and_then(|v| v.as_array()) {{
                    let safe: Vec<Value> = details.iter().map(|item| {{
                        let detail_type = item.get("type").and_then(|v| v.as_str()).unwrap_or("unknown");
                        let text_len = item.get("text").and_then(|v| v.as_str()).map(|s| s.len()).unwrap_or(0);
                        json!({{"type": detail_type, "text_length": text_len}})
                    }}).collect();
                    return Value::Array(safe);
                }}
                if let Some(reasoning) = message.get("reasoning_content").and_then(|v| v.as_str()) {{
                    if !reasoning.is_empty() {{
                        return json!([{{"type": "reasoning_content", "text_length": reasoning.len()}}]);
                    }}
                }}
                Value::Null
            }}

            #[pyfunction]
            fn binding_metadata() -> PyResult<String> {{
                let body: Value = serde_json::from_str(REQUEST_BODY_JSON)
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                Ok(json!({{
                    "module": "{MODULE_NAME}",
                    "model": DEFAULT_MINIMAX_MODEL,
                    "adapter_kind": "OpenAI",
                    "normalized_endpoint_base_url": NORMALIZED_MINIMAX_ENDPOINT,
                    "effective_chat_completions_url": EFFECTIVE_CHAT_COMPLETIONS_URL,
                    "provider_body_persistence": "disabled",
                    "request_body_reasoning_split": body.get("reasoning_split").and_then(|v| v.as_bool()).unwrap_or(false)
                }}).to_string())
            }}

            #[pyfunction]
            fn resolve_target_metadata(model: String) -> PyResult<String> {{
                Ok(json!({{
                    "module": "{MODULE_NAME}",
                    "model": model,
                    "adapter_kind": "OpenAI",
                    "normalized_endpoint_base_url": NORMALIZED_MINIMAX_ENDPOINT,
                    "effective_chat_completions_url": EFFECTIVE_CHAT_COMPLETIONS_URL,
                    "provider_body_persistence": "disabled",
                    "request_body_reasoning_split": true
                }}).to_string())
            }}

            #[pyfunction]
            fn run_live_reasoning_split_once(model: String, credential_env: String, timeout_seconds: u64) -> PyResult<String> {{
                let credential = env::var(&credential_env)
                    .map_err(|_| pyo3::exceptions::PyRuntimeError::new_err("credential environment variable is unavailable"))?;
                let mut body: Value = serde_json::from_str(REQUEST_BODY_JSON)
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                body["model"] = Value::String(model);

                let runtime = tokio::runtime::Runtime::new()
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                let result: Result<Value, String> = runtime.block_on(async {{
                    let client = reqwest::Client::builder()
                        .timeout(Duration::from_secs(timeout_seconds))
                        .build()
                        .map_err(|err| err.to_string())?;
                    let response = client
                        .post(EFFECTIVE_CHAT_COMPLETIONS_URL)
                        .header(AUTHORIZATION, format!("Bearer {{}}", credential))
                        .header(CONTENT_TYPE, "application/json")
                        .json(&body)
                        .send()
                        .await
                        .map_err(|err| err.to_string())?;
                    let status = response.status().as_u16();
                    let decoded: Value = response.json().await.map_err(|err| err.to_string())?;
                    if !(200..300).contains(&status) {{
                        return Ok(json!({{
                            "status": "provider-http-error",
                            "http_status": status,
                            "safe_diagnostics": {{
                                "raw_provider_body_persisted": false,
                                "raw_reasoning_text_persisted": false
                            }}
                        }}));
                    }}
                    let message = decoded
                        .get("choices")
                        .and_then(|v| v.as_array())
                        .and_then(|choices| choices.first())
                        .and_then(|choice| choice.get("message"))
                        .cloned()
                        .unwrap_or(Value::Null);
                    let content = message.get("content").and_then(|v| v.as_str()).unwrap_or("");
                    let reasoning_details = safe_reasoning_details(&message);
                    Ok(json!({{
                        "status": "provider-response-received",
                        "message": {{
                            "content": content,
                            "reasoning_details": reasoning_details
                        }},
                        "safe_diagnostics": {{
                            "raw_provider_body_persisted": false,
                            "raw_reasoning_text_persisted": false
                        }}
                    }}))
                }});
                match result {{
                    Ok(value) => Ok(value.to_string()),
                    Err(err) => Err(pyo3::exceptions::PyRuntimeError::new_err(err)),
                }}
            }}

            #[pymodule]
            fn {MODULE_NAME}(m: &Bound<'_, PyModule>) -> PyResult<()> {{
                m.add_function(wrap_pyfunction!(binding_metadata, m)?)?;
                m.add_function(wrap_pyfunction!(resolve_target_metadata, m)?)?;
                m.add_function(wrap_pyfunction!(run_live_reasoning_split_once, m)?)?;
                Ok(())
            }}
            '''
        ).strip()
        + "\n"
    )


def import_probe_code(model: str) -> str:
    return textwrap.dedent(
        f"""
        import json
        import {MODULE_NAME} as proof

        metadata = json.loads(proof.binding_metadata())
        target = json.loads(proof.resolve_target_metadata({model!r}))
        assert metadata["adapter_kind"] == "OpenAI"
        assert target["adapter_kind"] == "OpenAI"
        assert metadata["request_body_reasoning_split"] is True
        assert target["request_body_reasoning_split"] is True
        print(json.dumps(target, sort_keys=True))
        """
    ).strip()


def provider_probe_code(model: str, credential_env: str, timeout_seconds: int) -> str:
    return textwrap.dedent(
        f"""
        import json
        import {MODULE_NAME} as proof

        payload = json.loads(proof.run_live_reasoning_split_once({model!r}, {credential_env!r}, {timeout_seconds!r}))
        print(json.dumps(payload, sort_keys=True))
        """
    ).strip()


def validate_resolver_metadata(metadata: dict[str, Any], *, endpoint_metadata: dict[str, Any], model: str) -> dict[str, Any]:
    ok = True
    root_cause = "none"
    if metadata.get("module") != MODULE_NAME:
        ok = False
        root_cause = "resolver-metadata-malformed"
    elif metadata.get("model") != model:
        ok = False
        root_cause = "resolver-metadata-malformed"
    elif metadata.get("adapter_kind") != "OpenAI":
        ok = False
        root_cause = "resolver-metadata-malformed"
    elif metadata.get("provider_body_persistence") != "disabled":
        ok = False
        root_cause = "resolver-metadata-malformed"
    elif metadata.get("request_body_reasoning_split") is not True:
        ok = False
        root_cause = "resolver-metadata-malformed"
    elif metadata.get("normalized_endpoint_base_url") != endpoint_metadata.get("normalized_base_url"):
        ok = False
        root_cause = "endpoint-contract-lost-v1"
    elif metadata.get("effective_chat_completions_url") != endpoint_metadata.get("effective_chat_completions_url"):
        ok = False
        root_cause = "endpoint-contract-lost-v1"

    return {
        "phase": "resolver",
        "status": "confirmed-runtime" if ok else "blocked-environment",
        "root_cause": root_cause,
        "metadata": metadata if ok else sanitize(metadata),
    }


def classify_provider_failure(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("timeout", "timed out", "deadline")):
        return "provider-timeout"
    if any(token in lowered for token in ("401", "403", "unauthorized", "forbidden", "invalid")):
        return "provider-http-error"
    if any(token in lowered for token in ("schema", "choices", "deserialize", "json", "missing field")):
        return "provider-schema-mismatch"
    return "provider-http-error"


def run_proof(
    *,
    model: str = DEFAULT_MODEL,
    endpoint: str = DEFAULT_ENDPOINT,
    credential_env: str = DEFAULT_CREDENTIAL_ENV,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    artifact_dir: Path | None = DEFAULT_ARTIFACT_DIR,
    runtime_dir: Path | None = DEFAULT_RUNTIME_DIR,
    keep_workspace: bool = False,
) -> dict[str, Any]:
    endpoint_metadata = normalize_minimax_endpoint(endpoint)
    provider_attempts = 0
    commands: list[dict[str, Any]] = []
    resolver_metadata: dict[str, Any] | None = None
    project_dir: Path | None = None
    runtime_workspace: str | None = None

    if not endpoint_metadata["endpoint_contract_valid"]:
        classification = classify_provider_response({})
        payload = build_failed_runtime_artifact(
            root_cause="invalid-endpoint",
            phase="endpoint-contract",
            classification=classification,
            provider_attempts=0,
            endpoint_metadata=endpoint_metadata,
            commands=[],
            model=model,
            timeout_seconds=timeout_seconds,
        )
        if artifact_dir is not None:
            write_artifacts(artifact_dir, payload)
        return payload

    actual_runtime_dir = runtime_dir or DEFAULT_RUNTIME_DIR
    actual_runtime_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = actual_runtime_dir / "workspace"
    if workspace_dir.exists() and not keep_workspace:
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    runtime_workspace = normalized_path(workspace_dir)
    credential_value = os.environ.get(credential_env, "")
    state = ProofState(
        runtime_dir=actual_runtime_dir,
        workspace_dir=workspace_dir,
        log_dir=actual_runtime_dir / "logs",
        timeout_seconds=timeout_seconds,
        sensitive_values=[credential_value] if credential_value else [],
    )

    if not command_available("uvx"):
        classification = classify_provider_response({})
        payload = build_failed_runtime_artifact(
            root_cause="uvx-missing",
            phase="build",
            classification=classification,
            provider_attempts=0,
            endpoint_metadata=endpoint_metadata,
            commands=commands,
            model=model,
            timeout_seconds=timeout_seconds,
            runtime_workspace=runtime_workspace,
        )
        payload["status"] = "blocked-environment"
        if artifact_dir is not None:
            write_artifacts(artifact_dir, payload)
        return payload

    project_dir = create_proof_project(workspace_dir, endpoint_metadata)
    build = run_command(
        ["uvx", "--from", "maturin", "maturin", "develop", "--uv", "--manifest-path", "Cargo.toml", "--quiet"],
        cwd=project_dir,
        state=state,
        phase="maturin-build",
    )
    commands.append(command_phase_payload(build))
    if build.timed_out or build.exit_code != 0:
        classification = classify_provider_response({})
        root = "maturin-build-timeout" if build.timed_out else "maturin-build-failed"
        payload = build_failed_runtime_artifact(
            root_cause=root,
            phase="build",
            classification=classification,
            provider_attempts=0,
            endpoint_metadata=endpoint_metadata,
            commands=commands,
            model=model,
            timeout_seconds=timeout_seconds,
            runtime_workspace=runtime_workspace,
        )
        payload["status"] = "blocked-environment"
        if artifact_dir is not None:
            write_artifacts(artifact_dir, payload)
        return payload

    imported = run_command(
        [sys.executable, "-c", import_probe_code(model)],
        cwd=project_dir,
        state=state,
        phase="python-import-resolver",
    )
    commands.append(command_phase_payload(imported))
    if imported.timed_out or imported.exit_code != 0:
        classification = classify_provider_response({})
        root = "python-import-timeout" if imported.timed_out else "python-import-failed"
        payload = build_failed_runtime_artifact(
            root_cause=root,
            phase="import",
            classification=classification,
            provider_attempts=0,
            endpoint_metadata=endpoint_metadata,
            commands=commands,
            model=model,
            timeout_seconds=timeout_seconds,
            runtime_workspace=runtime_workspace,
        )
        payload["status"] = "blocked-environment"
        if artifact_dir is not None:
            write_artifacts(artifact_dir, payload)
        return payload

    resolver_metadata = parse_json_tail(imported.stdout_summary.redacted_tail)
    if resolver_metadata is None:
        classification = classify_provider_response({})
        payload = build_failed_runtime_artifact(
            root_cause="resolver-metadata-malformed",
            phase="resolver",
            classification=classification,
            provider_attempts=0,
            endpoint_metadata=endpoint_metadata,
            commands=commands,
            model=model,
            timeout_seconds=timeout_seconds,
            runtime_workspace=runtime_workspace,
        )
        payload["status"] = "blocked-environment"
        if artifact_dir is not None:
            write_artifacts(artifact_dir, payload)
        return payload

    resolver_result = validate_resolver_metadata(resolver_metadata, endpoint_metadata=endpoint_metadata, model=model)
    resolver_metadata = cast(dict[str, Any], resolver_result["metadata"])
    if resolver_result["status"] != "confirmed-runtime":
        classification = classify_provider_response({})
        payload = build_failed_runtime_artifact(
            root_cause=cast(str, resolver_result["root_cause"]),
            phase="resolver",
            classification=classification,
            provider_attempts=0,
            endpoint_metadata=endpoint_metadata,
            resolver_metadata=resolver_metadata,
            commands=commands,
            model=model,
            timeout_seconds=timeout_seconds,
            runtime_workspace=runtime_workspace,
        )
        payload["status"] = "blocked-environment"
        if artifact_dir is not None:
            write_artifacts(artifact_dir, payload)
        return payload

    if not credential_value:
        payload = build_blocked_credential_artifact(
            endpoint_metadata=endpoint_metadata,
            resolver_metadata=resolver_metadata,
            commands=commands,
            model=model,
            timeout_seconds=timeout_seconds,
            runtime_workspace=runtime_workspace,
        )
        if artifact_dir is not None:
            write_artifacts(artifact_dir, payload)
        return payload

    provider_attempts = 1
    live = run_command(
        [sys.executable, "-c", provider_probe_code(model, credential_env, timeout_seconds)],
        cwd=project_dir,
        state=state,
        phase="minimax-live-reasoning-split-call",
        env=os.environ.copy(),
        persist_raw_log=False,
    )
    commands.append(command_phase_payload(live, include_stream_tails=False))
    if live.timed_out:
        classification = classify_provider_response({})
        payload = build_failed_runtime_artifact(
            root_cause="provider-timeout",
            phase="provider-response",
            classification=classification,
            provider_attempts=provider_attempts,
            endpoint_metadata=endpoint_metadata,
            resolver_metadata=resolver_metadata,
            commands=commands,
            model=model,
            timeout_seconds=timeout_seconds,
            runtime_workspace=runtime_workspace,
        )
    elif live.exit_code != 0:
        combined = f"{live.stdout_summary.redacted_tail}\n{live.stderr_summary.redacted_tail}"
        classification = classify_provider_response({})
        payload = build_failed_runtime_artifact(
            root_cause=classify_provider_failure(combined),
            phase="provider-response",
            classification=classification,
            provider_attempts=provider_attempts,
            endpoint_metadata=endpoint_metadata,
            resolver_metadata=resolver_metadata,
            commands=commands,
            model=model,
            timeout_seconds=timeout_seconds,
            runtime_workspace=runtime_workspace,
        )
    else:
        safe_summary = parse_json_tail(live.stdout_summary.redacted_tail)
        if safe_summary is None:
            classification = classify_provider_response({})
            payload = build_failed_runtime_artifact(
                root_cause="provider-malformed-response",
                phase="provider-response",
                classification=classification,
                provider_attempts=provider_attempts,
                endpoint_metadata=endpoint_metadata,
                resolver_metadata=resolver_metadata,
                commands=commands,
                model=model,
                timeout_seconds=timeout_seconds,
                runtime_workspace=runtime_workspace,
            )
        elif safe_summary.get("status") == "provider-http-error":
            classification = classify_provider_response({})
            payload = build_failed_runtime_artifact(
                root_cause="provider-http-error",
                phase="provider-response",
                classification=classification,
                provider_attempts=provider_attempts,
                endpoint_metadata=endpoint_metadata,
                resolver_metadata=resolver_metadata,
                commands=commands,
                model=model,
                timeout_seconds=timeout_seconds,
                runtime_workspace=runtime_workspace,
            )
        else:
            classification = classify_safe_provider_summary(safe_summary)
            if classification.get("accepted"):
                payload = build_confirmed_runtime_artifact(
                    classification=classification,
                    provider_attempts=provider_attempts,
                    endpoint_metadata=endpoint_metadata,
                    resolver_metadata=resolver_metadata,
                    commands=commands,
                    model=model,
                    timeout_seconds=timeout_seconds,
                    runtime_workspace=runtime_workspace,
                )
            else:
                payload = build_failed_runtime_artifact(
                    root_cause=cast(str, classification.get("root_cause", "provider-schema-mismatch")),
                    phase=cast(str, classification.get("phase", "provider-response")),
                    classification=classification,
                    provider_attempts=provider_attempts,
                    endpoint_metadata=endpoint_metadata,
                    resolver_metadata=resolver_metadata,
                    commands=commands,
                    model=model,
                    timeout_seconds=timeout_seconds,
                    runtime_workspace=runtime_workspace,
                )

    if artifact_dir is not None:
        write_artifacts(artifact_dir, payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    candidate = payload.get("candidate", {}) if isinstance(payload.get("candidate"), dict) else {}
    reasoning = payload.get("reasoning", {}) if isinstance(payload.get("reasoning"), dict) else {}
    endpoint = payload.get("endpoint", {}) if isinstance(payload.get("endpoint"), dict) else {}
    request = payload.get("request", {}) if isinstance(payload.get("request"), dict) else {}
    lines = [
        "# M003/S03 Reasoning-Safe Candidate",
        "",
        f"- Schema: `{payload.get('schema_version')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Root cause: `{payload.get('root_cause')}`",
        f"- Phase: `{payload.get('phase')}`",
        f"- Provider attempts: `{payload.get('provider_attempts')}`",
        f"- Effective chat URL: `{endpoint.get('effective_chat_completions_url')}`",
        f"- Preserves /v1/: `{endpoint.get('preserves_v1')}`",
        f"- Request reasoning split: `{request.get('reasoning_split')}`",
        f"- Prompt text persisted: `{request.get('prompt_text_persisted')}`",
        f"- Candidate accepted: `{candidate.get('accepted')}`",
        f"- Candidate starts with: `{candidate.get('starts_with')}`",
        f"- Think-tag contamination: `{candidate.get('has_think_tag')}`",
        f"- Markdown fence contamination: `{candidate.get('has_markdown_fence')}`",
        f"- Prose prefix: `{candidate.get('has_prose_prefix')}`",
        f"- Prose suffix: `{candidate.get('has_prose_suffix')}`",
        f"- Raw body persisted: `{candidate.get('raw_provider_body_persisted')}`",
        f"- Reasoning present: `{reasoning.get('present')}`",
        f"- Reasoning separated: `{reasoning.get('separated')}`",
        f"- Reasoning raw text persisted: `{reasoning.get('raw_text_persisted')}`",
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
    markdown = "\n".join(lines)
    assert_safe_artifact({"markdown_summary": markdown})
    return markdown


def write_artifacts(output_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    safe_payload = cast(dict[str, Any], sanitize(payload))
    assert_safe_artifact(safe_payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / JSON_ARTIFACT
    markdown_path = output_dir / MARKDOWN_ARTIFACT
    json_path.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(safe_payload), encoding="utf-8")
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--credential-env", default=DEFAULT_CREDENTIAL_ENV)
    parser.add_argument("--timeout", type=parse_positive_timeout, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--keep-workspace", action="store_true")
    parser.add_argument("--no-write-artifacts", action="store_true")
    parser.add_argument("--fixture", choices=("clean", "blocked-credential"), default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.fixture == "blocked-credential":
        artifact = build_blocked_credential_artifact(
            endpoint_metadata=normalize_minimax_endpoint(args.endpoint),
            model=args.model,
            timeout_seconds=args.timeout,
        )
        if not args.no_write_artifacts:
            write_artifacts(args.artifact_dir, artifact)
        print(json.dumps({"status": artifact["status"], "root_cause": artifact["root_cause"]}, sort_keys=True))
        return 0
    if args.fixture == "clean":
        classification = classify_provider_response(
            {"choices": [{"message": {"content": "MATCH (article:Article) RETURN article.id LIMIT 5"}}]}
        )
        artifact = build_confirmed_runtime_artifact(
            classification=classification,
            provider_attempts=0,
            endpoint_metadata=normalize_minimax_endpoint(args.endpoint),
            model=args.model,
            timeout_seconds=args.timeout,
        )
        if not args.no_write_artifacts:
            write_artifacts(args.artifact_dir, artifact)
        print(json.dumps({"status": artifact["status"], "root_cause": artifact["root_cause"]}, sort_keys=True))
        return 0

    payload = run_proof(
        model=args.model,
        endpoint=args.endpoint,
        credential_env=args.credential_env,
        timeout_seconds=args.timeout,
        artifact_dir=None if args.no_write_artifacts else args.artifact_dir,
        runtime_dir=args.runtime_dir,
        keep_workspace=args.keep_workspace,
    )
    print(json.dumps({"status": payload["status"], "root_cause": payload["root_cause"]}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
