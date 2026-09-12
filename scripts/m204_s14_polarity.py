#!/usr/bin/env python3
"""Bounded S14 consumer for the C4 acceptance polarity.

This additive harness consumes four frozen, tracked evidence surfaces.  It never
rewrites them, walks the corpus, calls validate-milestone, or treats integrity
of a receipt as operational acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/m204-s14-c4-acceptance/v1"
REQUIRED = {
    "s10_receipt": ROOT / "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json",
    "s10_battery": ROOT / "prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json",
    "s11_classification": ROOT
    / "prd/migration/rust-evidence/m204-s11-c4-failed-classification.json",
    "s13_battery": ROOT / "prd/migration/rust-evidence/m204-s13-s07-verification-battery.json",
}
EXPECTED_REASON = (
    "S10 duplicate inventory_digest in header and canonical_payload makes jsonl_valid=false"
)
EXPECTED_SUPERSESSION = {
    "from": "m204-s10-c4-operational-receipt.json",
    "to": "m204-s14-c4-acceptance.json",
    "reason": "S14 makes the non-pass acceptance polarity explicit without rewriting historical S10 evidence",
    "authorization": "bounded S14 roadmap scope; not user acceptance",
}


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def safe_source(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or "\\" in value or ".." in candidate.parts:
        raise ValueError(f"source path is not repository-relative: {value}")
    if ".gsd" in candidate.parts or ".git" in candidate.parts:
        raise ValueError(f"source path is outside tracked evidence boundary: {value}")
    resolved = (ROOT / candidate).resolve(strict=True)
    resolved.relative_to(ROOT.resolve())
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"source path is not a regular file: {value}")
    return resolved


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def source_row(path: Path, extracted: dict[str, Any]) -> dict[str, Any]:
    return {"path": rel(path), "sha256": digest(path), "extracted": extracted}


def compose(out: Path) -> None:
    receipt = load_json(REQUIRED["s10_receipt"])
    s10 = load_json(REQUIRED["s10_battery"])
    s11 = load_json(REQUIRED["s11_classification"])
    s13 = load_json(REQUIRED["s13_battery"])
    receipt_observed = receipt["observed_output"]
    value: dict[str, Any] = {
        "schema": SCHEMA,
        "scope": "S14 additive consumer; frozen tracked evidence only; no corpus walk",
        "c4_acceptance": "non-pass",
        "reason": EXPECTED_REASON,
        "distinct_from_product_failed": True,
        "integrity_pass_is_not_operational_pass": True,
        "s10_bytes_rewritten": False,
        "status_effect": "unchanged",
        "classification": "supporting-only",
        "s14_called_validate_milestone": False,
        "supersession": {
            **EXPECTED_SUPERSESSION,
            "preserved_hash": digest(REQUIRED["s10_receipt"]),
        },
        "surfaces": {
            "s10_receipt": source_row(
                REQUIRED["s10_receipt"],
                {
                    "schema": receipt["schema"],
                    "attempt_id": receipt["attempt_id"],
                    "jsonl_valid": receipt_observed["jsonl_valid"],
                    "operational_acceptance": receipt["claims"]["operational_acceptance"],
                    "inventory_digest": receipt_observed["inventory_digest"],
                },
            ),
            "s10_battery": source_row(
                REQUIRED["s10_battery"],
                {
                    "schema_version": s10["schema_version"],
                    "c4_observation": s10["c4"]["observation"],
                    "operational_acceptance": s10["c4"]["operational_acceptance"],
                    "jsonl_valid": s10["c4"]["jsonl_valid"],
                },
            ),
            "s11_classification": source_row(
                REQUIRED["s11_classification"],
                {
                    "schema": s11["schema"],
                    "duplicate_digest_occurrences": s11["jsonl"]["duplicate_digest_occurrences"],
                    "duplicate_digests_equal": s11["jsonl"]["duplicate_digests_equal"],
                    "distinct_from_product_failed": s11["battery_failed_check"][
                        "distinct_from_product_failed"
                    ],
                },
            ),
            "s13_battery": source_row(
                REQUIRED["s13_battery"],
                {
                    "schema": s13["schema"],
                    "operational_acceptance": s13["operational_acceptance"],
                    "classification": s13["classification"],
                    "status_effect": s13["status_effect"],
                },
            ),
        },
    }
    validate(value)
    encoded = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if out.exists():
        if out.read_text(encoding="utf-8") != encoded:
            raise ValueError(f"refusing to overwrite existing artifact: {out}")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(encoded, encoding="utf-8")


def validate(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("artifact must be an object")
    exact = {
        "schema",
        "scope",
        "c4_acceptance",
        "reason",
        "distinct_from_product_failed",
        "integrity_pass_is_not_operational_pass",
        "s10_bytes_rewritten",
        "status_effect",
        "classification",
        "s14_called_validate_milestone",
        "supersession",
        "surfaces",
    }
    if set(value) != exact:
        raise ValueError("artifact has missing or extra top-level keys")
    if (
        value["schema"] != SCHEMA
        or value["scope"] != "S14 additive consumer; frozen tracked evidence only; no corpus walk"
    ):
        raise ValueError("schema or scope mismatch")
    if value["c4_acceptance"] != "non-pass" or value["reason"] != EXPECTED_REASON:
        raise ValueError("C4 acceptance polarity is not the required non-pass reason")
    if (
        value["distinct_from_product_failed"] is not True
        or value["integrity_pass_is_not_operational_pass"] is not True
    ):
        raise ValueError("integrity/product distinction is not fail-closed")
    if value["s10_bytes_rewritten"] is not False or value["status_effect"] != "unchanged":
        raise ValueError("artifact claims mutation")
    if (
        value["classification"] != "supporting-only"
        or value["s14_called_validate_milestone"] is not False
    ):
        raise ValueError("artifact makes a lifecycle claim")
    if value["supersession"] != {
        **EXPECTED_SUPERSESSION,
        "preserved_hash": value["supersession"].get("preserved_hash"),
    }:
        raise ValueError("closed supersession contract mismatch")
    if not isinstance(value["supersession"]["preserved_hash"], str) or not value["supersession"][
        "preserved_hash"
    ].startswith("sha256:"):
        raise ValueError("missing preserved hash")
    surfaces = value["surfaces"]
    if not isinstance(surfaces, dict) or set(surfaces) != set(REQUIRED):
        raise ValueError("required surfaces are missing or extra")
    for name, row in surfaces.items():
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "extracted"}:
            raise ValueError(f"{name}: closed surface row required")
        path = safe_source(row["path"])
        if row["sha256"] != digest(path):
            raise ValueError(f"{name}: source hash mismatch")
        if not isinstance(row["extracted"], dict):
            raise ValueError(f"{name}: extracted fields must be object")
    receipt_path = safe_source(surfaces["s10_receipt"]["path"])
    battery_path = safe_source(surfaces["s10_battery"]["path"])
    classification_path = safe_source(surfaces["s11_classification"]["path"])
    s13_path = safe_source(surfaces["s13_battery"]["path"])
    receipt = load_json(receipt_path)
    battery = load_json(battery_path)
    classification = load_json(classification_path)
    s13 = load_json(s13_path)
    if value["supersession"]["preserved_hash"] != digest(receipt_path):
        raise ValueError("preserved S10 hash does not bind receipt")
    expected_extracted = {
        "s10_receipt": {
            "schema": receipt["schema"],
            "attempt_id": receipt["attempt_id"],
            "jsonl_valid": receipt["observed_output"]["jsonl_valid"],
            "operational_acceptance": receipt["claims"]["operational_acceptance"],
            "inventory_digest": receipt["observed_output"]["inventory_digest"],
        },
        "s10_battery": {
            "schema_version": battery["schema_version"],
            "c4_observation": battery["c4"]["observation"],
            "operational_acceptance": battery["c4"]["operational_acceptance"],
            "jsonl_valid": battery["c4"]["jsonl_valid"],
        },
        "s11_classification": {
            "schema": classification["schema"],
            "duplicate_digest_occurrences": classification["jsonl"]["duplicate_digest_occurrences"],
            "duplicate_digests_equal": classification["jsonl"]["duplicate_digests_equal"],
            "distinct_from_product_failed": classification["battery_failed_check"][
                "distinct_from_product_failed"
            ],
        },
        "s13_battery": {
            "schema": s13["schema"],
            "operational_acceptance": s13["operational_acceptance"],
            "classification": s13["classification"],
            "status_effect": s13["status_effect"],
        },
    }
    for name, expected in expected_extracted.items():
        if surfaces[name]["extracted"] != expected:
            raise ValueError(f"{name}: extracted fields do not match source bytes")
    if (
        receipt["observed_output"]["jsonl_valid"] is not False
        or receipt["claims"]["operational_acceptance"] != "non-pass"
    ):
        raise ValueError("forged S10 pass or jsonl validity")
    if (
        battery["c4"]["jsonl_valid"] is not False
        or battery["c4"]["operational_acceptance"] != "non-pass"
    ):
        raise ValueError("S10 battery does not preserve non-pass")
    if (
        classification["jsonl"]["duplicate_digest_occurrences"] != 2
        or classification["jsonl"]["duplicate_digests_equal"] is not True
    ):
        raise ValueError("duplicate inventory digest evidence missing")
    if classification["battery_failed_check"]["distinct_from_product_failed"] is not True:
        raise ValueError("product failure distinction missing")
    if (
        s13["operational_acceptance"] != "non-pass"
        or s13["classification"] != "supporting-only"
        or s13["status_effect"] != "unchanged"
    ):
        raise ValueError("S13 polarity drift")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check", "classify"))
    parser.add_argument(
        "--out", type=Path, default=ROOT / "prd/migration/rust-evidence/m204-s14-c4-acceptance.json"
    )
    args = parser.parse_args()
    try:
        if args.command == "compose":
            compose(args.out)
            print("S14_C4_ACCEPTANCE_COMPOSED")
        else:
            value = load_json(args.out)
            validate(value)
            if args.command == "check":
                print("S14_C4_ACCEPTANCE_CHECK_OK")
            else:
                print(
                    json.dumps(
                        {
                            "integrity": "pass",
                            "c4_acceptance": "non-pass",
                            "classification": "supporting-only",
                        },
                        separators=(",", ":"),
                    )
                )
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s14_polarity: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
