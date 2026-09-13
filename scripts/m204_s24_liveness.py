#!/usr/bin/env python3
"""Compose and check the source-bound S24 criterion-resolution packet.

The composer is deliberately offline-pure: it hashes only an explicit list of
tracked predecessor artifacts and never reads the GSD runtime, journal, or DB.
The checker is the host boundary and independently re-verifies the cited v2
receipt through the existing S23 reader.
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
LEDGER_SCHEMA = "law-nexus/m204-s24-criterion-resolution/v1"
MANIFEST_SCHEMA = "law-nexus/m204-s24-frozen-hashes/v1"
LEDGER_REL = "prd/migration/rust-evidence/m204-s24-criterion-resolution.json"
MANIFEST_REL = "prd/migration/rust-evidence/m204-s24-frozen-hashes.json"
V2_RECEIPT = "prd/migration/rust-evidence/m204-s23-remediation-v2-c4-receipt.json"
HISTORICAL_RECEIPT = "prd/migration/rust-evidence/m204-s23-c4-operational-receipt.json"
S22_PINS = (
    "prd/migration/rust-evidence/m204-s22-external-blocker.json",
    "prd/migration/rust-evidence/m204-s22-frozen-hashes.json",
    "prd/migration/rust-evidence/m204-s22-operational-battery.json",
)
PINS = S22_PINS + (
    "prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json",
    "prd/migration/rust-evidence/m204-s09-trigger-sql.json",
    V2_RECEIPT,
    "prd/migration/rust-evidence/m204-s23-remediation-v2-c4-diagnostics.jsonl",
    "prd/migration/rust-evidence/m204-s23-remediation-v2-battery.json",
    "prd/migration/rust-evidence/m204-s23-c4-operational-receipt.json",
    "prd/migration/rust-evidence/m204-s23-operational-battery.json",
    "prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json",
    "scripts/m204_s23_c4_run.py",
)
NON_CLAIMS = [
    "not a GSD recovery pass",
    "does not call validate",
    "does not close requirements or findings",
    "does not rewrite historical receipts",
    "debug timing is not a release performance claim",
    "S23 skip is not C4 non-existence",
    "local overlay preservation is not an engine fix",
]


def load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def safe_file(root: Path, value: Any, *, existing: bool = True) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("path must be a non-empty relative POSIX string")
    path = Path(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or any(part in {".git", ".gsd"} for part in path.parts)
    ):
        raise ValueError(f"unsafe path: {value}")
    candidate = root / path
    if any(part.is_symlink() for part in (root, *candidate.parents, candidate) if part.exists()):
        raise ValueError(f"symlink path: {value}")
    resolved = candidate.resolve(strict=False)
    if root.resolve() not in (resolved, *resolved.parents):
        raise ValueError(f"path escapes root: {value}")
    if existing and (not candidate.is_file() or candidate.is_symlink()):
        raise ValueError(f"not a regular file: {value}")
    return candidate


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def strict_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return list(actual) == list(expected) and all(
            strict_equal(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            strict_equal(a, b) for a, b in zip(actual, expected)
        )
    return actual == expected


def pins(root: Path) -> list[dict[str, Any]]:
    result = []
    for relative in PINS:
        source = safe_file(root, relative)
        result.append(
            {"path": relative, "sha256": digest(source), "size_bytes": source.stat().st_size}
        )
    return result


def expected_ledger() -> dict[str, Any]:
    return {
        "schema": LEDGER_SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S24",
        "predecessor_slice": "S22",
        "s23_status": "skipped",
        "path": "criterion-resolution",
        "gsd_recovery_liveness": "blocked-external",
        "c4_operational_acceptance": "pass",
        "c4_control": "pass",
        "c4_pass_receipt": V2_RECEIPT,
        "c4_pass_diagnostics": "prd/migration/rust-evidence/m204-s23-remediation-v2-c4-diagnostics.jsonl",
        "c4_pass_mode": "c4-artifact-replay",
        "c4_pass_duration_ms": 4991302,
        "historical_s23_receipt_sha256": "sha256:c6d1e650506cd2008fdb7762063940031ae7074a39a46972e65407a0ac7b56cc",
        "historical_s23_operational_acceptance": "non-pass",
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "law_nexus_fixable": False,
        "in_tree_engine_source": False,
        "local_overlay_preserve_patch": "not-engine-fix",
        "trigger_name": "trg_workflow_technical_verdict_scope",
        "sql_abort_message": "technical verdict requires the current criterion and matching settled attempt",
        "s22_blocker": "prd/migration/rust-evidence/m204-s22-external-blocker.json",
        "s09_trigger_snapshot": "prd/migration/rust-evidence/m204-s09-trigger-sql.json",
        "validation_projection_present": False,
        "s24_called_validate_milestone": False,
        "retry_substitute": False,
        "full_corpus_walk_in_slice": False,
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "disposition": "needs-remediation",
        "same_defect_as_s09": True,
        "sufficient_for_truthful_revalidation": True,
        "frozen_manifest": {"schema": MANIFEST_SCHEMA, "path": MANIFEST_REL},
        "non_claims": NON_CLAIMS,
    }


def compose(root: Path, ledger: Path, manifest: Path) -> None:
    ledger_rel = ledger.resolve().relative_to(root.resolve()).as_posix()
    manifest_rel = manifest.resolve().relative_to(root.resolve()).as_posix()
    safe_file(root, ledger_rel, existing=False)
    safe_file(root, manifest_rel, existing=False)
    if ledger.exists() or manifest.exists():
        raise ValueError("compose refuses to overwrite an existing destination")
    if ledger_rel != LEDGER_REL or manifest_rel != MANIFEST_REL:
        raise ValueError("S24 destinations are fixed and source-bound")
    manifest_doc = {
        "schema": MANIFEST_SCHEMA,
        "scope": "S24 ordered predecessor pins; no self-hash and no corpus walk",
        "files": pins(root),
        "non_claims": [
            "pins do not repair the GSD engine",
            "pins do not establish validation",
            "pins do not promote blocked-external liveness",
        ],
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(manifest_doc, indent=2) + "\n", encoding="utf-8")
    ledger.write_text(json.dumps(expected_ledger(), indent=2) + "\n", encoding="utf-8")


def verify_receipt(
    root: Path, receipt: str, require_pass: bool
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(root / "scripts/m204_s23_c4_run.py"),
        "--verify-receipt",
        receipt,
    ]
    if require_pass:
        command.append("--require-operational-pass")
    return subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)


def check(root: Path, ledger: Path, manifest: Path) -> None:
    ledger_rel = ledger.resolve().relative_to(root.resolve()).as_posix()
    manifest_rel = manifest.resolve().relative_to(root.resolve()).as_posix()
    if ledger_rel != LEDGER_REL or manifest_rel != MANIFEST_REL:
        raise ValueError("S24 destinations are fixed and source-bound")
    safe_file(root, ledger_rel)
    safe_file(root, manifest_rel)
    document = load(ledger)
    expected = expected_ledger()
    if document.get("c4_operational_acceptance") == "pass":
        receipt = document.get("c4_pass_receipt")
        if receipt != V2_RECEIPT:
            raise ValueError("operational pass must cite the v2 receipt")
        result = verify_receipt(root, receipt, True)
        if result.returncode != 0:
            raise ValueError("recorded v2 receipt did not pass independent verification")
        recorded = load(safe_file(root, receipt))
        if not _operational_pass_data(recorded):
            raise ValueError("recorded v2 receipt is not operational-pass data")
    historical = load(safe_file(root, HISTORICAL_RECEIPT))
    if digest(safe_file(root, HISTORICAL_RECEIPT)) != expected["historical_s23_receipt_sha256"]:
        raise ValueError("historical S23 receipt hash drifted")
    if historical.get("claims", {}).get("operational_acceptance") == "pass":
        raise ValueError("historical receipt was laundered")
    old = verify_receipt(root, HISTORICAL_RECEIPT, True)
    if old.returncode == 0 or "operational acceptance is not proven" not in (
        old.stdout + old.stderr
    ):
        raise ValueError("historical receipt unexpectedly passed operational verification")
    if not strict_equal(document, expected):
        raise ValueError("ledger schema, literals, or ordered fields mismatch")
    frozen = load(manifest)
    expected_manifest = {
        "schema": MANIFEST_SCHEMA,
        "scope": "S24 ordered predecessor pins; no self-hash and no corpus walk",
        "files": pins(root),
        "non_claims": [
            "pins do not repair the GSD engine",
            "pins do not establish validation",
            "pins do not promote blocked-external liveness",
        ],
    }
    if not strict_equal(frozen, expected_manifest):
        raise ValueError("manifest pins, schema, or ordering drifted")
    if any(row["path"] in {ledger_rel, manifest_rel} for row in frozen["files"]):
        raise ValueError("self-hash is forbidden")


def _operational_pass_data(data: dict[str, Any]) -> bool:
    terminal = data.get("terminal", {})
    corpus = data.get("corpus", {})
    binding = data.get("c4_binding", {})
    output = data.get("observed_output", {})
    return (
        terminal.get("outcome") == "complete"
        and terminal.get("exit_code") == 0
        and terminal.get("timeout") is False
        and type(data.get("duration_ms")) is int
        and data["duration_ms"] >= 3_600_000
        and binding.get("limit") is None
        and corpus.get("consultant_xml_count") == 43_785
        and isinstance(output.get("inventory_digest"), str)
        and bool(output["inventory_digest"])
        and output.get("jsonl_valid") is True
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--packet", "--ledger", dest="ledger", type=Path, default=Path(LEDGER_REL))
    parser.add_argument("--manifest", type=Path, default=Path(MANIFEST_REL))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    ledger = args.ledger if args.ledger.is_absolute() else root / args.ledger
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    if args.command == "compose":
        compose(root, ledger, manifest)
    else:
        check(root, ledger, manifest)
    print("S24_T01_CRITERION_OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"S24_T01_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
