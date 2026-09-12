#!/usr/bin/env python3
"""Validate the bounded, additive M204/S13 evidence aggregate.

The manifest is deliberately a frozen list of source-bound pins.  It does not
hash itself, read .gsd, walk the corpus, or promote any lifecycle state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import m204_s13_source_binding as binding

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/m204-s13-frozen-hashes/v1"
MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s13-frozen-hashes.json"
S13_BATTERY = ROOT / "prd/migration/rust-evidence/m204-s13-s07-verification-battery.json"

# This is the trust root for the aggregate.  It is intentionally not derived
# from the manifest being checked, preventing a self-consistent forged pin set.
PINS = {
    "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json": "sha256:f515e76bf757fb4e1143fc558b00ba7033ec383f586506085a9d2748ac5fbdab",
    "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json": "sha256:7c8e598779caa685ba978b29eca5f122f74e1cf81e4b437c132dc52f7eee7d69",
    "prd/migration/rust-evidence/m204-s07-c4-attempts/full-walk-001/diagnostics.jsonl": "sha256:3fe616e89a97a6eb83650c6a2c55b06e29d30e36c65a41f4719f016146ed49e4",
    "prd/migration/rust-evidence/m204-s07-c4-attempts/eligible-run-001/diagnostics.jsonl": "sha256:ad6437a2aed37cf08392f31a67e96aac762c3ea20147a3c62cc976c8c6b364f7",
    "prd/migration/rust-evidence/m204-s07-verification-battery.json": "sha256:f061af4342a75c6c0290f087f4503c74839f7f828b4081bfee7a4422fd408595",
    "prd/migration/rust-evidence/m204-s13-s07-source-binding.json": "sha256:10483c2a770bd3f5df3aa9df4ae26d8481033fa88f3a1ccdf4a4619f08520d68",
    "prd/migration/rust-evidence/m204-s13-s07-verification-battery.json": "sha256:e2953ea3d4336ebe44435c651046549388c5f1e4044784a084f22d44904938d4",
    "prd/migration/rust-evidence/m204-s12-frozen-hashes.json": "sha256:4ecaba1d7838a1a1b5f0484b39ef5764df43ff456ef95d7c134d6263b4041a66",
}


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def contained(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or "\\" in value or ".." in path.parts or ".gsd" in path.parts:
        raise ValueError(f"manifest path is not repository-relative: {value}")
    resolved = (ROOT / path).resolve(strict=True)
    resolved.relative_to(ROOT.resolve())
    if not resolved.is_file():
        raise ValueError(f"manifest source is not a file: {value}")
    return resolved


def load(path: Path = MANIFEST) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("S13 manifest must be an object")
    return value


def baseline_pins() -> dict[str, str]:
    return dict(PINS)


def validate(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"schema", "scope", "files", "non_claims"}:
        raise ValueError("S13 manifest has extra or missing keys")
    if (
        value["schema"] != SCHEMA
        or value["scope"] != "S13 serialized aggregate; tracked evidence only"
    ):
        raise ValueError("S13 manifest schema or scope mismatch")
    if value["non_claims"] != [
        "aggregate does not prove a new operational pass",
        "aggregate does not call validate-milestone or change lifecycle state",
        "historical S07-S12 and M203 evidence remains byte-immutable",
    ]:
        raise ValueError("S13 non-claims mismatch")
    files = value["files"]
    if not isinstance(files, list) or len(files) != len(PINS):
        raise ValueError("S13 manifest must contain the complete required pin set")
    expected = baseline_pins()
    seen: set[str] = set()
    for row in files:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size_bytes"}:
            raise ValueError("S13 manifest file row is not closed")
        path = row["path"]
        if path in seen or path not in expected:
            raise ValueError(f"S13 manifest pin is missing, duplicate, or extra: {path}")
        seen.add(path)
        actual = contained(path)
        if row["sha256"] != expected[path] or row["sha256"] != digest(actual):
            raise ValueError(f"S13 source drift: {path}")
        if row["size_bytes"] != actual.stat().st_size:
            raise ValueError(f"S13 source size drift: {path}")
    if seen != set(expected):
        raise ValueError("S13 manifest required pin set is incomplete")
    binding_path = ROOT / binding.ARTIFACT_REL
    binding.validate(json.loads(binding_path.read_text(encoding="utf-8")), ROOT)
    battery = json.loads(S13_BATTERY.read_text(encoding="utf-8"))
    if battery.get("source_binding") != digest(binding_path):
        raise ValueError("S13 battery source binding drift")
    if (
        battery.get("operational_acceptance") != "non-pass"
        or battery.get("classification") != "supporting-only"
    ):
        raise ValueError("S13 battery promotes operational acceptance")
    if (
        battery.get("status_effect") != "unchanged"
        or battery.get("s13_called_validate_milestone") is not False
    ):
        raise ValueError("S13 battery claims lifecycle change")


def compose() -> None:
    pins = baseline_pins()
    value = {
        "schema": SCHEMA,
        "scope": "S13 serialized aggregate; tracked evidence only",
        "files": [
            {"path": p, "sha256": h, "size_bytes": contained(p).stat().st_size}
            for p, h in pins.items()
        ],
        "non_claims": [
            "aggregate does not prove a new operational pass",
            "aggregate does not call validate-milestone or change lifecycle state",
            "historical S07-S12 and M203 evidence remains byte-immutable",
        ],
    }
    validate(value)
    encoded = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if MANIFEST.exists():
        if MANIFEST.read_text(encoding="utf-8") != encoded:
            raise ValueError("S13 frozen manifest exists and differs")
    else:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(encoded, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "verify"))
    args = parser.parse_args()
    try:
        if args.command == "compose":
            compose()
        else:
            validate(load())
            print("S13_MANIFEST_OK")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"m204_s13_evidence_verify: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
