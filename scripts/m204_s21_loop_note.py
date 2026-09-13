#!/usr/bin/env python3
"""Closed, bounded census of the mixed post-S20 validate loop."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "law-nexus/gsd-post-s20-validate-loop/v1"
MANIFEST_SCHEMA = "law-nexus/m204-s21-frozen-hashes/v1"
DEFAULT_CENSUS = ROOT / "prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json"
DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s21-frozen-hashes.json"
ABORT_MESSAGE = "finalize-retry: You must call gsd_validate_milestone to persist the validation results. No current canonical validation result exists in the database."
SQL_MESSAGE = "technical verdict requires the current criterion and matching settled attempt"
TRIGGER = "trg_workflow_technical_verdict_scope"
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
    (
        "prd/migration/rust-evidence/m204-s18-post-s17-validate-loop.json",
        "9834c37db2d91c582b4751e2f34ae644bdf2284cae911df982028127435fd67d",
        2618,
    ),
    (
        "prd/migration/rust-evidence/m204-s18-frozen-hashes.json",
        "9f0c6addbcf7a8d0e63e3bc80af518d47e8152551fbe5226a077a21e37817370",
        2529,
    ),
    (
        "prd/migration/rust-evidence/m204-s19-post-s18-validate-abort.json",
        "7432d88a2d8a856a59850b5a5e49de6b3b5002745ded248a0b8ff7bddf1869e0",
        2296,
    ),
    (
        "prd/migration/rust-evidence/m204-s19-frozen-hashes.json",
        "d8717e49dabacac98106e6b096e2fe85e2e80a962263bf96c8c35a2f8f42e0d9",
        2950,
    ),
    (
        "prd/migration/rust-evidence/m204-s20-post-s19-validate-loop.json",
        "96e0ccfc8294ff8654be147ad8e475708ae4ef5a9da3f4b8a02dfd50276cae32",
        3894,
    ),
    (
        "prd/migration/rust-evidence/m204-s20-frozen-hashes.json",
        "c7239703906e6d337507a68e741509e4a9ab972b8185ea7aa1ff3fa1a06cd956",
        3368,
    ),
)


def load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def safe_file(root: Path, value: Any) -> Path:
    if not isinstance(value, str):
        raise ValueError("manifest path must be a string")
    path = Path(value)
    if (
        path.is_absolute()
        or "\\" in value
        or ".." in path.parts
        or any(p in {".git", ".gsd", ".planning", ".audits"} for p in path.parts)
    ):
        raise ValueError(f"unsafe manifest path: {value}")
    candidate = root / path
    if any(part.exists() and part.is_symlink() for part in (root, *candidate.parents, candidate)):
        raise ValueError(f"symlink component: {value}")
    resolved = candidate.resolve(strict=True)
    if resolved != candidate or not candidate.is_file():
        raise ValueError(f"not a regular file: {value}")
    return candidate


def pins(root: Path) -> list[dict[str, Any]]:
    result = []
    for path, expected, size in PINNED:
        source = safe_file(root, path)
        if (
            hashlib.sha256(source.read_bytes()).hexdigest() != expected
            or source.stat().st_size != size
        ):
            raise ValueError(f"pinned predecessor drift: {path}")
        result.append({"path": path, "sha256": "sha256:" + expected, "size_bytes": size})
    return result


def aborts() -> list[dict[str, Any]]:
    rows = [
        (
            1,
            "2026-09-13T02:34:23.836Z",
            "2026-09-13T02:44:05.408Z",
            "061fea44-c911-4578-b952-f123e3cf0319",
        ),
        (
            2,
            "2026-09-13T02:46:00.698Z",
            "2026-09-13T02:52:15.651Z",
            "9f2369bd-5e43-406a-a9bd-555a895bebc6",
        ),
    ]
    return [
        {
            "ordinal": n,
            "unit_start_at": start,
            "unit_end_at": end,
            "unit_end_status": "no-artifact",
            "finalize_status": "retry",
            "iteration_end_reason": ABORT_MESSAGE,
            "flow_id": flow,
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
        }
        for n, start, end, flow in rows
    ]


def cancelled() -> list[dict[str, Any]]:
    rows = [
        (
            1,
            "2026-09-13T02:53:57.639Z",
            "2026-09-13T03:01:55.033Z",
            "5c9ed6e5-06e7-4228-ac9a-0b7b9322ac29",
        ),
        (
            2,
            "2026-09-13T03:03:28.710Z",
            "2026-09-13T03:03:52.252Z",
            "581f8dbe-b14f-4426-9b81-0cf5adc41ea4",
        ),
    ]
    return [
        {
            "ordinal": n,
            "unit_start_at": start,
            "unit_end_at": end,
            "unit_end_status": "cancelled",
            "artifact_verified": False,
            "error_category": "provider",
            "error_message": "Provider error: Connection error.",
            "flow_id": flow,
            "unit_id": "M204-w2ktfw",
            "unit_type": "validate-milestone",
            "journal_unit_start_present": True,
        }
        for n, start, end, flow in rows
    ]


def supervisor_exit() -> dict[str, Any]:
    return {
        "kind": "closeout_break_not_recovering",
        "query_at": "2026-09-13T03:02:36Z",
        "classify_at": "2026-09-13T03:04:04Z",
        "classify_status": "blocked",
        "interrupted": False,
        "tool_calls": 0,
        "journal_unit_start_present": True,
        "headless_pid": "1841192",
        "unit_id": "M204-w2ktfw",
        "unit_type": "validate-milestone",
        "stop_at": "2026-09-13T03:04:07Z",
        "stop_text": "closeout break not recovering after 4 retries (status=blocked)",
        "exit_reason": "closeout-break",
        "closeout_n": 0,
        "next_unit_type": "research-slice",
        "next_unit_id": "M204-w2ktfw/S21",
        "next_unit_start_at": "2026-09-13T03:20:45.066Z",
    }


def compose(root: Path, census: Path, manifest: Path) -> None:
    frozen = pins(root)
    document = {
        "schema": SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S21",
        "predecessor_slice": "S20",
        "s20_complete_at": "2026-09-13T02:32:31.723Z",
        "s20_uat_end_at": "2026-09-13T02:34:04.689Z",
        "dispatch_count": 4,
        "abort_count": 2,
        "aborts": aborts(),
        "cancelled_count": 2,
        "cancelled": cancelled(),
        "supervisor_exit": supervisor_exit(),
        "sql_abort_message": SQL_MESSAGE,
        "trigger_name": TRIGGER,
        "engine_fix": "not_fixed",
        "upstream_issue": "not_filed",
        "law_nexus_fixable": False,
        "s21_called_validate_milestone": False,
        "validation_projection_present": False,
        "c4_acceptance": "non-pass",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "same_defect_as_s09": True,
        "s12_hard_block_stopped_dispatch": False,
        "s16_census_stopped_dispatch": False,
        "s17_census_stopped_dispatch": False,
        "s18_census_stopped_dispatch": False,
        "s19_census_stopped_dispatch": False,
        "s20_census_stopped_dispatch": False,
        "retry_substitute": False,
        "frozen_manifest": {
            "schema": MANIFEST_SCHEMA,
            "path": manifest.resolve().relative_to(root.resolve()).as_posix(),
        },
    }
    manifest_doc = {
        "schema": MANIFEST_SCHEMA,
        "scope": "S21 predecessor-only; sixteen frozen tracked snapshots; no self-hash and no corpus walk",
        "files": frozen,
        "non_claims": [
            "census records do not repair the validate engine",
            "census does not call validate-milestone or change lifecycle state",
            "cancelled rows are not intercepts and have no finalize fields",
            "supervisor_exit is separate from abort and cancelled rows",
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
        "s20_complete_at",
        "s20_uat_end_at",
        "dispatch_count",
        "abort_count",
        "aborts",
        "cancelled_count",
        "cancelled",
        "supervisor_exit",
        "sql_abort_message",
        "trigger_name",
        "engine_fix",
        "upstream_issue",
        "law_nexus_fixable",
        "s21_called_validate_milestone",
        "validation_projection_present",
        "c4_acceptance",
        "classification",
        "status_effect",
        "same_defect_as_s09",
        "s12_hard_block_stopped_dispatch",
        "s16_census_stopped_dispatch",
        "s17_census_stopped_dispatch",
        "s18_census_stopped_dispatch",
        "s19_census_stopped_dispatch",
        "s20_census_stopped_dispatch",
        "retry_substitute",
        "frozen_manifest",
    }
    if not isinstance(doc, dict) or set(doc) != expected:
        raise ValueError("census schema is not closed")
    if (doc["schema"], doc["milestone"], doc["slice"], doc["predecessor_slice"]) != (
        SCHEMA,
        "M204-w2ktfw",
        "S21",
        "S20",
    ):
        raise ValueError("census identity mismatch")
    if (doc["s20_complete_at"], doc["s20_uat_end_at"]) != (
        "2026-09-13T02:32:31.723Z",
        "2026-09-13T02:34:04.689Z",
    ):
        raise ValueError("predecessor timestamps mismatch")
    if (
        type(doc["dispatch_count"]) is not int
        or doc["dispatch_count"] != 4
        or type(doc["abort_count"]) is not int
        or doc["abort_count"] != 2
        or doc["aborts"] != aborts()
    ):
        raise ValueError("abort or dispatch census mismatch")
    if (
        type(doc["cancelled_count"]) is not int
        or doc["cancelled_count"] != 2
        or doc["cancelled"] != cancelled()
    ):
        raise ValueError("cancelled census mismatch")
    if doc["supervisor_exit"] != supervisor_exit():
        raise ValueError("supervisor exit mismatch")
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
    false_flags = (
        "law_nexus_fixable",
        "s21_called_validate_milestone",
        "validation_projection_present",
        "s12_hard_block_stopped_dispatch",
        "s16_census_stopped_dispatch",
        "s17_census_stopped_dispatch",
        "s18_census_stopped_dispatch",
        "s19_census_stopped_dispatch",
        "s20_census_stopped_dispatch",
        "retry_substitute",
    )
    for key in false_flags:
        if type(doc[key]) is not bool or doc[key] is not False:
            raise ValueError(f"census polarity mismatch: {key}")
    if type(doc["same_defect_as_s09"]) is not bool or doc["same_defect_as_s09"] is not True:
        raise ValueError("census polarity mismatch: same_defect_as_s09")
    frozen = load(manifest)
    if (
        not isinstance(frozen, dict)
        or set(frozen) != {"schema", "scope", "files", "non_claims"}
        or frozen["schema"] != MANIFEST_SCHEMA
        or not isinstance(frozen["files"], list)
        or len(frozen["files"]) != 16
    ):
        raise ValueError("manifest schema is not closed")
    if frozen["files"] != pins(root):
        raise ValueError("manifest pin drift or ordering mismatch")
    if doc["frozen_manifest"] != {
        "schema": MANIFEST_SCHEMA,
        "path": manifest.resolve().relative_to(root.resolve()).as_posix(),
    }:
        raise ValueError("frozen manifest reference mismatch")
    print("S21_T01_CENSUS_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--census", type=Path, default=DEFAULT_CENSUS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        (compose if args.command == "compose" else check)(
            args.root.resolve(), args.census, args.manifest
        )
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s21_loop_note: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
