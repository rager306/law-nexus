#!/usr/bin/env python3
"""Immutable M204 S10 C4 operational recorder and receipt verifier.

This is deliberately a new schema and predicate.  It records an owned
subprocess attempt; the Rust binary remains the owner of diagnostic semantics.
The receipt is non-pass unless every observed fact satisfies the S10 predicate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "m204-s10-c4-operational-receipt/v1"
EXPECTED_CHECK = "c4-live-check"
EXPECTED_XML = 43_785
DURATION_FLOOR_MS = 3_600_000
_ATTEMPT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def canonical(path: Path, *, label: str) -> Path:
    """Resolve tracked-relative paths under ROOT; reject traversal explicitly."""
    if ".." in path.parts:
        raise ValueError(f"{label} contains traversal")
    candidate = path if path.is_absolute() else ROOT / path
    return candidate.resolve(strict=False)


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
    values: dict[str, Any] = {"commands_exit_code": {}}
    for name in ("rustc", "cargo"):
        try:
            proc = subprocess.run([name, "--version"], capture_output=True, text=True, check=False)
            values[name] = proc.stdout.strip() or proc.stderr.strip()
            values["commands_exit_code"][name] = proc.returncode
        except OSError as exc:
            values[name] = str(exc)
            values["commands_exit_code"][name] = 127
    return values


def inventory_from_jsonl(path: Path) -> tuple[str | None, bool, int]:
    if not path.is_file() or not path.stat().st_size:
        return None, False, 0
    digest: str | None = None
    valid = True
    lines = 0
    try:
        stream = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return None, False, 0
    with stream:
        for raw in stream:
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
            elif value.get("inventory_digest") is not None:
                candidate = value["inventory_digest"]
                if not isinstance(candidate, str) or digest is not None:
                    valid = False if digest is not None else valid
                else:
                    digest = candidate
    return digest, valid and lines > 0, lines


def argv_hash(argv: list[str]) -> str:
    return (
        "sha256:"
        + hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode("utf-8")).hexdigest()
    )


def terminate_group(proc: subprocess.Popen[str]) -> tuple[str, int | None]:
    """Terminate an owned process group, then reap it within a bounded grace."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return "SIGTERM", proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            return "SIGKILL", proc.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("owned process group did not reap after SIGKILL") from exc


def is_operational_pass_data(data: dict[str, Any]) -> bool:
    terminal = data.get("terminal", {})
    corpus = data.get("corpus", {})
    binding = data.get("c4_binding", {})
    output = data.get("observed_output", {})
    return (
        terminal.get("outcome") == "complete"
        and terminal.get("exit_code") == 0
        and terminal.get("timeout") is False
        and data.get("duration_ms", -1) >= DURATION_FLOOR_MS
        and binding.get("limit") is None
        and corpus.get("consultant_xml_count") == EXPECTED_XML
        and bool(output.get("inventory_digest"))
        and output.get("jsonl_valid") is True
    )


def run(args: argparse.Namespace) -> int:
    if not args.attempt_id or not _ATTEMPT.fullmatch(args.attempt_id):
        raise ValueError("attempt-id must be a safe non-empty identifier")
    if args.jobs < 0 or args.limit is not None and args.limit < 0:
        raise ValueError("jobs and limit must be non-negative")
    if args.timeout_seconds <= 0 or args.budget_seconds <= 0:
        raise ValueError("timeout and budget must be positive")
    binary = canonical(args.binary, label="binary")
    corpus = canonical(args.root, label="root")
    garant = canonical(args.garant_root, label="garant-root")
    contract_path = canonical(args.contract, label="contract")
    out = canonical(args.out, label="out") if args.out else None
    if args.diagnostics_out is None:
        raise ValueError("--diagnostics-out is required for S10 receipt integrity")
    diagnostics = canonical(args.diagnostics_out, label="diagnostics-out")
    for output in (out, diagnostics):
        if output is None:
            continue
        if output.exists():
            raise ValueError(f"immutable output already exists: {output}")
    if out is not None and out == diagnostics:
        raise ValueError("receipt and diagnostics output paths must differ")
    if (
        not binary.is_file()
        or not corpus.is_dir()
        or not garant.is_dir()
        or not contract_path.is_file()
    ):
        raise ValueError("binary, roots, or acceptance contract missing")
    contract = parse_contract(contract_path)
    log_dir = (
        (out.parent if out else ROOT / "prd/migration/rust-evidence")
        / "m204-s10-c4-attempts"
        / args.attempt_id
    )
    if log_dir.exists() and any(log_dir.iterdir()):
        raise ValueError(f"immutable attempt collision: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    diagnostics.parent.mkdir(parents=True, exist_ok=True)
    stdout_path, stderr_path = log_dir / "stdout.log", log_dir / "stderr.log"
    if stdout_path.exists() or stderr_path.exists():
        raise ValueError("immutable attempt log collision")
    argv = [
        str(binary),
        "--root",
        str(corpus),
        "--garant-root",
        str(garant),
        "--profile",
        args.profile,
        "--jobs",
        str(args.jobs),
        "--acceptance-contract",
        str(contract_path),
        "--source-revision",
        args.source_revision,
        "--out",
        str(diagnostics),
    ]
    if args.limit is not None:
        argv += ["--limit", str(args.limit)]
    started = utc_now()
    monotonic = time.monotonic()
    terminal: dict[str, Any]
    with (
        stdout_path.open("x", encoding="utf-8") as stdout,
        stderr_path.open("x", encoding="utf-8") as stderr,
    ):
        try:
            proc = subprocess.Popen(
                argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True, text=True
            )
        except OSError as exc:
            terminal = {
                "outcome": "launch_error",
                "exit_code": None,
                "signal": None,
                "timeout": False,
                "error": str(exc),
            }
        else:
            try:
                code = proc.wait(timeout=args.timeout_seconds)
                terminal = {
                    "outcome": "complete" if code == 0 else "nonzero",
                    "exit_code": code,
                    "signal": None,
                    "timeout": False,
                }
            except subprocess.TimeoutExpired:
                sig, code = terminate_group(proc)
                terminal = {"outcome": "timeout", "exit_code": code, "signal": sig, "timeout": True}
    duration_ms = int((time.monotonic() - monotonic) * 1000)
    inventory_digest, jsonl_valid, jsonl_lines = inventory_from_jsonl(diagnostics)
    corpus_count = count_files(corpus, ".xml")
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "attempt_id": args.attempt_id,
        "immutable_attempt_identity": {
            "attempt_id": args.attempt_id,
            "argv_sha256": argv_hash(argv),
        },
        "argv": argv,
        "binary": {"path": display(binary), "sha256": sha256(binary)},
        "binary_profile": args.binary_profile,
        "build_inputs": {
            "binary_sha256": sha256(binary),
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
            "consultant_xml_count": corpus_count,
            "consultant_root": display(corpus),
            "garant_file_count": sum(1 for item in garant.rglob("*") if item.is_file()),
            "garant_root": display(garant),
        },
        "c4_binding": {
            "profile": args.profile,
            "limit": args.limit,
            "jobs": args.jobs,
            "binary_profile": args.binary_profile,
            "inventory_scope": "consultant XML plus separate Garant files",
            "source_revision": args.source_revision,
        },
        "started_at": started,
        "finished_at": utc_now(),
        "duration_ms": duration_ms,
        "budget_seconds": args.budget_seconds,
        "terminal": terminal,
        "observed_output": {
            "diagnostics": display(diagnostics),
            "inventory_digest": inventory_digest,
            "jsonl_valid": jsonl_valid,
            "jsonl_lines": jsonl_lines,
        },
        "logs": {
            "stdout": display(stdout_path),
            "stderr": display(stderr_path),
            "stdout_sha256": sha256(stdout_path),
            "stderr_sha256": sha256(stderr_path),
            "diagnostics_sha256": sha256(diagnostics) if diagnostics.is_file() else None,
        },
        "claims": {
            "operational_acceptance": "pass"
            if is_operational_pass_data(
                {
                    "terminal": terminal,
                    "duration_ms": duration_ms,
                    "corpus": {"consultant_xml_count": corpus_count},
                    "c4_binding": {"limit": args.limit},
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
    if args.binary_profile == "debug":
        receipt["non_claims"].append("debug timing is not a release performance claim")
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "outcome": terminal["outcome"],
                "duration_ms": duration_ms,
                "output": str(out) if out else None,
            }
        )
    )
    return 0


def verify(
    path: Path, require_operational_pass: bool, historical_binding: Path | None = None
) -> int:
    receipt_path = canonical(path, label="receipt")
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    replay: dict[str, Any] | None = None
    if historical_binding is not None:
        from m204_s14_source_binding import validate_for_replay

        replay = validate_for_replay(
            ROOT, canonical(historical_binding, label="historical binding"), receipt_path
        )
    if data.get("schema") != SCHEMA:
        raise ValueError("receipt schema mismatch")
    attempt = data.get("attempt_id", "")
    if not isinstance(attempt, str) or not _ATTEMPT.fullmatch(attempt):
        raise ValueError("unsafe attempt identity")
    identity = data.get("immutable_attempt_identity", {})
    if identity.get("attempt_id") != attempt or not str(identity.get("argv_sha256", "")).startswith(
        "sha256:"
    ):
        raise ValueError("attempt identity mismatch")
    if data.get("source_revision") != data.get("c4_binding", {}).get("source_revision"):
        raise ValueError("source revision binding mismatch")
    if data.get("binary_profile") not in ("release", "debug") or data.get("c4_binding", {}).get(
        "binary_profile"
    ) != data.get("binary_profile"):
        raise ValueError("binary profile binding mismatch")
    if data.get("budget_seconds", 0) < 3600 or data.get("duration_ms", -1) < 0:
        raise ValueError("budget or duration metadata invalid")
    terminal = data.get("terminal", {})
    if terminal.get("outcome") == "complete" and terminal.get("exit_code") != 0:
        raise ValueError("complete receipt has nonzero exit")
    if terminal.get("outcome") == "timeout" and not terminal.get("timeout"):
        raise ValueError("timeout receipt missing timeout marker")
    argv = data.get("argv")
    binding = data.get("c4_binding", {})
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) for item in argv):
        raise ValueError("argv must be a string list")
    if data.get("binary", {}).get("path") != display(Path(argv[0])):
        raise ValueError("argv binary binding mismatch")
    if "--out" not in argv or display(Path(argv[argv.index("--out") + 1])) != data.get(
        "observed_output", {}
    ).get("diagnostics"):
        raise ValueError("argv diagnostics binding mismatch")

    def argv_value(flag: str) -> str | None:
        if flag not in argv:
            return None
        index = argv.index(flag) + 1
        if index >= len(argv):
            raise ValueError(f"argv missing value for {flag}")
        return argv[index]

    if argv_value("--jobs") != str(binding.get("jobs")) or argv_value("--profile") != binding.get(
        "profile"
    ):
        raise ValueError("argv execution binding mismatch")
    argv_limit = argv_value("--limit")
    if (
        (argv_limit is None) != (binding.get("limit") is None)
        or argv_limit is not None
        and int(argv_limit) != binding.get("limit")
    ):
        raise ValueError("argv limit binding mismatch")
    if identity.get("argv_sha256") != argv_hash(argv):
        raise ValueError("argv hash binding mismatch")

    def receipt_path(value: str, *, label: str) -> Path:
        candidate = Path(value)
        return canonical(candidate if candidate.is_absolute() else ROOT / candidate, label=label)

    binary = receipt_path(data["binary"]["path"], label="binary receipt path")
    contract = receipt_path(data["contract"]["path"], label="contract receipt path")
    parser = ROOT / "crates/ln-consultant-parser/src/contour_diagnostics.rs"
    if not contract.is_file():
        raise ValueError("receipt contract missing")
    if replay is None:
        if not binary.is_file():
            raise ValueError("receipt binary missing")
        if data["build_inputs"].get("binary_sha256") != data["binary"].get("sha256") or data[
            "binary"
        ]["sha256"] != sha256(binary):
            raise ValueError("binary hash binding mismatch")
        if data["build_inputs"].get("parser_source_sha256") != sha256(parser):
            raise ValueError("parser source hash binding mismatch")
    else:
        if data["binary"].get("sha256") != replay["historical_binary_sha256"]:
            raise ValueError("historical attested binary hash mismatch")
        if data["build_inputs"].get("binary_sha256") != replay["historical_binary_sha256"]:
            raise ValueError("historical build binary hash mismatch")
        if (
            data["build_inputs"].get("parser_source_sha256")
            != replay["historical_parser_source_sha256"]
        ):
            raise ValueError("historical parser hash mismatch")
        if sha256(parser) != replay["current_parser_source_sha256"]:
            raise ValueError("current parser hash mismatch")
        if data.get("parser_revision") != replay["parser_revision"]:
            raise ValueError("historical parser revision mismatch")
    if data["build_inputs"].get("contract_sha256") != data["contract"].get("sha256") or data[
        "contract"
    ]["sha256"] != sha256(contract):
        raise ValueError("contract hash binding mismatch")
    diagnostics = receipt_path(
        data.get("observed_output", {}).get("diagnostics", ""), label="diagnostics receipt path"
    )
    observed = data.get("observed_output", {})
    if diagnostics.is_file():
        if data.get("logs", {}).get("diagnostics_sha256") != sha256(diagnostics):
            raise ValueError("diagnostics output hash binding mismatch")
        digest, valid, lines = inventory_from_jsonl(diagnostics)
        if (digest, valid, lines) != (
            observed.get("inventory_digest"),
            observed.get("jsonl_valid"),
            observed.get("jsonl_lines"),
        ):
            raise ValueError("diagnostics inventory binding mismatch")
    elif terminal.get("outcome") == "complete" and terminal.get("exit_code") == 0:
        raise ValueError("successful receipt is missing diagnostics output")
    elif data.get("logs", {}).get("diagnostics_sha256") is not None:
        raise ValueError("missing diagnostics has a hash binding")
    for log_key in ("stdout", "stderr"):
        log_path = receipt_path(data.get("logs", {}).get(log_key, ""), label=f"{log_key} log path")
        if not log_path.is_file() or data.get("logs", {}).get(f"{log_key}_sha256") != sha256(
            log_path
        ):
            raise ValueError(f"{log_key} log hash binding mismatch")
    if data.get(
        "binary_profile"
    ) == "debug" and "debug timing is not a release performance claim" not in data.get(
        "non_claims", []
    ):
        raise ValueError("debug receipt is missing non-performance claim")
    actual = is_operational_pass_data(data)
    expected_claim = "pass" if actual else "non-pass"
    if data.get("claims", {}).get("operational_acceptance") != expected_claim:
        raise ValueError("operational claim does not match observed facts")
    if require_operational_pass and not actual:
        raise ValueError("operational acceptance is not proven")
    print(json.dumps({"status": "pass", "operational_acceptance": expected_claim}))
    return 0


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
    parser.add_argument("--source-revision")
    parser.add_argument("--attempt-id")
    parser.add_argument("--profile", default="contour")
    parser.add_argument("--binary-profile", choices=("release", "debug"), default="release")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--jobs", type=int, default=0)
    parser.add_argument("--budget-seconds", type=int, default=3600)
    parser.add_argument("--timeout-seconds", type=int, default=10800)
    parser.add_argument("--verify-receipt", type=Path)
    parser.add_argument("--historical-binding", type=Path)
    parser.add_argument("--require-operational-pass", action="store_true")
    args = parser.parse_args(argv)
    if not args.verify_receipt and (
        not args.source_revision or not args.attempt_id or not args.out
    ):
        parser.error("--source-revision, --attempt-id, and --out are required for a new attempt")
    try:
        return (
            verify(args.verify_receipt, args.require_operational_pass, args.historical_binding)
            if args.verify_receipt
            else run(args)
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
