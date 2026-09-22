#!/usr/bin/env python3
"""M207 S07 failure-policy gate: the sidecar policy is code, not prose (T04).

The S04 attempt published ``failed = 1`` with no identity at all: its attempt directory held only
``stdout.log`` and ``stderr.log``, and the five-row JSONL carries no path.  S07 adds the additive
``--failures-out`` sidecar, but a sidecar is only a file -- it can be padded by hand, bound to a
foreign path, or read as "no failures" while it is empty.  This module is the executable policy
that refuses each of those, and it is deliberately fail-closed: every refusal is a named,
machine-distinguishable diagnostic drawn from the successor contract's closed vocabulary.

Three commands:

* ``selftest`` -- proves the lawful cases (a short complete ``full_walk``, a ``timeout`` and an
  exit-3 allowlist refusal) and the hostile set against planted fixtures in a temp root, each
  hostile case with its own named code.  Prints ``M207_S07_POLICY_SELFTEST_OK``.
* ``check`` -- the read-only gate over one published attempt (the pinned successor receipt plus its
  attempt-directory sidecar).  Prints ``M207_S07_POLICY_OK``.

Nothing here accepts, promotes, scores or measures anything: ``acceptance_effect`` is ``none`` and
``promotion`` is ``none``.  Making a failure visible does not make it a measurement.

Standard library only (R064, ADR-0007); no network, no credentials, no PII.  The gate is read-only
except inside a throw-away ``tempfile`` root owned by ``selftest``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S07_POLICY_OK"
SELFTEST_MARKER = "M207_S07_POLICY_SELFTEST_OK"
GATE_NAME = "M207_S07_POLICY"
POLICY_REPORT_SCHEMA_ID = "m207-s07-policy-report/v1"

PROTOCOL_ID = "m207-s07-c4-protocol/v1"
SCHEMAS_ID = "m207-s07-schemas/v1"
RECEIPT_SCHEMA_ID = "m207-s07-c4-operational-successor/v1"
SIDECAR_SCHEMA_ID = "npa-contour-failure-trace/v1"
PROTOCOL_REL = "prd/annotation/m207-s07-c4-protocol.md"
SCHEMAS_REL = "prd/annotation/m207-s07-schemas.json"
DEFAULT_RECEIPT_REL = "prd/migration/rust-evidence/m207-s07-c4-operational-receipt.json"
ATTEMPT_DIR_REL = "prd/migration/rust-evidence/m207-s07-c4-attempts"
DEFAULT_ATTEMPT_ID = "m207-s07-c4-full-walk-001"
SIDECAR_FILENAME = "failures.jsonl"

# --- the reused failure sidecar closure (verbatim ``npa-contour-failure-trace/v1``) ----------
SIDECAR_KEYS = ("record_kind", "schema", "provider", "path", "class")
RECORD_KIND_VALUE = "failure"
PROVIDER_VALUES = ("consultant", "garant")
CLASS_VALUES = ("read", "digest", "decode", "toctou")
PROVIDER_ROOTS = {
    "consultant": "consru_export/consru_export/exports/",
    "garant": "law-source/garant/",
}
ACCEPTANCE_EFFECT_NONE = "none"
PROMOTION_NONE = "none"
HUMAN_PILOT_PERFORMED = False
S03_RATES_STATUS = "not-measured"

PIN_CONSULTANT_XML_COUNT = 43785
PIN_GARANT_FILE_COUNT = 12
PIN_AGGREGATE_FILES = 43797
PIN_SEED_FRAGMENTS = 180
BUDGET_SECONDS_MINIMUM = 3600
OUTCOME_VALUES = ("full_walk", "timeout", "nonzero", "launch_error")
TERMINAL_OUTCOME_VALUES = ("complete", "timeout", "nonzero", "launch_error")
EXIT_OUT_UNWRITABLE = 3
ALLOWLIST_REFUSAL_CLASS = "allowlist_refusal"

# The closed successor receipt closure.  ``operational_acceptance`` is deliberately absent: the
# successor receipt classifies an attempt and never accepts it.
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

# A duration floor inside the receipt is the exact defect S07 exists to separate: the frozen S04
# rule read ``duration_ms >= budget_seconds * 1000`` as acceptance, and S07 must never import it.
DURATION_FLOOR_KEYS = (
    "duration_ms_minimum",
    "minimum_duration_ms",
    "duration_floor_ms",
    "duration_floor",
    "acceptance_duration_floor",
)
# S03 rates, aspects, strata and the human pilot are a different measurement convention; the
# successor receipt may not carry any of them, and ``human_pilot_performed`` may never be forced.
S03_RATE_KEYS = (
    "aspect",
    "aspects",
    "aspect_rate",
    "stratum",
    "strata",
    "stratum_rate",
    "rate",
    "rates",
    "agreement_rate",
    "measurement_status",
    "human_pilot_performed",
)
SEED_KEYS = ("seed_count", "seed_fragments", "seed_size", "seed_fragment_count")

# Integrity markers are statements about the tool that printed them; a receipt that carries one as
# a value is reading a marker as acceptance.
INTEGRITY_MARKERS = (
    "M207_S07_VERIFY_OK",
    "M207_S04_VERIFY_OK",
    "M207_S07_C4_RECEIPT_OK",
    "M207_S04_C4_RECEIPT_OK",
    "M207_S07_POLICY_OK",
    "M207_S07_SCHEMAS_OK",
    "M207_S07_CLASSIFY_OK",
    "M207_S04_PROMOTION_NONE_OK",
    "M207_S07_C4_DRYRUN_OK",
    "M207_S07_SCHEMAS_SELFTEST_OK",
    "M207_S07_C4_CLASSIFY_SELFTEST_OK",
    "M207_S07_C4_RECORDER_SELFTEST_OK",
    "M207_S07_POLICY_SELFTEST_OK",
)

DIGEST_FORMAT = "bare lowercase hex sha256, no algorithm prefix"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

DIAGNOSTICS_BEGIN = "<!-- s07-diagnostics:begin -->"
DIAGNOSTICS_END = "<!-- s07-diagnostics:end -->"
_DIAGNOSTIC_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

# The closed vocabulary of the whole successor contract, exactly as the protocol's machine-readable
# block declares it.  This tool refuses any drift from it in either direction.
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

# The subset this policy gate can speak.  Declared here so the adversarial suite can prove that
# every code the module can emit is a member of the frozen contract vocabulary.
POLICY_CODES = (
    "USAGE",
    "MISSING_INPUT",
    "MISSING_ARTIFACT",
    "MALFORMED_RECEIPT",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_VERSION_DRIFT",
    "C4_RECEIPT_DRIFT",
    "ARGV_PIN_DRIFT",
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
    "UNSAFE_PATH",
    "GATE_INTERNAL_ERROR",
)

# Every load-bearing policy check, in evaluation order.  Each one is wrapped in
# ``# --- pcheck:<id> ---`` markers so the adversarial suite can prove that removing any single
# check makes its hostile case pass instead of refusing.
POLICY_CHECK_IDS = (
    "protocol-vocabulary",
    "receipt-load",
    "schema-document",
    "acceptance-keys",
    "duration-floor",
    "s03-isolation",
    "schema-id",
    "closed-keys",
    "argv-binding",
    "sidecar-binding",
    "sidecar-rows",
    "sidecar-count",
    "predicates",
    "exit-class",
)

REPORT_KEYS = (
    "schema",
    "receipt",
    "attempt_id",
    "terminal",
    "aggregate",
    "sidecar_present",
    "sidecar_rows",
    "exit_class",
    "classification",
    "predicates",
    "duration_ms",
    "budget_seconds",
    "short_walk_is_not_timeout",
    "acceptance_effect",
    "promotion",
    "human_pilot_performed",
    "s03_rates_status",
    "seed_count",
    "diagnostics",
)

SUCCESSOR_NON_CLAIMS = [
    "not an acceptance: the policy gate publishes no verdict over the walk",
    "not gold: no policy report, sidecar row or marker is a gold label",
    "not a promotion: promotion stays none and no requirement status changes",
    "not a duration floor: a short complete full_walk is lawful and duration_ms is never an input",
    "not a failure identity for the historical run: the S04 failed = 1 file stays unidentified",
    "not an S03 rate: no aspect, stratum, agreement rate or human-pilot flag is imported",
    "not a seed enlargement: the 180 frozen fragments stay 180",
    "not a measurement: a visible failure is not a rate, a quality score or a retry surface",
]


class GateError(Exception):
    """Fatal, named failure that stops the gate before it publishes anything."""

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


def load_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    """Read one JSONL document read-only.  Blank lines are skipped, a broken row is fatal."""
    text = _decode_text(path, label)
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except ValueError as exc:
            raise GateError(
                "MALFORMED_RECEIPT", f"{label} line {number} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(row, dict):
            raise GateError("MALFORMED_RECEIPT", f"{label} line {number} is not a JSON object")
        rows.append(row)
    return rows


def display_under(root: Path, path: Path) -> str:
    root_abs = Path(os.path.abspath(root))
    candidate = Path(os.path.abspath(path))
    try:
        return candidate.relative_to(root_abs).as_posix()
    except ValueError:
        return candidate.as_posix()


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


def _dig(document: Any, *keys: str) -> Any:
    current = document
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _row_for(rows: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    matches = [row for row in rows if row.get("record_kind") == kind]
    if len(matches) > 1:
        raise GateError(
            "MALFORMED_RECEIPT",
            f"attempt JSONL carries {len(matches)} {kind!r} rows, expected at most one",
        )
    return matches[0] if matches else None


# --------------------------------------------------------------------------- #
# The two recomputable predicates (duration is never an input)
# --------------------------------------------------------------------------- #


def predicate_full_walk(receipt: Any, rows: list[dict[str, Any]]) -> bool:
    argv = _dig(receipt, "argv")
    if not isinstance(argv, list) or "--limit" in argv:
        return False
    if _dig(receipt, "binding", "limit") is not None:
        return False
    header = _row_for(rows, "header")
    canonical = _row_for(rows, "canonical_payload")
    aggregate = _row_for(rows, "aggregate")
    if header is None or canonical is None or aggregate is None:
        return False
    if header.get("limit") is not None or canonical.get("limit") is not None:
        return False
    if _dig(receipt, "corpus", "consultant_xml_count") != PIN_CONSULTANT_XML_COUNT:
        return False
    if _dig(receipt, "corpus", "garant_file_count") != PIN_GARANT_FILE_COUNT:
        return False
    if aggregate.get("files") != PIN_AGGREGATE_FILES:
        return False
    terminal = _dig(receipt, "terminal")
    if not isinstance(terminal, dict):
        return False
    return (
        terminal.get("outcome") == "complete"
        and terminal.get("exit_code") == 0
        and terminal.get("timeout") is False
        and terminal.get("signal") is None
    )


def predicate_timeout(receipt: Any) -> bool:
    terminal = _dig(receipt, "terminal")
    if not isinstance(terminal, dict):
        return False
    return (
        terminal.get("outcome") == "timeout"
        and terminal.get("exit_code") is None
        and terminal.get("signal") == "SIGTERM"
        and terminal.get("timeout") is True
    )


def _refuse(diagnostic: str, detail: str) -> None:
    raise GateError(diagnostic, detail)


# --------------------------------------------------------------------------- #
# The policy checks.  Each block is marked so the adversarial suite can remove it
# and prove the removal is detected.
# --------------------------------------------------------------------------- #


# --- pcheck:protocol-vocabulary ---
def _check_protocol_vocabulary(ctx: dict[str, Any]) -> None:
    """Bind this tool's vocabulary to the protocol's machine-readable diagnostic block."""
    root = ctx["root"]
    protocol_path = root / PROTOCOL_REL
    if not protocol_path.is_file():
        _refuse("MISSING_INPUT", f"S07 protocol missing at {PROTOCOL_REL}")
    declared = parse_protocol_diagnostics(_decode_text(protocol_path, "S07 protocol"))
    if declared != set(DIAGNOSTIC_CODES):
        missing = sorted(set(DIAGNOSTIC_CODES) - declared)
        extra = sorted(declared - set(DIAGNOSTIC_CODES))
        _refuse(
            "PROTOCOL_DIAGNOSTIC_DRIFT",
            f"{PROTOCOL_REL} differs from this tool's vocabulary "
            f"(missing={missing}, extra={extra})",
        )


# --- /pcheck:protocol-vocabulary ---


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


# --- pcheck:receipt-load ---
def _check_receipt_load(ctx: dict[str, Any]) -> None:
    """Read the receipt and its attempt stdout log; absence and malformed bytes are named."""
    receipt_path = ctx["receipt_path"]
    if not receipt_path.is_file():
        _refuse("MISSING_INPUT", f"no S07 successor receipt is published at {ctx['receipt_label']}")
    receipt = load_json(receipt_path, "S07 successor receipt")
    if not isinstance(receipt, dict):
        _refuse("SCHEMA_KEY_DRIFT", "the S07 successor receipt must be a JSON object")
    ctx["receipt"] = receipt
    stdout_rel = _dig(receipt, "logs", "stdout")
    if isinstance(stdout_rel, str) and stdout_rel:
        stdout_path = resolve_repo_path(ctx["root"], stdout_rel, "logs.stdout")
    else:
        stdout_path = ctx["attempt_dir"] / "stdout.log"
    ctx["stdout_path"] = stdout_path
    if stdout_path.is_file():
        ctx["rows"] = load_jsonl(stdout_path, "attempt stdout JSONL log")
    else:
        ctx["rows"] = []


# --- /pcheck:receipt-load ---


# --- pcheck:schema-document ---
def _check_schema_document(ctx: dict[str, Any]) -> None:
    """Bind the policy closure to the frozen schema document (one source of truth)."""
    schema_path = ctx["schema_path"]
    if not schema_path.is_file():
        _refuse("MISSING_ARTIFACT", f"S07 schema document missing at {ctx['schema_label']}")
    schema = load_json(schema_path, "S07 schema document")
    if not isinstance(schema, dict):
        _refuse("MISSING_INPUT", "the S07 schema document is not a JSON object")
    if schema.get("schema") != SCHEMAS_ID:
        _refuse(
            "SCHEMA_VERSION_DRIFT",
            f"$.schema is {schema.get('schema')!r}, expected {SCHEMAS_ID!r}",
        )
    if schema.get("sidecar_schema_id") != SIDECAR_SCHEMA_ID:
        _refuse(
            "SCHEMA_VERSION_DRIFT",
            f"$.sidecar_schema_id is {schema.get('sidecar_schema_id')!r}, expected "
            f"{SIDECAR_SCHEMA_ID!r}",
        )
    if schema.get("receipt_schema_id") != RECEIPT_SCHEMA_ID:
        _refuse(
            "SCHEMA_VERSION_DRIFT",
            f"$.receipt_schema_id is {schema.get('receipt_schema_id')!r}, expected "
            f"{RECEIPT_SCHEMA_ID!r}",
        )
    policy = schema.get("failure_policy")
    if not isinstance(policy, dict):
        _refuse("SCHEMA_KEY_DRIFT", "$.failure_policy must be a JSON object")
    if set(policy.get("sidecar_keys") or []) != set(SIDECAR_KEYS):
        _refuse(
            "SIDECAR_KEY_DRIFT",
            f"$.failure_policy.sidecar_keys is {policy.get('sidecar_keys')!r}, expected "
            f"{list(SIDECAR_KEYS)!r}",
        )
    if policy.get("record_kind_value") != RECORD_KIND_VALUE:
        _refuse(
            "SIDECAR_KEY_DRIFT",
            f"$.failure_policy.record_kind_value is {policy.get('record_kind_value')!r}, expected "
            f"{RECORD_KIND_VALUE!r}",
        )
    if policy.get("acceptance_effect") != ACCEPTANCE_EFFECT_NONE:
        _refuse(
            "PROMOTION_CLAIM",
            f"$.failure_policy.acceptance_effect is {policy.get('acceptance_effect')!r}, must be "
            f"{ACCEPTANCE_EFFECT_NONE!r}",
        )
    if set(policy.get("provider_allowlist") or []) != set(PROVIDER_VALUES):
        _refuse(
            "SIDECAR_PROVIDER_DRIFT",
            f"$.failure_policy.provider_allowlist is {policy.get('provider_allowlist')!r}, "
            f"expected {list(PROVIDER_VALUES)!r}",
        )
    if set(policy.get("class_allowlist") or []) != set(CLASS_VALUES):
        _refuse(
            "SIDECAR_CLASS_DRIFT",
            f"$.failure_policy.class_allowlist is {policy.get('class_allowlist')!r}, expected "
            f"{list(CLASS_VALUES)!r}",
        )
    if policy.get("provider_roots") != PROVIDER_ROOTS:
        _refuse(
            "SIDECAR_PATH_ESCAPE",
            f"$.failure_policy.provider_roots is {policy.get('provider_roots')!r}, expected "
            f"{PROVIDER_ROOTS!r}",
        )
    ctx["schema"] = schema


# --- /pcheck:schema-document ---


# --- pcheck:acceptance-keys ---
def _check_acceptance_keys(ctx: dict[str, Any]) -> None:
    """The receipt classifies; it never accepts, promotes or labels gold."""
    receipt = ctx["receipt"]
    claims = receipt.get("claims") if isinstance(receipt.get("claims"), dict) else {}
    for scope_label, scope in (("receipt", receipt), ("receipt.claims", claims)):
        for key in RECEIPT_FORBIDDEN_ACCEPTANCE_KEYS:
            if key in scope:
                _refuse(
                    "SCHEMA_KEY_DRIFT",
                    f"{scope_label}.{key} is present: the successor receipt carries no "
                    "operational acceptance key",
                )
        for key in RECEIPT_FORBIDDEN_PROMOTION_KEYS:
            if key in scope:
                _refuse(
                    "PROMOTION_CLAIM",
                    f"{scope_label}.{key} is present: promotion stays none and classification is "
                    "not this receipt's authority",
                )
        for key in RECEIPT_FORBIDDEN_GOLD_KEYS:
            if key in scope:
                _refuse(
                    "GOLD_CLAIM",
                    f"{scope_label}.{key} is present: no S07 artifact is gold, human-accepted or "
                    "thresholded",
                )
    for label, block in (("claims", claims), ("failure_policy", _dig(receipt, "failure_policy"))):
        if isinstance(block, dict) and "acceptance_effect" in block:
            if block["acceptance_effect"] != ACCEPTANCE_EFFECT_NONE:
                _refuse(
                    "PROMOTION_CLAIM",
                    f"receipt.{label}.acceptance_effect is {block['acceptance_effect']!r}, must be "
                    f"{ACCEPTANCE_EFFECT_NONE!r}",
                )
    marker = _acceptance_marker(receipt)
    if marker is not None:
        _refuse(
            "PROMOTION_CLAIM",
            f"the receipt carries the integrity marker {marker!r} as a value: a marker is a "
            "statement about the tool that printed it, never acceptance",
        )


# --- /pcheck:acceptance-keys ---


def _acceptance_marker(document: Any, *, skip_key: str | None = "non_claims") -> str | None:
    """Find an integrity marker used as a value anywhere outside the ``non_claims`` block."""
    if isinstance(document, dict):
        for key, value in document.items():
            if key == skip_key:
                continue
            found = _acceptance_marker(value, skip_key=skip_key)
            if found is not None:
                return found
        return None
    if isinstance(document, list):
        for item in document:
            found = _acceptance_marker(item, skip_key=skip_key)
            if found is not None:
                return found
        return None
    if isinstance(document, str):
        for marker in INTEGRITY_MARKERS:
            if marker in document:
                return marker
    return None


# --- pcheck:duration-floor ---
def _check_duration_floor(ctx: dict[str, Any]) -> None:
    """A duration floor inside the receipt is the frozen S04 rule imported as acceptance."""
    for key in _walk_keys(ctx["receipt"]):
        if key in DURATION_FLOOR_KEYS:
            _refuse(
                "DURATION_FLOOR_AS_ACCEPTANCE",
                f"the receipt carries {key!r}: duration_ms is recorded and never a predicate input",
            )


# --- /pcheck:duration-floor ---


# --- pcheck:s03-isolation ---
def _check_s03_isolation(ctx: dict[str, Any]) -> None:
    """No S03 aspect/stratum/rate key and no forced human pilot; the 180-fragment seed stays 180."""
    receipt = ctx["receipt"]
    for key, value in _walk_items(receipt):
        if key in S03_RATE_KEYS:
            if key == "human_pilot_performed" and not value:
                continue
            _refuse(
                "S03_RATE_IMPORT",
                f"the receipt carries {key!r}: no S03 aspect, stratum, rate or human-pilot flag is "
                "imported by the successor contract",
            )
        if key in SEED_KEYS and value != PIN_SEED_FRAGMENTS:
            _refuse(
                "SEED_ENLARGE",
                f"the receipt carries {key}={value!r}: the frozen seed stays "
                f"{PIN_SEED_FRAGMENTS} fragments",
            )


# --- /pcheck:s03-isolation ---


def _walk_keys(document: Any) -> list[str]:
    return [key for key, _ in _walk_items(document)]


def _walk_items(document: Any) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    stack: list[Any] = [document]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                found.append((key, value))
                stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)
    return found


# --- pcheck:schema-id ---
def _check_schema_id(ctx: dict[str, Any]) -> None:
    receipt = ctx["receipt"]
    if receipt.get("schema") != RECEIPT_SCHEMA_ID:
        _refuse(
            "SCHEMA_VERSION_DRIFT",
            f"receipt.schema is {receipt.get('schema')!r}, expected {RECEIPT_SCHEMA_ID!r}",
        )


# --- /pcheck:schema-id ---


# --- pcheck:closed-keys ---
def _check_closed_keys(ctx: dict[str, Any]) -> None:
    """The receipt closure is closed at the root, in every nested object and in the terminal."""
    receipt = ctx["receipt"]
    if set(receipt) != set(RECEIPT_KEYS):
        extra = sorted(set(receipt) - set(RECEIPT_KEYS))
        missing = sorted(set(RECEIPT_KEYS) - set(receipt))
        _refuse(
            "SCHEMA_KEY_DRIFT",
            f"receipt keys differ from the closed closure (extra={extra}, missing={missing})",
        )
    for name, expected in RECEIPT_NESTED_KEYS.items():
        block = receipt.get(name)
        if not isinstance(block, dict) or set(block) != set(expected):
            actual = sorted(block) if isinstance(block, dict) else block
            _refuse(
                "SCHEMA_KEY_DRIFT",
                f"receipt.{name} keys are {actual!r}, expected exactly {list(expected)!r}",
            )
    terminal = receipt["terminal"]
    allowed = set(RECEIPT_TERMINAL_KEYS) | set(RECEIPT_TERMINAL_OPTIONAL_KEYS)
    if not set(terminal) <= allowed:
        _refuse(
            "SCHEMA_KEY_DRIFT",
            f"receipt.terminal keys {sorted(terminal)!r} exceed {sorted(allowed)!r}",
        )
    if "error" in terminal and terminal.get("outcome") != "launch_error":
        _refuse(
            "SCHEMA_KEY_DRIFT",
            "receipt.terminal.error is lawful only when the outcome is launch_error",
        )


# --- /pcheck:closed-keys ---


# --- pcheck:argv-binding ---
def _check_argv_binding(ctx: dict[str, Any]) -> None:
    """A limited walk is not a full walk, and the sidecar flag carries the bound path."""
    receipt = ctx["receipt"]
    argv = receipt.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        _refuse("ARGV_PIN_DRIFT", "receipt.argv must be a list of strings")
    if "--limit" in argv:
        _refuse("ARGV_PIN_DRIFT", "receipt.argv carries --limit: a limited walk is not a full walk")
    if _dig(receipt, "binding", "limit") is not None:
        _refuse(
            "ARGV_PIN_DRIFT",
            f"receipt.binding.limit is {_dig(receipt, 'binding', 'limit')!r}, must be null",
        )
    if "--failures-out" not in argv:
        _refuse(
            "ARGV_PIN_DRIFT",
            "receipt.argv carries no --failures-out: the failure identity flag is part of the new "
            "attempt's identity",
        )
    values = [argv[index + 1] for index, item in enumerate(argv) if item == "--failures-out"]
    bound = _dig(receipt, "failure_policy", "failures_out_path")
    if not values:
        _refuse("ARGV_PIN_DRIFT", "--failures-out is present without a value")
    if values != [bound]:
        _refuse(
            "ARGV_PIN_DRIFT",
            f"--failures-out {values!r} is not bound to failure_policy.failures_out_path {bound!r}",
        )


# --- /pcheck:argv-binding ---


# --- pcheck:sidecar-binding ---
def _check_sidecar_binding(ctx: dict[str, Any]) -> None:
    """The sidecar under test is the one this attempt declared, not a foreign file."""
    bound = _dig(ctx["receipt"], "failure_policy", "failures_out_path")
    if not isinstance(bound, str) or not bound:
        _refuse("C4_RECEIPT_DRIFT", "failure_policy.failures_out_path must be a relative path")
    declared = resolve_repo_path(ctx["root"], bound, "failure_policy.failures_out_path")
    if declared != Path(os.path.abspath(ctx["sidecar_path"])):
        _refuse(
            "C4_RECEIPT_DRIFT",
            f"the receipt binds failure_policy.failures_out_path={bound!r} but the policy was "
            f"given {display_under(ctx['root'], ctx['sidecar_path'])}: the sidecar identity is "
            "not interchangeable",
        )


# --- /pcheck:sidecar-binding ---


def _check_sidecar_path(root: Path, raw: Any, provider: str) -> None:
    """A failing path is repository-relative, canonical inside the repo and under its provider."""
    if (
        not isinstance(raw, str)
        or not raw
        or "\x00" in raw
        or raw.startswith("/")
        or "\\" in raw
        or (len(raw) > 1 and raw[1] == ":")
    ):
        _refuse(
            "SIDECAR_PATH_ESCAPE",
            f"failure path {raw!r} must be a non-empty repository-relative POSIX path",
        )
    parts = PurePosixPath(raw).parts
    if ".." in parts:
        _refuse("SIDECAR_PATH_ESCAPE", f"failure path {raw!r} escapes its provider root")
    prefix = PROVIDER_ROOTS[provider]
    if not raw.startswith(prefix):
        _refuse(
            "SIDECAR_PATH_ESCAPE",
            f"failure path {raw!r} is not under the {provider!r} root {prefix!r}",
        )
    root_real = Path(os.path.realpath(root))
    candidate_real = Path(os.path.realpath(root / raw))
    if candidate_real != root_real and root_real not in candidate_real.parents:
        _refuse(
            "SIDECAR_PATH_ESCAPE",
            f"failure path {raw!r} canonicalises outside the repository root",
        )
    expected = root_real / prefix.rstrip("/")
    if expected != candidate_real and expected not in candidate_real.parents:
        _refuse(
            "SIDECAR_PATH_ESCAPE",
            f"failure path {raw!r} resolves outside the {provider!r} provider root",
        )


# --- pcheck:sidecar-rows ---
def _check_sidecar_rows(ctx: dict[str, Any]) -> None:
    """Every sidecar row carries exactly the closed key set and a lawful provider/path/class."""
    sidecar_path = ctx["sidecar_path"]
    if not sidecar_path.is_file():
        ctx["sidecar_present"] = False
        ctx["sidecar_rows"] = []
        return
    rows = load_jsonl(sidecar_path, "failure sidecar JSONL")
    for number, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != set(SIDECAR_KEYS):
            actual = sorted(row) if isinstance(row, dict) else type(row).__name__
            _refuse(
                "SIDECAR_KEY_DRIFT",
                f"sidecar row {number} carries keys {actual!r}, expected {list(SIDECAR_KEYS)!r}",
            )
        if row.get("record_kind") != RECORD_KIND_VALUE:
            _refuse(
                "SIDECAR_KEY_DRIFT",
                f"sidecar row {number} record_kind is {row.get('record_kind')!r}, expected "
                f"{RECORD_KIND_VALUE!r}",
            )
        if row.get("schema") != SIDECAR_SCHEMA_ID:
            _refuse(
                "SCHEMA_VERSION_DRIFT",
                f"sidecar row {number} schema is {row.get('schema')!r}, expected "
                f"{SIDECAR_SCHEMA_ID!r}",
            )
        provider = row.get("provider")
        if provider not in PROVIDER_VALUES:
            _refuse(
                "SIDECAR_PROVIDER_DRIFT",
                f"sidecar row {number} provider {provider!r} is outside {list(PROVIDER_VALUES)!r}",
            )
        if row.get("class") not in CLASS_VALUES:
            _refuse(
                "SIDECAR_CLASS_DRIFT",
                f"sidecar row {number} class {row.get('class')!r} is outside "
                f"{list(CLASS_VALUES)!r}",
            )
        _check_sidecar_path(ctx["root"], row.get("path"), provider)
    ctx["sidecar_present"] = True
    ctx["sidecar_rows"] = rows


# --- /pcheck:sidecar-rows ---


# --- pcheck:sidecar-count ---
def _check_sidecar_count(ctx: dict[str, Any]) -> None:
    """The sidecar and this attempt's own aggregate must agree, row for failure."""
    rows = ctx["rows"]
    aggregate = _row_for(rows, "aggregate")
    if aggregate is None:
        _refuse("MALFORMED_RECEIPT", "attempt JSONL carries no 'aggregate' row")
    failed = aggregate.get("failed")
    if isinstance(failed, bool) or not isinstance(failed, int):
        _refuse(
            "MALFORMED_RECEIPT",
            f"aggregate.failed is {failed!r}, must be an integer",
        )
    sidecar_rows = ctx["sidecar_rows"]
    count = len(sidecar_rows)
    recorded = _dig(ctx["receipt"], "failure_policy", "sidecar_rows")
    recorded_failed = _dig(ctx["receipt"], "failure_policy", "aggregate_failed")
    if recorded != count:
        _refuse(
            "SIDECAR_COUNT_MISMATCH",
            f"failure_policy.sidecar_rows is {recorded!r}, the sidecar carries {count} row(s)",
        )
    if recorded_failed != failed:
        _refuse(
            "SIDECAR_COUNT_MISMATCH",
            f"failure_policy.aggregate_failed is {recorded_failed!r}, this attempt's aggregate "
            f"failed={failed}",
        )
    exit_code = _dig(ctx["receipt"], "terminal", "exit_code")
    if failed == 0 and count > 0:
        _refuse(
            "SIDECAR_UNEXPECTED",
            f"the sidecar carries {count} row(s) although aggregate failed=0",
        )
    if failed > 0 and count == 0 and exit_code != EXIT_OUT_UNWRITABLE:
        _refuse(
            "MISSING_SIDECAR",
            f"aggregate failed={failed} but the attempt published no failure sidecar and exited "
            f"{exit_code!r}: only an exit-3 allowlist refusal is lawful without one",
        )
    if failed > 0 and count > 0 and count != failed:
        _refuse(
            "SIDECAR_COUNT_MISMATCH",
            f"the sidecar carries {count} row(s) but aggregate failed={failed}",
        )
    ctx["aggregate"] = {
        "files": aggregate.get("files"),
        "failed": failed,
        "sidecar_rows": count,
    }


# --- /pcheck:sidecar-count ---


# --- pcheck:predicates ---
def _check_predicates(ctx: dict[str, Any]) -> None:
    """Recompute both predicates from the receipt and the JSONL; duration is never an input."""
    receipt = ctx["receipt"]
    terminal = receipt.get("terminal")
    outcome = terminal.get("outcome") if isinstance(terminal, dict) else None
    if outcome not in TERMINAL_OUTCOME_VALUES:
        _refuse(
            "TERMINAL_OUTCOME_DRIFT",
            f"receipt.terminal.outcome is {outcome!r}, outside {list(TERMINAL_OUTCOME_VALUES)!r}",
        )
    if outcome == "complete" and not (
        terminal.get("exit_code") == 0
        and terminal.get("timeout") is False
        and terminal.get("signal") is None
    ):
        _refuse(
            "TERMINAL_OUTCOME_DRIFT",
            "a 'complete' terminal requires exit_code 0, timeout false and signal null",
        )
    if outcome == "timeout" and not (
        terminal.get("exit_code") is None
        and terminal.get("timeout") is True
        and terminal.get("signal") == "SIGTERM"
    ):
        _refuse(
            "TERMINAL_OUTCOME_DRIFT",
            "a 'timeout' terminal requires exit_code null, timeout true and signal SIGTERM",
        )
    full_walk = predicate_full_walk(receipt, ctx["rows"])
    timeout = predicate_timeout(receipt)
    if full_walk and timeout:
        _refuse("PREDICATE_CONTRADICTION", "full_walk and timeout are both true")
    if outcome == "complete" and terminal.get("exit_code") == 0 and not full_walk:
        _refuse(
            "PREDICATE_CONTRADICTION",
            "a complete walk with exit code 0 is not a full_walk, so the predicates are not "
            "independent of duration or a limit",
        )
    if timeout:
        classification = "timeout"
    elif full_walk:
        classification = "full_walk"
    elif outcome in ("nonzero", "launch_error"):
        classification = outcome
    else:
        classification = "nonzero"
    recorded = receipt.get("predicates") if isinstance(receipt.get("predicates"), dict) else {}
    if bool(recorded.get("full_walk")) != full_walk or bool(recorded.get("timeout")) != timeout:
        _refuse(
            "PREDICATE_CONTRADICTION",
            f"receipt.predicates records {recorded!r}, recomputed "
            f"full_walk={full_walk} timeout={timeout}",
        )
    if recorded.get("outcome") != classification:
        _refuse(
            "PREDICATE_CONTRADICTION",
            f"receipt.predicates.outcome is {recorded.get('outcome')!r}, recomputed "
            f"{classification!r}",
        )
    claims = receipt.get("claims") if isinstance(receipt.get("claims"), dict) else {}
    if claims.get("operational_classification") != classification:
        _refuse(
            "PREDICATE_CONTRADICTION",
            f"claims.operational_classification is "
            f"{claims.get('operational_classification')!r}, recomputed {classification!r}",
        )
    duration = receipt.get("duration_ms")
    budget = receipt.get("budget_seconds")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < BUDGET_SECONDS_MINIMUM:
        _refuse(
            "PREDICATE_CONTRADICTION",
            f"receipt.budget_seconds is {budget!r}, must be an integer >= {BUDGET_SECONDS_MINIMUM}",
        )
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
        _refuse("PREDICATE_CONTRADICTION", f"receipt.duration_ms is {duration!r}, must be >= 0")
    ctx["classification"] = classification
    ctx["predicates"] = {"full_walk": full_walk, "timeout": timeout, "outcome": classification}
    ctx["short_walk_is_not_timeout"] = bool(full_walk and duration < budget * 1000)


# --- /pcheck:predicates ---


# --- pcheck:exit-class ---
def _check_exit_class(ctx: dict[str, Any]) -> None:
    """An exit-3 allowlist refusal is a lawful nonzero with no sidecar, and nothing else."""
    terminal = ctx["receipt"].get("terminal")
    exit_code = terminal.get("exit_code") if isinstance(terminal, dict) else None
    outcome = terminal.get("outcome") if isinstance(terminal, dict) else None
    count = len(ctx["sidecar_rows"])
    if exit_code == EXIT_OUT_UNWRITABLE:
        if count > 0:
            _refuse(
                "ALLOWLIST_REFUSAL",
                f"an exit-3 allowlist refusal publishes no sidecar, but {count} row(s) exist",
            )
        if ctx["classification"] != "nonzero":
            _refuse(
                "ALLOWLIST_REFUSAL",
                f"an exit-3 allowlist refusal is a lawful nonzero, not {ctx['classification']!r}",
            )
        ctx["exit_class"] = ALLOWLIST_REFUSAL_CLASS
        return
    if outcome == "timeout":
        ctx["exit_class"] = "timeout"
    elif outcome == "launch_error":
        ctx["exit_class"] = "launch_error"
    elif exit_code == 0:
        ctx["exit_class"] = "zero"
    else:
        ctx["exit_class"] = "nonzero"


# --- /pcheck:exit-class ---


def validate_attempt(
    repo_root: Path | str,
    receipt_path: Path | str,
    sidecar_path: Path | str,
    *,
    schema_rel: str = SCHEMAS_REL,
) -> dict[str, Any]:
    """Apply the whole failure policy to one published attempt; raise a named diagnostic on drift."""
    root = Path(repo_root)
    receipt_path = Path(receipt_path)
    sidecar_path = Path(sidecar_path)
    ctx: dict[str, Any] = {
        "root": root,
        "receipt_path": receipt_path,
        "receipt_label": display_under(root, receipt_path),
        "sidecar_path": sidecar_path,
        "attempt_dir": sidecar_path.parent,
        "schema_path": root / schema_rel,
        "schema_label": schema_rel,
        "sidecar_present": False,
        "sidecar_rows": [],
        "rows": [],
        "predicates": {},
        "classification": None,
        "exit_class": None,
        "short_walk_is_not_timeout": False,
    }
    _check_protocol_vocabulary(ctx)
    _check_receipt_load(ctx)
    _check_schema_document(ctx)
    _check_acceptance_keys(ctx)
    _check_duration_floor(ctx)
    _check_s03_isolation(ctx)
    _check_schema_id(ctx)
    _check_closed_keys(ctx)
    _check_argv_binding(ctx)
    _check_sidecar_binding(ctx)
    _check_sidecar_rows(ctx)
    _check_sidecar_count(ctx)
    _check_predicates(ctx)
    _check_exit_class(ctx)
    receipt = ctx["receipt"]
    return {
        "schema": POLICY_REPORT_SCHEMA_ID,
        "receipt": display_under(root, receipt_path),
        "attempt_id": receipt.get("attempt_id"),
        "terminal": receipt.get("terminal"),
        "aggregate": ctx["aggregate"],
        "sidecar_present": ctx["sidecar_present"],
        "sidecar_rows": len(ctx["sidecar_rows"]),
        "exit_class": ctx["exit_class"],
        "classification": ctx["classification"],
        "predicates": ctx["predicates"],
        "duration_ms": receipt.get("duration_ms"),
        "budget_seconds": receipt.get("budget_seconds"),
        "short_walk_is_not_timeout": ctx["short_walk_is_not_timeout"],
        "acceptance_effect": ACCEPTANCE_EFFECT_NONE,
        "promotion": PROMOTION_NONE,
        "human_pilot_performed": HUMAN_PILOT_PERFORMED,
        "s03_rates_status": S03_RATES_STATUS,
        "seed_count": PIN_SEED_FRAGMENTS,
        "diagnostics": [],
    }


# --------------------------------------------------------------------------- #
# CLI plumbing
# --------------------------------------------------------------------------- #


def refusal_payload(diagnostic: str, detail: str) -> dict[str, Any]:
    return {
        "schema": POLICY_REPORT_SCHEMA_ID,
        "status": "refused",
        "diagnostic": diagnostic,
        "detail": detail,
        "acceptance_effect": ACCEPTANCE_EFFECT_NONE,
    }


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def report_failure(exc: GateError) -> int:
    emit(refusal_payload(exc.diagnostic, exc.detail))
    print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
    print(
        f"FAIL {GATE_NAME}: nothing was published; the failure policy is not satisfied",
        file=sys.stderr,
    )
    return 1


def cmd_check(args: argparse.Namespace, root: Path) -> int:
    """Read-only gate over one published attempt (``M207_S07_POLICY_OK``)."""
    if not root.is_dir():
        raise GateError("MISSING_ARTIFACT", f"repository root {root} is not a directory")
    receipt_path = resolve_repo_path(root, args.receipt or DEFAULT_RECEIPT_REL, "--receipt")
    if args.sidecar:
        sidecar_path = resolve_repo_path(root, args.sidecar, "--sidecar")
    else:
        sidecar_path = resolve_repo_path(
            root, f"{ATTEMPT_DIR_REL}/{DEFAULT_ATTEMPT_ID}/{SIDECAR_FILENAME}", "--sidecar"
        )
    summary = validate_attempt(root, receipt_path, sidecar_path, schema_rel=args.schemas)
    emit(summary)
    print(MARKER, file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Selftest: lawful controls and the hostile set, each with its own named code
# --------------------------------------------------------------------------- #


def _fixture_rows(
    *,
    failed: int = 1,
    files: int = PIN_AGGREGATE_FILES,
    limit: Any = None,
) -> list[dict[str, Any]]:
    return [
        {
            "record_kind": "header",
            "schema": "npa-contour-inventory/v1",
            "limit": limit,
            "argv": ["--root", "consru_export/consru_export/exports"],
        },
        {
            "record_kind": "aggregate",
            "files": files,
            "decoded": files - failed,
            "failed": failed,
        },
        {"record_kind": "inventory", "consultant_xml": PIN_CONSULTANT_XML_COUNT},
        {"record_kind": "canonical_payload", "limit": limit, "jobs": 0},
        {"record_kind": "operational_envelope", "run_status": "complete"},
    ]


def _fixture_receipt(
    *,
    root: Path,
    attempt_id: str = DEFAULT_ATTEMPT_ID,
    terminal: dict[str, Any] | None = None,
    duration_ms: int = 387174,
    budget_seconds: int = BUDGET_SECONDS_MINIMUM,
    failed: int = 1,
    sidecar_rows: int = 1,
    predicates: dict[str, Any] | None = None,
    classification: str = "full_walk",
) -> dict[str, Any]:
    if terminal is None:
        terminal = {"outcome": "complete", "exit_code": 0, "signal": None, "timeout": False}
    sidecar_rel = f"{ATTEMPT_DIR_REL}/{attempt_id}/{SIDECAR_FILENAME}"
    stdout_rel = f"{ATTEMPT_DIR_REL}/{attempt_id}/stdout.log"
    argv = [
        "--root",
        "consru_export/consru_export/exports",
        "--garant-root",
        "law-source/garant",
        "--profile",
        "contour",
        "--jobs",
        "0",
        "--acceptance-contract",
        "prd/architecture/npa-acceptance-contract.yaml",
        "--source-revision",
        "m207-s07-c4-caller-pin-2026-09-22",
        "--failures-out",
        sidecar_rel,
    ]
    if predicates is None:
        predicates = {
            "full_walk": classification == "full_walk",
            "timeout": classification == "timeout",
            "outcome": classification,
        }
    return {
        "schema": RECEIPT_SCHEMA_ID,
        "attempt_id": attempt_id,
        "immutable_attempt_identity": {"attempt_id": attempt_id, "argv_sha256": "0" * 64},
        "argv": argv,
        "binary": {"path": "target/release/npa-contour-diagnostics", "sha256": "1" * 64},
        "build_inputs": {
            "binary_sha256": "1" * 64,
            "parser_source_sha256": "2" * 64,
            "protocol_sha256": "3" * 64,
            "schemas_sha256": "4" * 64,
        },
        "toolchain": {"rustc": "rustc 1.0.0", "cargo": "cargo 1.0.0", "commands_exit_code": 0},
        "parser_revision": "PARSER_REVISION",
        "source_revision": "m207-s07-c4-caller-pin-2026-09-22",
        "contract": {
            "path": "prd/architecture/npa-acceptance-contract.yaml",
            "sha256": "5" * 64,
            "version": "npa-acceptance-contract/v1",
        },
        "corpus": {
            "consultant_xml_count": PIN_CONSULTANT_XML_COUNT,
            "consultant_root": "consru_export/consru_export/exports",
            "garant_file_count": PIN_GARANT_FILE_COUNT,
            "garant_root": "law-source/garant",
        },
        "observed_output": {"stdout_sha256": "6" * 64, "inventory_digest": "7" * 64},
        "binding": {
            "profile": "contour",
            "limit": None,
            "jobs": 0,
            "inventory_scope": "consultant XML plus separate Garant files",
        },
        "started_at": "2026-09-22T00:00:00Z",
        "finished_at": "2026-09-22T00:06:27Z",
        "duration_ms": duration_ms,
        "budget_seconds": budget_seconds,
        "terminal": terminal,
        "logs": {
            "stdout": stdout_rel,
            "stderr": f"{ATTEMPT_DIR_REL}/{attempt_id}/stderr.log",
            "stdout_sha256": "6" * 64,
            "stderr_sha256": "8" * 64,
            "inventory_digest": "7" * 64,
        },
        "failure_policy": {
            "failures_out_path": sidecar_rel,
            "failures_sha256": "9" * 64 if sidecar_rows else None,
            "sidecar_rows": sidecar_rows,
            "aggregate_failed": failed,
            "acceptance_effect": ACCEPTANCE_EFFECT_NONE,
        },
        "predicates": predicates,
        "claims": {
            "operational_classification": classification,
            "acceptance_effect": ACCEPTANCE_EFFECT_NONE,
            "receipt_is_runtime_attempt": True,
        },
        "non_claims": list(SUCCESSOR_NON_CLAIMS),
    }


def _fixture_sidecar(provider: str = "consultant", klass: str = "decode") -> list[dict[str, Any]]:
    return [
        {
            "record_kind": RECORD_KIND_VALUE,
            "schema": SIDECAR_SCHEMA_ID,
            "provider": provider,
            "path": f"{PROVIDER_ROOTS[provider]}2026/file.xml",
            "class": klass,
        }
    ]


def _plant_attempt(
    root: Path,
    *,
    receipt: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    sidecar: list[dict[str, Any]] | None = None,
    attempt_id: str = DEFAULT_ATTEMPT_ID,
) -> Path:
    """Plant one lawful attempt fixture under a temp root; returns the receipt path."""
    attempt_dir = root / ATTEMPT_DIR_REL / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = attempt_dir / "stdout.log"
    if rows is None:
        rows = _fixture_rows()
    stdout_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    (attempt_dir / "stderr.log").write_text("", encoding="utf-8")
    sidecar_path = attempt_dir / SIDECAR_FILENAME
    if sidecar is not None:
        sidecar_path.write_text(
            "".join(json.dumps(row) + "\n" for row in sidecar), encoding="utf-8"
        )
    if receipt is None:
        receipt = _fixture_receipt(root=root, attempt_id=attempt_id)
    receipt_path = root / DEFAULT_RECEIPT_REL
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt_path


def _plant_frozen_docs(root: Path, source_root: Path) -> None:
    """Plant the frozen protocol and schema documents the policy binds itself to."""
    (root / "prd" / "annotation").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_root / PROTOCOL_REL, root / PROTOCOL_REL)
    shutil.copyfile(source_root / SCHEMAS_REL, root / SCHEMAS_REL)


def _default_sidecar(root: Path, attempt_id: str = DEFAULT_ATTEMPT_ID) -> Path:
    return root / ATTEMPT_DIR_REL / attempt_id / SIDECAR_FILENAME


def _expect_code(problems: list[str], name: str, expected: str, thunk: Callable[[], Any]) -> None:
    try:
        thunk()
    except GateError as exc:
        if exc.diagnostic != expected:
            problems.append(f"{name}: expected {expected}, got {exc.diagnostic} ({exc.detail})")
        return
    problems.append(f"{name}: no refusal, expected {expected}")


def _expect_ok(problems: list[str], name: str, thunk: Callable[[], Any]) -> dict[str, Any]:
    try:
        report = thunk()
    except GateError as exc:
        problems.append(f"{name}: expected a lawful attempt, got {exc.diagnostic}: {exc.detail}")
        return {}
    if not isinstance(report, dict):
        problems.append(f"{name}: expected a report object")
        return {}
    return report


def _expect_true(problems: list[str], name: str, detail: str, condition: bool) -> None:
    if not condition:
        problems.append(f"{name}: {detail}")


def run_selftest(source_root: Path) -> int:
    """Prove the lawful controls and the hostile set in throw-away temp roots."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="m207-s07-policy-selftest-") as holder:
        base = Path(holder)
        base.mkdir(parents=True, exist_ok=True)

        # --- lawful controls -------------------------------------------------
        root = base / "lawful"
        root.mkdir()
        _plant_frozen_docs(root, source_root)
        _plant_attempt(root, sidecar=_fixture_sidecar())
        report = _expect_ok(
            problems,
            "lawful_short_full_walk",
            lambda: validate_attempt(root, root / DEFAULT_RECEIPT_REL, _default_sidecar(root)),
        )
        _expect_true(
            problems,
            "lawful_short_full_walk",
            f"classification is {report.get('classification')!r}",
            report.get("classification") == "full_walk",
        )
        _expect_true(
            problems,
            "lawful_short_full_walk",
            "short_walk_is_not_timeout must be true for 387174 ms under a 3600 s ceiling",
            report.get("short_walk_is_not_timeout") is True,
        )
        _expect_true(
            problems,
            "lawful_short_full_walk",
            f"sidecar_rows is {report.get('sidecar_rows')!r}",
            report.get("sidecar_rows") == 1,
        )
        _expect_true(
            problems,
            "lawful_short_full_walk",
            "promotion/acceptance_effect must stay none",
            report.get("promotion") == "none"
            and report.get("acceptance_effect") == "none"
            and report.get("human_pilot_performed") is False,
        )
        _expect_true(
            problems,
            "lawful_short_full_walk",
            "the report closure must be exactly the declared key set",
            set(report) == set(REPORT_KEYS),
        )

        timeout_root = base / "timeout"
        _plant_frozen_docs(timeout_root, source_root)
        timeout_receipt = _fixture_receipt(
            root=timeout_root,
            terminal={
                "outcome": "timeout",
                "exit_code": None,
                "signal": "SIGTERM",
                "timeout": True,
            },
            duration_ms=3600000,
            failed=0,
            sidecar_rows=0,
            classification="timeout",
        )
        _plant_attempt(
            timeout_root, receipt=timeout_receipt, rows=_fixture_rows(failed=0), sidecar=None
        )
        report = _expect_ok(
            problems,
            "lawful_timeout",
            lambda: validate_attempt(
                timeout_root, timeout_root / DEFAULT_RECEIPT_REL, _default_sidecar(timeout_root)
            ),
        )
        _expect_true(
            problems,
            "lawful_timeout",
            f"classification is {report.get('classification')!r}",
            report.get("classification") == "timeout",
        )
        _expect_true(
            problems,
            "lawful_timeout",
            f"exit_class is {report.get('exit_class')!r}",
            report.get("exit_class") == "timeout",
        )

        refusal_root = base / "allowlist-refusal"
        _plant_frozen_docs(refusal_root, source_root)
        refusal_receipt = _fixture_receipt(
            root=refusal_root,
            terminal={
                "outcome": "nonzero",
                "exit_code": EXIT_OUT_UNWRITABLE,
                "signal": None,
                "timeout": False,
            },
            failed=1,
            sidecar_rows=0,
            classification="nonzero",
        )
        _plant_attempt(
            refusal_root, receipt=refusal_receipt, rows=_fixture_rows(failed=1), sidecar=None
        )
        report = _expect_ok(
            problems,
            "lawful_allowlist_refusal",
            lambda: validate_attempt(
                refusal_root, refusal_root / DEFAULT_RECEIPT_REL, _default_sidecar(refusal_root)
            ),
        )
        _expect_true(
            problems,
            "lawful_allowlist_refusal",
            f"classification is {report.get('classification')!r}",
            report.get("classification") == "nonzero",
        )
        _expect_true(
            problems,
            "lawful_allowlist_refusal",
            f"exit_class is {report.get('exit_class')!r}",
            report.get("exit_class") == ALLOWLIST_REFUSAL_CLASS,
        )

        empty_sidecar_root = base / "empty-sidecar"
        _plant_frozen_docs(empty_sidecar_root, source_root)
        empty_receipt = _fixture_receipt(
            root=empty_sidecar_root, failed=0, sidecar_rows=0, classification="full_walk"
        )
        _plant_attempt(
            empty_sidecar_root,
            receipt=empty_receipt,
            rows=_fixture_rows(failed=0),
            sidecar=[],
        )
        _expect_ok(
            problems,
            "lawful_empty_sidecar_with_failed_zero",
            lambda: validate_attempt(
                empty_sidecar_root,
                empty_sidecar_root / DEFAULT_RECEIPT_REL,
                _default_sidecar(empty_sidecar_root),
            ),
        )

        # --- the hostile set: one mutation, one named code -------------------
        def hostile(
            name: str,
            expected: str,
            mutate: Callable[[Path], None],
            *,
            source_root_override: Path | None = None,
        ) -> None:
            hroot = base / name
            _plant_frozen_docs(hroot, source_root_override or source_root)
            _plant_attempt(hroot, sidecar=_fixture_sidecar())
            mutate(hroot)
            _expect_code(
                problems,
                name,
                expected,
                lambda: validate_attempt(
                    hroot, hroot / DEFAULT_RECEIPT_REL, _default_sidecar(hroot)
                ),
            )

        def edit_receipt(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
            path = root / DEFAULT_RECEIPT_REL
            document = json.loads(path.read_text(encoding="utf-8"))
            mutate(document)
            path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

        hostile(
            "timeout_as_full_walk",
            "PREDICATE_CONTRADICTION",
            lambda root: edit_receipt(
                root,
                lambda document: document.update(
                    {
                        "terminal": {
                            "outcome": "timeout",
                            "exit_code": None,
                            "signal": "SIGTERM",
                            "timeout": True,
                        }
                    }
                ),
            ),
        )
        hostile(
            "duration_floor_as_timeout",
            "PREDICATE_CONTRADICTION",
            lambda root: edit_receipt(
                root,
                lambda document: document["predicates"].update(
                    {"full_walk": False, "timeout": True, "outcome": "timeout"}
                ),
            ),
        )
        hostile(
            "missing_sidecar",
            "MISSING_SIDECAR",
            lambda root: (
                (_default_sidecar(root)).unlink(),
                edit_receipt(
                    root,
                    lambda document: document["failure_policy"].update(
                        {"sidecar_rows": 0, "failures_sha256": None}
                    ),
                ),
            ),
        )
        hostile(
            "sidecar_count_mismatch",
            "SIDECAR_COUNT_MISMATCH",
            lambda root: edit_receipt(
                root,
                lambda document: document["failure_policy"].update(
                    {"sidecar_rows": 1, "aggregate_failed": 2}
                ),
            ),
        )

        def zero_failed_but_keep_the_sidecar(root: Path) -> None:
            stdout_path = root / ATTEMPT_DIR_REL / DEFAULT_ATTEMPT_ID / "stdout.log"
            rows = [
                json.loads(line) for line in stdout_path.read_text(encoding="utf-8").splitlines()
            ]
            for row in rows:
                if row.get("record_kind") == "aggregate":
                    row["failed"] = 0
            stdout_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            edit_receipt(
                root,
                lambda document: document["failure_policy"].update(
                    {"aggregate_failed": 0, "sidecar_rows": 1}
                ),
            )

        hostile(
            "sidecar_unexpected",
            "SIDECAR_UNEXPECTED",
            zero_failed_but_keep_the_sidecar,
        )
        hostile(
            "extra_sidecar_key",
            "SIDECAR_KEY_DRIFT",
            lambda root: _default_sidecar(root).write_text(
                json.dumps({**_fixture_sidecar()[0], "payload": "boom"}) + "\n", encoding="utf-8"
            ),
        )
        hostile(
            "sidecar_schema_field_drift",
            "SCHEMA_VERSION_DRIFT",
            lambda root: _default_sidecar(root).write_text(
                json.dumps({**_fixture_sidecar()[0], "schema": "npa-contour-failure-trace/v2"})
                + "\n",
                encoding="utf-8",
            ),
        )
        hostile(
            "sidecar_provider_drift",
            "SIDECAR_PROVIDER_DRIFT",
            lambda root: _default_sidecar(root).write_text(
                json.dumps({**_fixture_sidecar()[0], "provider": "falkor"}) + "\n",
                encoding="utf-8",
            ),
        )
        hostile(
            "sidecar_class_drift",
            "SIDECAR_CLASS_DRIFT",
            lambda root: _default_sidecar(root).write_text(
                json.dumps({**_fixture_sidecar()[0], "class": "retry"}) + "\n", encoding="utf-8"
            ),
        )
        hostile(
            "sidecar_path_escape",
            "SIDECAR_PATH_ESCAPE",
            lambda root: _default_sidecar(root).write_text(
                json.dumps({**_fixture_sidecar()[0], "path": "../outside/secret.xml"}) + "\n",
                encoding="utf-8",
            ),
        )
        hostile(
            "sidecar_provider_path_mismatch",
            "SIDECAR_PATH_ESCAPE",
            lambda root: _default_sidecar(root).write_text(
                json.dumps(
                    {
                        **_fixture_sidecar()[0],
                        "provider": "garant",
                        "path": "consru_export/consru_export/exports/2026/file.xml",
                    }
                )
                + "\n",
                encoding="utf-8",
            ),
        )
        hostile(
            "receipt_operational_acceptance",
            "SCHEMA_KEY_DRIFT",
            lambda root: edit_receipt(
                root, lambda document: document.update({"operational_acceptance": "pass"})
            ),
        )
        hostile(
            "receipt_promotion_claim",
            "PROMOTION_CLAIM",
            lambda root: edit_receipt(
                root, lambda document: document.update({"promotion": "pass"})
            ),
        )
        hostile(
            "receipt_gold_claim",
            "GOLD_CLAIM",
            lambda root: edit_receipt(root, lambda document: document.update({"is_gold": True})),
        )
        hostile(
            "receipt_marker_as_acceptance",
            "PROMOTION_CLAIM",
            lambda root: edit_receipt(
                root, lambda document: document.update({"acceptance_marker": "M207_S07_VERIFY_OK"})
            ),
        )
        hostile(
            "receipt_s03_rate_import",
            "S03_RATE_IMPORT",
            lambda root: edit_receipt(root, lambda document: document.update({"aspect_rate": 0.5})),
        )
        hostile(
            "receipt_seed_enlarge",
            "SEED_ENLARGE",
            lambda root: edit_receipt(
                root, lambda document: document.update({"seed_fragments": 181})
            ),
        )
        hostile(
            "receipt_duration_floor",
            "DURATION_FLOOR_AS_ACCEPTANCE",
            lambda root: edit_receipt(
                root, lambda document: document.update({"duration_ms_minimum": 3600000})
            ),
        )
        hostile(
            "receipt_schema_drift",
            "SCHEMA_VERSION_DRIFT",
            lambda root: edit_receipt(
                root, lambda document: document.update({"schema": "m207-s07-c4-successor/v2"})
            ),
        )
        hostile(
            "receipt_key_drift",
            "SCHEMA_KEY_DRIFT",
            lambda root: edit_receipt(root, lambda document: document.pop("non_claims", None)),
        )
        hostile(
            "limit_in_argv",
            "ARGV_PIN_DRIFT",
            lambda root: edit_receipt(
                root, lambda document: document["argv"].extend(["--limit", "5"])
            ),
        )

        def rebind_the_sidecar(root: Path) -> None:
            other = f"{ATTEMPT_DIR_REL}/m207-s07-other-002/{SIDECAR_FILENAME}"

            def mutate(document: dict[str, Any]) -> None:
                document["failure_policy"]["failures_out_path"] = other
                document["argv"] = [
                    other if item.endswith(SIDECAR_FILENAME) else item for item in document["argv"]
                ]

            edit_receipt(root, mutate)

        hostile("sidecar_binding_drift", "C4_RECEIPT_DRIFT", rebind_the_sidecar)
        # exit 3 with a published sidecar is not a lawful allowlist refusal
        refusal_sidecar_root = base / "allowlist_refusal_with_sidecar"
        _plant_frozen_docs(refusal_sidecar_root, source_root)
        refusal_sidecar_receipt = _fixture_receipt(
            root=refusal_sidecar_root,
            terminal={
                "outcome": "nonzero",
                "exit_code": EXIT_OUT_UNWRITABLE,
                "signal": None,
                "timeout": False,
            },
            failed=1,
            sidecar_rows=1,
            classification="nonzero",
        )
        _plant_attempt(
            refusal_sidecar_root,
            receipt=refusal_sidecar_receipt,
            rows=_fixture_rows(failed=1),
            sidecar=_fixture_sidecar(),
        )
        _expect_code(
            problems,
            "allowlist_refusal_with_sidecar",
            "ALLOWLIST_REFUSAL",
            lambda: validate_attempt(
                refusal_sidecar_root,
                refusal_sidecar_root / DEFAULT_RECEIPT_REL,
                _default_sidecar(refusal_sidecar_root),
            ),
        )
        hostile(
            "aggregate_missing",
            "MALFORMED_RECEIPT",
            lambda root: (root / ATTEMPT_DIR_REL / DEFAULT_ATTEMPT_ID / "stdout.log").write_text(
                json.dumps({"record_kind": "header", "limit": None}) + "\n", encoding="utf-8"
            ),
        )
        hostile(
            "missing_receipt",
            "MISSING_INPUT",
            lambda root: (root / DEFAULT_RECEIPT_REL).unlink(),
        )
        hostile(
            "malformed_receipt",
            "MALFORMED_RECEIPT",
            lambda root: (root / DEFAULT_RECEIPT_REL).write_text("{not json", encoding="utf-8"),
        )

        # protocol↔code drift: a protocol block missing one code
        drift_root = base / "protocol_diagnostic_drift"
        _plant_frozen_docs(drift_root, source_root)
        protocol_text = (source_root / PROTOCOL_REL).read_text(encoding="utf-8")
        (drift_root / PROTOCOL_REL).write_text(
            protocol_text.replace("SEED_ENLARGE\n", "", 1), encoding="utf-8"
        )
        shutil.copyfile(source_root / SCHEMAS_REL, drift_root / SCHEMAS_REL)
        _plant_attempt(drift_root, sidecar=_fixture_sidecar())
        _expect_code(
            problems,
            "protocol_diagnostic_drift",
            "PROTOCOL_DIAGNOSTIC_DRIFT",
            lambda: validate_attempt(
                drift_root, drift_root / DEFAULT_RECEIPT_REL, _default_sidecar(drift_root)
            ),
        )

        # schema closure drift: the schema's sidecar key set was opened
        schema_root = base / "schema_sidecar_key_drift"
        _plant_frozen_docs(schema_root, source_root)
        document = json.loads((source_root / SCHEMAS_REL).read_text(encoding="utf-8"))
        document["failure_policy"]["sidecar_keys"] = [*SIDECAR_KEYS, "payload"]
        (schema_root / SCHEMAS_REL).write_text(json.dumps(document, indent=2) + "\n", "utf-8")
        _plant_attempt(schema_root, sidecar=_fixture_sidecar())
        _expect_code(
            problems,
            "schema_sidecar_key_drift",
            "SIDECAR_KEY_DRIFT",
            lambda: validate_attempt(
                schema_root, schema_root / DEFAULT_RECEIPT_REL, _default_sidecar(schema_root)
            ),
        )

    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        print(f"FAIL {GATE_NAME}: {len(problems)} selftest failure(s)", file=sys.stderr)
        return 1
    print(SELFTEST_MARKER)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m207_s07_policy.py", description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser(
        "check", help="read-only failure-policy gate over the published successor attempt"
    )
    check_parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="repository root the pinned paths are resolved against (default: the cwd)",
    )
    check_parser.add_argument("--schemas", default=SCHEMAS_REL, help="schema path under the root")
    check_parser.add_argument(
        "--receipt", default=None, help="receipt path override (default: the pinned path)"
    )
    check_parser.add_argument(
        "--sidecar", default=None, help="sidecar path override (default: the pinned attempt path)"
    )

    selftest_parser = subparsers.add_parser(
        "selftest", help="prove the lawful controls and the hostile set of the failure policy"
    )
    selftest_parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="root the fixture material is copied from (default: this checkout)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        if args.command == "check":
            return cmd_check(args, root)
        return run_selftest(root)
    except GateError as exc:
        return report_failure(exc)
    except Exception as exc:  # noqa: BLE001 - fail-closed: never a bare traceback
        emit(refusal_payload("GATE_INTERNAL_ERROR", f"{type(exc).__name__}: {exc}"))
        print(f"FAIL GATE_INTERNAL_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
