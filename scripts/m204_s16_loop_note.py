#!/usr/bin/env python3
"""Closed census of the three post-S15 validate no-artifact aborts.

This tool is deliberately a frozen-input consumer.  ``compose`` hashes only the
six predecessor snapshots named by the task contract; ``check`` is read-only
and can be pointed at an isolated fixture root for subprocess tests.  It never
opens GSD, journal, git, a database, or the corpus and never calls lifecycle
APIs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/gsd-post-s15-validate-loop/v1"
MANIFEST_SCHEMA = "law-nexus/m204-s16-frozen-hashes/v1"
DEFAULT_CENSUS = ROOT / "prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json"
DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s16-frozen-hashes.json"
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
        "prd/migration/rust-evidence/m204-s12-validate-hard-block.json",
        "0ec27bbd4c0cf9bf3e48b74a375affee0824288f233598a0758d43d1ba0220f3",
        629,
    ),
    (
        "prd/migration/rust-evidence/m204-s12-frozen-hashes.json",
        "4ecaba1d7838a1a1b5f0484b39ef5764df43ff456ef95d7c134d6263b4041a66",
        3272,
    ),
    (
        "prd/migration/rust-evidence/m204-s15-requirement-class.json",
        "440dc6eb4bafabe2501002483012d373dee5133ec705c9677ef8b49c2d7b0d4d",
        13705,
    ),
    (
        "prd/migration/rust-evidence/m204-s15-frozen-hashes.json",
        "6e2030811c8d0f4f03b35acc1ea141b78609c941077737ceeb8321bf1746e446",
        1186,
    ),
)
ABORT_MESSAGE = "finalize-retry: You must call gsd_validate_milestone to persist the validation results. No current canonical validation result exists in the database."
SQL_MESSAGE = "technical verdict requires the current criterion and matching settled attempt"
TRIGGER = "trg_workflow_technical_verdict_scope"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def safe_relative(root: Path, value: Any) -> Path:
    if not isinstance(value, str):
        raise ValueError("manifest path must be a string")
    path = Path(value)
    banned = {".git", ".gsd", ".planning", ".audits"}
    if (
        path.is_absolute()
        or "\\" in value
        or ".." in path.parts
        or any(p in banned for p in path.parts)
    ):
        raise ValueError(f"unsafe manifest path: {value}")
    candidate = root / path
    for part in (root, *candidate.parents, candidate):
        if part.exists() and part.is_symlink():
            raise ValueError(f"symlink component in manifest path: {value}")
    resolved = candidate.resolve(strict=True)
    if resolved != candidate or not resolved.is_file():
        raise ValueError(f"manifest path is not a regular file: {value}")
    return candidate


def rows() -> list[dict[str, Any]]:
    return [
        {
            "ordinal": 1,
            "unit_start_at": "2026-09-12T15:22:25.039Z",
            "unit_end_at": "2026-09-12T15:36:33.426Z",
            "unit_end_status": "no-artifact",
            "finalize_status": "retry",
            "iteration_end_reason": ABORT_MESSAGE,
            "flow_id": "15422f5d-d070-49d0-af02-aac38792728b",
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
        },
        {
            "ordinal": 2,
            "unit_start_at": "2026-09-12T15:38:14.425Z",
            "unit_end_at": "2026-09-12T15:53:57.240Z",
            "unit_end_status": "no-artifact",
            "finalize_status": "retry",
            "iteration_end_reason": ABORT_MESSAGE,
            "flow_id": "a93b8d9a-fbaa-46b1-8be9-b7fbeca8a9ef",
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
        },
        {
            "ordinal": 3,
            "unit_start_at": "2026-09-12T15:55:29.390Z",
            "unit_end_at": "2026-09-12T16:06:07.059Z",
            "unit_end_status": "no-artifact",
            "finalize_status": "retry",
            "iteration_end_reason": ABORT_MESSAGE,
            "flow_id": "3e84ca53-9b0e-40b2-9bab-09cd88c7a489",
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
        },
    ]


def compose(root: Path, census: Path, manifest: Path) -> None:
    files = []
    for path, expected, size in PINNED:
        source = safe_relative(root, path)
        actual = digest(source)
        if actual != expected or source.stat().st_size != size:
            raise ValueError(f"pinned predecessor drift: {path}")
        files.append(
            {"path": path, "sha256": "sha256:" + actual, "size_bytes": source.stat().st_size}
        )
    document = {
        "schema": SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S16",
        "predecessor_slice": "S15",
        "s15_complete_at": "2026-09-12T15:17:39.296Z",
        "s15_uat_end_at": "2026-09-12T15:22:05.811Z",
        "abort_count": 3,
        "aborts": rows(),
        "sql_abort_message": SQL_MESSAGE,
        "trigger_name": TRIGGER,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "law_nexus_fixable": False,
        "s16_called_validate_milestone": False,
        "validation_projection_present": False,
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "same_defect_as_s09": True,
        "s12_hard_block_stopped_dispatch": False,
        "retry_substitute": False,
        "frozen_manifest": {"schema": MANIFEST_SCHEMA, "path": rel(root, manifest)},
    }
    manifest_doc = {
        "schema": MANIFEST_SCHEMA,
        "scope": "S16 predecessor-only; frozen tracked snapshots; no corpus walk",
        "files": files,
        "non_claims": [
            "census records do not repair the validate engine",
            "census does not call validate-milestone or change lifecycle state",
            "frozen hashes do not establish a validation projection",
        ],
    }
    census.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    census.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    manifest.write_text(json.dumps(manifest_doc, indent=2) + "\n", encoding="utf-8")


def check(root: Path, census: Path, manifest: Path) -> None:
    doc = load(census)
    keys = {
        "schema",
        "milestone",
        "slice",
        "predecessor_slice",
        "s15_complete_at",
        "s15_uat_end_at",
        "abort_count",
        "aborts",
        "sql_abort_message",
        "trigger_name",
        "engine_fix",
        "upstream_issue",
        "law_nexus_fixable",
        "s16_called_validate_milestone",
        "validation_projection_present",
        "c4_acceptance",
        "classification",
        "status_effect",
        "same_defect_as_s09",
        "s12_hard_block_stopped_dispatch",
        "retry_substitute",
        "frozen_manifest",
    }
    if not isinstance(doc, dict) or set(doc) != keys:
        raise ValueError("census schema is not closed")
    if (
        doc["schema"] != SCHEMA
        or doc["milestone"] != "M204-w2ktfw"
        or doc["slice"] != "S16"
        or doc["predecessor_slice"] != "S15"
    ):
        raise ValueError("census identity mismatch")
    if (
        type(doc["abort_count"]) is not int
        or doc["abort_count"] != 3
        or not isinstance(doc["aborts"], list)
        or len(doc["aborts"]) != 3
    ):
        raise ValueError("census must contain exactly three aborts")
    row_keys = {
        "ordinal",
        "unit_start_at",
        "unit_end_at",
        "unit_end_status",
        "finalize_status",
        "iteration_end_reason",
        "flow_id",
        "unit_id",
        "unit_type",
    }
    expected = rows()
    for actual, want in zip(doc["aborts"], expected):
        if not isinstance(actual, dict) or set(actual) != row_keys or actual != want:
            raise ValueError("abort row mismatch or ordering drift")
    for key, want in {
        "sql_abort_message": SQL_MESSAGE,
        "trigger_name": TRIGGER,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
    }.items():
        if doc[key] != want:
            raise ValueError(f"census {key} mismatch")
    for key in (
        "law_nexus_fixable",
        "s16_called_validate_milestone",
        "validation_projection_present",
        "same_defect_as_s09",
        "s12_hard_block_stopped_dispatch",
        "retry_substitute",
    ):
        if type(doc[key]) is not bool:
            raise ValueError(f"census {key} must be boolean")
    if any(
        doc[key] != want
        for key, want in {
            "law_nexus_fixable": False,
            "s16_called_validate_milestone": False,
            "validation_projection_present": False,
            "same_defect_as_s09": True,
            "s12_hard_block_stopped_dispatch": False,
            "retry_substitute": False,
        }.items()
    ):
        raise ValueError("census lifecycle polarity mismatch")
    manifest_doc = load(manifest)
    if (
        not isinstance(manifest_doc, dict)
        or set(manifest_doc) != {"schema", "scope", "files", "non_claims"}
        or manifest_doc["schema"] != MANIFEST_SCHEMA
    ):
        raise ValueError("manifest schema is not closed")
    if not isinstance(manifest_doc["files"], list) or len(manifest_doc["files"]) != len(PINNED):
        raise ValueError("manifest must contain six predecessor pins")
    for actual, (path, expected, size) in zip(manifest_doc["files"], PINNED):
        if (
            not isinstance(actual, dict)
            or set(actual) != {"path", "sha256", "size_bytes"}
            or actual["path"] != path
        ):
            raise ValueError(f"manifest row mismatch: {path}")
        source = safe_relative(root, path)
        if (
            actual["sha256"] != "sha256:" + expected
            or digest(source) != expected
            or type(actual["size_bytes"]) is not int
            or actual["size_bytes"] != size
        ):
            raise ValueError(f"manifest pin drift: {path}")
    print("S16_T01_CENSUS_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--census", type=Path, default=DEFAULT_CENSUS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        if args.command == "compose":
            compose(args.root.resolve(), args.census, args.manifest)
        else:
            check(args.root.resolve(), args.census, args.manifest)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s16_loop_note: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
