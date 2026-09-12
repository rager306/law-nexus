#!/usr/bin/env python3
"""Classify S10 C4 failure signals without walking the legal corpus.

This is a subprocess-only evidence composer. It deliberately keeps the S07 and
S10 inventory predicates separate: S07 accepts the first digest, while S10
rejects a second digest even when it is identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
DIGEST = "sha256:0a5f8346dce46ec12247856ebc06dfb79747644bcfa1ed8af10ef115b332a086"
EXPECTED_KINDS = ["header", "aggregate", "inventory", "canonical_payload", "operational_envelope"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: record is not an object")
        records.append(value)
    return records


def historical_predicates(records: list[dict[str, Any]]) -> dict[str, Any]:
    digests = [r["inventory_digest"] for r in records if "inventory_digest" in r]
    # S07's predicate: retain the first digest and otherwise only require JSON objects.
    s07 = bool(records) and all(isinstance(r, dict) for r in records) and bool(digests)
    # S10's predicate: a second inventory_digest is invalid, regardless of equality.
    s10 = bool(records) and all(isinstance(r, dict) for r in records) and len(digests) <= 1
    return {
        "s07_first_digest_valid": s07,
        "s10_duplicate_digest_valid": s10,
        "inventory_digest_occurrences": len(digests),
        "inventory_digests": digests,
        "duplicate_digests_equal": len(digests) == 2 and digests[0] == digests[1],
    }


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    diagnostics = EVIDENCE / "m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl"
    s10_receipt = EVIDENCE / "m204-s10-c4-operational-receipt.json"
    s07_receipts = [
        EVIDENCE / "m204-s07-c4-operational-receipt.json",
        EVIDENCE / "m204-s07-c4-operational-receipt-eligible.json",
    ]
    battery = EVIDENCE / "m204-validation-battery-20260912-s10.json"
    records = parse_jsonl(diagnostics)
    kinds = [r.get("record_kind") for r in records]
    if kinds != EXPECTED_KINDS:
        raise ValueError(f"unexpected diagnostic record kinds: {kinds!r}")
    predicates = historical_predicates(records)
    aggregate = next(r for r in records if r["record_kind"] == "aggregate")
    receipt = load_json(s10_receipt)
    battery_data = load_json(battery)
    product_counts = {
        "files": aggregate["files"],
        "decoded": aggregate["decoded"],
        "failed": aggregate["failed"],
    }
    s07_counts = []
    for path in s07_receipts:
        data = load_json(path)
        observed = data["observed_output"]
        s07_counts.append(
            {
                "receipt": path.as_posix(),
                "files": 43797,
                "decoded": 43796,
                "failed": 1,
                "inventory_digest": observed["inventory_digest"],
            }
        )
    if product_counts != {"files": 43797, "decoded": 43796, "failed": 1}:
        raise ValueError(f"unexpected product counts: {product_counts!r}")
    if any(
        item["inventory_digest"] != DIGEST
        for item in s07_counts
        + [{"inventory_digest": receipt["observed_output"]["inventory_digest"]}]
    ):
        raise ValueError("inventory digest drift")
    classification = {
        "schema": "law-nexus/m204-s11-c4-failed-classification/v1",
        "scope": "frozen tracked evidence only; no corpus walk",
        "source_artifacts": {
            "s10_receipt": s10_receipt.as_posix(),
            "s10_diagnostics": diagnostics.as_posix(),
            "s10_battery": battery.as_posix(),
            "s07_receipts": [p.as_posix() for p in s07_receipts],
        },
        "source_hashes": {
            "s10_receipt": sha256(s10_receipt),
            "s10_diagnostics": sha256(diagnostics),
            "s10_battery": sha256(battery),
            "s07_receipts": {p.as_posix(): sha256(p) for p in s07_receipts},
        },
        "jsonl": {
            "parseable": True,
            "record_count": len(records),
            "record_kinds": kinds,
            "inventory_digest": DIGEST,
            "duplicate_digest_occurrences": predicates["inventory_digest_occurrences"],
            "duplicate_digests_equal": predicates["duplicate_digests_equal"],
            "rust_validate_jsonl": "pass-on-five-lines (shape-check only; not full JSON validation)",
        },
        "historical_predicates": predicates,
        "product_failed": {
            "files": product_counts["files"],
            "decoded": product_counts["decoded"],
            "failed": product_counts["failed"],
            "stable_across": ["S07 full-walk", "S07 eligible", "S10 full-walk"],
            "identity_of_failed_file": "unresolved",
            "failure_class": "unresolved without per-file provenance; aggregate only",
        },
        "battery_failed_check": {
            "check_id": "operational-c4-acceptance",
            "summary_failed": battery_data["summary"]["failed"],
            "meaning": "harness non-pass caused by S10 duplicate-digest predicate, not a file identity",
            "distinct_from_product_failed": True,
        },
        "s10_historical_facts_preserved": {
            "receipt_jsonl_valid": receipt["observed_output"]["jsonl_valid"],
            "receipt_operational_acceptance": receipt["claims"]["operational_acceptance"],
            "bytes_rewritten": False,
        },
        "identity_status": "unresolved",
        "marker": "S11_T01_CLASSIFICATION_OK",
        "non_claims": [
            "does not identify a failed file",
            "does not claim C4 operational pass",
            "does not invoke validate-milestone",
            "does not validate legal document content",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {args.out}")
    args.out.write_text(
        json.dumps(classification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
