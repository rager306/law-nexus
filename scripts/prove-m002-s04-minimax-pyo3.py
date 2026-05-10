#!/usr/bin/env python3
"""Run a bounded M002/S04 MiniMax PyO3/genai adapter proof.

This proof creates a temporary PyO3 module that uses genai's
ServiceTargetResolver to route MiniMax-M2.7-highspeed through the OpenAI adapter
at https://api.minimax.io/v1. It is a proof harness only: provider output is
untrusted draft text, raw provider bodies are not persisted, and no Legal KnowQL
product behavior or legal answer is shipped here.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m002-s04-minimax-pyo3-proof/v2"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_ENDPOINT = "https://api.minimax.io/v1"
DEFAULT_API_KEY_ENV = "MINIMAX_API_KEY"
DEFAULT_RUNTIME_DIR = ROOT / ".gsd/runtime-smoke/text-to-cypher-minimax"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M002/slices/S04"
DEFAULT_SCHEMA_CONTRACT = ROOT / "tests/fixtures/m002_legalgraph_schema_contract.json"
DEFAULT_FALKOR_HOST = "127.0.0.1"
DEFAULT_FALKOR_PORT = 6380
READ_ONLY_TIMEOUT_MS = 1000
S03_VALIDATOR_PATH = ROOT / "scripts/verify-m002-cypher-safety-contract.py"
MODULE_NAME = "m002_s04_minimax_pyo3_proof"
JSON_ARTIFACT = "S04-MINIMAX-PYO3-PROOF.json"
MARKDOWN_ARTIFACT = "S04-MINIMAX-PYO3-PROOF.md"

Status = Literal[
    "confirmed-runtime",
    "blocked-credential",
    "blocked-environment",
    "failed-runtime",
]

SECRET_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
)
FORBIDDEN_TERMS = ("Authorization", "Bearer ", "api_key", "sk-", "BEGIN PRIVATE KEY")


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
    findings: list[dict[str, Any]] = field(default_factory=list)


class FalkorGraph(Protocol):
    def query(self, query: str) -> Any: ...

    def ro_query(self, query: str, params: dict[str, Any] | None = None, timeout: int | None = None) -> Any: ...


class FalkorClient(Protocol):
    def select_graph(self, graph_name: str) -> FalkorGraph: ...


def load_s03_validator() -> Any:
    spec = importlib.util.spec_from_file_location("verify_m002_cypher_safety_contract", S03_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("S03 validator could not be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def default_safe_candidate() -> str:
    return textwrap.dedent(
        """
        MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
              (span)-[:IN_BLOCK]->(block)
        WHERE article.id = $article_id AND article.valid_from <= $as_of AND $as_of < article.valid_to
        RETURN article.id, span.id, block.id, block.source_id, span.start_offset, span.end_offset
        LIMIT 5
        """
    ).strip()


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


def assert_safe_payload(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for term in FORBIDDEN_TERMS:
        if term in text:
            raise ValueError(f"refusing to write forbidden term: {term}")


def sanitize(value: Any, *, sensitive_values: list[str] | None = None) -> Any:
    if isinstance(value, str):
        return redact(value, sensitive_values=sensitive_values)
    if isinstance(value, list):
        return [sanitize(item, sensitive_values=sensitive_values) for item in value]
    if isinstance(value, tuple):
        return [sanitize(item, sensitive_values=sensitive_values) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize(item, sensitive_values=sensitive_values) for key, item in value.items()}
    return value


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


def add_finding(
    state: ProofState,
    *,
    finding_id: str,
    status: Status,
    phase: str,
    root_cause: str,
    summary: str,
    diagnostics: dict[str, Any] | None = None,
) -> None:
    state.findings.append(
        {
            "id": finding_id,
            "status": status,
            "phase": phase,
            "root_cause": root_cause,
            "summary": summary,
            "diagnostics": diagnostics or {"safe_category": root_cause},
        }
    )


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def create_proof_project(workspace_dir: Path) -> Path:
    project_dir = workspace_dir / "minimax_pyo3_genai_proof"
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
            name = "m002-s04-minimax-pyo3-proof"
            version = "0.1.0"
            requires-python = ">=3.13"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (src_dir / "lib.rs").write_text(rust_source(), encoding="utf-8")
    return project_dir


def rust_source() -> str:
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
            const DEFAULT_MINIMAX_ENDPOINT: &str = "{DEFAULT_ENDPOINT}";

            fn minimax_endpoint(endpoint: &str) -> Endpoint {{
                if endpoint == DEFAULT_MINIMAX_ENDPOINT {{
                    Endpoint::from_static(DEFAULT_MINIMAX_ENDPOINT)
                }} else {{
                    Endpoint::from_owned(endpoint.to_string())
                }}
            }}

            fn build_minimax_client(endpoint: String, api_key_env: String) -> Client {{
                let target_resolver = ServiceTargetResolver::from_resolver_fn(
                    move |service_target: ServiceTarget| -> Result<ServiceTarget, genai::resolver::Error> {{
                        let ServiceTarget {{ model, .. }} = service_target;
                        let endpoint = minimax_endpoint(&endpoint);
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
                    "proof_scope": "minimax-pyo3-genai-service-target-resolver",
                    "default_model": DEFAULT_MINIMAX_MODEL,
                    "default_endpoint": DEFAULT_MINIMAX_ENDPOINT,
                    "adapter_kind": "OpenAI",
                    "provider_body_persistence": "disabled"
                }}).to_string())
            }}

            #[pyfunction]
            fn resolve_target_metadata(model: String, endpoint: String, api_key_env: String) -> PyResult<String> {{
                let client = build_minimax_client(endpoint, api_key_env.clone());
                let runtime = tokio::runtime::Runtime::new()
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                let target = runtime
                    .block_on(async {{ client.resolve_service_target(&model).await }})
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                Ok(json!({{
                    "model_name": String::from(target.model.model_name.clone()),
                    "adapter_kind": target.model.adapter_kind.as_str(),
                    "endpoint": target.endpoint.base_url(),
                    "auth_debug": format!("{{:?}}", target.auth),
                    "api_key_env": api_key_env
                }}).to_string())
            }}

            #[pyfunction]
            fn run_live_minimax_once(model: String, endpoint: String, api_key_env: String, timeout_seconds: u64) -> PyResult<String> {{
                let client = build_minimax_client(endpoint, api_key_env);
                let runtime = tokio::runtime::Runtime::new()
                    .map_err(|err| pyo3::exceptions::PyRuntimeError::new_err(err.to_string()))?;
                let chat_req = ChatRequest::default()
                    .with_system("Return exactly one safe read-only Cypher candidate over synthetic labels Article, EvidenceSpan, and SourceBlock. Do not include prose, markdown fences, or legal text.")
                    .append_message(ChatMessage::user("Use synthetic IDs only. Return article id, evidence span id, and source block id with LIMIT 5."));
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
                        let upper = text.trim_start().to_ascii_uppercase();
                        let cypher_like = upper.starts_with("MATCH") || upper.starts_with("CALL");
                        let reasoning = chat_res.reasoning_content.as_deref().unwrap_or("");
                        let has_think_tag = text.contains("<think>") || text.contains("</think>") || reasoning.contains("<think>") || reasoning.contains("</think>");
                        Ok(json!({{
                            "status": "provider-response-received",
                            "candidate_kind": if cypher_like {{ "cypher_like" }} else {{ "non_cypher_text" }},
                            "has_think_tag": has_think_tag,
                            "has_reasoning_content": !reasoning.is_empty(),
                            "candidate_length": text.len()
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


def classify_command_failure(result: CommandResult) -> str:
    if result.timed_out:
        return f"{result.phase}-timeout"
    return f"{result.phase}-exit-{result.exit_code}"


def classify_provider_failure(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("401", "403", "unauthorized", "forbidden", "invalid api key", "api key")):
        return "minimax-auth-failed"
    if any(token in lowered for token in ("schema", "choices", "deserialize", "missing field", "chatresponsegeneration")):
        return "minimax-openai-schema-mismatch"
    if any(token in lowered for token in ("resolver", "endpoint", "route", "url", "invalid uri")):
        return "minimax-endpoint-routing-blocked"
    return "minimax-provider-call-failed"


def detect_reasoning_contamination(provider_payload: dict[str, Any]) -> bool:
    return bool(
        provider_payload.get("has_think_tag")
        or provider_payload.get("has_reasoning_content")
        or provider_payload.get("candidate_kind") == "non_cypher_text"
    )


def safe_validation_payload(report: Any, *, include_query: bool) -> dict[str, Any]:
    payload = asdict(report)
    if not include_query:
        payload["normalized_query"] = "<omitted-untrusted-draft>" if payload.get("normalized_query") else ""
    return cast("dict[str, Any]", sanitize(payload))


def validate_generated_cypher(
    candidate: object,
    *,
    schema_contract_path: Path = DEFAULT_SCHEMA_CONTRACT,
    request_context: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, Any]]:
    validator = load_s03_validator()
    contract = validator.load_schema_contract(schema_contract_path)
    context = request_context or {"as_of": "2025-01-01"}
    report = validator.validate_candidate(
        candidate,
        contract,
        query_case="s04-generated-cypher-candidate",
        request_context=context,
    )
    include_query = bool(report.accepted)
    return report, {
        "phase": "generated-cypher-validation",
        "accepted": bool(report.accepted),
        "schema_contract": normalized_path(schema_contract_path),
        "request_context": context,
        "report": safe_validation_payload(report, include_query=include_query),
        "legal_answer_produced": False,
        "execution_skipped": not bool(report.accepted),
        "skip_reason": None if report.accepted else "generated-cypher-validation-failed",
    }


def connect_falkordb_client(host: str, port: int) -> FalkorClient:
    module = importlib.import_module("falkordb")
    client_class = getattr(module, "FalkorDB")
    return cast("FalkorClient", client_class(host=host, port=port))


def setup_synthetic_legalgraph(graph: FalkorGraph) -> None:
    graph.query("MATCH (n) DETACH DELETE n")
    graph.query(
        """
        CREATE
          (:Act {id:'act:44fz', title_hash:'sha256:act-title', jurisdiction:'RU', status:'active'}),
          (:Article {id:'article:44fz:1', number:'1', valid_from:'2024-01-01', valid_to:'9999-12-31', text_hash:'sha256:article-1'}),
          (:SourceBlock {id:'sourceblock:garant:44fz:1', source_id:'garant-44fz-synthetic', block_hash:'sha256:sourceblock-1', search_text:'synthetic evidence anchor'}),
          (:EvidenceSpan {id:'evidence:44fz:art1:span1', span_hash:'sha256:evidence-1', start_offset:0, end_offset:42})
        """
    )
    graph.query(
        """
        MATCH
          (act:Act {id:'act:44fz'}),
          (article:Article {id:'article:44fz:1'}),
          (block:SourceBlock {id:'sourceblock:garant:44fz:1'}),
          (span:EvidenceSpan {id:'evidence:44fz:art1:span1'})
        CREATE
          (act)-[:HAS_ARTICLE {ordinal:1}]->(article),
          (article)-[:SUPPORTED_BY]->(block),
          (span)-[:IN_BLOCK]->(block),
          (span)-[:SUPPORTS]->(article)
        """
    )


def _rows_from_result(result: Any) -> list[Any]:
    rows = getattr(result, "result_set", result)
    if rows is None:
        return []
    if isinstance(rows, list):
        return rows
    return list(rows)


def safe_row_diagnostics(rows: list[Any]) -> dict[str, Any]:
    row_shapes: list[dict[str, Any]] = []
    safe_identifiers: list[list[str]] = []
    for row in rows[:5]:
        values = list(row) if isinstance(row, list | tuple) else [row]
        row_shapes.append({"column_count": len(values), "value_types": [type(value).__name__ for value in values]})
        safe_row = [value for value in values if isinstance(value, str) and re.match(r"^(act|article|sourceblock|evidence|garant)[A-Za-z0-9:._-]*$", value)]
        safe_identifiers.append(safe_row[:6])
    return {"row_count": len(rows), "row_shapes": row_shapes, "safe_identifiers": safe_identifiers}


def classify_ro_query_exception(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if isinstance(exc, TimeoutError) or "timeout" in text or "timed out" in text:
        return "read-only-execution-timeout"
    return "read-only-execution-failed"


def execute_validated_cypher(
    validation_report: Any,
    *,
    host: str = DEFAULT_FALKOR_HOST,
    port: int = DEFAULT_FALKOR_PORT,
    graph_name: str | None = None,
    client: FalkorClient | None = None,
    request_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not getattr(validation_report, "accepted", False):
        return {
            "phase": "read-only-execution",
            "status": "skipped",
            "root_cause": "generated-cypher-validation-failed",
            "legal_answer_produced": False,
            "query_method": "not-called",
        }
    graph_label = graph_name or f"s04_minimax_pyo3_{uuid.uuid4().hex[:10]}"
    context = request_context or {"as_of": "2025-01-01"}
    params = {"article_id": "article:44fz:1", "as_of": context["as_of"]}
    started = time.monotonic()
    try:
        falkor_client = client or connect_falkordb_client(host, port)
        graph = falkor_client.select_graph(graph_label)
        setup_synthetic_legalgraph(graph)
        result = graph.ro_query(validation_report.normalized_query, params=params, timeout=READ_ONLY_TIMEOUT_MS)
        rows = _rows_from_result(result)
        status = "confirmed-runtime"
        root_cause = "none"
        diagnostics = safe_row_diagnostics(rows)
        cleanup_status = "not-attempted"
        try:
            graph.query("MATCH (n) DETACH DELETE n")
            cleanup_status = "deleted"
        except Exception as cleanup_exc:  # noqa: BLE001 - cleanup is diagnostic only
            cleanup_status = f"cleanup-failed:{type(cleanup_exc).__name__}"
    except Exception as exc:  # noqa: BLE001 - classified proof diagnostics
        environment_error = isinstance(exc, (ImportError, ModuleNotFoundError, ConnectionError))
        status = "blocked-environment" if environment_error else "failed-runtime"
        root_cause = "blocked-environment" if environment_error else classify_ro_query_exception(exc)
        diagnostics = {"safe_category": root_cause, "error_type": type(exc).__name__}
        cleanup_status = "not-attempted"
    duration_ms = int((time.monotonic() - started) * 1000)
    return {
        "phase": "read-only-execution",
        "status": status,
        "root_cause": root_cause,
        "query_method": "Graph.ro_query",
        "timeout_ms": READ_ONLY_TIMEOUT_MS,
        "params_keys": sorted(params),
        "graph_name": graph_label,
        "endpoint": {"host": host, "port": port},
        "duration_ms": duration_ms,
        "diagnostics": diagnostics,
        "cleanup_status": cleanup_status,
        "legal_answer_produced": False,
    }


def add_validation_and_execution_findings(
    state: ProofState,
    *,
    validation_payload: dict[str, Any],
    execution_payload: dict[str, Any],
) -> None:
    if validation_payload["accepted"]:
        add_finding(
            state,
            finding_id="generated-cypher-validation",
            status="confirmed-runtime",
            phase="generated-cypher-validation",
            root_cause="none",
            summary="S03 deterministic validator accepted the generated/synthetic Cypher candidate before any database execution.",
            diagnostics={
                "safe_category": "validation-accepted",
                "rejection_codes": [],
                "schema_contract": validation_payload["schema_contract"],
            },
        )
    else:
        rejection_codes = validation_payload["report"].get("rejection_codes", [])
        add_finding(
            state,
            finding_id="generated-cypher-validation",
            status="failed-runtime",
            phase="generated-cypher-validation",
            root_cause="generated-cypher-validation-failed",
            summary="S03 deterministic validator rejected the candidate; read-only FalkorDB execution was skipped and no legal answer was produced.",
            diagnostics={"safe_category": "generated-cypher-validation-failed", "rejection_codes": rejection_codes},
        )
    exec_status = execution_payload.get("status")
    if exec_status == "confirmed-runtime":
        add_finding(
            state,
            finding_id="read-only-falkordb-execution",
            status="confirmed-runtime",
            phase="read-only-execution",
            root_cause="none",
            summary="Validated Cypher was executed only through Graph.ro_query(..., timeout=1000) against synthetic LegalGraph-shaped data.",
            diagnostics={"safe_category": "read-only-execution-confirmed", **execution_payload.get("diagnostics", {})},
        )
    elif exec_status == "skipped":
        add_finding(
            state,
            finding_id="read-only-falkordb-execution",
            status="failed-runtime",
            phase="read-only-execution",
            root_cause="generated-cypher-validation-failed",
            summary="Read-only FalkorDB execution was skipped because validation failed; no legal answer was produced.",
            diagnostics={"safe_category": "generated-cypher-validation-failed"},
        )
    else:
        status = "blocked-environment" if exec_status == "blocked-environment" else "failed-runtime"
        add_finding(
            state,
            finding_id="read-only-falkordb-execution",
            status=cast("Status", status),
            phase="read-only-execution",
            root_cause=str(execution_payload.get("root_cause", "read-only-execution-failed")),
            summary="Validated Cypher did not complete read-only FalkorDB execution; categorical diagnostics were persisted without raw legal text.",
            diagnostics=execution_payload.get("diagnostics", {"safe_category": execution_payload.get("root_cause", "unknown")}),
        )


def payload_status(findings: list[dict[str, Any]]) -> Status:
    statuses = [finding.get("status") for finding in findings]
    if "failed-runtime" in statuses:
        return "failed-runtime"
    if "blocked-environment" in statuses:
        return "blocked-environment"
    if "blocked-credential" in statuses:
        return "blocked-credential"
    return "confirmed-runtime"


def boundary_payload() -> dict[str, list[str]]:
    return {
        "proves": [
            "proof-only MiniMax PyO3/genai adapter route generation and local build/import status",
            "genai ServiceTargetResolver can be wired to AdapterKind::OpenAI and the configured MiniMax endpoint when the generated module builds",
            "one credential-gated MiniMax provider attempt status when credentials are available",
            "S03 deterministic validation gates the Cypher candidate before any database execution",
            "accepted Cypher execution is attempted only through Python FalkorDB Graph.ro_query(..., timeout=1000) against synthetic LegalGraph-shaped data",
        ],
        "does_not_prove": [
            "Legal KnowQL product behavior",
            "provider generation quality",
            "generated Cypher correctness or safety",
            "legal-answer correctness",
            "production graph schema fitness",
            "Garant ODT parsing or retrieval quality",
        ],
        "safety": [
            "raw provider bodies are not persisted",
            "credentials, auth headers, provider metadata values, and raw legal text are redacted or omitted",
            "provider output remains untrusted draft text until deterministic S03 validation accepts it",
            "validation failure skips Graph.ro_query execution and records rejection codes with no legal answer produced",
            "read-only execution artifacts expose only safe row-shape diagnostics and synthetic identifiers",
        ],
    }


def command_payload(result: CommandResult) -> dict[str, Any]:
    return {
        "phase": result.phase,
        "command": result.command,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "duration_ms": result.duration_ms,
        "stdout_summary": asdict(result.stdout_summary),
        "stderr_summary": asdict(result.stderr_summary),
        "log_path": result.log_path,
    }


def import_probe_code(model: str, endpoint: str, api_key_env: str) -> str:
    return textwrap.dedent(
        f"""
        import json
        import {MODULE_NAME} as proof

        metadata = json.loads(proof.binding_metadata())
        target = json.loads(proof.resolve_target_metadata({model!r}, {endpoint!r}, {api_key_env!r}))
        assert metadata["adapter_kind"] == "OpenAI"
        assert target["adapter_kind"] == "OpenAI"
        assert target["endpoint"] == {endpoint!r}
        assert target["auth_debug"] == "AuthData::FromEnv(REDACTED)"
        print(json.dumps({{"adapter_kind": target["adapter_kind"], "endpoint": target["endpoint"], "provider_body_persistence": metadata["provider_body_persistence"]}}, sort_keys=True))
        """
    ).strip()


def provider_probe_code(model: str, endpoint: str, api_key_env: str, timeout_seconds: int) -> str:
    return textwrap.dedent(
        f"""
        import json
        import {MODULE_NAME} as proof

        payload = json.loads(proof.run_live_minimax_once({model!r}, {endpoint!r}, {api_key_env!r}, {timeout_seconds!r}))
        print(json.dumps(payload, sort_keys=True))
        """
    ).strip()


def run_proof(
    *,
    artifact_dir: Path,
    runtime_dir: Path,
    model: str,
    endpoint: str,
    api_key_env: str,
    timeout_seconds: int,
    keep_workspace: bool,
    schema_contract_path: Path = DEFAULT_SCHEMA_CONTRACT,
    candidate_cypher: str | None = None,
    host: str = DEFAULT_FALKOR_HOST,
    port: int = DEFAULT_FALKOR_PORT,
) -> dict[str, Any]:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = runtime_dir / "workspace"
    if workspace_dir.exists() and not keep_workspace:
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    secret_value = os.environ.get(api_key_env, "")
    state = ProofState(
        runtime_dir=runtime_dir,
        workspace_dir=workspace_dir,
        log_dir=runtime_dir / "logs",
        timeout_seconds=timeout_seconds,
        sensitive_values=[secret_value] if secret_value else [],
    )

    if not command_available("uvx"):
        add_finding(
            state,
            finding_id="maturin-build",
            status="blocked-environment",
            phase="environment-check",
            root_cause="blocked-environment",
            summary="uvx is unavailable, so maturin could not be invoked for the generated PyO3 proof module.",
            diagnostics={"missing": "uvx"},
        )
    else:
        project_dir = create_proof_project(workspace_dir)
        build = run_command(
            ["uvx", "--from", "maturin", "maturin", "develop", "--uv", "--manifest-path", "Cargo.toml", "--quiet"],
            cwd=project_dir,
            state=state,
            phase="maturin-build",
        )
        if build.exit_code == 0 and not build.timed_out:
            add_finding(
                state,
                finding_id="maturin-build",
                status="confirmed-runtime",
                phase="maturin-build",
                root_cause="none",
                summary="maturin built the generated proof-only MiniMax PyO3/genai module.",
                diagnostics={"project_dir": normalized_path(project_dir)},
            )
            imported = run_command(
                [sys.executable, "-c", import_probe_code(model, endpoint, api_key_env)],
                cwd=project_dir,
                state=state,
                phase="python-import-target-resolution",
            )
            if imported.exit_code == 0 and not imported.timed_out:
                add_finding(
                    state,
                    finding_id="target-resolution",
                    status="confirmed-runtime",
                    phase="python-import-target-resolution",
                    root_cause="none",
                    summary="Python imported the module and resolved MiniMax through genai ServiceTargetResolver using AdapterKind::OpenAI.",
                    diagnostics={"endpoint": endpoint, "model": model, "credential_env_name": api_key_env},
                )
            else:
                add_finding(
                    state,
                    finding_id="target-resolution",
                    status="failed-runtime",
                    phase="python-import-target-resolution",
                    root_cause="minimax-endpoint-routing-blocked",
                    summary="Generated module import or target resolution failed before any provider request.",
                    diagnostics={"safe_category": classify_command_failure(imported), "log_path": imported.log_path},
                )
        else:
            add_finding(
                state,
                finding_id="maturin-build",
                status="blocked-environment",
                phase="maturin-build",
                root_cause="minimax-endpoint-routing-blocked",
                summary="maturin could not build the generated ServiceTargetResolver proof module.",
                diagnostics={"safe_category": classify_command_failure(build), "log_path": build.log_path},
            )

    provider_attempts = 0
    if any(finding["id"] == "target-resolution" and finding["status"] == "confirmed-runtime" for finding in state.findings):
        if not secret_value:
            add_finding(
                state,
                finding_id="minimax-live-proof",
                status="blocked-credential",
                phase="credential-check",
                root_cause="minimax-credential-missing",
                summary="MiniMax API key was not present; no provider request was made.",
                diagnostics={"safe_category": "missing-credential", "credential_env_name": api_key_env},
            )
        else:
            provider_attempts = 1
            live = run_command(
                [sys.executable, "-c", provider_probe_code(model, endpoint, api_key_env, timeout_seconds)],
                cwd=state.workspace_dir,
                state=state,
                phase="minimax-live-provider-call",
                env=os.environ.copy(),
                persist_raw_log=False,
            )
            if live.exit_code == 0 and not live.timed_out:
                try:
                    provider_payload = json.loads(live.stdout_summary.redacted_tail)
                except json.JSONDecodeError:
                    provider_payload = {"candidate_kind": "malformed-safe-summary"}
                if detect_reasoning_contamination(provider_payload):
                    add_finding(
                        state,
                        finding_id="minimax-live-proof",
                        status="failed-runtime",
                        phase="minimax-live-provider-call",
                        root_cause="reasoning-contamination",
                        summary="MiniMax returned output categorized as reasoning/prose-contaminated; raw body was not persisted.",
                        diagnostics={"safe_category": "reasoning-contamination", "provider_summary": provider_payload},
                    )
                else:
                    add_finding(
                        state,
                        finding_id="minimax-live-proof",
                        status="confirmed-runtime",
                        phase="minimax-live-provider-call",
                        root_cause="none",
                        summary="MiniMax provider call returned a Cypher-like candidate through the proof-only PyO3/genai route; raw body was not persisted.",
                        diagnostics={"safe_category": "provider-response-received", "provider_summary": provider_payload},
                    )
            else:
                combined = f"{live.stdout_summary.redacted_tail}\n{live.stderr_summary.redacted_tail}"
                root_cause = "minimax-provider-timeout" if live.timed_out else classify_provider_failure(combined)
                add_finding(
                    state,
                    finding_id="minimax-live-proof",
                    status="failed-runtime",
                    phase="minimax-live-provider-call",
                    root_cause=root_cause,
                    summary="MiniMax provider call failed; only categorical redacted diagnostics were persisted.",
                    diagnostics={"safe_category": root_cause},
                )

    request_context = {"as_of": "2025-01-01"}
    candidate_source = "synthetic-safe-candidate" if candidate_cypher is None else "cli-candidate"
    validation_report, validation_payload = validate_generated_cypher(
        candidate_cypher or default_safe_candidate(),
        schema_contract_path=schema_contract_path,
        request_context=request_context,
    )
    execution_payload = execute_validated_cypher(
        validation_report,
        host=host,
        port=port,
        request_context=request_context,
    )
    add_validation_and_execution_findings(
        state,
        validation_payload=validation_payload,
        execution_payload=execution_payload,
    )

    status = payload_status(state.findings)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": status,
        "phase": state.findings[-1]["phase"] if state.findings else "not-started",
        "model": model,
        "endpoint": endpoint,
        "credential_env_name": api_key_env,
        "provider_attempts": provider_attempts,
        "candidate_source": candidate_source,
        "validation": validation_payload,
        "execution": execution_payload,
        "workspace_dir": normalized_path(workspace_dir),
        "findings": state.findings,
        "commands": [command_payload(result) for result in state.commands],
        "boundaries": boundary_payload(),
    }
    write_artifacts(artifact_dir, payload, sensitive_values=state.sensitive_values)
    return cast("dict[str, Any]", sanitize(payload, sensitive_values=state.sensitive_values))


def write_artifacts(
    output_dir: Path,
    payload: dict[str, Any],
    *,
    sensitive_values: list[str] | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_payload = cast("dict[str, Any]", sanitize(payload, sensitive_values=sensitive_values))
    assert_safe_payload(safe_payload)
    json_path = output_dir / JSON_ARTIFACT
    markdown_path = output_dir / MARKDOWN_ARTIFACT
    json_path.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    findings = safe_payload.get("findings", [])
    lines = [
        "# M002/S04 MiniMax PyO3/genai Proof",
        "",
        f"- Schema: `{safe_payload.get('schema_version')}`",
        f"- Status: `{safe_payload.get('status')}`",
        f"- Phase: `{safe_payload.get('phase')}`",
        f"- Model: `{safe_payload.get('model')}`",
        f"- Endpoint: `{safe_payload.get('endpoint')}`",
        f"- Provider attempts: `{safe_payload.get('provider_attempts', 0)}`",
        f"- Candidate source: `{safe_payload.get('candidate_source')}`",
        f"- Validation accepted: `{safe_payload.get('validation', {}).get('accepted')}`",
        f"- Execution status: `{safe_payload.get('execution', {}).get('status')}`",
        "",
        "This artifact covers a proof-only MiniMax PyO3/genai adapter route plus deterministic S03 validation and bounded synthetic read-only FalkorDB execution evidence. It does not prove Legal KnowQL product behavior, provider generation quality, legal-answer correctness, production schema fitness, or retrieval quality. Provider output remains untrusted draft text until deterministic S03 validation accepts it. Validation failure skips `Graph.ro_query` execution and explicitly records that no legal answer was produced. Credentials, auth headers, provider metadata values, raw provider bodies, and raw legal text are redacted or omitted; raw provider bodies are not persisted.",
        "",
        "## Findings",
        "",
    ]
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        diagnostics = finding.get("diagnostics", {})
        safe_category = diagnostics.get("safe_category") if isinstance(diagnostics, dict) else "unknown"
        lines.extend(
            [
                f"### `{finding.get('id')}`",
                "",
                f"- Status: `{finding.get('status')}`",
                f"- Phase: `{finding.get('phase')}`",
                f"- Root cause: `{finding.get('root_cause')}`",
                f"- Safe category: `{safe_category}`",
                f"- Summary: {finding.get('summary')}`" if False else f"- Summary: {finding.get('summary')}",
                "",
            ]
        )
    validation = safe_payload.get("validation", {})
    execution = safe_payload.get("execution", {})
    rejection_codes = validation.get("report", {}).get("rejection_codes", []) if isinstance(validation, dict) else []
    row_diagnostics = execution.get("diagnostics", {}) if isinstance(execution, dict) else {}
    lines.extend(
        [
            "## Validation and Read-Only Execution",
            "",
            f"- Validation phase: `{validation.get('phase') if isinstance(validation, dict) else 'unknown'}`",
            f"- Validation accepted: `{validation.get('accepted') if isinstance(validation, dict) else False}`",
            f"- Rejection codes: `{rejection_codes}`",
            f"- Execution phase: `{execution.get('phase') if isinstance(execution, dict) else 'unknown'}`",
            f"- Execution status: `{execution.get('status') if isinstance(execution, dict) else 'unknown'}`",
            f"- Execution root cause: `{execution.get('root_cause') if isinstance(execution, dict) else 'unknown'}`",
            f"- Query method: `{execution.get('query_method') if isinstance(execution, dict) else 'unknown'}`",
            f"- Timeout ms: `{execution.get('timeout_ms') if isinstance(execution, dict) else 'unknown'}`",
            f"- Safe row diagnostics: `{json.dumps(row_diagnostics, ensure_ascii=False, sort_keys=True)}`",
            "- Legal answer produced: `False`",
            "",
        ]
    )
    lines.extend(
        [
            "## Boundaries",
            "",
            "### Proves",
            *[f"- {item}" for item in safe_payload.get("boundaries", {}).get("proves", [])],
            "",
            "### Does not prove",
            *[f"- {item}" for item in safe_payload.get("boundaries", {}).get("does_not_prove", [])],
            "",
            "### Safety",
            *[f"- {item}" for item in safe_payload.get("boundaries", {}).get("safety", [])],
            "",
        ]
    )
    markdown_text = "\n".join(lines)
    assert_safe_payload({"markdown": markdown_text})
    markdown_path.write_text(markdown_text, encoding="utf-8")
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--host", default=DEFAULT_FALKOR_HOST, help="FalkorDB host for validated read-only synthetic execution.")
    parser.add_argument("--port", type=int, default=DEFAULT_FALKOR_PORT, help="FalkorDB port for validated read-only synthetic execution.")
    parser.add_argument("--schema-contract", type=Path, default=DEFAULT_SCHEMA_CONTRACT)
    parser.add_argument("--candidate-cypher", help="Optional generated Cypher draft to validate before read-only execution; defaults to a synthetic safe candidate.")
    parser.add_argument("--timeout", type=parse_positive_timeout, default=240)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--keep-workspace", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_proof(
        artifact_dir=args.output_dir,
        runtime_dir=args.runtime_dir,
        model=args.model,
        endpoint=args.endpoint,
        api_key_env=args.api_key_env,
        timeout_seconds=args.timeout,
        keep_workspace=args.keep_workspace,
        schema_contract_path=args.schema_contract,
        candidate_cypher=args.candidate_cypher,
        host=args.host,
        port=args.port,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "phase": payload["phase"],
                "json": normalized_path(args.output_dir / JSON_ARTIFACT),
                "markdown": normalized_path(args.output_dir / MARKDOWN_ARTIFACT),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
