"""Command-line surface for the repository control-plane harness."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from law_nexus_harness.adr_matrix import (
    AdrMatrixError,
    build_adr_matrix,
    check_adr_matrix_output,
    render_adr_matrix,
)
from law_nexus_harness.governor import (
    GOVERNOR_CHECK_SPECS,
    GovernorSelectionError,
    format_governor_report_text,
    get_governor_check_spec,
    run_governor,
)
from law_nexus_harness.preflight import run_preflight
from law_nexus_harness.review_case import (
    NormalizationMethod,
    RegisterReviewCaseCommand,
    ReviewCaseApplicationError,
    SourceKind,
    register_review_case,
    review_case_inventory,
    review_case_status,
    validate_review_cases,
)
from law_nexus_harness.review_case.adapters.filesystem import (
    FilesystemReviewPacketStore,
    FilesystemReviewSourceReader,
)
from law_nexus_harness.review_case.adapters.filesystem_ledger import FilesystemEventLedger
from law_nexus_harness.review_case.adapters.hashlib_adapter import HashlibContentHasher
from law_nexus_harness.review_case.ports import ReviewCasePortError
from law_nexus_harness.review_case.report import render_failure_report, render_success_report
from law_nexus_harness.subprocess_runner import (
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    run_rust_binary,
)

DEFAULT_STATUS_BINARY = Path("target/debug/ln-status")
DEFAULT_REVIEW_PACKETS_DIR = "prd/architecture/review-cases/packets"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="law-nexus-harness", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    status = subcommands.add_parser("status", help="Run the Rust repository status tracer.")
    status.add_argument("--binary", type=Path, default=DEFAULT_STATUS_BINARY)
    status.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    status.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_OUTPUT_BYTES)
    governor = subcommands.add_parser(
        "governor",
        help=(
            "Run trajectory anti-drift checks for roadmap freshness, hostile proof "
            "chain coherence, and residual GSD debt."
        ),
    )
    governor.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    governor.add_argument("--only", help="Run one check group (for example: adr or semantic).")
    governor.add_argument("--check", help="Run one exact check ID.")
    governor.add_argument("--explain", help="Explain one check contract without running it.")
    governor.add_argument(
        "--list-checks",
        action="store_true",
        help="List the machine-readable Governor check inventory without running checks.",
    )
    governor.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Return exit 1 when executed checks retain advisory warnings; default remains exit 0.",
    )
    governor.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format for executed checks (default: json).",
    )
    governor.add_argument(
        "--json",
        action="store_true",
        help="Compatibility alias for --format json (Governor default is already json).",
    )
    adr_verify = subcommands.add_parser(
        "adr-verify",
        help="Generate or check the non-authoritative ADR metadata matrix.",
    )
    adr_verify.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    adr_verify.add_argument("--matrix", choices=("generate", "check"), required=True)
    adr_verify.add_argument(
        "--stdout",
        action="store_true",
        help="Emit generated matrix to stdout; required for generate.",
    )
    adr_verify.add_argument(
        "--output",
        type=Path,
        help="Explicit derived matrix path for check; authority paths are rejected.",
    )
    preflight = subcommands.add_parser(
        "preflight",
        help="Run early non-mutating repository preflight checks before completion/commit.",
    )
    preflight.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    review_case = subcommands.add_parser(
        "review-case",
        help=(
            "Non-authoritative Review Case register/validate/status/inventory "
            "operations. Does not promote authority or create GSD work."
        ),
    )
    review_case.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    review_case.add_argument(
        "--packets-dir",
        default=DEFAULT_REVIEW_PACKETS_DIR,
        help=(
            f"Repository-relative packet store directory (default: {DEFAULT_REVIEW_PACKETS_DIR})."
        ),
    )
    review_ops = review_case.add_subparsers(dest="review_case_command", required=True)
    register = review_ops.add_parser(
        "register",
        help="Register an immutable review source as a draft Review Case packet.",
    )
    register.add_argument("--packet-id", required=True)
    register.add_argument("--source-path", required=True)
    register.add_argument("--reviewed-revision", required=True)
    register.add_argument("--received-at", required=True)
    register.add_argument(
        "--source-kind",
        choices=tuple(item.value for item in SourceKind),
        default=SourceKind.HUMAN_EXTERNAL.value,
    )
    register.add_argument(
        "--normalization-method",
        choices=tuple(item.value for item in NormalizationMethod),
        default=NormalizationMethod.MANUAL.value,
    )
    register.add_argument(
        "--non-claim",
        action="append",
        default=[],
        dest="non_claims",
        help="Additional packet non-claim (repeatable).",
    )
    register.add_argument("--extractor-version", default=None)
    review_ops.add_parser(
        "validate",
        help="Validate stored packets against source hashes and pure policy.",
    )
    status_cmd = review_ops.add_parser(
        "status",
        help="Report deterministic non-authoritative packet/finding status rollups.",
    )
    status_cmd.add_argument("--packet-id", default=None)
    inventory_cmd = review_ops.add_parser(
        "inventory",
        help=(
            "Project multi-axis FSM residual inventory (read-only stage continuity). "
            "Does not record dispositions or create GSD work."
        ),
    )
    inventory_cmd.add_argument("--packet-id", default=None)
    return parser


def _review_case_exit_class(code: str, *, cause_code: str | None = None) -> str:
    """Map failure codes to CLI exit class.

    exit 1 = validation/policy/user-correctable
    exit 2 = tool/adapter/infrastructure failure
    """

    user_codes = {
        "duplicate_packet",
        "invalid_path",
        "invalid_packet_id",
        "invalid_packet",
        "invalid_store_path",
        "source_hash_drift",
        "packet_not_found",
    }
    tool_codes = {
        "source_not_found",
        "source_read_failed",
        "source_not_file",
        "store_unavailable",
        "store_write_failed",
        "store_read_failed",
        "store_list_failed",
        "corrupt_packet",
        "corrupt_envelope",
        "corrupt_ledger",
        "ledger_unavailable",
        "ledger_read_failed",
        "ledger_list_failed",
        "ledger_write_failed",
        "symlink_rejected",
        "path_escape",
        "hash_failed",
        "invalid_root",
        "invalid_hash_input",
        "unexpected_failure",
    }
    ledger_user_codes = {
        "ledger_gap_or_fork",
        "ledger_chain_break",
        "ledger_fork",
        "envelope_hash_mismatch",
        "event_hash_mismatch",
        "packet_id_mismatch",
        "envelope_name_mismatch",
        "duplicate_event_id",
        "invalid_event_id",
        "invalid_source_revision",
        "invalid_event",
        "base_packet_not_clean",
        "unsupported_replay_event",
        "ledger_projection_mismatch",
    }
    user_codes = user_codes | ledger_user_codes
    if code in user_codes:
        return "validation-error"
    if code in tool_codes:
        return "tool-error"
    if cause_code in {"read_bytes", "add", "get", "list_all", "sha256", "__init__"}:
        return "tool-error"
    # Pure policy / domain validation codes and unknown application codes default to exit 1.
    return "validation-error"


def _run_review_case(args: argparse.Namespace) -> int:
    operation = f"review-case.{args.review_case_command}"
    try:
        reader = FilesystemReviewSourceReader(args.root)
        hasher = HashlibContentHasher()
        store = FilesystemReviewPacketStore(args.root, packets_dir=args.packets_dir)
        # validate/status rematerialize base packets through the append-only ledger.
        # register remains base-only and does not invent human decisions.
        ledger = FilesystemEventLedger(args.root, packets_dir=args.packets_dir)
        if args.review_case_command == "register":
            non_claims = tuple(args.non_claims) or ("Non-authoritative review projection",)
            report = register_review_case(
                RegisterReviewCaseCommand(
                    packet_id=args.packet_id,
                    source_path=args.source_path,
                    reviewed_revision=args.reviewed_revision,
                    received_at=args.received_at,
                    source_kind=SourceKind(args.source_kind),
                    normalization_method=NormalizationMethod(args.normalization_method),
                    non_claims=non_claims,
                    extractor_version=args.extractor_version,
                ),
                reader,
                hasher,
                store,
            )
            sys.stdout.write(render_success_report(operation=operation, payload=report))
            return 0
        if args.review_case_command == "validate":
            report = validate_review_cases(reader, hasher, store, ledger=ledger)
            sys.stdout.write(render_success_report(operation=operation, payload=report))
            return 0
        if args.review_case_command == "status":
            report = review_case_status(store, packet_id=args.packet_id, ledger=ledger)
            sys.stdout.write(render_success_report(operation=operation, payload=report))
            return 0
        if args.review_case_command == "inventory":
            report = review_case_inventory(store, packet_id=args.packet_id, ledger=ledger)
            sys.stdout.write(render_success_report(operation=operation, payload=report))
            return 0
        raise AssertionError(f"unhandled review-case command: {args.review_case_command}")
    except ReviewCaseApplicationError as error:
        exit_class = _review_case_exit_class(error.code, cause_code=error.cause_code)
        sys.stdout.write(
            render_failure_report(
                operation=operation,
                code=error.code,
                message=error.message,
                exit_class=exit_class,
            )
        )
        return 2 if exit_class == "tool-error" else 1
    except ReviewCasePortError as error:
        exit_class = _review_case_exit_class(error.code, cause_code=error.operation)
        sys.stdout.write(
            render_failure_report(
                operation=operation,
                code=error.code,
                message=error.message,
                exit_class=exit_class,
            )
        )
        return 2 if exit_class == "tool-error" else 1
    except Exception:
        sys.stdout.write(
            render_failure_report(
                operation=operation,
                code="unexpected_failure",
                message="unexpected review-case CLI failure",
                exit_class="tool-error",
            )
        )
        return 2


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "governor" and getattr(args, "json", False):
        args.format = "json"
    if args.command == "status":
        result = run_rust_binary(
            args.binary,
            ["status"],
            timeout_seconds=args.timeout,
            max_output_bytes=args.max_output_bytes,
        )
        sys.stdout.write(result.to_json())
        return 0 if result.status == "ok" else 1
    if args.command == "governor":
        try:
            if args.list_checks:
                if args.only or args.check or args.explain or args.fail_on_warn:
                    raise GovernorSelectionError(
                        "conflicting-selectors",
                        "--list-checks cannot be combined with execution or explanation selectors",
                    )
                inventory = {
                    "schema_version": "law-nexus-governor-check-inventory/v1",
                    "non_authoritative": True,
                    "checks": [spec.to_explanation() for spec in GOVERNOR_CHECK_SPECS],
                    "non_claim": (
                        "Inventory presence does not validate repository state, product behavior, "
                        "legal correctness, or lifecycle."
                    ),
                }
                sys.stdout.write(
                    json.dumps(
                        inventory,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                return 0
            if args.explain:
                if args.only or args.check or args.fail_on_warn:
                    raise GovernorSelectionError(
                        "conflicting-selectors",
                        "--explain cannot be combined with execution selectors",
                    )
                explanation = get_governor_check_spec(args.explain).to_explanation()
                sys.stdout.write(
                    json.dumps(
                        explanation,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                return 0
            report = run_governor(args.root, only=args.only, check=args.check)
        except GovernorSelectionError as error:
            sys.stdout.write(
                json.dumps(
                    {
                        "schema_version": "law-nexus-governor-tool-error/v1",
                        "status": "tool-error",
                        "error": error.error,
                        "value": error.value,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
            return 2
        if args.format == "text":
            sys.stdout.write(format_governor_report_text(report))
        else:
            sys.stdout.write(report.to_json())
        if report.tool_error_count:
            return 2
        if args.fail_on_warn and report.warn_count:
            return 1
        return 0 if report.status == "ok" else 1
    if args.command == "adr-verify":
        try:
            if args.matrix == "generate":
                if not args.stdout or args.output is not None:
                    raise AdrMatrixError(
                        "invalid-matrix-output",
                        "generate requires --stdout and rejects --output",
                    )
                sys.stdout.write(render_adr_matrix(build_adr_matrix(args.root)))
                return 0
            if args.stdout or args.output is None:
                raise AdrMatrixError(
                    "invalid-matrix-output",
                    "check requires --output and rejects --stdout",
                )
            result = check_adr_matrix_output(args.root, args.output)
        except AdrMatrixError as error:
            sys.stdout.write(
                json.dumps(
                    {
                        "schema_version": "law-nexus-adr-matrix-tool-error/v1",
                        "status": "tool-error",
                        "error": error.error,
                        "value": error.value,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
            return 2
        sys.stdout.write(
            json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        )
        return 0 if result["status"] == "ok" else 1
    if args.command == "preflight":
        report = run_preflight(args.root)
        sys.stdout.write(report.to_json())
        return 0 if report.status == "ok" else 1
    if args.command == "review-case":
        return _run_review_case(args)
    raise AssertionError(f"unhandled command: {args.command}")
