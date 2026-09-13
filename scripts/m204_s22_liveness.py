#!/usr/bin/env python3
"""Compose and independently check the bounded S22 external-blocker packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER_SCHEMA = "law-nexus/m204-s22-external-blocker/v1"
MANIFEST_SCHEMA = "law-nexus/m204-s22-frozen-hashes/v1"
DEFAULT_LEDGER = ROOT / "prd/migration/rust-evidence/m204-s22-external-blocker.json"
DEFAULT_MANIFEST = ROOT / "prd/migration/rust-evidence/m204-s22-frozen-hashes.json"
TRIGGER = "trg_workflow_technical_verdict_scope"
SQL_ABORT = "technical verdict requires the current criterion and matching settled attempt"

# This is an explicit, ordered allowlist.  It intentionally does not walk the corpus.
S21_PINS = (
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
EXTRA = (
    ("prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json",),
    ("prd/migration/rust-evidence/m204-s21-frozen-hashes.json",),
    ("prd/migration/rust-evidence/m204-s14-c4-acceptance.json",),
    ("prd/migration/rust-evidence/m204-s14-verification-battery.json",),
    ("prd/migration/rust-evidence/m204-s10-c4-operational-receipt.json",),
    ("prd/migration/rust-evidence/m204-validation-battery-20260912-s10.json",),
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


def safe_path(root: Path, value: Any, *, existing: bool = True) -> Path:
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


def frozen_pins(root: Path) -> list[dict[str, Any]]:
    entries = list(S21_PINS)
    for (path,) in EXTRA:
        source = safe_path(root, path)
        entries.append(
            (path, hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_size)
        )
    result = []
    for path, expected, size in entries:
        source = safe_path(root, path)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != expected or source.stat().st_size != size:
            raise ValueError(f"predecessor drift: {path}")
        result.append({"path": path, "sha256": f"sha256:{expected}", "size_bytes": size})
    if len(result) != 22 or len({row["path"] for row in result}) != 22:
        raise ValueError("manifest must contain 22 unique pins")
    return result


def expected_ledger(manifest_path: str) -> dict[str, Any]:
    return {
        "schema": LEDGER_SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S22",
        "predecessor_slice": "S21",
        "path": "external-blocker",
        "gsd_recovery_liveness": "blocked-external",
        "engine_fix": "not_fixed",
        "law_nexus_fixable": False,
        "upstream_issue": "not_filed",
        "same_defect_as_s09": True,
        "trigger_name": TRIGGER,
        "sql_abort_message": SQL_ABORT,
        "predecessor_refs": {
            "s09_deadlock": "prd/migration/rust-evidence/m204-s09-gsd-validate-deadlock.json",
            "s09_trigger_sql": "prd/migration/rust-evidence/m204-s09-trigger-sql.json",
            "s21_census": "prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json",
        },
        "c4_control_surface": "contour_diagnostics_contract.Comparison",
        "c4_control": "not-run",
        "c4_operational_acceptance": "non-pass",
        "reason": "S10 duplicate inventory_digest",
        "duration_ms": 4969991,
        "duration_floor_ms": 3600000,
        "product_failed_distinct": True,
        "retry_substitute": False,
        "s22_called_validate_milestone": False,
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "frozen_manifest": {"schema": MANIFEST_SCHEMA, "path": manifest_path},
    }


def compose(root: Path, ledger: Path, manifest: Path) -> None:
    if ledger.exists() or manifest.exists():
        raise ValueError("compose refuses to overwrite an existing destination")
    ledger_rel = ledger.resolve().relative_to(root.resolve()).as_posix()
    manifest_rel = manifest.resolve().relative_to(root.resolve()).as_posix()
    safe_path(root, ledger_rel, existing=False)
    safe_path(root, manifest_rel, existing=False)
    pins = frozen_pins(root)
    manifest_doc = {
        "schema": MANIFEST_SCHEMA,
        "scope": "S22 predecessor-only; 22 ordered pins; no self-hash and no corpus walk",
        "files": pins,
        "non_claims": [
            "pins do not repair the GSD engine",
            "pins do not establish validation",
            "C4 control is measured separately",
            "no validate retry or lifecycle promotion is claimed",
        ],
    }
    ledger_doc = expected_ledger(manifest_rel)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(manifest_doc, indent=2) + "\n", encoding="utf-8")
    ledger.write_text(json.dumps(ledger_doc, indent=2) + "\n", encoding="utf-8")


def check(root: Path, ledger: Path, manifest: Path) -> None:
    ledger_rel = ledger.resolve().relative_to(root.resolve()).as_posix()
    manifest_rel = manifest.resolve().relative_to(root.resolve()).as_posix()
    safe_path(root, ledger_rel)
    safe_path(root, manifest_rel)
    doc = load(ledger)
    expected = expected_ledger(manifest_rel)
    if not strict_equal(doc, expected):
        raise ValueError("ledger schema, literals, or ordered fields mismatch")
    frozen = load(manifest)
    if (
        list(frozen) != ["schema", "scope", "files", "non_claims"]
        or frozen["schema"] != MANIFEST_SCHEMA
    ):
        raise ValueError("manifest schema is not closed")
    if not isinstance(frozen["files"], list) or not strict_equal(
        frozen["files"], frozen_pins(root)
    ):
        raise ValueError("manifest pins drifted, reordered, or changed")
    if any(row["path"] in {ledger_rel, manifest_rel} for row in frozen["files"]):
        raise ValueError("self-hash is forbidden")
    print("S22_T01_BLOCKER_OK")
    print("S22_T01_EXACT_RECORDS_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        ledger = args.ledger if args.ledger.is_absolute() else root / args.ledger
        manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
        (compose if args.command == "compose" else check)(root, ledger, manifest)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"m204_s22_liveness: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
