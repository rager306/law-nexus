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
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S07_CLASSIFY_OK"
SELFTEST_MARKER = "M207_S07_C4_CLASSIFY_SELFTEST_OK"
GATE_NAME = "M207_S07_C4_CLASSIFY"

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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read an attempt JSONL log read-only.  Blank lines are skipped, a broken row is fatal."""
    text = _decode_text(path, "attempt stdout JSONL log")
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


def resolve_repo_path(root: Path, raw: Any, label: str) -> Path:
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
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must not escape the repository root")
    resolved = (root / relative).resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside the repository root")
    return resolved


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
# Commands
# --------------------------------------------------------------------------- #


def refusal_payload(diagnostic: str, detail: str) -> dict[str, Any]:
    return {
        "schema": CLASSIFICATION_SCHEMA_ID,
        "status": "refused",
        "diagnostic": diagnostic,
        "detail": detail,
        "acceptance_effect": "none",
    }


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def report_failure(exc: GateError) -> int:
    emit(refusal_payload(exc.diagnostic, exc.detail))
    print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
    print(
        f"FAIL {GATE_NAME}: no classification was published; the frozen successor contract "
        "is not satisfied",
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


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)

    try:
        if args.command == "classify":
            return cmd_classify(Path(args.repo_root).resolve(), args.schemas)
        return run_selftest(Path(args.repo_root).resolve())
    except GateError as exc:
        return report_failure(exc)
    except Exception as exc:  # noqa: BLE001 - fail-closed: never a bare traceback
        emit(refusal_payload("GATE_INTERNAL_ERROR", f"{type(exc).__name__}: {exc}"))
        print(f"FAIL GATE_INTERNAL_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
