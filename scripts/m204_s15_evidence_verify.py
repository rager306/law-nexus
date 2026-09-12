#!/usr/bin/env python3
"""Verify the bounded, additive M204/S15 evidence aggregate.

This verifier is a frozen-input consumer.  It does not read GSD/DB/projections,
walk the corpus, mutate historical evidence, or promote requirement state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
S15_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s15-frozen-hashes.json"
S15_ARTIFACT = ROOT / "prd/migration/rust-evidence/m204-s15-requirement-class.json"
S14_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s14-frozen-hashes.json"
S14_ACCEPTANCE = ROOT / "prd/migration/rust-evidence/m204-s14-c4-acceptance.json"
S14_RESULT = {
    "integrity": "pass",
    "c4_acceptance": "non-pass",
    "classification": "supporting-only",
}
S15_RESULT = {
    "c4_acceptance": "non-pass",
    "classification": "supporting-only",
    "class_matched_ids": [],
    "status_effect": "unchanged",
}
S14_PINS = {
    "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json": "sha256:0c7602c051102807d50767ac836f7627b1e213ffded55c665f1743a01bb15dac",
    "prd/migration/rust-evidence/m204-s10-c4-attempts/s10-full-walk-001/diagnostics.jsonl": "sha256:177282f3a2e99c80f55b85b2a1568e1a9c80c35e7999f9b6bf42491de0379e35",
    "prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json": "sha256:7e735d8c10d5fddf84a0f0a164778c4d1576612d1b11e313dac96bf22a3248b8",
    "prd/migration/rust-evidence/m204-s11-c4-failed-classification.json": "sha256:d2c542d4538cdace8c11802479e3fc8e6697103db81435a0e3ccbd242cb12834",
    "prd/migration/rust-evidence/m204-s12-frozen-hashes.json": "sha256:4ecaba1d7838a1a1b5f0484b39ef5764df43ff456ef95d7c134d6263b4041a66",
    "prd/migration/rust-evidence/m204-s13-s07-source-binding.json": "sha256:10483c2a770bd3f5df3aa9df4ae26d8481033fa88f3a1ccdf4a4619f08520d68",
    "prd/migration/rust-evidence/m204-s13-s07-verification-battery.json": "sha256:e2953ea3d4336ebe44435c651046549388c5f1e4044784a084f22d44904938d4",
    "prd/migration/rust-evidence/m204-s13-frozen-hashes.json": "sha256:4c25ef0858f0a414e5a431c7f42d166cfcaec1b1ad019ec5a5b8395338cf5da9",
}
S15_PINS = {
    "prd/migration/rust-evidence/m204-s06-requirement-evidence.json": "sha256:3ad805bb063058176a52a44c2b9768a86d09ff9c7ee2587cd6aa4144b3774ce3",
    "prd/migration/rust-evidence/m204-s07-requirement-evidence.json": "sha256:f599d67c5ddc2e2bcc923acf179df38904512d0ac398caac34e8edf206098203",
    "prd/migration/rust-evidence/m204-s10-requirement-evidence.json": "sha256:72d08be71b5225fb58980ca9d415ba5d2bbc8a8a94e9cf104a37dcfdfb33f3d7",
    "prd/migration/rust-evidence/m204-s14-c4-acceptance.json": "sha256:07038cc66b6c8e1bd1d96c2cac40d1ab823e90cfade8b4940f451c2eab7f7f17",
    "prd/migration/rust-evidence/m204-s14-frozen-hashes.json": "sha256:c8823df7e333d8c98b401c2c6d3b8769e0eb629db6cfb5f936bc58cca17d413a",
}


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def safe_source(value: str) -> Path:
    path = Path(value)
    banned = {".git", ".gsd", ".planning", ".audits"}
    if (
        path.is_absolute()
        or "\\" in value
        or ".." in path.parts
        or any(p in banned for p in path.parts)
    ):
        raise ValueError(f"unsafe source path: {value}")
    candidate = ROOT / path
    if any(part.is_symlink() for part in [ROOT, *candidate.parents, candidate] if part.exists()):
        raise ValueError(f"symlink source path: {value}")
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(ROOT.resolve())
    if resolved != candidate or not resolved.is_file():
        raise ValueError(f"source is not a regular repository file: {value}")
    return resolved


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def closed_manifest(path: Path, schema: str, scope: str, pins: dict[str, str]) -> list[str]:
    value = load(path)
    required_keys = {"schema", "scope", "files"}
    if path == S14_MANIFEST:
        required_keys.add("non_claims")
    if not isinstance(value, dict) or set(value) != required_keys:
        raise ValueError(f"{path.name}: manifest schema is not closed")
    if value["schema"] != schema or value["scope"] != scope:
        raise ValueError(f"{path.name}: schema or scope mismatch")
    rows = value["files"]
    if not isinstance(rows, list) or len(rows) != len(pins):
        raise ValueError(f"{path.name}: required pin set is incomplete")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size_bytes"}:
            raise ValueError(f"{path.name}: file row is not closed")
        source_path = row["path"]
        if source_path in seen or source_path not in pins:
            raise ValueError(f"{path.name}: missing, duplicate, or extra pin: {source_path}")
        seen.add(source_path)
        source = safe_source(source_path)
        expected = pins[source_path]
        if row["sha256"] != expected or digest(source) != expected:
            raise ValueError(f"{path.name}: source drift: {source_path}")
        if type(row["size_bytes"]) is not int or row["size_bytes"] != source.stat().st_size:
            raise ValueError(f"{path.name}: source size drift: {source_path}")
    if seen != set(pins):
        raise ValueError(f"{path.name}: required pin set is incomplete")
    return list(seen)


def verify_s14_manifest() -> list[str]:
    return closed_manifest(
        S14_MANIFEST,
        "law-nexus/m204-s14-frozen-hashes/v1",
        "S14 aggregate; frozen tracked evidence only; no corpus walk",
        S14_PINS,
    )


def run_json(command: list[str], label: str, timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{label} timed out") from exc
    if result.returncode != 0:
        raise ValueError(f"{label} failed: {result.stderr.strip() or result.returncode}")
    if result.stderr or not result.stdout.strip():
        raise ValueError(f"{label} did not emit strict JSON")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} emitted invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} emitted non-object JSON")
    return value


def run_marker(command: list[str], marker: str, label: str) -> None:
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=120, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{label} timed out") from exc
    if result.returncode != 0:
        raise ValueError(f"{label} failed: {result.stderr.strip() or result.returncode}")
    lines = result.stdout.splitlines()
    if result.stderr or not any(line == marker or line.startswith(marker + " ") for line in lines):
        raise ValueError(f"{label} missing marker {marker}")


def verify() -> None:
    closed_manifest(
        S15_MANIFEST,
        "law-nexus/m204-s15-frozen-hashes/v1",
        "S15 additive classifier; frozen tracked evidence only; no corpus walk",
        S15_PINS,
    )
    s14_paths = verify_s14_manifest()
    acceptance = load(S14_ACCEPTANCE)
    if not isinstance(acceptance, dict) or {
        key: acceptance.get(key) for key in ("c4_acceptance", "classification")
    } != {"c4_acceptance": "non-pass", "classification": "supporting-only"}:
        raise ValueError("S14 acceptance is not non-pass/supporting-only")
    run_marker(["bash", "scripts/m204_s15_t01_verify.sh"], "S15_T01_CLASS_OK", "T01 host")
    run_marker(["bash", "scripts/m204_s15_t02_verify.sh"], "S15_T02_NEGATIVES_OK", "T02 host")
    s15 = run_json(
        ["uv", "run", "python", "scripts/m204_s15_requirement_class.py", "classify"], "S15 classify"
    )
    s14 = run_json(
        ["uv", "run", "python", "scripts/m204_s14_polarity.py", "classify"], "S14 classify"
    )
    if s15 != S15_RESULT:
        raise ValueError("S15 classify result mismatch")
    if s14 != S14_RESULT:
        raise ValueError("S14 classify result mismatch")
    if (
        s15["c4_acceptance"] != s14["c4_acceptance"]
        or s15["classification"] != s14["classification"]
    ):
        raise ValueError("S15/S14 polarity mismatch")
    artifact = load(S15_ARTIFACT)
    if not isinstance(artifact, dict) or artifact.get("class_matched_ids") != []:
        raise ValueError("S15 artifact promotes class-matched coverage")
    # Re-read every S14 contained entry after the subprocesses.  This catches
    # accidental rewrites even when the manifest itself remains unchanged.
    for source_path in s14_paths:
        safe_source(source_path)
    print("S15_VERIFY_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify", "check"))
    parser.parse_args()
    try:
        verify()
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s15_evidence_verify: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
