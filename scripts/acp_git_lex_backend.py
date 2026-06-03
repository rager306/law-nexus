#!/usr/bin/env python3
"""Internal ACP-facing git-lex diagnostic backend adapter for M055/S02.

This module normalizes the M054 proof-only wrapper records into bounded ACP-facing
L1 shadow diagnostic/projection records. It deliberately preserves ACP authority
boundaries: diagnostics are non-authoritative and cannot validate requirements or
mutate ACP source truth.
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import git_lex_diagnostic_adapter as git_lex
except ModuleNotFoundError:  # pragma: no cover - fallback for import-by-path tests.
    import importlib.util

    WRAPPER_PATH = Path(__file__).with_name("git_lex_diagnostic_adapter.py")
    spec = importlib.util.spec_from_file_location("git_lex_diagnostic_adapter", WRAPPER_PATH)
    if spec is None or spec.loader is None:
        raise
    git_lex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(git_lex)

SCHEMA_VERSION = "m055.acp_git_lex_backend_diagnostic.v1"
ADAPTER_VERSION = "m055.s02.v1"
BACKEND_LEVEL = "L1-shadow-diagnostic-projection"
BACKEND_NAME = "git-lex"
AUTHORITY = "non-authoritative-diagnostic"
DEFAULT_LIFECYCLE = "synthetic-fixture"

ACP_OPERATION_TO_WRAPPER = {
    "backend_help": ("help", "read-only"),
    "workspace_init": ("init", "projection"),
    "workspace_sync": ("sync", "projection"),
    "class_inventory": ("list_json", "projection"),
    "bounded_query": ("query", "projection"),
    "bounded_query_json": ("query_json", "projection"),
    "validation_diagnostic": ("validate_wrapped", "validation-diagnostic"),
    "reject_denied": ("reject_denied", "policy-rejection"),
}

WRAPPER_OPERATION_TO_ACP = {
    wrapper: acp for acp, (wrapper, _operation_class) in ACP_OPERATION_TO_WRAPPER.items()
}

CLASSIFICATION_MAP = {
    "pass": "pass",
    "git-lex-fail": "diagnostic-fail",
    "wrapper-fail": "adapter-fail",
    "blocked": "blocked",
    "rejected": "rejected",
    "not-run": "not-run",
}

SUCCESS_CLASSIFICATIONS = {"pass", "diagnostic-fail", "rejected"}
PRIVATE_FIELDS = {"_stdout_raw", "_stderr_raw"}
SAFETY_FIELDS = {
    "main_lex_absent_before",
    "main_lex_absent_after",
    "main_squad_absent_before",
    "main_squad_absent_after",
    "main_raw_absent_before",
    "main_raw_absent_after",
}


class BackendAdapterError(RuntimeError):
    """ACP backend adapter contract error."""


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bounded_text(value: object, limit: int = 1200) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...<truncated {len(text) - limit} chars>"


def operation_class_for(acp_operation: str) -> str:
    try:
        return ACP_OPERATION_TO_WRAPPER[acp_operation][1]
    except KeyError as exc:
        raise BackendAdapterError(f"unsupported ACP backend operation: {acp_operation}") from exc


def acp_operation_for(wrapper_operation: object) -> str:
    operation = str(wrapper_operation or "")
    try:
        return WRAPPER_OPERATION_TO_ACP[operation]
    except KeyError as exc:
        raise BackendAdapterError(f"unsupported wrapper operation: {operation}") from exc


def wrapper_operation_for(acp_operation: str) -> str:
    try:
        return ACP_OPERATION_TO_WRAPPER[acp_operation][0]
    except KeyError as exc:
        raise BackendAdapterError(f"unsupported ACP backend operation: {acp_operation}") from exc


def private_fields_present(record: dict[str, Any]) -> bool:
    return any(key in record for key in PRIVATE_FIELDS) or any(key.startswith("_") for key in record)


def main_state_safe(record: dict[str, Any]) -> bool:
    return all(record.get(field) is True for field in SAFETY_FIELDS)


def infer_error_class(wrapper_record: dict[str, Any], acp_operation: str) -> str | None:
    if not main_state_safe(wrapper_record):
        return "main-state-residue"
    if wrapper_record.get("workspace_is_main_repo") is True:
        return "workspace-policy-violation"
    if wrapper_record.get("git_lex_source_commit") != git_lex.PINNED_SOURCE_COMMIT:
        return "source-pin-mismatch"
    if wrapper_record.get("binary_sha256") != git_lex.PINNED_BINARY_SHA256:
        return "binary-identity-failed"
    if wrapper_record.get("authority") != AUTHORITY:
        return "unknown-adapter-error"

    wrapper_classification = str(wrapper_record.get("classification") or "")
    stderr = str(wrapper_record.get("stderr_digest") or "")
    stderr_lower = stderr.lower()

    if wrapper_classification == "rejected":
        if "query_id is not allowed" in stderr:
            return "query-id-rejected"
        if acp_operation == "reject_denied":
            return "denied-surface"
        return "unsupported-operation"
    if wrapper_classification == "blocked":
        if "workspace" in stderr_lower or "main repository" in stderr_lower:
            return "workspace-policy-violation"
        if "binary" in stderr_lower or "sha256" in stderr_lower:
            return "binary-identity-failed"
        return "unsupported-operation"
    if wrapper_classification == "wrapper-fail":
        if "missing_shapes" in stderr:
            return "missing-shape"
        if "missing_files" in stderr:
            return "missing-fixture"
        if "validated count mismatch" in stderr_lower:
            return "validation-count-mismatch"
        if "json" in stderr_lower and "parse" in stderr_lower:
            return "json-parse-failed"
        if any(token in stderr_lower for token in ("skipp", "failed to load", "schema", "compile")):
            return "validation-setup-ambiguous"
        return "unknown-adapter-error"
    if wrapper_classification == "git-lex-fail" and acp_operation == "validation_diagnostic":
        return "concrete-validation-violation"
    return None


def normalized_classification(wrapper_record: dict[str, Any]) -> str:
    if not main_state_safe(wrapper_record):
        return "adapter-fail"
    if wrapper_record.get("git_lex_source_commit") != git_lex.PINNED_SOURCE_COMMIT:
        return "adapter-fail"
    if wrapper_record.get("binary_sha256") != git_lex.PINNED_BINARY_SHA256:
        return "adapter-fail"
    if wrapper_record.get("authority") != AUTHORITY:
        return "adapter-fail"
    wrapper_classification = str(wrapper_record.get("classification") or "not-run")
    return CLASSIFICATION_MAP.get(wrapper_classification, "adapter-fail")


def diagnostic_summary(wrapper_record: dict[str, Any], classification: str) -> str:
    stderr = bounded_text(wrapper_record.get("stderr_digest"))
    stdout = bounded_text(wrapper_record.get("stdout_digest"))
    if stderr:
        return stderr
    if stdout:
        return stdout
    return f"git-lex backend diagnostic classified as {classification}"


def normalize_wrapper_record(
    wrapper_record: dict[str, Any],
    *,
    source_record_id: str | None = None,
    source_record_type: str | None = None,
    source_record_lifecycle: str | None = None,
    acp_operation: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Normalize one M054 wrapper record into an ACP-facing diagnostic record."""
    operation = acp_operation or acp_operation_for(wrapper_record.get("operation_type"))
    wrapper_operation = wrapper_operation_for(operation)
    if wrapper_record.get("operation_type") != wrapper_operation:
        raise BackendAdapterError(
            f"wrapper operation {wrapper_record.get('operation_type')} does not match ACP operation {operation}"
        )

    classification = normalized_classification(wrapper_record)
    error_class = infer_error_class(wrapper_record, operation)
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_id": str(uuid.uuid4()),
        "backend_level": BACKEND_LEVEL,
        "backend_name": BACKEND_NAME,
        "adapter_version": ADAPTER_VERSION,
        "source_record_id": source_record_id,
        "source_record_type": source_record_type,
        "source_record_lifecycle": source_record_lifecycle or DEFAULT_LIFECYCLE,
        "operation": operation,
        "operation_class": operation_class_for(operation),
        "classification": classification,
        "wrapper_classification": wrapper_record.get("classification"),
        "authority": AUTHORITY,
        "can_validate_requirement": False,
        "can_mutate_source_truth": False,
        "workspace_path": wrapper_record.get("workspace_path"),
        "workspace_is_main_repo": wrapper_record.get("workspace_is_main_repo"),
        "main_lex_absent_before": wrapper_record.get("main_lex_absent_before"),
        "main_lex_absent_after": wrapper_record.get("main_lex_absent_after"),
        "main_squad_absent_before": wrapper_record.get("main_squad_absent_before"),
        "main_squad_absent_after": wrapper_record.get("main_squad_absent_after"),
        "main_raw_absent_before": wrapper_record.get("main_raw_absent_before"),
        "main_raw_absent_after": wrapper_record.get("main_raw_absent_after"),
        "git_lex_source_commit": wrapper_record.get("git_lex_source_commit"),
        "binary_sha256": wrapper_record.get("binary_sha256"),
        "wrapper_schema_version": wrapper_record.get("schema_version"),
        "wrapper_operation_id": wrapper_record.get("operation_id"),
        "result_count": wrapper_record.get("result_count"),
        "observed_validated_count": wrapper_record.get("observed_validated_count"),
        "query_id": wrapper_record.get("query_id"),
        "diagnostic_summary": diagnostic_summary(wrapper_record, classification),
        "cleanup_status": wrapper_record.get("cleanup_status"),
        "created_at": created_at or now_iso(),
    }
    if error_class is not None:
        record["error_class"] = error_class
    if private_fields_present(wrapper_record):
        record["classification"] = "adapter-fail"
        record["error_class"] = "unknown-adapter-error"
        record["diagnostic_summary"] = "private wrapper fields were stripped from ACP diagnostic output"
    return record


def run_backend_operation(
    operation: str,
    *,
    workspace: str | None = None,
    kit: str = "squad",
    query_id: str | None = None,
    expected_shapes: list[str] | None = None,
    expected_files: list[str] | None = None,
    expected_count: int | None = None,
    negative: bool = False,
    command: str | None = None,
    source_record_id: str | None = None,
    source_record_type: str | None = None,
    source_record_lifecycle: str | None = None,
) -> dict[str, Any]:
    """Run one allowed ACP backend operation and return an ACP-facing diagnostic."""
    wrapper_operation_for(operation)
    if operation == "backend_help":
        wrapper_record = git_lex.operation_help()
    elif operation == "workspace_init":
        if workspace is None:
            raise BackendAdapterError("workspace is required for workspace_init")
        wrapper_record = git_lex.operation_init(workspace, kit)
    elif operation == "workspace_sync":
        if workspace is None:
            raise BackendAdapterError("workspace is required for workspace_sync")
        wrapper_record = git_lex.operation_sync(workspace)
    elif operation == "class_inventory":
        if workspace is None:
            raise BackendAdapterError("workspace is required for class_inventory")
        wrapper_record = git_lex.operation_list_json(workspace)
    elif operation in {"bounded_query", "bounded_query_json"}:
        if workspace is None:
            raise BackendAdapterError(f"workspace is required for {operation}")
        if query_id is None:
            raise BackendAdapterError(f"query_id is required for {operation}")
        wrapper_record = git_lex.operation_query(
            workspace, query_id, json_output=operation == "bounded_query_json"
        )
    elif operation == "validation_diagnostic":
        if workspace is None:
            raise BackendAdapterError("workspace is required for validation_diagnostic")
        if expected_count is None:
            raise BackendAdapterError("expected_count is required for validation_diagnostic")
        wrapper_record = git_lex.operation_validate_wrapped(
            workspace,
            expected_shapes or [],
            expected_files or [],
            expected_count,
            negative,
        )
    elif operation == "reject_denied":
        if command is None:
            raise BackendAdapterError("command is required for reject_denied")
        wrapper_record = git_lex.operation_reject_denied(command)
    else:  # pragma: no cover - wrapper_operation_for guards this branch.
        raise BackendAdapterError(f"unhandled ACP backend operation: {operation}")

    return normalize_wrapper_record(
        wrapper_record,
        source_record_id=source_record_id,
        source_record_type=source_record_type,
        source_record_lifecycle=source_record_lifecycle,
        acp_operation=operation,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="M055 ACP git-lex diagnostic backend adapter")
    sub = parser.add_subparsers(dest="operation", required=True)

    sub.add_parser("backend-help")

    reject_parser = sub.add_parser("reject-denied")
    reject_parser.add_argument("--command", required=True)

    init_parser = sub.add_parser("workspace-init")
    init_parser.add_argument("--workspace", required=True)
    init_parser.add_argument("--kit", default="squad")

    sync_parser = sub.add_parser("workspace-sync")
    sync_parser.add_argument("--workspace", required=True)

    inventory_parser = sub.add_parser("class-inventory")
    inventory_parser.add_argument("--workspace", required=True)

    query_parser = sub.add_parser("bounded-query")
    query_parser.add_argument("--workspace", required=True)
    query_parser.add_argument("--query-id", required=True, choices=sorted(git_lex.QUERY_TEMPLATES))

    query_json_parser = sub.add_parser("bounded-query-json")
    query_json_parser.add_argument("--workspace", required=True)
    query_json_parser.add_argument("--query-id", required=True, choices=sorted(git_lex.QUERY_TEMPLATES))

    validate_parser = sub.add_parser("validation-diagnostic")
    validate_parser.add_argument("--workspace", required=True)
    validate_parser.add_argument("--expected-shape", action="append", default=[])
    validate_parser.add_argument("--expected-file", action="append", default=[])
    validate_parser.add_argument("--expected-count", type=int, required=True)
    validate_parser.add_argument("--negative", action="store_true")

    for child in sub.choices.values():
        child.add_argument("--source-record-id")
        child.add_argument("--source-record-type")
        child.add_argument("--source-record-lifecycle")
    return parser


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    operation = args.operation.replace("-", "_")
    return run_backend_operation(
        operation,
        workspace=getattr(args, "workspace", None),
        kit=getattr(args, "kit", "squad"),
        query_id=getattr(args, "query_id", None),
        expected_shapes=getattr(args, "expected_shape", None),
        expected_files=getattr(args, "expected_file", None),
        expected_count=getattr(args, "expected_count", None),
        negative=getattr(args, "negative", False),
        command=getattr(args, "command", None),
        source_record_id=getattr(args, "source_record_id", None),
        source_record_type=getattr(args, "source_record_type", None),
        source_record_lifecycle=getattr(args, "source_record_lifecycle", None),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        record = dispatch(args)
    except BackendAdapterError as exc:
        record = {
            "schema_version": SCHEMA_VERSION,
            "record_id": str(uuid.uuid4()),
            "backend_level": BACKEND_LEVEL,
            "backend_name": BACKEND_NAME,
            "adapter_version": ADAPTER_VERSION,
            "operation": args.operation.replace("-", "_"),
            "classification": "rejected",
            "error_class": "unsupported-operation",
            "authority": AUTHORITY,
            "can_validate_requirement": False,
            "can_mutate_source_truth": False,
            "diagnostic_summary": bounded_text(exc),
            "created_at": now_iso(),
        }
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0 if record.get("classification") in SUCCESS_CLASSIFICATIONS else 1


if __name__ == "__main__":
    raise SystemExit(main())
