#!/usr/bin/env python3
"""Detached, source-bound S23 remediation walk with immutable new outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
RECEIPT = "prd/migration/rust-evidence/m204-s23-remediation-v2-c4-receipt.json"
DIAGNOSTICS = "prd/migration/rust-evidence/m204-s23-remediation-v2-c4-diagnostics.jsonl"
BATTERY = "prd/migration/rust-evidence/m204-s23-remediation-v2-battery.json"
MANIFEST = "prd/migration/rust-evidence/m204-s23-remediation-v2-frozen-hashes.json"
OWNER = "prd/migration/rust-evidence/m204-s23-remediation-v2-owner-resolution.json"
ATTEMPTS = EVIDENCE / "m204-s23-remediation-v2-attempts"
LOCK = ATTEMPTS / ".active-lock"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def immutable(path: Path) -> None:
    if path.exists():
        raise ValueError(f"immutable remediation output exists: {path.relative_to(ROOT)}")


def owner_resolution() -> dict[str, Any]:
    return {
        "schema": "law-nexus/m204-s23-owner-resolution/v1",
        "decision": "D453",
        "scope": "evidence-contract",
        "resolution": "reader-aligned-to-product-format",
        "rule": "non-empty lines are JSON objects; at least one non-empty inventory_digest exists; all present digests agree",
        "malformed_cases": ["malformed", "non-object", "empty digest", "unequal digest"],
        "engine_owner_resolution": "not-live-probed",
        "gsd_recovery_liveness": "blocked-external",
        "law_nexus_fixable": False,
        "engine_fix": "not_fixed",
        "retry_substitute": False,
        "s23_called_validate_milestone": False,
        "disposition": "needs-remediation",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "non_claims": [
            "D453 resolves the evidence-reader format only",
            "this packet is not a live GSD recovery proof",
            "no validate call or engine mutation was performed",
        ],
    }


def compose() -> None:
    for rel in (BATTERY, MANIFEST):
        immutable(ROOT / rel)
    owner = owner_resolution()
    owner_path = ROOT / OWNER
    if owner_path.exists():
        if load(owner_path) != owner:
            raise ValueError("existing owner-resolution packet does not match D453")
    else:
        owner_path.parent.mkdir(parents=True, exist_ok=True)
        with owner_path.open("x", encoding="utf-8") as stream:
            json.dump(owner, stream, indent=2)
            stream.write("\n")
    manifest_paths = [
        "scripts/m204_s23_c4_run.py",
        "scripts/m204_s23_remediation.py",
        OWNER,
    ]
    manifest = {
        "schema": "law-nexus/m204-s23-remediation-frozen-hashes/v1",
        "scope": "D453-aligned remediation source and owner-resolution pins; no corpus walk",
        "files": [
            {
                "path": value,
                "sha256": digest(ROOT / value),
                "size_bytes": (ROOT / value).stat().st_size,
            }
            for value in manifest_paths
        ],
        "non_claims": [
            "pins do not establish GSD recovery",
            "full walk remains required for C4 acceptance",
        ],
    }
    with (ROOT / MANIFEST).open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    battery = {
        "schema": "law-nexus/m204-s23-remediation-battery/v1",
        "milestone": "M204-w2ktfw",
        "slice": "S23",
        "owner_resolution": OWNER,
        "frozen_manifest": MANIFEST,
        "c4_operational_acceptance": "not-run",
        "gsd_recovery_liveness": "blocked-external",
        "disposition": "needs-remediation",
        "classification": "supporting-only",
        "status_effect": "unchanged",
        "receipt": RECEIPT,
        "diagnostics": DIAGNOSTICS,
        "non_claims": [
            "not a GSD recovery pass",
            "does not call validate",
            "does not close requirements",
        ],
    }
    with (ROOT / BATTERY).open("x", encoding="utf-8") as stream:
        json.dump(battery, stream, indent=2)
        stream.write("\n")


def live(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def read_lock() -> dict[str, Any] | None:
    if not LOCK.exists():
        return None
    value = load(LOCK)
    if (
        not isinstance(value, dict)
        or type(value.get("pid")) is not int
        or not isinstance(value.get("attempt_id"), str)
    ):
        raise ValueError("remediation lock schema is malformed")
    return value


def worker(attempt_id: str) -> int:
    build = subprocess.run(
        ["cargo", "build", "--offline", "--bin", "npa-contour-diagnostics"], cwd=ROOT, check=False
    )
    if build.returncode:
        return build.returncode
    source = digest(ROOT / "scripts/m204_s23_c4_run.py")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/m204_s23_c4_run.py"),
            "--source-revision",
            source,
            "--attempt-id",
            attempt_id,
            "--out",
            RECEIPT,
            "--diagnostics-out",
            DIAGNOSTICS,
            "--jobs",
            "1",
            "--budget-seconds",
            "3600",
            "--timeout-seconds",
            "10800",
        ],
        cwd=ROOT,
        check=False,
    )
    receipt = ROOT / RECEIPT
    if not receipt.is_file():
        return result.returncode or 1
    battery = load(ROOT / BATTERY)
    observed = load(receipt)
    battery.update(
        {
            "c4_operational_acceptance": observed["claims"]["operational_acceptance"],
            "terminal_outcome": observed["terminal"],
            "duration_ms": observed["duration_ms"],
            "source_revision": source,
            "gsd_recovery_liveness": "blocked-external",
            "disposition": "needs-remediation",
        }
    )
    with (ROOT / BATTERY).open("w", encoding="utf-8") as stream:
        json.dump(battery, stream, indent=2)
        stream.write("\n")
    return result.returncode


def start(attempt_id: str) -> None:
    if not attempt_id or any(c in attempt_id for c in "/\\.") or ".." in attempt_id:
        raise ValueError("unsafe attempt id")
    if (ROOT / RECEIPT).exists() or (ROOT / DIAGNOSTICS).exists():
        raise ValueError("remediation outputs are immutable and single-use")
    old = read_lock()
    if old and live(old["pid"]):
        raise ValueError(f"remediation walk already running: {old['attempt_id']}")
    if old:
        LOCK.unlink()
    attempt = ATTEMPTS / attempt_id
    if attempt.exists():
        raise ValueError("attempt directory already exists")
    ATTEMPTS.mkdir(parents=True, exist_ok=True)
    attempt.mkdir()
    fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump({"pid": os.getpid(), "attempt_id": attempt_id, "state": "starting"}, stream)
    try:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__)), "worker", "--attempt-id", attempt_id],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        LOCK.write_text(
            json.dumps({"pid": proc.pid, "attempt_id": attempt_id, "state": "running"}) + "\n",
            encoding="utf-8",
        )
    except OSError:
        LOCK.unlink(missing_ok=True)
        raise
    print(json.dumps({"status": "started", "attempt_id": attempt_id, "pid": proc.pid}))


def poll() -> None:
    lock = read_lock()
    if lock and live(lock["pid"]):
        print(json.dumps({"status": "running", **lock}))
        return
    if lock:
        LOCK.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "status": "terminal" if (ROOT / RECEIPT).exists() else "idle",
                "receipt": (ROOT / RECEIPT).exists(),
            }
        )
    )


def cancel() -> None:
    lock = read_lock()
    if not lock:
        print(json.dumps({"status": "idle"}))
        return
    if live(lock["pid"]):
        try:
            os.killpg(lock["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
    LOCK.unlink(missing_ok=True)
    print(json.dumps({"status": "cancelled", "attempt_id": lock["attempt_id"]}))


def check() -> None:
    receipt = ROOT / RECEIPT
    battery = ROOT / BATTERY
    owner = ROOT / OWNER
    for path in (receipt, battery, owner):
        if not path.is_file():
            raise ValueError(f"missing remediation evidence: {path.relative_to(ROOT)}")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/m204_s23_c4_run.py"),
            "--verify-receipt",
            str(receipt),
        ],
        cwd=ROOT,
        check=True,
    )
    b, o = load(battery), load(owner)
    if (
        b["gsd_recovery_liveness"] != "blocked-external"
        or b["disposition"] != "needs-remediation"
        or o["decision"] != "D453"
    ):
        raise ValueError("remediation battery was promoted")
    print("S23_T06_C4_RECEIPT_BOUND_OK")
    print("S23_T06_GSD_BLOCKED_EXTERNAL_OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("compose", "start", "poll", "cancel", "worker", "check")
    )
    parser.add_argument("--attempt-id", default="m204-s23-remediation-full-walk-r1")
    args = parser.parse_args()
    try:
        if args.command == "compose":
            compose()
        elif args.command == "start":
            start(args.attempt_id)
        elif args.command == "poll":
            poll()
        elif args.command == "cancel":
            cancel()
        elif args.command == "worker":
            return worker(args.attempt_id)
        else:
            check()
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
