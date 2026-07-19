#!/usr/bin/env python3
# ruff: noqa: E402
"""Build deterministic Consultant WordML norm candidate records.

This generator emits candidate-only NormStatement records from hierarchy
record excerpts containing deontic lexemes (obligation, permission,
prohibition). It preserves provenance but intentionally does not claim
legal correctness, parser completeness, product ETL readiness, or
FalkorDB loading/runtime readiness.

Per proposal 26 Section 8: bounded extraction, no legal-effect assertions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from law_nexus.adapters.sources.consultant_hierarchy import extract_norm_candidates  # noqa: E402

HIERARCHY_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_records.jsonl"
OUTPUT_PATH = ROOT / "prd" / "parser" / "consultant_norm_candidates.jsonl"

def load_hierarchy_records() -> list[dict[str, Any]]:
    """Load hierarchy records from JSONL."""

    if not HIERARCHY_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in HIERARCHY_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records

def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    """Write records as JSONL."""

    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

def build_and_write() -> dict[str, Any]:
    """Build norm candidates and write output."""

    hierarchy = load_hierarchy_records()
    candidates = extract_norm_candidates(hierarchy)
    write_jsonl(candidates, OUTPUT_PATH)

    modality_counts: dict[str, int] = {}
    for c in candidates:
        modality_counts[c["modality"]] = modality_counts.get(c["modality"], 0) + 1

    return {
        "candidate_count": len(candidates),
        "modality_breakdown": dict(sorted(modality_counts.items())),
        "output_path": str(OUTPUT_PATH),
        "status": "pass",
        "non_authoritative": True,
    }

def check_outputs() -> dict[str, Any]:
    """Check if outputs are fresh."""

    result = build_and_write()
    existing = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    fresh = len(existing.strip().splitlines()) == result["candidate_count"] if existing else False
    return {**result, "status": "pass" if fresh else "stale"}

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Write output artifacts")
    mode.add_argument("--check", action="store_true", help="Check freshness only")
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.check:
        result = check_outputs()
    else:
        result = build_and_write()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1

if __name__ == "__main__":
    raise SystemExit(main())
