#!/usr/bin/env python3
"""Closed, source-bound attestation for the historical M204 S10 receipt replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/m204-s14-s10-source-binding/v1"
PARSER_REL = "crates/ln-consultant-parser/src/contour_diagnostics.rs"
RECEIPT_REL = "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json"
DIAGNOSTICS_REL = (
    "prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl"
)
BATTERY_REL = "prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json"
STDOUT_REL = "prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/stdout.log"
STDERR_REL = "prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/stderr.log"
CONTRACT_REL = "prd/architecture/npa-acceptance-contract.yaml"
PARSER_REVISION = "m204-s04-c4-contour-v1"


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def contained(repo: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("source-binding path must be relative and contained")
    repo = repo.resolve()
    resolved = (repo / path).resolve(strict=True)
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError("source-binding path escapes repository") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError("source-binding path must be a regular non-symlink file")
    return resolved


def parser_revision(repo: Path) -> str:
    text = contained(repo, PARSER_REL).read_text(encoding="utf-8")
    marker = 'pub const PARSER_REVISION: &str = "'
    start = text.index(marker) + len(marker)
    return text[start : text.index('"', start)]


def surface(repo: Path, path: str) -> dict[str, Any]:
    actual = contained(repo, path)
    return {"path": path, "sha256": digest(actual), "size_bytes": actual.stat().st_size}


def compose(repo: Path) -> dict[str, Any]:
    receipt = contained(repo, RECEIPT_REL)
    value = json.loads(receipt.read_text(encoding="utf-8"))
    if value.get("schema") != "m204-s10-c4-operational-receipt/v1":
        raise ValueError("historical receipt schema mismatch")
    if value.get("claims", {}).get("operational_acceptance") != "non-pass":
        raise ValueError("historical receipt is not an operational non-pass")
    if value.get("observed_output", {}).get("jsonl_valid") is not False:
        raise ValueError("historical receipt JSONL must be invalid")
    return {
        "schema": SCHEMA,
        "historical_receipt": surface(repo, RECEIPT_REL),
        "historical_surfaces": [
            surface(repo, DIAGNOSTICS_REL),
            surface(repo, BATTERY_REL),
            surface(repo, STDOUT_REL),
            surface(repo, STDERR_REL),
            surface(repo, CONTRACT_REL),
        ],
        "historical_binary_sha256": value["binary"]["sha256"],
        "historical_parser_source_sha256": value["build_inputs"]["parser_source_sha256"],
        "current_parser_source_sha256": digest(contained(repo, PARSER_REL)),
        "parser_revision": value["parser_revision"],
        "receipt_operational_acceptance": "non-pass",
        "receipt_jsonl_valid": False,
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "s14_called_validate_milestone": False,
    }


def validate_for_replay(repo: Path, artifact: Path, receipt: Path) -> dict[str, Any]:
    value = json.loads(artifact.read_text(encoding="utf-8"))
    required = {
        "schema",
        "historical_receipt",
        "historical_surfaces",
        "historical_binary_sha256",
        "historical_parser_source_sha256",
        "current_parser_source_sha256",
        "parser_revision",
        "receipt_operational_acceptance",
        "receipt_jsonl_valid",
        "classification",
        "status_effect",
        "s14_called_validate_milestone",
    }
    if not isinstance(value, dict) or set(value) != required or value["schema"] != SCHEMA:
        raise ValueError("source-binding schema is not closed")
    repo = repo.resolve()
    receipt = receipt.resolve(strict=True)
    pinned = value["historical_receipt"]
    if not isinstance(pinned, dict) or set(pinned) != {"path", "sha256", "size_bytes"}:
        raise ValueError("historical receipt pin is not closed")
    actual_receipt = contained(repo, pinned["path"])
    if (
        actual_receipt != receipt
        or pinned["sha256"] != digest(receipt)
        or pinned["size_bytes"] != receipt.stat().st_size
    ):
        raise ValueError("historical receipt pin mismatch")
    surfaces = value["historical_surfaces"]
    expected = {DIAGNOSTICS_REL, BATTERY_REL, STDOUT_REL, STDERR_REL, CONTRACT_REL}
    if not isinstance(surfaces, list) or len(surfaces) != len(expected):
        raise ValueError("historical surface set is incomplete")
    seen: set[str] = set()
    for item in surfaces:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size_bytes"}:
            raise ValueError("historical surface pin is not closed")
        path = item["path"]
        if path in seen or path not in expected:
            raise ValueError("historical surface set has missing, duplicate, or extra path")
        seen.add(path)
        actual = contained(repo, path)
        if item["sha256"] != digest(actual) or item["size_bytes"] != actual.stat().st_size:
            raise ValueError(f"historical surface hash mismatch: {path}")
    if seen != expected:
        raise ValueError("historical surface set mismatch")
    receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
    by_path = {item["path"]: item for item in surfaces}
    for field, path in (
        ("contract", CONTRACT_REL),
        ("diagnostics", DIAGNOSTICS_REL),
        ("stdout", STDOUT_REL),
        ("stderr", STDERR_REL),
    ):
        receipt_path_value = (
            receipt_data.get("contract", {}).get("path")
            if field == "contract"
            else receipt_data.get("observed_output", {}).get("diagnostics")
            if field == "diagnostics"
            else receipt_data.get("logs", {}).get(field)
        )
        if Path(str(receipt_path_value)).as_posix() != path:
            raise ValueError(f"historical receipt {field} path is not pinned")
        if (
            receipt_data.get("contract", {}).get("sha256") != by_path[path]["sha256"]
            if field == "contract"
            else receipt_data.get("logs", {}).get(f"{field}_sha256") != by_path[path]["sha256"]
            if field in {"stdout", "stderr"}
            else receipt_data.get("logs", {}).get("diagnostics_sha256") != by_path[path]["sha256"]
        ):
            raise ValueError(f"historical receipt {field} hash is not pinned")
    if not isinstance(value["historical_binary_sha256"], str) or not value[
        "historical_binary_sha256"
    ].startswith("sha256:"):
        raise ValueError("historical binary attestation is malformed")
    if (
        value["historical_parser_source_sha256"]
        != json.loads(receipt.read_text(encoding="utf-8"))["build_inputs"]["parser_source_sha256"]
    ):
        raise ValueError("historical parser attestation mismatch")
    if value["current_parser_source_sha256"] != digest(contained(repo, PARSER_REL)):
        raise ValueError("current parser hash does not match live bytes")
    if (
        parser_revision(repo) != value["parser_revision"]
        or value["parser_revision"] != PARSER_REVISION
    ):
        raise ValueError("parser revision mismatch")
    if (
        value["receipt_operational_acceptance"] != "non-pass"
        or value["receipt_jsonl_valid"] is not False
    ):
        raise ValueError("historical operational claim is impermissible")
    if (
        value["classification"] != "supporting-only"
        or value["status_effect"] != "unchanged"
        or value["s14_called_validate_milestone"] is not False
    ):
        raise ValueError("source binding makes an impermissible lifecycle claim")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "verify"))
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=ROOT / "prd/migration/rust-evidence/m204-s14-s10-source-binding.json",
    )
    parser.add_argument("--receipt", type=Path, default=ROOT / RECEIPT_REL)
    args = parser.parse_args()
    repo = args.repo.resolve()
    artifact = args.artifact if args.artifact.is_absolute() else repo / args.artifact
    if args.command == "compose":
        encoded = json.dumps(compose(repo), indent=2) + "\n"
        if artifact.exists() and artifact.read_text(encoding="utf-8") != encoded:
            raise ValueError("binding artifact already exists and differs")
        if not artifact.exists():
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(encoded, encoding="utf-8")
        print("S14_T02_BINDING_OK")
    else:
        validate_for_replay(repo, artifact.resolve(), args.receipt)
        print("S14_T02_BINDING_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError) as exc:
        print(f"source binding verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
