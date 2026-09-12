#!/usr/bin/env python3
"""Verify the bounded M204/S14 evidence aggregate.

This verifier is intentionally additive and read-only in ``check`` mode.  Its
trust root is the literal pin table below, not the manifest under test.  It
binds S10/S11/S12/S13 evidence, while preserving the distinction between
integrity and operational C4 acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/m204-s14-frozen-hashes/v1"
MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s14-frozen-hashes.json"
BATTERY = ROOT / "prd/migration/rust-evidence/m204-s14-verification-battery.json"
S12_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s12-frozen-hashes.json"

# Deliberately independent of the S14 manifest.  A forged manifest therefore
# cannot make itself authoritative by repeating its own hashes.
PINS = {
    "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json": "sha256:0c7602c051102807d50767ac836f7627b1e213ffded55c665f1743a01bb15dac",
    "prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl": "sha256:177282f3a2e99c80f55b85b2a1568e1a9c80c35e7999f9b6bf42491de0379e35",
    "prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json": "sha256:7e735d8c10d5fddf84a0f0a164778c4d1576612d1b11e313dac96bf22a3248b8",
    "prd/migration/rust-evidence/m204-s11-c4-failed-classification.json": "sha256:d2c542d4538cdace8c11802479e3fc8e6697103db81435a0e3ccbd242cb12834",
    "prd/migration/rust-evidence/m204-s12-frozen-hashes.json": "sha256:4ecaba1d7838a1a1b5f0484b39ef5764df43ff456ef95d7c134d6263b4041a66",
    "prd/migration/rust-evidence/m204-s13-s07-source-binding.json": "sha256:10483c2a770bd3f5df3aa9df4ae26d8481033fa88f3a1ccdf4a4619f08520d68",
    "prd/migration/rust-evidence/m204-s13-s07-verification-battery.json": "sha256:e2953ea3d4336ebe44435c651046549388c5f1e4044784a084f22d44904938d4",
    "prd/migration/rust-evidence/m204-s13-frozen-hashes.json": "sha256:4c25ef0858f0a414e5a431c7f42d166cfcaec1b1ad019ec5a5b8395338cf5da9",
}


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or "\\" in value or ".." in path.parts:
        raise ValueError(f"source path is not repository-relative: {value}")
    if ".gsd" in path.parts or ".git" in path.parts:
        raise ValueError(f"source path is outside evidence boundary: {value}")
    resolved = (ROOT / path).resolve(strict=True)
    resolved.relative_to(ROOT.resolve())
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"source is not a regular file: {value}")
    return resolved


def load(path: Path) -> Any:
    value = json.loads(path.read_text(encoding="utf-8"))
    return value


def validate_s12_anchors() -> None:
    value = load(S12_MANIFEST)
    if not isinstance(value, dict) or value.get("schema") != "law-nexus/m204-s12-frozen-hashes/v1":
        raise ValueError("S12 manifest schema mismatch")
    rows = {row.get("path"): row for row in value.get("files", []) if isinstance(row, dict)}
    for path in (
        "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json",
        "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json",
        "prd/migration/rust-evidence/m204-s07-verification-battery.json",
    ):
        if path not in rows:
            raise ValueError(f"S07 anchor missing from S12 manifest: {path}")
        actual = safe_path(path)
        if (
            rows[path].get("sha256") != digest(actual)
            or rows[path].get("size_bytes") != actual.stat().st_size
        ):
            raise ValueError(f"S07 anchor drift in S12 manifest: {path}")


def validate_manifest(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"schema", "scope", "files", "non_claims"}:
        raise ValueError("S14 manifest has extra or missing keys")
    if (
        value["schema"] != SCHEMA
        or value["scope"] != "S14 aggregate; frozen tracked evidence only; no corpus walk"
    ):
        raise ValueError("S14 manifest schema or scope mismatch")
    if value["non_claims"] != [
        "integrity verification does not make C4 operational acceptance pass",
        "aggregate does not call validate-milestone or change lifecycle state",
        "historical S10-S13 evidence remains byte-immutable",
    ]:
        raise ValueError("S14 non-claims mismatch")
    files = value["files"]
    if not isinstance(files, list) or len(files) != len(PINS):
        raise ValueError("S14 manifest must contain the complete required pin set")
    seen: set[str] = set()
    for row in files:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size_bytes"}:
            raise ValueError("S14 manifest file row is not closed")
        path = row["path"]
        if path in seen or path not in PINS:
            raise ValueError(f"S14 pin is missing, duplicate, or extra: {path}")
        seen.add(path)
        actual = safe_path(path)
        if row["sha256"] != PINS[path] or row["sha256"] != digest(actual):
            raise ValueError(f"S14 source drift: {path}")
        if row["size_bytes"] != actual.stat().st_size:
            raise ValueError(f"S14 source size drift: {path}")
    if seen != set(PINS):
        raise ValueError("S14 required pin set is incomplete")
    validate_s12_anchors()


def validate_battery(value: Any) -> None:
    required = {
        "schema",
        "integrity",
        "c4_acceptance",
        "classification",
        "status_effect",
        "s14_called_validate_milestone",
        "consumer",
        "replay",
        "s13_distinction",
        "marker",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("S14 verification battery has extra or missing keys")
    if value["schema"] != "law-nexus/m204-s14-verification-battery/v1":
        raise ValueError("S14 battery schema mismatch")
    if value["integrity"] != "pass" or value["c4_acceptance"] != "non-pass":
        raise ValueError("S14 battery confuses integrity with acceptance")
    if (
        value["classification"] != "supporting-only"
        or value["status_effect"] != "unchanged"
        or value["s14_called_validate_milestone"] is not False
    ):
        raise ValueError("S14 battery makes an impermissible lifecycle claim")
    if value["consumer"] != {
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
        "integrity": "pass",
    }:
        raise ValueError("consumer result mismatch")
    if value["replay"] != {
        "operational_acceptance": "non-pass",
        "historical_binding": "valid",
        "live_binary_required": False,
    }:
        raise ValueError("historical replay result mismatch")
    if value["s13_distinction"] != {
        "operational_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
    }:
        raise ValueError("S13 distinction mismatch")
    if value["marker"] != "S14_VERIFY_OK":
        raise ValueError("S14 marker mismatch")


def compose() -> None:
    value = {
        "schema": SCHEMA,
        "scope": "S14 aggregate; frozen tracked evidence only; no corpus walk",
        "files": [
            {"path": path, "sha256": sha, "size_bytes": safe_path(path).stat().st_size}
            for path, sha in PINS.items()
        ],
        "non_claims": [
            "integrity verification does not make C4 operational acceptance pass",
            "aggregate does not call validate-milestone or change lifecycle state",
            "historical S10-S13 evidence remains byte-immutable",
        ],
    }
    validate_manifest(value)
    encoded = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if MANIFEST.exists():
        if MANIFEST.read_text(encoding="utf-8") != encoded:
            raise ValueError("S14 frozen manifest exists and differs")
    else:
        MANIFEST.write_text(encoded, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "verify"))
    args = parser.parse_args()
    try:
        if args.command == "compose":
            compose()
        else:
            validate_manifest(load(MANIFEST))
            validate_battery(load(BATTERY))
            print("S14_VERIFY_OK")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s14_evidence_verify: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
