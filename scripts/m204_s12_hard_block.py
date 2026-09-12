#!/usr/bin/env python3
"""Compose and verify the S12 validate hard-block carrier.

This is a bounded, subprocess-only evidence composer. It does not call GSD,
read lifecycle state, walk a corpus, or alter historical receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import m204_s12_failure_probe as probe

SCHEMA = "law-nexus/gsd-validate-hard-block/v1"
ABORT_MESSAGE = "technical verdict requires the current criterion and matching settled attempt"
MANIFEST_SCHEMA = "law-nexus/m204-s12-frozen-hashes/v1"
IDENTITY = Path("prd/migration/rust-evidence/m204-s12-failed-file.json")


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def relative_source(path: str, repo: Path) -> Path:
    value = Path(path)
    if value.is_absolute() or ".." in value.parts or ".gsd" in value.parts:
        raise ValueError(f"source path is not repository-relative: {path}")
    target = repo / value
    if not target.is_file():
        raise ValueError(f"missing source evidence: {path}")
    return value


def load_identity(repo: Path) -> dict[str, Any]:
    value = json.loads((repo / IDENTITY).read_text(encoding="utf-8"))
    probe.validate_identity(value, repo)
    if value["identity_status"] != "resolved":
        raise ValueError("S12 identity is not resolved")
    return value


def verify_manifest(value: dict[str, Any], repo: Path) -> None:
    if set(value) != {"schema", "scope", "files", "non_claims"}:
        raise ValueError("frozen manifest has extra or missing keys")
    if value["schema"] != MANIFEST_SCHEMA or not isinstance(value["files"], list):
        raise ValueError("frozen manifest schema mismatch")
    for row in value["files"]:
        if set(row) != {"path", "sha256", "size_bytes"}:
            raise ValueError("frozen manifest file row is not closed")
        path = relative_source(row["path"], repo)
        if (
            row["sha256"] != digest(repo / path)
            or row["size_bytes"] != (repo / path).stat().st_size
        ):
            raise ValueError(f"frozen source changed: {path}")


def verify_record(value: dict[str, Any], repo: Path) -> None:
    required = {
        "schema",
        "milestone",
        "slice",
        "abort_message",
        "engine_fix",
        "upstream_issue",
        "law_nexus_fixable",
        "s12_called_validate_milestone",
        "s12_identity_resolved",
        "s10_receipts_byte_identical",
        "status_effect",
        "findings",
        "classification",
        "marker",
        "frozen_manifest",
    }
    if set(value) != required:
        raise ValueError("hard-block record has extra or missing keys")
    expected = {
        "schema": SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S12",
        "abort_message": ABORT_MESSAGE,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "law_nexus_fixable": False,
        "s12_called_validate_milestone": False,
        "s12_identity_resolved": True,
        "s10_receipts_byte_identical": True,
        "status_effect": "unchanged",
        "classification": "supporting-only",
        "marker": "S12_T03_HARD_BLOCK_OK",
    }
    for key, expected_value in expected.items():
        if value[key] != expected_value:
            raise ValueError(f"hard-block contradiction in {key}")
    if value["findings"] != ["open"]:
        raise ValueError("findings must remain open")
    if not isinstance(value["frozen_manifest"], str):
        raise ValueError("frozen manifest path is not closed")
    manifest = relative_source(value["frozen_manifest"], repo)
    verify_manifest(json.loads((repo / manifest).read_text(encoding="utf-8")), repo)
    identity = load_identity(repo)
    if identity["s10_bytes_rewritten"] is not False:
        raise ValueError("identity permits historical rewrite")


def compose(repo: Path, out: Path, manifest: Path) -> None:
    identity = load_identity(repo)
    manifest_value = json.loads(manifest.read_text(encoding="utf-8"))
    verify_manifest(manifest_value, repo)
    value = {
        "schema": SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S12",
        "abort_message": ABORT_MESSAGE,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "law_nexus_fixable": False,
        "s12_called_validate_milestone": False,
        "s12_identity_resolved": identity["identity_status"] == "resolved",
        "s10_receipts_byte_identical": identity["s10_bytes_rewritten"] is False,
        "status_effect": "unchanged",
        "findings": ["open"],
        "classification": "supporting-only",
        "marker": "S12_T03_HARD_BLOCK_OK",
        "frozen_manifest": manifest.relative_to(repo).as_posix(),
    }
    verify_record(value, repo)
    encoded = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if out.exists():
        if out.read_text(encoding="utf-8") != encoded:
            raise ValueError("hard-block output already exists and differs")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(encoded, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "verify"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("prd/migration/rust-evidence/m204-s12-validate-hard-block.json"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("prd/migration/rust-evidence/m204-s12-frozen-hashes.json"),
    )
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    try:
        if args.command == "compose":
            compose(repo, repo / args.out, repo / args.manifest)
        else:
            value = json.loads((repo / args.out).read_text(encoding="utf-8"))
            verify_record(value, repo)
            print("S12_T03_HARD_BLOCK_OK")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"m204_s12_hard_block: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
