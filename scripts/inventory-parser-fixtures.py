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
import json
import sys
from pathlib import Path

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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated artifacts are current without writing them",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    manifest = make_parser_inventory_use_case().build_parser_fixture_inventory(root)
    if args.check:
        errors = check_outputs(root, manifest)
        print(json.dumps(observability_summary(manifest), ensure_ascii=False, sort_keys=True))
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        return 0
    write_outputs(root, manifest)
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
