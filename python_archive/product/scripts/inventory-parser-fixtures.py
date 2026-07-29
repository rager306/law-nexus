#!/usr/bin/env python3
"""Inventory canonical parser fixtures for source hygiene (M006, M072).

Thin CLI wrapper for the M076 onion migration. Reusable inventory logic lives in
``law_nexus.adapters.sources.filesystem_inventory`` and is invoked through the
composition-root use case. The legacy function names are re-exported here so
existing script-level tests and downstream proof scripts remain compatible while
migration proceeds wave by wave.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from law_nexus.adapters.observability.job_ledger import append_job_ledger_record
from law_nexus.adapters.observability.source_inventory_ledger import (
    SourceInventoryLedgerContext,
    build_source_inventory_artifact_written,
    build_source_inventory_built,
    build_source_inventory_job_failed,
    build_source_inventory_job_queued,
    build_source_inventory_scan_started,
)
from law_nexus.adapters.sources.filesystem_inventory import (
    CANONICAL_CONSULTANT_XML_PATH,
    CONSULTANT_FULL_ACT_XML_PATH,
    JSON_OUTPUT,
    MARKDOWN_OUTPUT,
    NON_CLAIMS,
    OBSERVED_PP_FIXTURE_PATH,
    REMOVED_DUPLICATE_PATH,
    SCHEMA_VERSION,
    SCRIPT_PATH,
    STATED_PP_FIXTURE_PATH,
    InventoryError,
    artifact_sha_mismatch_errors,
    build_fixture_hygiene,
    build_inventory,
    build_parser_fixture_inventory,
    check_outputs,
    classify_document_type,
    discover_fixtures,
    extract_consultant_title_first_line,
    find_internal_duplicates,
    fixture_ok,
    inspect_fixture,
    inspect_odt,
    observability_summary,
    render_markdown,
    sha256_file,
    write_outputs,
    xml_name_observations,
    xml_summary_from_bytes,
    xml_summary_from_file,
)
from law_nexus.composition import make_parser_inventory_use_case

_MAX_LEDGER_ERROR_MESSAGE_LENGTH = 300
_UNSAFE_LEDGER_ERROR_MARKERS = (
    "GIGACHAT_AUTH_DATA",
    "OPENAI_API_KEY",
    "provider_payload",
    "raw_legal_text",
    "-----BEGIN",
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated artifacts are current without writing them",
    )
    parser.add_argument(
        "--ledger-jsonl",
        type=Path,
        help="append bounded source inventory job ledger events to this JSONL path",
    )
    return parser.parse_args(argv)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _ledger_context(manifest: dict[str, object]) -> SourceInventoryLedgerContext:
    manifest_fingerprint = _sha256_json(manifest)
    short_hash = manifest_fingerprint.removeprefix("sha256:")[:12]
    return SourceInventoryLedgerContext(
        trace_id=f"trace-source-inventory-{short_hash}",
        correlation_id=f"corr-source-inventory-{short_hash}",
        job_id=f"job-source-inventory-{short_hash}",
        source_ref="law-source",
        artifact_ref=str(JSON_OUTPUT),
        input_fingerprint=manifest_fingerprint,
    )


def _bounded_ledger_error_message(errors: list[str]) -> str:
    message = "; ".join(errors)
    for marker in _UNSAFE_LEDGER_ERROR_MARKERS:
        message = message.replace(marker, "[redacted]")
    if len(message) > _MAX_LEDGER_ERROR_MESSAGE_LENGTH:
        return message[: _MAX_LEDGER_ERROR_MESSAGE_LENGTH - 1] + "…"
    return message


def _append_inventory_ledger_events(
    *,
    ledger_path: Path,
    manifest: dict[str, object],
    check_mode: bool,
    errors: list[str],
) -> None:
    context = _ledger_context(manifest)
    output_fingerprint = _sha256_json(observability_summary(manifest))
    produced_artifacts = (str(JSON_OUTPUT), str(MARKDOWN_OUTPUT))
    append_job_ledger_record(
        ledger_path,
        build_source_inventory_job_queued(context, ts=_utc_now()),
    )
    append_job_ledger_record(
        ledger_path,
        build_source_inventory_scan_started(context, ts=_utc_now()),
    )
    if errors:
        append_job_ledger_record(
            ledger_path,
            build_source_inventory_job_failed(
                context,
                ts=_utc_now(),
                reason_code="validation_failed",
                error_code="source_inventory_check_failed",
                error_class="InventoryError",
                error_message=_bounded_ledger_error_message(errors),
                recovery_instruction="Regenerate parser fixture inventory artifacts or inspect source fixtures.",
            ),
        )
        return
    append_job_ledger_record(
        ledger_path,
        build_source_inventory_built(
            context,
            ts=_utc_now(),
            output_fingerprint=output_fingerprint,
            produced_artifacts=produced_artifacts,
            reason_code="inventory_reused" if check_mode else "inventory_built",
        ),
    )
    append_job_ledger_record(
        ledger_path,
        build_source_inventory_artifact_written(
            context,
            ts=_utc_now(),
            output_fingerprint=output_fingerprint,
            produced_artifacts=produced_artifacts,
            reason_code="artifact_fresh" if check_mode else "artifact_written",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    manifest = make_parser_inventory_use_case().build_parser_fixture_inventory(root)
    if args.check:
        errors = check_outputs(root, manifest)
        if args.ledger_jsonl is not None:
            _append_inventory_ledger_events(
                ledger_path=args.ledger_jsonl,
                manifest=manifest,
                check_mode=True,
                errors=errors,
            )
        print(json.dumps(observability_summary(manifest), ensure_ascii=False, sort_keys=True))
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        return 0
    write_outputs(root, manifest)
    if args.ledger_jsonl is not None:
        _append_inventory_ledger_events(
            ledger_path=args.ledger_jsonl,
            manifest=manifest,
            check_mode=False,
            errors=[],
        )
    print(json.dumps(observability_summary(manifest), ensure_ascii=False, sort_keys=True))
    return 0 if manifest["status"] == "pass" else 1


__all__ = [
    "CANONICAL_CONSULTANT_XML_PATH",
    "CONSULTANT_FULL_ACT_XML_PATH",
    "JSON_OUTPUT",
    "MARKDOWN_OUTPUT",
    "NON_CLAIMS",
    "OBSERVED_PP_FIXTURE_PATH",
    "REMOVED_DUPLICATE_PATH",
    "SCHEMA_VERSION",
    "SCRIPT_PATH",
    "STATED_PP_FIXTURE_PATH",
    "InventoryError",
    "artifact_sha_mismatch_errors",
    "build_fixture_hygiene",
    "build_inventory",
    "build_parser_fixture_inventory",
    "check_outputs",
    "classify_document_type",
    "discover_fixtures",
    "extract_consultant_title_first_line",
    "find_internal_duplicates",
    "fixture_ok",
    "inspect_fixture",
    "inspect_odt",
    "_append_inventory_ledger_events",
    "_ledger_context",
    "_sha256_json",
    "main",
    "observability_summary",
    "parse_args",
    "render_markdown",
    "sha256_file",
    "write_outputs",
    "xml_name_observations",
    "xml_summary_from_bytes",
    "xml_summary_from_file",
]


if __name__ == "__main__":
    raise SystemExit(main())
