#!/usr/bin/env python3
"""Source-bound S23 C4 operational receipt runner and verifier.

This is intentionally a new schema and predicate.  It never rewrites historical
S10 evidence and treats the Rust diagnostic JSONL as an observed subprocess
output, not as product or lifecycle authority.
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
SCHEMA = "m204-s23-c4-operational-receipt/v1"
PARSER_REL = "crates/ln-consultant-parser/src/contour_diagnostics.rs"
CONTRACT_REL = "prd/architecture/npa-acceptance-contract.yaml"
EXPECTED_XML = 43_785
DURATION_FLOOR_MS = 3_600_000
DEFAULT_BINARY = "target/debug/npa-contour-diagnostics"
DEFAULT_ROOT = "consru_export/consru_export/exports"
DEFAULT_GARANT = "law-source/garant"
S23_PREFIX = "prd/migration/rust-evidence/m204-s23-"


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
        return path.resolve(strict=False).relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def safe_s23_output(path: Path, label: str) -> Path:
    """Return a new, repository-relative S23 output path or reject it."""
    if path.is_absolute() or ".." in path.parts or "\\" in str(path):
        raise ValueError(f"{label} must be a relative S23 path")
    relative = path.as_posix()
    if not relative.startswith(S23_PREFIX) or ".git" in path.parts or ".gsd" in path.parts:
        raise ValueError(f"{label} is outside the S23 evidence destination")
    candidate = (ROOT / path).resolve(strict=False)
    current = ROOT
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label} traverses a symlink")
    try:
        candidate.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} escapes repository") from exc
    if candidate.exists():
        raise ValueError(f"immutable output already exists: {relative}")
    return candidate


def safe_input(path: Path, label: str) -> Path:
    """Canonicalize an input while rejecting repository metadata as an input pin."""
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve(strict=False)
    if ".git" in resolved.parts or ".gsd" in resolved.parts:
        raise ValueError(f"{label} may not use repository metadata")
    return resolved


def count_files(root: Path, suffix: str) -> int:
    return sum(1 for item in root.rglob(f"*{suffix}") if item.is_file())


def parser_revision() -> str:
    source = ROOT / PARSER_REL
    marker = 'pub const PARSER_REVISION: &str = "'
    text = source.read_text(encoding="utf-8")
    start = text.index(marker) + len(marker)
    return text[start : text.index('"', start)]


def toolchain() -> dict[str, Any]:
    result: dict[str, Any] = {"commands_exit_code": {}}
    for name in ("rustc", "cargo"):
        try:
            proc = subprocess.run([name, "--version"], capture_output=True, text=True, check=False)
            result[name] = proc.stdout.strip() or proc.stderr.strip()
            result["commands_exit_code"][name] = proc.returncode
        except OSError as exc:
            result[name] = str(exc)
            result["commands_exit_code"][name] = 127
    return result


def inventory_from_jsonl_v2(path: Path) -> tuple[str | None, bool, int]:
    """Read only object records and accept repeated equal inventory digests."""
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
                continue
            candidate = value.get("inventory_digest")
            if not isinstance(candidate, str) or not candidate:
                valid = False
            elif digest is None:
                digest = candidate
            elif candidate != digest:
                valid = False
    return digest, valid and lines > 0 and digest is not None, lines


def argv_hash(argv: list[str]) -> str:
    encoded = json.dumps(argv, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def terminate_group(proc: subprocess.Popen[str]) -> tuple[str, int | None]:
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
        return "SIGKILL", proc.wait(timeout=5)


def is_operational_pass_data(data: dict[str, Any]) -> bool:
    terminal = data.get("terminal", {})
    corpus = data.get("corpus", {})
    binding = data.get("c4_binding", {})
    output = data.get("observed_output", {})
    return (
        terminal.get("outcome") == "complete"
        and terminal.get("exit_code") == 0
        and terminal.get("timeout") is False
        and type(data.get("duration_ms")) is int
        and data["duration_ms"] >= DURATION_FLOOR_MS
        and binding.get("limit") is None
        and corpus.get("consultant_xml_count") == EXPECTED_XML
        and isinstance(output.get("inventory_digest"), str)
        and bool(output["inventory_digest"])
        and output.get("jsonl_valid") is True
    )


def exclusive_log(path: Path) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("x", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    if (
        not args.attempt_id
        or "." in args.attempt_id
        or "/" in args.attempt_id
        or ".." in args.attempt_id
    ):
        raise ValueError("attempt-id must be a safe non-empty identifier")
    if args.jobs < 0 or (args.limit is not None and args.limit < 0):
        raise ValueError("jobs and limit must be non-negative")
    if args.timeout_seconds <= 0 or args.budget_seconds <= 0:
        raise ValueError("timeout and budget must be positive")
    if not args.source_revision or not args.non_performance_claim:
        raise ValueError("source-revision and non-performance claim are required")

    binary = safe_input(args.binary, "binary")
    corpus = safe_input(args.root, "root")
    garant = safe_input(args.garant_root, "garant-root")
    contract_path = safe_input(args.contract, "contract")
    out = safe_s23_output(Path(args.out), "out")
    diagnostics = safe_s23_output(Path(args.diagnostics_out), "diagnostics-out")
    if out == diagnostics:
        raise ValueError("receipt and diagnostics output paths must differ")
    if (
        not binary.is_file()
        or not corpus.is_dir()
        or not garant.is_dir()
        or not contract_path.is_file()
    ):
        raise ValueError("binary, roots, or acceptance contract missing")
    contract_text = contract_path.read_text(encoding="utf-8")
    if (
        "schema: npa-acceptance-contract/v1" not in contract_text
        or "check_id: c4-live-check" not in contract_text
    ):
        raise ValueError("acceptance contract schema mismatch")

    log_dir = out.parent / f"{out.stem}-attempts" / args.attempt_id
    if not log_dir.is_relative_to(ROOT) or ".git" in log_dir.parts or ".gsd" in log_dir.parts:
        raise ValueError("log destination is unsafe")
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
    with exclusive_log(stdout_path) as stdout, exclusive_log(stderr_path) as stderr:
        try:
            proc = subprocess.Popen(
                argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True, text=True
            )
        except OSError as exc:
            terminal: dict[str, Any] = {
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
    inventory_digest, jsonl_valid, jsonl_lines = inventory_from_jsonl_v2(diagnostics)
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
            "contract_sha256": sha256(contract_path),
            "parser_source_sha256": sha256(ROOT / PARSER_REL),
        },
        "toolchain": toolchain(),
        "parser_revision": parser_revision(),
        "source_revision": args.source_revision,
        "contract": {
            "path": display(contract_path),
            "sha256": sha256(contract_path),
            "version": "npa-acceptance-contract/v1",
            "check_id": "c4-live-check",
            "mode": "runtime",
        },
        "corpus": {
            "consultant_xml_count": count_files(corpus, ".xml"),
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
                    "corpus": {"consultant_xml_count": count_files(corpus, ".xml")},
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
            args.non_performance_claim,
            "receipt presence is not runtime freshness",
            "source_revision is caller pin, not GSD aggregate",
            "semantic acceptance remains in Rust JSONL",
        ],
    }
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
                "output": display(out),
            }
        )
    )
    return 0


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} schema is not closed")
    return value


def verify(path: Path, require_operational_pass: bool) -> int:
    receipt_path = path.resolve(strict=True)
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    required = {
        "schema",
        "attempt_id",
        "immutable_attempt_identity",
        "argv",
        "binary",
        "binary_profile",
        "build_inputs",
        "toolchain",
        "parser_revision",
        "source_revision",
        "contract",
        "corpus",
        "c4_binding",
        "started_at",
        "finished_at",
        "duration_ms",
        "budget_seconds",
        "terminal",
        "observed_output",
        "logs",
        "claims",
        "non_claims",
    }
    _closed(data, required, "receipt")
    if (
        data["schema"] != SCHEMA
        or not isinstance(data["attempt_id"], str)
        or not data["attempt_id"]
    ):
        raise ValueError("receipt schema or attempt identity mismatch")
    identity = _closed(
        data["immutable_attempt_identity"], {"attempt_id", "argv_sha256"}, "attempt identity"
    )
    if identity["attempt_id"] != data["attempt_id"] or identity["argv_sha256"] != argv_hash(
        data["argv"]
    ):
        raise ValueError("argv hash binding mismatch")
    if (
        not isinstance(data["argv"], list)
        or not data["argv"]
        or any(type(item) is not str for item in data["argv"])
    ):
        raise ValueError("argv must be a string list")
    binary_info = _closed(data["binary"], {"path", "sha256"}, "binary")
    build = _closed(
        data["build_inputs"],
        {"binary_sha256", "contract_sha256", "parser_source_sha256"},
        "build inputs",
    )
    contract = _closed(
        data["contract"], {"path", "sha256", "version", "check_id", "mode"}, "contract"
    )
    _closed(
        data["corpus"],
        {"consultant_xml_count", "consultant_root", "garant_file_count", "garant_root"},
        "corpus",
    )
    binding = _closed(
        data["c4_binding"],
        {"profile", "limit", "jobs", "binary_profile", "inventory_scope", "source_revision"},
        "C4 binding",
    )
    terminal = _closed(data["terminal"], {"outcome", "exit_code", "signal", "timeout"}, "terminal")
    observed = _closed(
        data["observed_output"],
        {"diagnostics", "inventory_digest", "jsonl_valid", "jsonl_lines"},
        "observed output",
    )
    logs = _closed(
        data["logs"],
        {"stdout", "stderr", "stdout_sha256", "stderr_sha256", "diagnostics_sha256"},
        "logs",
    )
    claims = _closed(data["claims"], {"operational_acceptance", "duration_floor_ms"}, "claims")
    if (
        data["binary_profile"] not in ("debug", "release")
        or binding["binary_profile"] != data["binary_profile"]
        or binding["source_revision"] != data["source_revision"]
    ):
        raise ValueError("profile or source binding mismatch")
    if (
        type(data["duration_ms"]) is not int
        or data["duration_ms"] < 0
        or type(data["budget_seconds"]) is not int
        or data["budget_seconds"] < 3600
    ):
        raise ValueError("duration or budget metadata invalid")
    if terminal["outcome"] == "complete" and terminal["exit_code"] != 0:
        raise ValueError("complete receipt has nonzero exit")
    if terminal["timeout"] is not (terminal["outcome"] == "timeout"):
        raise ValueError("timeout binding mismatch")
    if (
        claims["duration_floor_ms"] != DURATION_FLOOR_MS
        or not isinstance(data["non_claims"], list)
        or any(type(x) is not str for x in data["non_claims"])
    ):
        raise ValueError("claim metadata malformed")
    if not any("non-performance" in item for item in data["non_claims"]):
        raise ValueError("non-performance claim is missing")

    def repo_file(value: str, label: str) -> Path:
        if (
            not isinstance(value, str)
            or Path(value).is_absolute()
            or ".." in Path(value).parts
            or "\\" in value
        ):
            raise ValueError(f"{label} path is unsafe")
        candidate = (ROOT / value).resolve(strict=True)
        try:
            candidate.relative_to(ROOT)
        except ValueError as exc:
            raise ValueError(f"{label} path escapes repository") from exc
        if (
            not candidate.is_file()
            or candidate.is_symlink()
            or ".git" in candidate.parts
            or ".gsd" in candidate.parts
        ):
            raise ValueError(f"{label} path is not an allowed regular file")
        return candidate

    binary = repo_file(binary_info["path"], "binary")
    contract_file = repo_file(contract["path"], "contract")
    parser = ROOT / PARSER_REL
    diagnostics = repo_file(observed["diagnostics"], "diagnostics")
    stdout = repo_file(logs["stdout"], "stdout")
    stderr = repo_file(logs["stderr"], "stderr")
    for label, value in (
        ("binary", binary_info),
        ("contract", contract),
        ("build binary", {"sha256": build["binary_sha256"]}),
        ("build contract", {"sha256": build["contract_sha256"]}),
    ):
        if not isinstance(value["sha256"], str) or not value["sha256"].startswith("sha256:"):
            raise ValueError(f"{label} hash is malformed")
    if (
        binary_info["sha256"] != sha256(binary)
        or build["binary_sha256"] != binary_info["sha256"]
        or contract["sha256"] != sha256(contract_file)
        or build["contract_sha256"] != contract["sha256"]
        or build["parser_source_sha256"] != sha256(parser)
    ):
        raise ValueError("source or binary hash binding mismatch")
    digest, valid, lines = inventory_from_jsonl_v2(diagnostics)
    if (digest, valid, lines) != (
        observed["inventory_digest"],
        observed["jsonl_valid"],
        observed["jsonl_lines"],
    ):
        raise ValueError("diagnostics inventory binding mismatch")
    if (
        logs["diagnostics_sha256"] != sha256(diagnostics)
        or logs["stdout_sha256"] != sha256(stdout)
        or logs["stderr_sha256"] != sha256(stderr)
    ):
        raise ValueError("log or diagnostics hash binding mismatch")
    if data["parser_revision"] != parser_revision():
        raise ValueError("parser revision mismatch")
    actual = is_operational_pass_data(data)
    expected = "pass" if actual else "non-pass"
    if claims["operational_acceptance"] != expected:
        raise ValueError("operational claim does not match observed facts")
    if require_operational_pass and not actual:
        raise ValueError("operational acceptance is not proven")
    print(json.dumps({"status": "pass", "operational_acceptance": expected}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, default=ROOT / DEFAULT_BINARY)
    parser.add_argument("--root", type=Path, default=ROOT / DEFAULT_ROOT)
    parser.add_argument("--garant-root", type=Path, default=ROOT / DEFAULT_GARANT)
    parser.add_argument("--contract", type=Path, default=ROOT / CONTRACT_REL)
    parser.add_argument("--out", default=f"{S23_PREFIX}c4-operational-receipt.json")
    parser.add_argument("--diagnostics-out", default=f"{S23_PREFIX}c4-diagnostics.jsonl")
    parser.add_argument("--source-revision")
    parser.add_argument("--attempt-id")
    parser.add_argument("--profile", default="contour")
    parser.add_argument("--binary-profile", choices=("debug", "release"), default="debug")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--budget-seconds", type=int, default=3600)
    parser.add_argument("--timeout-seconds", type=int, default=10800)
    parser.add_argument(
        "--non-performance-claim", default="debug timing is not a release performance claim"
    )
    parser.add_argument("--verify-receipt", type=Path)
    parser.add_argument("--require-operational-pass", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify_receipt:
            return verify(args.verify_receipt, args.require_operational_pass)
        if not args.source_revision or not args.attempt_id:
            parser.error("--source-revision and --attempt-id are required for a new attempt")
        return run(args)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
