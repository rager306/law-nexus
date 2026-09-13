#!/usr/bin/env python3
"""Compose and verify the S23 battery, or own a detached C4 full walk.

The long-running walk is intentionally a small state machine: ``start`` returns
immediately, ``poll`` is bounded, and ``cancel`` reaps the owned process group.
The C4 runner remains the source of truth for the immutable receipt predicate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
SCHEMA = "law-nexus/m204-s23-operational-battery/v1"
RECEIPT_REL = "prd/migration/rust-evidence/m204-s23-c4-operational-receipt.json"
DIAGNOSTICS_REL = "prd/migration/rust-evidence/m204-s23-c4-diagnostics.jsonl"
PACKET_REL = "prd/migration/rust-evidence/m204-s23-external-blocker.json"
MANIFEST_REL = "prd/migration/rust-evidence/m204-s23-frozen-hashes.json"
S22 = EVIDENCE / "m204-s22-frozen-hashes.json"
ATTEMPTS = EVIDENCE / "m204-s23-c4-operational-receipt-attempts"
ACTIVE_LOCK = ATTEMPTS / ".active-lock"
BATTERY = EVIDENCE / "m204-s23-operational-battery.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_rel(value: Any) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
        or "\\" in value
        or ".git" in Path(value).parts
        or ".gsd" in Path(value).parts
    ):
        raise ValueError("unsafe battery path")
    path = ROOT / value
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing or symlinked battery path: {value}")
    return path


def compose() -> None:
    if BATTERY.exists():
        raise ValueError("compose refuses to overwrite immutable S23 battery")
    if not (EVIDENCE / "m204-s23-frozen-hashes.json").exists():
        old = load(S22)
        rows = []
        for row in old["files"]:
            path = safe_rel(row["path"])
            rows.append(
                {"path": row["path"], "sha256": digest(path), "size_bytes": path.stat().st_size}
            )
        for value in ("scripts/m204_s23_c4_run.py", "scripts/m204_s23_battery.py", PACKET_REL):
            path = safe_rel(value)
            rows.append({"path": value, "sha256": digest(path), "size_bytes": path.stat().st_size})
        (EVIDENCE / "m204-s23-frozen-hashes.json").write_text(
            json.dumps(
                {
                    "schema": "law-nexus/m204-s23-frozen-hashes/v1",
                    "scope": "S07-S22 predecessor pins plus S23 runner and blocker packet; no self-hash and no corpus walk",
                    "files": rows,
                    "non_claims": [
                        "pins do not establish GSD recovery",
                        "full walk is required for C4 operational acceptance",
                        "this manifest is not a lifecycle validation",
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    manifest = load(EVIDENCE / "m204-s23-frozen-hashes.json")
    for row in manifest["files"]:
        path = safe_rel(row["path"])
        if row.get("sha256") != digest(path) or row.get("size_bytes") != path.stat().st_size:
            raise ValueError(f"existing frozen pin drift: {row.get('path')}")
    BATTERY.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "milestone": "M204-w2ktfw",
                "slice": "S23",
                "c4_operational_acceptance": "not-run",
                "gsd_recovery_liveness": "blocked-external",
                "disposition": "needs-remediation",
                "receipt": RECEIPT_REL,
                "diagnostics": DIAGNOSTICS_REL,
                "frozen_manifest": MANIFEST_REL,
                "blocker_packet": PACKET_REL,
                "classification": "supporting-only",
                "status_effect": "unchanged",
                "non_claims": [
                    "not a GSD recovery pass",
                    "does not call validate",
                    "does not close requirements",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def pid_live(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def read_lock() -> dict[str, Any] | None:
    if not ACTIVE_LOCK.exists():
        return None
    try:
        value = load(ACTIVE_LOCK)
        if (
            not isinstance(value, dict)
            or type(value.get("pid")) is not int
            or not isinstance(value.get("attempt_id"), str)
        ):
            raise ValueError("active lock schema is malformed")
        return value
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"active lock is unreadable: {exc}") from exc


def clear_dead_lock() -> None:
    lock = read_lock()
    if lock and pid_live(lock["pid"]):
        raise ValueError(f"full walk already running: {lock['attempt_id']}")
    if lock:
        ACTIVE_LOCK.unlink()


def worker(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/m204_s23_battery.py"),
        "_run-c4",
        "--attempt-id",
        args.attempt_id,
    ]
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def run_c4(args: argparse.Namespace) -> int:
    build = subprocess.run(
        ["cargo", "build", "--offline", "--bin", "npa-contour-diagnostics"], cwd=ROOT, check=False
    )
    if build.returncode:
        raise ValueError(f"cargo build failed: {build.returncode}")
    source_revision = digest(ROOT / "scripts/m204_s23_c4_run.py")
    cmd = [
        sys.executable,
        str(ROOT / "scripts/m204_s23_c4_run.py"),
        "--source-revision",
        source_revision,
        "--attempt-id",
        args.attempt_id,
        "--out",
        RECEIPT_REL,
        "--diagnostics-out",
        DIAGNOSTICS_REL,
        "--jobs",
        "1",
        "--budget-seconds",
        "3600",
        "--timeout-seconds",
        "10800",
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    # The runner writes a terminal receipt even for nonzero/partial product runs.
    # A nonzero harness result is not allowed to turn that fact into a pass.
    receipt_path = ROOT / RECEIPT_REL
    if not receipt_path.is_file():
        raise ValueError(f"C4 runner produced no terminal receipt (exit {result.returncode})")
    receipt = load(receipt_path)
    battery = load(BATTERY)
    battery.update(
        {
            "c4_operational_acceptance": receipt["claims"]["operational_acceptance"],
            "terminal_outcome": receipt["terminal"],
            "duration_ms": receipt["duration_ms"],
            "source_revision": source_revision,
        }
    )
    BATTERY.write_text(json.dumps(battery, indent=2) + "\n", encoding="utf-8")
    return result.returncode


def start(args: argparse.Namespace) -> None:
    if (
        not args.attempt_id
        or any(x in args.attempt_id for x in (".", "/", "\\"))
        or ".." in args.attempt_id
    ):
        raise ValueError("attempt-id must be a safe non-empty identifier")
    if (ROOT / RECEIPT_REL).exists() or (ROOT / DIAGNOSTICS_REL).exists():
        raise ValueError("full walk is single-use and output destinations are immutable")
    clear_dead_lock()
    attempt = ATTEMPTS / args.attempt_id
    if attempt.exists():
        raise ValueError("attempt directory already exists")
    attempt.mkdir(parents=True)
    # Claim the lock before spawning anything.  A caller that observes this
    # startup record fails closed rather than creating a second worker.
    try:
        lock_fd = os.open(ACTIVE_LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(lock_fd, "w", encoding="utf-8") as lock_stream:
            json.dump(
                {"pid": os.getpid(), "attempt_id": args.attempt_id, "state": "starting"},
                lock_stream,
            )
            lock_stream.write("\n")
    except OSError as exc:
        raise ValueError("active full-walk lock was acquired by another caller") from exc
    try:
        # The C4 runner owns the immutable attempt logs.  The controller itself
        # is detached with stdio closed so it cannot collide with those files.
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__)), "worker", "--attempt-id", args.attempt_id],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )
        ACTIVE_LOCK.write_text(
            json.dumps({"pid": proc.pid, "attempt_id": args.attempt_id, "state": "running"}) + "\n",
            encoding="utf-8",
        )
    except OSError:
        ACTIVE_LOCK.unlink(missing_ok=True)
        raise
    print(
        json.dumps(
            {
                "status": "started",
                "attempt_id": args.attempt_id,
                "pid": proc.pid,
                "attempt_dir": str(attempt.relative_to(ROOT)),
            }
        )
    )


def poll(args: argparse.Namespace) -> None:
    lock = read_lock()
    if not lock:
        receipt = ROOT / RECEIPT_REL
        print(
            json.dumps(
                {"status": "terminal" if receipt.exists() else "idle", "receipt": receipt.exists()}
            )
        )
        return
    if pid_live(lock["pid"]):
        print(json.dumps({"status": "running", **lock}))
        return
    ACTIVE_LOCK.unlink(missing_ok=True)
    receipt = ROOT / RECEIPT_REL
    print(
        json.dumps(
            {"status": "terminal", "attempt_id": lock["attempt_id"], "receipt": receipt.exists()}
        )
    )


def cancel(args: argparse.Namespace) -> None:
    lock = read_lock()
    if not lock:
        print(json.dumps({"status": "idle"}))
        return
    if pid_live(lock["pid"]):
        try:
            os.killpg(lock["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 10
        while pid_live(lock["pid"]) and time.monotonic() < deadline:
            time.sleep(0.2)
        if pid_live(lock["pid"]):
            try:
                os.killpg(lock["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
    ACTIVE_LOCK.unlink(missing_ok=True)
    print(json.dumps({"status": "cancelled", "attempt_id": lock["attempt_id"]}))


def check() -> None:
    manifest = load(EVIDENCE / "m204-s23-frozen-hashes.json")
    if manifest.get("schema") != "law-nexus/m204-s23-frozen-hashes/v1" or not isinstance(
        manifest.get("files"), list
    ):
        raise ValueError("frozen manifest schema mismatch")
    seen = set()
    for row in manifest["files"]:
        if set(row) != {"path", "sha256", "size_bytes"} or row["path"] in seen:
            raise ValueError("frozen manifest is not closed or unique")
        seen.add(row["path"])
        path = safe_rel(row["path"])
        if row["sha256"] != digest(path) or row["size_bytes"] != path.stat().st_size:
            raise ValueError(f"frozen pin drift: {row['path']}")
    receipt = ROOT / RECEIPT_REL
    diagnostics = ROOT / DIAGNOSTICS_REL
    if not receipt.is_file() or not diagnostics.is_file():
        raise ValueError("C4 terminal receipt or diagnostics missing")
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
    packet = load(ROOT / PACKET_REL)
    if (
        packet.get("gsd_recovery_liveness") != "blocked-external"
        or packet.get("disposition") != "needs-remediation"
        or packet.get("classification") != "supporting-only"
        or packet.get("s23_called_validate_milestone") is not False
    ):
        raise ValueError("blocker packet was promoted")
    battery = load(BATTERY)
    actual = load(receipt).get("claims", {}).get("operational_acceptance")
    if battery.get("c4_operational_acceptance") != actual:
        raise ValueError("battery and receipt verdict differ")
    print("S23_T04_VERIFY_OK")
    print(f"S23_T04_C4_{actual.upper()}_OK")
    print("S23_T04_GSD_BLOCKED_EXTERNAL_OK")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "command", choices=("compose", "start", "poll", "cancel", "check", "worker", "_run-c4")
    )
    p.add_argument("--attempt-id", default="m204-s23-c4")
    args = p.parse_args(argv)
    try:
        if args.command == "compose":
            compose()
        elif args.command == "start":
            start(args)
        elif args.command == "poll":
            poll(args)
        elif args.command == "cancel":
            cancel(args)
        elif args.command == "check":
            check()
        elif args.command == "worker":
            worker(args)
        else:
            run_c4(args)
    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
