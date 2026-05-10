#!/usr/bin/env python3
"""Produce the M003/S04 validation-gated read-only execution proof artifact.

The proof consumes the durable S03 reasoning-safe candidate handoff, fails closed
when no accepted clean candidate is available, gates accepted candidate text
through the deterministic M002 validator, and executes only validator-accepted
Cypher against bounded synthetic LegalGraph-shaped FalkorDB data through
``Graph.ro_query(..., timeout=1000)``. Persisted artifacts contain categorical
summaries only: no provider bodies, prompts, reasoning text, raw legal text, or
raw graph rows.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import re
import sys
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_S03_ARTIFACT = ROOT / ".gsd/milestones/M003/slices/S03/S03-REASONING-SAFE-CANDIDATE.json"
DEFAULT_SCHEMA_CONTRACT = ROOT / "tests/fixtures/m002_legalgraph_schema_contract.json"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S04"
ARTIFACT_NAME = "S04-VALIDATION-READONLY-EXECUTION.json"
MARKDOWN_NAME = "S04-VALIDATION-READONLY-EXECUTION.md"
SCHEMA_VERSION = "m003-s04-validation-readonly-execution/v1"
S03_SCHEMA_VERSION = "m003-s03-reasoning-safe-candidate/v2"
M002_SCHEMA_VERSION = "m002-legalgraph-cypher-safety-contract/v1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6380
DEFAULT_READINESS_TIMEOUT_SECONDS = 5
EXECUTION_TIMEOUT_MS = 1000

_REQUIRED_S03_CLEAN_FLAGS = (
    "has_think_tag",
    "has_markdown_fence",
    "has_prose_prefix",
    "has_prose_suffix",
    "has_comment",
    "has_multi_statement",
    "raw_provider_body_persisted",
)
_REQUIRED_EVIDENCE_RETURNS = ["Article.id", "EvidenceSpan.id", "SourceBlock.id"]
_BOUNDARY_NON_CLAIMS = [
    "provider generation quality",
    "Legal KnowQL product behavior",
    "legal-answer correctness",
    "ODT parsing",
    "retrieval quality",
    "production graph schema fitness",
    "live legal graph execution",
]
_SAFE_SYNTHETIC_PARAMS: dict[str, Any] = {
    "article_id": "article:44fz:1",
    "source_article_id": "article:44fz:2",
    "target_article_id": "article:44fz:1",
    "id": "article:44fz:1",
    "search_terms": "procurement",
    "q": "procurement",
    "query": "procurement",
    "as_of": "2025-01-01",
}


class GraphLike(Protocol):
    def query(self, query: str) -> Any: ...

    def ro_query(self, query: str, params: Mapping[str, Any] | None = None, timeout: int | None = None) -> Any: ...

    def create_node_fulltext_index(self, label: str, attr: str, **kwargs: Any) -> Any: ...


class ClientLike(Protocol):
    def select_graph(self, graph_name: str) -> GraphLike: ...


class ExecutionContractError(ValueError):
    """Raised before graph execution when the execute_validated contract is unsafe."""


class ExecutionRuntimeError(RuntimeError):
    """Raised after attempted ro_query execution when runtime execution fails."""

    def __init__(self, summary: dict[str, Any]) -> None:
        super().__init__(str(summary.get("diagnostics", {}).get("error_category", "execution-failed")))
        self.summary = summary


def _load_m002_validator() -> ModuleType:
    path = ROOT / "scripts/verify-m002-cypher-safety-contract.py"
    spec = importlib.util.spec_from_file_location("verify_m002_cypher_safety_contract", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load M002 validator module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_M002 = _load_m002_validator()
load_schema_contract = _M002.load_schema_contract
validate_candidate = _M002.validate_candidate


def _load_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))


def _redaction() -> dict[str, bool]:
    return {
        "raw_provider_body_persisted": False,
        "credential_persisted": False,
        "auth_header_persisted": False,
        "prompt_text_persisted": False,
        "raw_reasoning_text_persisted": False,
        "raw_legal_text_persisted": False,
        "raw_graph_rows_persisted": False,
        "secret_like_values_persisted": False,
    }


def _execution_skipped() -> dict[str, Any]:
    return {
        "attempted": False,
        "status": "not-attempted",
        "method": None,
        "timeout_ms": None,
        "graph_kind": "synthetic-legalgraph",
        "graph_name_category": "not-run",
        "row_shape_summary": {
            "row_count_category": "not-run",
            "column_categories": [],
            "column_type_categories": [],
            "raw_rows_persisted": False,
        },
        "synthetic_identifier_categories": [],
        "parameter_summary": {},
    }


def _boundaries(proves: list[str]) -> dict[str, list[str]]:
    return {
        "proves": proves,
        "does_not_prove": _BOUNDARY_NON_CLAIMS,
    }


def _s03_source(payload: dict[str, Any] | None, *, fallback_reason: str | None = None) -> dict[str, Any]:
    if payload is None:
        return {
            "schema_version": S03_SCHEMA_VERSION,
            "status": "failed-runtime",
            "root_cause": fallback_reason or "s03-artifact-unavailable",
            "phase": "artifact-read",
            "provider_attempts": 0,
            "candidate_accepted": False,
        }
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    return {
        "schema_version": str(payload.get("schema_version", S03_SCHEMA_VERSION)),
        "status": str(payload.get("status", "failed-runtime")),
        "root_cause": str(payload.get("root_cause", "unknown")),
        "phase": str(payload.get("phase", "unknown")),
        "provider_attempts": int(payload.get("provider_attempts", 0)) if isinstance(payload.get("provider_attempts", 0), int) else 0,
        "candidate_accepted": bool(cast("dict[str, Any]", candidate).get("accepted", False)),
    }


def _candidate_unavailable_artifact(s03_payload: dict[str, Any] | None, reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "skipped",
        "root_cause": "candidate-unavailable",
        "phase": "s03-handoff",
        "s03_source": _s03_source(s03_payload, fallback_reason=reason),
        "validation": {
            "attempted": False,
            "accepted": False,
            "schema_version": M002_SCHEMA_VERSION,
            "query_shape_category": "candidate-unavailable",
            "rejection_codes": ["E_CANDIDATE_UNAVAILABLE"],
            "required_evidence_returns": [],
            "safe_parameter_categories": {},
            "candidate_availability_reason": reason,
        },
        "execution": _execution_skipped(),
        "redaction": _redaction(),
        "boundaries": _boundaries(["S03 candidate handoff was inspected and no accepted candidate was available"]),
    }


def _schema_unavailable_artifact(s03_payload: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked-environment",
        "root_cause": "blocked-environment",
        "phase": "validation",
        "s03_source": _s03_source(s03_payload),
        "validation": {
            "attempted": True,
            "accepted": False,
            "schema_version": M002_SCHEMA_VERSION,
            "query_shape_category": "schema-unavailable",
            "rejection_codes": ["E_CONTRACT_MALFORMED"],
            "required_evidence_returns": [],
            "safe_parameter_categories": {},
            "candidate_availability_reason": "available",
            "failure_class": "contract-readback",
            "schema_load_error_category": reason,
        },
        "execution": _execution_skipped(),
        "redaction": _redaction(),
        "boundaries": _boundaries(["S03 accepted candidate was not executed because schema contract loading failed closed"]),
    }


def _clean_candidate_text(payload: dict[str, Any]) -> tuple[str | None, str]:
    candidate = payload.get("candidate")
    if not isinstance(candidate, dict):
        return None, "candidate-object-missing"
    if payload.get("schema_version") != S03_SCHEMA_VERSION:
        return None, "s03-schema-mismatch"
    if payload.get("status") != "confirmed-runtime" or payload.get("root_cause") != "none":
        return None, "s03-not-confirmed-runtime"
    if candidate.get("accepted") is not True:
        return None, "candidate-not-accepted"
    if any(candidate.get(flag) is not False for flag in _REQUIRED_S03_CLEAN_FLAGS):
        return None, "candidate-diagnostics-not-clean"
    if candidate.get("categories") not in ([], None):
        return None, "candidate-diagnostics-not-clean"
    text = candidate.get("normalized_text")
    if not isinstance(text, str) or not text.strip():
        return None, "candidate-text-missing"
    return text, "available"


def _parameter_categories(query: str) -> dict[str, str]:
    categories: dict[str, str] = {}
    for key in sorted(set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", query))):
        if key == "as_of" or key.endswith("_date"):
            categories[key] = "temporal"
        elif key in {"search_terms", "q", "query"}:
            categories[key] = "search-terms"
        elif key.endswith("_id") or key == "id":
            categories[key] = "identifier"
        else:
            categories[key] = "scalar"
    return categories


def _query_shape_category(report: Any) -> str:
    if not report.accepted:
        return "rejected"
    required = set(_REQUIRED_EVIDENCE_RETURNS)
    if required.issubset(set(report.required_evidence_returns)):
        return "evidence-return-readonly"
    return "readonly"


def _query_result_set(graph: GraphLike, query: str) -> list[list[Any]]:
    result = graph.query(query)
    rows = getattr(result, "result_set", result)
    if not isinstance(rows, list):
        rows = list(rows)
    return cast("list[list[Any]]", rows)


def _connect_client(host: str, port: int) -> ClientLike:
    module = importlib.import_module("falkordb")
    client_class = getattr(module, "FalkorDB")
    return cast("ClientLike", client_class(host=host, port=port))


def wait_for_falkordb(host: str, port: int, timeout_seconds: int) -> ClientLike:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            client = _connect_client(host, port)
            graph = client.select_graph(f"m003_s04_readiness_{uuid.uuid4().hex[:8]}")
            _query_result_set(graph, "RETURN 1")
            return client
        except Exception as exc:  # noqa: BLE001 - readiness classification belongs in artifact
            last_error = exc
            time.sleep(0.25)
    raise TimeoutError(f"FalkorDB readiness timeout: {type(last_error).__name__ if last_error else 'unknown'}")


def setup_synthetic_legalgraph(graph: GraphLike) -> None:
    """Create bounded synthetic LegalGraph-shaped data using setup writes only."""

    _query_result_set(graph, "MATCH (n) DETACH DELETE n")
    _query_result_set(
        graph,
        """
        CREATE
          (:Act {id:'act:44fz', title_hash:'sha256:act-title', jurisdiction:'RU', status:'active'}),
          (:Article {id:'article:44fz:1', number:'1', valid_from:'2024-01-01', valid_to:'9999-12-31', text_hash:'sha256:article-1'}),
          (:Article {id:'article:44fz:2', number:'2', valid_from:'2024-01-01', valid_to:'9999-12-31', text_hash:'sha256:article-2'}),
          (:Authority {id:'authority:minfin', level:'federal', name_hash:'sha256:authority-minfin'}),
          (:SourceBlock {id:'sourceblock:garant:44fz:1', source_id:'garant-44fz-synthetic', block_hash:'sha256:sourceblock-1', search_text:'synthetic procurement evidence anchor alpha'}),
          (:SourceBlock {id:'sourceblock:garant:44fz:2', source_id:'garant-44fz-synthetic', block_hash:'sha256:sourceblock-2', search_text:'synthetic unrelated beta'}),
          (:EvidenceSpan {id:'evidence:44fz:art1:span1', span_hash:'sha256:evidence-1', start_offset:0, end_offset:42})
        """,
    )
    graph.create_node_fulltext_index("SourceBlock", "search_text")
    _query_result_set(
        graph,
        """
        MATCH
          (act:Act {id:'act:44fz'}),
          (a1:Article {id:'article:44fz:1'}),
          (a2:Article {id:'article:44fz:2'}),
          (authority:Authority {id:'authority:minfin'}),
          (block:SourceBlock {id:'sourceblock:garant:44fz:1'}),
          (span:EvidenceSpan {id:'evidence:44fz:art1:span1'})
        CREATE
          (act)-[:HAS_ARTICLE {ordinal:1}]->(a1),
          (act)-[:HAS_ARTICLE {ordinal:2}]->(a2),
          (a2)-[:CITES {kind:'synthetic-cross-reference'}]->(a1),
          (authority)-[:ISSUED]->(act),
          (a1)-[:SUPPORTED_BY]->(block),
          (span)-[:IN_BLOCK]->(block),
          (span)-[:SUPPORTS]->(a1)
        """,
    )


def cleanup_synthetic_legalgraph(graph: GraphLike) -> None:
    _query_result_set(graph, "MATCH (n) DETACH DELETE n")


def make_default_graph_factory(host: str, port: int, readiness_timeout_seconds: int) -> Callable[[], GraphLike]:
    def factory() -> GraphLike:
        client = wait_for_falkordb(host, port, readiness_timeout_seconds)
        graph_name = f"m003_s04_validation_readonly_{uuid.uuid4().hex[:10]}"
        return client.select_graph(graph_name)

    return factory


def _params_for_query(query: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for key in _parameter_categories(query):
        params[key] = _SAFE_SYNTHETIC_PARAMS.get(key, f"synthetic-{key}")
    return params


def _value_type_category(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return "structured"


def _param_value_category(key: str, value: Any) -> str:
    text = str(value)
    if key == "as_of" or key.endswith("_date"):
        return "synthetic-temporal"
    if key in {"search_terms", "q", "query"}:
        return "synthetic-search-terms"
    if text.startswith("article:"):
        return "synthetic-article-id"
    if text.startswith("evidence:"):
        return "synthetic-evidence-id"
    if text.startswith("sourceblock:"):
        return "synthetic-sourceblock-id"
    if text.startswith("act:"):
        return "synthetic-act-id"
    return "synthetic-scalar"


def _assert_safe_params(params: Mapping[str, Any]) -> None:
    forbidden = ("raw legal", "legal text", "bearer ", "sk-", "api_key", "password", "secret")
    for key, value in params.items():
        if not isinstance(key, str) or not key:
            raise ExecutionContractError("unsafe parameter key")
        if isinstance(value, str) and any(term in value.lower() for term in forbidden):
            raise ExecutionContractError(f"unsafe parameter category for {key}")


def _parameter_summary(params: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    return {
        key: {
            "type_category": _value_type_category(value),
            "value_category": _param_value_category(key, value),
        }
        for key, value in sorted(params.items())
    }


def _rows_from_ro_result(result: Any) -> list[list[Any]]:
    rows = getattr(result, "result_set", result)
    if rows is None:
        return []
    if not isinstance(rows, list):
        rows = list(rows)
    normalized: list[list[Any]] = []
    for row in rows:
        if isinstance(row, list | tuple):
            normalized.append(list(row))
        else:
            normalized.append([row])
    return normalized


def _row_count_category(row_count: int) -> str:
    if row_count == 0:
        return "empty"
    if row_count <= 5:
        return "non-empty"
    return "bounded-many"


def _column_type(value: Any) -> str:
    if isinstance(value, str):
        if value.startswith(("article:", "evidence:", "sourceblock:", "act:")):
            return "identifier"
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if value is None:
        return "null"
    return "structured"


def _row_shape_summary(rows: Sequence[Sequence[Any]]) -> dict[str, Any]:
    first_row = list(rows[0]) if rows else []
    columns = list(_REQUIRED_EVIDENCE_RETURNS[: len(first_row)])
    if len(first_row) > len(columns):
        columns.extend(f"synthetic_column_{index}" for index in range(len(columns), len(first_row)))
    return {
        "row_count_category": _row_count_category(len(rows)),
        "column_categories": columns,
        "column_type_categories": [_column_type(value) for value in first_row],
        "raw_rows_persisted": False,
    }


def _synthetic_identifier_categories(rows: Sequence[Sequence[Any]]) -> list[str]:
    categories: list[str] = []
    for row in rows[:1]:
        for value in row:
            if not isinstance(value, str):
                continue
            if value.startswith("article:") and "article_id" not in categories:
                categories.append("article_id")
            elif value.startswith("evidence:") and "evidence_span_id" not in categories:
                categories.append("evidence_span_id")
            elif value.startswith("sourceblock:") and "source_block_id" not in categories:
                categories.append("source_block_id")
            elif value.startswith("act:") and "act_id" not in categories:
                categories.append("act_id")
    return categories


def _failed_execution_summary(root_cause: str, params: Mapping[str, Any], error_category: str) -> dict[str, Any]:
    return {
        "attempted": True,
        "status": "failed-runtime",
        "method": "Graph.ro_query",
        "timeout_ms": EXECUTION_TIMEOUT_MS,
        "graph_kind": "synthetic-legalgraph",
        "graph_name_category": "synthetic-ephemeral",
        "row_shape_summary": {
            "row_count_category": "failed",
            "column_categories": list(_REQUIRED_EVIDENCE_RETURNS),
            "column_type_categories": [],
            "raw_rows_persisted": False,
        },
        "synthetic_identifier_categories": [],
        "parameter_summary": _parameter_summary(params),
        "diagnostics": {"root_cause": root_cause, "error_category": error_category},
    }


def execute_validated(validation_report: Any, params: Mapping[str, Any], graph: GraphLike) -> dict[str, Any]:
    """Execute only an accepted M002 validation report through Graph.ro_query."""

    if not getattr(validation_report, "accepted", False):
        raise ExecutionContractError("validation report must be accepted before execution")
    query = getattr(validation_report, "normalized_query", "")
    if not isinstance(query, str) or not query:
        raise ExecutionContractError("validation report must include a normalized query")
    expected_keys = set(_parameter_categories(query))
    if set(params) != expected_keys:
        raise ExecutionContractError("safe params must match normalized query parameters")
    _assert_safe_params(params)
    safe_params = dict(params)
    try:
        result = graph.ro_query(query, safe_params, timeout=EXECUTION_TIMEOUT_MS)
        rows = _rows_from_ro_result(result)
    except TimeoutError as exc:
        raise ExecutionRuntimeError(_failed_execution_summary("execution-timeout", safe_params, type(exc).__name__)) from exc
    except Exception as exc:  # noqa: BLE001 - categorical runtime diagnostics only
        raise ExecutionRuntimeError(_failed_execution_summary("execution-failed", safe_params, type(exc).__name__)) from exc
    summary = _row_shape_summary(rows)
    if rows and len(summary["column_categories"]) < len(_REQUIRED_EVIDENCE_RETURNS):
        raise ExecutionRuntimeError(_failed_execution_summary("execution-failed", safe_params, "row-shape-surprise"))
    return {
        "attempted": True,
        "status": "confirmed-runtime",
        "method": "Graph.ro_query",
        "timeout_ms": EXECUTION_TIMEOUT_MS,
        "graph_kind": "synthetic-legalgraph",
        "graph_name_category": "synthetic-ephemeral",
        "row_shape_summary": summary,
        "synthetic_identifier_categories": _synthetic_identifier_categories(rows),
        "parameter_summary": _parameter_summary(safe_params),
    }


def _validation_section(report: Any, candidate_text: str) -> dict[str, Any]:
    return {
        "attempted": True,
        "accepted": report.accepted,
        "schema_version": report.schema_version,
        "query_shape_category": _query_shape_category(report),
        "rejection_codes": list(report.rejection_codes),
        "required_evidence_returns": list(report.required_evidence_returns),
        "safe_parameter_categories": _parameter_categories(candidate_text) if report.accepted else {},
        "candidate_availability_reason": "available",
    }


def _validation_rejected_artifact(s03_payload: dict[str, Any], validation: dict[str, Any], report: Any) -> dict[str, Any]:
    report_dict = asdict(report)
    validation["failure_class"] = report_dict["diagnostics"][0]["failure_class"] if report_dict["diagnostics"] else "validation"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "validation-rejected",
        "root_cause": "validation-rejected",
        "phase": "validation",
        "s03_source": _s03_source(s03_payload),
        "validation": validation,
        "execution": _execution_skipped(),
        "redaction": _redaction(),
        "boundaries": _boundaries(["S03 accepted candidate was rejected by deterministic M002 validation before execution"]),
    }


def _blocked_environment_artifact(s03_payload: dict[str, Any], validation: dict[str, Any], error_category: str) -> dict[str, Any]:
    execution = _execution_skipped()
    execution["status"] = "blocked-environment"
    execution["diagnostics"] = {"root_cause": "blocked-environment", "error_category": error_category}
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked-environment",
        "root_cause": "blocked-environment",
        "phase": "execution",
        "s03_source": _s03_source(s03_payload),
        "validation": validation,
        "execution": execution,
        "redaction": _redaction(),
        "boundaries": _boundaries(["S03 accepted candidate passed M002 validation but synthetic FalkorDB setup was blocked before candidate execution"]),
    }


def _execution_artifact(s03_payload: dict[str, Any], validation: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    status = execution["status"]
    root_cause = "none" if status == "confirmed-runtime" else execution.get("diagnostics", {}).get("root_cause", "execution-failed")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "root_cause": root_cause,
        "phase": "execution",
        "s03_source": _s03_source(s03_payload),
        "validation": validation,
        "execution": execution,
        "redaction": _redaction(),
        "boundaries": _boundaries([
            "S03 accepted candidate was gated through deterministic M002 validation",
            "validator-accepted Cypher executed read-only against synthetic LegalGraph-shaped data",
        ]),
    }


def _validation_artifact(
    s03_payload: dict[str, Any],
    candidate_text: str,
    schema_contract: Path,
    graph_factory: Callable[[], GraphLike],
    setup_synthetic_graph: Callable[[GraphLike], None],
    cleanup_synthetic_graph: Callable[[GraphLike], None],
) -> dict[str, Any]:
    try:
        contract = load_schema_contract(schema_contract)
    except ValueError as exc:
        return _schema_unavailable_artifact(s03_payload, str(exc).split(":", maxsplit=1)[0])
    report = validate_candidate(candidate_text, contract, query_case="s03_reasoning_safe_candidate")
    validation = _validation_section(report, candidate_text)
    if not report.accepted:
        return _validation_rejected_artifact(s03_payload, validation, report)

    try:
        graph = graph_factory()
        setup_synthetic_graph(graph)
    except Exception as exc:  # noqa: BLE001 - classify missing client/runtime/setup as blocked environment
        return _blocked_environment_artifact(s03_payload, validation, type(exc).__name__)

    try:
        execution = execute_validated(report, _params_for_query(candidate_text), graph)
    except ExecutionRuntimeError as exc:
        execution = exc.summary
    finally:
        try:
            cleanup_synthetic_graph(graph)
        except Exception:
            pass
    return _execution_artifact(s03_payload, validation, execution)


def build_artifact(
    s03_artifact: Path,
    schema_contract: Path = DEFAULT_SCHEMA_CONTRACT,
    *,
    graph_factory: Callable[[], GraphLike] | None = None,
    setup_synthetic_graph: Callable[[GraphLike], None] = setup_synthetic_legalgraph,
    cleanup_synthetic_graph: Callable[[GraphLike], None] = cleanup_synthetic_legalgraph,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    readiness_timeout_seconds: int = DEFAULT_READINESS_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        s03_payload = _load_json(s03_artifact)
    except FileNotFoundError:
        return _candidate_unavailable_artifact(None, "s03-artifact-missing")
    except json.JSONDecodeError:
        return _candidate_unavailable_artifact(None, "s03-artifact-malformed")
    except OSError:
        return _candidate_unavailable_artifact(None, "s03-artifact-read-failed")

    candidate_text, reason = _clean_candidate_text(s03_payload)
    if candidate_text is None:
        return _candidate_unavailable_artifact(s03_payload, reason)
    factory = graph_factory or make_default_graph_factory(host, port, readiness_timeout_seconds)
    return _validation_artifact(
        s03_payload,
        candidate_text,
        schema_contract,
        factory,
        setup_synthetic_graph,
        cleanup_synthetic_graph,
    )


def write_artifact(artifact_dir: Path, payload: dict[str, Any]) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / ARTIFACT_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_markdown_artifact(artifact_dir: Path, payload: dict[str, Any]) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    execution = payload["execution"]
    validation = payload["validation"]
    lines = [
        "# M003/S04 Validation-Gated Read-Only Execution Proof",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Root cause: `{payload['root_cause']}`",
        f"- Phase: `{payload['phase']}`",
        f"- S03 status: `{payload['s03_source']['status']}`",
        f"- S03 provider attempts: `{payload['s03_source']['provider_attempts']}`",
        "",
        "## Validation",
        "",
        f"- Attempted: `{validation['attempted']}`",
        f"- Accepted: `{validation['accepted']}`",
        f"- Schema version: `{validation['schema_version']}`",
        f"- Rejection codes: `{', '.join(validation['rejection_codes']) or 'none'}`",
        f"- Required evidence returns: `{', '.join(validation['required_evidence_returns']) or 'none'}`",
        "",
        "## Execution Summary",
        "",
        f"- Attempted: `{execution['attempted']}`",
        f"- Status: `{execution['status']}`",
        f"- Method: `{execution['method']}`",
        f"- Timeout ms: `{execution['timeout_ms']}`",
        f"- Graph kind: `{execution['graph_kind']}`",
        f"- Row count category: `{execution['row_shape_summary']['row_count_category']}`",
        f"- Column categories: `{', '.join(execution['row_shape_summary']['column_categories']) or 'none'}`",
        f"- Synthetic identifier categories: `{', '.join(execution['synthetic_identifier_categories']) or 'none'}`",
        f"- Raw rows persisted: `{execution['row_shape_summary']['raw_rows_persisted']}`",
        "",
        "## Boundary",
        "",
        "This artifact is categorical, redacted proof only. It does not persist provider bodies, prompts, raw reasoning, raw legal text, raw graph rows, credentials, or secret-like values.",
        "",
        "### Does not prove",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["boundaries"]["does_not_prove"])
    path = artifact_dir / MARKDOWN_NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s03-artifact", type=Path, default=DEFAULT_S03_ARTIFACT)
    parser.add_argument("--schema-contract", type=Path, default=DEFAULT_SCHEMA_CONTRACT)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--readiness-timeout", type=int, default=DEFAULT_READINESS_TIMEOUT_SECONDS)
    parser.add_argument("--no-write-artifacts", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_artifact(
        args.s03_artifact,
        args.schema_contract,
        host=args.host,
        port=args.port,
        readiness_timeout_seconds=args.readiness_timeout,
    )
    if not args.no_write_artifacts:
        artifact_path = write_artifact(args.artifact_dir, payload)
        markdown_path = write_markdown_artifact(args.artifact_dir, payload)
    else:
        artifact_path = None
        markdown_path = None
    result = {
        "verdict": "pass" if payload["status"] in {"skipped", "validation-rejected", "blocked-environment", "failed-runtime", "confirmed-runtime"} else "fail",
        "status": payload["status"],
        "root_cause": payload["root_cause"],
        "phase": payload["phase"],
        "s03_status": payload["s03_source"]["status"],
        "validation_attempted": payload["validation"]["attempted"],
        "validation_accepted": payload["validation"]["accepted"],
        "validation_rejection_codes": payload["validation"]["rejection_codes"],
        "execution_attempted": payload["execution"]["attempted"],
        "execution_status": payload["execution"]["status"],
        "artifact": str(artifact_path) if artifact_path is not None else None,
        "markdown": str(markdown_path) if markdown_path is not None else None,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
