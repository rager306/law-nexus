#!/usr/bin/env python3
"""Closed, bounded census of the two post-S17 aborts and one intercept."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/gsd-post-s17-validate-loop/v1"
MANIFEST_SCHEMA = "law-nexus/m204-s18-frozen-hashes/v1"
DEFAULT_CENSUS = ROOT / "prd/migration/rust-evidence/m204-s18-post-s17-validate-loop.json"
DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s18-frozen-hashes.json"
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
    (
        "prd/migration/rust-evidence/m204-s17-post-s16-validate-loop.json",
        "181e85df6741dad91c4f28ab6d225ad03a8d6dc300fd0234b4698506eeae5867",
        2578,
    ),
    (
        "prd/migration/rust-evidence/m204-s17-frozen-hashes.json",
        "8237e88a8faadf74cdc1653a74e9986e4298b4d386ef4a7cef82054fc877b7ba",
        2069,
    ),
)
ABORT_MESSAGE = "finalize-retry: You must call gsd_validate_milestone to persist the validation results. No current canonical validation result exists in the database."
SQL_MESSAGE = "technical verdict requires the current criterion and matching settled attempt"
TRIGGER = "trg_workflow_technical_verdict_scope"


def load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def safe_file(root: Path, value: Any) -> Path:
    if not isinstance(value, str):
        raise ValueError("manifest path must be a string")
    path = Path(value)
    if (
        path.is_absolute()
        or "\\" in value
        or ".." in path.parts
        or any(x in {".git", ".gsd", ".planning", ".audits"} for x in path.parts)
    ):
        raise ValueError(f"unsafe manifest path: {value}")
    candidate = root / path
    for part in (root, *candidate.parents, candidate):
        if part.exists() and part.is_symlink():
            raise ValueError(f"symlink component: {value}")
    resolved = candidate.resolve(strict=True)
    if resolved != candidate or not candidate.is_file():
        raise ValueError(f"not a regular file: {value}")
    return candidate


def aborts() -> list[dict[str, Any]]:
    return [
        {
            "ordinal": 1,
            "unit_start_at": "2026-09-12T18:15:23.617Z",
            "unit_end_at": "2026-09-12T18:43:50.786Z",
            "unit_end_status": "no-artifact",
            "finalize_status": "retry",
            "iteration_end_reason": ABORT_MESSAGE,
            "flow_id": "f76ce443-afce-43bb-9342-0b0484260951",
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
        },
        {
            "ordinal": 2,
            "unit_start_at": "2026-09-12T18:45:33.306Z",
            "unit_end_at": "2026-09-12T18:59:08.582Z",
            "unit_end_status": "no-artifact",
            "finalize_status": "retry",
            "iteration_end_reason": ABORT_MESSAGE,
            "flow_id": "886e98de-6b9f-4385-a9e5-0ac0504139d0",
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
        },
    ]


def intercept() -> dict[str, Any]:
    return {
        "kind": "predispatch_cancelled_interrupted",
        "query_at": "2026-09-12T18:59:51Z",
        "classify_at": "2026-09-12T19:00:36Z",
        "classify_status": "cancelled",
        "interrupted": True,
        "tool_calls": 0,
        "journal_unit_start_present": False,
        "headless_pid": "1130971",
        "unit_id": "M204-w2ktfw",
        "unit_type": "validate-milestone",
        "next_unit_type": "research-slice",
        "next_unit_id": "M204-w2ktfw/S18",
        "next_unit_start_at": "2026-09-12T19:01:58.658Z",
        "crash_restart": 2,
    }


def pins(root: Path) -> list[dict[str, Any]]:
    result = []
    for path, expected, size in PINNED:
        source = safe_file(root, path)
        if digest(source) != expected or source.stat().st_size != size:
            raise ValueError(f"pinned predecessor drift: {path}")
        result.append({"path": path, "sha256": "sha256:" + expected, "size_bytes": size})
    return result


def compose(root: Path, census: Path, manifest: Path) -> None:
    files = pins(root)
    document = {
        "schema": SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S18",
        "predecessor_slice": "S17",
        "s17_complete_at": "2026-09-12T18:13:44.221Z",
        "s17_uat_end_at": "2026-09-12T18:15:00.597Z",
        "abort_count": 2,
        "aborts": aborts(),
        "intercept": intercept(),
        "sql_abort_message": SQL_MESSAGE,
        "trigger_name": TRIGGER,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "law_nexus_fixable": False,
        "s18_called_validate_milestone": False,
        "validation_projection_present": False,
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "same_defect_as_s09": True,
        "s12_hard_block_stopped_dispatch": False,
        "s16_census_stopped_dispatch": False,
        "s17_census_stopped_dispatch": False,
        "retry_substitute": False,
        "frozen_manifest": {"schema": MANIFEST_SCHEMA, "path": rel(root, manifest)},
    }
    manifest_doc = {
        "schema": MANIFEST_SCHEMA,
        "scope": "S18 predecessor-only; ten frozen tracked snapshots; no self-hash and no corpus walk",
        "files": files,
        "non_claims": [
            "census records do not repair the validate engine",
            "census does not call validate-milestone or change lifecycle state",
            "intercept is separate from the two no-artifact aborts",
            "frozen hashes do not establish a validation projection",
            "no SIGTERM claim is made",
        ],
    }
    census.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    census.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    manifest.write_text(json.dumps(manifest_doc, indent=2) + "\n", encoding="utf-8")


def check(root: Path, census: Path, manifest: Path) -> None:
    doc = load(census)
    expected = {
        "schema",
        "milestone",
        "slice",
        "predecessor_slice",
        "s17_complete_at",
        "s17_uat_end_at",
        "abort_count",
        "aborts",
        "intercept",
        "sql_abort_message",
        "trigger_name",
        "engine_fix",
        "upstream_issue",
        "law_nexus_fixable",
        "s18_called_validate_milestone",
        "validation_projection_present",
        "c4_acceptance",
        "classification",
        "status_effect",
        "same_defect_as_s09",
        "s12_hard_block_stopped_dispatch",
        "s16_census_stopped_dispatch",
        "s17_census_stopped_dispatch",
        "retry_substitute",
        "frozen_manifest",
    }
    if not isinstance(doc, dict) or set(doc) != expected:
        raise ValueError("census schema is not closed")
    if (doc["schema"], doc["milestone"], doc["slice"], doc["predecessor_slice"]) != (
        SCHEMA,
        "M204-w2ktfw",
        "S18",
        "S17",
    ):
        raise ValueError("census identity mismatch")
    if type(doc["abort_count"]) is not int or doc["abort_count"] != 2 or doc["aborts"] != aborts():
        raise ValueError("abort census mismatch")
    if doc["intercept"] != intercept():
        raise ValueError("intercept mismatch")
    for key, value in {
        "sql_abort_message": SQL_MESSAGE,
        "trigger_name": TRIGGER,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
    }.items():
        if doc[key] != value:
            raise ValueError(f"census {key} mismatch")
    for key, value in {
        "law_nexus_fixable": False,
        "s18_called_validate_milestone": False,
        "validation_projection_present": False,
        "same_defect_as_s09": True,
        "s12_hard_block_stopped_dispatch": False,
        "s16_census_stopped_dispatch": False,
        "s17_census_stopped_dispatch": False,
        "retry_substitute": False,
    }.items():
        if type(doc[key]) is not bool or doc[key] != value:
            raise ValueError(f"census polarity mismatch: {key}")
    m = load(manifest)
    if (
        not isinstance(m, dict)
        or set(m) != {"schema", "scope", "files", "non_claims"}
        or m["schema"] != MANIFEST_SCHEMA
        or not isinstance(m["files"], list)
        or len(m["files"]) != 10
    ):
        raise ValueError("manifest schema is not closed")
    if m["files"] != pins(root):
        raise ValueError("manifest pin drift or ordering mismatch")
    print("S18_T01_CENSUS_OK")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("compose", "check"))
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--census", type=Path, default=DEFAULT_CENSUS)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    a = p.parse_args()
    try:
        (compose if a.command == "compose" else check)(a.root.resolve(), a.census, a.manifest)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s18_loop_note: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
