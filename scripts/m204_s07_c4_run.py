#!/usr/bin/env python3
"""Immutable, process-only C4 recorder for the M204 S07 operational attempt.

This adapter owns process facts and receipt integrity; the Rust binary owns the
JSONL diagnostic semantics.  ``--out`` is the receipt path and
``--diagnostics-out`` is passed to the binary as its atomic JSONL output path.
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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "m204-s07-c4-operational-receipt/v1"
EXPECTED_CHECK = "c4-live-check"
EXPECTED_XML = 43_785
DURATION_FLOOR_MS = 3_600_000


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def count_files(root: Path, suffix: str) -> int:
    return sum(1 for item in root.rglob(f"*{suffix}") if item.is_file())


def parse_contract(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "schema: npa-acceptance-contract/v1" not in text:
        raise ValueError("acceptance contract schema mismatch")
    if "check_id: c4-live-check" not in text or "mode: runtime" not in text:
        raise ValueError("c4-live-check runtime contract missing")
    return {
        "path": display(path),
        "sha256": sha256(path),
        "version": "npa-acceptance-contract/v1",
        "check_id": EXPECTED_CHECK,
        "mode": "runtime",
    }


def parser_revision() -> str:
    source = ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
    text = source.read_text(encoding="utf-8")
    marker = 'pub const PARSER_REVISION: &str = "'
    start = text.index(marker) + len(marker)
    return text[start : text.index('"', start)]


def toolchain() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name in ("rustc", "cargo"):
        try:
            proc = subprocess.run([name, "--version"], capture_output=True, text=True, check=False)
            values[name] = proc.stdout.strip() or proc.stderr.strip()
            values.setdefault("commands_exit_code", {})[name] = proc.returncode
        except OSError as exc:
            values[name] = str(exc)
            values.setdefault("commands_exit_code", {})[name] = 127
    return values


def inventory_from_jsonl(path: Path) -> tuple[str | None, bool, int]:
    if not path.is_file() or not path.stat().st_size:
        return None, False, 0
    digest: str | None = None
    valid = True
    lines = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        lines += 1
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            valid = False
            continue
        if not isinstance(value, dict):
            valid = False
        elif value.get("inventory_digest") and digest is None:
            digest = value["inventory_digest"]
    return digest, valid and lines > 0, lines


def run(args: argparse.Namespace) -> int:
    for output in (args.out, args.diagnostics_out):
        if output is not None and output.exists():
            raise ValueError(f"immutable output already exists: {output}")
    args.binary = args.binary.resolve()
    args.root = args.root.resolve()
    args.garant_root = args.garant_root.resolve()
    args.contract = args.contract.resolve()
    if not args.binary.is_file() or not args.root.is_dir():
        raise ValueError("binary or consultant corpus root missing")
    contract = parse_contract(args.contract)
    if args.diagnostics_out is None:
        raise ValueError("--diagnostics-out is required for S07 receipt integrity")
    args.diagnostics_out = args.diagnostics_out.resolve()
    args.out = args.out.resolve() if args.out else None
    if args.out is not None and args.out == args.diagnostics_out:
        raise ValueError("receipt and diagnostics output paths must differ")
    args.diagnostics_out.parent.mkdir(parents=True, exist_ok=True)
    log_dir = (
        (args.out.parent if args.out else ROOT / "prd/migration/rust-evidence")
        / "m204-s07-c4-attempts"
        / args.attempt_id
    )
    if log_dir.exists() and any(log_dir.iterdir()):
        raise ValueError(f"immutable attempt collision: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path, stderr_path = log_dir / "stdout.log", log_dir / "stderr.log"
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
        "--out",
        str(args.diagnostics_out),
    ]
    if args.limit is not None:
        argv += ["--limit", str(args.limit)]
    started, monotonic = utc_now(), time.monotonic()
    with (
        stdout_path.open("x", encoding="utf-8") as out,
        stderr_path.open("x", encoding="utf-8") as err,
    ):
        try:
            proc = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=err, start_new_session=True)
            try:
                code = proc.wait(timeout=args.timeout_seconds)
                terminal = {
                    "outcome": "complete" if code == 0 else "nonzero",
                    "exit_code": code,
                    "signal": None,
                    "timeout": False,
                }
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait()
                terminal = {
                    "outcome": "timeout",
                    "exit_code": None,
                    "signal": "SIGTERM",
                    "timeout": True,
                }
        except OSError as exc:
            terminal = {
                "outcome": "launch_error",
                "exit_code": None,
                "signal": None,
                "timeout": False,
                "error": str(exc),
            }
    duration_ms = int((time.monotonic() - monotonic) * 1000)
    inventory_digest, jsonl_valid, jsonl_lines = inventory_from_jsonl(args.diagnostics_out)
    receipt = {
        "schema": SCHEMA,
        "attempt_id": args.attempt_id,
        "immutable_attempt_identity": {
            "attempt_id": args.attempt_id,
            "argv_sha256": "sha256:"
            + hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest(),
        },
        "argv": argv,
        "binary": {"path": display(args.binary), "sha256": sha256(args.binary)},
        "build_inputs": {
            "binary_sha256": sha256(args.binary),
            "contract_sha256": contract["sha256"],
            "parser_source_sha256": sha256(
                ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
            ),
        },
        "toolchain": toolchain(),
        "parser_revision": parser_revision(),
        "source_revision": args.source_revision,
        "contract": contract,
        "corpus": {
            "consultant_xml_count": count_files(args.root, ".xml"),
            "consultant_root": display(args.root),
            "garant_file_count": sum(1 for item in args.garant_root.rglob("*") if item.is_file())
            if args.garant_root.is_dir()
            else 0,
            "garant_root": display(args.garant_root),
        },
        "c4_binding": {
            "profile": args.profile,
            "limit": args.limit,
            "jobs": args.jobs,
            "inventory_scope": "consultant XML plus separate Garant files",
            "source_revision": args.source_revision,
        },
        "started_at": started,
        "finished_at": utc_now(),
        "duration_ms": duration_ms,
        "budget_seconds": args.budget_seconds,
        "terminal": terminal,
        "observed_output": {
            "diagnostics": display(args.diagnostics_out),
            "inventory_digest": inventory_digest,
            "jsonl_valid": jsonl_valid,
            "jsonl_lines": jsonl_lines,
        },
        "logs": {
            "stdout": display(stdout_path),
            "stderr": display(stderr_path),
            "stdout_sha256": sha256(stdout_path),
            "stderr_sha256": sha256(stderr_path),
            "diagnostics_sha256": sha256(args.diagnostics_out)
            if args.diagnostics_out.exists()
            else None,
        },
        "claims": {
            "operational_acceptance": "pass"
            if is_operational_pass_data(
                {
                    "terminal": terminal,
                    "duration_ms": duration_ms,
                    "budget_seconds": args.budget_seconds,
                    "corpus": {"consultant_xml_count": count_files(args.root, ".xml")},
                    "c4_binding": {"limit": args.limit, "jobs": args.jobs},
                    "observed_output": {
                        "inventory_digest": inventory_digest,
                        "jsonl_valid": jsonl_valid,
                    },
                }
            )
            else "non-pass",
            "duration_floor_ms": DURATION_FLOOR_MS,
        },
        "non_claims": [
            "receipt presence is not runtime freshness",
            "source_revision is caller pin, not GSD aggregate",
            "semantic acceptance remains in Rust JSONL",
        ],
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "outcome": terminal["outcome"],
                "duration_ms": duration_ms,
                "output": str(args.out) if args.out else None,
            }
        )
    )
    return 0


def is_operational_pass_data(data: dict[str, Any]) -> bool:
    terminal, corpus, binding, output = (
        data["terminal"],
        data["corpus"],
        data["c4_binding"],
        data["observed_output"],
    )
    return (
        terminal.get("outcome") == "complete"
        and terminal.get("exit_code") == 0
        and data["duration_ms"] >= DURATION_FLOOR_MS
        and binding.get("limit") is None
        and binding.get("jobs") == 0
        and corpus.get("consultant_xml_count") == EXPECTED_XML
        and bool(output.get("inventory_digest"))
        and output.get("jsonl_valid") is True
    )


def _load_receipt(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("receipt must be a JSON object")
    return value


def verify(path: Path, require_operational_pass: bool) -> int:
    """Verify a newly produced receipt against the current live parser epoch."""
    data = _load_receipt(path)
    if data.get("schema") != SCHEMA:
        raise ValueError("receipt schema mismatch")
    if (
        not data.get("attempt_id")
        or data["immutable_attempt_identity"].get("attempt_id") != data["attempt_id"]
    ):
        raise ValueError("attempt identity mismatch")
    if (
        data.get("contract", {}).get("check_id") != EXPECTED_CHECK
        or data["contract"].get("mode") != "runtime"
    ):
        raise ValueError("runtime contract binding missing")
    if data.get("budget_seconds", 0) < 3600 or data.get("duration_ms", -1) < 0:
        raise ValueError("timeout budget or duration floor metadata invalid")
    if not isinstance(data.get("argv"), list) or "--out" not in data["argv"]:
        raise ValueError("binary argv must include atomic --out")
    if data.get("c4_binding", {}).get("limit") is not None:
        raise ValueError("operational receipt must have no limit")
    if data.get("c4_binding", {}).get("source_revision") != data.get("source_revision"):
        raise ValueError("source revision binding mismatch")
    terminal = data.get("terminal", {})
    if terminal.get("outcome") == "complete" and terminal.get("exit_code") != 0:
        raise ValueError("complete receipt has nonzero exit")
    if terminal.get("outcome") == "timeout" and not terminal.get("timeout"):
        raise ValueError("timeout receipt missing timeout marker")
    if data.get("build_inputs", {}).get("binary_sha256") != data.get("binary", {}).get("sha256"):
        raise ValueError("binary hash binding mismatch")
    if data.get("build_inputs", {}).get("contract_sha256") != data.get("contract", {}).get(
        "sha256"
    ):
        raise ValueError("contract hash binding mismatch")
    if data.get("build_inputs", {}).get("parser_source_sha256") != sha256(
        ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
    ):
        raise ValueError("parser source hash binding mismatch")
    diagnostics = ROOT / data.get("observed_output", {}).get("diagnostics", "")
    if not diagnostics.is_file() or data.get("logs", {}).get("diagnostics_sha256") != sha256(
        diagnostics
    ):
        raise ValueError("diagnostics output hash binding mismatch")
    digest, jsonl_valid, jsonl_lines = inventory_from_jsonl(diagnostics)
    observed = data.get("observed_output", {})
    if (
        digest != observed.get("inventory_digest")
        or jsonl_valid != observed.get("jsonl_valid")
        or jsonl_lines != observed.get("jsonl_lines")
    ):
        raise ValueError("diagnostics inventory binding mismatch")
    actual = is_operational_pass_data(data)
    if data.get("claims", {}).get("operational_acceptance") != ("pass" if actual else "non-pass"):
        raise ValueError("operational claim does not match observed facts")
    if require_operational_pass and not actual:
        raise ValueError("operational acceptance is not proven")
    print(
        json.dumps({"status": "pass", "operational_acceptance": "pass" if actual else "non-pass"})
    )
    return 0


def verify_historical(
    path: Path,
    binding_path: Path,
    pinned_path: Path,
    require_operational_pass: bool = False,
) -> int:
    """Replay historical receipt bytes through the validated T01 binding only."""
    import m204_s13_source_binding as binding

    repo = ROOT.resolve()
    binding_value = _load_receipt(binding_path)
    binding.validate(binding_value, repo)
    supplied = _load_receipt(path)
    pinned = _load_receipt(pinned_path)
    if supplied != pinned:
        raise ValueError("historical receipt differs from pinned receipt content")
    relative = pinned_path.resolve().relative_to(repo).as_posix()
    expected = binding.PINNED.get(relative)
    if expected is None or sha256(pinned_path.resolve()) != expected:
        raise ValueError("historical receipt is not a pinned tracked artifact")
    current_source = sha256(repo / "crates/ln-consultant-parser/src/contour_diagnostics.rs")
    if binding_value["current"]["parser_source_sha256"] != current_source:
        raise ValueError("historical binding current parser digest is stale")
    if pinned.get("parser_revision") != binding.PARSER_REVISION:
        raise ValueError("historical receipt parser revision mismatch")
    if pinned.get("build_inputs", {}).get("parser_source_sha256") != binding.HISTORICAL_SOURCE:
        raise ValueError("historical receipt parser digest mismatch")
    if binding_value["parser_revision"] != parser_revision():
        raise ValueError("historical binding revision does not match live parser")
    diagnostics_value = pinned.get("observed_output", {}).get("diagnostics")
    diagnostics = (repo / diagnostics_value).resolve() if diagnostics_value else None
    if diagnostics is None or diagnostics.relative_to(repo).as_posix() not in binding.PINNED:
        raise ValueError("historical diagnostics is not a pinned tracked artifact")
    if sha256(diagnostics) != binding.PINNED[diagnostics.relative_to(repo).as_posix()]:
        raise ValueError("historical diagnostics pin mismatch")
    digest, valid, lines = inventory_from_jsonl(diagnostics)
    observed = pinned["observed_output"]
    if (digest, valid, lines) != (
        observed.get("inventory_digest"),
        observed.get("jsonl_valid"),
        observed.get("jsonl_lines"),
    ):
        raise ValueError("historical diagnostics inventory mismatch")
    _verify_receipt_facts(pinned, require_operational_pass)
    print(json.dumps({"status": "pass", "historical": True}))
    return 0


def _verify_receipt_facts(data: dict[str, Any], require_operational_pass: bool) -> None:
    """Validate facts after epoch and pinned-content checks have succeeded."""
    if data.get("schema") != SCHEMA:
        raise ValueError("receipt schema mismatch")
    if data.get("c4_binding", {}).get("limit") is not None:
        raise ValueError("operational receipt must have no limit")
    if data.get("c4_binding", {}).get("jobs") != 0:
        raise ValueError("operational receipt must have zero jobs")
    actual = is_operational_pass_data(data)
    if data.get("claims", {}).get("operational_acceptance") != ("pass" if actual else "non-pass"):
        raise ValueError("operational claim does not match observed facts")
    if require_operational_pass and not actual:
        raise ValueError("operational acceptance is not proven")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--binary", type=Path, default=ROOT / "target/release/npa-contour-diagnostics"
    )
    parser.add_argument("--root", type=Path, default=ROOT / "consru_export/consru_export/exports")
    parser.add_argument("--garant-root", type=Path, default=ROOT / "law-source/garant")
    parser.add_argument(
        "--contract", type=Path, default=ROOT / "prd/architecture/npa-acceptance-contract.yaml"
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--diagnostics-out", type=Path)
    # Receipt replay is intentionally independent of launch-time identity.  Keep
    # these fields mandatory for a new process attempt, but do not make an
    # artifact verifier supply values it will never use.
    parser.add_argument("--source-revision")
    parser.add_argument("--attempt-id")
    parser.add_argument("--profile", default="contour")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--jobs", type=int, default=0)
    parser.add_argument("--budget-seconds", type=int, default=3600)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    parser.add_argument("--verify-receipt", type=Path)
    parser.add_argument("--verify-historical", type=Path)
    parser.add_argument(
        "--binding",
        type=Path,
        default=ROOT / "prd/migration/rust-evidence/m204-s13-s07-source-binding.json",
    )
    parser.add_argument("--pinned-receipt", type=Path)
    parser.add_argument("--require-operational-pass", action="store_true")
    args = parser.parse_args(argv)
    if args.verify_receipt and args.verify_historical:
        parser.error("receipt replay modes are mutually exclusive")
    if args.verify_historical and not args.pinned_receipt:
        parser.error("--pinned-receipt is required for historical replay")
    if (
        not args.verify_receipt
        and not args.verify_historical
        and (not args.source_revision or not args.attempt_id)
    ):
        parser.error("--source-revision and --attempt-id are required for a new attempt")
    try:
        if args.verify_historical:
            return verify_historical(
                args.verify_historical,
                args.binding,
                args.pinned_receipt,
                args.require_operational_pass,
            )
        return (
            verify(args.verify_receipt, args.require_operational_pass)
            if args.verify_receipt
            else run(args)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
