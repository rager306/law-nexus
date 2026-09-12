#!/usr/bin/env python3
"""Compose and verify the bounded S13 source-bound S07 parser binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/m204-s13-s07-source-binding/v1"
PARSER_REVISION = "m204-s04-c4-contour-v1"
HISTORICAL_SOURCE = "sha256:e53a0961c8ecfaf8fcc133da1b37efcbca9dcbd41ffba28e842fa6d7de34d3a4"
SOURCE_REL = "crates/ln-consultant-parser/src/contour_diagnostics.rs"
ARTIFACT_REL = "prd/migration/rust-evidence/m204-s13-s07-source-binding.json"

PINNED = {
    "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json": "sha256:f515e76bf757fb4e1143fc558b00ba7033ec383f586506085a9d2748ac5fbdab",
    "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json": "sha256:7c8e598779caa685ba978b29eca5f122f74e1cf81e4b437c132dc52f7eee7d69",
    "prd/migration/rust-evidence/m204-s07-c4-attempts/full-walk-001/diagnostics.jsonl": "sha256:3fe616e89a97a6eb83650c6a2c55b06e29d30e36c65a41f4719f016146ed49e4",
    "prd/migration/rust-evidence/m204-s07-c4-attempts/eligible-run-001/diagnostics.jsonl": "sha256:ad6437a2aed37cf08392f31a67e96aac762c3ea20147a3c62cc976c8c6b364f7",
    "prd/migration/rust-evidence/m204-s07-verification-battery.json": "sha256:f061af4342a75c6c0290f087f4503c74839f7f828b4081bfee7a4422fd408595",
}


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def contained(repo: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("path must be repository-relative without traversal")
    resolved = (repo / path).resolve(strict=True)
    try:
        resolved.relative_to(repo.resolve())
    except ValueError as exc:
        raise ValueError("path escapes repository containment") from exc
    if not resolved.is_file():
        raise ValueError("pinned path is not a regular file")
    return resolved


def parser_revision(repo: Path) -> str:
    text = contained(repo, SOURCE_REL).read_text(encoding="utf-8")
    marker = 'pub const PARSER_REVISION: &str = "'
    start = text.index(marker) + len(marker)
    return text[start : text.index('"', start)]


def pins(repo: Path) -> list[dict[str, Any]]:
    result = []
    for path, expected in PINNED.items():
        actual_path = contained(repo, path)
        actual = digest(actual_path)
        if actual != expected:
            raise ValueError(f"historical pin mismatch: {path}")
        result.append({"path": path, "sha256": actual, "size_bytes": actual_path.stat().st_size})
    return result


def compose(repo: Path) -> dict[str, Any]:
    current = digest(contained(repo, SOURCE_REL))
    revision = parser_revision(repo)
    if revision != PARSER_REVISION:
        raise ValueError("live parser revision mismatch")
    return {
        "schema": SCHEMA,
        "historical": {"parser_source_sha256": HISTORICAL_SOURCE},
        "current": {"parser_source_sha256": current},
        "parser_revision": revision,
        "cause": "S12 additive sidecar npa-contour-failure-trace/v1",
        "canonical_five_record_jsonl_changed": False,
        "historical_receipts": pins(repo),
        "s07_bytes_rewritten": False,
        "status_effect": "unchanged",
        "classification": "supporting-only",
    }


def validate(value: Any, repo: Path) -> None:
    if not isinstance(value, dict):
        raise ValueError("binding must be an object")
    required = {
        "schema",
        "historical",
        "current",
        "parser_revision",
        "cause",
        "canonical_five_record_jsonl_changed",
        "historical_receipts",
        "s07_bytes_rewritten",
        "status_effect",
        "classification",
    }
    if set(value) != required:
        raise ValueError("binding schema is not closed")
    if value["schema"] != SCHEMA or value["parser_revision"] != PARSER_REVISION:
        raise ValueError("binding schema or revision mismatch")
    for key in ("historical", "current"):
        if not isinstance(value[key], dict) or set(value[key]) != {"parser_source_sha256"}:
            raise ValueError("source epoch object is not closed")
        if not isinstance(value[key]["parser_source_sha256"], str) or not value[key][
            "parser_source_sha256"
        ].startswith("sha256:"):
            raise ValueError("source digest is malformed")
    if value["historical"]["parser_source_sha256"] != HISTORICAL_SOURCE:
        raise ValueError("historical source digest is not the frozen baseline")
    if value["current"]["parser_source_sha256"] != digest(contained(repo, SOURCE_REL)):
        raise ValueError("current source digest does not match live file")
    if parser_revision(repo) != value["parser_revision"]:
        raise ValueError("binding revision does not match live parser")
    if (
        value["cause"] != "S12 additive sidecar npa-contour-failure-trace/v1"
        or value["canonical_five_record_jsonl_changed"] is not False
    ):
        raise ValueError("cause or canonical payload claim mismatch")
    if (
        value["s07_bytes_rewritten"] is not False
        or value["status_effect"] != "unchanged"
        or value["classification"] != "supporting-only"
    ):
        raise ValueError("binding makes an impermissible lifecycle claim")
    entries = value["historical_receipts"]
    if not isinstance(entries, list) or len(entries) != len(PINNED):
        raise ValueError("binding must contain exactly five historical pins")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size_bytes"}:
            raise ValueError("receipt pin is not closed")
        path = entry["path"]
        if path in seen or path not in PINNED:
            raise ValueError("receipt pin set is missing, duplicate, or extra")
        seen.add(path)
        actual_path = contained(repo, path)
        if (
            entry["sha256"] != PINNED[path]
            or entry["sha256"] != digest(actual_path)
            or entry["size_bytes"] != actual_path.stat().st_size
        ):
            raise ValueError(f"receipt pin mismatch: {path}")
        if path in {
            "prd/migration/rust-evidence/m204-s07-c4-operational-receipt.json",
            "prd/migration/rust-evidence/m204-s07-c4-operational-receipt-eligible.json",
        }:
            receipt = json.loads(actual_path.read_text(encoding="utf-8"))
            if (
                receipt.get("parser_revision") != PARSER_REVISION
                or receipt.get("build_inputs", {}).get("parser_source_sha256") != HISTORICAL_SOURCE
            ):
                raise ValueError("historical receipt parser binding mismatch")
    if seen != set(PINNED):
        raise ValueError("historical pin set mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "verify"))
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--artifact", type=Path, default=ROOT / ARTIFACT_REL)
    args = parser.parse_args()
    repo = args.repo.resolve()
    artifact = args.artifact if args.artifact.is_absolute() else repo / args.artifact
    if args.command == "compose":
        value = compose(repo)
        encoded = json.dumps(value, indent=2) + "\n"
        if artifact.exists():
            if artifact.read_text(encoding="utf-8") != encoded:
                raise ValueError("binding artifact already exists and differs")
        else:
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(encoded, encoding="utf-8")
    else:
        value = json.loads(artifact.read_text(encoding="utf-8"))
        validate(value, repo)
        print("S13_T01_BINDING_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"binding verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
