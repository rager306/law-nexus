#!/usr/bin/env python3
"""Verify M003/S04 validation and read-only execution proof artifacts.

The verifier is intentionally contract-only: it reads one small local JSON artifact,
checks categorical diagnostics, redaction, and state-machine boundaries, and never
calls providers or FalkorDB. Runtime execution is valid only when a prior M002
validation report accepted the S03 candidate and the artifact records bounded
synthetic `Graph.ro_query(..., timeout=1000)` execution.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s04-validation-readonly-execution/v1"
S03_SCHEMA_VERSION = "m003-s03-reasoning-safe-candidate/v2"
M002_SCHEMA_VERSION = "m002-legalgraph-cypher-safety-contract/v1"
DEFAULT_ARTIFACT = ROOT / ".gsd/milestones/M003/slices/S04/S04-VALIDATION-READONLY-EXECUTION.json"

STATUS_CATEGORIES = {
    "skipped",
    "validation-rejected",
    "blocked-environment",
    "failed-runtime",
    "confirmed-runtime",
}
ROOT_CAUSE_CATEGORIES = {
    "none",
    "candidate-unavailable",
    "validation-rejected",
    "blocked-environment",
    "execution-timeout",
    "execution-failed",
    "contract-invalid",
    "redaction-violation",
}
PHASE_CATEGORIES = {
    "s03-handoff",
    "validation",
    "execution",
    "artifact-redaction",
}
S03_STATUS_CATEGORIES = {
    "blocked-credential",
    "blocked-environment",
    "failed-runtime",
    "confirmed-runtime",
}
EXECUTION_STATUS_CATEGORIES = {
    "not-attempted",
    "blocked-environment",
    "failed-runtime",
    "confirmed-runtime",
}
REQUIRED_REDACTION_FALSE_FIELDS = {
    "raw_provider_body_persisted",
    "credential_persisted",
    "auth_header_persisted",
    "prompt_text_persisted",
    "raw_reasoning_text_persisted",
    "raw_legal_text_persisted",
    "raw_graph_rows_persisted",
    "secret_like_values_persisted",
}
ALLOWED_FALSE_FIELD_NAMES = REQUIRED_REDACTION_FALSE_FIELDS | {
    "raw_rows_persisted",
}
FORBIDDEN_FIELD_PARTS = {
    "authorization",
    "auth_header_value",
    "credential_value",
    "provider_body",
    "raw_response",
    "request_prompt",
    "raw_reasoning",
    "reasoning_text",
    "raw_legal_text",
    "legal_text",
    "falkordb_rows",
    "raw_falkordb",
    "graph_rows",
    "secret_value",
}
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;}]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;}]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"raw_provider_body_value"),
    re.compile(r"request_prompt"),
    re.compile(r"reasoning_text_value"),
    re.compile(r"raw_legal_text_value"),
    re.compile(r"falkordb_rows_value"),
    re.compile(r"RAW_LEGAL_TEXT_SENTINEL[^\n\r\t,;}]*"),
    re.compile(r"(?i)<\s*/?\s*think\s*>"),
)
OVERCLAIM_PATTERNS = (
    re.compile(r"(?i)Legal KnowQL product behavior\s+(is\s+)?(validated|proven|confirmed|implemented|production[- ]ready)"),
    re.compile(r"(?i)legal-answer correctness\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)ODT parsing.*(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)retrieval quality.*(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)production graph schema fitness\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)live legal graph execution\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
)
REQUIRED_NON_CLAIMS = {
    "provider generation quality",
    "Legal KnowQL product behavior",
    "legal-answer correctness",
    "ODT parsing",
    "retrieval quality",
    "production graph schema fitness",
    "live legal graph execution",
}
REQUIRED_EXECUTION_COLUMNS = {
    "Article.id",
    "EvidenceSpan.id",
    "SourceBlock.id",
}


class VerificationError(ValueError):
    """Raised when the S04 artifact violates the validation/execution contract."""


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


def require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        fail(f"{path} must be boolean")
    return value


def require_field(mapping: dict[str, Any], key: str, path: str) -> Any:
    if key not in mapping:
        fail(f"{path}.{key} is required")
    return mapping[key]


def load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        fail(f"missing artifact: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"malformed-json: {exc.msg} at line {exc.lineno} column {exc.colno}")
    return require_dict(payload, "payload")


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


def validate_top_level(payload: dict[str, Any]) -> tuple[str, str, str]:
    require(payload.get("schema_version") == SCHEMA_VERSION, "schema_version mismatch")
    status = payload.get("status")
    root_cause = payload.get("root_cause")
    phase = payload.get("phase")
    require(isinstance(status, str) and status in STATUS_CATEGORIES, "status must be a known category")
    require(isinstance(root_cause, str) and root_cause in ROOT_CAUSE_CATEGORIES, "root_cause must be a known category")
    require(isinstance(phase, str) and phase in PHASE_CATEGORIES, "phase must be a known category")
    return status, root_cause, phase


def validate_s03_source(payload: dict[str, Any]) -> dict[str, Any]:
    source = require_dict(payload.get("s03_source"), "s03_source")
    require(source.get("schema_version") == S03_SCHEMA_VERSION, "s03_source.schema_version mismatch")
    require(source.get("status") in S03_STATUS_CATEGORIES, "s03_source.status must be known")
    require(isinstance(source.get("root_cause"), str) and source["root_cause"], "s03_source.root_cause must be non-empty")
    require(isinstance(source.get("phase"), str) and source["phase"], "s03_source.phase must be non-empty")
    provider_attempts = source.get("provider_attempts")
    require(isinstance(provider_attempts, int) and provider_attempts >= 0, "s03_source.provider_attempts must be a non-negative integer")
    require_bool(source.get("candidate_accepted"), "s03_source.candidate_accepted")
    return source


def validate_validation(payload: dict[str, Any]) -> dict[str, Any]:
    validation = require_dict(payload.get("validation"), "validation")
    accepted = require_bool(require_field(validation, "accepted", "validation"), "validation.accepted")
    require(require_field(validation, "schema_version", "validation") == M002_SCHEMA_VERSION, "validation.schema_version mismatch")
    rejection_codes = require_list(require_field(validation, "rejection_codes", "validation"), "validation.rejection_codes")
    require(all(isinstance(code, str) and code for code in rejection_codes), "validation.rejection_codes must contain strings")
    evidence_returns = require_list(require_field(validation, "required_evidence_returns", "validation"), "validation.required_evidence_returns")
    require(all(isinstance(item, str) and item for item in evidence_returns), "validation.required_evidence_returns must contain strings")
    if accepted:
        require(rejection_codes == [], "accepted validation must not include rejection codes")
        missing = sorted(REQUIRED_EXECUTION_COLUMNS - set(evidence_returns))
        require(not missing, "accepted validation missing required evidence returns: " + ", ".join(missing))
    else:
        require(bool(rejection_codes), "rejected validation requires at least one rejection code")
    return validation


def validate_execution(payload: dict[str, Any]) -> dict[str, Any]:
    execution = require_dict(payload.get("execution"), "execution")
    attempted = require_bool(require_field(execution, "attempted", "execution"), "execution.attempted")
    require(require_field(execution, "status", "execution") in EXECUTION_STATUS_CATEGORIES, "execution.status must be known")
    graph_kind = require_field(execution, "graph_kind", "execution")
    require(graph_kind == "synthetic-legalgraph", "execution.graph_kind must be synthetic-legalgraph")
    summary = require_dict(require_field(execution, "row_shape_summary", "execution"), "execution.row_shape_summary")
    require(summary.get("raw_rows_persisted") is False, "execution.row_shape_summary.raw_rows_persisted must be false")
    require(isinstance(summary.get("row_count_category"), str) and summary["row_count_category"], "execution.row_shape_summary.row_count_category required")
    columns = require_list(summary.get("column_categories"), "execution.row_shape_summary.column_categories")
    require(all(isinstance(column, str) for column in columns), "execution.row_shape_summary.column_categories must contain strings")
    identifier_categories = require_list(require_field(execution, "synthetic_identifier_categories", "execution"), "execution.synthetic_identifier_categories")
    require(all(isinstance(item, str) for item in identifier_categories), "execution.synthetic_identifier_categories must contain strings")

    if attempted:
        require(execution.get("method") == "Graph.ro_query", "execution.method must be Graph.ro_query")
        require(execution.get("timeout_ms") == 1000, "execution.timeout_ms must be 1000")
        require(execution.get("status") in {"confirmed-runtime", "failed-runtime"}, "attempted execution status invalid")
        missing = sorted(REQUIRED_EXECUTION_COLUMNS - set(columns))
        require(not missing, "execution.row_shape_summary missing required columns: " + ", ".join(missing))
        require(bool(identifier_categories), "attempted execution requires synthetic identifier categories")
    else:
        require(execution.get("method") is None, "not-attempted execution.method must be null")
        require(execution.get("timeout_ms") is None, "not-attempted execution.timeout_ms must be null")
        require(execution.get("status") == "not-attempted", "not-attempted execution.status must be not-attempted")
    return execution


def validate_redaction(payload: dict[str, Any]) -> None:
    redaction = require_dict(payload.get("redaction"), "redaction")
    for field in REQUIRED_REDACTION_FALSE_FIELDS:
        require(require_field(redaction, field, "redaction") is False, f"redaction.{field} must be false")


def validate_boundaries(payload: dict[str, Any]) -> None:
    boundaries = require_dict(payload.get("boundaries"), "boundaries")
    proves = "\n".join(str(item) for item in require_list(boundaries.get("proves"), "boundaries.proves"))
    does_not_prove_items = require_list(boundaries.get("does_not_prove"), "boundaries.does_not_prove")
    does_not_prove = "\n".join(str(item) for item in does_not_prove_items)
    assert_no_forbidden_text(proves, path="boundaries.proves")
    missing = sorted(item for item in REQUIRED_NON_CLAIMS if item not in does_not_prove)
    require(not missing, "boundaries.does_not_prove missing: " + ", ".join(missing))


def validate_state_semantics(
    status: str,
    root_cause: str,
    phase: str,
    s03_source: dict[str, Any],
    validation: dict[str, Any],
    execution: dict[str, Any],
) -> None:
    s03_accepted = cast("bool", s03_source["candidate_accepted"])
    validation_accepted = cast("bool", validation["accepted"])
    execution_attempted = cast("bool", execution["attempted"])

    if execution_attempted and not validation_accepted:
        fail("execution cannot be attempted unless validation.accepted is true")
    if validation_accepted and not execution_attempted:
        fail("accepted validation requires execution.attempted=true")
    if validation_accepted and not s03_accepted:
        fail("validation.accepted requires s03_source.candidate_accepted=true")

    if status == "skipped":
        require(root_cause == "candidate-unavailable", "skipped root_cause must be candidate-unavailable")
        require(phase == "s03-handoff", "skipped phase must be s03-handoff")
        require(not s03_accepted, "skipped artifact requires unaccepted S03 candidate")
        require(not validation_accepted, "skipped artifact must not accept validation")
        require(not execution_attempted, "skipped artifact must not execute")
        return

    if status == "validation-rejected":
        require(root_cause == "validation-rejected", "validation-rejected root_cause mismatch")
        require(phase == "validation", "validation-rejected phase must be validation")
        require(s03_accepted, "validation rejection requires accepted S03 candidate")
        require(not validation_accepted, "validation-rejected artifact must not accept validation")
        require(not execution_attempted, "validation-rejected artifact must not execute")
        return

    if status == "blocked-environment":
        require(root_cause == "blocked-environment", "blocked-environment root_cause mismatch")
        require(phase in {"validation", "execution"}, "blocked-environment phase invalid")
        require(not execution_attempted, "blocked-environment must fail before execution attempt")
        return

    if status == "failed-runtime":
        require(root_cause in {"execution-timeout", "execution-failed"}, "failed-runtime root_cause mismatch")
        require(phase == "execution", "failed-runtime phase must be execution")
        require(validation_accepted, "failed runtime requires accepted validation")
        require(execution_attempted, "failed runtime requires attempted execution")
        require(execution.get("status") == "failed-runtime", "failed runtime execution.status mismatch")
        return

    require(status == "confirmed-runtime", "unexpected status after category validation")
    require(root_cause == "none", "confirmed-runtime root_cause must be none")
    require(phase == "execution", "confirmed-runtime phase must be execution")
    require(s03_accepted, "confirmed-runtime requires accepted S03 candidate")
    require(validation_accepted, "confirmed-runtime requires accepted validation")
    require(execution_attempted, "confirmed-runtime requires attempted execution")
    require(execution.get("status") == "confirmed-runtime", "confirmed-runtime execution.status mismatch")


def verify_artifact(path: Path = DEFAULT_ARTIFACT) -> dict[str, Any]:
    payload = load_payload(path)
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    assert_no_forbidden_text(serialized, path="artifact", check_overclaims=False)
    assert_no_unsafe_fields(payload)
    status, root_cause, phase = validate_top_level(payload)
    s03_source = validate_s03_source(payload)
    validation = validate_validation(payload)
    execution = validate_execution(payload)
    validate_redaction(payload)
    validate_boundaries(payload)
    validate_state_semantics(status, root_cause, phase, s03_source, validation, execution)
    return {
        "verdict": "pass",
        "status": status,
        "root_cause": root_cause,
        "phase": phase,
        "s03_status": s03_source["status"],
        "s03_provider_attempts": s03_source["provider_attempts"],
        "validation_accepted": validation["accepted"],
        "validation_rejection_codes": validation["rejection_codes"],
        "execution_attempted": execution["attempted"],
        "execution_method": execution["method"],
        "execution_timeout_ms": execution["timeout_ms"],
        "artifact": str(path),
    }


def failure_result(error: str) -> dict[str, Any]:
    root_cause = "contract-invalid"
    if error.startswith("malformed-json"):
        root_cause = "malformed-json"
    elif "redaction violation" in error:
        root_cause = "redaction-violation"
    elif "boundary overclaim" in error:
        root_cause = "boundary-overclaim"
    return {
        "verdict": "fail",
        "status": "contract-invalid",
        "root_cause": root_cause,
        "phase": "artifact-redaction" if root_cause in {"redaction-violation", "boundary-overclaim"} else "contract-readback",
        "validation_accepted": None,
        "execution_attempted": None,
        "first_error": error,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = verify_artifact(args.artifact)
    except VerificationError as exc:
        print(json.dumps(failure_result(str(exc)), sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
