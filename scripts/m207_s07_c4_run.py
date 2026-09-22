#!/usr/bin/env python3
"""Read-only classifier and recomputable predicate engine for M207 S07 (T02).

The frozen S04 receipt is an honest ``non-pass``: under the frozen M204/S06 acceptance rule a walk
counts only when ``duration_ms >= budget_seconds * 1000``, so a corpus walk that finished in
387 s is labelled ``non-pass`` even though it walked the whole corpus.  That rule is not repaired
here -- it is frozen bytes (``scripts/m207_s04_c4_run.py`` is never imported).  The successor
contract ``m207-s07-c4-operational-successor/v1`` is built beside it, and this module is the
read-only half of that contract:

* ``predicate_full_walk`` and ``predicate_timeout`` are two independent predicates recomputed from
  the receipt's terminal facts plus the attempt JSONL -- never from ``claims``;
* ``classify`` composes them into the closed outcome set ``full_walk | timeout | nonzero |
  launch_error``;
* ``classify`` (the CLI command) re-classifies the two historical receipts byte-for-byte, with a
  sha256 taken before and after, so "the new predicate is proven on the old bytes" is a fact about
  the frozen files rather than a story about them.

What this tool may and may not say:

* ``duration_ms`` is recorded and is **not** an input to any predicate.  A complete walk that
  finished faster than the budget floor is a lawful ``full_walk``; reading a short duration as a
  timeout (or as acceptance) is ``DURATION_FLOOR_AS_ACCEPTANCE``;
* ``claims.operational_acceptance`` is read and echoed for comparison only.  The verdict is
  recomputed from ``terminal.*`` and the JSONL; a claim never sets it (R038);
* ``operational_envelope.run_status`` is **not** terminal evidence: the Rust renderer writes the
  literal ``"complete"`` before the harness observes the process (D444), so the classifier never
  reads it;
* nothing is written.  No receipt, no log, no sidecar, no report; the classification exists on
  stdout and the refusal exists on stderr.  A byte that moves under the read is
  ``HISTORICAL_BYTES_CHANGED``, not a new verdict;
* the marker ``M207_S07_CLASSIFY_OK`` means "the historical bytes were classified read-only and
  the diagnostic vocabulary matches the frozen protocol".  It is not acceptance, not gold, not a
  promotion, and it does not close R038.

The diagnostic vocabulary is the protocol's closed block, checked in both directions: every code
this tool can emit must be declared in ``prd/annotation/m207-s07-c4-protocol.md`` between the
``s07-diagnostics`` markers and in the schema's ``diagnostics`` array, and the protocol block must
not carry a code this tool does not know (``PROTOCOL_DIAGNOSTIC_DRIFT``).

The other half of the same contract is the *recorder* (``run``), the write-once publisher of one
new attempt, and the read-only gate over its receipt (``check``):

* the historical S04 argv never carried ``--failures-out``, so the file behind its single
  ``failed = 1`` is unpublished and unrecoverable.  A new attempt is therefore a **new identity**:
  same corpus pin and same kill ceiling, but a new argv (which changes ``argv_sha256``), a new
  ``attempt_id`` and a new receipt under ``prd/migration/rust-evidence/m207-s07-*`` (MEM1608).
  No frozen S04/M204 byte, claim or path is edited or overwritten -- the frozen paths are refused
  by name (``C4_RECEIPT_DRIFT``) and both the receipt and the sidecar are write-once;
* ``run --dry-run`` prints the staged argv, the receipt path, the attempt directory, the corpus
  counts, ``argv_sha256`` and the predicate preview, prints ``M207_S07_C4_DRYRUN_OK`` and creates
  no file and no directory at all.  It is the cheapest honest anchor that the argv carries
  ``--failures-out`` and never ``--limit``;
* the receipt is published only after the terminal facts are known, and it carries no
  ``operational_acceptance`` key at all: ``claims.operational_classification`` is the successor
  outcome and ``acceptance_effect`` is ``none``.  A moved ``promotion`` is ``PROMOTION_CLAIM`` and a
  moved ``is_gold`` / ``human_acceptance`` is ``GOLD_CLAIM``;
* ``predicates`` is recomputed from the receipt's own terminal facts plus the attempt JSONL it just
  wrote (the same engine as ``classify``); a recorded value that disagrees with the recomputation
  is ``PREDICATE_CONTRADICTION``, and ``duration_ms`` is swept across the whole range in ``check``
  to prove it is not a predicate input (``DURATION_FLOOR_AS_ACCEPTANCE`` if the verdict moves);
* the failure sidecar ``npa-contour-failure-trace/v1`` is reused verbatim via ``--failures-out``:
  its closed key set, provider/class allowlists and provider-root-relative paths are validated, and
  its row count is compared with this attempt's own ``aggregate.failed``.  A missing sidecar is
  lawful (recorded as ``sidecar_rows: 0``); an unwritable one is the Rust exit-3 allowlist refusal
  and stays a lawful ``nonzero``.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import os
import re
import shutil
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

MARKER = "M207_S07_CLASSIFY_OK"
SELFTEST_MARKER = "M207_S07_C4_CLASSIFY_SELFTEST_OK"
GATE_NAME = "M207_S07_C4_CLASSIFY"

RECORDER_MARKER = "M207_S07_C4_RECEIPT_OK"
DRY_RUN_MARKER = "M207_S07_C4_DRYRUN_OK"
RECORDER_SELFTEST_MARKER = "M207_S07_C4_RECORDER_SELFTEST_OK"
RECORDER_GATE_NAME = "M207_S07_C4_RECORDER"
SIDECAR_SCHEMA_ID = "npa-contour-failure-trace/v1"

PROTOCOL_ID = "m207-s07-c4-protocol/v1"
SCHEMAS_ID = "m207-s07-schemas/v1"
RECEIPT_SCHEMA_ID = "m207-s07-c4-operational-successor/v1"
CLASSIFICATION_SCHEMA_ID = "m207-s07-c4-classification/v1"
PROTOCOL_REL = "prd/annotation/m207-s07-c4-protocol.md"
SCHEMAS_REL = "prd/annotation/m207-s07-schemas.json"

# The two historical receipts the successor contract classifies.  Both are frozen bytes: their
# sha256 is declared in the schema's ``frozen_sources`` and re-checked around every read.
KEY_S04 = "m207_s04_c4_operational_receipt"
KEY_M204 = "m204_s06_c4_operational_receipt"
CLASSIFY_SOURCE_KEYS = (KEY_S04, KEY_M204)

TERMINAL_OUTCOME_VALUES = ("complete", "timeout", "nonzero", "launch_error")
OUTCOME_VALUES = ("full_walk", "timeout", "nonzero", "launch_error")

PIN_CONSULTANT_XML_COUNT = 43785
PIN_GARANT_FILE_COUNT = 12
PIN_AGGREGATE_FILES = 43797
BUDGET_SECONDS_MINIMUM = 3600

# --- recorder: one new attempt under a new identity --------------------------
DEFAULT_BINARY_REL = "target/release/npa-contour-diagnostics"
DEFAULT_CONSULTANT_REL = "consru_export/consru_export/exports"
DEFAULT_GARANT_REL = "law-source/garant"
DEFAULT_CONTRACT_REL = "prd/architecture/npa-acceptance-contract.yaml"
DEFAULT_PARSER_SOURCE_REL = "crates/ln-consultant-parser/src/contour_diagnostics.rs"
DEFAULT_RECEIPT_REL = "prd/migration/rust-evidence/m207-s07-c4-operational-receipt.json"
ATTEMPT_DIR_REL = "prd/migration/rust-evidence/m207-s07-c4-attempts"
EVIDENCE_DIR_REL = "prd/migration/rust-evidence"
CONSULTANT_XML_SUFFIX = ".xml"
CONTRACT_VERSION = "npa-acceptance-contract/v1"
INVENTORY_SCOPE = "consultant XML plus separate Garant files"
FROZEN_PROFILE = "contour"
FROZEN_JOBS = 0
FROZEN_LOG_FILES = ("stdout.log", "stderr.log")
SIDECAR_FILENAME = "failures.jsonl"
SIDECAR_KEYS = ("record_kind", "schema", "provider", "path", "class")
SIDECAR_ARG = "--failures-out"
KILL_GRACE_SECONDS = 30
DEFAULT_ATTEMPT_ID = "m207-s07-c4-full-walk-001"
DEFAULT_SOURCE_REVISION = "m207-s07-c4-caller-pin-2026-09-22"
ARGV_REQUIRED_FLAGS = (
    "--root",
    "--garant-root",
    "--profile",
    "--jobs",
    "--acceptance-contract",
    "--source-revision",
    "--failures-out",
)
ARGV_FORBIDDEN_FLAGS = ("--limit",)
ISO_SECONDS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ATTEMPT_ID_RE = re.compile(r"^m207-s07-[a-z0-9]+(-[a-z0-9]+)*-[0-9]{3}$")

# The closed receipt closure.  ``operational_acceptance`` is deliberately absent: the successor
# receipt classifies an attempt and never accepts it.
RECEIPT_KEYS = (
    "schema",
    "attempt_id",
    "immutable_attempt_identity",
    "argv",
    "binary",
    "build_inputs",
    "toolchain",
    "parser_revision",
    "source_revision",
    "contract",
    "corpus",
    "observed_output",
    "binding",
    "started_at",
    "finished_at",
    "duration_ms",
    "budget_seconds",
    "terminal",
    "logs",
    "failure_policy",
    "predicates",
    "claims",
    "non_claims",
)
RECEIPT_NESTED_KEYS: dict[str, tuple[str, ...]] = {
    "immutable_attempt_identity": ("attempt_id", "argv_sha256"),
    "binary": ("path", "sha256"),
    "build_inputs": (
        "binary_sha256",
        "parser_source_sha256",
        "protocol_sha256",
        "schemas_sha256",
    ),
    "toolchain": ("rustc", "cargo", "commands_exit_code"),
    "contract": ("path", "sha256", "version"),
    "corpus": ("consultant_xml_count", "consultant_root", "garant_file_count", "garant_root"),
    "observed_output": ("stdout_sha256", "inventory_digest"),
    "binding": ("profile", "limit", "jobs", "inventory_scope"),
    "logs": ("stdout", "stderr", "stdout_sha256", "stderr_sha256", "inventory_digest"),
    "failure_policy": (
        "failures_out_path",
        "failures_sha256",
        "sidecar_rows",
        "aggregate_failed",
        "acceptance_effect",
    ),
    "predicates": ("full_walk", "timeout", "outcome"),
    "claims": ("operational_classification", "acceptance_effect", "receipt_is_runtime_attempt"),
}
RECEIPT_TERMINAL_KEYS = ("outcome", "exit_code", "signal", "timeout")
RECEIPT_TERMINAL_OPTIONAL_KEYS = ("error",)
RECEIPT_FORBIDDEN_ACCEPTANCE_KEYS = ("operational_acceptance", "acceptance")
RECEIPT_FORBIDDEN_PROMOTION_KEYS = (
    "promotion",
    "classification",
    "model_invoked",
    "legal_claim",
    "rate_publication",
)
RECEIPT_FORBIDDEN_GOLD_KEYS = ("is_gold", "human_acceptance", "threshold")

SUCCESSOR_NON_CLAIMS = [
    "not an acceptance: the successor receipt classifies an attempt and publishes no verdict",
    "not gold: no S07 receipt, predicate or sidecar row is a gold label",
    "not a promotion: promotion stays none and classification stays not-authorized",
    "not a rewrite of S04/M204: the frozen receipt, its logs and its non-pass claim stay byte-identical",
    "not a duration floor: a short complete walk is a lawful full walk and duration_ms is never a predicate input",
    "not a budget achievement: budget_seconds is a kill ceiling, never evidence the envelope was exercised",
    "not a failure identity for the historical run: the S04 failed = 1 file stays unidentified",
    "not a product surface: S07 is an offline Python harness and crates/** gains no reader",
    "not a requirement status change: status_effect stays unchanged and R035/R070 stay HOLD",
    "not a rate publication: no aspect rate, stratum rate or measurement_status is imported",
]

DIGEST_FORMAT = "bare lowercase hex sha256, no algorithm prefix"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

DIAGNOSTICS_BEGIN = "<!-- s07-diagnostics:begin -->"
DIAGNOSTICS_END = "<!-- s07-diagnostics:end -->"
_DIAGNOSTIC_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

# The closed vocabulary of the successor contract.  It is the union of the schema gate's codes and
# the classifier/recorder/policy codes, and it must equal the protocol marker block (step 6).
DIAGNOSTIC_CODES = (
    "USAGE",
    "SCHEMA_PARSE_ERROR",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_VERSION_DRIFT",
    "MISSING_INPUT",
    "MALFORMED_RECEIPT",
    "C4_RECEIPT_DRIFT",
    "HISTORICAL_BYTES_CHANGED",
    "CORPUS_COUNT_DRIFT",
    "ARGV_PIN_DRIFT",
    "BUDGET_BELOW_MINIMUM",
    "TERMINAL_OUTCOME_DRIFT",
    "PREDICATE_CONTRADICTION",
    "DURATION_FLOOR_AS_ACCEPTANCE",
    "PROTOCOL_DIAGNOSTIC_DRIFT",
    "MISSING_SIDECAR",
    "SIDECAR_UNEXPECTED",
    "SIDECAR_COUNT_MISMATCH",
    "SIDECAR_KEY_DRIFT",
    "SIDECAR_PROVIDER_DRIFT",
    "SIDECAR_CLASS_DRIFT",
    "SIDECAR_PATH_ESCAPE",
    "ALLOWLIST_REFUSAL",
    "PROMOTION_CLAIM",
    "GOLD_CLAIM",
    "S03_RATE_IMPORT",
    "SEED_ENLARGE",
    "ATTEMPT_LOG_MISSING",
    "SUBCLI_FAILURE",
    "MISSING_MARKER",
    "MISSING_ARTIFACT",
    "MISSING_SECTION",
    "UNSAFE_PATH",
    "MARKER_CONTRACT_DRIFT",
    "GATE_INTERNAL_ERROR",
)

# The schema must declare the same predicate constants this module recomputes with; a disagreement
# is drift, not a locally-owned tuning knob.
SCHEMA_FULL_WALK_PINS: dict[str, Any] = {
    "requires_no_limit_flag": True,
    "header_limit_is_null": True,
    "canonical_payload_limit_is_null": True,
    "corpus_consultant_xml_count": PIN_CONSULTANT_XML_COUNT,
    "corpus_garant_file_count": PIN_GARANT_FILE_COUNT,
    "aggregate_files_equals": PIN_AGGREGATE_FILES,
    "terminal_outcome": "complete",
    "terminal_exit_code": 0,
    "terminal_timeout": False,
    "terminal_signal_is_null": True,
}
SCHEMA_TIMEOUT_PINS: dict[str, Any] = {
    "terminal_outcome": "timeout",
    "terminal_exit_code_is_null": True,
    "terminal_signal": "SIGTERM",
    "terminal_timeout": True,
}
SCHEMA_PREDICATE_FLAGS: dict[str, Any] = {
    "duration_ms_is_recorded": True,
    "duration_ms_is_not_a_predicate_input": True,
    "duration_floor_is_not_acceptance": True,
    "short_complete_is_lawful_full_walk": True,
    "budget_seconds_is_a_kill_ceiling": True,
    "budget_seconds_minimum": BUDGET_SECONDS_MINIMUM,
    "outcome_is_recomputed_not_read_from_a_claim": True,
    "run_status_is_not_terminal_evidence": True,
}
DURATION_FLOOR_FLAGS = (
    "duration_ms_is_not_a_predicate_input",
    "duration_floor_is_not_acceptance",
)

# Keys that would turn the read-only classification into a verdict it has no authority to publish.
ACCEPTANCE_FORBIDDEN_KEYS = (
    "operational_acceptance",
    "acceptance",
    "promotion",
    "classification",
    "is_gold",
    "human_acceptance",
    "threshold",
    "model_invoked",
)


class GateError(Exception):
    """Fatal, named failure that stops the tool before it publishes anything."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalise_digest(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value[7:] if value.startswith("sha256:") else value
    return raw if HEX64_RE.match(raw) else None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate object key {key!r}")
        seen[key] = value
    return seen


def _decode_text(path: Path, label: str) -> str:
    if not path.is_file():
        raise GateError("MISSING_INPUT", f"{label} not found at {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("MALFORMED_RECEIPT", f"{label} is not UTF-8: {exc}") from exc


def load_json(path: Path, label: str) -> Any:
    """Read one JSON document read-only: missing -> MISSING_INPUT, broken -> MALFORMED_RECEIPT."""
    text = _decode_text(path, label)
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as exc:
        raise GateError("MALFORMED_RECEIPT", f"{label} is not valid JSON: {exc}") from exc


def load_jsonl(path: Path, label: str = "attempt stdout JSONL log") -> list[dict[str, Any]]:
    """Read an attempt JSONL log read-only.  Blank lines are skipped, a broken row is fatal."""
    text = _decode_text(path, label)
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except ValueError as exc:
            raise GateError(
                "MALFORMED_RECEIPT",
                f"attempt stdout JSONL line {number} is not valid JSON: {exc}",
            ) from exc
        if not isinstance(row, dict):
            raise GateError(
                "MALFORMED_RECEIPT",
                f"attempt stdout JSONL line {number} is not a JSON object",
            )
        rows.append(row)
    return rows


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def argv_sha256(argv: list[str]) -> str:
    payload = json.dumps(list(argv), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def display_under(root: Path, path: Path) -> str:
    """Render a path relative to the declared root, without following symlinks.

    The receipt records paths *as the declared root names them*, so a symlinked corpus root is
    recorded as the relative path the operator declared rather than as its real location.
    """
    root_abs = Path(os.path.abspath(root))
    candidate = Path(os.path.abspath(path))
    try:
        return candidate.relative_to(root_abs).as_posix()
    except ValueError:
        return candidate.as_posix()


def count_files(root: Path, suffix: str) -> int:
    return sum(1 for path in root.rglob(f"*{suffix}") if path.is_file())


def count_all_files(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file())


def resolve_repo_path(root: Path, raw: Any, label: str) -> Path:
    """Resolve a repository-relative path under the declared root, fail-closed on escapes."""
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
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must not escape the repository root")
    root_abs = Path(os.path.abspath(root))
    candidate = Path(os.path.abspath(root_abs / relative))
    if candidate != root_abs and root_abs not in candidate.parents:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_abs}")
    return candidate


# --------------------------------------------------------------------------- #
# Predicate engine
# --------------------------------------------------------------------------- #


def _row_for(rows: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    matches = [row for row in rows if row.get("record_kind") == kind]
    if len(matches) > 1:
        raise GateError(
            "MALFORMED_RECEIPT",
            f"attempt JSONL carries {len(matches)} {kind!r} rows, expected at most one",
        )
    return matches[0] if matches else None


def aggregate_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row = _row_for(rows, "aggregate")
    if row is None:
        raise GateError("MALFORMED_RECEIPT", "attempt JSONL carries no 'aggregate' row")
    return row


def canonical_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row = _row_for(rows, "canonical_payload")
    if row is None:
        raise GateError("MALFORMED_RECEIPT", "attempt JSONL carries no 'canonical_payload' row")
    return row


def predicate_full_walk(receipt: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute ``full_walk`` from the receipt's terminal facts and the attempt JSONL.

    No duration term takes part: a short complete walk over the pinned corpus is a full walk.
    """
    reasons: list[str] = []
    if not isinstance(receipt, dict):
        return {"full_walk": False, "reasons": ["receipt is not a JSON object"]}

    argv = receipt.get("argv")
    if not isinstance(argv, list):
        reasons.append("receipt.argv is not a list")
    elif "--limit" in argv:
        reasons.append("receipt.argv carries --limit")

    header = _row_for(rows, "header")
    canonical = _row_for(rows, "canonical_payload")
    aggregate = _row_for(rows, "aggregate")

    if header is None:
        reasons.append("attempt JSONL carries no 'header' row")
    elif header.get("limit") is not None:
        reasons.append("header.limit is not JSON null")
    if canonical is None:
        reasons.append("attempt JSONL carries no 'canonical_payload' row")
    elif canonical.get("limit") is not None:
        reasons.append("canonical_payload.limit is not JSON null")

    corpus = receipt.get("corpus")
    if not isinstance(corpus, dict):
        reasons.append("receipt.corpus is not an object")
    else:
        if corpus.get("consultant_xml_count") != PIN_CONSULTANT_XML_COUNT:
            reasons.append(
                f"corpus.consultant_xml_count is {corpus.get('consultant_xml_count')!r}, "
                f"pinned {PIN_CONSULTANT_XML_COUNT}"
            )
        if corpus.get("garant_file_count") != PIN_GARANT_FILE_COUNT:
            reasons.append(
                f"corpus.garant_file_count is {corpus.get('garant_file_count')!r}, "
                f"pinned {PIN_GARANT_FILE_COUNT}"
            )

    if aggregate is None:
        reasons.append("attempt JSONL carries no 'aggregate' row")
    elif aggregate.get("files") != PIN_AGGREGATE_FILES:
        reasons.append(
            f"aggregate.files is {aggregate.get('files')!r}, pinned {PIN_AGGREGATE_FILES}"
        )

    terminal = receipt.get("terminal")
    if not isinstance(terminal, dict):
        reasons.append("receipt.terminal is not an object")
    else:
        if terminal.get("outcome") != "complete":
            reasons.append(f"terminal.outcome is {terminal.get('outcome')!r}, expected 'complete'")
        if terminal.get("exit_code") != 0:
            reasons.append(f"terminal.exit_code is {terminal.get('exit_code')!r}, expected 0")
        if terminal.get("timeout") is not False:
            reasons.append(f"terminal.timeout is {terminal.get('timeout')!r}, expected false")
        if terminal.get("signal") is not None:
            reasons.append(f"terminal.signal is {terminal.get('signal')!r}, expected null")

    return {"full_walk": not reasons, "reasons": reasons}


def predicate_timeout(receipt: Any) -> dict[str, Any]:
    """Recompute ``timeout`` from the receipt's terminal facts only."""
    reasons: list[str] = []
    if not isinstance(receipt, dict):
        return {"timeout": False, "reasons": ["receipt is not a JSON object"]}
    terminal = receipt.get("terminal")
    if not isinstance(terminal, dict):
        return {"timeout": False, "reasons": ["receipt.terminal is not an object"]}
    if terminal.get("outcome") != "timeout":
        reasons.append(f"terminal.outcome is {terminal.get('outcome')!r}, expected 'timeout'")
    if terminal.get("exit_code") is not None:
        reasons.append(f"terminal.exit_code is {terminal.get('exit_code')!r}, expected null")
    if terminal.get("signal") != "SIGTERM":
        reasons.append(f"terminal.signal is {terminal.get('signal')!r}, expected 'SIGTERM'")
    if terminal.get("timeout") is not True:
        reasons.append(f"terminal.timeout is {terminal.get('timeout')!r}, expected true")
    return {"timeout": not reasons, "reasons": reasons}


def _terminal_view(receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise GateError("MALFORMED_RECEIPT", "receipt is not a JSON object")
    terminal = receipt.get("terminal")
    if not isinstance(terminal, dict):
        raise GateError("MALFORMED_RECEIPT", "receipt.terminal is not a JSON object")
    for key in ("outcome", "exit_code", "signal", "timeout"):
        if key not in terminal:
            raise GateError("MALFORMED_RECEIPT", f"receipt.terminal.{key} is missing")
    outcome = terminal["outcome"]
    exit_code = terminal["exit_code"]
    if not isinstance(outcome, str) or outcome not in TERMINAL_OUTCOME_VALUES:
        raise GateError(
            "TERMINAL_OUTCOME_DRIFT",
            f"terminal.outcome {outcome!r} is outside {list(TERMINAL_OUTCOME_VALUES)}",
        )
    if exit_code is not None and (isinstance(exit_code, bool) or not isinstance(exit_code, int)):
        raise GateError(
            "TERMINAL_OUTCOME_DRIFT",
            f"terminal.exit_code {exit_code!r} must be an integer or JSON null",
        )
    if not isinstance(terminal["timeout"], bool):
        raise GateError(
            "TERMINAL_OUTCOME_DRIFT",
            f"terminal.timeout {terminal['timeout']!r} must be a JSON boolean",
        )
    return dict(terminal)


def _limit_view(receipt: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    header = _row_for(rows, "header")
    canonical = _row_for(rows, "canonical_payload")
    argv = receipt.get("argv") if isinstance(receipt, dict) else None
    return {
        "argv_limit_present": isinstance(argv, list) and "--limit" in argv,
        "header_limit": header.get("limit") if isinstance(header, dict) else None,
        "canonical_payload_limit": canonical.get("limit") if isinstance(canonical, dict) else None,
    }


def _aggregate_view(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    aggregate = _row_for(rows, "aggregate")
    if aggregate is None:
        return None
    return {
        "provider": aggregate.get("provider"),
        "files": aggregate.get("files"),
        "decoded": aggregate.get("decoded"),
        "failed": aggregate.get("failed"),
    }


def _claim_view(receipt: Any) -> Any:
    """Read ``claims.operational_acceptance`` as history, never as a verdict input."""
    if not isinstance(receipt, dict):
        return None
    claims = receipt.get("claims")
    if not isinstance(claims, dict):
        return None
    return claims.get("operational_acceptance")


def assert_no_acceptance_keys(report: dict[str, Any]) -> None:
    """Refuse to publish a classification that carries a verdict this tool has no authority over."""
    for forbidden in ACCEPTANCE_FORBIDDEN_KEYS:
        if forbidden in report:
            raise GateError(
                "DURATION_FLOOR_AS_ACCEPTANCE",
                f"classification must not carry {forbidden!r}: the successor contract publishes "
                "no acceptance, no promotion and no classification verdict",
            )


def classify(receipt: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify one receipt into the closed outcome set, recomputed from terminal facts + JSONL."""
    terminal = _terminal_view(receipt)
    raw_outcome = terminal["outcome"]
    exit_code = terminal["exit_code"]

    # A complete walk that claims exit 0 must carry the JSONL evidence it is judged on.  A timeout
    # or launch error legitimately has a short or empty log.
    if raw_outcome == "complete" and exit_code == 0:
        aggregate_row(rows)
        canonical_row(rows)

    full = predicate_full_walk(receipt, rows)
    timed_out = predicate_timeout(receipt)
    if full["full_walk"] and timed_out["timeout"]:
        raise GateError(
            "PREDICATE_CONTRADICTION",
            "full_walk and timeout are both true for one receipt",
        )

    if raw_outcome == "complete":
        if exit_code != 0:
            raise GateError(
                "TERMINAL_OUTCOME_DRIFT",
                f"a complete walk must exit 0, saw exit_code={exit_code!r}",
            )
        if not full["full_walk"]:
            raise GateError(
                "PREDICATE_CONTRADICTION",
                "terminal is complete with exit_code 0 but full_walk is false: "
                + "; ".join(full["reasons"]),
            )
        outcome = "full_walk"
    elif raw_outcome == "timeout":
        if not timed_out["timeout"]:
            raise GateError(
                "TERMINAL_OUTCOME_DRIFT",
                "terminal.outcome is 'timeout' without the timeout shape: "
                + "; ".join(timed_out["reasons"]),
            )
        outcome = "timeout"
    elif raw_outcome == "nonzero":
        if exit_code in (None, 0):
            raise GateError(
                "TERMINAL_OUTCOME_DRIFT",
                f"a nonzero walk must publish a non-zero exit_code, saw {exit_code!r}",
            )
        if full["full_walk"]:
            raise GateError("PREDICATE_CONTRADICTION", "a nonzero terminal cannot be a full walk")
        outcome = "nonzero"
    else:
        if exit_code is not None:
            raise GateError(
                "TERMINAL_OUTCOME_DRIFT",
                f"a launch error publishes no exit_code, saw {exit_code!r}",
            )
        outcome = "launch_error"

    if outcome not in OUTCOME_VALUES:
        raise GateError("TERMINAL_OUTCOME_DRIFT", f"outcome {outcome!r} is outside the closed set")

    report: dict[str, Any] = {
        "full_walk": bool(full["full_walk"]),
        "timeout": bool(timed_out["timeout"]),
        "outcome": outcome,
        "terminal": terminal,
        "aggregate": _aggregate_view(rows),
        "limits": _limit_view(receipt, rows),
        "claims_operational_acceptance": _claim_view(receipt),
        "duration_ms": receipt.get("duration_ms") if isinstance(receipt, dict) else None,
        "budget_seconds": receipt.get("budget_seconds") if isinstance(receipt, dict) else None,
    }
    assert_no_acceptance_keys(report)
    return report


# --------------------------------------------------------------------------- #
# Contract binding: the tool's vocabulary must equal the frozen protocol's block
# --------------------------------------------------------------------------- #


def parse_protocol_diagnostics(text: str) -> set[str]:
    """Read the closed diagnostic vocabulary between the protocol's machine-readable markers."""
    lines = text.splitlines()
    begins = [index for index, line in enumerate(lines) if line.strip() == DIAGNOSTICS_BEGIN]
    ends = [index for index, line in enumerate(lines) if line.strip() == DIAGNOSTICS_END]
    if len(begins) != 1 or len(ends) != 1:
        raise GateError(
            "PROTOCOL_DIAGNOSTIC_DRIFT",
            f"expected exactly one diagnostic block, begin={len(begins)} end={len(ends)}",
        )
    if ends[0] <= begins[0]:
        raise GateError("PROTOCOL_DIAGNOSTIC_DRIFT", "diagnostic block markers are out of order")
    codes: set[str] = set()
    for line in lines[begins[0] + 1 : ends[0]]:
        stripped = line.strip()
        if not stripped:
            continue
        if not _DIAGNOSTIC_CODE_RE.match(stripped):
            raise GateError(
                "PROTOCOL_DIAGNOSTIC_DRIFT", f"non-code line in diagnostic block: {stripped!r}"
            )
        if stripped in codes:
            raise GateError(
                "PROTOCOL_DIAGNOSTIC_DRIFT", f"duplicate code {stripped!r} in diagnostic block"
            )
        codes.add(stripped)
    if not codes:
        raise GateError("PROTOCOL_DIAGNOSTIC_DRIFT", "diagnostic block is empty")
    return codes


def _compare_code_sets(declared: set[str], label: str) -> None:
    expected = set(DIAGNOSTIC_CODES)
    if declared != expected:
        missing = sorted(expected - declared)
        extra = sorted(declared - expected)
        raise GateError(
            "PROTOCOL_DIAGNOSTIC_DRIFT",
            f"{label} differs from this tool's vocabulary (missing={missing}, extra={extra})",
        )


def check_contract_vocabulary(root: Path, schema: Any) -> None:
    """Bind this tool, the frozen protocol block and the schema's diagnostic array to one set."""
    if not isinstance(schema, dict):
        raise GateError("MISSING_INPUT", "the S07 schema document is not a JSON object")
    protocol_path = root / PROTOCOL_REL
    if not protocol_path.is_file():
        raise GateError("MISSING_INPUT", f"S07 protocol missing at {PROTOCOL_REL}")
    _compare_code_sets(
        parse_protocol_diagnostics(_decode_text(protocol_path, "S07 protocol")), PROTOCOL_REL
    )

    declared = schema.get("diagnostics")
    if not isinstance(declared, list) or not all(isinstance(code, str) for code in declared):
        raise GateError(
            "PROTOCOL_DIAGNOSTIC_DRIFT", "$.diagnostics must be a list of diagnostic codes"
        )
    if len(declared) != len(set(declared)):
        raise GateError("PROTOCOL_DIAGNOSTIC_DRIFT", "$.diagnostics contains duplicate codes")
    _compare_code_sets(set(declared), f"{SCHEMAS_REL} $.diagnostics")

    predicates = schema.get("predicates")
    if not isinstance(predicates, dict):
        raise GateError("PREDICATE_CONTRADICTION", "$.predicates must be a JSON object")
    outcomes = predicates.get("outcomes")
    if not isinstance(outcomes, list) or set(outcomes) != set(OUTCOME_VALUES):
        raise GateError(
            "TERMINAL_OUTCOME_DRIFT",
            f"$.predicates.outcomes is {outcomes!r}, expected {list(OUTCOME_VALUES)}",
        )
    for name, pins in (("full_walk", SCHEMA_FULL_WALK_PINS), ("timeout", SCHEMA_TIMEOUT_PINS)):
        body = predicates.get(name)
        if not isinstance(body, dict):
            raise GateError("PREDICATE_CONTRADICTION", f"$.predicates.{name} must be an object")
        for key, expected in pins.items():
            if body.get(key) != expected:
                raise GateError(
                    "PREDICATE_CONTRADICTION",
                    f"$.predicates.{name}.{key} is {body.get(key)!r}, this tool recomputes {expected!r}",
                )
    for key, expected in SCHEMA_PREDICATE_FLAGS.items():
        actual = predicates.get(key)
        if actual != expected:
            diagnostic = (
                "DURATION_FLOOR_AS_ACCEPTANCE"
                if key in DURATION_FLOOR_FLAGS
                else "PREDICATE_CONTRADICTION"
            )
            raise GateError(
                diagnostic,
                f"$.predicates.{key} is {actual!r}, the frozen contract declares {expected!r}",
            )


def assert_no_frozen_acceptance_rule() -> None:
    """The successor verdict never borrows the frozen S04 duration floor.

    Two executable checks: this module exposes no ``acceptance_for`` symbol and holds no reference
    to the frozen S04 module, so the M204/S06 rule can never be an input to the successor verdict.
    Duration-freedom itself is proven behaviourally in ``selftest``, which sweeps ``duration_ms``
    across the whole range and requires the verdict not to move.
    """
    borrowed = sorted(name for name in globals() if "acceptance_for" in name)
    if borrowed:
        raise GateError(
            "DURATION_FLOOR_AS_ACCEPTANCE",
            f"this module exposes {borrowed}: the frozen S04 acceptance rule is never an input to "
            "the successor verdict",
        )
    imported = sorted(
        name
        for name, value in globals().items()
        if getattr(value, "__name__", None) == "m207_s04_c4_run"
    )
    if imported:
        raise GateError(
            "DURATION_FLOOR_AS_ACCEPTANCE",
            f"this module imports the frozen S04 module as {imported}: the successor verdict is "
            "not computed from the M204/S06 duration floor",
        )


# --------------------------------------------------------------------------- #
# Read-only classification of the frozen historical receipts
# --------------------------------------------------------------------------- #


def _frozen_entry(schema: Any, key: str) -> dict[str, Any]:
    frozen = schema.get("frozen_sources") if isinstance(schema, dict) else None
    if not isinstance(frozen, dict):
        raise GateError("MISSING_INPUT", "$.frozen_sources is missing from the S07 schema")
    entry = frozen.get(key)
    if not isinstance(entry, dict):
        raise GateError("MISSING_INPUT", f"$.frozen_sources[{key}] is missing")
    if not isinstance(entry.get("path"), str):
        raise GateError("MISSING_INPUT", f"$.frozen_sources[{key}].path is missing")
    return entry


def classify_receipt(
    root: Path,
    schema: Any,
    key: str,
    between_reads: Callable[[str, Path], None] | None = None,
) -> dict[str, Any]:
    """Classify one pinned receipt read-only, proving the file did not move under the read.

    ``between_reads`` is a test-only seam used by ``selftest`` to prove the
    ``HISTORICAL_BYTES_CHANGED`` refusal; production callers never pass it.
    """
    entry = _frozen_entry(schema, key)
    path = resolve_repo_path(root, entry["path"], f"frozen_sources[{key}].path")
    pin = normalise_digest(entry.get("sha256"))
    if pin is None:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"$.frozen_sources[{key}].sha256 is not {DIGEST_FORMAT}",
        )
    if not path.is_file():
        raise GateError("MISSING_INPUT", f"frozen receipt for {key} not found at {entry['path']}")
    sha_before = sha256_file(path)
    if sha_before != pin:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{entry['path']} hashes to {sha_before}, pinned {pin}: the historical bytes moved",
        )

    receipt = load_json(path, f"frozen receipt {key}")
    log_path = _log_path(root, receipt, key)
    _check_log_digest(receipt, log_path, key)
    rows = load_jsonl(log_path)
    report = classify(receipt, rows)

    if between_reads is not None:
        between_reads(key, path)

    sha_after = sha256_file(path)
    if sha_after != sha_before:
        raise GateError(
            "HISTORICAL_BYTES_CHANGED",
            f"{entry['path']} changed under the read ({sha_before} -> {sha_after})",
        )
    return {
        "path": entry["path"],
        "sha256_before": sha_before,
        "sha256_after": sha_after,
        "full_walk": report["full_walk"],
        "timeout": report["timeout"],
        "outcome": report["outcome"],
        "terminal": report["terminal"],
        "aggregate": report["aggregate"],
        "limit": report["limits"],
        "claims_operational_acceptance": report["claims_operational_acceptance"],
    }


def _log_path(root: Path, receipt: Any, key: str) -> Path:
    if not isinstance(receipt, dict):
        raise GateError("MALFORMED_RECEIPT", f"{key} receipt is not a JSON object")
    logs = receipt.get("logs")
    if not isinstance(logs, dict) or not isinstance(logs.get("stdout"), str):
        raise GateError("MALFORMED_RECEIPT", f"{key} receipt carries no logs.stdout path")
    return resolve_repo_path(root, logs["stdout"], f"{key} logs.stdout")


def _check_log_digest(receipt: dict[str, Any], log_path: Path, key: str) -> None:
    """Bind the attempt log to the frozen receipt: a swapped log is drift, not new evidence."""
    if not log_path.is_file():
        raise GateError("MISSING_INPUT", f"{key} attempt log missing at {log_path}")
    recorded = normalise_digest(receipt.get("logs", {}).get("stdout_sha256"))
    if recorded is None:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{key} receipt does not bind its stdout log with a {DIGEST_FORMAT} digest",
        )
    actual = sha256_file(log_path)
    if actual != recorded:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{key} stdout log hashes to {actual}, recorded {recorded}: the frozen log moved",
        )


def classify_root(
    root: Path,
    schemas_rel: str = SCHEMAS_REL,
    *,
    between_reads: Callable[[str, Path], None] | None = None,
) -> dict[str, Any]:
    """Classify every pinned historical receipt under ``root``.

    ``between_reads`` is a test-only seam used by ``selftest`` to prove the
    ``HISTORICAL_BYTES_CHANGED`` refusal; production callers never pass it.
    """
    if not root.is_dir():
        raise GateError("MISSING_INPUT", f"repository root {root} is not a directory")
    schema = load_json(root / schemas_rel, "S07 schema document")
    check_contract_vocabulary(root, schema)
    assert_no_frozen_acceptance_rule()
    entries: list[dict[str, Any]] = []
    for key in CLASSIFY_SOURCE_KEYS:
        entries.append(classify_receipt(root, schema, key, between_reads))
    return {
        "schema": CLASSIFICATION_SCHEMA_ID,
        "protocol": PROTOCOL_ID,
        "schemas": (schema.get("schema") if isinstance(schema, dict) else None) or SCHEMAS_ID,
        "receipt_schema_id": (schema.get("receipt_schema_id") if isinstance(schema, dict) else None)
        or RECEIPT_SCHEMA_ID,
        "acceptance_effect": "none",
        "duration_floor_is_not_acceptance": True,
        "run_status_is_not_terminal_evidence": True,
        "outcome_values": list(OUTCOME_VALUES),
        "receipts": entries,
    }


# --------------------------------------------------------------------------- #
# Recorder: one new S07 attempt under a new identity (write-once)
# --------------------------------------------------------------------------- #


def _object_block(schema: Any, key: str) -> dict[str, Any]:
    block = schema.get(key) if isinstance(schema, dict) else None
    if not isinstance(block, dict):
        raise GateError("SCHEMA_KEY_DRIFT", f"$.{key} must be a JSON object in {SCHEMAS_REL}")
    return block


def _string_list(block: dict[str, Any], key: str, diagnostic: str) -> list[str]:
    value = block.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(i, str) and i for i in value):
        raise GateError(diagnostic, f"{key} must be a non-empty list of non-empty strings")
    return list(value)


def check_recorder_schema(schema: Any) -> None:
    """Bind the recorder's constants to the frozen schema's attempt/failure/promotion policy."""
    if not isinstance(schema, dict):
        raise GateError("SCHEMA_KEY_DRIFT", "the S07 schema document must be a JSON object")
    if schema.get("receipt_schema_id") != RECEIPT_SCHEMA_ID:
        raise GateError(
            "SCHEMA_VERSION_DRIFT",
            f"$.receipt_schema_id is {schema.get('receipt_schema_id')!r}, expected "
            f"{RECEIPT_SCHEMA_ID!r}",
        )
    if schema.get("sidecar_schema_id") != SIDECAR_SCHEMA_ID:
        raise GateError(
            "SCHEMA_VERSION_DRIFT",
            f"$.sidecar_schema_id is {schema.get('sidecar_schema_id')!r}, expected "
            f"{SIDECAR_SCHEMA_ID!r}",
        )

    policy = _object_block(schema, "new_attempt_policy")
    if policy.get("sidecar_arg") != SIDECAR_ARG:
        raise GateError(
            "ARGV_PIN_DRIFT", f"$.new_attempt_policy.sidecar_arg must be {SIDECAR_ARG!r}"
        )
    if policy.get("limit_flag_forbidden") is not True:
        raise GateError("ARGV_PIN_DRIFT", "$.new_attempt_policy.limit_flag_forbidden must be true")
    if policy.get("attempt_id_slug_pattern") != ATTEMPT_ID_RE.pattern:
        raise GateError(
            "USAGE",
            f"$.new_attempt_policy.attempt_id_slug_pattern is "
            f"{policy.get('attempt_id_slug_pattern')!r}, this recorder enforces "
            f"{ATTEMPT_ID_RE.pattern!r}",
        )
    if policy.get("receipt_path") != DEFAULT_RECEIPT_REL:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"$.new_attempt_policy.receipt_path is {policy.get('receipt_path')!r}, this recorder "
            f"publishes {DEFAULT_RECEIPT_REL!r}",
        )
    if policy.get("attempt_dir_prefix") != ATTEMPT_DIR_REL + "/":
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"$.new_attempt_policy.attempt_dir_prefix is {policy.get('attempt_dir_prefix')!r}, "
            f"this recorder logs under {ATTEMPT_DIR_REL}/",
        )
    for key in ("write_once", "new_argv_changes_identity", "old_argv_must_not_be_edited"):
        if policy.get(key) is not True:
            raise GateError("C4_RECEIPT_DRIFT", f"$.new_attempt_policy.{key} must be true")
    if policy.get("forbidden_write_diagnostic") != "C4_RECEIPT_DRIFT":
        raise GateError(
            "C4_RECEIPT_DRIFT",
            "$.new_attempt_policy.forbidden_write_diagnostic must be C4_RECEIPT_DRIFT",
        )

    corpus = _object_block(schema, "corpus_pins")
    if (
        corpus.get("consultant_xml_count") != PIN_CONSULTANT_XML_COUNT
        or corpus.get("garant_file_count") != PIN_GARANT_FILE_COUNT
    ):
        raise GateError(
            "CORPUS_COUNT_DRIFT",
            f"$.corpus_pins is {corpus.get('consultant_xml_count')!r}/{corpus.get('garant_file_count')!r}, "
            f"this recorder pins {PIN_CONSULTANT_XML_COUNT}/{PIN_GARANT_FILE_COUNT}",
        )

    failure = _object_block(schema, "failure_policy")
    if failure.get("sidecar_schema_id") != SIDECAR_SCHEMA_ID:
        raise GateError(
            "SCHEMA_VERSION_DRIFT", "$.failure_policy.sidecar_schema_id is not the reused id"
        )
    if set(_string_list(failure, "sidecar_keys", "SIDECAR_KEY_DRIFT")) != set(SIDECAR_KEYS):
        raise GateError(
            "SIDECAR_KEY_DRIFT",
            f"$.failure_policy.sidecar_keys must be exactly {list(SIDECAR_KEYS)!r}",
        )
    if failure.get("acceptance_effect") != "none":
        raise GateError("PROMOTION_CLAIM", "$.failure_policy.acceptance_effect must stay 'none'")

    promotion = _object_block(schema, "promotion_contract")
    if (
        promotion.get("promotion") != "none"
        or promotion.get("classification") != "not-authorized"
        or promotion.get("model_invoked") is not False
    ):
        raise GateError(
            "PROMOTION_CLAIM",
            "$.promotion_contract must keep promotion=none, classification=not-authorized and "
            "model_invoked=false",
        )
    if promotion.get("is_gold") is not False or promotion.get("human_acceptance") is not None:
        raise GateError(
            "GOLD_CLAIM",
            "$.promotion_contract must keep is_gold=false and human_acceptance=null",
        )


def frozen_write_targets(schema: Any) -> tuple[set[str], set[str]]:
    """The exact repo-relative paths and directory prefixes no S07 attempt may write to."""
    frozen = _object_block(schema, "frozen_sources")
    exact: set[str] = set()
    for key, entry in frozen.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise GateError("MISSING_INPUT", f"$.frozen_sources[{key}] carries no path")
        exact.add(entry["path"])
    policy = _object_block(schema, "new_attempt_policy")
    exact |= set(_string_list(policy, "forbidden_write_paths", "C4_RECEIPT_DRIFT"))
    prefixes = set(_string_list(policy, "forbidden_write_prefixes", "C4_RECEIPT_DRIFT"))
    return exact, prefixes


def assert_write_allowed(root: Path, schema: Any, target: Path, label: str) -> None:
    """Refuse a write target that names a frozen S04/M204/S03 artifact or attempt directory."""
    exact, prefixes = frozen_write_targets(schema)
    rel = display_under(root, target)
    if rel in exact or any(rel == p.rstrip("/") or rel.startswith(p) for p in prefixes):
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{label} {rel!r} is a frozen path: an S07 attempt is a new identity and never writes "
            "over S04/M204/S03 evidence",
        )


def check_attempt_id(value: Any) -> str:
    if not isinstance(value, str) or not ATTEMPT_ID_RE.match(value):
        raise GateError(
            "USAGE",
            f"--attempt-id {value!r} must match the pinned slug pattern {ATTEMPT_ID_RE.pattern}",
        )
    return value


def check_budget(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < BUDGET_SECONDS_MINIMUM:
        raise GateError(
            "BUDGET_BELOW_MINIMUM",
            f"--budget-seconds {value!r} is below the frozen {BUDGET_SECONDS_MINIMUM}s kill ceiling",
        )
    return value


def check_pinned_binding(profile: Any, jobs: Any) -> None:
    if profile != FROZEN_PROFILE:
        raise GateError(
            "ARGV_PIN_DRIFT", f"--profile {profile!r} is not the pinned {FROZEN_PROFILE!r}"
        )
    if jobs != FROZEN_JOBS:
        raise GateError("ARGV_PIN_DRIFT", f"--jobs {jobs!r} is not the pinned {FROZEN_JOBS}")


def check_source_revision(value: Any) -> str:
    revision = value.strip() if isinstance(value, str) else ""
    if not revision or is_digest_like(revision):
        raise GateError(
            "MISSING_INPUT",
            "--source-revision must be a caller pin, never empty and never a digest",
        )
    return revision


def build_argv(
    binary: Path,
    corpus_root: Path,
    garant_root: Path,
    contract: Path,
    source_revision: str,
    failures_out: Path,
) -> list[str]:
    """The S04 required flag set plus ``--failures-out``: same walk, new identity, no ``--out``."""
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
        SIDECAR_ARG,
        str(failures_out),
    ]


def check_argv_shape(argv: Any) -> None:
    """Refuse any argv that is not the pinned full-walk argv carrying ``--failures-out``."""
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        raise GateError("ARGV_PIN_DRIFT", "the attempt argv must be a non-empty list of strings")
    for flag in ARGV_FORBIDDEN_FLAGS:
        if flag in argv:
            raise GateError(
                "ARGV_PIN_DRIFT",
                f"the recorder never forwards {flag}: a limited walk is not a full walk",
            )
    if "--out" in argv:
        raise GateError(
            "ARGV_PIN_DRIFT",
            "the recorder never forwards --out: stdout stays the five-row JSONL",
        )
    for flag in ARGV_REQUIRED_FLAGS:
        if flag not in argv:
            raise GateError("ARGV_PIN_DRIFT", f"the attempt argv must carry {flag}")
    forwarded = flag_values(argv, SIDECAR_ARG)
    if len(forwarded) != 1 or not forwarded[0]:
        raise GateError("ARGV_PIN_DRIFT", f"{SIDECAR_ARG} must carry exactly one non-empty path")
    for flag in ("--profile", "--jobs"):
        if len(flag_values(argv, flag)) != 1:
            raise GateError("ARGV_PIN_DRIFT", f"the attempt argv must carry {flag} exactly once")


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
            proc = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True)
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
        if isinstance(record, dict):
            value = record.get("inventory_digest")
            if isinstance(value, str) and value:
                return value
    return None


def read_parser_revision(source: Path) -> str:
    if not source.is_file():
        raise GateError(
            "MISSING_ARTIFACT", f"parser source not found at {display_under(ROOT, source)}"
        )
    replacement = source.read_text(encoding="utf-8")
    marker = 'pub const PARSER_REVISION: &str = "'
    start = replacement.find(marker)
    if start < 0:
        raise GateError(
            "MISSING_ARTIFACT", f"PARSER_REVISION is not declared in {source.as_posix()}"
        )
    start += len(marker)
    end = replacement.find('"', start)
    if end < 0:
        raise GateError("MISSING_ARTIFACT", f"PARSER_REVISION is malformed in {source.as_posix()}")
    return replacement[start:end]


def toolchain() -> dict[str, Any]:
    try:
        rustc = subprocess.run(["rustc", "--version"], capture_output=True, text=True, check=False)
        cargo = subprocess.run(["cargo", "--version"], capture_output=True, text=True, check=False)
    except OSError as exc:
        raise GateError("MISSING_ARTIFACT", f"the Rust toolchain is not runnable: {exc}") from exc
    return {
        "rustc": (rustc.stdout + rustc.stderr).strip(),
        "cargo": (cargo.stdout + cargo.stderr).strip(),
        "commands_exit_code": {"rustc": rustc.returncode, "cargo": cargo.returncode},
    }


def parse_contract(root: Path, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise GateError("MISSING_ARTIFACT", f"acceptance contract not found at {path.as_posix()}")
    text = path.read_text(encoding="utf-8")
    if f"schema: {CONTRACT_VERSION}" not in text:
        raise GateError(
            "C4_RECEIPT_DRIFT", f"{path.as_posix()} does not declare schema {CONTRACT_VERSION}"
        )
    return {
        "path": display_under(root, path),
        "sha256": sha256_file(path),
        "version": CONTRACT_VERSION,
    }


def _sidecar_path_ok(raw: Any, prefix: str) -> bool:
    if (
        not isinstance(raw, str)
        or not raw
        or "\x00" in raw
        or raw.startswith("/")
        or "\\" in raw
        or (len(raw) > 1 and raw[1] == ":")
    ):
        return False
    if ".." in PurePosixPath(raw).parts:
        return False
    return raw.startswith(prefix)


def load_sidecar(path: Path, schema: Any) -> list[dict[str, Any]]:
    """Validate the reused ``npa-contour-failure-trace/v1`` sidecar against the closed policy."""
    policy = _object_block(schema, "failure_policy")
    keys = _string_list(policy, "sidecar_keys", "SIDECAR_KEY_DRIFT")
    if set(keys) != set(SIDECAR_KEYS):
        raise GateError(
            "SIDECAR_KEY_DRIFT",
            f"$.failure_policy.sidecar_keys is {keys!r}, expected {list(SIDECAR_KEYS)!r}",
        )
    providers = _string_list(policy, "provider_allowlist", "SIDECAR_PROVIDER_DRIFT")
    classes = _string_list(policy, "class_allowlist", "SIDECAR_CLASS_DRIFT")
    roots = policy.get("provider_roots")
    if not isinstance(roots, dict):
        raise GateError("SIDECAR_PATH_ESCAPE", "$.failure_policy.provider_roots must be an object")
    record_kind = policy.get("record_kind_value")
    rows = load_jsonl(path, "failure sidecar JSONL")
    for number, row in enumerate(rows, start=1):
        if set(row) != set(SIDECAR_KEYS):
            raise GateError(
                "SIDECAR_KEY_DRIFT",
                f"sidecar row {number} carries keys {sorted(row)!r}, expected {list(SIDECAR_KEYS)!r}",
            )
        if row.get("record_kind") != record_kind:
            raise GateError(
                "SIDECAR_KEY_DRIFT",
                f"sidecar row {number} record_kind is {row.get('record_kind')!r}, expected "
                f"{record_kind!r}",
            )
        if row.get("schema") != SIDECAR_SCHEMA_ID:
            raise GateError(
                "SIDECAR_KEY_DRIFT",
                f"sidecar row {number} schema is {row.get('schema')!r}, expected "
                f"{SIDECAR_SCHEMA_ID!r}",
            )
        provider = row.get("provider")
        if provider not in providers:
            raise GateError(
                "SIDECAR_PROVIDER_DRIFT",
                f"sidecar row {number} provider {provider!r} is outside {providers!r}",
            )
        klass = row.get("class")
        if klass not in classes:
            raise GateError(
                "SIDECAR_CLASS_DRIFT",
                f"sidecar row {number} class {klass!r} is outside {classes!r}",
            )
        prefix = roots.get(provider)
        if not isinstance(prefix, str) or not _sidecar_path_ok(row.get("path"), prefix):
            raise GateError(
                "SIDECAR_PATH_ESCAPE",
                f"sidecar row {number} path {row.get('path')!r} is not repository-relative under "
                f"{prefix!r}",
            )
    return rows


def assert_write_targets_free(
    root: Path,
    receipt_path: Path,
    attempt_dir: Path,
    *,
    resume_orphan_logs: bool,
) -> dict[str, Any]:
    """Write-path preconditions, evaluated before the first ``mkdir``."""
    if receipt_path.exists():
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{display_under(root, receipt_path)} already exists; a later attempt needs a new "
            "attempt_id and a new receipt, published evidence is never overwritten",
        )
    nonempty = attempt_dir.is_dir() and any(attempt_dir.iterdir())
    if nonempty and not resume_orphan_logs:
        raise GateError(
            "ATTEMPT_LOG_MISSING",
            f"{display_under(root, attempt_dir)} already holds logs and no receipt was published; "
            "pass --resume-orphan-logs to reuse an interrupted attempt that published nothing",
        )
    return {"receipt_exists": False, "attempt_dir_nonempty": nonempty}


def _resolve_under(root: Path, raw: str) -> Path:
    candidate = Path(raw)
    return candidate if candidate.is_absolute() else root / candidate


def cmd_run(args: argparse.Namespace, root: Path) -> int:
    """Record exactly one new S07 attempt under a new identity, or refuse by name."""
    if not root.is_dir():
        raise GateError("MISSING_ARTIFACT", f"repository root {root} is not a directory")
    if args.limit is not None:
        raise GateError(
            "ARGV_PIN_DRIFT",
            f"--limit {args.limit!r} is refused: a limited walk is not a full walk, and the "
            "recorder never forwards it to the binary",
        )
    attempt_id = check_attempt_id(args.attempt_id)
    check_budget(args.budget_seconds)
    check_pinned_binding(args.profile, args.jobs)
    revision = check_source_revision(args.source_revision)

    schema = load_json(root / args.schemas, "S07 schema document")
    check_contract_vocabulary(root, schema)
    assert_no_frozen_acceptance_rule()
    check_recorder_schema(schema)

    binary = _resolve_under(root, args.binary)
    corpus_root = _resolve_under(root, args.consultant_root)
    garant_root = _resolve_under(root, args.garant_root)
    contract_path = _resolve_under(root, args.contract)
    parser_source = _resolve_under(root, args.parser_source)
    for label, path, kind in (
        ("binary", binary, "file"),
        ("corpus root", corpus_root, "dir"),
        ("Garant root", garant_root, "dir"),
        ("acceptance contract", contract_path, "file"),
        ("parser source", parser_source, "file"),
    ):
        present = path.is_file() if kind == "file" else path.is_dir()
        if not present:
            raise GateError("MISSING_ARTIFACT", f"{label} {display_under(root, path)} is absent")

    policy = _object_block(schema, "new_attempt_policy")
    evidence_root = (root / EVIDENCE_DIR_REL).resolve()
    if args.out:
        receipt_path = Path(args.out).resolve()
        if not receipt_path.is_relative_to(evidence_root):
            raise GateError(
                "UNSAFE_PATH",
                f"--out {receipt_path.as_posix()} must stay under {EVIDENCE_DIR_REL}",
            )
    else:
        receipt_path = resolve_repo_path(root, policy["receipt_path"], "receipt_path")
    attempt_dir = resolve_repo_path(
        root, f"{policy['attempt_dir_prefix']}{attempt_id}", "attempt_dir"
    )
    assert_write_allowed(root, schema, receipt_path, "the receipt path")
    assert_write_allowed(root, schema, attempt_dir, "the attempt log directory")
    failures_out = attempt_dir / SIDECAR_FILENAME

    argv = build_argv(binary, corpus_root, garant_root, contract_path, revision, failures_out)
    check_argv_shape(argv)

    corpus = {
        "consultant_xml_count": count_files(corpus_root, CONSULTANT_XML_SUFFIX),
        "consultant_root": display_under(root, corpus_root),
        "garant_file_count": count_all_files(garant_root),
        "garant_root": display_under(root, garant_root),
    }
    if corpus["consultant_xml_count"] != PIN_CONSULTANT_XML_COUNT:
        raise GateError(
            "CORPUS_COUNT_DRIFT",
            f"consultant XML count {corpus['consultant_xml_count']} is not the frozen "
            f"{PIN_CONSULTANT_XML_COUNT}",
        )
    if corpus["garant_file_count"] != PIN_GARANT_FILE_COUNT:
        raise GateError(
            "CORPUS_COUNT_DRIFT",
            f"Garant file count {corpus['garant_file_count']} is not the frozen "
            f"{PIN_GARANT_FILE_COUNT}",
        )

    if args.dry_run:
        emit(
            {
                "schema": RECEIPT_SCHEMA_ID,
                "dry_run": True,
                "attempt_id": attempt_id,
                "argv": argv,
                "argv_sha256": argv_sha256(argv),
                "receipt": display_under(root, receipt_path),
                "attempt_dir": display_under(root, attempt_dir),
                "failures_out": display_under(root, failures_out),
                "corpus": corpus,
                "budget_seconds": args.budget_seconds,
                "source_revision": revision,
                "binary": {"path": display_under(root, binary), "sha256": sha256_file(binary)},
                "contract": parse_contract(root, contract_path),
                "predicates": schema.get("predicates"),
                "receipt_exists": receipt_path.exists(),
                "attempt_dir_nonempty": attempt_dir.is_dir() and any(attempt_dir.iterdir()),
                "acceptance_effect": "none",
            }
        )
        print(DRY_RUN_MARKER, file=sys.stderr)
        return 0

    assert_write_targets_free(
        root, receipt_path, attempt_dir, resume_orphan_logs=args.resume_orphan_logs
    )
    contract = parse_contract(root, contract_path)
    parser_revision = read_parser_revision(parser_source)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    terminal, elapsed_ms, stdout_path, stderr_path = launch_walk(
        argv, attempt_dir, timeout_seconds=args.budget_seconds
    )
    finished_at = utc_now()

    if terminal["outcome"] == "launch_error":
        print(
            f"SUBCLI_FAILURE: the walk could not be launched: {terminal.get('error')}",
            file=sys.stderr,
        )
        return 2

    stdout_rows = load_jsonl(stdout_path)
    stdout_text = _decode_text(stdout_path, "attempt stdout log")
    inventory_digest = extract_inventory_digest(stdout_text)
    logs = {
        "stdout": display_under(root, stdout_path),
        "stderr": display_under(root, stderr_path),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "inventory_digest": inventory_digest,
    }
    aggregate = _row_for(stdout_rows, "aggregate")
    aggregate_failed = aggregate.get("failed") if isinstance(aggregate, dict) else None
    if isinstance(aggregate_failed, bool) or not isinstance(aggregate_failed, int):
        aggregate_failed = None
    sidecar_rows = 0
    failures_sha256 = None
    if failures_out.is_file():
        sidecar_rows = len(load_sidecar(failures_out, schema))
        failures_sha256 = sha256_file(failures_out)
    binary_hash = sha256_file(binary)

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA_ID,
        "attempt_id": attempt_id,
        "immutable_attempt_identity": {
            "attempt_id": attempt_id,
            "argv_sha256": argv_sha256(argv),
        },
        "argv": argv,
        "binary": {"path": display_under(root, binary), "sha256": binary_hash},
        "build_inputs": {
            "binary_sha256": binary_hash,
            "parser_source_sha256": sha256_file(parser_source),
            "protocol_sha256": sha256_file(root / PROTOCOL_REL),
            "schemas_sha256": sha256_file(root / args.schemas),
        },
        "toolchain": toolchain(),
        "parser_revision": parser_revision,
        "source_revision": revision,
        "contract": contract,
        "corpus": corpus,
        "observed_output": {
            "stdout_sha256": logs["stdout_sha256"],
            "inventory_digest": inventory_digest,
        },
        "binding": {
            "profile": FROZEN_PROFILE,
            "limit": None,
            "jobs": FROZEN_JOBS,
            "inventory_scope": INVENTORY_SCOPE,
        },
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": elapsed_ms,
        "budget_seconds": args.budget_seconds,
        "terminal": terminal,
        "logs": logs,
        "failure_policy": {
            "failures_out_path": display_under(root, failures_out),
            "failures_sha256": failures_sha256,
            "sidecar_rows": sidecar_rows,
            "aggregate_failed": aggregate_failed,
            "acceptance_effect": "none",
        },
        "predicates": {"full_walk": False, "timeout": False, "outcome": "launch_error"},
        "claims": {
            "operational_classification": "launch_error",
            "acceptance_effect": "none",
            "receipt_is_runtime_attempt": True,
        },
        "non_claims": list(SUCCESSOR_NON_CLAIMS),
    }

    report = classify(receipt, stdout_rows)
    receipt["predicates"] = {
        "full_walk": bool(report["full_walk"]),
        "timeout": bool(report["timeout"]),
        "outcome": report["outcome"],
    }
    receipt["claims"]["operational_classification"] = report["outcome"]

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    if receipt_path.exists():
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"{display_under(root, receipt_path)} appeared during the attempt; refusing to "
            "overwrite published evidence",
        )
    staged = receipt_path.with_name(receipt_path.name + ".partial")
    staged.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    staged.replace(receipt_path)

    emit(
        {
            "schema": RECEIPT_SCHEMA_ID,
            "receipt": display_under(root, receipt_path),
            "attempt_id": attempt_id,
            "argv_sha256": receipt["immutable_attempt_identity"]["argv_sha256"],
            "terminal": terminal,
            "duration_ms": elapsed_ms,
            "budget_seconds": args.budget_seconds,
            "failure_policy": receipt["failure_policy"],
            "predicates": receipt["predicates"],
            "acceptance_effect": "none",
        }
    )
    print(RECORDER_MARKER, file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Read-only gate over the published successor receipt
# --------------------------------------------------------------------------- #


def _check_receipt_acceptance_keys(receipt: dict[str, Any]) -> None:
    """The successor receipt classifies; it never accepts, promotes or labels gold."""
    for scope_label, scope in (
        ("receipt", receipt),
        (
            "receipt.claims",
            receipt.get("claims") if isinstance(receipt.get("claims"), dict) else {},
        ),
    ):
        found = sorted(key for key in RECEIPT_FORBIDDEN_ACCEPTANCE_KEYS if key in scope)
        if found:
            raise GateError(
                "SCHEMA_KEY_DRIFT",
                f"{scope_label} must not carry {found}: the successor receipt publishes no "
                "acceptance verdict",
            )
        promoted = sorted(key for key in RECEIPT_FORBIDDEN_PROMOTION_KEYS if key in scope)
        if promoted:
            raise GateError(
                "PROMOTION_CLAIM",
                f"{scope_label} must not carry promotion keys {promoted}: promotion stays none",
            )
        gold = sorted(key for key in RECEIPT_FORBIDDEN_GOLD_KEYS if key in scope)
        if gold:
            raise GateError(
                "GOLD_CLAIM",
                f"{scope_label} must not carry gold keys {gold}: the attempt is never a gold label",
            )


def _check_receipt_shape(receipt: dict[str, Any]) -> None:
    extra = sorted(set(receipt) - set(RECEIPT_KEYS))
    missing = sorted(set(RECEIPT_KEYS) - set(receipt))
    if extra:
        raise GateError("SCHEMA_KEY_DRIFT", f"receipt carries keys outside the closure: {extra}")
    if missing:
        raise GateError("SCHEMA_KEY_DRIFT", f"receipt is missing required keys: {missing}")
    if receipt.get("schema") != RECEIPT_SCHEMA_ID:
        raise GateError(
            "SCHEMA_VERSION_DRIFT",
            f"receipt.schema is {receipt.get('schema')!r}, expected {RECEIPT_SCHEMA_ID!r}",
        )
    for name, keys in RECEIPT_NESTED_KEYS.items():
        block = receipt.get(name)
        if not isinstance(block, dict):
            raise GateError("SCHEMA_KEY_DRIFT", f"receipt.{name} must be an object")
        gap = sorted(set(keys) - set(block))
        if gap:
            raise GateError("SCHEMA_KEY_DRIFT", f"receipt.{name} is missing keys: {gap}")
        surplus = sorted(set(block) - set(keys))
        if surplus:
            raise GateError(
                "SCHEMA_KEY_DRIFT", f"receipt.{name} carries keys outside the closure: {surplus}"
            )
    terminal = receipt["terminal"]
    surplus = sorted(
        set(terminal) - set(RECEIPT_TERMINAL_KEYS) - set(RECEIPT_TERMINAL_OPTIONAL_KEYS)
    )
    if surplus:
        raise GateError(
            "SCHEMA_KEY_DRIFT", f"receipt.terminal carries keys outside the closure: {surplus}"
        )
    if terminal.get("outcome") == "launch_error":
        if not isinstance(terminal.get("error"), str) or not terminal["error"]:
            raise GateError(
                "SCHEMA_KEY_DRIFT", "a launch_error terminal must record a non-empty error"
            )
    elif "error" in terminal:
        raise GateError("SCHEMA_KEY_DRIFT", "only a launch_error terminal may record an error")
    claims = receipt["claims"]
    if claims.get("acceptance_effect") != "none":
        raise GateError(
            "PROMOTION_CLAIM",
            f"receipt.claims.acceptance_effect is {claims.get('acceptance_effect')!r}, must be 'none'",
        )
    if claims.get("receipt_is_runtime_attempt") is not True:
        raise GateError(
            "SCHEMA_KEY_DRIFT", "receipt.claims.receipt_is_runtime_attempt must be true"
        )
    if not isinstance(receipt.get("non_claims"), list) or not receipt["non_claims"]:
        raise GateError("SCHEMA_KEY_DRIFT", "receipt.non_claims must be a non-empty list")


def _check_receipt_identity(receipt: dict[str, Any]) -> None:
    identity = receipt["immutable_attempt_identity"]
    attempt_id = receipt.get("attempt_id")
    if not isinstance(attempt_id, str) or not ATTEMPT_ID_RE.match(attempt_id):
        raise GateError("USAGE", f"receipt.attempt_id {attempt_id!r} is not a safe S07 attempt id")
    if identity.get("attempt_id") != attempt_id:
        raise GateError(
            "ARGV_PIN_DRIFT", "immutable_attempt_identity.attempt_id differs from attempt_id"
        )
    argv = receipt.get("argv")
    recomputed = argv_sha256(argv) if isinstance(argv, list) else None
    if recomputed is None or identity.get("argv_sha256") != recomputed:
        raise GateError(
            "ARGV_PIN_DRIFT",
            f"immutable_attempt_identity.argv_sha256 is {identity.get('argv_sha256')!r}, "
            f"recomputed {recomputed!r}",
        )


def _check_receipt_argv(root: Path, receipt: dict[str, Any]) -> None:
    argv = receipt.get("argv")
    check_argv_shape(argv)
    if flag_values(argv, "--profile") != [FROZEN_PROFILE]:
        raise GateError(
            "ARGV_PIN_DRIFT", f"receipt.argv --profile is not the pinned {FROZEN_PROFILE!r}"
        )
    if flag_values(argv, "--jobs") != [str(FROZEN_JOBS)]:
        raise GateError("ARGV_PIN_DRIFT", f"receipt.argv --jobs is not the pinned {FROZEN_JOBS}")
    forwarded = flag_values(argv, SIDECAR_ARG)[0]
    recorded = receipt["failure_policy"].get("failures_out_path")
    if display_under(root, Path(forwarded)) != recorded:
        raise GateError(
            "ARGV_PIN_DRIFT",
            f"{SIDECAR_ARG} {forwarded!r} is not bound to "
            f"failure_policy.failures_out_path {recorded!r}",
        )
    binding = receipt["binding"]
    if binding.get("profile") != FROZEN_PROFILE:
        raise GateError("ARGV_PIN_DRIFT", "binding.profile is not the pinned contour")
    if binding.get("limit") is not None:
        raise GateError("ARGV_PIN_DRIFT", "binding.limit must stay null: no limited walk")
    if binding.get("jobs") != FROZEN_JOBS:
        raise GateError("ARGV_PIN_DRIFT", f"binding.jobs is not the pinned {FROZEN_JOBS}")
    if binding.get("inventory_scope") != INVENTORY_SCOPE:
        raise GateError("C4_RECEIPT_DRIFT", "binding.inventory_scope must be declared")


def _check_receipt_pins(root: Path, receipt: dict[str, Any], schemas_rel: str) -> None:
    binary = receipt["binary"]
    if binary.get("path") != DEFAULT_BINARY_REL:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"binary.path {binary.get('path')!r} is not the pinned {DEFAULT_BINARY_REL!r}",
        )
    binary_path = root / DEFAULT_BINARY_REL
    if not binary_path.is_file():
        raise GateError("MISSING_INPUT", f"pinned binary {DEFAULT_BINARY_REL} is absent")
    live_binary = sha256_file(binary_path)
    if binary.get("sha256") != live_binary:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"binary.sha256 {binary.get('sha256')!r} is not the live binary digest {live_binary}",
        )
    build = receipt["build_inputs"]
    if build.get("binary_sha256") != binary.get("sha256"):
        raise GateError("C4_RECEIPT_DRIFT", "build_inputs.binary_sha256 differs from binary.sha256")
    if any(
        isinstance(v, bool) or not isinstance(v, int) or v != 0
        for v in receipt["toolchain"]["commands_exit_code"].values()
    ):
        raise GateError("C4_RECEIPT_DRIFT", "toolchain rustc/cargo must both exit 0")
    for label, rel, key in (
        ("protocol", PROTOCOL_REL, "protocol_sha256"),
        ("schemas", schemas_rel, "schemas_sha256"),
    ):
        live = sha256_file(root / rel)
        if build.get(key) != live:
            raise GateError(
                "C4_RECEIPT_DRIFT",
                f"build_inputs.{key} {build.get(key)!r} is not the live {label} digest {live}",
            )
    contract = receipt["contract"]
    if contract.get("version") != CONTRACT_VERSION:
        raise GateError("C4_RECEIPT_DRIFT", f"contract.version is not {CONTRACT_VERSION!r}")
    contract_path = resolve_repo_path(root, contract.get("path"), "contract.path")
    if not contract_path.is_file():
        raise GateError("MISSING_INPUT", f"contract {contract.get('path')!r} is absent")
    live_contract = sha256_file(contract_path)
    if contract.get("sha256") != live_contract:
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"contract.sha256 {contract.get('sha256')!r} is not the live contract digest {live_contract}",
        )
    parser_source = root / DEFAULT_PARSER_SOURCE_REL
    if not parser_source.is_file():
        raise GateError("MISSING_INPUT", f"parser source {DEFAULT_PARSER_SOURCE_REL} is absent")
    if receipt.get("parser_revision") != read_parser_revision(parser_source):
        raise GateError("C4_RECEIPT_DRIFT", "parser_revision is not the live parser revision")
    if sha256_file(parser_source) != build.get("parser_source_sha256"):
        raise GateError("C4_RECEIPT_DRIFT", "build_inputs.parser_source_sha256 has drifted")
    if (
        not isinstance(receipt.get("source_revision"), str)
        or not receipt["source_revision"].strip()
    ):
        raise GateError("C4_RECEIPT_DRIFT", "source_revision must be a non-empty caller pin")


def _check_receipt_corpus(root: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    corpus = receipt["corpus"]
    consultant_root = resolve_repo_path(
        root, corpus.get("consultant_root"), "corpus.consultant_root"
    )
    garant_root = resolve_repo_path(root, corpus.get("garant_root"), "corpus.garant_root")
    if not consultant_root.is_dir() or not garant_root.is_dir():
        raise GateError("MISSING_INPUT", "the declared corpus roots are not both directories")
    live_xml = count_files(consultant_root, CONSULTANT_XML_SUFFIX)
    live_garant = count_all_files(garant_root)
    if corpus.get("consultant_xml_count") != live_xml:
        raise GateError(
            "CORPUS_COUNT_DRIFT",
            f"corpus.consultant_xml_count is {corpus.get('consultant_xml_count')!r}, live {live_xml}",
        )
    if corpus.get("consultant_xml_count") != PIN_CONSULTANT_XML_COUNT:
        raise GateError("CORPUS_COUNT_DRIFT", "corpus.consultant_xml_count is not the frozen pin")
    if corpus.get("garant_file_count") != live_garant:
        raise GateError(
            "CORPUS_COUNT_DRIFT",
            f"corpus.garant_file_count is {corpus.get('garant_file_count')!r}, live {live_garant}",
        )
    if corpus.get("garant_file_count") != PIN_GARANT_FILE_COUNT:
        raise GateError("CORPUS_COUNT_DRIFT", "corpus.garant_file_count is not the frozen pin")
    return corpus


def _check_receipt_logs(
    root: Path, receipt: dict[str, Any], schema: Any
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    logs = receipt["logs"]
    stdout_path = resolve_repo_path(root, logs.get("stdout"), "logs.stdout")
    stderr_path = resolve_repo_path(root, logs.get("stderr"), "logs.stderr")
    prefix = str(_object_block(schema, "new_attempt_policy")["attempt_dir_prefix"])
    if not display_under(root, stdout_path).startswith(prefix):
        raise GateError(
            "C4_RECEIPT_DRIFT",
            f"logs.stdout {display_under(root, stdout_path)!r} is not under the pinned attempt-dir "
            f"prefix {prefix!r}",
        )
    for label, path, key in (
        ("stdout", stdout_path, "stdout_sha256"),
        ("stderr", stderr_path, "stderr_sha256"),
    ):
        if not path.is_file():
            raise GateError(
                "MISSING_INPUT", f"attempt {label} log is missing at {display_under(root, path)}"
            )
        live = sha256_file(path)
        if logs.get(key) != live:
            raise GateError(
                "C4_RECEIPT_DRIFT",
                f"logs.{key} {logs.get(key)!r} is not the live {label} log digest {live}",
            )
    observed = receipt["observed_output"]
    if observed.get("stdout_sha256") != logs.get("stdout_sha256"):
        raise GateError(
            "C4_RECEIPT_DRIFT", "observed_output.stdout_sha256 differs from logs.stdout_sha256"
        )
    if observed.get("inventory_digest") != logs.get("inventory_digest"):
        raise GateError(
            "C4_RECEIPT_DRIFT",
            "observed_output.inventory_digest differs from logs.inventory_digest",
        )
    rows = load_jsonl(stdout_path)
    failures_out = receipt["failure_policy"].get("failures_out_path")
    if failures_out != display_under(root, stdout_path.parent / SIDECAR_FILENAME):
        raise GateError(
            "C4_RECEIPT_DRIFT",
            "failure_policy.failures_out_path is not the attempt directory's sidecar path",
        )
    aggregate = _row_for(rows, "aggregate")
    return rows, {"aggregate": aggregate, "stdout_path": stdout_path, "stderr_path": stderr_path}


def _check_receipt_predicates(
    receipt: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    baseline = classify(receipt, rows)
    for probe in (0, 1, 10**12):
        mutated = copy.deepcopy(receipt)
        mutated["duration_ms"] = probe
        swept = classify(mutated, rows)
        if (swept["full_walk"], swept["timeout"], swept["outcome"]) != (
            baseline["full_walk"],
            baseline["timeout"],
            baseline["outcome"],
        ):
            raise GateError(
                "DURATION_FLOOR_AS_ACCEPTANCE",
                f"the verdict moved when duration_ms was set to {probe}: duration is never a "
                "predicate input",
            )
    expected = {
        "full_walk": bool(baseline["full_walk"]),
        "timeout": bool(baseline["timeout"]),
        "outcome": baseline["outcome"],
    }
    recorded = receipt["predicates"]
    for key, value in expected.items():
        if recorded.get(key) != value:
            raise GateError(
                "PREDICATE_CONTRADICTION",
                f"receipt.predicates.{key} is {recorded.get(key)!r}, recomputed {value!r}",
            )
    claims = receipt["claims"]
    if claims.get("operational_classification") != expected["outcome"]:
        raise GateError(
            "PREDICATE_CONTRADICTION",
            f"claims.operational_classification is {claims.get('operational_classification')!r}, "
            f"recomputed {expected['outcome']!r}",
        )
    return expected


def _check_receipt_failure_policy(
    root: Path, receipt: dict[str, Any], schema: Any, aggregate: dict[str, Any] | None
) -> dict[str, Any]:
    recorded = receipt["failure_policy"]
    if recorded.get("acceptance_effect") != "none":
        raise GateError(
            "PROMOTION_CLAIM",
            f"failure_policy.acceptance_effect is {recorded.get('acceptance_effect')!r}, must be "
            "'none': making a failure visible is not a measurement",
        )
    failures_path = resolve_repo_path(root, recorded.get("failures_out_path"), "failures_out_path")
    aggregate_failed = aggregate.get("failed") if isinstance(aggregate, dict) else None
    if isinstance(aggregate_failed, bool) or not isinstance(aggregate_failed, int):
        aggregate_failed = None
    if failures_path.is_file():
        sidecar_rows = len(load_sidecar(failures_path, schema))
        failures_sha256 = sha256_file(failures_path)
        if recorded.get("sidecar_rows") != sidecar_rows:
            raise GateError(
                "SIDECAR_COUNT_MISMATCH",
                f"failure_policy.sidecar_rows is {recorded.get('sidecar_rows')!r}, the sidecar "
                f"carries {sidecar_rows} row(s)",
            )
        if recorded.get("failures_sha256") != failures_sha256:
            raise GateError(
                "C4_RECEIPT_DRIFT",
                f"failure_policy.failures_sha256 {recorded.get('failures_sha256')!r} is not the "
                f"live sidecar digest {failures_sha256}",
            )
    else:
        sidecar_rows = 0
        failures_sha256 = None
        if recorded.get("sidecar_rows") not in (0, None):
            raise GateError(
                "MISSING_SIDECAR",
                f"failure_policy.sidecar_rows is {recorded.get('sidecar_rows')!r} but no sidecar "
                "was published",
            )
        if recorded.get("failures_sha256") is not None:
            raise GateError(
                "MISSING_SIDECAR", "failure_policy.failures_sha256 is set but no sidecar exists"
            )
    if recorded.get("aggregate_failed") != aggregate_failed:
        raise GateError(
            "SIDECAR_COUNT_MISMATCH",
            f"failure_policy.aggregate_failed is {recorded.get('aggregate_failed')!r}, this "
            f"attempt's aggregate failed={aggregate_failed}",
        )
    terminal = receipt["terminal"]
    if aggregate_failed is None:
        if sidecar_rows:
            raise GateError(
                "SIDECAR_UNEXPECTED",
                "a sidecar was published although the attempt has no aggregate failed count",
            )
    elif sidecar_rows != aggregate_failed:
        exit_code = terminal.get("exit_code")
        if exit_code == 3 and terminal.get("outcome") == "nonzero":
            pass
        elif aggregate_failed > 0 and sidecar_rows == 0:
            raise GateError(
                "MISSING_SIDECAR",
                f"aggregate failed={aggregate_failed} but the attempt published no failure "
                f"sidecar and exited {exit_code!r}: only an exit-3 allowlist refusal is lawful "
                "without one",
            )
        else:
            raise GateError(
                "SIDECAR_COUNT_MISMATCH",
                f"the sidecar carries {sidecar_rows} row(s) but aggregate failed={aggregate_failed}",
            )
    return {
        "failures_out_path": recorded.get("failures_out_path"),
        "failures_sha256": failures_sha256,
        "sidecar_rows": sidecar_rows,
        "aggregate_failed": aggregate_failed,
        "acceptance_effect": "none",
    }


def _check_receipt_clock(receipt: dict[str, Any]) -> None:
    for label in ("started_at", "finished_at"):
        value = receipt.get(label)
        if not isinstance(value, str) or not ISO_SECONDS_RE.match(value):
            raise GateError("C4_RECEIPT_DRIFT", f"{label} must be an ISO-8601 UTC second timestamp")
    if receipt["finished_at"] < receipt["started_at"]:
        raise GateError("C4_RECEIPT_DRIFT", "finished_at precedes started_at")
    duration = receipt.get("duration_ms")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
        raise GateError(
            "C4_RECEIPT_DRIFT", f"duration_ms={duration!r} must be a non-negative integer"
        )
    check_budget(receipt.get("budget_seconds"))


def check_receipt(root: Path, receipt: Any, schema: Any, schemas_rel: str) -> dict[str, Any]:
    """Validate the published successor receipt read-only; raise a named diagnostic on drift."""
    if not isinstance(receipt, dict):
        raise GateError("SCHEMA_KEY_DRIFT", "the S07 successor receipt must be a JSON object")
    _check_receipt_acceptance_keys(receipt)
    _check_receipt_shape(receipt)
    _check_receipt_identity(receipt)
    _check_receipt_argv(root, receipt)
    _check_receipt_pins(root, receipt, schemas_rel)
    _check_receipt_corpus(root, receipt)
    rows, view = _check_receipt_logs(root, receipt, schema)
    _check_receipt_clock(receipt)
    predicates = _check_receipt_predicates(receipt, rows)
    failure_policy = _check_receipt_failure_policy(root, receipt, schema, view["aggregate"])
    return {
        "schema": RECEIPT_SCHEMA_ID,
        "attempt_id": receipt["attempt_id"],
        "argv_sha256": receipt["immutable_attempt_identity"]["argv_sha256"],
        "terminal": receipt["terminal"],
        "predicates": predicates,
        "failure_policy": failure_policy,
        "acceptance_effect": "none",
    }


def cmd_check(args: argparse.Namespace, root: Path) -> int:
    """Read-only gate over the published successor receipt (``M207_S07_C4_RECEIPT_OK``)."""
    if not root.is_dir():
        raise GateError("MISSING_ARTIFACT", f"repository root {root} is not a directory")
    schema = load_json(root / args.schemas, "S07 schema document")
    check_contract_vocabulary(root, schema)
    assert_no_frozen_acceptance_rule()
    check_recorder_schema(schema)
    policy = _object_block(schema, "new_attempt_policy")
    if args.receipt:
        receipt_path = resolve_repo_path(root, args.receipt, "--receipt")
    else:
        receipt_path = resolve_repo_path(root, policy["receipt_path"], "receipt_path")
    if not receipt_path.is_file():
        raise GateError(
            "MISSING_INPUT",
            f"no S07 successor receipt is published at {display_under(root, receipt_path)}",
        )
    assert_write_allowed(root, schema, receipt_path, "the receipt path")
    receipt = load_json(receipt_path, "S07 successor receipt")
    summary = check_receipt(root, receipt, schema, args.schemas)
    summary["receipt"] = display_under(root, receipt_path)
    emit(summary)
    print(RECORDER_MARKER, file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Recorder selftest: the hostile paths are proven, not asserted
# --------------------------------------------------------------------------- #


def _write_sidecar(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


# A fixture-only stand-in for the release binary: it emits the five-row JSONL and the write-once
# sidecar the real binary emits, so the recorder's write path and the read gate can be exercised in
# a throwaway root in about a second instead of during a 387 s corpus walk.
# ``NPA_S07_STUB_MODE=refuse`` makes it behave like the Rust exit-3 allowlist refusal (aggregate
# failed above zero, no sidecar).
STUB_BINARY = """#!/usr/bin/env python3
import json
import os
import sys

argv = sys.argv[1:]
mode = os.environ.get("NPA_S07_STUB_MODE", "full")
failures_out = None
for index, value in enumerate(argv):
    if value == "--failures-out" and index + 1 < len(argv):
        failures_out = argv[index + 1]
digest = "sha256:" + "0" * 64
rows = [
    {"record_kind": "header", "limit": None, "inventory_digest": digest},
    {"record_kind": "aggregate", "provider": "consultant", "files": 43797, "decoded": 43796, "failed": 1},
    {"record_kind": "inventory", "provider": "consultant"},
    {"record_kind": "canonical_payload", "limit": None, "files": 43797, "failed": 1, "inventory_digest": digest},
    {"record_kind": "operational_envelope", "run_status": "complete"},
]
for row in rows:
    print(json.dumps(row))
if mode == "refuse":
    sys.exit(3)
if failures_out:
    try:
        with open(failures_out, "x", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "record_kind": "failure",
                        "schema": "npa-contour-failure-trace/v1",
                        "provider": "consultant",
                        "path": "consru_export/consru_export/exports/a.xml",
                        "class": "read",
                    }
                )
                + "\\n"
            )
    except OSError:
        sys.exit(3)
sys.exit(0)
"""


def _stub_root(tmp: Path, root: Path) -> None:
    """A throwaway root that satisfies the pinned paths without touching the checkout."""
    for rel in ("consru_export", "law-source"):
        (tmp / rel).symlink_to(root / rel)
    for rel in (PROTOCOL_REL, SCHEMAS_REL, DEFAULT_CONTRACT_REL, DEFAULT_PARSER_SOURCE_REL):
        target = tmp / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, target)
    (tmp / EVIDENCE_DIR_REL).mkdir(parents=True, exist_ok=True)
    stub = tmp / DEFAULT_BINARY_REL
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text(STUB_BINARY, encoding="utf-8")
    stub.chmod(0o755)


def _expect_published_receipt(problems: list[str], stub_root: Path) -> dict[str, Any] | None:
    receipt_path = stub_root / DEFAULT_RECEIPT_REL
    if not receipt_path.is_file():
        problems.append(f"stub run published no receipt at {DEFAULT_RECEIPT_REL}")
        return None
    return json.loads(receipt_path.read_text(encoding="utf-8"))


@contextlib.contextmanager
def _quiet_recorder() -> Any:
    """Silence the recorder's CLI streams inside the selftest: only the marker may reach stdout."""
    with open(os.devnull, "w", encoding="utf-8") as sink:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            yield


def _recorder_end_to_end(problems: list[str], root: Path, schema: Any) -> None:
    """Exercise the real write path against a stub binary in a throwaway root, then gate it."""
    with tempfile.TemporaryDirectory() as raw_tmp:
        stub_root = Path(raw_tmp)
        _stub_root(stub_root, root)
        run_args = build_parser().parse_args(
            ["run", "--repo-root", str(stub_root), "--attempt-id", "m207-s07-c4-stub-001"]
        )
        with _quiet_recorder():
            code = cmd_run(run_args, stub_root)
        _expect_true(problems, "stub_full_run_exits_zero", f"cmd_run returned {code}", code == 0)
        published = _expect_published_receipt(problems, stub_root)
        if published is None:
            return
        _expect_true(
            problems,
            "stub_receipt_closure",
            f"root keys {sorted(published)!r}",
            set(published) == set(RECEIPT_KEYS),
        )
        _expect_true(
            problems,
            "stub_receipt_predicates",
            f"predicates {published.get('predicates')!r}",
            published.get("predicates")
            == {"full_walk": True, "timeout": False, "outcome": "full_walk"},
        )
        _expect_true(
            problems,
            "stub_receipt_failure_policy",
            f"failure_policy {published.get('failure_policy')!r}",
            published["failure_policy"]["sidecar_rows"] == 1
            and published["failure_policy"]["aggregate_failed"] == 1,
        )
        _expect_true(
            problems,
            "stub_receipt_has_no_acceptance_key",
            "operational_acceptance leaked into the successor receipt",
            "operational_acceptance" not in published,
        )
        _expect_true(
            problems,
            "stub_receipt_argv_shape",
            f"argv {published.get('argv')!r}",
            SIDECAR_ARG in published["argv"]
            and "--limit" not in published["argv"]
            and "--out" not in published["argv"],
        )
        summary = check_receipt(stub_root, published, schema, SCHEMAS_REL)
        _expect_true(
            problems,
            "stub_receipt_passes_the_read_gate",
            f"gate summary {summary!r}",
            summary["predicates"]["outcome"] == "full_walk",
        )

        for name, mutate, diagnostic in (
            (
                "gate_refuses_acceptance_key",
                lambda r: r.__setitem__("operational_acceptance", "pass"),
                "SCHEMA_KEY_DRIFT",
            ),
            (
                "gate_refuses_promotion_key",
                lambda r: r.__setitem__("promotion", "pass"),
                "PROMOTION_CLAIM",
            ),
            ("gate_refuses_gold_key", lambda r: r.__setitem__("is_gold", True), "GOLD_CLAIM"),
            (
                "gate_refuses_schema_version",
                lambda r: r.__setitem__("schema", "m204-s06-c4-operational-receipt/v1"),
                "SCHEMA_VERSION_DRIFT",
            ),
            (
                "gate_refuses_sidecar_count",
                lambda r: r["failure_policy"].__setitem__("sidecar_rows", 0),
                "SIDECAR_COUNT_MISMATCH",
            ),
            (
                "gate_refuses_acceptance_effect",
                lambda r: r["failure_policy"].__setitem__("acceptance_effect", "pass"),
                "PROMOTION_CLAIM",
            ),
            (
                "gate_refuses_limit",
                lambda r: r["binding"].__setitem__("limit", 100),
                "ARGV_PIN_DRIFT",
            ),
            (
                "gate_refuses_argv_identity",
                lambda r: r["immutable_attempt_identity"].__setitem__("argv_sha256", "0" * 64),
                "ARGV_PIN_DRIFT",
            ),
            (
                "gate_refuses_corpus_drift",
                lambda r: r["corpus"].__setitem__("consultant_xml_count", 1),
                "CORPUS_COUNT_DRIFT",
            ),
            (
                "gate_refuses_predicate_contradiction",
                lambda r: r.__setitem__(
                    "predicates", {"full_walk": False, "timeout": False, "outcome": "nonzero"}
                ),
                "PREDICATE_CONTRADICTION",
            ),
            (
                "gate_refuses_terminal_redefinition",
                lambda r: r.__setitem__(
                    "terminal",
                    {
                        "outcome": "timeout",
                        "exit_code": None,
                        "signal": "SIGTERM",
                        "timeout": True,
                    },
                ),
                "PREDICATE_CONTRADICTION",
            ),
        ):
            mutant = copy.deepcopy(published)
            mutate(mutant)
            _expect_code(
                problems,
                name,
                diagnostic,
                lambda m=mutant: check_receipt(stub_root, m, schema, SCHEMAS_REL),
            )

        duration_free = copy.deepcopy(published)
        duration_free["duration_ms"] = 0
        swept = check_receipt(stub_root, duration_free, schema, SCHEMAS_REL)
        _expect_true(
            problems,
            "gate_ignores_duration_for_the_verdict",
            f"a zero duration moved the verdict: {swept['predicates']!r}",
            swept["predicates"]["outcome"] == "full_walk",
        )

        _expect_code(
            problems,
            "write_once_second_run_is_refused",
            "C4_RECEIPT_DRIFT",
            lambda: cmd_run(run_args, stub_root),
        )

    with tempfile.TemporaryDirectory() as raw_tmp:
        refuse_root = Path(raw_tmp)
        _stub_root(refuse_root, root)
        refuse_args = build_parser().parse_args(
            [
                "run",
                "--repo-root",
                str(refuse_root),
                "--attempt-id",
                "m207-s07-c4-stub-refuse-002",
            ]
        )
        os.environ["NPA_S07_STUB_MODE"] = "refuse"
        try:
            with _quiet_recorder():
                code = cmd_run(refuse_args, refuse_root)
        finally:
            os.environ.pop("NPA_S07_STUB_MODE", None)
        _expect_true(
            problems, "allowlist_refusal_publishes_a_receipt", f"cmd_run returned {code}", code == 0
        )
        refused = _expect_published_receipt(problems, refuse_root)
        if refused is not None:
            _expect_true(
                problems,
                "allowlist_refusal_is_a_lawful_nonzero",
                f"receipt {refused.get('predicates')!r} / {refused.get('failure_policy')!r}",
                refused["predicates"]["outcome"] == "nonzero"
                and refused["terminal"]["exit_code"] == 3
                and refused["failure_policy"]["sidecar_rows"] == 0
                and refused["failure_policy"]["aggregate_failed"] == 1,
            )
            summary = check_receipt(refuse_root, refused, schema, SCHEMAS_REL)
            _expect_true(
                problems,
                "allowlist_refusal_passes_the_read_gate",
                f"gate summary {summary!r}",
                summary["predicates"]["outcome"] == "nonzero",
            )


def run_recorder_selftest(root: Path) -> int:
    """Every hostile recorder/failure-policy path must produce its named diagnostic."""
    problems: list[str] = []
    try:
        schema = load_json(root / SCHEMAS_REL, "S07 schema document")
        check_recorder_schema(schema)

        _expect_code(
            problems, "attempt_id_not_a_slug", "USAGE", lambda: check_attempt_id("M207-S07-Bad")
        )
        _expect_code(
            problems,
            "attempt_id_missing_number",
            "USAGE",
            lambda: check_attempt_id("m207-s07-c4-full-walk"),
        )
        _expect_code(
            problems, "budget_below_minimum", "BUDGET_BELOW_MINIMUM", lambda: check_budget(3599)
        )
        _expect_code(
            problems,
            "profile_drift",
            "ARGV_PIN_DRIFT",
            lambda: check_pinned_binding("decode", FROZEN_JOBS),
        )
        _expect_code(
            problems,
            "jobs_drift",
            "ARGV_PIN_DRIFT",
            lambda: check_pinned_binding(FROZEN_PROFILE, 4),
        )
        _expect_code(
            problems,
            "source_revision_empty",
            "MISSING_INPUT",
            lambda: check_source_revision("   "),
        )
        _expect_code(
            problems,
            "source_revision_digest",
            "MISSING_INPUT",
            lambda: check_source_revision("a" * 64),
        )

        binary = root / DEFAULT_BINARY_REL
        corpus = root / DEFAULT_CONSULTANT_REL
        garant = root / DEFAULT_GARANT_REL
        contract = root / DEFAULT_CONTRACT_REL
        sidecar = root / ATTEMPT_DIR_REL / DEFAULT_ATTEMPT_ID / SIDECAR_FILENAME
        pinned_argv = build_argv(binary, corpus, garant, contract, "pin", sidecar)
        _expect_true(
            problems,
            "built_argv_never_carries_limit",
            f"--limit leaked into {pinned_argv!r}",
            "--limit" not in pinned_argv,
        )
        _expect_true(
            problems,
            "built_argv_carries_failures_out",
            f"{SIDECAR_ARG} missing from {pinned_argv!r}",
            SIDECAR_ARG in pinned_argv,
        )
        _expect_true(
            problems,
            "built_argv_never_carries_out",
            f"--out leaked into {pinned_argv!r}",
            "--out" not in pinned_argv,
        )
        _expect_code(
            problems,
            "argv_limit_forbidden",
            "ARGV_PIN_DRIFT",
            lambda: check_argv_shape([*pinned_argv, "--limit", "10"]),
        )
        _expect_code(
            problems,
            "argv_out_forbidden",
            "ARGV_PIN_DRIFT",
            lambda: check_argv_shape([*pinned_argv, "--out", "/tmp/x"]),
        )
        _expect_code(
            problems,
            "argv_missing_failures_out",
            "ARGV_PIN_DRIFT",
            lambda: check_argv_shape([p for p in pinned_argv if p != SIDECAR_ARG][:-1]),
        )

        evidence = root / EVIDENCE_DIR_REL
        _expect_code(
            problems,
            "frozen_s04_receipt_target",
            "C4_RECEIPT_DRIFT",
            lambda: assert_write_allowed(
                root,
                schema,
                evidence / "m207-s04-c4-operational-receipt.json",
                "the receipt path",
            ),
        )
        _expect_code(
            problems,
            "frozen_m204_receipt_target",
            "C4_RECEIPT_DRIFT",
            lambda: assert_write_allowed(
                root,
                schema,
                evidence / "m204-s06-c4-operational-receipt.json",
                "the receipt path",
            ),
        )
        _expect_code(
            problems,
            "frozen_s04_attempt_prefix",
            "C4_RECEIPT_DRIFT",
            lambda: assert_write_allowed(
                root,
                schema,
                evidence / "m207-s04-c4-attempts" / DEFAULT_ATTEMPT_ID / FROZEN_LOG_FILES[0],
                "the attempt log directory",
            ),
        )
        _expect_code(
            problems,
            "frozen_s03_evaluation_report",
            "C4_RECEIPT_DRIFT",
            lambda: assert_write_allowed(
                root,
                schema,
                evidence / "m207-s03-evaluation-report.json",
                "the receipt path",
            ),
        )
        _expect_code(
            problems,
            "frozen_seed_sidecar",
            "C4_RECEIPT_DRIFT",
            lambda: assert_write_allowed(
                root,
                schema,
                root / "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json",
                "the receipt path",
            ),
        )

        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            live_receipt = tmp / "receipt.json"
            live_receipt.write_text("{}\n", encoding="utf-8")
            _expect_code(
                problems,
                "write_once_existing_receipt",
                "C4_RECEIPT_DRIFT",
                lambda: assert_write_targets_free(
                    root, live_receipt, tmp / "attempt", resume_orphan_logs=False
                ),
            )
            orphan = tmp / "attempt"
            orphan.mkdir()
            (orphan / FROZEN_LOG_FILES[0]).write_text("{}\n", encoding="utf-8")
            _expect_code(
                problems,
                "orphan_attempt_logs",
                "ATTEMPT_LOG_MISSING",
                lambda: assert_write_targets_free(
                    root, tmp / "absent.json", orphan, resume_orphan_logs=False
                ),
            )
            view = assert_write_targets_free(
                root, tmp / "absent.json", orphan, resume_orphan_logs=True
            )
            _expect_true(
                problems,
                "orphan_attempt_resume_is_lawful",
                f"resume-orphan-logs was refused: {view!r}",
                view["attempt_dir_nonempty"] is True,
            )

            policy = schema["failure_policy"]
            prefix = policy["provider_roots"]["consultant"]
            lawful = {
                "record_kind": policy["record_kind_value"],
                "schema": SIDECAR_SCHEMA_ID,
                "provider": "consultant",
                "path": f"{prefix}a.xml",
                "class": "read",
            }
            sidecar_path = tmp / "failures.jsonl"
            _write_sidecar(sidecar_path, [lawful])
            _expect_true(
                problems,
                "lawful_sidecar_row_is_accepted",
                "a lawful sidecar row was refused",
                len(load_sidecar(sidecar_path, schema)) == 1,
            )
            for name, mutant, diagnostic in (
                (
                    "sidecar_extra_key",
                    {**lawful, "retry": 1},
                    "SIDECAR_KEY_DRIFT",
                ),
                (
                    "sidecar_record_kind",
                    {**lawful, "record_kind": "ok"},
                    "SIDECAR_KEY_DRIFT",
                ),
                (
                    "sidecar_schema",
                    {**lawful, "schema": "npa-contour-failure-trace/v2"},
                    "SIDECAR_KEY_DRIFT",
                ),
                (
                    "sidecar_provider",
                    {**lawful, "provider": "other"},
                    "SIDECAR_PROVIDER_DRIFT",
                ),
                ("sidecar_class", {**lawful, "class": "parse"}, "SIDECAR_CLASS_DRIFT"),
                (
                    "sidecar_path_escape",
                    {**lawful, "path": "../outside.xml"},
                    "SIDECAR_PATH_ESCAPE",
                ),
                (
                    "sidecar_path_wrong_provider_root",
                    {**lawful, "path": "law-source/garant/a.xml"},
                    "SIDECAR_PATH_ESCAPE",
                ),
                (
                    "sidecar_path_absolute",
                    {**lawful, "path": "/etc/passwd"},
                    "SIDECAR_PATH_ESCAPE",
                ),
            ):
                _write_sidecar(sidecar_path, [mutant])
                _expect_code(
                    problems,
                    name,
                    diagnostic,
                    lambda path=sidecar_path: load_sidecar(path, schema),
                )
            sidecar_path.write_text("{not json\n", encoding="utf-8")
            _expect_code(
                problems,
                "sidecar_not_json",
                "MALFORMED_RECEIPT",
                lambda: load_sidecar(sidecar_path, schema),
            )
        _expect_code(
            problems,
            "cli_limit_is_refused_by_name",
            "ARGV_PIN_DRIFT",
            lambda: cmd_run(
                build_parser().parse_args(
                    [
                        "run",
                        "--repo-root",
                        str(root),
                        "--attempt-id",
                        DEFAULT_ATTEMPT_ID,
                        "--limit",
                        "5",
                    ]
                ),
                root,
            ),
        )
        _recorder_end_to_end(problems, root, schema)
    except GateError as exc:
        problems.append(f"recorder selftest could not run: {exc.diagnostic}: {exc.detail}")
    except Exception as exc:  # noqa: BLE001 - fail-closed: report, never a bare traceback
        problems.append(f"recorder selftest could not run: {type(exc).__name__}: {exc}")

    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(
            f"FAIL M207_S07_C4_RECORDER_SELFTEST: {len(problems)} hostile path(s) not proven",
            file=sys.stderr,
        )
        return 1
    print(RECORDER_SELFTEST_MARKER)
    return 0


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def refusal_payload(
    diagnostic: str, detail: str, schema_id: str = CLASSIFICATION_SCHEMA_ID
) -> dict[str, Any]:
    return {
        "schema": schema_id,
        "status": "refused",
        "diagnostic": diagnostic,
        "detail": detail,
        "acceptance_effect": "none",
    }


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def report_failure(
    exc: GateError, gate: str = GATE_NAME, schema_id: str = CLASSIFICATION_SCHEMA_ID
) -> int:
    emit(refusal_payload(exc.diagnostic, exc.detail, schema_id))
    print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
    print(
        f"FAIL {gate}: nothing was published; the frozen successor contract is not satisfied",
        file=sys.stderr,
    )
    return 1


def cmd_classify(root: Path, schemas_rel: str = SCHEMAS_REL) -> int:
    payload = classify_root(root, schemas_rel)
    emit(payload)
    print(MARKER, file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Negative proof: every hostile mutation must produce its named diagnostic.
# --------------------------------------------------------------------------- #


def _expect_code(problems: list[str], name: str, expected: str, thunk: Callable[[], Any]) -> None:
    try:
        thunk()
    except GateError as exc:
        if exc.diagnostic != expected:
            problems.append(
                f"hostile case {name!r} raised {exc.diagnostic}, expected {expected}: {exc.detail}"
            )
        return
    problems.append(f"hostile case {name!r} did not raise {expected}")


def _expect_true(problems: list[str], name: str, detail: str, condition: bool) -> None:
    if not condition:
        problems.append(f"{name} failed: {detail}")


def _expect_file_case(
    problems: list[str],
    name: str,
    thunk: Callable[[], dict[str, Any]],
    base_schema: dict[str, Any],
    expectations: dict[str, str],
) -> None:
    """Require a successful classification whose named receipts carry the expected outcome."""
    try:
        payload = thunk()
    except GateError as exc:
        problems.append(
            f"hostile case {name!r} raised {exc.diagnostic}, expected {expectations}: {exc.detail}"
        )
        return
    by_path = {item["path"]: item for item in payload["receipts"]}
    for key, expected in expectations.items():
        rel = str(_frozen_entry(base_schema, key)["path"])
        item = by_path.get(rel)
        if item is None:
            problems.append(f"hostile case {name!r}: no classification published for {rel}")
            continue
        if item["outcome"] != expected or not (
            item["full_walk"] is (expected == "full_walk")
            and item["timeout"] is (expected == "timeout")
        ):
            problems.append(
                f"hostile case {name!r}: {rel} classified as {item['outcome']!r} "
                f"(full_walk={item['full_walk']}, timeout={item['timeout']}), expected {expected!r}"
            )


def _tree_digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _fixture_tree(base: Path, source_root: Path) -> None:
    """Copy the frozen protocol, schema and both pinned receipts into a temp tree."""
    schema = load_json(source_root / SCHEMAS_REL, "S07 schema document")
    rels: list[str] = [PROTOCOL_REL, SCHEMAS_REL]
    for key in CLASSIFY_SOURCE_KEYS:
        entry = _frozen_entry(schema, key)
        rels.append(str(entry["path"]))
        receipt = load_json(source_root / str(entry["path"]), key)
        logs = receipt.get("logs") if isinstance(receipt, dict) else None
        if not isinstance(logs, dict) or not isinstance(logs.get("stdout"), str):
            raise GateError("MALFORMED_RECEIPT", f"{key} receipt carries no logs.stdout path")
        rels.append(str(logs["stdout"]))
    for rel in rels:
        destination = base / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / rel, destination)


def _fixture_schema(root: Path) -> dict[str, Any]:
    return load_json(root / SCHEMAS_REL, "fixture S07 schema document")


def _case(tmp: Path, base: Path, name: str) -> tuple[Path, dict[str, Any]]:
    root = tmp / name
    shutil.copytree(base, root)
    return root, _fixture_schema(root)


def _read_fixture(root: Path, schema: dict[str, Any], key: str) -> dict[str, Any]:
    return load_json(root / str(_frozen_entry(schema, key)["path"]), f"fixture receipt {key}")


def _write_receipt(root: Path, schema: dict[str, Any], key: str, receipt: dict[str, Any]) -> None:
    """Rewrite a fixture receipt and re-pin it, keeping the fixture tree self-consistent."""
    rel = str(_frozen_entry(schema, key)["path"])
    (root / rel).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    _repin(root, schema, key, rel)


def _repin(root: Path, schema: dict[str, Any], key: str, rel: str) -> None:
    document = _fixture_schema(root)
    document["frozen_sources"][key]["sha256"] = sha256_file(root / rel)
    (root / SCHEMAS_REL).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    schema.clear()
    schema.update(document)


def _rewrite_log(
    root: Path,
    schema: dict[str, Any],
    key: str,
    transform: Callable[[str], str],
    *,
    resync_receipt_digest: bool = True,
) -> None:
    receipt = _read_fixture(root, schema, key)
    log_path = root / str(receipt["logs"]["stdout"])
    log_path.write_text(transform(log_path.read_text(encoding="utf-8")), encoding="utf-8")
    if not resync_receipt_digest:
        return
    digest = sha256_file(log_path)
    receipt["logs"]["stdout_sha256"] = digest
    observed = receipt.get("observed_output")
    if isinstance(observed, dict):
        observed["stdout_sha256"] = digest
    _write_receipt(root, schema, key, receipt)


def _rewrite_schema(
    root: Path, schema: dict[str, Any], mutate: Callable[[dict[str, Any]], None]
) -> None:
    document = _fixture_schema(root)
    mutate(document)
    (root / SCHEMAS_REL).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    schema.clear()
    schema.update(document)


def _rewrite_protocol(root: Path, transform: Callable[[str], str]) -> None:
    path = root / PROTOCOL_REL
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def _predicate_duration_sweep(
    problems: list[str], s04: dict[str, Any], s04_rows: list[dict[str, Any]]
) -> None:
    """The S04 verdict must not move with duration_ms: duration is recorded, never an input."""
    moved: list[tuple[Any, Any, Any]] = []
    for duration in (0, 1, 1009, 387174, BUDGET_SECONDS_MINIMUM * 1000, 10**9):
        candidate = copy.deepcopy(s04)
        candidate["duration_ms"] = duration
        candidate["budget_seconds"] = BUDGET_SECONDS_MINIMUM
        report = classify(candidate, copy.deepcopy(s04_rows))
        moved.append((duration, report["outcome"], report["full_walk"]))
    _expect_true(
        problems,
        "duration_floor_is_not_a_predicate_input",
        f"the S04 verdict moved when duration_ms moved: {moved}",
        all(outcome == "full_walk" and full is True for _, outcome, full in moved),
    )


def run_selftest(source_root: Path) -> int:
    problems: list[str] = []
    try:
        assert_no_frozen_acceptance_rule()
        with tempfile.TemporaryDirectory(prefix="m207-s07-classify-") as raw:
            tmp = Path(raw)
            base = tmp / "base"
            base.mkdir(parents=True)
            _fixture_tree(base, source_root)
            base_schema = _fixture_schema(base)

            # --- green baseline over the historical bytes (copies, never the originals) ---
            before = _tree_digest(base)
            payload = classify_root(base)
            after = _tree_digest(base)
            _expect_true(
                problems,
                "read_only",
                "classification created or modified a file in the fixture tree",
                before == after,
            )
            _expect_true(
                problems,
                "baseline_count",
                f"expected {len(CLASSIFY_SOURCE_KEYS)} classified receipts, "
                f"saw {len(payload['receipts'])}",
                len(payload["receipts"]) == len(CLASSIFY_SOURCE_KEYS),
            )
            by_path = {item["path"]: item for item in payload["receipts"]}
            for key, expected in ((KEY_S04, "full_walk"), (KEY_M204, "timeout")):
                rel = str(_frozen_entry(base_schema, key)["path"])
                item = by_path[rel]
                _expect_true(
                    problems,
                    f"baseline_outcome_{key}",
                    f"{rel} classified as {item['outcome']!r}, expected {expected!r}",
                    item["outcome"] == expected,
                )
                _expect_true(
                    problems,
                    f"baseline_flags_{key}",
                    f"{rel} flags full_walk={item['full_walk']} timeout={item['timeout']}",
                    item["full_walk"] is (expected == "full_walk")
                    and item["timeout"] is (expected == "timeout"),
                )
                _expect_true(
                    problems,
                    f"baseline_sha_{key}",
                    f"{rel} sha256_before {item['sha256_before']} != sha256_after "
                    f"{item['sha256_after']}",
                    item["sha256_before"] == item["sha256_after"],
                )
                _expect_true(
                    problems,
                    f"baseline_claim_{key}",
                    f"{rel} claims.operational_acceptance is "
                    f"{item['claims_operational_acceptance']!r}, historical receipts stay non-pass",
                    item["claims_operational_acceptance"] == "non-pass",
                )

            # --- predicate-level negatives over in-memory copies of the frozen shapes ---
            s04 = _read_fixture(base, base_schema, KEY_S04)
            s04_rows = load_jsonl(base / str(s04["logs"]["stdout"]))
            m204 = _read_fixture(base, base_schema, KEY_M204)
            m204_rows = load_jsonl(base / str(m204["logs"]["stdout"]))

            _expect_true(
                problems,
                "s04_short_complete_is_lawful",
                "the S04 walk must be a full walk although duration_ms < budget_seconds * 1000",
                int(s04["duration_ms"]) < int(s04["budget_seconds"]) * 1000
                and predicate_full_walk(s04, copy.deepcopy(s04_rows))["full_walk"] is True,
            )
            _expect_true(
                problems,
                "timeout_is_not_full_walk",
                "the M204 timeout must not satisfy full_walk",
                predicate_full_walk(m204, m204_rows)["full_walk"] is False
                and predicate_timeout(m204)["timeout"] is True,
            )

            limited_rows = copy.deepcopy(s04_rows)
            for row in limited_rows:
                if row.get("record_kind") in ("header", "canonical_payload"):
                    row["limit"] = 5
            _expect_true(
                problems,
                "limit_is_not_full_walk",
                "header/canonical limit=5 must not be a full walk",
                predicate_full_walk(copy.deepcopy(s04), limited_rows)["full_walk"] is False,
            )
            _expect_code(
                problems,
                "limit_complete_contradicts",
                "PREDICATE_CONTRADICTION",
                lambda: classify(copy.deepcopy(s04), copy.deepcopy(limited_rows)),
            )
            claims_pass = copy.deepcopy(s04)
            claims_pass["claims"] = {"operational_acceptance": "pass"}
            _expect_true(
                problems,
                "claims_do_not_classify",
                "a claims.operational_acceptance of 'pass' must not turn a limited walk into a "
                "full walk",
                predicate_full_walk(claims_pass, copy.deepcopy(limited_rows))["full_walk"] is False,
            )
            argv_limited = copy.deepcopy(s04)
            argv_limited["argv"] = [*argv_limited["argv"], "--limit", "5"]
            _expect_true(
                problems,
                "argv_limit_is_not_full_walk",
                "--limit in argv must not be a full walk",
                predicate_full_walk(argv_limited, copy.deepcopy(s04_rows))["full_walk"] is False,
            )
            short_files = copy.deepcopy(s04_rows)
            for row in short_files:
                if row.get("record_kind") == "aggregate":
                    row["files"] = PIN_AGGREGATE_FILES - 1
            _expect_true(
                problems,
                "aggregate_files_pin",
                "aggregate.files below the pin must not be a full walk",
                predicate_full_walk(copy.deepcopy(s04), short_files)["full_walk"] is False,
            )
            _predicate_duration_sweep(problems, s04, s04_rows)

            # --- file-level hostile cases, each in its own copy of the fixture tree ---
            for name, diagnostic, thunk in (
                ("missing_stdout_log", "MISSING_INPUT", lambda: _case_missing_log(tmp, base)),
                ("malformed_jsonl", "MALFORMED_RECEIPT", lambda: _case_broken_jsonl(tmp, base)),
                (
                    "aggregate_row_absent",
                    "MALFORMED_RECEIPT",
                    lambda: _case_missing_row(tmp, base, "aggregate"),
                ),
                (
                    "canonical_row_absent",
                    "MALFORMED_RECEIPT",
                    lambda: _case_missing_row(tmp, base, "canonical_payload"),
                ),
                (
                    "aggregate_row_duplicated",
                    "MALFORMED_RECEIPT",
                    lambda: _case_duplicate_row(tmp, base),
                ),
                ("malformed_receipt", "MALFORMED_RECEIPT", lambda: _case_broken_receipt(tmp, base)),
                (
                    "timeout_without_shape",
                    "TERMINAL_OUTCOME_DRIFT",
                    lambda: _case_timeout_signal(tmp, base),
                ),
                (
                    "complete_with_timeout_flag",
                    "PREDICATE_CONTRADICTION",
                    lambda: _case_complete_with_timeout_flag(tmp, base),
                ),
                ("pin_drift", "C4_RECEIPT_DRIFT", lambda: _case_pin_drift(tmp, base)),
                ("log_drift", "C4_RECEIPT_DRIFT", lambda: _case_log_drift(tmp, base)),
                ("unsafe_path", "UNSAFE_PATH", lambda: _case_unsafe_path(tmp, base)),
                (
                    "bytes_changed_under_read",
                    "HISTORICAL_BYTES_CHANGED",
                    lambda: _case_bytes_changed(tmp, base),
                ),
                ("schema_absent", "MISSING_INPUT", lambda: _case_schema_absent(tmp, base)),
                ("receipt_absent", "MISSING_INPUT", lambda: _case_receipt_absent(tmp, base)),
                (
                    "frozen_sources_absent",
                    "MISSING_INPUT",
                    lambda: _case_frozen_sources_absent(tmp, base),
                ),
                (
                    "protocol_code_removed",
                    "PROTOCOL_DIAGNOSTIC_DRIFT",
                    lambda: _case_protocol_code_removed(tmp, base),
                ),
                (
                    "schema_diagnostics_removed",
                    "PROTOCOL_DIAGNOSTIC_DRIFT",
                    lambda: _case_schema_diagnostics_removed(tmp, base),
                ),
                (
                    "schema_outcomes_shortened",
                    "TERMINAL_OUTCOME_DRIFT",
                    lambda: _case_schema_outcomes(tmp, base),
                ),
                (
                    "schema_pin_moved",
                    "PREDICATE_CONTRADICTION",
                    lambda: _case_schema_pin_moved(tmp, base),
                ),
                (
                    "schema_duration_floor",
                    "DURATION_FLOOR_AS_ACCEPTANCE",
                    lambda: _case_schema_duration_floor(tmp, base),
                ),
            ):
                _expect_code(problems, name, diagnostic, thunk)

            # --- positive controls: honest nonzero, launch error and timeout stay closed ---
            _expect_file_case(
                problems,
                "nonzero_exit",
                lambda: _case_nonzero(tmp, base),
                base_schema,
                {KEY_S04: "nonzero"},
            )
            _expect_file_case(
                problems,
                "launch_error",
                lambda: _case_launch_error(tmp, base),
                base_schema,
                {KEY_S04: "launch_error"},
            )
            _expect_file_case(
                problems,
                "run_status_is_not_terminal_evidence",
                lambda: _case_run_status_is_not_evidence(tmp, base),
                base_schema,
                {KEY_S04: "timeout"},
            )
    except GateError as exc:
        problems.append(f"selftest could not run: {exc.diagnostic}: {exc.detail}")
    except Exception as exc:  # noqa: BLE001 - fail-closed: report, never a bare traceback
        problems.append(f"selftest could not run: {type(exc).__name__}: {exc}")

    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(
            f"FAIL M207_S07_C4_CLASSIFY_SELFTEST: {len(problems)} hostile path(s) not proven",
            file=sys.stderr,
        )
        return 1
    print(SELFTEST_MARKER)
    return 0


def _case_missing_log(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "missing_log")
    receipt = _read_fixture(root, schema, KEY_S04)
    (root / str(receipt["logs"]["stdout"])).unlink()
    classify_root(root)


def _case_broken_jsonl(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "broken_jsonl")
    _rewrite_log(root, schema, KEY_S04, lambda text: text + "{not json\n")
    classify_root(root)


def _case_missing_row(tmp: Path, base: Path, kind: str) -> None:
    def transform(text: str) -> str:
        kept = [line for line in text.splitlines() if f'"record_kind":"{kind}"' not in line]
        return "\n".join(kept) + "\n"

    root, schema = _case(tmp, base, f"missing_{kind}")
    _rewrite_log(root, schema, KEY_S04, transform)
    classify_root(root)


def _case_duplicate_row(tmp: Path, base: Path) -> None:
    def transform(text: str) -> str:
        lines = text.splitlines()
        aggregate = [line for line in lines if '"record_kind":"aggregate"' in line]
        return "\n".join([*lines, *aggregate]) + "\n"

    root, schema = _case(tmp, base, "duplicate_aggregate")
    _rewrite_log(root, schema, KEY_S04, transform)
    classify_root(root)


def _case_broken_receipt(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "broken_receipt")
    rel = str(_frozen_entry(schema, KEY_S04)["path"])
    path = root / rel
    broken = path.read_text(encoding="utf-8").replace('"terminal"', '"termin@l"', 1)
    path.write_text(broken, encoding="utf-8")
    _repin(root, schema, KEY_S04, rel)
    classify_root(root)


def _case_nonzero(tmp: Path, base: Path) -> dict[str, Any]:
    root, schema = _case(tmp, base, "nonzero")
    receipt = _read_fixture(root, schema, KEY_S04)
    receipt["terminal"] = {"outcome": "nonzero", "exit_code": 3, "signal": None, "timeout": False}
    _write_receipt(root, schema, KEY_S04, receipt)
    return classify_root(root)


def _case_launch_error(tmp: Path, base: Path) -> dict[str, Any]:
    root, schema = _case(tmp, base, "launch_error")
    receipt = _read_fixture(root, schema, KEY_S04)
    receipt["terminal"] = {
        "outcome": "launch_error",
        "exit_code": None,
        "signal": None,
        "timeout": False,
        "error": "no such binary",
    }
    _write_receipt(root, schema, KEY_S04, receipt)
    return classify_root(root)


def _case_timeout_signal(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "timeout_sigkill")
    receipt = _read_fixture(root, schema, KEY_M204)
    receipt["terminal"]["signal"] = "SIGKILL"
    _write_receipt(root, schema, KEY_M204, receipt)
    classify_root(root)


def _case_complete_with_timeout_flag(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "complete_timeout_flag")
    receipt = _read_fixture(root, schema, KEY_S04)
    receipt["terminal"]["timeout"] = True
    _write_receipt(root, schema, KEY_S04, receipt)
    classify_root(root)


def _case_run_status_is_not_evidence(tmp: Path, base: Path) -> dict[str, Any]:
    """A log whose operational_envelope says complete must not override a timeout terminal."""
    root, schema = _case(tmp, base, "run_status_not_evidence")
    receipt = _read_fixture(root, schema, KEY_S04)
    receipt["terminal"] = {
        "outcome": "timeout",
        "exit_code": None,
        "signal": "SIGTERM",
        "timeout": True,
    }
    _write_receipt(root, schema, KEY_S04, receipt)
    return classify_root(root)


def _case_pin_drift(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "pin_drift")
    receipt = _read_fixture(root, schema, KEY_S04)
    receipt["duration_ms"] = 1
    rel = str(_frozen_entry(schema, KEY_S04)["path"])
    (root / rel).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    classify_root(root)


def _case_log_drift(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "log_drift")
    _rewrite_log(
        root,
        schema,
        KEY_S04,
        lambda text: text.replace('"files":43797', '"files":43798', 1),
        resync_receipt_digest=False,
    )
    classify_root(root)


def _case_unsafe_path(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "unsafe_path")

    def mutate(document: dict[str, Any]) -> None:
        document["frozen_sources"][KEY_S04]["path"] = "../escape.json"

    _rewrite_schema(root, schema, mutate)
    classify_root(root)


def _case_bytes_changed(tmp: Path, base: Path) -> None:
    root, _schema = _case(tmp, base, "bytes_changed")

    def between_reads(key: str, path: Path) -> None:
        if key == KEY_S04:
            with path.open("ab") as stream:
                stream.write(b"\n")

    classify_root(root, between_reads=between_reads)


def _case_schema_absent(tmp: Path, base: Path) -> None:
    root, _schema = _case(tmp, base, "schema_absent")
    (root / SCHEMAS_REL).unlink()
    classify_root(root)


def _case_receipt_absent(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "receipt_absent")
    (root / str(_frozen_entry(schema, KEY_S04)["path"])).unlink()
    classify_root(root)


def _case_frozen_sources_absent(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "frozen_sources_absent")
    _rewrite_schema(root, schema, lambda document: document.pop("frozen_sources"))
    classify_root(root)


def _case_protocol_code_removed(tmp: Path, base: Path) -> None:
    root, _schema = _case(tmp, base, "protocol_code_removed")
    _rewrite_protocol(root, lambda text: text.replace("\nHISTORICAL_BYTES_CHANGED\n", "\n", 1))
    classify_root(root)


def _case_schema_diagnostics_removed(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "schema_diagnostics_removed")

    def mutate(document: dict[str, Any]) -> None:
        document["diagnostics"].remove("HISTORICAL_BYTES_CHANGED")

    _rewrite_schema(root, schema, mutate)
    classify_root(root)


def _case_schema_outcomes(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "schema_outcomes")

    def mutate(document: dict[str, Any]) -> None:
        document["predicates"]["outcomes"] = ["full_walk", "timeout", "nonzero"]

    _rewrite_schema(root, schema, mutate)
    classify_root(root)


def _case_schema_pin_moved(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "schema_pin_moved")

    def mutate(document: dict[str, Any]) -> None:
        document["predicates"]["full_walk"]["aggregate_files_equals"] = PIN_AGGREGATE_FILES - 1

    _rewrite_schema(root, schema, mutate)
    classify_root(root)


def _case_schema_duration_floor(tmp: Path, base: Path) -> None:
    root, schema = _case(tmp, base, "schema_duration_floor")

    def mutate(document: dict[str, Any]) -> None:
        document["predicates"]["duration_floor_is_not_acceptance"] = False

    _rewrite_schema(root, schema, mutate)
    classify_root(root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m207_s07_c4_run.py", description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify_parser = subparsers.add_parser(
        "classify",
        help="classify the pinned historical receipts read-only and print the canonical JSON",
    )
    classify_parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="repository root the frozen paths are resolved against (default: the cwd)",
    )
    classify_parser.add_argument(
        "--schemas", default=SCHEMAS_REL, help="schema path under the root"
    )

    selftest_parser = subparsers.add_parser(
        "selftest",
        help="prove the named negative paths of the classifier against planted fixtures",
    )
    selftest_parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="root the fixture material is copied from (default: this checkout)",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="record one new S07 attempt under a new identity (write-once); --dry-run writes nothing",
    )
    run_parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="repository root the pinned paths are resolved against (default: the cwd)",
    )
    run_parser.add_argument("--schemas", default=SCHEMAS_REL, help="schema path under the root")
    run_parser.add_argument(
        "--binary", default=DEFAULT_BINARY_REL, help="release diagnostic binary"
    )
    run_parser.add_argument(
        "--consultant-root", default=DEFAULT_CONSULTANT_REL, help="declared consultant corpus root"
    )
    run_parser.add_argument(
        "--garant-root", default=DEFAULT_GARANT_REL, help="declared Garant root"
    )
    run_parser.add_argument("--contract", default=DEFAULT_CONTRACT_REL, help="acceptance contract")
    run_parser.add_argument(
        "--parser-source",
        default=DEFAULT_PARSER_SOURCE_REL,
        help="parser source holding the revision",
    )
    run_parser.add_argument(
        "--attempt-id",
        required=True,
        help=f"new identity under the m207-s07-* namespace (template {DEFAULT_ATTEMPT_ID})",
    )
    run_parser.add_argument("--profile", default=FROZEN_PROFILE)
    run_parser.add_argument("--jobs", type=int, default=FROZEN_JOBS)
    run_parser.add_argument("--budget-seconds", type=int, default=BUDGET_SECONDS_MINIMUM)
    run_parser.add_argument("--source-revision", default=DEFAULT_SOURCE_REVISION)
    run_parser.add_argument(
        "--out", default=None, help="receipt path override, allowed only inside the evidence dir"
    )
    run_parser.add_argument(
        "--resume-orphan-logs",
        action="store_true",
        help="reuse a non-empty attempt log directory whose attempt published no receipt",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the staged argv, receipt path and predicate preview without writing anything",
    )
    run_parser.add_argument(
        "--limit",
        default=None,
        help=argparse.SUPPRESS,
    )

    check_parser = subparsers.add_parser(
        "check", help="read-only gate over the published S07 successor receipt"
    )
    check_parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="repository root the pinned paths are resolved against (default: the cwd)",
    )
    check_parser.add_argument("--schemas", default=SCHEMAS_REL, help="schema path under the root")
    check_parser.add_argument(
        "--receipt", default=None, help="receipt path override (default: the pinned successor path)"
    )

    recorder_selftest_parser = subparsers.add_parser(
        "recorder-selftest",
        help="prove the named negative paths of the recorder and the failure policy",
    )
    recorder_selftest_parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="root the frozen paths are resolved from (default: this checkout)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    gate = GATE_NAME if args.command in ("classify", "selftest") else RECORDER_GATE_NAME
    schema_id = (
        CLASSIFICATION_SCHEMA_ID if args.command in ("classify", "selftest") else RECEIPT_SCHEMA_ID
    )
    try:
        if args.command == "classify":
            return cmd_classify(root, args.schemas)
        if args.command == "selftest":
            return run_selftest(root)
        if args.command == "run":
            return cmd_run(args, root)
        if args.command == "check":
            return cmd_check(args, root)
        return run_recorder_selftest(root)
    except GateError as exc:
        return report_failure(exc, gate, schema_id)
    except Exception as exc:  # noqa: BLE001 - fail-closed: never a bare traceback
        emit(refusal_payload("GATE_INTERNAL_ERROR", f"{type(exc).__name__}: {exc}", schema_id))
        print(f"FAIL GATE_INTERNAL_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
