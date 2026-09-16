#!/usr/bin/env python3
"""Live C4 operational recorder and fail-closed receipt gate for the M207 S04 contour (T02).

The recorder launches the pinned C4 operational walk over the full declared corpus and publishes
a *process* receipt -- ``m204-s06-c4-operational-receipt/v1`` reused verbatim, as frozen by
``prd/annotation/m207-s04-c4-protocol.md`` -- under
``prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json`` with its logs under
``prd/migration/rust-evidence/m207-s04-c4-attempts/<attempt_id>/``.

What this tool may and may not say:

* the receipt records process facts only -- argv, binary hash, toolchain, contract pin, corpus
  counts, wall clock, terminal facts and log hashes.  It carries no rate, no threshold, no
  classification, no gold label and no human acceptance;
* ``--limit`` is structurally absent from the recorder and is rejected in the recorded argv: a
  limited walk is not the full corpus (``ARGV_PIN_DRIFT``);
* the terminal outcome is published as-is.  A walk that exceeds ``budget_seconds`` is killed as a
  process group (SIGTERM) and published ``timeout``; a walk that finishes with a non-zero exit is
  published ``nonzero``; a walk that finishes faster than the budget floor is published
  ``non-pass`` by the frozen acceptance rule (``pass`` needs ``complete`` + ``exit_code == 0`` +
  ``duration_ms >= budget_seconds * 1000``). Nothing is rewritten to success, ever
  (``C4_TIMEOUT_AS_PASS``);
* ``run`` never overwrites published evidence: an existing receipt refuses a second write, and a
  non-empty attempt log directory refuses reuse unless ``--resume-orphan-logs`` confirms that the
  interrupted attempt published no receipt;
* ``check`` is read-only.  It validates the receipt against the frozen S04 schema document and the
  live tree, and prints exactly ``M207_S04_C4_RECEIPT_OK``.  It validates integrity and honest
  publication, **not** acceptance: a receipt that honestly publishes ``operational_acceptance =
  non-pass`` is a well-formed receipt;
* ``selftest`` proves the hostile paths (mutated receipts and planted trees) produce their named
  diagnostics, and prints exactly ``M207_S04_C4_SELFTEST_OK``.

Nothing here promotes anything: ``promotion`` stays ``none``, S03 rates stay ``not-measured`` and
``M207_S04_VERIFY_OK`` remains a battery verdict, never a C4 pass.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

RECEIPT_SCHEMA_ID = "m204-s06-c4-operational-receipt/v1"
SCHEMAS_REL = "prd/annotation/m207-s04-schemas.json"
MARKER = "M207_S04_C4_RECEIPT_OK"
SELFTEST_MARKER = "M207_S04_C4_SELFTEST_OK"
GATE_NAME = "M207_S04_C4_RECEIPT_GATE"

DEFAULT_BINARY_REL = "target/release/npa-contour-diagnostics"
DEFAULT_CONSULTANT_REL = "consru_export/consru_export/exports"
DEFAULT_GARANT_REL = "law-source/garant"
DEFAULT_CONTRACT_REL = "prd/architecture/npa-acceptance-contract.yaml"
DEFAULT_PARSER_SOURCE_REL = "crates/ln-consultant-parser/src/contour_diagnostics.rs"

FROZEN_BUDGET_SECONDS_MINIMUM = 3600
FROZEN_PROFILE = "contour"
FROZEN_JOBS = 0
FROZEN_CONSULTANT_XML_SUFFIX = ".xml"
FROZEN_CONSULTANT_XML_COUNT = 43785
FROZEN_GARANT_FILE_COUNT = 12
FROZEN_CONTRACT_VERSION = "npa-acceptance-contract/v1"
FROZEN_CONTRACT_CHECK_ID = "c4-live-check"
FROZEN_CONTRACT_MODE = "runtime"
FROZEN_BINARY_PATH = DEFAULT_BINARY_REL
FROZEN_LOG_FILES = ("stdout.log", "stderr.log")
DIGEST_FORMAT = "bare lowercase hex sha256, no algorithm prefix"

OUTCOME_VALUES = ("complete", "nonzero", "timeout", "launch_error", "not-run")
ACCEPTANCE_VALUES = ("pass", "non-pass")
ARGV_REQUIRED_FLAGS = (
    "--root",
    "--garant-root",
    "--profile",
    "--jobs",
    "--acceptance-contract",
    "--source-revision",
)
ARGV_FORBIDDEN_FLAGS = ("--limit",)
HASH_FIELDS = (
    "binary.sha256",
    "build_inputs.binary_sha256",
    "build_inputs.contract_sha256",
    "build_inputs.parser_source_sha256",
    "contract.sha256",
    "observed_output.stdout_sha256",
    "logs.stdout_sha256",
    "logs.stderr_sha256",
)
HASH_FIELD_DIAGNOSTICS: dict[str, str] = {
    "binary.sha256": "BINARY_HASH_MISSING",
    "build_inputs.binary_sha256": "BINARY_HASH_MISSING",
    "build_inputs.contract_sha256": "C4_RECEIPT_DRIFT",
    "build_inputs.parser_source_sha256": "C4_RECEIPT_DRIFT",
    "contract.sha256": "C4_RECEIPT_DRIFT",
    "observed_output.stdout_sha256": "LOG_HASH_MISSING",
    "logs.stdout_sha256": "LOG_HASH_MISSING",
    "logs.stderr_sha256": "LOG_HASH_MISSING",
}
INVENTORY_SCOPE = "consultant XML plus separate Garant files"
DEFAULT_ATTEMPT_ID = "m207-s04-c4-full-walk-001"
DEFAULT_SOURCE_REVISION = "m207-s04-c4-caller-pin-2026-09-16"
NON_CLAIMS = [
    "receipt presence is not freshness",
    "source_revision is caller pin, not GSD aggregate",
    "semantic acceptance remains in Rust JSONL",
    "not gold: the receipt is a process record, never a gold label",
    "not a promotion: promotion stays none and classification stays not-authorized",
    "not an S03 rate publication: no aspect rate, stratum rate or measurement_status is imported",
    "not a seed enlargement: the frozen fragment seed is untouched",
    "not an R035 or R070 closure: a corpus walk is operational diagnostics only",
    "not a marker promotion: M207_S04_VERIFY_OK means the integrity battery ran",
]

KILL_GRACE_SECONDS = 30
DURATION_TOLERANCE_MS = 5000
ISO_SECONDS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
S03_TOKEN_RE = re.compile(r"m207[-_]s03")
ATTEMPT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

Failures = list[tuple[str, str]]
_MISSING = object()


class GateError(Exception):
    """Fatal, named failure that stops the tool before it writes anything."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def argv_sha256(argv: list[str]) -> str:
    payload = json.dumps(argv, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GateError("DUPLICATE_JSON_KEY", f"duplicate object key {key!r}")
        seen[key] = value
    return seen


def parse_json_text(text: str, label: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not valid JSON: {exc}") from exc


def load_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise GateError("MISSING_ARTIFACT", f"{label} not found at {path}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} carries a UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not UTF-8: {exc}") from exc
    return parse_json_text(text, label)


def dig(data: dict[str, Any], dotted: str) -> Any:
    node: Any = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def is_bare_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX64_RE.match(value))


def is_digest_like(value: Any) -> bool:
    return isinstance(value, str) and (value.startswith("sha256:") or bool(HEX64_RE.match(value)))


def flag_values(argv: Any, flag: str) -> list[str]:
    if not isinstance(argv, list):
        return []
    return [
        argv[index + 1]
        for index, value in enumerate(argv)
        if value == flag and index + 1 < len(argv) and isinstance(argv[index + 1], str)
    ]


def resolve_repo_path(root: Path, raw: Any, label: str, *, suffix: str = "") -> Path:
    """Resolve a repository-relative path, fail-closed on escapes."""
    if (
        not isinstance(raw, str)
        or not raw
        or "\x00" in raw
        or raw.startswith("/")
        or "\\" in raw
        or (len(raw) > 1 and raw[1] == ":")
    ):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must be a POSIX relative path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} may not escape the repository")
    if suffix and relative.suffix != suffix:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must have suffix {suffix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def count_files(root: Path, suffix: str) -> int:
    return sum(1 for path in root.rglob(f"*{suffix}") if path.is_file())


def count_all_files(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file())


def read_parser_revision(source: Path) -> str:
    if not source.is_file():
        raise GateError("MISSING_ARTIFACT", f"parser source not found at {source}")
    text = source.read_text(encoding="utf-8")
    marker = 'pub const PARSER_REVISION: &str = "'
    start = text.find(marker)
    if start < 0:
        raise GateError(
            "MISSING_ARTIFACT", f"PARSER_REVISION is not declared in {source.as_posix()}"
        )
    start += len(marker)
    end = text.find('"', start)
    if end < 0:
        raise GateError("MISSING_ARTIFACT", f"PARSER_REVISION is malformed in {source.as_posix()}")
    return text[start:end]


def toolchain() -> dict[str, Any]:
    rustc = subprocess.run(
        ["rustc", "--version"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    cargo = subprocess.run(
        ["cargo", "--version"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return {
        "rustc": (rustc.stdout + rustc.stderr).strip(),
        "cargo": (cargo.stdout + cargo.stderr).strip(),
        "commands_exit_code": {"rustc": rustc.returncode, "cargo": cargo.returncode},
    }


def parse_contract(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise GateError("MISSING_ARTIFACT", f"acceptance contract not found at {path.as_posix()}")
    text = path.read_text(encoding="utf-8")
    if f"schema: {FROZEN_CONTRACT_VERSION}" not in text:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{path.as_posix()} does not declare schema {FROZEN_CONTRACT_VERSION}",
        )
    if f"check_id: {FROZEN_CONTRACT_CHECK_ID}" not in text:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{path.as_posix()} does not declare check_id {FROZEN_CONTRACT_CHECK_ID}",
        )
    if f"mode: {FROZEN_CONTRACT_MODE}" not in text:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{FROZEN_CONTRACT_CHECK_ID} is not a {FROZEN_CONTRACT_MODE} check in {path.as_posix()}",
        )
    return {
        "path": display_path(path),
        "sha256": sha256_file(path),
        "version": FROZEN_CONTRACT_VERSION,
        "check_id": FROZEN_CONTRACT_CHECK_ID,
        "mode": FROZEN_CONTRACT_MODE,
    }


def acceptance_for(outcome: Any, exit_code: Any, duration_ms: Any, budget_seconds: Any) -> str:
    """The frozen M204/S06 rule, reused verbatim: nothing is relaxed here."""
    if (
        outcome == "complete"
        and exit_code == 0
        and isinstance(duration_ms, int)
        and isinstance(budget_seconds, int)
        and duration_ms >= budget_seconds * 1000
    ):
        return "pass"
    return "non-pass"


def schema_contract(schema_doc: Any) -> dict[str, Any]:
    if not isinstance(schema_doc, dict):
        raise GateError("SCHEMA_PARSE_ERROR", "S04 schemas document must be a JSON object")
    if schema_doc.get("schema") != "m207-s04-c4-schemas/v1":
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"S04 schemas document schema={schema_doc.get('schema')!r} is not the frozen id",
        )
    contract = schema_doc.get("receipt_contract")
    if not isinstance(contract, dict) or contract.get("schema_id") != RECEIPT_SCHEMA_ID:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"S04 schemas document must carry {RECEIPT_SCHEMA_ID!r} in receipt_contract",
        )
    return contract


def default_receipt_rel(schema_doc: Any) -> str:
    contract = schema_contract(schema_doc)
    rel = contract.get("receipt_path")
    if not isinstance(rel, str) or not rel.startswith("prd/migration/rust-evidence/"):
        raise GateError("UNSAFE_PATH", f"receipt_path={rel!r} is not the pinned evidence path")
    return rel


# --------------------------------------------------------------------------- #
# Recorder
# --------------------------------------------------------------------------- #


def build_argv(
    binary: Path, corpus_root: Path, garant_root: Path, contract: Path, source_revision: str
) -> list[str]:
    return [
        str(binary),
        "--root",
        str(corpus_root),
        "--garant-root",
        str(garant_root),
        "--profile",
        FROZEN_PROFILE,
        "--jobs",
        str(FROZEN_JOBS),
        "--acceptance-contract",
        str(contract),
        "--source-revision",
        source_revision,
    ]


def launch_walk(
    argv: list[str], log_dir: Path, timeout_seconds: int
) -> tuple[dict[str, Any], int, Path, Path]:
    """Run the walk, killing its process group on timeout. Returns (terminal, ms, out, err)."""
    stdout_path = log_dir / FROZEN_LOG_FILES[0]
    stderr_path = log_dir / FROZEN_LOG_FILES[1]
    started_mono = time.monotonic()
    with (
        stdout_path.open("w", encoding="utf-8") as out,
        stderr_path.open("w", encoding="utf-8") as err,
    ):
        try:
            proc = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=err, start_new_session=True)
        except OSError as exc:
            elapsed = int((time.monotonic() - started_mono) * 1000)
            return (
                {
                    "outcome": "launch_error",
                    "exit_code": None,
                    "signal": None,
                    "timeout": False,
                    "error": str(exc),
                },
                elapsed,
                stdout_path,
                stderr_path,
            )
        try:
            code = proc.wait(timeout=timeout_seconds)
            terminal = {
                "outcome": "complete" if code == 0 else "nonzero",
                "exit_code": code,
                "signal": None,
                "timeout": False,
            }
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=KILL_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            terminal = {
                "outcome": "timeout",
                "exit_code": None,
                "signal": "SIGTERM",
                "timeout": True,
            }
    elapsed = int((time.monotonic() - started_mono) * 1000)
    return terminal, elapsed, stdout_path, stderr_path


def extract_inventory_digest(stdout_text: str) -> str | None:
    for line in stdout_text.splitlines():
        if '"inventory_digest"' not in line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        value = record.get("inventory_digest")
        if isinstance(value, str) and value:
            return value
    return None


def cmd_run(args: argparse.Namespace) -> int:
    repo_root = Path(args.root).resolve()
    binary = Path(args.binary)
    binary = binary if binary.is_absolute() else repo_root / binary
    corpus_root = Path(args.consultant_root)
    corpus_root = corpus_root if corpus_root.is_absolute() else repo_root / corpus_root
    garant_root = Path(args.garant_root)
    garant_root = garant_root if garant_root.is_absolute() else repo_root / garant_root
    contract_path = Path(args.contract)
    contract_path = contract_path if contract_path.is_absolute() else repo_root / contract_path
    parser_source = repo_root / args.parser_source

    try:
        if not ATTEMPT_ID_RE.match(args.attempt_id):
            raise GateError("UNSAFE_PATH", f"--attempt-id {args.attempt_id!r} must be a safe slug")
        if args.budget_seconds < FROZEN_BUDGET_SECONDS_MINIMUM:
            raise GateError(
                "BUDGET_BELOW_MINIMUM",
                f"--budget-seconds {args.budget_seconds} is below the frozen "
                f"{FROZEN_BUDGET_SECONDS_MINIMUM}s floor",
            )
        if args.profile != FROZEN_PROFILE:
            raise GateError(
                "ARGV_PIN_DRIFT", f"--profile {args.profile!r} is not the pinned {FROZEN_PROFILE!r}"
            )
        if args.jobs != FROZEN_JOBS:
            raise GateError("ARGV_PIN_DRIFT", f"--jobs {args.jobs} is not the pinned {FROZEN_JOBS}")
        if not binary.is_file():
            raise GateError("MISSING_ARTIFACT", f"binary {binary.as_posix()} is absent")
        if not corpus_root.is_dir():
            raise GateError("MISSING_ARTIFACT", f"corpus root {corpus_root.as_posix()} is absent")
        if not garant_root.is_dir():
            raise GateError("MISSING_ARTIFACT", f"garant root {garant_root.as_posix()} is absent")
        if not args.source_revision.strip() or is_digest_like(args.source_revision.strip()):
            raise GateError(
                "SOURCE_REVISION_MISSING",
                "--source-revision must be a caller pin, never a digest",
            )
        schema_doc = load_json(repo_root / args.schemas, "S04 schemas document")
        contract_block = schema_contract(schema_doc)
        log_root = resolve_repo_path(
            repo_root, contract_block.get("attempt_log_dir"), "attempt_log_dir"
        )
        evidence_root = (repo_root / "prd/migration/rust-evidence").resolve()
        if args.out:
            receipt_path = Path(args.out).resolve()
            if not receipt_path.is_relative_to(evidence_root):
                raise GateError(
                    "UNSAFE_PATH",
                    f"--out {receipt_path.as_posix()} must stay under the pinned evidence dir",
                )
        else:
            receipt_path = resolve_repo_path(
                repo_root, contract_block.get("receipt_path"), "receipt_path"
            )
        log_dir = log_root / args.attempt_id
        if receipt_path.exists():
            raise GateError(
                "C4_RECEIPT_DRIFT",
                f"{display_path(receipt_path)} already exists; a later attempt needs a new "
                "attempt_id and a new receipt, published evidence is never overwritten",
            )
        if log_dir.exists() and any(log_dir.iterdir()) and not args.resume_orphan_logs:
            raise GateError(
                "ATTEMPT_LOG_MISSING",
                f"{display_path(log_dir)} already holds logs and no receipt was published; pass "
                "--resume-orphan-logs to reuse an interrupted attempt that published nothing",
            )
        contract = parse_contract(contract_path)
        parser_revision = read_parser_revision(parser_source)
    except GateError as exc:
        print(f"{exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return 2

    corpus = {
        "consultant_xml_count": count_files(corpus_root, FROZEN_CONSULTANT_XML_SUFFIX),
        "consultant_root": display_path(corpus_root),
        "garant_file_count": count_all_files(garant_root),
        "garant_root": display_path(garant_root),
    }
    if corpus["consultant_xml_count"] != FROZEN_CONSULTANT_XML_COUNT:
        print(
            f"CORPUS_COUNT_DRIFT: consultant XML count {corpus['consultant_xml_count']} is not "
            f"the frozen {FROZEN_CONSULTANT_XML_COUNT}",
            file=sys.stderr,
        )
        return 2
    if corpus["garant_file_count"] != FROZEN_GARANT_FILE_COUNT:
        print(
            f"CORPUS_COUNT_DRIFT: Garant file count {corpus['garant_file_count']} is not the "
            f"frozen {FROZEN_GARANT_FILE_COUNT}",
            file=sys.stderr,
        )
        return 2

    argv = build_argv(binary, corpus_root, garant_root, contract_path, args.source_revision)
    if any(flag in argv for flag in ARGV_FORBIDDEN_FLAGS):
        print("ARGV_PIN_DRIFT: the recorder never forwards a forbidden flag", file=sys.stderr)
        return 2

    log_dir.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    terminal, elapsed_ms, stdout_path, stderr_path = launch_walk(
        argv, log_dir, timeout_seconds=args.budget_seconds
    )
    finished_at = utc_now()

    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    inventory_digest = extract_inventory_digest(stdout_text)
    logs = {
        "stdout": display_path(stdout_path),
        "stderr": display_path(stderr_path),
        "stdout_sha256": sha256_file(stdout_path) if stdout_path.exists() else None,
        "stderr_sha256": sha256_file(stderr_path) if stderr_path.exists() else None,
        "inventory_digest": inventory_digest,
    }
    binary_hash = sha256_file(binary)
    receipt = {
        "schema": RECEIPT_SCHEMA_ID,
        "attempt_id": args.attempt_id,
        "immutable_attempt_identity": {
            "attempt_id": args.attempt_id,
            "argv_sha256": argv_sha256(argv),
        },
        "argv": argv,
        "binary": {"path": display_path(binary), "sha256": binary_hash},
        "build_inputs": {
            "binary_sha256": binary_hash,
            "contract_sha256": contract["sha256"],
            "parser_source_sha256": sha256_file(parser_source),
        },
        "toolchain": toolchain(),
        "parser_revision": parser_revision,
        "source_revision": args.source_revision,
        "contract": contract,
        "corpus": corpus,
        "observed_output": {
            "stdout_sha256": logs["stdout_sha256"],
            "inventory_digest": inventory_digest,
        },
        "c4_binding": {
            "profile": FROZEN_PROFILE,
            "limit": None,
            "jobs": FROZEN_JOBS,
            "inventory_scope": INVENTORY_SCOPE,
            "baseline_sha256": None,
        },
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": elapsed_ms,
        "budget_seconds": args.budget_seconds,
        "terminal": terminal,
        "logs": logs,
        "claims": {
            "operational_acceptance": acceptance_for(
                terminal.get("outcome"), terminal.get("exit_code"), elapsed_ms, args.budget_seconds
            ),
            "receipt_is_runtime_attempt": True,
        },
        "non_claims": list(NON_CLAIMS),
    }

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    if receipt_path.exists():
        print(
            f"C4_RECEIPT_DRIFT: {display_path(receipt_path)} appeared during the attempt; "
            "refusing to overwrite published evidence",
            file=sys.stderr,
        )
        return 2
    staged = receipt_path.with_name(receipt_path.name + ".partial")
    staged.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    staged.replace(receipt_path)

    print(
        json.dumps(
            {
                "schema": RECEIPT_SCHEMA_ID,
                "receipt": display_path(receipt_path),
                "attempt_id": args.attempt_id,
                "outcome": terminal["outcome"],
                "exit_code": terminal["exit_code"],
                "duration_ms": elapsed_ms,
                "budget_seconds": args.budget_seconds,
                "operational_acceptance": receipt["claims"]["operational_acceptance"],
            }
        )
    )
    return 0 if terminal["outcome"] in OUTCOME_VALUES else 3


# --------------------------------------------------------------------------- #
# Read-only receipt gate
# --------------------------------------------------------------------------- #


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def check_schema_pins(schema_doc: dict[str, Any], failures: Failures) -> None:
    """The frozen pins this tool holds in code must still agree with the frozen document."""
    contract = schema_doc.get("receipt_contract") or {}
    if contract.get("binary_path_pin") != FROZEN_BINARY_PATH:
        _fail(failures, "C4_RECEIPT_DRIFT", "schema binary_path_pin drifted from the release path")
    if contract.get("profile_pin") != FROZEN_PROFILE or contract.get("jobs_pin") != FROZEN_JOBS:
        _fail(failures, "ARGV_PIN_DRIFT", "schema profile/jobs pins drifted")
    if contract.get("limit_pin", _MISSING) is not None:
        _fail(failures, "ARGV_PIN_DRIFT", "schema limit_pin must stay null")
    if list(contract.get("argv_forbidden_flags") or []) != list(ARGV_FORBIDDEN_FLAGS):
        _fail(failures, "ARGV_PIN_DRIFT", "schema argv_forbidden_flags drifted")
    if list(contract.get("argv_required_flags") or []) != list(ARGV_REQUIRED_FLAGS):
        _fail(failures, "ARGV_PIN_DRIFT", "schema argv_required_flags drifted")
    minimum = contract.get("budget_seconds_minimum")
    if not isinstance(minimum, int) or minimum < FROZEN_BUDGET_SECONDS_MINIMUM:
        _fail(failures, "BUDGET_BELOW_MINIMUM", "schema budget_seconds_minimum is below 3600")
    if list(contract.get("outcome_values") or []) != list(OUTCOME_VALUES):
        _fail(failures, "TERMINAL_OUTCOME_DRIFT", "schema outcome_values drifted")
    if contract.get("contract_version_pin") != FROZEN_CONTRACT_VERSION:
        _fail(failures, "C4_RECEIPT_DRIFT", "schema contract_version_pin drifted")
    if contract.get("contract_check_id_pin") != FROZEN_CONTRACT_CHECK_ID:
        _fail(failures, "C4_RECEIPT_DRIFT", "schema contract_check_id_pin drifted")
    if contract.get("contract_mode_pin") != FROZEN_CONTRACT_MODE:
        _fail(failures, "C4_RECEIPT_DRIFT", "schema contract_mode_pin drifted")
    if schema_doc.get("digest_format") != DIGEST_FORMAT:
        _fail(
            failures, "C4_RECEIPT_DRIFT", "schema digest_format drifted from the bare digest rule"
        )
    pins = schema_doc.get("corpus_pins") or {}
    if pins.get("consultant_xml_count") != FROZEN_CONSULTANT_XML_COUNT:
        _fail(failures, "CORPUS_COUNT_DRIFT", "schema consultant_xml_count drifted")
    if pins.get("garant_file_count") != FROZEN_GARANT_FILE_COUNT:
        _fail(failures, "CORPUS_COUNT_DRIFT", "schema garant_file_count drifted")
    if list(contract.get("closed_keys") or []) and not set(contract["closed_keys"]) >= {
        "argv",
        "binary",
        "build_inputs",
        "toolchain",
        "contract",
        "corpus",
        "observed_output",
        "c4_binding",
        "started_at",
        "finished_at",
        "duration_ms",
        "budget_seconds",
        "terminal",
        "logs",
        "claims",
        "non_claims",
    }:
        _fail(failures, "C4_RECEIPT_DRIFT", "schema receipt closure lost required receipt keys")


def check_shape(receipt: dict[str, Any], contract: dict[str, Any], failures: Failures) -> bool:
    """Root/nested closure and required keys. Returns False when the shape is unusable."""
    closed = list(contract.get("closed_keys") or [])
    required = list(contract.get("required_keys") or [])
    nested = contract.get("nested_closed_keys") or {}
    if not closed or not required or not isinstance(nested, dict):
        _fail(failures, "C4_RECEIPT_DRIFT", "schema receipt closure is unusable")
        return False
    extra = sorted(set(receipt) - set(closed))
    if extra:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"receipt carries keys outside the closure: {extra}")
    missing = sorted(set(required) - set(receipt))
    if missing:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"receipt is missing required keys: {missing}")
    if extra or missing:
        return False
    if receipt.get("schema") != RECEIPT_SCHEMA_ID:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"receipt.schema={receipt.get('schema')!r} != {RECEIPT_SCHEMA_ID!r}",
        )
        return False
    for name, keys in nested.items():
        node = receipt.get(name)
        if not isinstance(node, dict):
            _fail(failures, "SCHEMA_KEY_DRIFT", f"receipt.{name} must be an object")
            return False
        drift = sorted(set(node) - set(keys))
        gap = sorted(set(keys) - set(node))
        if drift:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"receipt.{name} carries keys outside its closure: {drift}",
            )
        if gap:
            _fail(failures, "SCHEMA_KEY_DRIFT", f"receipt.{name} is missing keys: {gap}")
        if drift or gap:
            return False
    return True


def check_identity(receipt: dict[str, Any], failures: Failures) -> None:
    identity = receipt["immutable_attempt_identity"]
    argv = receipt["argv"]
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        _fail(failures, "ARGV_PIN_DRIFT", "receipt.argv must be a non-empty list of strings")
        return
    if identity.get("attempt_id") != receipt.get("attempt_id"):
        _fail(
            failures,
            "IMMUTABLE_IDENTITY_MISSING",
            "immutable_attempt_identity.attempt_id does not match the receipt attempt_id",
        )
    recorded = identity.get("argv_sha256")
    if not is_bare_digest(recorded):
        _fail(
            failures,
            "IMMUTABLE_IDENTITY_MISSING",
            f"argv_sha256={recorded!r} is not a bare sha256 digest",
        )
        return
    if recorded != argv_sha256(argv):
        _fail(
            failures,
            "IMMUTABLE_IDENTITY_MISSING",
            "argv_sha256 does not match the recorded argv: the identity was rebuilt or edited",
        )


def check_argv(receipt: dict[str, Any], failures: Failures) -> None:
    argv = receipt["argv"]
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        _fail(failures, "ARGV_PIN_DRIFT", "receipt.argv must be a non-empty list of strings")
        return
    for flag in ARGV_FORBIDDEN_FLAGS:
        if flag in argv:
            _fail(
                failures,
                "ARGV_PIN_DRIFT",
                f"receipt.argv carries the forbidden flag {flag!r}: a limited walk is not the "
                "full corpus",
            )
    for flag in ARGV_REQUIRED_FLAGS:
        values = flag_values(argv, flag)
        if len(values) != 1:
            _fail(
                failures,
                "ARGV_PIN_DRIFT",
                f"receipt.argv must carry {flag!r} exactly once (found {len(values)})",
            )
    if flag_values(argv, "--profile") != [FROZEN_PROFILE]:
        _fail(failures, "ARGV_PIN_DRIFT", "receipt.argv --profile is not the pinned contour")
    if flag_values(argv, "--jobs") != [str(FROZEN_JOBS)]:
        _fail(failures, "ARGV_PIN_DRIFT", "receipt.argv --jobs is not the pinned 0")
    corpus_root = receipt["corpus"].get("consultant_root")
    garant_root = receipt["corpus"].get("garant_root")
    for flag, relative in (
        ("--root", corpus_root),
        ("--garant-root", garant_root),
        ("--acceptance-contract", DEFAULT_CONTRACT_REL),
    ):
        values = flag_values(argv, flag)
        if len(values) == 1 and isinstance(relative, str):
            value = values[0]
            if not value.startswith("/") or not value.endswith(relative):
                _fail(
                    failures,
                    "ARGV_PIN_DRIFT",
                    f"receipt.argv {flag}={value!r} does not bind the declared path {relative!r}",
                )
    if flag_values(argv, "--source-revision") != [receipt.get("source_revision")]:
        _fail(
            failures,
            "ARGV_PIN_DRIFT",
            "receipt.argv --source-revision does not match receipt.source_revision",
        )


def check_binding(receipt: dict[str, Any], failures: Failures) -> None:
    binding = receipt["c4_binding"]
    if binding.get("profile") != FROZEN_PROFILE:
        _fail(failures, "ARGV_PIN_DRIFT", "c4_binding.profile is not the pinned contour")
    if binding.get("limit", _MISSING) is not None:
        _fail(failures, "ARGV_PIN_DRIFT", "c4_binding.limit must stay null: no limited walk")
    if binding.get("jobs") != FROZEN_JOBS:
        _fail(failures, "ARGV_PIN_DRIFT", "c4_binding.jobs is not the pinned 0")
    scope = binding.get("inventory_scope")
    if not isinstance(scope, str) or not scope.strip():
        _fail(failures, "C4_RECEIPT_DRIFT", "c4_binding.inventory_scope must be declared")
    baseline = binding.get("baseline_sha256", _MISSING)
    if baseline is not None and not is_bare_digest(baseline):
        _fail(failures, "C4_RECEIPT_DRIFT", "c4_binding.baseline_sha256 must be null or a digest")


def check_pins(receipt: dict[str, Any], schema_doc: dict[str, Any], failures: Failures) -> None:
    for field in HASH_FIELDS:
        value = dig(receipt, field)
        diagnostic = HASH_FIELD_DIAGNOSTICS[field]
        if value is _MISSING or value is None:
            _fail(failures, diagnostic, f"receipt.{field} is missing")
        elif not is_bare_digest(value):
            _fail(
                failures,
                diagnostic,
                f"receipt.{field}={value!r} is not a bare lowercase sha256 digest",
            )
    if receipt["binary"].get("path") != FROZEN_BINARY_PATH:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"binary.path={receipt['binary'].get('path')!r} != {FROZEN_BINARY_PATH!r}",
        )
    if receipt["binary"].get("sha256") != receipt["build_inputs"].get("binary_sha256"):
        _fail(
            failures,
            "BINARY_HASH_MISSING",
            "binary.sha256 and build_inputs.binary_sha256 disagree",
        )
    source_hash = receipt["build_inputs"].get("parser_source_sha256")
    if not is_bare_digest(source_hash):
        _fail(
            failures,
            "BINARY_HASH_MISSING",
            "build_inputs.parser_source_sha256 must be a bare sha256 digest",
        )
    toolchain_node = receipt["toolchain"]
    for field in ("rustc", "cargo"):
        value = toolchain_node.get(field)
        if not isinstance(value, str) or not value.strip():
            _fail(failures, "TOOLCHAIN_PIN_MISSING", f"toolchain.{field} must be recorded")
    codes = toolchain_node.get("commands_exit_code")
    if not isinstance(codes, dict) or codes.get("rustc") != 0 or codes.get("cargo") != 0:
        _fail(failures, "TOOLCHAIN_PIN_MISSING", "toolchain.commands_exit_code must be 0/0")
    source_revision = receipt.get("source_revision")
    if (
        not isinstance(source_revision, str)
        or not source_revision.strip()
        or is_digest_like(source_revision.strip())
        or source_revision.strip() == "unavailable"
    ):
        _fail(
            failures,
            "SOURCE_REVISION_MISSING",
            f"source_revision={source_revision!r} must be a caller pin, never a digest",
        )
    contract = receipt["contract"]
    if contract.get("version") != FROZEN_CONTRACT_VERSION:
        _fail(failures, "C4_RECEIPT_DRIFT", "contract.version is not the runtime contract version")
    if contract.get("check_id") != FROZEN_CONTRACT_CHECK_ID:
        _fail(failures, "C4_RECEIPT_DRIFT", "contract.check_id is not the c4-live-check id")
    if contract.get("mode") != FROZEN_CONTRACT_MODE:
        _fail(failures, "C4_RECEIPT_DRIFT", "contract.mode is not the runtime mode")
    frozen_path = dig(schema_doc, "frozen_sources.npa_acceptance_contract.path")
    if isinstance(frozen_path, str) and contract.get("path") != frozen_path:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"contract.path={contract.get('path')!r} != the frozen {frozen_path!r}",
        )
    if contract.get("sha256") != receipt["build_inputs"].get("contract_sha256"):
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "contract.sha256 and build_inputs.contract_sha256 disagree",
        )


def check_wall_clock(receipt: dict[str, Any], failures: Failures) -> None:
    duration = receipt.get("duration_ms")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        _fail(failures, "DURATION_MISSING", f"duration_ms={duration!r} must be a positive integer")
    budget = receipt.get("budget_seconds")
    if not isinstance(budget, int) or isinstance(budget, bool):
        _fail(failures, "BUDGET_BELOW_MINIMUM", f"budget_seconds={budget!r} must be an integer")
    elif budget < FROZEN_BUDGET_SECONDS_MINIMUM:
        _fail(
            failures,
            "BUDGET_BELOW_MINIMUM",
            f"budget_seconds={budget} is below the frozen {FROZEN_BUDGET_SECONDS_MINIMUM}s floor",
        )
    started = receipt.get("started_at")
    finished = receipt.get("finished_at")
    if not isinstance(started, str) or not ISO_SECONDS_RE.match(started):
        _fail(failures, "C4_RECEIPT_DRIFT", "started_at must be an ISO-8601 UTC second timestamp")
    if not isinstance(finished, str) or not ISO_SECONDS_RE.match(finished):
        _fail(failures, "C4_RECEIPT_DRIFT", "finished_at must be an ISO-8601 UTC second timestamp")
    if isinstance(started, str) and isinstance(finished, str) and finished < started:
        _fail(failures, "C4_RECEIPT_DRIFT", "finished_at precedes started_at")
    if (
        not isinstance(duration, int)
        or not isinstance(started, str)
        or not isinstance(finished, str)
    ):
        return
    try:
        delta_ms = int(
            (
                datetime.strptime(finished, "%Y-%m-%dT%H:%M:%SZ")
                - datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")
            ).total_seconds()
            * 1000
        )
    except ValueError:
        return
    if abs(delta_ms - duration) > DURATION_TOLERANCE_MS:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"duration_ms={duration} disagrees with the recorded wall clock ({delta_ms} ms)",
        )


def check_terminal(receipt: dict[str, Any], failures: Failures) -> None:
    terminal = receipt["terminal"]
    outcome = terminal.get("outcome")
    exit_code = terminal.get("exit_code")
    signal_name = terminal.get("signal")
    timeout = terminal.get("timeout")
    if outcome not in OUTCOME_VALUES:
        _fail(
            failures,
            "TERMINAL_OUTCOME_DRIFT",
            f"terminal.outcome={outcome!r} is outside {list(OUTCOME_VALUES)}",
        )
        return
    if not isinstance(timeout, bool):
        _fail(failures, "TERMINAL_OUTCOME_DRIFT", "terminal.timeout must be a boolean")
        return
    if outcome == "complete":
        if exit_code != 0 or timeout or signal_name is not None:
            _fail(
                failures,
                "TERMINAL_OUTCOME_DRIFT",
                "a complete outcome requires exit_code 0, timeout false and signal null",
            )
    elif outcome == "nonzero":
        if not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code == 0:
            _fail(
                failures,
                "TERMINAL_OUTCOME_DRIFT",
                "a nonzero outcome requires an integer non-zero exit_code",
            )
        if timeout or signal_name is not None:
            _fail(
                failures,
                "TERMINAL_OUTCOME_DRIFT",
                "a nonzero outcome requires timeout false and signal null",
            )
    elif outcome == "timeout":
        if timeout is not True or signal_name != "SIGTERM" or exit_code is not None:
            _fail(
                failures,
                "TERMINAL_OUTCOME_DRIFT",
                "a timeout outcome requires timeout true, signal SIGTERM and exit_code null",
            )
    else:
        if timeout or exit_code is not None:
            _fail(
                failures,
                "TERMINAL_OUTCOME_DRIFT",
                f"a {outcome} outcome requires timeout false and exit_code null",
            )
    claims = receipt["claims"]
    if claims.get("receipt_is_runtime_attempt") is not True:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "claims.receipt_is_runtime_attempt must stay true",
        )
    recorded = claims.get("operational_acceptance")
    if recorded not in ACCEPTANCE_VALUES:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"claims.operational_acceptance={recorded!r} is outside {list(ACCEPTANCE_VALUES)}",
        )
        return
    computed = acceptance_for(
        outcome, exit_code, receipt.get("duration_ms"), receipt.get("budget_seconds")
    )
    if recorded == computed:
        return
    if outcome == "timeout" and recorded == "pass":
        _fail(
            failures, "C4_TIMEOUT_AS_PASS", "a timeout is published pass: the outcome was laundered"
        )
    elif recorded == "pass":
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "operational_acceptance claims pass while the frozen rule computes non-pass "
            "(complete + exit_code 0 + duration_ms >= budget_seconds * 1000)",
        )
    else:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"operational_acceptance={recorded!r} disagrees with the frozen rule ({computed!r})",
        )


def check_logs(
    receipt: dict[str, Any], contract: dict[str, Any], root: Path, failures: Failures
) -> None:
    logs = receipt["logs"]
    observed = receipt["observed_output"]
    if observed.get("stdout_sha256") != logs.get("stdout_sha256"):
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "observed_output.stdout_sha256 and logs.stdout_sha256 disagree",
        )
    if observed.get("inventory_digest") != logs.get("inventory_digest"):
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "observed_output.inventory_digest and logs.inventory_digest disagree",
        )
    attempt_id = receipt.get("attempt_id")
    try:
        log_root = resolve_repo_path(root, contract.get("attempt_log_dir"), "attempt_log_dir")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    expected_dir = (log_root / str(attempt_id)) if isinstance(attempt_id, str) else log_root
    for field, name in (("stdout", FROZEN_LOG_FILES[0]), ("stderr", FROZEN_LOG_FILES[1])):
        raw = logs.get(field)
        try:
            path = resolve_repo_path(root, raw, f"logs.{field}")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        if path.parent != expected_dir.resolve(strict=False) or path.name != name:
            _fail(
                failures,
                "ATTEMPT_LOG_MISSING",
                f"logs.{field}={raw!r} is not {name} under the attempt log directory",
            )
            continue
        if not path.is_file():
            _fail(failures, "ATTEMPT_LOG_MISSING", f"attempt log {raw!r} is missing")
            continue
        recorded = logs.get(f"{field}_sha256")
        if is_bare_digest(recorded) and sha256_file(path) != recorded:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                f"attempt log {raw!r} does not hash to the recorded {field}_sha256",
            )


def check_corpus(
    receipt: dict[str, Any], schema_doc: dict[str, Any], root: Path, failures: Failures
) -> None:
    corpus = receipt["corpus"]
    pins = schema_doc.get("corpus_pins") or {}
    if corpus.get("consultant_root") != pins.get("consultant_root"):
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            f"corpus.consultant_root={corpus.get('consultant_root')!r} != the pinned root",
        )
    if corpus.get("garant_root") != pins.get("garant_root"):
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            f"corpus.garant_root={corpus.get('garant_root')!r} != the pinned root",
        )
    for field, frozen in (
        ("consultant_xml_count", FROZEN_CONSULTANT_XML_COUNT),
        ("garant_file_count", FROZEN_GARANT_FILE_COUNT),
    ):
        value = corpus.get(field)
        if value != frozen:
            _fail(
                failures,
                "CORPUS_COUNT_DRIFT",
                f"corpus.{field}={value!r} is not the frozen {frozen}",
            )
    try:
        consultant_root = resolve_repo_path(
            root, corpus.get("consultant_root"), "corpus.consultant_root"
        )
        garant_root = resolve_repo_path(root, corpus.get("garant_root"), "corpus.garant_root")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    if consultant_root.is_dir():
        actual = count_files(consultant_root, FROZEN_CONSULTANT_XML_SUFFIX)
        if actual != FROZEN_CONSULTANT_XML_COUNT:
            _fail(
                failures,
                "CORPUS_COUNT_DRIFT",
                f"live consultant XML count {actual} != the frozen {FROZEN_CONSULTANT_XML_COUNT}",
            )
    else:
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            f"declared consultant root {corpus.get('consultant_root')!r} is not a directory",
        )
    if garant_root.is_dir():
        actual_garant = count_all_files(garant_root)
        if actual_garant != FROZEN_GARANT_FILE_COUNT:
            _fail(
                failures,
                "CORPUS_COUNT_DRIFT",
                f"live Garant file count {actual_garant} != the frozen {FROZEN_GARANT_FILE_COUNT}",
            )
    else:
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            f"declared Garant root {corpus.get('garant_root')!r} is not a directory",
        )


def check_frozen_lineage(
    receipt: dict[str, Any], schema_doc: dict[str, Any], root: Path, failures: Failures
) -> None:
    """The pinned M204/S06 attempt stays a prior non-pass; no S03 report appears."""
    prior_path = dig(schema_doc, "prior_non_pass_pin.path")
    prior_sha = dig(schema_doc, "prior_non_pass_pin.sha256")
    if isinstance(prior_path, str) and isinstance(prior_sha, str):
        try:
            path = resolve_repo_path(root, prior_path, "prior_non_pass_pin.path")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
        else:
            if not path.is_file():
                _fail(
                    failures,
                    "C4_TIMEOUT_AS_PASS",
                    f"the pinned prior non-pass receipt {prior_path!r} is missing",
                )
            elif sha256_file(path) != prior_sha:
                _fail(
                    failures,
                    "C4_TIMEOUT_AS_PASS",
                    f"the pinned prior non-pass receipt {prior_path!r} was rewritten",
                )
    report_path = dig(schema_doc, "s03_isolation.evaluation_report_path")
    if isinstance(report_path, str):
        try:
            path = resolve_repo_path(root, report_path, "s03_isolation.evaluation_report_path")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
        else:
            if path.exists():
                _fail(
                    failures,
                    "REPORT_WITHOUT_HUMAN_DATA",
                    f"{report_path!r} exists: an S03 evaluation report is not an S04 output",
                )
    if S03_TOKEN_RE.search(json.dumps(receipt, sort_keys=True)):
        _fail(
            failures,
            "S03_RATE_IMPORTED",
            "the receipt references the S03 evaluation contour",
        )


def check_contract_live(
    receipt: dict[str, Any], schema_doc: dict[str, Any], root: Path, failures: Failures
) -> None:
    path = receipt["contract"].get("path")
    if not isinstance(path, str):
        return
    try:
        contract_path = resolve_repo_path(root, path, "contract.path")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    if contract_path.is_file() and sha256_file(contract_path) != receipt["contract"].get("sha256"):
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"{path!r} no longer hashes to the recorded contract pin",
        )


def validate_receipt(receipt: Any, root: Path, schema_doc: dict[str, Any]) -> Failures:
    failures: Failures = []
    if not isinstance(receipt, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "the receipt must be a JSON object")
        return failures
    check_schema_pins(schema_doc, failures)
    try:
        contract = schema_contract(schema_doc)
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return failures
    if not check_shape(receipt, contract, failures):
        return failures
    check_identity(receipt, failures)
    check_argv(receipt, failures)
    check_binding(receipt, failures)
    check_pins(receipt, schema_doc, failures)
    check_wall_clock(receipt, failures)
    check_terminal(receipt, failures)
    check_logs(receipt, contract, root, failures)
    check_corpus(receipt, schema_doc, root, failures)
    check_contract_live(receipt, schema_doc, root, failures)
    check_frozen_lineage(receipt, schema_doc, root, failures)
    non_claims = receipt.get("non_claims")
    if (
        not isinstance(non_claims, list)
        or not non_claims
        or not all(isinstance(item, str) and item.strip() for item in non_claims)
    ):
        _fail(failures, "C4_RECEIPT_DRIFT", "non_claims must be a non-empty list of strings")
    return failures


def report(failures: Failures, marker: str, gate: str) -> int:
    if not failures:
        print(marker)
        return 0
    seen: set[str] = set()
    for diagnostic, detail in failures:
        line = f"{diagnostic}: {detail}"
        if line in seen:
            continue
        seen.add(line)
        print(f"FAIL {line}", file=sys.stderr)
    print(f"FAIL {gate}: {len(seen)} finding(s); the receipt is not admissible", file=sys.stderr)
    return 1


def resolve_receipt_path(args: argparse.Namespace, root: Path, schema_doc: Any) -> Path:
    if args.receipt:
        candidate = Path(args.receipt)
        return candidate if candidate.is_absolute() else root / candidate
    return resolve_repo_path(root, default_receipt_rel(schema_doc), "receipt_path")


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        schema_doc = load_json(root / args.schemas, "S04 schemas document")
        receipt_path = resolve_receipt_path(args, root, schema_doc)
    except GateError as exc:
        return report([(exc.diagnostic, exc.detail)], MARKER, GATE_NAME)
    if not receipt_path.is_file():
        return report(
            [("C4_RECEIPT_MISSING", f"no receipt at {receipt_path.as_posix()}")],
            MARKER,
            GATE_NAME,
        )
    try:
        receipt = load_json(receipt_path, "S04 C4 receipt")
    except GateError as exc:
        return report([(exc.diagnostic, exc.detail)], MARKER, GATE_NAME)
    return report(validate_receipt(receipt, root, schema_doc), MARKER, GATE_NAME)


# --------------------------------------------------------------------------- #
# Negative proof: hostile receipts and planted trees must name their diagnostic
# --------------------------------------------------------------------------- #

Mutator = Callable[[dict[str, Any]], None]
FsCase = Callable[[Path, dict[str, Any], dict[str, Any]], Failures]


def _set_acceptance_pass(receipt: dict[str, Any]) -> None:
    receipt["claims"]["operational_acceptance"] = "pass"


def _drop_required_key(receipt: dict[str, Any]) -> None:
    receipt.pop("budget_seconds")


def _extra_root_key(receipt: dict[str, Any]) -> None:
    receipt["gold"] = False


def _extra_nested_key(receipt: dict[str, Any]) -> None:
    receipt["terminal"]["signal_name"] = "SIGTERM"


def _mutate_identity(receipt: dict[str, Any]) -> None:
    receipt["immutable_attempt_identity"]["argv_sha256"] = "0" * 64


def _mutate_argv_limit(receipt: dict[str, Any]) -> None:
    receipt["argv"] = [*receipt["argv"], "--limit", "1000"]
    receipt["immutable_attempt_identity"]["argv_sha256"] = argv_sha256(receipt["argv"])


def _mutate_corpus_count(receipt: dict[str, Any]) -> None:
    receipt["corpus"]["consultant_xml_count"] = 1


def _mutate_budget(receipt: dict[str, Any]) -> None:
    receipt["budget_seconds"] = 60


def _mutate_outcome(receipt: dict[str, Any]) -> None:
    receipt["terminal"]["outcome"] = "banana"


def _mutate_timeout_laundered(receipt: dict[str, Any]) -> None:
    receipt["terminal"] = {
        "outcome": "timeout",
        "exit_code": None,
        "signal": "SIGTERM",
        "timeout": True,
    }
    receipt["claims"]["operational_acceptance"] = "pass"


def _mutate_log_hash_missing(receipt: dict[str, Any]) -> None:
    receipt["logs"]["stderr_sha256"] = None


def _mutate_binary_digest_prefix(receipt: dict[str, Any]) -> None:
    receipt["binary"]["sha256"] = "sha256:" + receipt["binary"]["sha256"]


def _mutate_contract_digest_prefix(receipt: dict[str, Any]) -> None:
    receipt["contract"]["sha256"] = "sha256:" + receipt["contract"]["sha256"]


def _mutate_binary_hash(receipt: dict[str, Any]) -> None:
    receipt["build_inputs"]["binary_sha256"] = "0" * 64


def _mutate_toolchain(receipt: dict[str, Any]) -> None:
    receipt["toolchain"]["commands_exit_code"] = {"rustc": 1, "cargo": 0}


def _mutate_source_revision(receipt: dict[str, Any]) -> None:
    receipt["source_revision"] = "sha256:" + "1" * 64


def _mutate_duration(receipt: dict[str, Any]) -> None:
    receipt["duration_ms"] = 0


def _mutate_log_path(receipt: dict[str, Any]) -> None:
    receipt["logs"]["stdout"] = "../outside/stdout.log"


def _mutate_s03_reference(receipt: dict[str, Any]) -> None:
    receipt["non_claims"] = [*receipt["non_claims"], "imported from m207-s03 rates"]


def _mutate_audit_note(receipt: dict[str, Any]) -> None:
    receipt["audit_note"] = "gold: the walk is accepted"


DOC_CASES: tuple[tuple[str, str, Mutator], ...] = (
    ("acceptance-laundered", "C4_RECEIPT_DRIFT", _set_acceptance_pass),
    ("required-key-dropped", "SCHEMA_KEY_DRIFT", _drop_required_key),
    ("gold-claim-key", "SCHEMA_KEY_DRIFT", _extra_root_key),
    ("nested-closure-drift", "SCHEMA_KEY_DRIFT", _extra_nested_key),
    ("identity-rebuilt", "IMMUTABLE_IDENTITY_MISSING", _mutate_identity),
    ("argv-limit", "ARGV_PIN_DRIFT", _mutate_argv_limit),
    ("corpus-count", "CORPUS_COUNT_DRIFT", _mutate_corpus_count),
    ("budget-floor", "BUDGET_BELOW_MINIMUM", _mutate_budget),
    ("outcome-vocabulary", "TERMINAL_OUTCOME_DRIFT", _mutate_outcome),
    ("timeout-as-pass", "C4_TIMEOUT_AS_PASS", _mutate_timeout_laundered),
    ("log-hash-missing", "LOG_HASH_MISSING", _mutate_log_hash_missing),
    ("binary-digest-prefix", "BINARY_HASH_MISSING", _mutate_binary_digest_prefix),
    ("contract-digest-prefix", "C4_RECEIPT_DRIFT", _mutate_contract_digest_prefix),
    ("binary-hash-mismatch", "BINARY_HASH_MISSING", _mutate_binary_hash),
    ("toolchain-pin", "TOOLCHAIN_PIN_MISSING", _mutate_toolchain),
    ("source-revision-digest", "SOURCE_REVISION_MISSING", _mutate_source_revision),
    ("duration-missing", "DURATION_MISSING", _mutate_duration),
    ("log-path-escape", "UNSAFE_PATH", _mutate_log_path),
    ("s03-rate-import", "S03_RATE_IMPORTED", _mutate_s03_reference),
    ("audit-note-claim", "SCHEMA_KEY_DRIFT", _mutate_audit_note),
)


def _fs_log_tampered(_root: Path, receipt: dict[str, Any], schema_doc: dict[str, Any]) -> Failures:
    """A log rewritten after the attempt no longer hashes to the recorded digest."""
    with tempfile.TemporaryDirectory(prefix="m207-s04-c4-log-") as tmp:
        tmp_root = Path(tmp)
        for field in ("stdout", "stderr"):
            target = tmp_root / receipt["logs"][field]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("tampered-after-the-fact\n", encoding="utf-8")
        return validate_receipt(copy.deepcopy(receipt), tmp_root, schema_doc)


def _fs_prior_rewritten(
    root: Path, receipt: dict[str, Any], schema_doc: dict[str, Any]
) -> Failures:
    """The pinned M204/S06 non-pass rewritten into a completion."""
    prior_rel = dig(schema_doc, "prior_non_pass_pin.path")
    source = root / str(prior_rel)
    if not source.is_file():
        return [("MISSING_ARTIFACT", "selftest could not read the pinned prior receipt")]
    with tempfile.TemporaryDirectory(prefix="m207-s04-c4-prior-") as tmp:
        tmp_root = Path(tmp)
        target = tmp_root / str(prior_rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        rewritten = json.loads(source.read_text(encoding="utf-8"))
        rewritten["terminal"] = {
            "outcome": "complete",
            "exit_code": 0,
            "signal": None,
            "timeout": False,
        }
        rewritten["claims"]["operational_acceptance"] = "pass"
        target.write_text(json.dumps(rewritten), encoding="utf-8")
        return validate_receipt(copy.deepcopy(receipt), tmp_root, schema_doc)


def _fs_report_planted(
    _root: Path, receipt: dict[str, Any], schema_doc: dict[str, Any]
) -> Failures:
    """An S03 evaluation report planted while the pilot never ran."""
    report_rel = dig(schema_doc, "s03_isolation.evaluation_report_path")
    with tempfile.TemporaryDirectory(prefix="m207-s04-c4-report-") as tmp:
        tmp_root = Path(tmp)
        plant = tmp_root / str(report_rel)
        plant.parent.mkdir(parents=True, exist_ok=True)
        plant.write_text("{}\n", encoding="utf-8")
        return validate_receipt(copy.deepcopy(receipt), tmp_root, schema_doc)


def _fs_receipt_absent(
    root: Path, _receipt: dict[str, Any], _schema_doc: dict[str, Any]
) -> Failures:
    """An absent receipt is C4_RECEIPT_MISSING, never a reconstructed success."""
    try:
        load_json(root / "prd/migration/rust-evidence/m207-s04-c4-missing-probe.json", "receipt")
    except GateError as exc:
        return [(exc.diagnostic, exc.detail)]
    return []


FS_CASES: tuple[tuple[str, str, FsCase], ...] = (
    ("live-log-tampered", "C4_RECEIPT_DRIFT", _fs_log_tampered),
    ("live-prior-rewritten", "C4_TIMEOUT_AS_PASS", _fs_prior_rewritten),
    ("live-report-planted", "REPORT_WITHOUT_HUMAN_DATA", _fs_report_planted),
    ("live-receipt-absent", "MISSING_ARTIFACT", _fs_receipt_absent),
)


def run_selftest(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    problems: list[str] = []
    try:
        schema_doc = load_json(root / args.schemas, "S04 schemas document")
        receipt_path = resolve_receipt_path(args, root, schema_doc)
        receipt = load_json(receipt_path, "S04 C4 receipt")
    except GateError as exc:
        print(f"FAIL SELFTEST_BASELINE: {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        print(f"FAIL {GATE_NAME}_SELFTEST: the baseline receipt is absent", file=sys.stderr)
        return 1
    baseline = validate_receipt(receipt, root, schema_doc)
    if baseline:
        problems.append(
            "selftest baseline is not green: "
            + ", ".join(sorted({diagnostic for diagnostic, _ in baseline}))
        )
    for name, diagnostic, mutator in DOC_CASES:
        mutated = copy.deepcopy(receipt)
        mutator(mutated)
        seen = {diag for diag, _ in validate_receipt(mutated, root, schema_doc)}
        if diagnostic not in seen:
            problems.append(
                f"hostile case {name!r} did not raise {diagnostic} (saw {sorted(seen) or 'nothing'})"
            )
    for name, diagnostic, runner in FS_CASES:
        seen = {diag for diag, _ in runner(root, receipt, schema_doc)}
        if diagnostic not in seen:
            problems.append(
                f"hostile case {name!r} did not raise {diagnostic} (saw {sorted(seen) or 'nothing'})"
            )
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(
            f"FAIL {SELFTEST_MARKER}: {len(problems)} hostile path(s) not proven",
            file=sys.stderr,
        )
        return 1
    print(SELFTEST_MARKER)
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["run", "check", "selftest"],
        help="'run' launches the pinned walk; 'check' validates the receipt read-only; "
        "'selftest' proves the hostile paths",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="frozen S04 schema document")
    parser.add_argument("--receipt", default=None, help="receipt path relative to the root")
    parser.add_argument("--binary", default=DEFAULT_BINARY_REL, help="release diagnostic binary")
    parser.add_argument(
        "--consultant-root", default=DEFAULT_CONSULTANT_REL, help="declared consultant corpus root"
    )
    parser.add_argument("--garant-root", default=DEFAULT_GARANT_REL, help="declared Garant root")
    parser.add_argument("--contract", default=DEFAULT_CONTRACT_REL, help="acceptance contract")
    parser.add_argument(
        "--parser-source",
        default=DEFAULT_PARSER_SOURCE_REL,
        help="parser source holding the revision",
    )
    parser.add_argument("--attempt-id", default=DEFAULT_ATTEMPT_ID)
    parser.add_argument("--profile", default=FROZEN_PROFILE)
    parser.add_argument("--jobs", type=int, default=FROZEN_JOBS)
    parser.add_argument("--budget-seconds", type=int, default=FROZEN_BUDGET_SECONDS_MINIMUM)
    parser.add_argument("--source-revision", default=DEFAULT_SOURCE_REVISION)
    parser.add_argument("--out", default=None, help="receipt path override (successor attempts)")
    parser.add_argument(
        "--resume-orphan-logs",
        action="store_true",
        help="reuse a non-empty attempt log directory whose attempt published no receipt",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"MISSING_ARTIFACT: root {root} is not a directory", file=sys.stderr)
        return 2
    if args.mode == "run":
        return cmd_run(args)
    if args.mode == "selftest":
        return run_selftest(args)
    return cmd_check(args)


if __name__ == "__main__":
    raise SystemExit(main())
