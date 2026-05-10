#!/usr/bin/env python3
"""M003/S02 MiniMax PyO3/genai endpoint proof harness.

This harness creates a focused generated PyO3 module that routes MiniMax through
`genai`'s OpenAI adapter. It proves that endpoint normalization happens before
Rust target resolution, imports the generated module locally through maturin, and
optionally performs exactly one credential-gated provider attempt. It never
persists credentials, auth headers, raw prompts, raw provider bodies, raw legal
text, raw FalkorDB rows, or `<think>` content.
"""

from __future__ import annotations

import argparse
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
SCHEMA_VERSION = "m003-s02-minimax-pyo3-endpoint/v2"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_ENDPOINT = "https://api.minimax.io/v1"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_API_KEY_ENV = "MINIMAX_API_KEY"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S02"
DEFAULT_RUNTIME_DIR = ROOT / ".gsd/runtime-smoke/minimax-pyo3-endpoint"
MODULE_NAME = "m003_s02_minimax_pyo3_endpoint"
JSON_ARTIFACT = "S02-MINIMAX-PYO3-ENDPOINT.json"
MARKDOWN_ARTIFACT = "S02-MINIMAX-PYO3-ENDPOINT.md"
SUPPORTED_ENDPOINT_HOST = "api.minimax.io"

Status = Literal[
    "not-run-local-only",
    "blocked-environment",
    "blocked-credential",
    "failed-runtime",
    "confirmed-runtime",
]

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
    "uvx-missing",
    "maturin-build-timeout",
    "maturin-build-failed",
    "python-import-timeout",
    "python-import-failed",
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

BOUNDARY_NON_CLAIMS = (
    "Legal KnowQL product behavior",
    "legal-answer correctness",
    "S03 validation",
    "FalkorDB execution",
    "ODT parsing",
    "retrieval quality",
    "production schema quality",
)
BOUNDARY_STATEMENT = (
    "This artifact is a focused proof harness for M003/S02 endpoint normalization and "
    "PyO3/genai routing only. It shows the MiniMax endpoint input, normalized PyO3/genai "
    "base endpoint, resolver metadata, local build/import/provider phase categories, and "
    "effective /v1/chat/completions URL. It does not prove Legal KnowQL product behavior, "
    "legal-answer correctness, S03 validation, FalkorDB execution, ODT parsing, retrieval "
    "quality, or production schema quality. Raw provider bodies, credentials, auth headers, "
    "prompts, raw legal text, raw FalkorDB rows, reasoning-tag content, and secret-like strings "
    "are not persisted."
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


def _unsafe_endpoint(reason: str) -> dict[str, Any]:
    """Return an invalid endpoint without persisting unsafe user-supplied URL text."""
    return _invalid_endpoint("<rejected-unsafe-endpoint>", reason)


def normalize_genai_base_endpoint(base_url: str) -> dict[str, Any]:
    """Normalize MiniMax endpoint input into the base URL Rust may receive."""
    endpoint_input = base_url
    stripped = base_url.strip()
    if not stripped:
        return _invalid_endpoint(endpoint_input, "empty")

    parts = urlsplit(stripped)
    if parts.username or parts.password:
        return _unsafe_endpoint("userinfo-not-allowed")
    if parts.query:
        return _unsafe_endpoint("query-not-allowed")
    if parts.fragment:
        return _unsafe_endpoint("fragment-not-allowed")
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

    base_path = "/v1/"
    normalized_base_url = urlunsplit(("https", SUPPORTED_ENDPOINT_HOST, base_path, "", ""))
    effective_path = "/v1/chat/completions"
    effective_chat_completions_url = urlunsplit(("https", SUPPORTED_ENDPOINT_HOST, effective_path, "", ""))
    normalization_applied = stripped != normalized_base_url
    return {
        "endpoint_input": endpoint_input,
        "normalized_base_url": normalized_base_url,
        "effective_chat_completions_url": effective_chat_completions_url,
        "preserves_v1": True,
        "normalization_applied": normalization_applied,
        "normalization_status": "normalized" if normalization_applied else "already-normalized",
        "status": "not-run-local-only",
        "root_cause": "local-only-endpoint-contract",
        "invalid_endpoint_reason": None,
        "endpoint_contract_valid": True,
    }


def build_endpoint_contract_payload(*, model: str, endpoint: str, timeout: int) -> dict[str, Any]:
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
        "resolver_metadata": None,
        "runtime_workspace": None,
        "boundary_statement": BOUNDARY_STATEMENT,
        "boundaries": boundaries_payload(),
        "safety": safety_payload(),
        "phases": default_phases(endpoint_contract),
    }
    assert_safe_payload(payload)
    return payload


# Backward-compatible alias for T01 callers/tests.
def build_local_payload(*, model: str, endpoint: str, timeout: int) -> dict[str, Any]:
    return build_endpoint_contract_payload(model=model, endpoint=endpoint, timeout=timeout)


def safety_payload() -> dict[str, bool]:
    return {
        "credentials_persisted": False,
        "auth_headers_persisted": False,
        "raw_provider_body_persisted": False,
        "raw_prompt_persisted": False,
        "raw_legal_text_persisted": False,
        "raw_falkordb_rows_persisted": False,
        "think_content_persisted": False,
    }


def boundaries_payload() -> dict[str, list[str]]:
    return {"does_not_prove": list(BOUNDARY_NON_CLAIMS)}


def default_phases(endpoint_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "endpoint_contract": {
            "status": endpoint_contract["normalization_status"],
            "root_cause": endpoint_contract["root_cause"],
        },
        "build": {"status": "not-run", "root_cause": "not-run"},
        "import": {"status": "not-run", "root_cause": "not-run"},
        "resolver": {"status": "not-run", "root_cause": "not-run"},
        "provider": {"status": "not-run", "root_cause": "not-run", "raw_provider_body_persisted": False},
    }


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


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


def create_proof_project(workspace_dir: Path, normalized_endpoint: str) -> Path:
    project_dir = workspace_dir / "minimax_pyo3_genai_endpoint"
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
            genai = "0.5.3"
            pyo3 = {{ version = "0.27", features = ["extension-module"] }}
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
            name = "m003-s02-minimax-pyo3-endpoint"
            version = "0.1.0"
            requires-python = ">=3.13"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (src_dir / "lib.rs").write_text(rust_source(normalized_endpoint), encoding="utf-8")
    return project_dir


def rust_source(normalized_endpoint: str) -> str:
    return (
        textwrap.dedent(
            f'''
            use genai::adapter::AdapterKind;
            use genai::chat::{{ChatMessage, ChatOptions, ChatRequest}};
            use genai::resolver::{{AuthData, Endpoint, ServiceTargetResolver}};
            use genai::{{Client, ModelIden, ServiceTarget}};
            use pyo3::prelude::*;
            use serde_json::json;
            use std::time::Duration;

            const DEFAULT_MINIMAX_MODEL: &str = "{DEFAULT_MODEL}";
            const NORMALIZED_MINIMAX_ENDPOINT: &str = "{normalized_endpoint}";

            fn minimax_endpoint() -> Endpoint {{
                Endpoint::from_owned(NORMALIZED_MINIMAX_ENDPOINT.to_string())
            }}

            fn build_minimax_client(api_key_env: String) -> Client {{
                let target_resolver = ServiceTargetResolver::from_resolver_fn(
                    move |service_target: ServiceTarget| -> Result<ServiceTarget, genai::resolver::Error> {{
                        let ServiceTarget {{ model, .. }} = service_target;
                        let endpoint = minimax_endpoint();
                        let auth = AuthData::from_env(api_key_env.clone());
                        let model = ModelIden::new(AdapterKind::OpenAI, model.model_name);
                        Ok(ServiceTarget {{ endpoint, auth, model }})
                    }},
                );
                Client::builder().with_service_target_resolver(target_resolver).build()
            }}

            #[pyfunction]
            fn binding_metadata() -> PyResult<String> {{
                Ok(json!({{
                    "module": "{MODULE_NAME}",
                    "model": DEFAULT_MINIMAX_MODEL,
                    "adapter_kind": "OpenAI",
                    "normalized_endpoint_base_url": NORMALIZED_MINIMAX_ENDPOINT,
                    "provider_body_persistence": "disabled"
                }}).to_string())
            }}

            #[pyfunction]
            fn resolve_target_metadata(model: String, api_key_env: String) -> PyResult<String> {{
                let client = build_minimax_client(api_key_env);
                let runtime = tokio::runtime::Runtime::new()
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                let target = runtime
                    .block_on(async {{ client.resolve_service_target(&model).await }})
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                Ok(json!({{
                    "module": "{MODULE_NAME}",
                    "model": String::from(target.model.model_name.clone()),
                    "adapter_kind": target.model.adapter_kind.as_str(),
                    "normalized_endpoint_base_url": target.endpoint.base_url(),
                    "provider_body_persistence": "disabled"
                }}).to_string())
            }}

            #[pyfunction]
            fn run_live_minimax_once(model: String, api_key_env: String, timeout_seconds: u64) -> PyResult<String> {{
                let client = build_minimax_client(api_key_env);
                let runtime = tokio::runtime::Runtime::new()
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                let chat_req = ChatRequest::default()
                    .with_system("Return the single token OK. Do not include prose, markdown, legal text, or reasoning.")
                    .append_message(ChatMessage::user("Return OK only."));
                let chat_options = ChatOptions::default().with_normalize_reasoning_content(true);
                let result = runtime.block_on(async {{
                    tokio::time::timeout(
                        Duration::from_secs(timeout_seconds),
                        client.exec_chat(&model, chat_req, Some(&chat_options)),
                    )
                    .await
                }});
                match result {{
                    Err(_) => Ok(json!({{"status": "timeout", "candidate_kind": "none"}}).to_string()),
                    Ok(Err(err)) => Err(pyo3::exceptions::PyRuntimeError::new_err(err.to_string())),
                    Ok(Ok(chat_res)) => {{
                        let text = chat_res.first_text().unwrap_or("");
                        let reasoning = chat_res.reasoning_content.as_deref().unwrap_or("");
                        let has_think_tag = text.contains("<think>") || text.contains("</think>") || reasoning.contains("<think>") || reasoning.contains("</think>");
                        Ok(json!({{
                            "status": "provider-response-received",
                            "candidate_kind": if text.trim().is_empty() {{ "empty" }} else {{ "text" }},
                            "has_think_tag": has_think_tag,
                            "has_reasoning_content": !reasoning.is_empty(),
                            "text_length": text.len()
                        }}).to_string())
                    }}
                }}
            }}

            #[pymodule]
            fn {MODULE_NAME}(m: &Bound<'_, PyModule>) -> PyResult<()> {{
                m.add_function(wrap_pyfunction!(binding_metadata, m)?)?;
                m.add_function(wrap_pyfunction!(resolve_target_metadata, m)?)?;
                m.add_function(wrap_pyfunction!(run_live_minimax_once, m)?)?;
                Ok(())
            }}
            '''
        ).strip()
        + "\n"
    )


def import_probe_code(model: str, api_key_env: str) -> str:
    return textwrap.dedent(
        f"""
        import json
        import {MODULE_NAME} as proof

        metadata = json.loads(proof.binding_metadata())
        target = json.loads(proof.resolve_target_metadata({model!r}, {api_key_env!r}))
        assert metadata["adapter_kind"] == "OpenAI"
        assert target["adapter_kind"] == "OpenAI"
        print(json.dumps(target, sort_keys=True))
        """
    ).strip()


def provider_probe_code(model: str, api_key_env: str, timeout_seconds: int) -> str:
    return textwrap.dedent(
        f"""
        import json
        import {MODULE_NAME} as proof

        payload = json.loads(proof.run_live_minimax_once({model!r}, {api_key_env!r}, {timeout_seconds!r}))
        print(json.dumps(payload, sort_keys=True))
        """
    ).strip()


def command_failure_root(result: CommandResult, *, timeout_root: str, failed_root: str) -> str:
    if result.timed_out:
        return timeout_root
    return f"{result.phase}-exit-{result.exit_code}" if result.exit_code not in (None, 1) else failed_root


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


def classify_provider_failure(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("401", "403", "unauthorized", "forbidden", "invalid api key", "api key")):
        return "minimax-auth-failed"
    if any(token in lowered for token in ("429", "rate limit", "too many requests", "quota")):
        return "minimax-rate-limited"
    if any(token in lowered for token in ("schema", "choices", "deserialize", "missing field", "chatresponsegeneration")):
        return "minimax-openai-schema-mismatch"
    if any(token in lowered for token in ("404", "not found", "/chat/completions", "route", "url", "invalid uri")):
        return "endpoint-contract-lost-v1"
    return "minimax-provider-call-failed"


def validate_resolver_metadata(
    metadata: dict[str, Any], *, endpoint_metadata: dict[str, Any], model: str
) -> dict[str, Any]:
    expected_endpoint = endpoint_metadata.get("normalized_base_url")
    actual_endpoint = metadata.get("normalized_endpoint_base_url")
    root_cause = "none"
    ok = True
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
    elif actual_endpoint != expected_endpoint or not str(actual_endpoint).startswith("https://api.minimax.io/v1/"):
        ok = False
        root_cause = "endpoint-contract-lost-v1"

    return {
        "phase": "resolver",
        "status": "confirmed-runtime" if ok else "blocked-environment",
        "root_cause": root_cause,
        "provider_attempts": 0,
        "metadata": metadata if ok else sanitize(metadata),
    }


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


def payload_status(phases: dict[str, Any]) -> tuple[Status, str, str]:
    order = ("endpoint_contract", "build", "import", "resolver", "provider")
    last_phase = "endpoint-contract"
    root_cause = "none"
    for phase_name in order:
        phase = phases.get(phase_name, {})
        status = phase.get("status")
        if status in ("blocked-environment", "blocked-credential", "failed-runtime"):
            return cast(Status, status), str(phase.get("root_cause", "unknown")), str(phase.get("phase", phase_name.replace("_", "-")))
        if status and status != "not-run":
            last_phase = str(phase.get("phase", phase_name.replace("_", "-")))
            root_cause = str(phase.get("root_cause", root_cause))
    provider = phases.get("provider", {})
    if provider.get("status") == "confirmed-runtime":
        return "confirmed-runtime", "none", "provider"
    return "not-run-local-only", root_cause, last_phase


def run_proof(
    *,
    model: str,
    endpoint: str,
    api_key_env: str,
    timeout_seconds: int,
    artifact_dir: Path | None = DEFAULT_ARTIFACT_DIR,
    runtime_dir: Path | None = DEFAULT_RUNTIME_DIR,
    keep_workspace: bool = False,
) -> dict[str, Any]:
    endpoint_metadata = normalize_genai_base_endpoint(endpoint)
    phases = default_phases(endpoint_metadata)
    provider_attempts = 0
    commands: list[dict[str, Any]] = []
    resolver_metadata: dict[str, Any] | None = None
    project_dir: Path | None = None

    if not endpoint_metadata["endpoint_contract_valid"]:
        phases["endpoint_contract"] = {
            "phase": "endpoint-contract",
            "status": "blocked-environment",
            "root_cause": endpoint_metadata["root_cause"],
            "category": "endpoint-contract",
        }
        payload = final_payload(
            status="blocked-environment",
            root_cause=cast(str, endpoint_metadata["root_cause"]),
            phase="endpoint-contract",
            model=model,
            timeout_seconds=timeout_seconds,
            endpoint_metadata=endpoint_metadata,
            resolver_metadata=resolver_metadata,
            provider_attempts=provider_attempts,
            phases=phases,
            commands=commands,
            runtime_workspace=None,
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
    secret_value = os.environ.get(api_key_env, "")
    state = ProofState(
        runtime_dir=actual_runtime_dir,
        workspace_dir=workspace_dir,
        log_dir=actual_runtime_dir / "logs",
        timeout_seconds=timeout_seconds,
        sensitive_values=[secret_value] if secret_value else [],
    )

    if not command_available("uvx"):
        phases["build"] = {
            "phase": "build",
            "status": "blocked-environment",
            "root_cause": "uvx-missing",
            "category": "environment",
            "summary": "uvx is unavailable, so maturin could not build the generated PyO3 module.",
        }
    else:
        project_dir = create_proof_project(workspace_dir, cast(str, endpoint_metadata["normalized_base_url"]))
        build = run_command(
            ["uvx", "--from", "maturin", "maturin", "develop", "--uv", "--manifest-path", "Cargo.toml", "--quiet"],
            cwd=project_dir,
            state=state,
            phase="maturin-build",
        )
        commands.append(command_phase_payload(build))
        if build.exit_code == 0 and not build.timed_out:
            phases["build"] = {
                "phase": "build",
                "status": "confirmed-runtime",
                "root_cause": "none",
                "category": "build",
                "project_dir": normalized_path(project_dir),
            }
        else:
            root = "maturin-build-timeout" if build.timed_out else "maturin-build-failed"
            phases["build"] = {
                "phase": "build",
                "status": "blocked-environment",
                "root_cause": root,
                "category": "build-timeout" if build.timed_out else "build",
                "exit_code": build.exit_code,
                "log_path": build.log_path,
            }

    if phases["build"].get("status") == "confirmed-runtime" and project_dir is not None:
        imported = run_command(
            [sys.executable, "-c", import_probe_code(model, api_key_env)],
            cwd=project_dir,
            state=state,
            phase="python-import-resolver",
        )
        commands.append(command_phase_payload(imported))
        if imported.exit_code == 0 and not imported.timed_out:
            phases["import"] = {"phase": "import", "status": "confirmed-runtime", "root_cause": "none", "category": "import"}
            resolver_metadata = parse_json_tail(imported.stdout_summary.redacted_tail)
            if resolver_metadata is None:
                phases["resolver"] = {
                    "phase": "resolver",
                    "status": "blocked-environment",
                    "root_cause": "resolver-metadata-malformed",
                    "category": "resolver",
                }
            else:
                resolver_result = validate_resolver_metadata(resolver_metadata, endpoint_metadata=endpoint_metadata, model=model)
                phases["resolver"] = {
                    "phase": "resolver",
                    "status": resolver_result["status"],
                    "root_cause": resolver_result["root_cause"],
                    "category": "resolver" if resolver_result["status"] == "confirmed-runtime" else "endpoint-contract",
                }
                resolver_metadata = cast(dict[str, Any], resolver_result["metadata"])
        else:
            root = "resolver-timeout" if imported.timed_out else "python-import-resolver-failed"
            phases["import"] = {
                "phase": "import",
                "status": "blocked-environment",
                "root_cause": root,
                "category": "resolver-timeout" if imported.timed_out else "import",
                "log_path": imported.log_path,
            }

    if phases["resolver"].get("status") == "confirmed-runtime" and project_dir is not None:
        if not secret_value:
            phases["provider"] = {
                "phase": "provider",
                "status": "blocked-credential",
                "root_cause": "minimax-credential-missing",
                "category": "credential",
                "raw_provider_body_persisted": False,
            }
        else:
            provider_attempts = 1
            live = run_command(
                [sys.executable, "-c", provider_probe_code(model, api_key_env, timeout_seconds)],
                cwd=project_dir,
                state=state,
                phase="minimax-live-provider-call",
                env=os.environ.copy(),
                persist_raw_log=False,
            )
            commands.append(command_phase_payload(live, include_stream_tails=False))
            if live.timed_out:
                phases["provider"] = {
                    "phase": "provider",
                    "status": "failed-runtime",
                    "root_cause": "provider-timeout",
                    "category": "timeout",
                    "raw_provider_body_persisted": False,
                }
            elif live.exit_code == 0:
                provider_payload = parse_json_tail(live.stdout_summary.redacted_tail) or {"safe_category": "provider-schema-mismatch"}
                provider_status = str(provider_payload.get("status"))
                if provider_status == "timeout":
                    phases["provider"] = {
                        "phase": "provider",
                        "status": "failed-runtime",
                        "root_cause": "provider-timeout",
                        "category": "timeout",
                        "raw_provider_body_persisted": False,
                        "provider_summary": sanitize(provider_payload),
                    }
                elif provider_payload.get("has_think_tag") or provider_payload.get("has_reasoning_content"):
                    phases["provider"] = {
                        "phase": "provider",
                        "status": "failed-runtime",
                        "root_cause": "provider-non-cypher-diagnostic",
                        "category": "schema",
                        "raw_provider_body_persisted": False,
                        "provider_summary": sanitize(provider_payload),
                    }
                else:
                    phases["provider"] = {
                        "phase": "provider",
                        "status": "confirmed-runtime",
                        "root_cause": "none",
                        "category": "provider",
                        "raw_provider_body_persisted": False,
                        "provider_summary": sanitize(provider_payload),
                    }
            else:
                combined = f"{live.stdout_summary.redacted_tail}\n{live.stderr_summary.redacted_tail}"
                root = classify_provider_failure(combined)
                phases["provider"] = {
                    "phase": "provider",
                    "status": "failed-runtime",
                    "root_cause": root,
                    "category": "endpoint-contract" if root == "endpoint-contract-lost-v1" else root.replace("minimax-", ""),
                    "raw_provider_body_persisted": False,
                }

    status, root_cause, phase = payload_status(phases)
    payload = final_payload(
        status=status,
        root_cause=root_cause,
        phase=phase,
        model=model,
        timeout_seconds=timeout_seconds,
        endpoint_metadata=endpoint_metadata,
        resolver_metadata=resolver_metadata,
        provider_attempts=provider_attempts,
        phases=phases,
        commands=commands,
        runtime_workspace=normalized_path(workspace_dir),
    )
    if artifact_dir is not None:
        write_artifacts(artifact_dir, payload)
    return payload


def final_payload(
    *,
    status: Status,
    root_cause: str,
    phase: str,
    model: str,
    timeout_seconds: int,
    endpoint_metadata: dict[str, Any],
    resolver_metadata: dict[str, Any] | None,
    provider_attempts: int,
    phases: dict[str, Any],
    commands: list[dict[str, Any]],
    runtime_workspace: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "status": status,
        "root_cause": root_cause,
        "phase": phase,
        "provider_attempts": provider_attempts,
        "model": model,
        "timeout_seconds": timeout_seconds,
        "endpoint": endpoint_metadata,
        "resolver_metadata": resolver_metadata,
        "runtime_workspace": runtime_workspace,
        "commands": commands,
        "boundary_statement": BOUNDARY_STATEMENT,
        "boundaries": boundaries_payload(),
        "safety": safety_payload(),
        "phases": phases,
    }
    safe_payload = cast(dict[str, Any], sanitize(payload))
    assert_safe_payload(safe_payload)
    return safe_payload


def write_artifacts(artifact_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    safe_payload = cast(dict[str, Any], sanitize(payload))
    assert_safe_payload(safe_payload)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    json_path = artifact_dir / JSON_ARTIFACT
    markdown_path = artifact_dir / MARKDOWN_ARTIFACT
    json_path.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# M003/S02 MiniMax PyO3 endpoint proof",
        "",
        f"- Schema: `{safe_payload['schema_version']}`",
        f"- Status: `{safe_payload['status']}`",
        f"- Root cause: `{safe_payload['root_cause']}`",
        f"- Phase: `{safe_payload['phase']}`",
        f"- Model: `{safe_payload['model']}`",
        f"- Provider attempts: `{safe_payload['provider_attempts']}`",
        f"- Normalized endpoint: `{safe_payload['endpoint'].get('normalized_base_url')}`",
        f"- Effective chat URL: `{safe_payload['endpoint'].get('effective_chat_completions_url')}`",
        "",
        safe_payload["boundary_statement"],
        "",
        "## Explicit non-claims",
        "",
    ]
    for non_claim in safe_payload.get("boundaries", {}).get("does_not_prove", []):
        lines.append(f"- Does not prove: {non_claim}")
    lines.extend(
        [
            "",
            "## Safety booleans",
            "",
            f"- Credentials persisted: `{safe_payload['safety'].get('credentials_persisted')}`",
            f"- Auth headers persisted: `{safe_payload['safety'].get('auth_headers_persisted')}`",
            f"- Raw provider body persisted: `{safe_payload['safety'].get('raw_provider_body_persisted')}`",
            f"- Raw prompt persisted: `{safe_payload['safety'].get('raw_prompt_persisted')}`",
            f"- Raw legal text persisted: `{safe_payload['safety'].get('raw_legal_text_persisted')}`",
            f"- Raw FalkorDB rows persisted: `{safe_payload['safety'].get('raw_falkordb_rows_persisted')}`",
            f"- Think content persisted: `{safe_payload['safety'].get('think_content_persisted')}`",
            "",
            "## Phase categories",
            "",
        ]
    )
    for name, phase in safe_payload.get("phases", {}).items():
        if isinstance(phase, dict):
            lines.append(f"- `{name}`: status=`{phase.get('status')}`, root_cause=`{phase.get('root_cause')}`")
    markdown_text = "\n".join(lines) + "\n"
    assert_safe_payload({"markdown": markdown_text})
    markdown_path.write_text(markdown_text, encoding="utf-8")
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--timeout", type=parse_positive_timeout, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--keep-workspace", action="store_true")
    parser.add_argument("--no-write-artifacts", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_proof(
        model=args.model,
        endpoint=args.endpoint,
        api_key_env=args.api_key_env,
        timeout_seconds=args.timeout,
        artifact_dir=None if args.no_write_artifacts else args.artifact_dir,
        runtime_dir=args.runtime_dir,
        keep_workspace=args.keep_workspace,
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
