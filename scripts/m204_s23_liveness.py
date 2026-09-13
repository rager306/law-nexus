#!/usr/bin/env python3
"""Compose and check the S23 owner-scoped, external GSD blocker proof.

This is predecessor evidence only. It deliberately never opens the GSD database,
loads the external engine, or calls validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
DEFAULT_PACKET = EVIDENCE / "m204-s23-external-blocker.json"
DEFAULT_MANIFEST = EVIDENCE / "m204-s23-frozen-hashes.json"
SCHEMA = "law-nexus/m204-s23-external-blocker/v1"
MANIFEST_SCHEMA = "law-nexus/m204-s23-frozen-hashes/v1"
TRIGGER = "trg_workflow_technical_verdict_scope"
SQL_ABORT = "technical verdict requires the current criterion and matching settled attempt"

# These are the only predecessor bytes this proof is allowed to consume.
PINNED = (
    (
        "prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json",
        "78e1d64c56afde92e433396b4b906fe9a69fae7bc58bbc54d17fb4aaed3d6bc4",
        1177,
    ),
    (
        "prd/migration/rust-evidence/m204-s09-trigger-sql.json",
        "c115c2feea8692fc86b91001f8d71da2d155c6ee4182ec4f7a3387eca6962c97",
        2909,
    ),
    (
        "prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json",
        "4d5057fa9f7ffacf21cdf115c63df90d10e3471f1d8fc060261b1feed957273b",
        3906,
    ),
    (
        "prd/migration/rust-evidence/m204-s22-frozen-hashes.json",
        "a202233fc86f6607624355113eda68f7ee42aae4405329e522b59bca6661735a",
        4903,
    ),
)


def load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def safe_path(root: Path, value: Any, *, existing: bool) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("path must be a non-empty relative POSIX string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or any(p in {".git", ".gsd"} for p in path.parts):
        raise ValueError(f"unsafe path: {value}")
    candidate = root / path
    if any(p.is_symlink() for p in (root, *candidate.parents, candidate) if p.exists()):
        raise ValueError(f"symlink path: {value}")
    resolved = candidate.resolve(strict=False)
    if root.resolve() not in (resolved, *resolved.parents):
        raise ValueError(f"path escapes root: {value}")
    if existing and (not candidate.is_file() or candidate.is_symlink()):
        raise ValueError(f"not a regular file: {value}")
    return candidate


def strict_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return list(actual) == list(expected) and all(
            strict_equal(actual[k], expected[k]) for k in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            strict_equal(a, e) for a, e in zip(actual, expected)
        )
    return actual == expected


def predecessor_pins(root: Path) -> list[dict[str, Any]]:
    rows = []
    sources: dict[str, Any] = {}
    for path, expected, size in PINNED:
        source = safe_path(root, path, existing=True)
        if (
            hashlib.sha256(source.read_bytes()).hexdigest() != expected
            or source.stat().st_size != size
        ):
            raise ValueError(f"predecessor drift: {path}")
        rows.append({"path": path, "sha256": f"sha256:{expected}", "size_bytes": size})
        sources[path] = load(source)
    if sources[PINNED[0][0]]["trigger_name"] != TRIGGER:
        raise ValueError("S09 trigger provenance mismatch")
    if sources[PINNED[0][0]]["abort_message"] != SQL_ABORT:
        raise ValueError("S09 SQL abort provenance mismatch")
    if (
        sources[PINNED[2][0]]["trigger_name"] != TRIGGER
        or sources[PINNED[2][0]]["sql_abort_message"] != SQL_ABORT
    ):
        raise ValueError("S21 liveness provenance mismatch")
    return rows


def exclusive_write(path: Path, payload: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)


def expected_packet(manifest_rel: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S23",
        "predecessor_slices": ["S22", "S09"],
        "evidence_kind": "predecessor-evidence",
        "proof_completeness": "predecessor-pins-and-boundary-complete",
        "gsd_recovery_liveness": "blocked-external",
        "law_nexus_fixable": False,
        "engine_fix": "not_fixed",
        "retry_substitute": False,
        "s23_called_validate_milestone": False,
        "owner_scope": "GSD engine owner",
        "owner_resolution": "missing",
        "disposition": "needs-remediation",
        "upstream_issue": "not_filed",
        "trigger_name": TRIGGER,
        "sql_abort_message": SQL_ABORT,
        "predecessor_refs": {
            "s09_deadlock": "prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json",
            "s09_trigger_sql": "prd/migration/rust-evidence/m204-s09-trigger-sql.json",
            "s21_liveness_census": "prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json",
            "s22_manifest": "prd/migration/rust-evidence/m204-s22-frozen-hashes.json",
        },
        "c4_operational_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "non_claims": [
            "not a live SQL probe",
            "not a recovery pass or sanctioned resolution",
            "does not file an upstream issue",
            "does not close R035, R070, or F19",
            "does not call validate or mutate the GSD engine",
        ],
        "frozen_manifest": {"schema": MANIFEST_SCHEMA, "path": manifest_rel},
    }


def compose(root: Path, packet: Path, manifest: Path) -> None:
    if packet.exists() or manifest.exists():
        raise ValueError("compose refuses to overwrite an existing destination")
    packet_rel = packet.resolve().relative_to(root.resolve()).as_posix()
    manifest_rel = manifest.resolve().relative_to(root.resolve()).as_posix()
    safe_path(root, packet_rel, existing=False)
    safe_path(root, manifest_rel, existing=False)
    rows = predecessor_pins(root)
    manifest_doc = {
        "schema": MANIFEST_SCHEMA,
        "scope": "S23 predecessor evidence only; ordered pins; no live probe",
        "files": rows,
        "non_claims": [
            "pins do not repair or resolve the GSD engine",
            "pins do not establish validation",
        ],
    }
    packet_doc = expected_packet(manifest_rel)
    packet.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    exclusive_write(packet, json.dumps(packet_doc, indent=2) + "\n")
    try:
        exclusive_write(manifest, json.dumps(manifest_doc, indent=2) + "\n")
    except Exception:
        packet.unlink(missing_ok=True)
        raise


def check(root: Path, packet: Path, manifest: Path) -> None:
    packet_rel = packet.resolve().relative_to(root.resolve()).as_posix()
    manifest_rel = manifest.resolve().relative_to(root.resolve()).as_posix()
    safe_path(root, packet_rel, existing=True)
    safe_path(root, manifest_rel, existing=True)
    doc = load(packet)
    if not strict_equal(doc, expected_packet(manifest_rel)):
        raise ValueError("packet schema, literals, or ordered fields mismatch")
    frozen = load(manifest)
    if (
        list(frozen) != ["schema", "scope", "files", "non_claims"]
        or frozen["schema"] != MANIFEST_SCHEMA
    ):
        raise ValueError("manifest schema is not closed")
    if not strict_equal(frozen["files"], predecessor_pins(root)):
        raise ValueError("predecessor pins drifted, reordered, or changed")
    if any(row["path"] in {packet_rel, manifest_rel} for row in frozen["files"]):
        raise ValueError("self-hash is forbidden")
    print("S23_T03_BLOCKER_PROOF_OK")
    print("S23_T03_EXTERNAL_BOUNDARY_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        packet = args.packet if args.packet.is_absolute() else root / args.packet
        manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
        (compose if args.command == "compose" else check)(root, packet, manifest)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s23_liveness: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
