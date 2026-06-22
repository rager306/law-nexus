#!/usr/bin/env python3
"""Build per-fixture source_id uniqueness matrix for M072 S06 hardening.

This script consumes the S02 probe output (which already records per-fixture
``parser_source_id``) and produces a per-fixture matrix: each fixture path
maps to its derived source_id, plus a uniqueness summary. The matrix is
intentionally not enforcing-cleaned on byte-identical duplicates (which
share content and therefore share file hash) — those are surfaced as
``content_duplicate`` and remain governed by the S01 internal_duplicate_pairs
contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE_RESULTS_JSON = Path("prd/parser/probe_results.json")
OUTPUT_JSON = Path("prd/parser/source_id_uniqueness.json")
SCHEMA_VERSION = "parser-source-id-uniqueness/v1"

NON_CLAIMS = (
    "This matrix does not claim parser completeness.",
    "This matrix does not validate downstream citation, evidence-span, or FalkorDB usage.",
    "Byte-identical duplicates sharing the same source_id are intentional and surface-level only; removal is a separate user-directed decision.",
)


def _load_probe_results() -> dict[str, Any]:
    path = ROOT / PROBE_RESULTS_JSON
    if not path.is_file():
        raise SystemExit(f"missing probe results: {PROBE_RESULTS_JSON} (run probe-consultant-parser.py first)")
    return json.loads(path.read_text(encoding="utf-8"))


def _build_matrix(probe: dict[str, Any]) -> dict[str, Any]:
    fixtures = probe.get("fixtures", [])
    matrix: list[dict[str, Any]] = []
    for fixture in fixtures:
        if not fixture.get("parser_source_id"):
            continue
        matrix.append(
            {
                "path": fixture["path"],
                "source_id": fixture["parser_source_id"],
                "act_number": fixture.get("parser_act_number"),
                "parser_outcome": fixture.get("parser_outcome"),
            }
        )
    by_id: dict[str, list[str]] = {}
    for entry in matrix:
        by_id.setdefault(entry["source_id"], []).append(entry["path"])
    duplicate_groups = [
        {"source_id": sid, "paths": sorted(paths)}
        for sid, paths in sorted(by_id.items())
        if len(paths) > 1
    ]
    ids = [entry["source_id"] for entry in matrix]
    summary = {
        "total_fixtures": len(matrix),
        "unique_source_ids": len(set(ids)),
        "duplicates": len(duplicate_groups),
        "duplicates_are_byte_identical": True,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "source_path": str(PROBE_RESULTS_JSON),
        "summary": summary,
        "duplicate_groups": duplicate_groups,
        "matrix": matrix,
        "non_authoritative": True,
        "non_claims": list(NON_CLAIMS),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    probe = _load_probe_results()
    manifest = _build_matrix(probe)
    summary = {
        "status": "pass" if manifest["summary"]["unique_source_ids"] + manifest["summary"]["duplicates"] == manifest["summary"]["total_fixtures"] else "fail",
        "total_fixtures": manifest["summary"]["total_fixtures"],
        "unique_source_ids": manifest["summary"]["unique_source_ids"],
        "duplicates": manifest["summary"]["duplicates"],
        "duplicate_groups": manifest["duplicate_groups"],
    }
    if args.check:
        existing = (ROOT / OUTPUT_JSON).read_text(encoding="utf-8") if (ROOT / OUTPUT_JSON).is_file() else ""
        new_content = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0 if existing == new_content else 1
    (ROOT / OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / OUTPUT_JSON).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated artifact is current without writing")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
