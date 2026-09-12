#!/usr/bin/env python3
"""Closed census of the two post-S16 validate aborts and one predispatch intercept.

The command is a bounded, subprocess-only consumer of frozen evidence.  It never
opens GSD, a journal, a database, a supervisor log, or the legal corpus, and it
never calls a lifecycle API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/gsd-post-s16-validate-loop/v1"
MANIFEST_SCHEMA = "law-nexus/m204-s17-frozen-hashes/v1"
DEFAULT_CENSUS = ROOT / "prd/migration/rust-evidence/m204-s17-post-s16-validate-loop.json"
DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s17-frozen-hashes.json"
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
    (
        "prd/migration/rust-evidence/m204-s16-post-s15-validate-loop.json",
        "be53f15f7b4aa9ef60638b52fe6d05f6a2b98d50a366fd126e9a5fcb7239ffc1",
        2525,
    ),
    (
        "prd/migration/rust-evidence/m204-s16-frozen-hashes.json",
        "bfbad5070c356e7405415a32afc12bdf16714f89ba0778b91b76bef01da6af61",
        1589,
    ),
)
ABORT_MESSAGE = "finalize-retry: You must call gsd_validate_milestone to persist the validation results. No current canonical validation result exists in the database."
SQL_MESSAGE = "technical verdict requires the current criterion and matching settled attempt"
TRIGGER = "trg_workflow_technical_verdict_scope"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
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
        or any(part in banned for part in path.parts)
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


def aborts() -> list[dict[str, Any]]:
    return [
        {
            "ordinal": 1,
            "unit_start_at": "2026-09-12T17:02:09.344Z",
            "unit_end_at": "2026-09-12T17:09:53.896Z",
            "unit_end_status": "no-artifact",
            "finalize_status": "retry",
            "iteration_end_reason": ABORT_MESSAGE,
            "flow_id": "348f1061-7c45-42ec-a4f3-49d75280035b",
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
        },
        {
            "ordinal": 2,
            "unit_start_at": "2026-09-12T17:11:22.286Z",
            "unit_end_at": "2026-09-12T17:21:38.037Z",
            "unit_end_status": "no-artifact",
            "finalize_status": "retry",
            "iteration_end_reason": ABORT_MESSAGE,
            "flow_id": "5d433aca-cb02-462e-84fc-20ac708ad76e",
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
        },
    ]


def intercept() -> dict[str, Any]:
    return {
        "kind": "predispatch_cancelled_interrupted",
        "query_at": "2026-09-12T17:22:08Z",
        "classify_at": "2026-09-12T17:22:52Z",
        "classify_status": "cancelled",
        "interrupted": True,
        "tool_calls": 0,
        "journal_unit_start_present": False,
        "headless_pid": "1000787",
        "unit_id": "M204-w2ktfw",
        "unit_type": "validate-milestone",
        "next_unit_type": "research-slice",
        "next_unit_id": "M204-w2ktfw/S17",
        "next_unit_start_at": "2026-09-12T17:24:08.671Z",
        "crash_restart": 2,
    }


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
        "slice": "S17",
        "predecessor_slice": "S16",
        "s16_complete_at": "2026-09-12T17:00:29.680Z",
        "s16_uat_end_at": "2026-09-12T17:01:50.342Z",
        "abort_count": 2,
        "aborts": aborts(),
        "intercept": intercept(),
        "sql_abort_message": SQL_MESSAGE,
        "trigger_name": TRIGGER,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "law_nexus_fixable": False,
        "s17_called_validate_milestone": False,
        "validation_projection_present": False,
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "same_defect_as_s09": True,
        "s12_hard_block_stopped_dispatch": False,
        "s16_census_stopped_dispatch": False,
        "retry_substitute": False,
        "frozen_manifest": {"schema": MANIFEST_SCHEMA, "path": rel(root, manifest)},
    }
    manifest_doc = {
        "schema": MANIFEST_SCHEMA,
        "scope": "S17 predecessor-only; eight frozen tracked snapshots; no corpus walk",
        "files": files,
        "non_claims": [
            "census records do not repair the validate engine",
            "census does not call validate-milestone or change lifecycle state",
            "intercept is separate from the two no-artifact aborts",
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
        "s16_complete_at",
        "s16_uat_end_at",
        "abort_count",
        "aborts",
        "intercept",
        "sql_abort_message",
        "trigger_name",
        "engine_fix",
        "upstream_issue",
        "law_nexus_fixable",
        "s17_called_validate_milestone",
        "validation_projection_present",
        "c4_acceptance",
        "classification",
        "status_effect",
        "same_defect_as_s09",
        "s12_hard_block_stopped_dispatch",
        "s16_census_stopped_dispatch",
        "retry_substitute",
        "frozen_manifest",
    }
    if not isinstance(doc, dict) or set(doc) != keys:
        raise ValueError("census schema is not closed")
    if (doc["schema"], doc["milestone"], doc["slice"], doc["predecessor_slice"]) != (
        SCHEMA,
        "M204-w2ktfw",
        "S17",
        "S16",
    ):
        raise ValueError("census identity mismatch")
    if (
        type(doc["abort_count"]) is not int
        or doc["abort_count"] != 2
        or not isinstance(doc["aborts"], list)
        or len(doc["aborts"]) != 2
    ):
        raise ValueError("census must contain exactly two aborts")
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
    for actual, want in zip(doc["aborts"], aborts()):
        if not isinstance(actual, dict) or set(actual) != row_keys or actual != want:
            raise ValueError("abort row mismatch or ordering drift")
    intercept_keys = set(intercept())
    if (
        not isinstance(doc["intercept"], dict)
        or set(doc["intercept"]) != intercept_keys
        or doc["intercept"] != intercept()
    ):
        raise ValueError("intercept mismatch or closed-schema drift")
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
        "s17_called_validate_milestone",
        "validation_projection_present",
        "same_defect_as_s09",
        "s12_hard_block_stopped_dispatch",
        "s16_census_stopped_dispatch",
        "retry_substitute",
    ):
        if type(doc[key]) is not bool:
            raise ValueError(f"census {key} must be boolean")
    if any(
        doc[key] != want
        for key, want in {
            "law_nexus_fixable": False,
            "s17_called_validate_milestone": False,
            "validation_projection_present": False,
            "same_defect_as_s09": True,
            "s12_hard_block_stopped_dispatch": False,
            "s16_census_stopped_dispatch": False,
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
        raise ValueError("manifest must contain eight predecessor pins")
    for actual, (path, expected, size) in zip(manifest_doc["files"], PINNED):
        if not isinstance(actual, dict) or set(actual) != {"path", "sha256", "size_bytes"}:
            raise ValueError(f"manifest row mismatch: {path}")
        source = safe_relative(root, actual["path"])
        if actual["path"] != path:
            raise ValueError(f"manifest row mismatch: {path}")
        if (
            actual["sha256"] != "sha256:" + expected
            or digest(source) != expected
            or type(actual["size_bytes"]) is not int
            or actual["size_bytes"] != size
        ):
            raise ValueError(f"manifest pin drift: {path}")
    print("S17_T01_CENSUS_OK")


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
        print(f"m204_s17_loop_note: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
