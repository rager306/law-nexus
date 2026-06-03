#!/usr/bin/env python3
"""Proof-only git-lex diagnostic adapter for M054.

This wrapper is intentionally narrow:
- it uses the D077 pinned local source-built git-lex debug binary;
- it rejects mutating/raw/server/destructive commands by policy;
- it runs runtime operations only in isolated workspaces outside this repo;
- it emits one non-authoritative JSON diagnostic record per operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PINNED_SOURCE_COMMIT = "eaa4b24d144a78a8b8e4969404d74cf22267df1f"
PINNED_BINARY = Path("/root/vendor-source/git-lex/target/debug/git-lex")
PINNED_BINARY_SHA256 = "40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c"
SCHEMA_VERSION = "m054.git_lex_diagnostic.v1"
AUTHORITY = "non-authoritative-diagnostic"

ALLOWED_OPERATIONS = {
    "help",
    "init",
    "sync",
    "list_json",
    "query",
    "query_json",
    "validate_wrapped",
    "reject_denied",
}

DENIED_COMMANDS = {
    "save",
    "create",
    "raw",
    "raw backfill",
    "join",
    "kit-update",
    "nuke",
    "display",
    "serve",
    "viz",
    "listen",
    "history-verify",
    "dump",
    "parse",
}

QUERY_TEMPLATES = {
    "graph_inventory": "SELECT ?g WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g LIMIT 50",
    "frontmatter_fixture": "SELECT ?s ?title WHERE { ?s fm:title ?title } LIMIT 20",
    "negative_empty": "SELECT ?s WHERE { ?s <urn:m054:missing> ?o } LIMIT 1",
    "history_reifies_ask": (
        "ASK WHERE { GRAPH ?g { ?r <http://www.w3.org/ns/rdf#reifies> <<( ?s ?p ?o )>> } }"
    ),
}

SETUP_DIAGNOSTIC_RE = re.compile(
    r"(skipp|missing|failed to load|failed to parse|parse error|compile|processor|schema|shape.*not found)",
    re.IGNORECASE,
)
VALIDATED_COUNT_RE = re.compile(r"Validated\s+(\d+)\s+files?", re.IGNORECASE)
SHACL_VIOLATION_RE = re.compile(
    r"(violation|MinCount|sh:minCount|sh:in|sh:datatype|Constraint)", re.IGNORECASE
)


class AdapterError(RuntimeError):
    """Wrapper-level failure before or after executing git-lex."""


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_text(value: str, limit: int = 1200) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n...<truncated {len(value) - limit} chars>"


def main_state() -> dict[str, bool]:
    return {
        "main_lex_absent": not (ROOT / ".lex").exists(),
        "main_squad_absent": not (ROOT / "Squad").exists(),
        "main_raw_absent": not (ROOT / "Raw").exists(),
    }


def is_inside_main_repo(path: Path) -> bool:
    resolved = path.resolve()
    root = ROOT.resolve()
    return resolved == root or root in resolved.parents


def resolve_workspace(raw_workspace: str | None, *, required: bool) -> Path | None:
    if raw_workspace is None:
        if required:
            raise AdapterError("workspace is required for this operation")
        return None
    workspace = Path(raw_workspace).expanduser()
    if not workspace.is_absolute():
        workspace = Path.cwd() / workspace
    if is_inside_main_repo(workspace):
        raise AdapterError(f"workspace must not be the main repository or a child of it: {workspace}")
    return workspace


def resolve_workspace_member(workspace: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve()
    workspace_resolved = workspace.resolve()
    if resolved != workspace_resolved and workspace_resolved not in resolved.parents:
        raise AdapterError(f"expected path escapes workspace: {raw_path}")
    return resolved


def binary_identity_ok() -> tuple[bool, str | None]:
    if not PINNED_BINARY.exists():
        return False, f"pinned binary missing: {PINNED_BINARY}"
    actual = sha256(PINNED_BINARY)
    if actual != PINNED_BINARY_SHA256:
        return False, f"pinned binary sha256 mismatch: {actual}"
    return True, None


def base_record(operation_type: str, workspace: Path | None, command: list[str] | None) -> dict[str, Any]:
    before = main_state()
    return {
        "schema_version": SCHEMA_VERSION,
        "operation_id": str(uuid.uuid4()),
        "operation_type": operation_type,
        "classification": "not-run",
        "workspace_path": str(workspace) if workspace is not None else None,
        "workspace_is_main_repo": is_inside_main_repo(workspace) if workspace is not None else False,
        "git_lex_binary": str(PINNED_BINARY),
        "git_lex_source_commit": PINNED_SOURCE_COMMIT,
        "binary_sha256": PINNED_BINARY_SHA256,
        "command": command or [],
        "exit_code": None,
        "stdout_digest": "",
        "stderr_digest": "",
        "expected_shapes": [],
        "expected_files": [],
        "observed_validated_count": None,
        "query_id": None,
        "result_count": None,
        "raw_payload_touched": False,
        "main_lex_absent_before": before["main_lex_absent"],
        "main_lex_absent_after": None,
        "main_squad_absent_before": before["main_squad_absent"],
        "main_squad_absent_after": None,
        "main_raw_absent_before": before["main_raw_absent"],
        "main_raw_absent_after": None,
        "cleanup_status": "not-needed",
        "authority": AUTHORITY,
        "duration_ms": 0,
    }


def finalize_record(record: dict[str, Any], started_ms: int) -> dict[str, Any]:
    after = main_state()
    record["main_lex_absent_after"] = after["main_lex_absent"]
    record["main_squad_absent_after"] = after["main_squad_absent"]
    record["main_raw_absent_after"] = after["main_raw_absent"]
    record["duration_ms"] = monotonic_ms() - started_ms
    return record


def run_command(command: list[str], workspace: Path | None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{PINNED_BINARY.parent}:{env.get('PATH', '')}"
    return subprocess.run(
        command,
        cwd=workspace or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        env=env,
    )


def run_git_lex(
    operation_type: str,
    command: list[str],
    workspace: Path | None,
    *,
    include_raw: bool = False,
) -> dict[str, Any]:
    started = monotonic_ms()
    record = base_record(operation_type, workspace, command)
    try:
        ok, message = binary_identity_ok()
        if not ok:
            record["classification"] = "blocked"
            record["stderr_digest"] = message or "binary identity failed"
            return finalize_record(record, started)
        if workspace is not None and record["workspace_is_main_repo"]:
            record["classification"] = "blocked"
            record["stderr_digest"] = "workspace is main repository or child"
            return finalize_record(record, started)
        completed = run_command(command, workspace)
        record["exit_code"] = completed.returncode
        record["stdout_digest"] = digest_text(completed.stdout)
        record["stderr_digest"] = digest_text(completed.stderr)
        record["classification"] = "pass" if completed.returncode == 0 else "git-lex-fail"
        finalized = finalize_record(record, started)
        if include_raw:
            finalized["_stdout_raw"] = completed.stdout
            finalized["_stderr_raw"] = completed.stderr
        return finalized
    except Exception as exc:  # noqa: BLE001 - proof harness must capture diagnostics.
        record["classification"] = "wrapper-fail"
        record["stderr_digest"] = str(exc)
        return finalize_record(record, started)


def operation_help() -> dict[str, Any]:
    return run_git_lex("help", [str(PINNED_BINARY), "--help"], None)


def operation_reject_denied(command_name: str) -> dict[str, Any]:
    started = monotonic_ms()
    normalized = command_name.strip()
    record = base_record("reject_denied", None, ["git-lex", normalized])
    if normalized in DENIED_COMMANDS:
        record["classification"] = "rejected"
        record["stderr_digest"] = f"command denied by M054 policy: {normalized}"
    else:
        record["classification"] = "blocked"
        record["stderr_digest"] = f"command is not in denylist; use explicit adapter operation: {normalized}"
    return finalize_record(record, started)


def operation_init(workspace_raw: str, kit: str) -> dict[str, Any]:
    workspace = resolve_workspace(workspace_raw, required=True)
    assert workspace is not None
    workspace.mkdir(parents=True, exist_ok=True)
    return run_git_lex("init", [str(PINNED_BINARY), "init", "--kit", kit, str(workspace)], workspace)


def operation_sync(workspace_raw: str) -> dict[str, Any]:
    workspace = resolve_workspace(workspace_raw, required=True)
    assert workspace is not None
    return run_git_lex("sync", [str(PINNED_BINARY), "sync"], workspace)


def operation_list_json(workspace_raw: str) -> dict[str, Any]:
    workspace = resolve_workspace(workspace_raw, required=True)
    assert workspace is not None
    record = run_git_lex(
        "list_json", [str(PINNED_BINARY), "list", "--json"], workspace, include_raw=True
    )
    raw_stdout = str(record.pop("_stdout_raw", ""))
    record.pop("_stderr_raw", None)
    if record["classification"] == "pass":
        try:
            payload = json.loads(raw_stdout)
            if isinstance(payload, list):
                record["result_count"] = len(payload)
        except json.JSONDecodeError:
            record["classification"] = "wrapper-fail"
            record["stderr_digest"] = "list --json did not emit parseable JSON"
    return record


def operation_query(workspace_raw: str, query_id: str, *, json_output: bool) -> dict[str, Any]:
    if query_id not in QUERY_TEMPLATES:
        started = monotonic_ms()
        workspace = resolve_workspace(workspace_raw, required=True)
        record = base_record("query_json" if json_output else "query", workspace, [])
        record["classification"] = "rejected"
        record["query_id"] = query_id
        record["stderr_digest"] = f"query_id is not allowed: {query_id}"
        return finalize_record(record, started)
    workspace = resolve_workspace(workspace_raw, required=True)
    assert workspace is not None
    command = [str(PINNED_BINARY), "query", QUERY_TEMPLATES[query_id]]
    if json_output:
        command = [str(PINNED_BINARY), "query", "--json", QUERY_TEMPLATES[query_id]]
    record = run_git_lex("query_json" if json_output else "query", command, workspace, include_raw=json_output)
    raw_stdout = str(record.pop("_stdout_raw", ""))
    record.pop("_stderr_raw", None)
    record["query_id"] = query_id
    if json_output and record["classification"] == "pass":
        try:
            payload = json.loads(raw_stdout)
            bindings = payload.get("results", {}).get("bindings", []) if isinstance(payload, dict) else []
            record["result_count"] = len(bindings) if isinstance(bindings, list) else None
        except json.JSONDecodeError:
            record["classification"] = "wrapper-fail"
            record["stderr_digest"] = "query --json did not emit parseable JSON"
    return record


def operation_validate_wrapped(
    workspace_raw: str,
    expected_shapes: list[str],
    expected_files: list[str],
    expected_count: int,
    negative: bool,
) -> dict[str, Any]:
    started = monotonic_ms()
    workspace = resolve_workspace(workspace_raw, required=True)
    assert workspace is not None
    record = base_record("validate_wrapped", workspace, [str(PINNED_BINARY), "validate"])
    record["expected_shapes"] = expected_shapes
    record["expected_files"] = expected_files
    try:
        if expected_count < 0:
            raise AdapterError("expected-count must be non-negative")
        shape_paths = [resolve_workspace_member(workspace, item) for item in expected_shapes]
        file_paths = [resolve_workspace_member(workspace, item) for item in expected_files]
        missing_shapes = [str(path) for path in shape_paths if not path.exists()]
        missing_files = [str(path) for path in file_paths if not path.exists()]
        if missing_shapes or missing_files:
            record["classification"] = "wrapper-fail"
            record["stderr_digest"] = json.dumps(
                {"missing_shapes": missing_shapes, "missing_files": missing_files}, sort_keys=True
            )
            return finalize_record(record, started)
        ok, message = binary_identity_ok()
        if not ok:
            record["classification"] = "blocked"
            record["stderr_digest"] = message or "binary identity failed"
            return finalize_record(record, started)
        completed = run_command([str(PINNED_BINARY), "validate"], workspace)
        combined = f"{completed.stdout}\n{completed.stderr}"
        record["exit_code"] = completed.returncode
        record["stdout_digest"] = digest_text(completed.stdout)
        record["stderr_digest"] = digest_text(completed.stderr)
        count_match = VALIDATED_COUNT_RE.search(combined)
        if count_match:
            record["observed_validated_count"] = int(count_match.group(1))
        has_setup_diagnostic = bool(SETUP_DIAGNOSTIC_RE.search(combined))
        has_violation = bool(SHACL_VIOLATION_RE.search(combined))
        if negative:
            if completed.returncode != 0 and has_violation and not has_setup_diagnostic:
                record["classification"] = "git-lex-fail"
            else:
                record["classification"] = "wrapper-fail"
            return finalize_record(record, started)
        if completed.returncode != 0:
            record["classification"] = "git-lex-fail"
        elif record["observed_validated_count"] != expected_count:
            record["classification"] = "wrapper-fail"
            record["stderr_digest"] = (
                record["stderr_digest"]
                + f"\nvalidated count mismatch: expected {expected_count}, observed {record['observed_validated_count']}"
            ).strip()
        elif has_setup_diagnostic:
            record["classification"] = "wrapper-fail"
        else:
            record["classification"] = "pass"
        return finalize_record(record, started)
    except Exception as exc:  # noqa: BLE001 - proof harness must capture diagnostics.
        record["classification"] = "wrapper-fail"
        record["stderr_digest"] = str(exc)
        return finalize_record(record, started)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="M054 proof-only git-lex diagnostic adapter")
    sub = parser.add_subparsers(dest="operation", required=True)

    help_parser = sub.add_parser("help")
    help_parser.add_argument("--json", action="store_true", help="Emit JSON diagnostic record")

    reject_parser = sub.add_parser("reject-denied")
    reject_parser.add_argument("--command", required=True)

    init_parser = sub.add_parser("init")
    init_parser.add_argument("--workspace", required=True)
    init_parser.add_argument("--kit", default="squad")

    sync_parser = sub.add_parser("sync")
    sync_parser.add_argument("--workspace", required=True)

    list_parser = sub.add_parser("list-json")
    list_parser.add_argument("--workspace", required=True)

    query_parser = sub.add_parser("query")
    query_parser.add_argument("--workspace", required=True)
    query_parser.add_argument("--query-id", required=True, choices=sorted(QUERY_TEMPLATES))

    query_json_parser = sub.add_parser("query-json")
    query_json_parser.add_argument("--workspace", required=True)
    query_json_parser.add_argument("--query-id", required=True, choices=sorted(QUERY_TEMPLATES))

    validate_parser = sub.add_parser("validate-wrapped")
    validate_parser.add_argument("--workspace", required=True)
    validate_parser.add_argument("--expected-shape", action="append", default=[])
    validate_parser.add_argument("--expected-file", action="append", default=[])
    validate_parser.add_argument("--expected-count", type=int, required=True)
    validate_parser.add_argument("--negative", action="store_true")
    return parser


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    operation = args.operation.replace("-", "_")
    if operation not in ALLOWED_OPERATIONS:
        raise AdapterError(f"unsupported adapter operation: {args.operation}")
    if args.operation == "help":
        return operation_help()
    if args.operation == "reject-denied":
        return operation_reject_denied(args.command)
    if args.operation == "init":
        return operation_init(args.workspace, args.kit)
    if args.operation == "sync":
        return operation_sync(args.workspace)
    if args.operation == "list-json":
        return operation_list_json(args.workspace)
    if args.operation == "query":
        return operation_query(args.workspace, args.query_id, json_output=False)
    if args.operation == "query-json":
        return operation_query(args.workspace, args.query_id, json_output=True)
    if args.operation == "validate-wrapped":
        return operation_validate_wrapped(
            args.workspace,
            args.expected_shape,
            args.expected_file,
            args.expected_count,
            args.negative,
        )
    raise AdapterError(f"unhandled adapter operation: {args.operation}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        record = dispatch(args)
    except AdapterError as exc:
        started = monotonic_ms()
        record = base_record(args.operation.replace("-", "_"), None, [])
        record["classification"] = "blocked"
        record["stderr_digest"] = str(exc)
        finalize_record(record, started)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0 if record["classification"] in {"pass", "rejected", "git-lex-fail"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
