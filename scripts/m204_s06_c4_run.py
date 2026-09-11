#!/usr/bin/env python3
"""Process-only recorder for a pinned C4 operational attempt.

The Rust diagnostic remains the source of semantic C4 data. This sidecar records
terminal process facts that the JSONL envelope intentionally does not claim.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "m204-s06-c4-operational-receipt/v1"
EXPECTED_CHECK = "c4-live-check"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


def run_text(argv: list[str]) -> tuple[str, int]:
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
    return (p.stdout + p.stderr).strip(), p.returncode


def toolchain() -> dict[str, Any]:
    rustc, r1 = run_text(["rustc", "--version"])
    cargo, r2 = run_text(["cargo", "--version"])
    return {"rustc": rustc, "cargo": cargo, "commands_exit_code": {"rustc": r1, "cargo": r2}}


def count_files(root: Path, suffix: str) -> int:
    return sum(1 for p in root.rglob(f"*{suffix}") if p.is_file())


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_contract(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "schema: npa-acceptance-contract/v1" not in text or "check_id: c4-live-check" not in text:
        raise ValueError("contract missing npa-acceptance-contract/v1 or c4-live-check")
    if "mode: runtime" not in text:
        raise ValueError("c4-live-check is not runtime")
    return {
        "path": display_path(path),
        "sha256": sha256(path),
        "version": "npa-acceptance-contract/v1",
        "check_id": EXPECTED_CHECK,
        "mode": "runtime",
    }


def parser_revision(binary: Path) -> str:
    # The revision is a semantic product binding, not inferred from GSD/git.
    source = ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
    text = source.read_text(encoding="utf-8")
    marker = 'pub const PARSER_REVISION: &str = "'
    start = text.index(marker) + len(marker)
    return text[start : text.index('"', start)]


def build_receipt(
    args: argparse.Namespace,
    argv: list[str],
    started: str,
    finished: str,
    elapsed_ms: int,
    result: dict[str, Any],
    logs: dict[str, Any],
    corpus: dict[str, Any],
    contract: dict[str, Any],
    binary_hash: str,
    tc: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "attempt_id": args.attempt_id,
        "immutable_attempt_identity": {
            "attempt_id": args.attempt_id,
            "argv_sha256": "sha256:"
            + hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest(),
        },
        "argv": argv,
        "binary": {"path": display_path(args.binary), "sha256": binary_hash},
        "build_inputs": {
            "binary_sha256": binary_hash,
            "contract_sha256": contract["sha256"],
            "parser_source_sha256": sha256(
                ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
            ),
        },
        "toolchain": tc,
        "parser_revision": parser_revision(args.binary),
        "source_revision": args.source_revision,
        "contract": contract,
        "corpus": corpus,
        "observed_output": {
            "stdout_sha256": logs["stdout_sha256"],
            "inventory_digest": logs.get("inventory_digest"),
        },
        "c4_binding": {
            "profile": args.profile,
            "limit": args.limit,
            "jobs": args.jobs,
            "inventory_scope": "consultant XML plus separate Garant files",
            "baseline_sha256": args.baseline_sha256,
        },
        "started_at": started,
        "finished_at": finished,
        "duration_ms": elapsed_ms,
        "budget_seconds": args.budget_seconds,
        "terminal": result,
        "logs": logs,
        "claims": {
            "operational_acceptance": "pass"
            if result.get("outcome") == "complete" and elapsed_ms >= args.budget_seconds * 1000
            else "non-pass",
            "receipt_is_runtime_attempt": True,
        },
        "non_claims": [
            "receipt presence is not freshness",
            "source_revision is caller pin, not GSD aggregate",
            "semantic acceptance remains in Rust JSONL",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--binary",
        type=Path,
        required=False,
        default=ROOT / "target/release/npa-contour-diagnostics",
    )
    ap.add_argument("--root", type=Path, default=ROOT / "consru_export/consru_export/exports")
    ap.add_argument("--garant-root", type=Path, default=ROOT / "law-source/garant")
    ap.add_argument(
        "--contract", type=Path, default=ROOT / "prd/architecture/npa-acceptance-contract.yaml"
    )
    ap.add_argument("--out", type=Path)
    ap.add_argument(
        "--source-revision", required=False, default="m204-s06-c4-caller-pin-2026-09-11"
    )
    ap.add_argument("--attempt-id", default="m204-s06-c4-attempt-001")
    ap.add_argument("--profile", default="contour")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--budget-seconds", type=int, default=3600)
    ap.add_argument("--timeout-seconds", type=int, default=3600)
    ap.add_argument("--baseline-sha256", default=None)
    ap.add_argument("--verify-receipt", type=Path)
    ap.add_argument(
        "--no-run", action="store_true", help="only for tests; records no fake terminal success"
    )
    args = ap.parse_args()
    if args.verify_receipt:
        return verify(args.verify_receipt)
    args.binary = args.binary.resolve()
    args.root = args.root.resolve()
    args.garant_root = args.garant_root.resolve()
    args.contract = args.contract.resolve()
    if not args.binary.is_file():
        print("binary missing", file=sys.stderr)
        return 2
    if not args.root.is_dir():
        print("corpus root missing", file=sys.stderr)
        return 2
    contract = parse_contract(args.contract)
    corpus = {
        "consultant_xml_count": count_files(args.root, ".xml"),
        "consultant_root": display_path(args.root),
        "garant_file_count": sum(1 for p in args.garant_root.rglob("*") if p.is_file())
        if args.garant_root.is_dir()
        else 0,
        "garant_root": display_path(args.garant_root),
    }
    argv = [
        str(args.binary),
        "--root",
        str(args.root),
        "--garant-root",
        str(args.garant_root),
        "--profile",
        args.profile,
        "--jobs",
        str(args.jobs),
        "--acceptance-contract",
        str(args.contract),
        "--source-revision",
        args.source_revision,
    ]
    if args.limit is not None:
        argv += ["--limit", str(args.limit)]
    log_dir = (
        (args.out.parent if args.out else ROOT / "prd/migration/rust-evidence")
        / "m204-s06-c4-attempts"
        / args.attempt_id
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    mono = time.monotonic()
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    if args.no_run:
        result = {"outcome": "not-run", "exit_code": None, "signal": None, "timeout": False}
    else:
        with (
            stdout_path.open("w", encoding="utf-8") as out,
            stderr_path.open("w", encoding="utf-8") as err,
        ):
            try:
                proc = subprocess.Popen(
                    argv, cwd=ROOT, stdout=out, stderr=err, start_new_session=True
                )
                try:
                    code = proc.wait(timeout=args.timeout_seconds)
                    result = {
                        "outcome": "complete" if code == 0 else "nonzero",
                        "exit_code": code,
                        "signal": None,
                        "timeout": False,
                    }
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait()
                    result = {
                        "outcome": "timeout",
                        "exit_code": None,
                        "signal": "SIGTERM",
                        "timeout": True,
                    }
            except OSError as exc:
                result = {
                    "outcome": "launch_error",
                    "exit_code": None,
                    "signal": None,
                    "timeout": False,
                    "error": str(exc),
                }
    finished = utc_now()
    elapsed_ms = int((time.monotonic() - mono) * 1000)
    stdout_text = (
        stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    )
    inventory_digest = None
    for line in stdout_text.splitlines():
        if '"inventory_digest"' in line:
            try:
                inventory_digest = json.loads(line).get("inventory_digest")
            except json.JSONDecodeError:
                pass
    logs = {
        "stdout": display_path(stdout_path),
        "stderr": display_path(stderr_path),
        "stdout_sha256": sha256(stdout_path) if stdout_path.exists() else None,
        "stderr_sha256": sha256(stderr_path) if stderr_path.exists() else None,
        "inventory_digest": inventory_digest,
    }
    receipt = build_receipt(
        args,
        argv,
        started,
        finished,
        elapsed_ms,
        result,
        logs,
        corpus,
        contract,
        sha256(args.binary),
        toolchain(),
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "outcome": result["outcome"],
                "duration_ms": elapsed_ms,
                "output": str(args.out) if args.out else None,
            }
        )
    )
    return (
        0
        if result["outcome"] in {"complete", "nonzero", "timeout", "launch_error", "not-run"}
        else 3
    )


def verify(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == SCHEMA
    assert data["contract"]["check_id"] == EXPECTED_CHECK and data["contract"]["mode"] == "runtime"
    assert data["source_revision"] and not data["source_revision"].startswith("sha256:")
    assert (
        isinstance(data["argv"], list)
        and data["argv"]
        and all(isinstance(x, str) for x in data["argv"])
    )
    assert data["budget_seconds"] >= 3600 and data["duration_ms"] >= 0
    assert data["terminal"]["outcome"] in {
        "complete",
        "nonzero",
        "timeout",
        "launch_error",
        "not-run",
    }
    if data["terminal"]["outcome"] == "complete":
        assert data["terminal"]["exit_code"] == 0
    if data["terminal"]["outcome"] == "timeout":
        assert data["terminal"]["timeout"] is True
    assert data["corpus"]["consultant_xml_count"] >= 0
    assert data["build_inputs"]["binary_sha256"] == data["binary"]["sha256"]
    assert data["build_inputs"]["contract_sha256"] == data["contract"]["sha256"]
    for key in ("stdout_sha256", "stderr_sha256"):
        assert data["logs"][key] is None or data["logs"][key].startswith("sha256:")
    print("M204_S06_C4_RECEIPT_VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
