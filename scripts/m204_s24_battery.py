#!/usr/bin/env python3
"""Compose and check the S24 operational battery without a corpus walk.

The battery is a source-bound projection over already-recorded S22/S23/S24
artifacts.  It never opens the GSD database, journal, or external engine.
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
BATTERY_SCHEMA = "law-nexus/m204-s24-operational-battery/v1"
BATTERY_REL = "prd/migration/rust-evidence/m204-s24-operational-battery.json"
LEDGER_REL = "prd/migration/rust-evidence/m204-s24-criterion-resolution.json"
MANIFEST_REL = "prd/migration/rust-evidence/m204-s24-frozen-hashes.json"
RECEIPT_REL = "prd/migration/rust-evidence/m204-s23-remediation-v2-c4-receipt.json"
DIAGNOSTICS_REL = "prd/migration/rust-evidence/m204-s23-remediation-v2-c4-diagnostics.jsonl"
SOURCE_REVISION = "sha256:fb0ef39ac1f557555266139d3b76620b4f41994a609dc6cd9f68ab30c027cd5b"
DURATION_MS = 4991302
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


def safe_file(root: Path, value: str, *, existing: bool = True) -> Path:
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


def expected_battery() -> dict[str, Any]:
    return {
        "schema": BATTERY_SCHEMA,
        "milestone": "M204-w2ktfw",
        "slice": "S24",
        "c4_operational_acceptance": "pass",
        "c4_control": "pass",
        "gsd_recovery_liveness": "blocked-external",
        "disposition": "needs-remediation",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "receipt": RECEIPT_REL,
        "diagnostics": DIAGNOSTICS_REL,
        "criterion_resolution": LEDGER_REL,
        "frozen_manifest": MANIFEST_REL,
        "source_revision": SOURCE_REVISION,
        "terminal_outcome": {"outcome": "complete", "exit_code": 0, "timeout": False},
        "duration_ms": DURATION_MS,
        "non_claims": NON_CLAIMS,
    }


def compose(root: Path, battery: Path) -> None:
    battery_rel = battery.resolve().relative_to(root.resolve()).as_posix()
    if battery_rel != BATTERY_REL:
        raise ValueError("S24 battery destination is fixed and source-bound")
    safe_file(root, battery_rel, existing=False)
    if battery.exists():
        raise ValueError("compose refuses to overwrite an existing destination")
    battery.parent.mkdir(parents=True, exist_ok=True)
    with battery.open("x", encoding="utf-8") as stream:
        json.dump(expected_battery(), stream, indent=2)
        stream.write("\n")


def run(root: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)


def check_consumers(root: Path) -> None:
    checks = [
        [sys.executable, "scripts/m204_s24_liveness.py", "check"],
        [
            sys.executable,
            "scripts/m204_s23_c4_run.py",
            "--verify-receipt",
            RECEIPT_REL,
            "--require-operational-pass",
        ],
        [sys.executable, "scripts/m204_s22_liveness.py", "check"],
    ]
    for command in checks:
        result = run(root, command)
        if result.returncode != 0:
            raise ValueError(
                f"consumer failed: {' '.join(command)}: {result.stdout}{result.stderr}"
            )


def check(root: Path, battery: Path) -> None:
    battery_rel = battery.resolve().relative_to(root.resolve()).as_posix()
    if battery_rel != BATTERY_REL:
        raise ValueError("S24 battery destination is fixed and source-bound")
    safe_file(root, battery_rel)
    document = load(battery)
    if not strict_equal(document, expected_battery()):
        raise ValueError("battery schema, literals, or ordered fields mismatch")
    ledger = load(safe_file(root, LEDGER_REL))
    if (
        ledger.get("c4_operational_acceptance") != "pass"
        or ledger.get("gsd_recovery_liveness") != "blocked-external"
    ):
        raise ValueError("criterion-resolution does not preserve the required outcome")
    receipt = load(safe_file(root, RECEIPT_REL))
    if (
        receipt.get("source_revision") != SOURCE_REVISION
        or receipt.get("duration_ms") != DURATION_MS
    ):
        raise ValueError("receipt source binding or duration drifted")
    if (
        digest(safe_file(root, DIAGNOSTICS_REL))
        != "sha256:4d3165605dc44c7b78858f5b260b75b13837b2749d7da5d87d419c44df9ab30d"
    ):
        raise ValueError("diagnostics hash drifted")
    check_consumers(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compose", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--battery", type=Path, default=Path(BATTERY_REL))
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        battery = args.battery if args.battery.is_absolute() else root / args.battery
        if args.command == "compose":
            compose(root, battery)
        else:
            check(root, battery)
        print("S24_T03_C4_PASS_OK")
        print("S24_T03_GSD_BLOCKED_EXTERNAL_OK")
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"m204_s24_battery: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
