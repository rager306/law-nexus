#!/usr/bin/env python3
"""Record and validate the S12 Garant-first C4 failure identity attempt.

This module is deliberately a subprocess-only harness. It never decodes legal
files and never accepts a corpus root for the bounded verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

SCHEMA = "law-nexus/m204-s12-failed-file/v1"
SIDECAR_SCHEMA = "npa-contour-failure-trace/v1"
ALLOWED_PROVIDERS = {"consultant", "garant"}
ALLOWED_CLASSES = {"read", "digest", "decode", "toctou"}
ATTEMPT_ROOT = Path("prd/migration/rust-evidence/m204-s12-c4-attempts")
IDENTITY_PATH = Path("prd/migration/rust-evidence/m204-s12-failed-file.json")


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def repo_relative(path: str, root: Path) -> str:
    candidate = Path(path)
    resolved_root = root.resolve()
    resolved = candidate.resolve(strict=True)
    relative = resolved.relative_to(resolved_root).as_posix()
    if not (
        relative.startswith("consru_export/consru_export/exports/")
        or relative.startswith("law-source/garant/")
    ):
        raise ValueError(f"identity path outside production allowlist: {relative}")
    return relative


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL record in {path}")
        rows.append(value)
    return rows


def validate_sidecar(path: Path, repo: Path) -> list[dict[str, str]]:
    rows = parse_jsonl(path)
    result: list[dict[str, str]] = []
    for row in rows:
        if set(row) != {"record_kind", "schema", "provider", "path", "class"}:
            raise ValueError("sidecar record has extra or missing keys")
        if row["record_kind"] != "failure" or row["schema"] != SIDECAR_SCHEMA:
            raise ValueError("sidecar schema mismatch")
        provider = row["provider"]
        failure_class = row["class"]
        if provider not in ALLOWED_PROVIDERS or failure_class not in ALLOWED_CLASSES:
            raise ValueError("sidecar provider/class is not closed")
        if not isinstance(row["path"], str) or not row["path"]:
            raise ValueError("sidecar path must be non-empty")
        relative = repo_relative(row["path"], repo)
        expected_prefix = (
            "law-source/garant/" if provider == "garant" else "consru_export/consru_export/exports/"
        )
        if not relative.startswith(expected_prefix):
            raise ValueError("sidecar provider/path binding mismatch")
        result.append({"provider": provider, "path": relative, "class": failure_class})
    return result


def aggregate_failed(path: Path) -> int:
    rows = parse_jsonl(path)
    aggregates = [row for row in rows if row.get("record_kind") == "aggregate"]
    if len(aggregates) != 1 or not isinstance(aggregates[0].get("failed"), int):
        raise ValueError("diagnostic output has no unique aggregate failed count")
    return aggregates[0]["failed"]


def validate_identity(value: dict[str, Any], repo: Path) -> None:
    required = {
        "schema",
        "provider",
        "path",
        "class",
        "sidecar_sha256",
        "attempt_id",
        "attempt_provenance",
        "identity_status",
        "s10_bytes_rewritten",
        "status_effect",
        "classification",
        "marker",
    }
    if set(value) != required:
        raise ValueError("identity record has extra or missing keys")
    if value["schema"] != SCHEMA or value["identity_status"] != "resolved":
        raise ValueError("identity status/schema mismatch")
    if value["provider"] not in ALLOWED_PROVIDERS or value["class"] not in ALLOWED_CLASSES:
        raise ValueError("identity provider/class is not closed")
    if value["s10_bytes_rewritten"] is not False or value["status_effect"] != "unchanged":
        raise ValueError("identity record makes an impermissible historical claim")
    if value["classification"] != "supporting-only":
        raise ValueError("identity must remain supporting-only")
    if value["marker"] != "S12_T02_FAILURE_IDENTITY_OK":
        raise ValueError("identity marker mismatch")
    attempt = value["attempt_provenance"]
    if not isinstance(attempt, dict) or set(attempt) != {
        "diagnostics_path",
        "failures_path",
        "metadata_path",
        "diagnostics_sha256",
        "failures_sha256",
    }:
        raise ValueError("attempt provenance is not closed")
    for key in ("diagnostics_path", "failures_path", "metadata_path"):
        p = Path(attempt[key])
        if p.is_absolute() or ".." in p.parts:
            raise ValueError("attempt path is not repository-relative")
        if not (repo / p).is_file():
            raise ValueError(f"missing attempt artifact: {p}")
    if value["path"] != value["path"].replace("\\", "/") or value["path"].startswith("/"):
        raise ValueError("identity path is not repository-relative")


def run_attempt(args: argparse.Namespace) -> int:
    repo = Path.cwd().resolve()
    root = Path(args.root)
    garant_root = Path(args.garant_root)
    if not root.is_dir() or not garant_root.is_dir():
        raise ValueError("--root and --garant-root must be existing directories")
    if any(root.iterdir()):
        raise ValueError("--root must be an existing empty worktree-local directory")
    binary = Path(args.binary)
    if not binary.is_file():
        raise ValueError("diagnostic binary is missing")
    binary = binary.resolve()
    attempt_id = f"attempt-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:10]}"
    attempt = repo / ATTEMPT_ROOT / attempt_id
    attempt.parent.mkdir(parents=True, exist_ok=True)
    attempt.mkdir()
    failures = attempt / "failures.jsonl"
    diagnostics = attempt / "diagnostics.jsonl"
    metadata = attempt / "attempt.json"
    argv = [
        str(binary),
        "--root",
        str(root),
        "--garant-root",
        str(garant_root),
        "--profile",
        "contour",
        "--jobs",
        str(args.jobs),
        "--failures-out",
        str(failures),
        "--out",
        str(diagnostics),
    ]
    started = time.monotonic()
    completed = subprocess.run(argv, cwd=repo, text=True, capture_output=True, check=False)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    metadata_value = {
        "schema": "law-nexus/m204-s12-attempt/v1",
        "attempt_id": attempt_id,
        "argv": argv,
        "binary": {"path": binary.relative_to(repo).as_posix(), "sha256": sha256(binary)},
        "source": {
            "path": "crates/ln-consultant-parser/src/contour_diagnostics.rs",
            "sha256": sha256(repo / "crates/ln-consultant-parser/src/contour_diagnostics.rs"),
        },
        "inputs": {
            "root": str(root.relative_to(repo)) if root.is_relative_to(repo) else str(root),
            "garant_root": str(garant_root.relative_to(repo))
            if garant_root.is_relative_to(repo)
            else str(garant_root),
            "root_is_empty": True,
        },
        "toolchain": subprocess.run(
            ["rustc", "--version"], text=True, capture_output=True, check=False
        ).stdout.strip(),
        "exit_code": completed.returncode,
        "elapsed_ms": elapsed_ms,
        "stdout_sha256": "sha256:" + hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_sha256": "sha256:" + hashlib.sha256(completed.stderr.encode()).hexdigest(),
    }
    metadata.write_text(json.dumps(metadata_value, indent=2) + "\n", encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            f"diagnostic subprocess failed with exit {completed.returncode}: {completed.stderr.strip()}"
        )
    records = validate_sidecar(failures, repo)
    failed = aggregate_failed(diagnostics)
    if len(records) != failed or len(records) != 1:
        raise ValueError(f"sidecar/aggregate mismatch: records={len(records)} failed={failed}")
    record = records[0]
    identity = {
        "schema": SCHEMA,
        "provider": record["provider"],
        "path": record["path"],
        "class": record["class"],
        "sidecar_sha256": sha256(failures),
        "attempt_id": attempt_id,
        "attempt_provenance": {
            "diagnostics_path": diagnostics.relative_to(repo).as_posix(),
            "failures_path": failures.relative_to(repo).as_posix(),
            "metadata_path": metadata.relative_to(repo).as_posix(),
            "diagnostics_sha256": sha256(diagnostics),
            "failures_sha256": sha256(failures),
        },
        "identity_status": "resolved",
        "s10_bytes_rewritten": False,
        "status_effect": "unchanged",
        "classification": "supporting-only",
        "marker": "S12_T02_FAILURE_IDENTITY_OK",
    }
    if IDENTITY_PATH.exists():
        if json.loads(IDENTITY_PATH.read_text(encoding="utf-8")) != identity:
            raise ValueError("published identity already exists and differs")
    else:
        IDENTITY_PATH.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return 0


def verify_artifacts() -> int:
    repo = Path.cwd().resolve()
    value = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    validate_identity(value, repo)
    provenance = value["attempt_provenance"]
    failures = repo / provenance["failures_path"]
    diagnostics = repo / provenance["diagnostics_path"]
    records = validate_sidecar(failures, repo)
    if len(records) != aggregate_failed(diagnostics) or len(records) != 1:
        raise ValueError("published attempt aggregate mismatch")
    record = records[0]
    if any(value[key] != record[key] for key in ("provider", "path", "class")):
        raise ValueError("published identity does not match sidecar")
    if sha256(failures) != value["sidecar_sha256"]:
        raise ValueError("sidecar digest mismatch")
    print("S12_T02_FAILURE_IDENTITY_OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--binary", required=True)
    record.add_argument("--root", required=True)
    record.add_argument("--garant-root", required=True)
    record.add_argument("--jobs", type=int, default=1)
    sub.add_parser("verify")
    args = parser.parse_args()
    try:
        return run_attempt(args) if args.command == "record" else verify_artifacts()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"m204_s12_failure_probe: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
