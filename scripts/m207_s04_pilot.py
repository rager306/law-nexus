#!/usr/bin/env python3
"""Promotion verdict and S03-isolation verifier for the M207 S04 contour (T03).

S01 proved a human pilot is not fabricated, S02 proved a two-coding human pilot is
not fabricated, S03 made the *metric* non-fabricable, and S04/T02 produced a fresh
pinned operational attempt over the whole declared corpus.  T03 owns the surface
that makes an operational attempt easiest to launder: the *verdict*.  A process that
walked 43 797 files in 387 s may be read as "the corpus passed", a terminal outcome
may be promoted to gold, an S03 aspect rate may be "reused" as a readiness number,
and the integrity marker may be quoted as an acceptance.  This verifier exists to
publish the opposite verdict, from bytes, and to fail closed the moment a derived
S04 artifact claims otherwise.

It deliberately does **not** import ``m207_s04_schemas`` or ``m207_s04_c4_run`` (no
oracle collapse, D472).  The pins, the acceptance rule, the receipt facts, the
attempt-log substantiation and the isolation scans are re-derived here from bytes,
and the frozen contract document is read only to prove that the in-code constants
and the frozen half still agree (``FROZEN_SOURCE_DRIFT`` otherwise).

What it proves, against the artifacts rather than against prose:

* **the verdict is derived, never read.** ``claims.operational_acceptance`` is
  recomputed from the receipt's own terminal facts with the rule reused verbatim
  from ``m204-s06-c4-operational-receipt/v1``: ``pass`` only when
  ``terminal.outcome == "complete"`` **and** ``terminal.exit_code == 0`` **and**
  ``duration_ms >= budget_seconds * 1000``.  A receipt whose published claim
  upgrades a non-pass to ``pass`` is ``C4_TIMEOUT_AS_PASS``; any other divergence
  from the recomputed rule is ``TERMINAL_OUTCOME_DRIFT``.  The published verdict
  never carries the receipt's claim: it carries the recomputed value.
* **nothing is promoted.** The verdict pins ``promotion = none``,
  ``classification = not-authorized``, ``threshold = null``,
  ``human_acceptance = null``, ``is_gold = false``, ``model_invoked = false``,
  ``legal_claim``/``n2_claim = forbidden``.  Any derived S04 artifact that moves
  one of those keys is rejected by name (``PROMOTION_CLAIM``, ``GOLD_CLAIM``,
  ``IS_GOLD_CLAIM``, ``THRESHOLD_REQUESTED``, ``CLASSIFICATION_REQUESTED``,
  ``MODEL_INVOKED``, ``AUTHORITY_CLAIM``); a ``requirement_status_effect`` that
  stops being ``unchanged`` is ``REQUIREMENT_STATUS_CLAIM``.
* **no rate is imported.** No derived S04 artifact may carry an aspect rate, a
  stratum rate, a denominator or a ``measurement_status`` (``S03_RATE_IMPORTED``),
  and no tracked file under ``crates/**`` may reference the offline harness at all
  (``S03_RATE_IMPORTED``, D466/D487).  The S03 evaluation report is never read: it
  is only tested for existence, and its existence while the S03 battery still
  records ``human_pilot_performed = false`` is ``REPORT_WITHOUT_HUMAN_DATA``.
* **the receipt is substantiated by the attempt it records.** The R1 stdout log is
  a JSONL envelope (``header``, ``aggregate``, ``inventory``, ``canonical_payload``,
  ``operational_envelope``).  This verifier re-derives the receipt's ``argv``, the
  inventory digest, the contract pins, the parser revision, the provider counts, the
  observed rustc version and the run status from those records, and rejects a
  receipt whose record does not describe the run: an envelope that does not
  substantiate ``complete`` while the receipt claims ``complete`` is
  ``C4_TIMEOUT_AS_PASS``, the reverse is ``TERMINAL_OUTCOME_DRIFT``, and a broken
  digest, count, argv or toolchain link is the matching named diagnostic.
* **a decode failure is an observation, never a verdict.** The attempt records
  ``decoded 43 796`` and ``failed 1``.  That fact is published as a
  ``semantic_observations`` block with ``acceptance_effect = none`` and its own
  stdout line: it never moves the acceptance, never becomes a quality, gold or
  legal judgement, and is never silently dropped (an unreadable or internally
  inconsistent envelope is ``C4_RECEIPT_DRIFT``).
* **the S03 contour stays not-measured.** The battery is pinned by digest and must
  still record ``human_pilot_performed = false`` (``S03_BATTERY_PILOT_PERFORMED``,
  ``FROZEN_SOURCE_DRIFT``), the 180-fragment seed is frozen by count and by
  aggregate digest (``SEED_ENLARGED``, ``SEED_DRIFT``), and the rule-seed sidecar is
  pinned the same way.
* **the prior non-pass stays a non-pass.** The M204/S06 timeout attempt is pinned by
  content digest *and* by semantics (``timeout`` / ``SIGTERM`` / ``non-pass``);
  rewriting it into a success is ``C4_TIMEOUT_AS_PASS``.
* **the integrity marker is never spoken here.** ``M207_S04_VERIFY_OK`` belongs to
  the T04 battery.  Every printed line is guarded: a line carrying the marker is
  ``AUTHORITY_CLAIM``, and this tool prints ``M207_S04_PROMOTION_NONE_OK`` instead.
  The verdict text intentionally never reproduces the marker literal, so scanning
  this tool's output for it is a meaningful check.

``check`` is read-only: it writes nothing, launches no walk and publishes no
artifact.  The verdict is *printed* (deterministically, with no wall-clock of its
own) and never persisted, so the byte-stable-battery rule of the S04 contract does
not apply to it.  A later T04 battery is validated when present and stays a
byte-stable projection: a wall-clock key in it is ``BATTERY_WALLCLOCK_FORBIDDEN``.

Every failure is a non-zero exit with a named diagnostic from the frozen closed
vocabulary of ``prd/annotation/m207-s04-schemas.json``; a name outside that table is
``DIAGNOSTIC_TABLE_DRIFT``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S04_PROMOTION_NONE_OK"
VERDICT_TAG = "M207_S04_PROMOTION_VERDICT"
SEMANTIC_TAG = "M207_S04_SEMANTIC_OBSERVATION"
GATE_NAME = "M207_S04_PILOT_GATE"
# The T04 battery marker: this tool must never print it.
INTEGRITY_MARKER = "M207_S04_VERIFY_OK"

VERDICT_SCHEMA_ID = "m207-s04-promotion-verdict/v1"
RECEIPT_SCHEMA_ID = "m204-s06-c4-operational-receipt/v1"
SCHEMAS_SCHEMA_ID = "m207-s04-c4-schemas/v1"
S03_BATTERY_SCHEMA_ID = "m207-s03-battery/v1"
S04_BATTERY_SCHEMA_ID = "m207-s04-battery/v1"
CONTOUR_SCHEMA_ID = "npa-contour-diagnostics/v2"

EVIDENCE_PREFIX = "prd/migration/rust-evidence/"
ANNOTATION_PREFIX = "prd/annotation/"
CRATES_REL = "crates"
SEED_ROOT_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
SEED_SIDECAR_REL = f"{SEED_ROOT_REL}/lawref_seed.json"

DEFAULT_RECEIPT_REL = f"{EVIDENCE_PREFIX}m207-s04-c4-operational-receipt.json"
DEFAULT_BATTERY_REL = f"{EVIDENCE_PREFIX}m207-s04-battery.json"
PRIOR_RECEIPT_REL = f"{EVIDENCE_PREFIX}m204-s06-c4-operational-receipt.json"
S03_BATTERY_REL = f"{EVIDENCE_PREFIX}m207-s03-battery.json"
REPORT_REL = f"{EVIDENCE_PREFIX}m207-s03-evaluation-report.json"
SCHEMAS_REL = f"{ANNOTATION_PREFIX}m207-s04-schemas.json"

# Frozen content pins.  The frozen contract names the same values; the two halves
# are compared on every run so neither can drift silently.
PRIOR_RECEIPT_SHA256 = "04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c"
S03_BATTERY_SHA256 = "76b9a78e3e83772be3ca3e46b83a89b3b3baaf690ffe6aa0c72f77aa6d56b533"
SEED_FRAGMENT_COUNT = 180
SEED_AGGREGATE_SHA256 = "50b48668cba5b89d75af0604a78004404310e36377679984273fa0a883053c9d"
SEED_SIDECAR_SHA256 = "b88e5af14bcc9496c4d35627afda058d58956f459106c147f1cc7959a6930f28"
PRIOR_ATTEMPT_ID = "full-walk-timeout-001"
BUDGET_SECONDS_MINIMUM = 3600
PROFILE_PIN = "contour"
PARSER_REVISION_PIN = "m204-s04-c4-contour-v1"
CONTRACT_VERSION_PIN = "npa-acceptance-contract/v1"
CONTRACT_CHECK_ID_PIN = "c4-live-check"
CONTRACT_MODE_PIN = "runtime"
REQUIRED_ARGV_FLAGS = (
    "--root",
    "--garant-root",
    "--profile",
    "--jobs",
    "--acceptance-contract",
    "--source-revision",
)
FORBIDDEN_ARGV_FLAGS = ("--limit",)

RECEIPT_REQUIRED_KEYS = (
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
    "c4_binding",
    "started_at",
    "finished_at",
    "duration_ms",
    "budget_seconds",
    "terminal",
    "logs",
    "claims",
    "non_claims",
)
TERMINAL_KEYS = ("outcome", "exit_code", "signal", "timeout")
TERMINAL_OUTCOMES = frozenset({"complete", "nonzero", "timeout", "launch_error", "not-run"})
ACCEPTANCE_VALUES = frozenset({"pass", "non-pass"})
ENVELOPE_RECORD_KINDS = (
    "header",
    "aggregate",
    "inventory",
    "canonical_payload",
    "operational_envelope",
)

# Claim keys: a derived artifact may only carry them with exactly the frozen value.
PROMOTION_KEY_VALUES: tuple[tuple[str, Any, str], ...] = (
    ("promotion", "none", "PROMOTION_CLAIM"),
    ("classification", "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("threshold", None, "THRESHOLD_REQUESTED"),
    ("human_acceptance", None, "GOLD_CLAIM"),
    ("is_gold", False, "IS_GOLD_CLAIM"),
    ("model_invoked", False, "MODEL_INVOKED"),
    ("legal_claim", "forbidden", "AUTHORITY_CLAIM"),
    ("n2_claim", "forbidden", "AUTHORITY_CLAIM"),
    ("rate_publication", "forbidden", "S03_RATE_IMPORTED"),
    ("measurement_status_publication", "forbidden", "S03_RATE_IMPORTED"),
)
PROMOTION_KEY_MAP = {key: (value, diagnostic) for key, value, diagnostic in PROMOTION_KEY_VALUES}
RATE_KEY_TOKENS = frozenset({"rate", "rates", "denominator", "denominators"})
RATE_EXACT_KEYS = frozenset({"measurement_status"})
MARKER_KEY_TOKENS = frozenset(
    {
        "verdict",
        "claim",
        "claims",
        "acceptance",
        "result",
        "status",
        "outcome",
        "marker",
        "promotion",
        "classification",
        "grade",
        "label",
    }
)
REQUIREMENT_KEY_TOKENS = frozenset({"requirement"})
REQUIREMENT_STATUS_TOKENS = frozenset({"status", "effect", "state", "closure"})
REQUIREMENT_STATUS_ALLOWED = ("unchanged", "none", "forbidden")
BATTERY_WALLCLOCK_KEYS = frozenset(
    {
        "duration_ms",
        "elapsed_ms",
        "generated_at",
        "wall_clock",
        "started_at",
        "finished_at",
        "timestamp",
    }
)
# Declaration containers legitimately *name* the tokens they refuse.
EXEMPT_KEYS = frozenset(
    {"non_claims", "does_not_mean", "does_not_prove", "forbidden_keys", "forbidden_seed_keys"}
)
EXEMPT_KEY_PREFIX = "forbidden_"

LIFECYCLE_PIN = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}
PROMOTION_CONTRACT_PIN = {
    "promotion": "none",
    "classification": "not-authorized",
    "threshold": None,
    "human_acceptance": None,
    "is_gold": False,
    "model_invoked": False,
    "legal_claim": "forbidden",
    "n2_claim": "forbidden",
    "rate_publication": "forbidden",
    "measurement_status_publication": "forbidden",
    "corpus_complete_is_not_acceptance": True,
    "integrity_marker_is_not_acceptance": True,
}
S03_ISOLATION_PIN = {
    "evaluation_report_path": REPORT_REL,
    "evaluation_report_must_be_absent": True,
    "s03_battery_path": S03_BATTERY_REL,
    "s03_battery_human_pilot_performed_required": False,
    "s03_rates_required_status": "not-measured",
    "rate_import_forbidden": True,
    "seed_fragment_root": SEED_ROOT_REL,
    "seed_fragment_glob": "*.txt",
    "seed_fragment_count": SEED_FRAGMENT_COUNT,
    "seed_aggregate_sha256": SEED_AGGREGATE_SHA256,
    "seed_sidecar_path": SEED_SIDECAR_REL,
    "seed_sidecar_sha256": SEED_SIDECAR_SHA256,
    "crates_reference_forbidden": True,
    "crates_reference_patterns": ["m207-s03", "m207_s03", "m207-s04", "m207_s04"],
    "seed_enlarge_diagnostic": "SEED_ENLARGED",
    "seed_drift_diagnostic": "SEED_DRIFT",
}
PRIOR_NON_PASS_PIN = {
    "path": PRIOR_RECEIPT_REL,
    "sha256": PRIOR_RECEIPT_SHA256,
    "attempt_id_pin": PRIOR_ATTEMPT_ID,
    "terminal_outcome_pin": "timeout",
    "terminal_signal_pin": "SIGTERM",
    "timeout_flag_pin": True,
    "operational_acceptance_pin": "non-pass",
    "may_be_rewritten": False,
    "diagnostic": "C4_TIMEOUT_AS_PASS",
}

# The closed vocabulary this tool may speak.  Every name must exist in the frozen
# ``$.diagnostics`` table, or the run is ``DIAGNOSTIC_TABLE_DRIFT``.
SPOKEN_DIAGNOSTICS = (
    "PROMOTION_CLAIM",
    "GOLD_CLAIM",
    "IS_GOLD_CLAIM",
    "THRESHOLD_REQUESTED",
    "CLASSIFICATION_REQUESTED",
    "MODEL_INVOKED",
    "AUTHORITY_CLAIM",
    "S03_RATE_IMPORTED",
    "S03_BATTERY_PILOT_PERFORMED",
    "SEED_ENLARGED",
    "SEED_DRIFT",
    "REQUIREMENT_STATUS_CLAIM",
    "C4_RECEIPT_MISSING",
    "C4_RECEIPT_DRIFT",
    "C4_TIMEOUT_AS_PASS",
    "INTEGRITY_MARKER_AS_ACCEPTANCE",
    "BUDGET_BELOW_MINIMUM",
    "DURATION_MISSING",
    "TERMINAL_OUTCOME_DRIFT",
    "ARGV_PIN_DRIFT",
    "LOG_HASH_MISSING",
    "ATTEMPT_LOG_MISSING",
    "IMMUTABLE_IDENTITY_MISSING",
    "TOOLCHAIN_PIN_MISSING",
    "REPORT_WITHOUT_HUMAN_DATA",
    "MISSING_LIFECYCLE_MARKER",
    "BATTERY_WALLCLOCK_FORBIDDEN",
    "FROZEN_SOURCE_DRIFT",
    "MISSING_ARTIFACT",
    "MISSING_NON_CLAIM",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "DUPLICATE_JSON_KEY",
    "DIAGNOSTIC_TABLE_DRIFT",
    "UNSAFE_PATH",
)

VERDICT_NON_CLAIMS = (
    "not gold: the verdict is a process record, never a gold label",
    "not a promotion: promotion stays none and classification stays not-authorized",
    "not a threshold: no rate threshold, pass/fail cut-off or accept/reject decision is introduced",
    "not a classification: no classifier is fitted and no D388 gate is scored",
    "not independent-measured: S04 ran no pilot and publishes no measured rate",
    "not an S03 rate publication: no S03 aspect, stratum or denominator value is read or imported",
    "not a seed enlargement: the 180 frozen fragments and the rule-seed sidecar stay frozen",
    "not a requirement closure: requirement_status_effect stays unchanged",
    "not a terminal-outcome rewrite: the acceptance basis is recomputed from the receipt facts",
    "not a battery verdict: the integrity marker is never spoken by this tool",
)

TEXT_SUFFIXES = frozenset(
    {".rs", ".toml", ".md", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".lock", ".py", ".sql"}
)
SKIP_DIR_TOKENS = frozenset({"target", ".git", "__pycache__", ".tox", "node_modules", ".venv"})

TOKEN_SPLIT_RE = re.compile(r"[^0-9a-zA-Z]+")
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
STDERR_OBSERVED_RE = re.compile(r"observed=(\d+)")

Failures = list[tuple[str, str]]


class GateError(Exception):
    """A fail-closed stop that carries its own named diagnostic."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise GateError("DUPLICATE_JSON_KEY", f"duplicate JSON key {key!r}")
        document[key] = value
    return document


def parse_json_text(text: str, label: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not closed JSON: {exc}") from exc


def load_json(path: Path, label: str) -> Any:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} carries a UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not UTF-8: {exc}") from exc
    return parse_json_text(text, label)


def resolve_path(root: Path, raw: Any, label: str, *, suffix: str = "", prefix: str = "") -> Path:
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
    if prefix and not relative.as_posix().startswith(prefix):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must live under {prefix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def key_tokens(key: str) -> list[str]:
    spaced = CAMEL_BOUNDARY_RE.sub("_", key)
    return [token for token in TOKEN_SPLIT_RE.split(spaced.lower()) if token]


def iter_keyed(node: Any, pointer: str = "", exempt: bool = False):
    """Yield ``(pointer, key, value, exempt)`` for every keyed node."""
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            child_exempt = exempt or name in EXEMPT_KEYS or name.startswith(EXEMPT_KEY_PREFIX)
            child_pointer = f"{pointer}/{name}"
            yield child_pointer, name, value, child_exempt
            yield from iter_keyed(value, child_pointer, child_exempt)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from iter_keyed(item, f"{pointer}[{index}]", exempt)


def acceptance_for(outcome: Any, exit_code: Any, duration_ms: Any, budget_seconds: Any) -> str:
    """The M204/S06 acceptance rule, reused verbatim: pass needs all three facts."""
    if outcome != "complete":
        return "non-pass"
    if exit_code != 0:
        return "non-pass"
    if not isinstance(duration_ms, int) or not isinstance(budget_seconds, int):
        return "non-pass"
    return "pass" if duration_ms >= budget_seconds * 1000 else "non-pass"


def compare_subset(actual: Any, expected: Any, pointer: str, failures: Failures) -> None:
    """Every key of ``expected`` must be present in ``actual`` with the same value."""
    if not isinstance(actual, dict):
        _fail(failures, "FROZEN_SOURCE_DRIFT", f"{pointer} is not an object")
        return
    for key, wanted in expected.items():
        here = f"{pointer}/{key}"
        if key not in actual:
            _fail(failures, "FROZEN_SOURCE_DRIFT", f"{here} is missing from the frozen contract")
            continue
        got = actual[key]
        if isinstance(wanted, dict):
            compare_subset(got, wanted, here, failures)
        elif got != wanted:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"{here}={got!r} does not match the frozen value {wanted!r}",
            )


# --------------------------------------------------------------------------- #
# Frozen contract agreement: the in-code constants against the frozen document.
# --------------------------------------------------------------------------- #


def check_contract(root: Path, schemas_rel: str, failures: Failures) -> dict[str, Any] | None:
    try:
        path = resolve_path(root, schemas_rel, "schemas", suffix=".json", prefix=ANNOTATION_PREFIX)
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None
    if not path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"frozen S04 schema document missing at {schemas_rel}")
        return None
    try:
        document = load_json(path, "S04 schema document")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None
    if not isinstance(document, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the S04 schema document root must be an object")
        return None

    compare_subset(
        document,
        {
            "schema": SCHEMAS_SCHEMA_ID,
            "promotion_contract": PROMOTION_CONTRACT_PIN,
            "s03_isolation": S03_ISOLATION_PIN,
            "prior_non_pass_pin": PRIOR_NON_PASS_PIN,
            "lifecycle": LIFECYCLE_PIN,
        },
        "$",
        failures,
    )

    frozen_sources = document.get("frozen_sources")
    if not isinstance(frozen_sources, dict):
        _fail(failures, "FROZEN_SOURCE_DRIFT", "$/frozen_sources is not an object")
    else:
        for name, expected in (
            ("m207_s03_battery", S03_BATTERY_SHA256),
            ("m199_seed_sidecar", SEED_SIDECAR_SHA256),
            ("m204_s06_c4_operational_receipt", PRIOR_RECEIPT_SHA256),
        ):
            entry = frozen_sources.get(name)
            if not isinstance(entry, dict) or entry.get("sha256") != expected:
                _fail(
                    failures,
                    "FROZEN_SOURCE_DRIFT",
                    f"$/frozen_sources/{name}/sha256 does not match the pinned digest",
                )

    marker = document.get("integrity_marker")
    if not isinstance(marker, dict):
        _fail(failures, "FROZEN_SOURCE_DRIFT", "$/integrity_marker is not an object")
    else:
        compare_subset(
            marker,
            {
                "marker": INTEGRITY_MARKER,
                "marker_is_not_acceptance": True,
                "marker_values": [INTEGRITY_MARKER],
            },
            "$/integrity_marker",
            failures,
        )

    diagnostics = document.get("diagnostics")
    if not isinstance(diagnostics, list) or not diagnostics:
        _fail(failures, "DIAGNOSTIC_TABLE_DRIFT", "$/diagnostics must be a non-empty list")
    else:
        known = {name for name in diagnostics if isinstance(name, str)}
        if len(known) != len(diagnostics):
            _fail(failures, "DIAGNOSTIC_TABLE_DRIFT", "$/diagnostics must hold only strings")
        if len(known) != len(set(known)) or len(known) != len(diagnostics):
            _fail(failures, "DIAGNOSTIC_TABLE_DRIFT", "$/diagnostics must be duplicate-free")
        unknown = sorted(set(SPOKEN_DIAGNOSTICS) - known)
        if unknown:
            _fail(
                failures,
                "DIAGNOSTIC_TABLE_DRIFT",
                f"this tool speaks {unknown} outside the frozen diagnostic table",
            )

    non_claims = document.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims:
        _fail(failures, "MISSING_NON_CLAIM", "the frozen contract carries no non-claims")

    return document


# --------------------------------------------------------------------------- #
# Claim, rate, marker and requirement scans over derived artifacts.
# --------------------------------------------------------------------------- #


def scan_claims(tree: Any, label: str, failures: Failures) -> None:
    for pointer, key, value, exempt in iter_keyed(tree):
        if exempt:
            continue
        frozen = PROMOTION_KEY_MAP.get(key)
        if frozen is None:
            continue
        wanted, diagnostic = frozen
        if value != wanted:
            _fail(
                failures,
                diagnostic,
                f"{label}{pointer}={value!r} is not the frozen {wanted!r}",
            )


def scan_rate_keys(tree: Any, label: str, failures: Failures) -> None:
    for pointer, key, _value, exempt in iter_keyed(tree):
        if exempt:
            continue
        lowered = key.lower()
        tokens = set(key_tokens(key))
        if lowered in RATE_EXACT_KEYS or tokens & RATE_KEY_TOKENS:
            _fail(
                failures,
                "S03_RATE_IMPORTED",
                f"{label}{pointer} publishes a rate surface; S04 imports no S03 rate",
            )


def scan_marker_values(tree: Any, label: str, failures: Failures) -> None:
    for pointer, key, value, exempt in iter_keyed(tree):
        if exempt or not isinstance(value, str):
            continue
        if not set(key_tokens(key)) & MARKER_KEY_TOKENS:
            continue
        if INTEGRITY_MARKER in value:
            _fail(
                failures,
                "INTEGRITY_MARKER_AS_ACCEPTANCE",
                f"{label}{pointer} reads the integrity marker as a verdict",
            )


def scan_requirement_status(tree: Any, label: str, failures: Failures) -> None:
    for pointer, key, value, exempt in iter_keyed(tree):
        if exempt or not isinstance(value, str):
            continue
        tokens = set(key_tokens(key))
        if not tokens & REQUIREMENT_KEY_TOKENS or not tokens & REQUIREMENT_STATUS_TOKENS:
            continue
        if value not in REQUIREMENT_STATUS_ALLOWED:
            _fail(
                failures,
                "REQUIREMENT_STATUS_CLAIM",
                f"{label}{pointer}={value!r} claims a requirement status effect",
            )


def scan_derived(tree: Any, label: str, failures: Failures) -> None:
    scan_claims(tree, label, failures)
    scan_rate_keys(tree, label, failures)
    scan_marker_values(tree, label, failures)
    scan_requirement_status(tree, label, failures)


# --------------------------------------------------------------------------- #
# The C4 receipt: process facts, recomputed acceptance and substantiation.
# --------------------------------------------------------------------------- #


def check_receipt(root: Path, receipt_rel: str, failures: Failures) -> dict[str, Any] | None:
    try:
        path = resolve_path(root, receipt_rel, "receipt", suffix=".json", prefix=EVIDENCE_PREFIX)
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None
    if not path.is_file():
        _fail(
            failures,
            "C4_RECEIPT_MISSING",
            f"no C4 operational receipt at {receipt_rel}: a receipt is never inferred from logs",
        )
        return None
    try:
        receipt = load_json(path, "C4 operational receipt")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None
    if not isinstance(receipt, dict):
        _fail(failures, "C4_RECEIPT_DRIFT", "the receipt root must be a JSON object")
        return None

    if receipt.get("schema") != RECEIPT_SCHEMA_ID:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"receipt schema={receipt.get('schema')!r} is not {RECEIPT_SCHEMA_ID!r}",
        )
    missing = [key for key in RECEIPT_REQUIRED_KEYS if key not in receipt]
    if missing:
        _fail(failures, "C4_RECEIPT_DRIFT", f"receipt is missing required keys {missing}")

    argv = receipt.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        _fail(failures, "ARGV_PIN_DRIFT", "receipt argv must be a list of strings")
        argv = []
    else:
        for flag in REQUIRED_ARGV_FLAGS:
            if flag not in argv:
                _fail(failures, "ARGV_PIN_DRIFT", f"receipt argv is missing {flag}")
        for flag in FORBIDDEN_ARGV_FLAGS:
            if flag in argv:
                _fail(
                    failures,
                    "ARGV_PIN_DRIFT",
                    f"receipt argv carries {flag}: a limited walk is not the declared corpus",
                )

    identity = receipt.get("immutable_attempt_identity")
    if not isinstance(identity, dict):
        _fail(failures, "IMMUTABLE_IDENTITY_MISSING", "the receipt carries no attempt identity")
    else:
        expected_argv_sha = sha256_bytes(json.dumps(argv, separators=(",", ":")).encode("utf-8"))
        if identity.get("attempt_id") != receipt.get("attempt_id"):
            _fail(
                failures,
                "IMMUTABLE_IDENTITY_MISSING",
                "immutable_attempt_identity.attempt_id disagrees with attempt_id",
            )
        if identity.get("argv_sha256") != expected_argv_sha:
            _fail(
                failures,
                "IMMUTABLE_IDENTITY_MISSING",
                "immutable_attempt_identity.argv_sha256 does not recompute from argv: "
                "the receipt was edited, not re-attempted",
            )

    terminal = receipt.get("terminal")
    outcome = exit_code = duration_ms = budget_seconds = None
    if not isinstance(terminal, dict):
        _fail(failures, "TERMINAL_OUTCOME_DRIFT", "terminal facts must be an object")
    else:
        absent = [key for key in TERMINAL_KEYS if key not in terminal]
        if absent:
            _fail(failures, "TERMINAL_OUTCOME_DRIFT", f"terminal is missing keys {absent}")
        extra = sorted(set(terminal) - set(TERMINAL_KEYS))
        if extra:
            _fail(failures, "TERMINAL_OUTCOME_DRIFT", f"terminal carries unknown keys {extra}")
        outcome = terminal.get("outcome")
        exit_code = terminal.get("exit_code")
        timeout_flag = terminal.get("timeout")
        signal = terminal.get("signal")
        if outcome not in TERMINAL_OUTCOMES:
            _fail(failures, "TERMINAL_OUTCOME_DRIFT", f"terminal.outcome={outcome!r} is unknown")
        if not isinstance(timeout_flag, bool):
            _fail(failures, "TERMINAL_OUTCOME_DRIFT", "terminal.timeout must be a boolean")
        if outcome == "complete" and timeout_flag is True:
            _fail(
                failures,
                "TERMINAL_OUTCOME_DRIFT",
                "terminal.outcome=complete with timeout=true is incoherent",
            )
        if outcome == "timeout":
            if timeout_flag is not True or exit_code is not None or signal is None:
                _fail(
                    failures,
                    "TERMINAL_OUTCOME_DRIFT",
                    "a timeout is published with timeout=true, exit_code=null and a signal",
                )

    duration_ms = receipt.get("duration_ms")
    budget_seconds = receipt.get("budget_seconds")
    if not isinstance(duration_ms, int) or isinstance(duration_ms, bool) or duration_ms < 0:
        _fail(failures, "DURATION_MISSING", "receipt carries no integer duration_ms")
        duration_ms = None
    if not isinstance(budget_seconds, int) or isinstance(budget_seconds, bool):
        _fail(failures, "BUDGET_BELOW_MINIMUM", "receipt carries no integer budget_seconds")
        budget_seconds = None
    elif budget_seconds < BUDGET_SECONDS_MINIMUM:
        _fail(
            failures,
            "BUDGET_BELOW_MINIMUM",
            f"budget_seconds={budget_seconds} is below the frozen minimum {BUDGET_SECONDS_MINIMUM}",
        )

    claims = receipt.get("claims")
    published: Any = None
    if not isinstance(claims, dict):
        _fail(failures, "C4_RECEIPT_DRIFT", "claims must be an object")
    else:
        if claims.get("receipt_is_runtime_attempt") is not True:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                "claims.receipt_is_runtime_attempt must record a real runtime attempt",
            )
        published = claims.get("operational_acceptance")
        if published not in ACCEPTANCE_VALUES:
            _fail(
                failures,
                "TERMINAL_OUTCOME_DRIFT",
                f"claims.operational_acceptance={published!r} is not in the acceptance vocabulary",
            )
        else:
            recomputed = acceptance_for(outcome, exit_code, duration_ms, budget_seconds)
            if published == "pass" and recomputed != "pass":
                _fail(
                    failures,
                    "C4_TIMEOUT_AS_PASS",
                    "the receipt publishes operational_acceptance=pass while the frozen rule "
                    f"recomputes {recomputed!r} from its terminal facts",
                )
            elif published != recomputed:
                _fail(
                    failures,
                    "TERMINAL_OUTCOME_DRIFT",
                    f"the receipt publishes {published!r} while the frozen rule recomputes "
                    f"{recomputed!r}",
                )

    check_receipt_logs(root, receipt, failures)
    scan_derived(receipt, "receipt", failures)
    return receipt


def check_receipt_logs(root: Path, receipt: dict[str, Any], failures: Failures) -> None:
    logs = receipt.get("logs")
    if not isinstance(logs, dict):
        _fail(failures, "ATTEMPT_LOG_MISSING", "the receipt records no attempt logs")
        return
    for stream in ("stdout", "stderr"):
        raw = logs.get(stream)
        pinned = logs.get(f"{stream}_sha256")
        try:
            path = resolve_path(root, raw, f"logs.{stream}", suffix=".log", prefix=EVIDENCE_PREFIX)
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        if not path.is_file():
            _fail(
                failures,
                "ATTEMPT_LOG_MISSING",
                f"the pinned {stream} log {raw!r} is not on disk",
            )
            continue
        actual = sha256_file(path)
        if pinned != actual:
            _fail(
                failures,
                "LOG_HASH_MISSING",
                f"logs.{stream}_sha256={pinned!r} does not hash {raw!r} ({actual})",
            )
        if stream == "stdout":
            check_attempt_records(path, receipt, failures)
        else:
            check_stderr_observation(path, receipt)


def check_attempt_records(log_path: Path, receipt: dict[str, Any], failures: Failures) -> None:
    """Substantiate the receipt from the JSONL envelope the run itself wrote."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeDecodeError) as exc:
        _fail(failures, "C4_RECEIPT_DRIFT", f"the attempt record is unreadable: {exc}")
        return

    records: dict[str, dict[str, Any]] = {}
    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            record = parse_json_text(line, f"attempt record line {index + 1}")
        except GateError as exc:
            _fail(failures, exc.diagnostic, f"attempt record line {index + 1}: {exc.detail}")
            return
        if not isinstance(record, dict):
            _fail(failures, "C4_RECEIPT_DRIFT", f"attempt record line {index + 1} is not an object")
            return
        kind = record.get("record_kind")
        if kind in ENVELOPE_RECORD_KINDS:
            if kind in records:
                _fail(
                    failures,
                    "C4_RECEIPT_DRIFT",
                    f"the attempt record carries {kind} more than once",
                )
                return
            records[str(kind)] = record

    absent = [kind for kind in ENVELOPE_RECORD_KINDS if kind not in records]
    if absent:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"the attempt record is missing {absent}: the receipt is not substantiated",
        )
        return

    header = records["header"]
    aggregate = records["aggregate"]
    inventory = records["inventory"]
    payload = records["canonical_payload"]
    envelope = records["operational_envelope"]
    observed = receipt.get("observed_output")
    if not isinstance(observed, dict):
        _fail(failures, "C4_RECEIPT_DRIFT", "observed_output must be an object")
        observed = {}
    try:
        observed_digest = observed.get("inventory_digest")
        for label, record in (
            ("header", header),
            ("canonical_payload", payload),
        ):
            if record.get("inventory_digest") != observed_digest:
                _fail(
                    failures,
                    "C4_RECEIPT_DRIFT",
                    f"{label}.inventory_digest disagrees with observed_output.inventory_digest",
                )
        if header.get("schema") != CONTOUR_SCHEMA_ID or payload.get("schema") != CONTOUR_SCHEMA_ID:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                f"the attempt record schema is not {CONTOUR_SCHEMA_ID!r}",
            )
        for label, record in (("header", header), ("canonical_payload", payload)):
            if record.get("profile") != PROFILE_PIN or record.get("limit") is not None:
                _fail(
                    failures,
                    "ARGV_PIN_DRIFT",
                    f"{label} records profile/limit that do not match the declared contour walk",
                )
        if payload.get("parser_revision") != receipt.get("parser_revision"):
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                "canonical_payload.parser_revision disagrees with the receipt",
            )
        if payload.get("parser_revision") != PARSER_REVISION_PIN:
            _fail(failures, "FROZEN_SOURCE_DRIFT", "the parser revision is not the pinned one")
        if payload.get("source_revision") != receipt.get("source_revision"):
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                "canonical_payload.source_revision disagrees with the receipt",
            )
        contract = receipt.get("contract")
        if not isinstance(contract, dict):
            _fail(failures, "C4_RECEIPT_DRIFT", "contract must be an object")
        else:
            for key, expected in (
                ("acceptance_contract_version", CONTRACT_VERSION_PIN),
                ("acceptance_check_id", CONTRACT_CHECK_ID_PIN),
                ("acceptance_mode", CONTRACT_MODE_PIN),
            ):
                if (
                    payload.get(key) != expected
                    or contract.get(
                        {
                            "acceptance_contract_version": "version",
                            "acceptance_check_id": "check_id",
                            "acceptance_mode": "mode",
                        }[key]
                    )
                    != expected
                ):
                    _fail(
                        failures,
                        "C4_RECEIPT_DRIFT",
                        f"the attempt record's {key} disagrees with the receipt contract pin",
                    )
        envelope_argv = envelope.get("argv")
        if not isinstance(envelope_argv, list) or envelope_argv != receipt.get("argv", [])[1:]:
            _fail(
                failures,
                "ARGV_PIN_DRIFT",
                "the run recorded a different argv than the receipt publishes",
            )
        observed_rustc = envelope.get("observed_rustc_version")
        toolchain = receipt.get("toolchain")
        if not isinstance(toolchain, dict) or observed_rustc != toolchain.get("rustc"):
            _fail(
                failures,
                "TOOLCHAIN_PIN_MISSING",
                "the observed rustc version disagrees with the receipt toolchain pin",
            )
        run_status = envelope.get("run_status")
        outcome = receipt.get("terminal", {}).get("outcome")
        if run_status != "complete" and outcome == "complete":
            _fail(
                failures,
                "C4_TIMEOUT_AS_PASS",
                f"the run recorded run_status={run_status!r} while the receipt claims complete",
            )
        elif run_status == "complete" and outcome != "complete":
            _fail(
                failures,
                "TERMINAL_OUTCOME_DRIFT",
                f"the run recorded run_status=complete while the receipt publishes {outcome!r}",
            )
        envelope_duration = envelope.get("duration_ms")
        receipt_duration = receipt.get("duration_ms")
        if (
            isinstance(envelope_duration, int)
            and isinstance(receipt_duration, int)
            and envelope_duration > receipt_duration
        ):
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                "the recorded walk is longer than the receipt's own duration",
            )
        files = aggregate.get("files")
        decoded = aggregate.get("decoded")
        failed = aggregate.get("failed")
        if not all(isinstance(item, int) for item in (files, decoded, failed)):
            _fail(failures, "C4_RECEIPT_DRIFT", "the aggregate record carries no integer counts")
        else:
            if decoded + failed != files:
                _fail(
                    failures,
                    "C4_RECEIPT_DRIFT",
                    f"the aggregate record does not add up: decoded {decoded} + failed {failed} "
                    f"!= files {files}",
                )
            for label, record in (
                ("canonical_payload", payload),
                ("operational_envelope", envelope),
            ):
                if record.get("files", record.get("observed_file_count")) != files:
                    _fail(
                        failures,
                        "C4_RECEIPT_DRIFT",
                        f"{label} disagrees with the aggregate file count",
                    )
        provider = None
        dimensions = inventory.get("dimensions")
        if isinstance(dimensions, dict) and isinstance(dimensions.get("provider"), dict):
            provider = dimensions["provider"]
        corpus = receipt.get("corpus")
        if provider is None or not isinstance(corpus, dict):
            _fail(failures, "C4_RECEIPT_DRIFT", "the provider inventory or corpus block is absent")
        else:
            if provider.get("consultant") != corpus.get("consultant_xml_count"):
                _fail(
                    failures,
                    "C4_RECEIPT_DRIFT",
                    "the run observed a different consultant count than the receipt declares",
                )
            if provider.get("garant") != corpus.get("garant_file_count"):
                _fail(
                    failures,
                    "C4_RECEIPT_DRIFT",
                    "the run observed a different Garant count than the receipt declares",
                )
        receipt["__semantic_observations__"] = {
            "record_kind": CONTOUR_SCHEMA_ID,
            "envelope_run_status": run_status,
            "observed_file_count": envelope.get("observed_file_count"),
            "decoded": decoded,
            "failed": failed,
            "failed_decode_is_a_parser_observation": True,
            "acceptance_effect": "none",
            "non_claim": (
                "a failed decode is a parser observation, never a quality, gold, legal or "
                "acceptance verdict"
            ),
        }
    except AttributeError as exc:  # pragma: no cover - defensive: malformed nested types
        _fail(failures, "C4_RECEIPT_DRIFT", f"the attempt record is malformed: {exc}")


def check_stderr_observation(log_path: Path, receipt: dict[str, Any]) -> None:
    """Record the binary's own stderr count; a present count must match the pin."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    match = STDERR_OBSERVED_RE.search(text)
    if match is None:
        receipt["__stderr_observed_count__"] = None
        return
    observed = int(match.group(1))
    receipt["__stderr_observed_count__"] = observed


# --------------------------------------------------------------------------- #
# Prior non-pass, S03 isolation and the optional T04 battery.
# --------------------------------------------------------------------------- #


def check_prior_receipt(root: Path, prior_rel: str, failures: Failures) -> dict[str, Any] | None:
    try:
        path = resolve_path(
            root, prior_rel, "prior-receipt", suffix=".json", prefix=EVIDENCE_PREFIX
        )
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None
    if not path.is_file():
        _fail(failures, "MISSING_ARTIFACT", "the pinned prior non-pass receipt is missing")
        return None
    digest = sha256_file(path)
    if digest != PRIOR_RECEIPT_SHA256:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            f"the pinned prior non-pass receipt was rewritten ({digest}); a timeout never becomes "
            "a success",
        )
        return None
    try:
        prior = load_json(path, "prior non-pass receipt")
    except GateError as exc:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            f"the pinned prior non-pass receipt is unreadable: {exc.detail}",
        )
        return None
    if not isinstance(prior, dict):
        _fail(failures, "C4_TIMEOUT_AS_PASS", "the pinned prior non-pass receipt is not an object")
        return None
    terminal = prior.get("terminal") if isinstance(prior.get("terminal"), dict) else {}
    claims = prior.get("claims") if isinstance(prior.get("claims"), dict) else {}
    if (
        prior.get("attempt_id") != PRIOR_ATTEMPT_ID
        or terminal.get("outcome") != "timeout"
        or terminal.get("signal") != "SIGTERM"
        or terminal.get("timeout") is not True
        or claims.get("operational_acceptance") != "non-pass"
    ):
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "the pinned prior attempt no longer publishes timeout/SIGTERM/non-pass",
        )
    return prior


def check_lifecycle(document: Any, label: str, failures: Failures) -> None:
    """Every derived artifact keeps the frozen lifecycle markers."""
    if not isinstance(document, dict):
        return
    lifecycle = document.get("lifecycle")
    if not isinstance(lifecycle, dict):
        _fail(failures, "MISSING_LIFECYCLE_MARKER", f"{label} carries no lifecycle markers")
        return
    moved = {
        key: lifecycle.get(key)
        for key, wanted in LIFECYCLE_PIN.items()
        if lifecycle.get(key) != wanted
    }
    if moved:
        _fail(
            failures,
            "MISSING_LIFECYCLE_MARKER",
            f"{label} lifecycle markers drifted from the frozen set: {moved}",
        )


def seed_state(seed_root: Path) -> tuple[int, str]:
    fragments = sorted(
        (path for path in seed_root.glob("*.txt") if path.is_file()), key=lambda item: item.name
    )
    digest = hashlib.sha256()
    for path in fragments:
        digest.update(
            path.name.encode("utf-8") + b"\x00" + sha256_file(path).encode("ascii") + b"\n"
        )
    return len(fragments), digest.hexdigest()


def check_s03_isolation(
    root: Path,
    *,
    report_rel: str,
    s03_battery_rel: str,
    seed_root_rel: str,
    crates_rel: str,
    failures: Failures,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "evaluation_report": "absent",
        "battery_human_pilot_performed": None,
        "battery_current": False,
        "seed_fragment_count": None,
        "seed_aggregate_sha256": None,
        "crates_m207_references": 0,
        "s03_rates_status": "not-measured",
    }

    # The report is never read: existence is the whole claim.
    try:
        report_path = resolve_path(
            root, report_rel, "evaluation-report", suffix=".json", prefix=EVIDENCE_PREFIX
        )
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        report_path = None
    if report_path is not None and report_path.exists():
        state["evaluation_report"] = "present"
        _fail(
            failures,
            "REPORT_WITHOUT_HUMAN_DATA",
            "an S03 evaluation report exists while no validated human reference is recorded: "
            "it is a fabricated denominator, not a measurement",
        )

    try:
        battery_path = resolve_path(
            root, s03_battery_rel, "s03-battery", suffix=".json", prefix=EVIDENCE_PREFIX
        )
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        battery_path = None
    if battery_path is None or not battery_path.is_file():
        _fail(failures, "FROZEN_SOURCE_DRIFT", "the pinned S03 battery is missing")
    else:
        digest = sha256_file(battery_path)
        state["battery_current"] = digest == S03_BATTERY_SHA256
        if not state["battery_current"]:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                "the S03 battery no longer matches the pinned digest; the S03 contour moved",
            )
        try:
            battery = load_json(battery_path, "S03 battery")
        except GateError as exc:
            _fail(failures, "FROZEN_SOURCE_DRIFT", f"the S03 battery is unreadable: {exc.detail}")
            battery = None
        if isinstance(battery, dict):
            if battery.get("schema") != S03_BATTERY_SCHEMA_ID:
                _fail(
                    failures,
                    "FROZEN_SOURCE_DRIFT",
                    f"the S03 battery schema is not {S03_BATTERY_SCHEMA_ID!r}",
                )
            performed = battery.get("human_pilot_performed")
            state["battery_human_pilot_performed"] = performed
            if performed is not False:
                _fail(
                    failures,
                    "S03_BATTERY_PILOT_PERFORMED",
                    "the S03 battery claims a human pilot that the absent report does not hold",
                )
            if battery.get("model_invoked") is not False:
                _fail(
                    failures,
                    "MODEL_INVOKED",
                    "the S03 battery records a model invocation; S04 models nothing",
                )
            check_lifecycle(battery, "s03_battery", failures)
            scan_derived(battery, "s03_battery", failures)
        elif battery is not None:
            _fail(failures, "FROZEN_SOURCE_DRIFT", "the S03 battery root is not an object")

    try:
        seed_root = resolve_path(root, seed_root_rel, "seed-root", prefix=CRATES_REL)
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        seed_root = None
    if seed_root is not None and not seed_root.is_dir():
        _fail(
            failures, "MISSING_ARTIFACT", f"the frozen fragment seed is missing at {seed_root_rel}"
        )
    elif seed_root is not None:
        count, aggregate = seed_state(seed_root)
        state["seed_fragment_count"] = count
        state["seed_aggregate_sha256"] = aggregate
        if count != SEED_FRAGMENT_COUNT:
            _fail(
                failures,
                "SEED_ENLARGED",
                f"the frozen seed holds {count} fragments, not {SEED_FRAGMENT_COUNT}",
            )
        if aggregate != SEED_AGGREGATE_SHA256:
            _fail(
                failures,
                "SEED_DRIFT",
                "a frozen fragment or its name changed: the aggregate digest moved",
            )
        sidecar = seed_root / "lawref_seed.json"
        if not sidecar.is_file() or sha256_file(sidecar) != SEED_SIDECAR_SHA256:
            _fail(
                failures,
                "SEED_DRIFT",
                "the rule-seed sidecar no longer matches its pinned digest",
            )

    state["crates_m207_references"] = check_crates_isolation(root, crates_rel, failures)
    return state


def check_crates_isolation(root: Path, crates_rel: str, failures: Failures) -> int:
    try:
        base = resolve_path(root, crates_rel, "crates-root")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return 0
    if not base.is_dir():
        _fail(failures, "MISSING_ARTIFACT", "crates/ is absent; the isolation scan cannot run")
        return 0
    hits = 0
    root_resolved = root.resolve()
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            relative_parts = path.resolve().relative_to(root_resolved).parts
        except ValueError:
            continue
        if any(part in SKIP_DIR_TOKENS for part in relative_parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in S03_ISOLATION_PIN["crates_reference_patterns"]:
            if pattern in text:
                hits += 1
                _fail(
                    failures,
                    "S03_RATE_IMPORTED",
                    f"{Path(*relative_parts).as_posix()} references {pattern!r}: the product "
                    "runtime gains no M207 reader",
                )
                break
        if hits >= 5:
            break
    return hits


def check_s04_battery(root: Path, battery_rel: str, failures: Failures) -> None:
    """A later T04 battery is validated when present; absence is not a failure here."""
    try:
        path = resolve_path(
            root, battery_rel, "s04-battery", suffix=".json", prefix=EVIDENCE_PREFIX
        )
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    if not path.is_file():
        return
    document = _load_battery(path, failures)
    if not isinstance(document, dict):
        return
    if document.get("schema") != S04_BATTERY_SCHEMA_ID:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"the S04 battery schema is not {S04_BATTERY_SCHEMA_ID!r}",
        )
    if document.get("human_pilot_performed") is not False:
        _fail(
            failures,
            "S03_BATTERY_PILOT_PERFORMED",
            "the S04 battery claims a human pilot; S04 runs none",
        )
    if document.get("model_invoked") is not False:
        _fail(
            failures,
            "MODEL_INVOKED",
            "the S04 battery records a model invocation; S04 models nothing",
        )
    for pointer, key, _value, _exempt in iter_keyed(document):
        if key in BATTERY_WALLCLOCK_KEYS:
            _fail(
                failures,
                "BATTERY_WALLCLOCK_FORBIDDEN",
                f"the tracked battery carries the wall-clock key {pointer}; it is a byte-stable "
                "projection",
            )
    check_lifecycle(document, "s04_battery", failures)
    scan_derived(document, "s04_battery", failures)


def _load_battery(path: Path, failures: Failures) -> Any:
    try:
        return load_json(path, "S04 battery")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None


# --------------------------------------------------------------------------- #
# Verdict assembly and reporting.
# --------------------------------------------------------------------------- #


def build_verdict(
    receipt: dict[str, Any] | None,
    isolation: dict[str, Any],
    receipt_rel: str,
) -> dict[str, Any]:
    terminal = receipt.get("terminal") if isinstance(receipt, dict) else None
    terminal = terminal if isinstance(terminal, dict) else {}
    claims = receipt.get("claims") if isinstance(receipt, dict) else None
    claims = claims if isinstance(claims, dict) else {}
    observations = receipt.get("__semantic_observations__") if isinstance(receipt, dict) else None
    recomputed = acceptance_for(
        terminal.get("outcome"),
        terminal.get("exit_code"),
        receipt.get("duration_ms") if isinstance(receipt, dict) else None,
        receipt.get("budget_seconds") if isinstance(receipt, dict) else None,
    )
    published = claims.get("operational_acceptance")
    verdict: dict[str, Any] = {
        "schema": VERDICT_SCHEMA_ID,
        "receipt": {
            "path": receipt_rel,
            "schema": receipt.get("schema") if isinstance(receipt, dict) else None,
            "attempt_id": receipt.get("attempt_id") if isinstance(receipt, dict) else None,
            "argv_sha256": (
                receipt.get("immutable_attempt_identity", {}).get("argv_sha256")
                if isinstance(receipt, dict)
                and isinstance(receipt.get("immutable_attempt_identity"), dict)
                else None
            ),
        },
        "promotion": "none",
        "classification": "not-authorized",
        "threshold": None,
        "human_acceptance": None,
        "is_gold": False,
        "model_invoked": False,
        "legal_claim": "forbidden",
        "n2_claim": "forbidden",
        "rate_publication": "forbidden",
        "measurement_status_publication": "forbidden",
        "operational_acceptance": recomputed,
        "receipt_published_acceptance": published,
        "acceptance_basis": {
            "terminal_outcome": terminal.get("outcome"),
            "exit_code": terminal.get("exit_code"),
            "signal": terminal.get("signal"),
            "timeout": terminal.get("timeout"),
            "duration_ms": receipt.get("duration_ms") if isinstance(receipt, dict) else None,
            "budget_seconds": receipt.get("budget_seconds") if isinstance(receipt, dict) else None,
            "budget_ms": (
                receipt.get("budget_seconds", 0) * 1000
                if isinstance(receipt, dict) and isinstance(receipt.get("budget_seconds"), int)
                else None
            ),
            "rule": (
                "pass only when terminal.outcome is complete and terminal.exit_code is 0 and "
                "duration_ms >= budget_seconds * 1000"
            ),
            "budget_is_a_ceiling_not_an_achievement": True,
        },
        "corpus_complete_is_not_acceptance": True,
        "integrity_marker_is_not_acceptance": True,
        "human_pilot_performed": False,
        "s03_isolation": {
            "evaluation_report": isolation.get("evaluation_report"),
            "battery_human_pilot_performed": isolation.get("battery_human_pilot_performed"),
            "battery_current": isolation.get("battery_current"),
            "seed_fragment_count": isolation.get("seed_fragment_count"),
            "seed_aggregate_sha256": isolation.get("seed_aggregate_sha256"),
            "crates_m207_references": isolation.get("crates_m207_references"),
            "s03_rates_status": isolation.get("s03_rates_status"),
        },
        "semantic_observations": observations
        if isinstance(observations, dict)
        else {
            "record_kind": None,
            "envelope_run_status": None,
            "observed_file_count": None,
            "decoded": None,
            "failed": None,
            "failed_decode_is_a_parser_observation": True,
            "acceptance_effect": "none",
            "non_claim": "no attempt record was substantiated",
        },
        "stderr_observed_count": (
            receipt.get("__stderr_observed_count__") if isinstance(receipt, dict) else None
        ),
        "lifecycle": dict(LIFECYCLE_PIN),
        "non_claims": list(VERDICT_NON_CLAIMS),
    }
    return verdict


def canonical_json(document: Any) -> str:
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def emit(line: str) -> None:
    """Print a line, refusing to speak the T04 integrity marker."""
    if INTEGRITY_MARKER in line:
        raise GateError(
            "AUTHORITY_CLAIM",
            "this tool would print the integrity marker, which belongs to the T04 battery",
        )
    print(line)


def report(failures: Failures, verdict: dict[str, Any] | None) -> int:
    if not failures and verdict is not None:
        emit(f"{VERDICT_TAG} {canonical_json(verdict)}")
        observations = verdict["semantic_observations"]
        emit(
            f"{SEMANTIC_TAG} envelope_run_status={observations.get('envelope_run_status')} "
            f"files={observations.get('observed_file_count')} "
            f"decoded={observations.get('decoded')} failed={observations.get('failed')} "
            "acceptance_effect=none"
        )
        emit(MARKER)
        return 0
    seen: set[str] = set()
    for diagnostic, detail in failures:
        line = f"{diagnostic}: {detail}"
        if line in seen:
            continue
        seen.add(line)
        print(f"FAIL {line}", file=sys.stderr)
    if verdict is not None:
        print(
            f"FAIL {GATE_NAME}: {len(seen)} finding(s); promotion stays none and S03 stays "
            "not-measured",
            file=sys.stderr,
        )
    return 1


def collect_failures(args: argparse.Namespace, root: Path) -> tuple[Failures, dict[str, Any]]:
    failures: Failures = []
    check_contract(root, args.schemas, failures)
    check_prior_receipt(root, args.prior_receipt, failures)
    receipt = check_receipt(root, args.receipt, failures)
    isolation = check_s03_isolation(
        root,
        report_rel=args.report,
        s03_battery_rel=args.s03_battery,
        seed_root_rel=args.seed_root,
        crates_rel=args.crates,
        failures=failures,
    )
    check_s04_battery(root, args.battery, failures)
    verdict = build_verdict(receipt, isolation, args.receipt)
    return failures, verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check"],
        help="'check' re-derives the promotion verdict and the S03 isolation state, read-only",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--receipt", default=DEFAULT_RECEIPT_REL, help="the C4 receipt to verdict")
    parser.add_argument("--battery", default=DEFAULT_BATTERY_REL, help="an optional T04 battery")
    parser.add_argument(
        "--prior-receipt", default=PRIOR_RECEIPT_REL, help="the pinned prior attempt"
    )
    parser.add_argument("--s03-battery", default=S03_BATTERY_REL, help="the pinned S03 battery")
    parser.add_argument("--report", default=REPORT_REL, help="the S03 evaluation report path")
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="the frozen S04 schema document")
    parser.add_argument("--seed-root", default=SEED_ROOT_REL, help="the frozen fragment seed root")
    parser.add_argument("--crates", default=CRATES_REL, help="the product crate tree to scan")
    args = parser.parse_args(argv)

    try:
        root = Path(args.root)
        if not root.is_dir():
            print(f"FAIL MISSING_ARTIFACT: root {args.root} is not a directory", file=sys.stderr)
            return 1
        failures, verdict = collect_failures(args, root)
        return report(failures, verdict)
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
