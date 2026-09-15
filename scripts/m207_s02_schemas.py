#!/usr/bin/env python3
"""Frozen-protocol and closed-schema gate for the M207 S02 coding/pilot contour (T01).

This is an offline, fail-closed evidence gate for the S02 slice.  It binds four
frozen sources and two S02 artifacts:

* the frozen M199 annotation protocol (sha256-pinned), whose section 5 fixes the
  closed slot space, section 7 fixes annotator independence, section 8 fixes the
  span-exact rule and section 9 keeps agreement alpha out of reach;
* ``prd/annotation/m207-s01-codebook.md`` -- the frozen S01 coder codebook;
* ``prd/annotation/m207-s01-schemas.json`` -- the frozen S01 closed schemas,
  whose ``m207-s01-coding-submission/v1`` form S02 reuses **verbatim**;
* ``prd/migration/rust-evidence/m207-s01-pilot-cases.json`` -- the 40 frozen cases;
* ``prd/annotation/m207-s02-coder-protocol.md`` -- the frozen S02 protocol;
* ``prd/annotation/m207-s02-schemas.json`` -- the eight closed S02 schemas.

The gate proves, against the frozen sources rather than against prose:

* the S02 slot space is exactly the S01 / M199 section-5 set -- no ninth slot, no
  schema-version bump, and the submission form is not redefined;
* no closed key set, at any nesting depth or inside a ``*_keys`` array, mints a
  predicted-answer key (``label``/``expected``/``answer``/``prediction``/``gold``/
  ``capture``), a rule-seed span field, or a kit case field that would inline
  fragment text, slot names, slot values or ``work_family``;
* no surface claims authority (``authority``/``suggestion_status``), invokes a
  model, requests a classification, sets a threshold, promotes a label or claims
  gold; ``is_gold`` is admitted only where it is pinned ``false``;
* abstention stays a coder outcome, disjoint from the reference decision, and
  keeps its own agreement axis;
* adjudication carries a closed per-axis resolution space, ``append_only`` and
  ``is_gold: false``, and never rewrites the pre-adjudication agreement pin;
* the lifecycle markers and non-claims are present and exact;
* the store paths keep the D480 prefix lock;
* the protocol keeps its required sections and its ``[bounded]`` tag.

No annotation is created, inferred or repaired here: this gate only reads the
frozen artifacts and rejects drift.  ``check`` prints exactly the marker
``M207_S02_SCHEMAS_OK``; ``selftest`` additionally proves the negative paths
(including a real ``FROZEN_SOURCE_DRIFT`` against a mutated S01 copy) and prints
``M207_S02_SELFTEST_OK``.  Every failure is a non-zero exit with a named
diagnostic on stderr.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S02_SCHEMAS_OK"
SELFTEST_MARKER = "M207_S02_SELFTEST_OK"

SCHEMA_ID = "m207-s02-annotation-schemas/v1"
SCHEMA_VERSION = 1
PROTOCOL_ID = "m207-s02-coder-protocol/v1"
SUBMISSION_SCHEMA_ID = "m207-s01-coding-submission/v1"
SUBMISSION_SCHEMA_REUSED = True

PROTOCOL_REL = "prd/annotation/m207-s02-coder-protocol.md"
SCHEMAS_REL = "prd/annotation/m207-s02-schemas.json"
ANNOTATION_PREFIX = "prd/annotation/"
CONTRACT_HEADING = "Machine-readable protocol contract"
BOUNDED_TAG = "[bounded]"

M199_PROTOCOL_REL = "prd/migration/rust-evidence/m199-s01-annotation-protocol.md"
M199_PROTOCOL_SHA256 = "eed922b02c1b89b8e51e8b342b1a9f113a8029b8a2fe0a1bee84f9f2035c6e3d"
M199_SLOT_SECTION = "## 5. Closed slot set"
SLOT_SPACE_SOURCE = "prd/migration/rust-evidence/m199-s01-annotation-protocol.md#5"

S01_CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
S01_SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
S01_CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"

# Every frozen input S02 rests on, pinned by content digest.  A byte of drift in
# any of them stops the gate: the codebook and the S01 schemas must not be
# "improved" underneath a human pilot, and the case manifest must not be redrawn.
FROZEN_SOURCES: dict[str, tuple[str, str]] = {
    "m207_s01_codebook": (
        S01_CODEBOOK_REL,
        "1a1bfe944207e69cb5fb507e94d680384dadecf7ac98ac29b1de4932d7cb76c6",
    ),
    "m207_s01_schemas": (
        S01_SCHEMAS_REL,
        "63a4bc6629bade752f9fa02d1dd5fa6bbf21238e20772d2ba5b74f88ecca3682",
    ),
    "m207_s01_cases": (
        S01_CASES_REL,
        "9b0b6bc6bd8eadf9eb86886e45eb756ebade654e96ac3a84132ed9452bdeb9ad",
    ),
    "m199_protocol": (M199_PROTOCOL_REL, M199_PROTOCOL_SHA256),
}
EXPECTED_FROZEN_SOURCES = {
    key: {"path": path, "sha256": digest} for key, (path, digest) in FROZEN_SOURCES.items()
}

M199_SLOT_SPACE = (
    "marker_chain",
    "hier_nums",
    "date",
    "doc_no",
    "law_code",
    "anaphora",
    "range",
    "quoted_enum",
)
M199_BINARY_OUTCOME = "not_a_reference"
SLOT_KEY_COUNT = 9

ABSTENTION_VALUES = ("not-abstained", "ambiguous", "insufficient-context")
DECISION_VALUES = ("reference", "not_a_reference")
CODER_PASS_VALUES = (1, 2)
PROVENANCE_VALUE = "human-reviewed"
CASE_COUNT = 40
WORK_FAMILY_CAP = 4
RATIONALE_MAX_CHARS = 280
RATIONALE_MAX_CHARS_LIMIT = 500

AGREEMENT_AXES = (
    "reference_decision",
    "span_exact",
    "abstention",
    *(f"slot_{name}" for name in M199_SLOT_SPACE),
)

RESOLUTION_SPACE = {
    "by_axis": {
        "reference_decision": ["reference", "not_a_reference"],
        "span_exact": ["span_pass_1", "span_pass_2"],
        "abstention": ["not-abstained", "ambiguous", "insufficient-context"],
        **{f"slot_{name}": ["slot_present", "slot_absent"] for name in M199_SLOT_SPACE},
    },
    "derived_from": (
        "m207-s01-codebook/v1 alternative_classes plus the codebook abstention vocabulary"
    ),
    "span_axis_rule": (
        "span_pass_1 and span_pass_2 name one of the two already-committed coder spans; "
        "the adjudicator never mints a third span"
    ),
    "new_values_allowed": False,
}

OUTPUT_CONTRACT = {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": False,
    "classification": "not-authorized",
    "promotion": "none",
    "threshold": None,
}

STORE_PATHS = {
    "submissions": "prd/annotation/m207-s02-submissions",
    "adjudications": "prd/annotation/m207-s02-adjudications",
    "evidence": "prd/migration/rust-evidence",
    "allowed_prefix": ANNOTATION_PREFIX,
    "store_prefix_lock": True,
    "prefix_diagnostic": "UNSAFE_PATH",
}

PASS_PROTOCOL = {
    "coder_pass_values": [1, 2],
    "independence": "mutually-blind",
    "cross_pass_artifact_sharing": "forbidden",
    "both_passes_committed_before": "agreement",
    "adjudication_after": "agreement_freeze",
}

ORDER_OF_OPERATIONS = (
    "pass_1_committed",
    "pass_2_committed",
    "agreement_computed_and_frozen",
    "adjudication_recorded_separately",
)

REQUIRED_MARKERS = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}

REQUIRED_SECTIONS = (
    "1. Scope and frozen inputs",
    "2. Two independent passes",
    "3. Order of operations: agreement before adjudication",
    "4. Span-exact rule",
    "5. Abstention is a separate coder outcome",
    "6. Coder kit and the frozen submission form",
    "7. Agreement computation and honest denominators",
    "8. Adjudication is separate and never gold",
    "9. Store paths and pseudonyms",
    "10. Fail-closed diagnostics",
    "11. Lifecycle markers, non-claims and boundaries",
    "Machine-readable protocol contract",
)

REQUIRED_SUBSCHEMAS = (
    "coder_kit",
    "intake_record",
    "agreement_report",
    "disagreement_inventory",
    "adjudication_input",
    "adjudication_record",
    "pilot_receipt",
    "battery",
)
SUBSchema_IDS = {
    "coder_kit": "m207-s02-coder-kit/v1",
    "intake_record": "m207-s02-intake-record/v1",
    "agreement_report": "m207-s02-agreement-report/v1",
    "disagreement_inventory": "m207-s02-disagreement-inventory/v1",
    "adjudication_input": "m207-s02-adjudication-input/v1",
    "adjudication_record": "m207-s02-adjudication-record/v1",
    "pilot_receipt": "m207-s02-pilot-receipt/v1",
    "battery": "m207-s02-battery/v1",
}

SCHEMA_ROOT_KEYS = (
    "schema",
    "schema_version",
    "protocol",
    "codebook",
    "submission_schema_id",
    "submission_schema_reused_verbatim",
    "slot_space_source",
    "frozen_sources",
    "slot_space",
    "agreement_axes",
    "resolution_space",
    "vocabularies",
    "output_contract",
    "store_paths",
    "pass_protocol",
    "diagnostics",
    "schemas",
    "non_claims",
    "lifecycle",
)

CONTRACT_ROOT_KEYS = (
    "protocol_id",
    "schema_id",
    "codebook",
    "submission_schema_id",
    "submission_schema_reused_verbatim",
    "slot_space",
    "agreement_axes",
    "resolution_space",
    "output_contract",
    "store_paths",
    "pass_protocol",
    "order_of_operations",
    "rationale_max_chars",
    "diagnostics",
    "forbidden_keys",
    "forbidden_seed_keys",
    "required_sections",
    "non_claims",
    "lifecycle",
)

VOCABULARY_EXPECTATIONS: dict[str, Any] = {
    "provenance": [PROVENANCE_VALUE],
    "coder_pass": list(CODER_PASS_VALUES),
    "authority": ["none"],
    "suggestion_status": ["none-provided"],
    "output_type": ["AnnotationSuggestion"],
    "classification": ["not-authorized"],
    "promotion": ["none"],
    "threshold": None,
    "decision_values": list(DECISION_VALUES),
    "abstention_values": list(ABSTENTION_VALUES),
    "measurement_status": ["computed", "undefined"],
    "resolution_provenance": [PROVENANCE_VALUE],
    "adjudicator_provenance": [PROVENANCE_VALUE],
    "span_coordinate": ["half-open-byte-range-utf8-boundaries"],
}

KIT_FORBIDDEN_CASE_KEYS = ("fragment_text", "slot_values", "slots", "work_family")
BATTERY_FORBIDDEN_KEYS = ("duration_ms", "elapsed_ms", "generated_at", "wall_clock")

# The diagnostic vocabulary is closed: every S02 tool must speak exactly these
# names so a red run is machine-distinguishable from a green one.
EXPECTED_DIAGNOSTICS = (
    "HUMAN_PILOT_ABSENT",
    "MACHINERY_GREEN_HUMAN_ABSENT",
    "NO_ADJUDICATION_INPUT",
    "UNFILLED_SUBMISSION",
    "TEST_FIXTURE_IN_STORE",
    "PROVENANCE_NOT_HUMAN",
    "CODER_PASS_INVALID",
    "DUPLICATE_CODER_ID",
    "DUPLICATE_SUBMISSION_ID",
    "UNKNOWN_CASE_ID",
    "SUBMISSION_CONFLICT",
    "NINTH_SLOT",
    "SLOT_SET_DRIFT",
    "SUBMISSION_SCHEMA_DRIFT",
    "LEAK_FORBIDDEN_KEY",
    "ABSTENTION_COLLAPSE",
    "SPAN_BEYOND_EOF",
    "SPAN_NOT_UTF8_BOUNDARY",
    "SPAN_NOT_ORIGIN",
    "AUTHORITY_CLAIM",
    "MODEL_INVOKED",
    "AGREEMENT_UNDEFINED",
    "ONE_CODER_ONLY",
    "DENOMINATOR_MISMATCH",
    "PERFECT_AGREEMENT_UNCOMPUTED",
    "CLASSIFICATION_REQUESTED",
    "THRESHOLD_REQUESTED",
    "GOLD_CLAIM",
    "PROMOTION_CLAIM",
    "IS_GOLD_CLAIM",
    "ADJUDICATION_NOT_A_DISAGREEMENT",
    "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
    "RESOLUTION_OUT_OF_SPACE",
    "RESOLUTION_SPACE_DRIFT",
    "RATIONALE_NOT_BOUNDED",
    "SUPERSEDES_UNKNOWN",
    "UNRESOLVED_NONZERO",
    "WORK_FAMILY_DOMINANCE",
    "FRAGMENT_PIN_DRIFT",
    "KIT_TEXT_INLINED",
    "KIT_CROSS_PASS_INVARIANT",
    "FROZEN_SOURCE_DRIFT",
    "SEED_ENLARGED",
    "PROMPT_ISOLATION_VIOLATION",
    "UNSAFE_PATH",
    "BATTERY_STALE",
    "BATTERY_WALLCLOCK_FORBIDDEN",
    "MISSING_ARTIFACT",
    "MISSING_SCHEMA",
    "MISSING_SECTION",
    "MISSING_NON_CLAIM",
    "MISSING_LIFECYCLE_MARKER",
    "EMPTY_SUITE",
    "SUBCLI_FAILURE",
    "S01_REGRESSION_FAILED",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "DUPLICATE_JSON_KEY",
    "VOCABULARY_DRIFT",
    "ALTERNATIVE_DRIFT",
    "CASE_COUNT_OUT_OF_RANGE",
    "DIAGNOSTIC_TABLE_DRIFT",
)

EXPECTED_NON_CLAIMS = (
    "not a human pilot: S02 fabricates no coding and reports no agreement without "
    "two human submissions",
    "not gold: no S02 artifact, coded span or adjudicated resolution is a gold label",
    "not a promotion: classification stays not-authorized and promotion stays none",
    "not a threshold: no agreement threshold, pass/fail or accept/reject decision is introduced",
    "not per-aspect rates: span, slot, scope, binding and false-authority rates belong to S03",
    "not official-publication provenance (R070 stays open)",
    "not amendment provenance (R070 stays open)",
    "not LawRef / act-tree / clause segmentation",
    "not the N2-gate acceptance decision",
    "not legal interpretation",
    "not product authority: no coder kit, submission or adjudication drives the product runtime",
    "not a second product surface: S02 stays an offline Python harness under scripts/",
)

FORBIDDEN_KEYS_CANONICAL = ("label", "expected", "answer", "prediction", "gold", "capture")
FORBIDDEN_SEED_KEYS_CANONICAL = (
    "seed_span",
    "rule_seed_span",
    "rule_seed",
    "ds_span",
    "seed_slots",
)
FORBIDDEN_KEY_TOKENS = frozenset(
    {
        "label",
        "labels",
        "expected",
        "answer",
        "answers",
        "prediction",
        "predictions",
        "predicted",
        "gold",
        "golden",
        "capture",
        "captures",
    }
)
FORBIDDEN_EXACT_KEYS = frozenset(FORBIDDEN_SEED_KEYS_CANONICAL)
# Fields that name a forbidden claim but are themselves the *guard*: ``is_gold``
# is admitted where it is declared, and admitting it is only legal when it is
# pinned ``false``.  Claiming ``true`` is ``GOLD_CLAIM``, declaring it ``false``
# is the contract that forbids the claim.
GUARDED_FALSE_CLAIM_KEYS = frozenset({"is_gold"})
# The deny-lists themselves legitimately hold the forbidden names.
EXEMPT_KEY_PREFIX = "forbidden_"

_MISSING = object()

FENCE_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)
SLOT_ROW_RE = re.compile(r"^\|\s*`([a-z_]+)`\s*\|", re.MULTILINE)
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
TOKEN_SEPARATOR_RE = re.compile(r"[^A-Za-z0-9]+")

Failures = list[tuple[str, str]]


class GateError(Exception):
    """Fatal, named gate failure that stops the check immediately."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def resolve_artifact(
    root: Path,
    raw: str,
    label: str,
    *,
    suffix: str,
    prefix: str,
) -> Path:
    """Resolve a repository-relative artifact path, fail-closed on escapes."""
    if (
        not raw
        or "\x00" in raw
        or raw.startswith("/")
        or "\\" in raw
        or (len(raw) > 1 and raw[1] == ":")
    ):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must be a POSIX relative path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} may not escape the repository")
    if relative.suffix != suffix:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must have suffix {suffix}")
    if prefix and not relative.as_posix().startswith(prefix):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must live under {prefix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GateError("DUPLICATE_JSON_KEY", f"duplicate object key {key!r}")
        seen[key] = value
    return seen


def load_json_text(text: str, label: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not closed JSON: {exc}") from exc


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
    return load_json_text(text, label)


def key_tokens(key: str) -> list[str]:
    spaced = CAMEL_BOUNDARY_RE.sub("_", key)
    return [token for token in TOKEN_SEPARATOR_RE.split(spaced.lower()) if token]


def forbidden_key_hit(name: str, value: Any = _MISSING) -> str | None:
    """Return the forbidden-field class for a candidate key name, if any."""
    lowered = name.strip().lower()
    if lowered in GUARDED_FALSE_CLAIM_KEYS:
        if value is _MISSING or value is False:
            return None
        return "gold-claim"
    if set(key_tokens(name)) & FORBIDDEN_KEY_TOKENS:
        return "predicted-answer"
    if lowered in FORBIDDEN_EXACT_KEYS:
        return "rule-seed-span"
    return None


def scan_forbidden_keys(
    node: Any, pointer: str, failures: Failures, *, key_list: bool = False
) -> None:
    """Reject predicted-answer, gold-claim and rule-seed keys at any depth.

    Closed key sets are JSON arrays of key names, so a forbidden name arrives as
    an element of a ``*_keys`` list at least as often as it arrives as a dict
    key.  Both surfaces are checked; the ``forbidden_*`` deny-lists themselves
    are exempt because they are the deny-list and are pinned by value.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            hit = forbidden_key_hit(key, value)
            if hit == "gold-claim":
                _fail(failures, "GOLD_CLAIM", f"key {key!r} at {pointer or '$'} claims gold")
            elif hit:
                _fail(
                    failures,
                    "LEAK_FORBIDDEN_KEY",
                    f"key {key!r} at {pointer or '$'} mints a {hit} field",
                )
            nested_key_list = key.endswith("_keys") and not key.startswith(EXEMPT_KEY_PREFIX)
            scan_forbidden_keys(value, f"{pointer}.{key}", failures, key_list=nested_key_list)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            if key_list and isinstance(item, str):
                element_hit = forbidden_key_hit(item)
                if element_hit and element_hit != "gold-claim":
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"closed key {item!r} at {pointer}[{index}] mints a {element_hit} field",
                    )
            scan_forbidden_keys(item, f"{pointer}[{index}]", failures)


# Claim-bearing scalar keys: the value decides whether the surface is honest.
CLAIM_VALUE_RULES: tuple[tuple[str, Any, str], ...] = (
    ("authority", lambda value: value == "none", "AUTHORITY_CLAIM"),
    ("suggestion_status", lambda value: value == "none-provided", "AUTHORITY_CLAIM"),
    ("model_invoked", lambda value: value is False, "MODEL_INVOKED"),
    ("classification", lambda value: value == "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("promotion", lambda value: value == "none", "PROMOTION_CLAIM"),
)


def scan_forbidden_values(node: Any, pointer: str, failures: Failures) -> None:
    """Reject authority, model, classification, threshold and promotion claims.

    Scalars only: a *list* of legal values (``$.vocabularies.authority``) states
    the closed set, while a scalar states the choice.  Only a scalar can claim.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                scan_forbidden_values(value, f"{pointer}.{key}", failures)
                continue
            for name, is_legal, diagnostic in CLAIM_VALUE_RULES:
                if key == name and not is_legal(value):
                    _fail(
                        failures,
                        diagnostic,
                        f"{pointer}.{key}={value!r} claims what this slice forbids",
                    )
            if key == "threshold" and value is not None:
                _fail(
                    failures,
                    "THRESHOLD_REQUESTED",
                    f"{pointer}.threshold={value!r} introduces a threshold",
                )
            if key == "is_gold" and value is not False:
                _fail(failures, "GOLD_CLAIM", f"{pointer}.is_gold={value!r} claims gold")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_forbidden_values(item, f"{pointer}[{index}]", failures)


def _close_keys(label: str, keys: Any, failures: Failures) -> tuple[str, ...]:
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) for k in keys):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} must be a non-empty list of string keys")
        return ()
    if len(set(keys)) != len(keys):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} carries duplicate keys")
    return tuple(keys)


def _check_closed_pair(label: str, sub: dict[str, Any], failures: Failures) -> tuple[str, ...]:
    closed = _close_keys(f"{label}.closed_keys", sub.get("closed_keys"), failures)
    required = _close_keys(f"{label}.required_keys", sub.get("required_keys"), failures)
    for key in required:
        if key not in closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"{label} required key {key!r} is not in its closed key set",
            )
    return closed


def _check_slot_space(label: str, declared: Any, failures: Failures) -> None:
    keys = _close_keys(f"{label}.closed_keys", declared, failures)
    if not keys:
        return
    if len(keys) > len(M199_SLOT_SPACE):
        _fail(
            failures,
            "NINTH_SLOT",
            f"{label} declares {len(keys)} slots; the M199 §5 space is closed at "
            f"{len(M199_SLOT_SPACE)} + {M199_BINARY_OUTCOME}",
        )
    elif keys != M199_SLOT_SPACE:
        _fail(
            failures, "SLOT_SET_DRIFT", f"{label}={list(keys)} != M199 §5 {list(M199_SLOT_SPACE)}"
        )


def scan_slot_lists(node: Any, pointer: str, failures: Failures) -> None:
    """Reject a ninth slot in *any* key list that already holds slot names.

    A closed key list that carries ``marker_chain`` is a slot list wherever it
    appears, so it must equal the M199 section-5 space exactly.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key.endswith("_keys") and isinstance(value, list) and "marker_chain" in value:
                _check_slot_space(f"{pointer}.{key}".lstrip("$."), value, failures)
            scan_slot_lists(value, f"{pointer}.{key}", failures)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_slot_lists(item, f"{pointer}[{index}]", failures)


def _check_non_claims(label: str, claims: Any, failures: Failures) -> None:
    if not isinstance(claims, list) or claims != list(EXPECTED_NON_CLAIMS):
        _fail(
            failures,
            "MISSING_NON_CLAIM",
            f"{label} must equal the frozen non-claim list ({len(EXPECTED_NON_CLAIMS)} entries)",
        )


def _check_lifecycle(label: str, markers: Any, failures: Failures) -> None:
    if markers != REQUIRED_MARKERS:
        _fail(
            failures,
            "MISSING_LIFECYCLE_MARKER",
            f"{label}={markers!r} != required lifecycle markers {REQUIRED_MARKERS!r}",
        )


def check_submission_form(schema: Any, failures: Failures) -> None:
    """The S01 coding-submission form must not be redefined under S02."""
    if not isinstance(schema, dict):
        return
    if schema.get("submission_schema_id") != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"$.submission_schema_id={schema.get('submission_schema_id')!r} != "
            f"{SUBMISSION_SCHEMA_ID!r} (D475: reused verbatim)",
        )
    if schema.get("submission_schema_reused_verbatim") is not SUBMISSION_SCHEMA_REUSED:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            "$.submission_schema_reused_verbatim must be exactly true",
        )
    subschemas = schema.get("schemas")
    if isinstance(subschemas, dict) and "coding_submission" in subschemas:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            "$.schemas.coding_submission redefines the frozen S01 submission form",
        )


def check_store_paths(schema: Any, failures: Failures) -> None:
    store = schema.get("store_paths") if isinstance(schema, dict) else None
    if not isinstance(store, dict):
        _fail(failures, "UNSAFE_PATH", "$.store_paths must be an object")
        return
    if store.get("store_prefix_lock") is not True:
        _fail(failures, "UNSAFE_PATH", "$.store_paths.store_prefix_lock must be true")
    prefix = store.get("allowed_prefix")
    if prefix != ANNOTATION_PREFIX:
        _fail(
            failures,
            "UNSAFE_PATH",
            f"$.store_paths.allowed_prefix={prefix!r} != {ANNOTATION_PREFIX!r}",
        )
    for key in ("submissions", "adjudications"):
        value = store.get(key)
        if value != STORE_PATHS[key]:
            _fail(
                failures,
                "UNSAFE_PATH",
                f"$.store_paths.{key}={value!r} != D480 path {STORE_PATHS[key]!r}",
            )
        elif not str(value).startswith(ANNOTATION_PREFIX):
            _fail(
                failures,
                "UNSAFE_PATH",
                f"$.store_paths.{key}={value!r} escapes the locked prefix",
            )
    if store.get("evidence") != STORE_PATHS["evidence"]:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"$.store_paths.evidence={store.get('evidence')!r} != {STORE_PATHS['evidence']!r}",
        )
    if store.get("prefix_diagnostic") != STORE_PATHS["prefix_diagnostic"]:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.store_paths.prefix_diagnostic must name the UNSAFE_PATH diagnostic",
        )
    if set(store) != set(STORE_PATHS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"$.store_paths keys differ from {sorted(STORE_PATHS)}",
        )


def check_vocabularies(schema: Any, failures: Failures) -> None:
    vocabularies = schema.get("vocabularies") if isinstance(schema, dict) else None
    if not isinstance(vocabularies, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.vocabularies must be an object")
        return
    if set(vocabularies) != set(VOCABULARY_EXPECTATIONS):
        _fail(
            failures,
            "VOCABULARY_DRIFT",
            "$.vocabularies keys differ: extra="
            f"{sorted(set(vocabularies) - set(VOCABULARY_EXPECTATIONS))} missing="
            f"{sorted(set(VOCABULARY_EXPECTATIONS) - set(vocabularies))}",
        )
    for name, expected in VOCABULARY_EXPECTATIONS.items():
        if vocabularies.get(name) != expected:
            _fail(
                failures,
                "VOCABULARY_DRIFT",
                f"$.vocabularies.{name}={vocabularies.get(name)!r} != {expected!r}",
            )
    abstention = vocabularies.get("abstention_values")
    if isinstance(abstention, list) and set(abstention) & set(DECISION_VALUES):
        _fail(
            failures,
            "ABSTENTION_COLLAPSE",
            "abstention values may never reuse reference-decision values",
        )


def check_output_contract(schema: Any, failures: Failures) -> None:
    contract = schema.get("output_contract") if isinstance(schema, dict) else None
    if not isinstance(contract, dict):
        _fail(failures, "AUTHORITY_CLAIM", "$.output_contract must be an object")
        return
    if contract.get("output_type") != OUTPUT_CONTRACT["output_type"]:
        _fail(
            failures,
            "AUTHORITY_CLAIM",
            "$.output_contract.output_type must be AnnotationSuggestion",
        )
    if contract.get("authority") != "none":
        _fail(failures, "AUTHORITY_CLAIM", "$.output_contract.authority must be 'none'")
    if contract.get("suggestion_status") != "none-provided":
        _fail(
            failures,
            "AUTHORITY_CLAIM",
            "$.output_contract.suggestion_status must be 'none-provided'",
        )
    if contract.get("model_invoked") is not False:
        _fail(failures, "MODEL_INVOKED", "$.output_contract.model_invoked must be false")
    if contract.get("classification") != "not-authorized":
        _fail(
            failures,
            "CLASSIFICATION_REQUESTED",
            "$.output_contract.classification must be 'not-authorized'",
        )
    if contract.get("promotion") != "none":
        _fail(failures, "PROMOTION_CLAIM", "$.output_contract.promotion must be 'none'")
    if contract.get("threshold") is not None:
        _fail(failures, "THRESHOLD_REQUESTED", "$.output_contract.threshold must be null")


def check_axes_and_resolution(schema: Any, failures: Failures) -> None:
    axes = schema.get("agreement_axes") if isinstance(schema, dict) else None
    if axes != list(AGREEMENT_AXES):
        _fail(
            failures,
            "VOCABULARY_DRIFT",
            f"$.agreement_axes={axes!r} != {list(AGREEMENT_AXES)!r}",
        )
    resolution = schema.get("resolution_space") if isinstance(schema, dict) else None
    if resolution != RESOLUTION_SPACE:
        _fail(
            failures,
            "RESOLUTION_SPACE_DRIFT",
            "$.resolution_space must equal the closed per-axis codebook decision space",
        )
        return
    if isinstance(axes, list) and set(resolution["by_axis"]) != set(axes):
        _fail(
            failures,
            "RESOLUTION_SPACE_DRIFT",
            "resolution_space.by_axis must cover exactly the agreement axes",
        )


def check_sub_schemas(schema: Any, failures: Failures) -> None:
    subschemas = schema.get("schemas") if isinstance(schema, dict) else None
    if not isinstance(subschemas, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.schemas must be an object")
        return
    for name in REQUIRED_SUBSCHEMAS:
        if name not in subschemas:
            _fail(failures, "MISSING_SCHEMA", f"$.schemas.{name} is absent")
    if set(subschemas) != set(REQUIRED_SUBSCHEMAS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.schemas keys differ: extra="
            f"{sorted(set(subschemas) - set(REQUIRED_SUBSCHEMAS))} missing="
            f"{sorted(set(REQUIRED_SUBSCHEMAS) - set(subschemas))}",
        )
        return
    for name, sub in subschemas.items():
        if not isinstance(sub, dict):
            _fail(failures, "SCHEMA_KEY_DRIFT", f"$.schemas.{name} must be an object")
            continue
        if sub.get("schema_id") != SUBSchema_IDS[name]:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"$.schemas.{name}.schema_id={sub.get('schema_id')!r} != {SUBSchema_IDS[name]!r}",
            )
        _check_closed_pair(f"$.schemas.{name}", sub, failures)
    _check_coder_kit(subschemas.get("coder_kit"), failures)
    _check_intake_record(subschemas.get("intake_record"), failures)
    _check_agreement_report(subschemas.get("agreement_report"), failures)
    _check_disagreement_inventory(subschemas.get("disagreement_inventory"), failures)
    _check_adjudication_input(subschemas.get("adjudication_input"), failures)
    _check_adjudication_record(subschemas.get("adjudication_record"), failures)
    _check_pilot_receipt(subschemas.get("pilot_receipt"), failures)
    _check_battery(subschemas.get("battery"), failures)


def _check_coder_kit(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    case_closed = _close_keys(
        "$.schemas.coder_kit.case_closed_keys", sub.get("case_closed_keys"), failures
    )
    _close_keys("$.schemas.coder_kit.case_required_keys", sub.get("case_required_keys"), failures)
    _close_keys(
        "$.schemas.coder_kit.template_closed_keys", sub.get("template_closed_keys"), failures
    )
    forbidden = sub.get("forbidden_case_keys")
    if forbidden != list(KIT_FORBIDDEN_CASE_KEYS):
        _fail(
            failures,
            "KIT_TEXT_INLINED",
            f"$.schemas.coder_kit.forbidden_case_keys={forbidden!r} != "
            f"{list(KIT_FORBIDDEN_CASE_KEYS)!r}",
        )
    for banned in KIT_FORBIDDEN_CASE_KEYS:
        if banned in case_closed:
            _fail(
                failures,
                "KIT_TEXT_INLINED",
                f"coder kit case key {banned!r} would inline text, slots or work_family",
            )
    for slot in M199_SLOT_SPACE:
        if slot in case_closed:
            _fail(
                failures,
                "NINTH_SLOT",
                f"coder kit case key {slot!r} would ship a slot",
            )
    if sub.get("text_inlined") is not False:
        _fail(failures, "KIT_TEXT_INLINED", "$.schemas.coder_kit.text_inlined must be false")
    if sub.get("case_count") != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"$.schemas.coder_kit.case_count={sub.get('case_count')!r} != {CASE_COUNT}",
        )
    cap = sub.get("work_family_cap")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap != WORK_FAMILY_CAP:
        _fail(
            failures,
            "WORK_FAMILY_DOMINANCE",
            f"$.schemas.coder_kit.work_family_cap={cap!r} != {WORK_FAMILY_CAP}",
        )
    if sub.get("kits") != len(CODER_PASS_VALUES):
        _fail(
            failures,
            "KIT_CROSS_PASS_INVARIANT",
            f"$.schemas.coder_kit.kits={sub.get('kits')!r} != {len(CODER_PASS_VALUES)}",
        )


def _check_intake_record(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    _close_keys(
        "$.schemas.intake_record.submission_closed_keys",
        sub.get("submission_closed_keys"),
        failures,
    )
    _close_keys(
        "$.schemas.intake_record.submission_required_keys",
        sub.get("submission_required_keys"),
        failures,
    )
    if sub.get("submission_schema_id") != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            "$.schemas.intake_record.submission_schema_id must be the frozen S01 id",
        )
    if sub.get("store_read_only") is not True:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.schemas.intake_record.store_read_only must be true (D474/D476)",
        )


def _check_agreement_report(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    _close_keys(
        "$.schemas.agreement_report.axis_closed_keys", sub.get("axis_closed_keys"), failures
    )
    _close_keys(
        "$.schemas.agreement_report.submission_ref_closed_keys",
        sub.get("submission_ref_closed_keys"),
        failures,
    )
    if sub.get("units_total") != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"$.schemas.agreement_report.units_total={sub.get('units_total')!r} != {CASE_COUNT}",
        )
    cap = sub.get("work_family_cap")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap != WORK_FAMILY_CAP:
        _fail(
            failures,
            "WORK_FAMILY_DOMINANCE",
            f"$.schemas.agreement_report.work_family_cap={cap!r} != {WORK_FAMILY_CAP}",
        )
    if sub.get("pre_adjudication") is not True:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.schemas.agreement_report.pre_adjudication must be true",
        )
    closed = sub.get("closed_keys") or []
    for key in ("alpha", "threshold", "classification", "promotion"):
        if key not in closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"agreement report must declare {key!r} explicitly (null/none, never absent)",
            )


def _check_disagreement_inventory(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    _close_keys(
        "$.schemas.disagreement_inventory.entry_closed_keys", sub.get("entry_closed_keys"), failures
    )
    _close_keys(
        "$.schemas.disagreement_inventory.entry_required_keys",
        sub.get("entry_required_keys"),
        failures,
    )
    if sub.get("pre_adjudication") is not True:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.schemas.disagreement_inventory.pre_adjudication must be true",
        )


def _check_adjudication_input(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    closed = sub.get("closed_keys") or []
    for key in ("resolution", "provenance", "adjudicator_id", "supersedes"):
        if key not in closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"adjudication input must declare {key!r}",
            )
    if sub.get("adjudicator_provenance") != PROVENANCE_VALUE:
        _fail(
            failures,
            "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
            "$.schemas.adjudication_input.adjudicator_provenance must be human-reviewed",
        )
    limit = sub.get("rationale_max_chars")
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 0 < limit <= RATIONALE_MAX_CHARS_LIMIT
    ):
        _fail(
            failures,
            "RATIONALE_NOT_BOUNDED",
            f"$.schemas.adjudication_input.rationale_max_chars={limit!r} must be a bounded "
            f"positive integer <= {RATIONALE_MAX_CHARS_LIMIT}",
        )
    if sub.get("rationale_single_line") is not True:
        _fail(
            failures,
            "RATIONALE_NOT_BOUNDED",
            "$.schemas.adjudication_input.rationale_single_line must be true",
        )


def _check_adjudication_record(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    entry_closed = _close_keys(
        "$.schemas.adjudication_record.entry_closed_keys", sub.get("entry_closed_keys"), failures
    )
    _close_keys(
        "$.schemas.adjudication_record.entry_required_keys",
        sub.get("entry_required_keys"),
        failures,
    )
    closed = sub.get("closed_keys") or []
    if "pre_adjudication_agreement_sha256" not in closed:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "adjudication record must pin pre_adjudication_agreement_sha256",
        )
    if "is_gold" not in entry_closed:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "adjudication entry must declare the is_gold guard explicitly",
        )
    if sub.get("append_only") is not True:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.schemas.adjudication_record.append_only must be true",
        )
    if sub.get("is_gold") is not False:
        _fail(failures, "GOLD_CLAIM", "$.schemas.adjudication_record.is_gold must be false")
    if sub.get("promotion") != "none":
        _fail(
            failures,
            "PROMOTION_CLAIM",
            "$.schemas.adjudication_record.promotion must be 'none'",
        )
    if sub.get("adjudicator_provenance") != PROVENANCE_VALUE:
        _fail(
            failures,
            "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
            "$.schemas.adjudication_record.adjudicator_provenance must be human-reviewed",
        )


def _check_pilot_receipt(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    if sub.get("case_count") != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"$.schemas.pilot_receipt.case_count={sub.get('case_count')!r} != {CASE_COUNT}",
        )
    if sub.get("coder_count") != len(CODER_PASS_VALUES):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"$.schemas.pilot_receipt.coder_count={sub.get('coder_count')!r} != "
            f"{len(CODER_PASS_VALUES)}",
        )
    minimum = sub.get("adjudicator_count_min")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.schemas.pilot_receipt.adjudicator_count_min must be >= 1",
        )
    if sub.get("promotion") != "none":
        _fail(failures, "PROMOTION_CLAIM", "$.schemas.pilot_receipt.promotion must be 'none'")


def _check_battery(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    check_closed = _close_keys(
        "$.schemas.battery.check_closed_keys", sub.get("check_closed_keys"), failures
    )
    pins_closed = _close_keys(
        "$.schemas.battery.pins_closed_keys", sub.get("pins_closed_keys"), failures
    )
    _close_keys("$.schemas.battery.check_required_keys", sub.get("check_required_keys"), failures)
    forbidden = sub.get("forbidden_battery_keys")
    if forbidden != list(BATTERY_FORBIDDEN_KEYS):
        _fail(
            failures,
            "BATTERY_WALLCLOCK_FORBIDDEN",
            f"$.schemas.battery.forbidden_battery_keys={forbidden!r} != "
            f"{list(BATTERY_FORBIDDEN_KEYS)!r}",
        )
    for banned in BATTERY_FORBIDDEN_KEYS:
        if banned in check_closed or banned in pins_closed:
            _fail(
                failures,
                "BATTERY_WALLCLOCK_FORBIDDEN",
                f"battery key {banned!r} would make the battery non-reproducible (D473)",
            )
    if sub.get("model_invoked") is not False:
        _fail(failures, "MODEL_INVOKED", "$.schemas.battery.model_invoked must be false")


def check_schema_document(schema: Any, failures: Failures) -> None:
    if not isinstance(schema, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "schemas document must be a JSON object")
        return
    scan_forbidden_keys(schema, "$", failures)
    scan_forbidden_values(schema, "$", failures)
    scan_slot_lists(schema, "$", failures)
    if set(schema) != set(SCHEMA_ROOT_KEYS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$ keys differ: extra="
            f"{sorted(set(schema) - set(SCHEMA_ROOT_KEYS))} missing="
            f"{sorted(set(SCHEMA_ROOT_KEYS) - set(schema))}",
        )
    if schema.get("schema") != SCHEMA_ID:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"$.schema={schema.get('schema')!r} != {SCHEMA_ID!r}")
    if schema.get("schema_version") != SCHEMA_VERSION:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"$.schema_version must be {SCHEMA_VERSION}")
    if schema.get("protocol") != PROTOCOL_REL:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"$.protocol={schema.get('protocol')!r} != {PROTOCOL_REL!r}",
        )
    if schema.get("codebook") != S01_CODEBOOK_REL:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"$.codebook={schema.get('codebook')!r} must be the frozen S01 codebook "
            f"{S01_CODEBOOK_REL!r}",
        )
    if schema.get("slot_space_source") != SLOT_SPACE_SOURCE:
        _fail(
            failures,
            "SLOT_SET_DRIFT",
            f"$.slot_space_source={schema.get('slot_space_source')!r} != {SLOT_SPACE_SOURCE!r}",
        )
    if schema.get("frozen_sources") != EXPECTED_FROZEN_SOURCES:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            "$.frozen_sources must pin exactly the four frozen inputs with their digests",
        )

    slot_space = schema.get("slot_space")
    if not isinstance(slot_space, dict):
        _fail(failures, "SLOT_SET_DRIFT", "$.slot_space must be an object")
    else:
        _check_slot_space("$.slot_space", slot_space.get("closed_keys"), failures)
        if slot_space.get("binary_outcome") != {"key": M199_BINARY_OUTCOME, "type": "boolean"}:
            _fail(
                failures,
                "SLOT_SET_DRIFT",
                "$.slot_space.binary_outcome must declare the boolean not_a_reference outcome",
            )
        expected_count = len(M199_SLOT_SPACE) + 1
        if slot_space.get("closed_key_count") != expected_count:
            _fail(
                failures,
                "SLOT_SET_DRIFT",
                f"$.slot_space.closed_key_count must be {expected_count}",
            )

    check_submission_form(schema, failures)
    check_axes_and_resolution(schema, failures)
    check_vocabularies(schema, failures)
    check_output_contract(schema, failures)
    check_store_paths(schema, failures)

    if schema.get("pass_protocol") != PASS_PROTOCOL:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.pass_protocol must keep the mutually-blind two-pass contract",
        )
    if schema.get("diagnostics") != list(EXPECTED_DIAGNOSTICS):
        _fail(
            failures,
            "DIAGNOSTIC_TABLE_DRIFT",
            "$.diagnostics must equal the closed S02 diagnostic vocabulary",
        )
    _check_non_claims("$.non_claims", schema.get("non_claims"), failures)
    _check_lifecycle("$.lifecycle", schema.get("lifecycle"), failures)
    check_sub_schemas(schema, failures)


CONTRACT_COMPARISONS: tuple[tuple[str, str], ...] = (
    ("submission_schema_id", "SUBMISSION_SCHEMA_DRIFT"),
    ("submission_schema_reused_verbatim", "SUBMISSION_SCHEMA_DRIFT"),
    ("slot_space", "SLOT_SET_DRIFT"),
    ("agreement_axes", "VOCABULARY_DRIFT"),
    ("resolution_space", "RESOLUTION_SPACE_DRIFT"),
    ("output_contract", "AUTHORITY_CLAIM"),
    ("store_paths", "UNSAFE_PATH"),
    ("pass_protocol", "SCHEMA_KEY_DRIFT"),
    ("diagnostics", "DIAGNOSTIC_TABLE_DRIFT"),
    ("non_claims", "MISSING_NON_CLAIM"),
    ("lifecycle", "MISSING_LIFECYCLE_MARKER"),
)


def check_contract(contract: Any, schema: Any, headings: list[str], failures: Failures) -> None:
    if not isinstance(contract, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "protocol contract must be a JSON object")
        return
    scan_forbidden_keys(contract, "contract$", failures)
    scan_forbidden_values(contract, "contract$", failures)
    if set(contract) != set(CONTRACT_ROOT_KEYS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "contract keys differ: extra="
            f"{sorted(set(contract) - set(CONTRACT_ROOT_KEYS))} missing="
            f"{sorted(set(CONTRACT_ROOT_KEYS) - set(contract))}",
        )
    if contract.get("protocol_id") != PROTOCOL_ID:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"contract.protocol_id={contract.get('protocol_id')!r} != {PROTOCOL_ID!r}",
        )
    if contract.get("schema_id") != SCHEMA_ID:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"contract.schema_id={contract.get('schema_id')!r} != {SCHEMA_ID!r}",
        )
    if contract.get("codebook") != S01_CODEBOOK_REL:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            "contract.codebook must be the frozen S01 codebook",
        )
    if not isinstance(schema, dict):
        return
    for key, diagnostic in CONTRACT_COMPARISONS:
        if contract.get(key) != schema.get(key):
            _fail(
                failures,
                diagnostic,
                f"contract.{key} differs from the schemas document (edit both or neither)",
            )
    if contract.get("order_of_operations") != list(ORDER_OF_OPERATIONS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "contract.order_of_operations must keep agreement before adjudication",
        )
    limit = contract.get("rationale_max_chars")
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 0 < limit <= RATIONALE_MAX_CHARS_LIMIT
        or limit != RATIONALE_MAX_CHARS
    ):
        _fail(
            failures,
            "RATIONALE_NOT_BOUNDED",
            f"contract.rationale_max_chars={limit!r} must be {RATIONALE_MAX_CHARS}",
        )
    if contract.get("forbidden_keys") != list(FORBIDDEN_KEYS_CANONICAL):
        _fail(failures, "LEAK_FORBIDDEN_KEY", "contract.forbidden_keys must be the canonical six")
    if contract.get("forbidden_seed_keys") != list(FORBIDDEN_SEED_KEYS_CANONICAL):
        _fail(
            failures,
            "LEAK_FORBIDDEN_KEY",
            "contract.forbidden_seed_keys must be the canonical set",
        )
    if contract.get("required_sections") != list(REQUIRED_SECTIONS):
        _fail(
            failures,
            "MISSING_SECTION",
            "contract.required_sections must equal the frozen section list",
        )
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            _fail(failures, "MISSING_SECTION", f"protocol heading '## {section}' is absent")
    _check_non_claims("contract.non_claims", contract.get("non_claims"), failures)
    _check_lifecycle("contract.lifecycle", contract.get("lifecycle"), failures)


def parse_protocol_slots(text: str) -> tuple[tuple[str, ...], str | None, int]:
    """Return the frozen M199 section-5 slot space as declared by the protocol."""
    if M199_SLOT_SECTION not in text:
        return (), None, 0
    section = text.split(M199_SLOT_SECTION, 1)[1].split("\n## 6.", 1)[0]
    names = SLOT_ROW_RE.findall(section)
    outcome = names[-1] if names and names[-1] == M199_BINARY_OUTCOME else None
    slots = tuple(names[:-1]) if outcome else tuple(names)
    return slots, outcome, len(names)


def protocol_headings(text: str) -> list[str]:
    return [match.group(1).strip() for match in HEADING_RE.finditer(text)]


def extract_contract(text: str, heading: str, label: str) -> dict[str, Any]:
    index = text.find(f"## {heading}")
    if index < 0:
        raise GateError("MISSING_SECTION", f"{label} section '## {heading}' is absent")
    block = FENCE_RE.search(text[index:])
    if block is None:
        raise GateError(
            "MISSING_SECTION", f"{label} section '## {heading}' has no fenced json block"
        )
    contract = load_json_text(block.group(1), label)
    if not isinstance(contract, dict):
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} must be a JSON object")
    return contract


def collect_failures(root: Path, protocol_rel: str, schemas_rel: str) -> Failures:
    """Run every read-only check and return the named findings."""
    failures: Failures = []
    try:
        protocol_path = resolve_artifact(
            root, protocol_rel, "protocol", suffix=".md", prefix=ANNOTATION_PREFIX
        )
        schemas_path = resolve_artifact(
            root, schemas_rel, "schemas", suffix=".json", prefix=ANNOTATION_PREFIX
        )
        frozen_paths: dict[str, Path] = {}
        for key, (rel, _) in FROZEN_SOURCES.items():
            frozen_paths[key] = resolve_artifact(
                root,
                rel,
                f"frozen source {key}",
                suffix=PurePosixPath(rel).suffix,
                prefix="prd/",
            )
    except GateError as exc:
        return [(exc.diagnostic, exc.detail)]

    protocol_slots: tuple[str, ...] = ()
    frozen_hashes: dict[str, str] = {}
    for key, path in frozen_paths.items():
        expected = FROZEN_SOURCES[key][1]
        if not path.is_file():
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"frozen source {key} missing at {FROZEN_SOURCES[key][0]}",
            )
            continue
        digest = sha256_file(path)
        frozen_hashes[key] = digest
        if digest != expected:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"frozen source {key} sha256 {digest} != pinned {expected}",
            )
    if "m199_protocol" in frozen_hashes and frozen_hashes["m199_protocol"] == M199_PROTOCOL_SHA256:
        text = frozen_paths["m199_protocol"].read_text(encoding="utf-8")
        slots, outcome, row_count = parse_protocol_slots(text)
        if row_count != SLOT_KEY_COUNT or len(slots) != len(M199_SLOT_SPACE):
            _fail(
                failures,
                "SLOT_SET_DRIFT",
                f"M199 §5 table parsed {row_count} rows / {len(slots)} slots "
                f"(expected {SLOT_KEY_COUNT} / {len(M199_SLOT_SPACE)})",
            )
        elif outcome != M199_BINARY_OUTCOME:
            _fail(
                failures,
                "SLOT_SET_DRIFT",
                f"M199 §5 binary outcome {outcome!r} != {M199_BINARY_OUTCOME!r}",
            )
        else:
            protocol_slots = slots

    headings: list[str] = []
    contract: dict[str, Any] | None = None
    if not protocol_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"S02 protocol missing at {protocol_rel}")
    else:
        protocol_text = protocol_path.read_text(encoding="utf-8")
        headings = protocol_headings(protocol_text)
        if BOUNDED_TAG not in protocol_text:
            _fail(
                failures,
                "MISSING_SECTION",
                f"S02 protocol must carry the {BOUNDED_TAG} lifecycle tag",
            )
        try:
            contract = extract_contract(protocol_text, CONTRACT_HEADING, "S02 protocol contract")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    schema: Any = None
    if not schemas_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"S02 schemas missing at {schemas_rel}")
    else:
        try:
            schema = load_json(schemas_path, "S02 schemas document")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    if schema is not None:
        check_schema_document(schema, failures)
    if contract is not None:
        check_contract(contract, schema, headings, failures)
    cross_check_frozen_artifacts(
        frozen_paths, frozen_hashes, schema, contract, protocol_slots, failures
    )
    return failures


def check_resolution_against_codebook(
    schema: Any, codebook_contract: Any, failures: Failures
) -> None:
    """Derive the closed resolution space from the frozen codebook decision poles.

    Adjudication may only resolve an axis to a value the frozen codebook already
    names.  Deriving the comparison from the codebook contract, rather than from
    a second hand-written copy of the same list, keeps "no new decision values"
    true by construction: if the codebook poles ever move, the S02 space must
    follow them exactly and anything else is ``ALTERNATIVE_DRIFT``.
    """
    if not isinstance(schema, dict) or not isinstance(codebook_contract, dict):
        return
    by_axis = schema.get("resolution_space", {}).get("by_axis")
    if not isinstance(by_axis, dict):
        return
    alternatives = codebook_contract.get("alternative_axes")
    if not isinstance(alternatives, list):
        _fail(
            failures,
            "ALTERNATIVE_DRIFT",
            "S01 codebook contract carries no alternative_axes to derive from",
        )
        return
    poles: dict[str, list[Any]] = {}
    for row in alternatives:
        if isinstance(row, dict) and isinstance(row.get("axis"), str):
            poles[row["axis"]] = list(row.get("values") or [])
    reference = poles.get("reference_decision")
    if reference is not None and by_axis.get("reference_decision") != reference:
        _fail(
            failures,
            "ALTERNATIVE_DRIFT",
            f"resolution space for reference_decision {by_axis.get('reference_decision')!r} "
            f"!= codebook poles {reference!r}",
        )
    slot_presence = poles.get("slot_presence")
    if slot_presence is not None:
        for name in M199_SLOT_SPACE:
            axis = f"slot_{name}"
            if by_axis.get(axis) != slot_presence:
                _fail(
                    failures,
                    "ALTERNATIVE_DRIFT",
                    f"resolution space for {axis} {by_axis.get(axis)!r} != codebook "
                    f"slot_presence poles {slot_presence!r}",
                )
    abstention = codebook_contract.get("abstention")
    if isinstance(abstention, dict):
        values = list(abstention.get("values") or [])
        if values and by_axis.get("abstention") != values:
            _fail(
                failures,
                "ALTERNATIVE_DRIFT",
                f"resolution space for abstention {by_axis.get('abstention')!r} != codebook "
                f"abstention vocabulary {values!r}",
            )


def cross_check_frozen_artifacts(
    frozen_paths: dict[str, Path],
    frozen_hashes: dict[str, str],
    schema: Any,
    contract: Any,
    protocol_slots: tuple[str, ...],
    failures: Failures,
) -> None:
    """Bind the S02 declarations to the actual frozen S01 artifacts.

    The sha256 pins already prove the frozen bytes; this second, structural pass
    states the contract they carry: the slot space, the reused submission schema
    id, and the M199 section-5 table.
    """
    if not isinstance(schema, dict):
        return
    s01_slot_space: tuple[str, ...] = ()
    s01_submission_id: str | None = None
    s01_schemas_path = frozen_paths.get("m207_s01_schemas")
    if (
        s01_schemas_path is not None
        and frozen_hashes.get("m207_s01_schemas") == (FROZEN_SOURCES["m207_s01_schemas"][1])
    ):
        try:
            s01 = json.loads(
                s01_schemas_path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (OSError, GateError, json.JSONDecodeError):
            s01 = None
        if isinstance(s01, dict):
            s01_slot_space = tuple(s01.get("slot_space", {}).get("closed_keys") or ())
            submission = s01.get("schemas", {}).get("coding_submission", {})
            if isinstance(submission, dict):
                s01_submission_id = submission.get("schema_id")
    s01_codebook_path = frozen_paths.get("m207_s01_codebook")
    codebook_slot_space: tuple[str, ...] = ()
    if s01_codebook_path is not None and s01_codebook_path.is_file():
        try:
            codebook_contract = extract_contract(
                s01_codebook_path.read_text(encoding="utf-8"),
                "Machine-readable codebook contract",
                "S01 codebook contract",
            )
        except GateError:
            codebook_contract = None
        if isinstance(codebook_contract, dict):
            codebook_slot_space = tuple(
                codebook_contract.get("slot_space", {}).get("closed_keys") or ()
            )
            check_resolution_against_codebook(schema, codebook_contract, failures)

    declared = tuple(schema.get("slot_space", {}).get("closed_keys") or ())
    if not declared:
        return
    for label, other in (
        ("S01 schemas", s01_slot_space),
        ("S01 codebook contract", codebook_slot_space),
        ("M199 §5", protocol_slots),
    ):
        if other and declared != other:
            _fail(
                failures,
                "SLOT_SET_DRIFT",
                f"S02 slot space {list(declared)} != {label} {list(other)}",
            )
    if not declared == M199_SLOT_SPACE:
        _fail(
            failures,
            "SLOT_SET_DRIFT",
            f"S02 slot space {list(declared)} != M199 §5 {list(M199_SLOT_SPACE)}",
        )
    if s01_submission_id is not None and schema.get("submission_schema_id") != s01_submission_id:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"S02 submission_schema_id={schema.get('submission_schema_id')!r} != frozen S01 "
            f"{s01_submission_id!r}",
        )
    if isinstance(contract, dict) and contract.get("submission_schema_id") != schema.get(
        "submission_schema_id"
    ):
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            "protocol contract and schemas disagree on the submission schema id",
        )


def report(failures: Failures, marker: str) -> int:
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
    print(
        f"FAIL M207_S02_SCHEMAS_GATE: {len(seen)} finding(s); the frozen S02 contract "
        "is not satisfied",
        file=sys.stderr,
    )
    return 1


# --------------------------------------------------------------------------- #
# Negative proof: every hostile mutation must produce its named diagnostic.
# --------------------------------------------------------------------------- #

Mutator = Callable[[dict[str, Any], dict[str, Any]], None]


def _mutate_slot_ninth(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["slot_space"]["closed_keys"].append("extra_slot")


def _mutate_label_key(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["intake_record"]["submission_closed_keys"].append("label")


def _mutate_seed_key(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["coder_kit"]["case_closed_keys"].append("seed_span")


def _mutate_kit_inlines_text(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["coder_kit"]["case_closed_keys"].append("fragment_text")


def _mutate_kit_slots(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["coder_kit"]["case_closed_keys"].append("marker_chain")


def _mutate_authority(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["authority"] = "authoritative"


def _mutate_suggestion(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["suggestion_status"] = "provided"


def _mutate_model(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["model_invoked"] = True


def _mutate_classification(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["classification"] = "pass"


def _mutate_threshold(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["threshold"] = 0.8


def _mutate_gold(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["is_gold"] = True


def _mutate_promotion(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["promotion"] = "gold"


def _mutate_submission_form(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["submission_schema_id"] = "m207-s02-coding-submission/v1"


def _mutate_abstention(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["vocabularies"]["abstention_values"] = ["not-abstained", "ambiguous", "reference"]


def _mutate_lifecycle(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["lifecycle"]["human_adoption"] = "adopted"


def _mutate_non_claim(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["non_claims"].append("not a real non-claim")


def _mutate_rationale(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["adjudication_input"]["rationale_max_chars"] = 0


def _mutate_battery_wallclock(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["battery"]["check_closed_keys"].append("duration_ms")


def _mutate_resolution(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["resolution_space"]["by_axis"]["reference_decision"].append("maybe")


def _mutate_store_path(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["store_paths"]["submissions"] = "some/other/dir"


def _mutate_diagnostics(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["diagnostics"].append("UNKNOWN_DIAGNOSTIC")


def _mutate_adjudication_gold(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["adjudication_record"]["is_gold"] = True


def _mutate_contract_authority(_schema: dict[str, Any], contract: dict[str, Any]) -> None:
    contract["output_contract"]["authority"] = "authoritative"


def _mutate_contract_diagnostics(_schema: dict[str, Any], contract: dict[str, Any]) -> None:
    contract["diagnostics"] = [*contract["diagnostics"], "EXTRA"]


def _mutate_contract_order(_schema: dict[str, Any], contract: dict[str, Any]) -> None:
    contract["order_of_operations"] = ["adjudication_recorded_separately", "pass_1_committed"]


SELFTEST_CASES: tuple[tuple[str, str, Mutator], ...] = (
    ("ninth-slot", "NINTH_SLOT", _mutate_slot_ninth),
    ("label-key", "LEAK_FORBIDDEN_KEY", _mutate_label_key),
    ("seed-span-key", "LEAK_FORBIDDEN_KEY", _mutate_seed_key),
    ("kit-inlines-text", "KIT_TEXT_INLINED", _mutate_kit_inlines_text),
    ("kit-ships-slot", "NINTH_SLOT", _mutate_kit_slots),
    ("authority-authoritative", "AUTHORITY_CLAIM", _mutate_authority),
    ("suggestion-provided", "AUTHORITY_CLAIM", _mutate_suggestion),
    ("model-invoked", "MODEL_INVOKED", _mutate_model),
    ("classification-pass", "CLASSIFICATION_REQUESTED", _mutate_classification),
    ("threshold-set", "THRESHOLD_REQUESTED", _mutate_threshold),
    ("gold-claim", "GOLD_CLAIM", _mutate_gold),
    ("promotion-claim", "PROMOTION_CLAIM", _mutate_promotion),
    ("submission-form-redefined", "SUBMISSION_SCHEMA_DRIFT", _mutate_submission_form),
    ("abstention-collapse", "ABSTENTION_COLLAPSE", _mutate_abstention),
    ("lifecycle-drift", "MISSING_LIFECYCLE_MARKER", _mutate_lifecycle),
    ("non-claim-drift", "MISSING_NON_CLAIM", _mutate_non_claim),
    ("rationale-unbounded", "RATIONALE_NOT_BOUNDED", _mutate_rationale),
    ("battery-wallclock", "BATTERY_WALLCLOCK_FORBIDDEN", _mutate_battery_wallclock),
    ("resolution-out-of-space", "RESOLUTION_SPACE_DRIFT", _mutate_resolution),
    ("store-prefix-escape", "UNSAFE_PATH", _mutate_store_path),
    ("diagnostic-table-drift", "DIAGNOSTIC_TABLE_DRIFT", _mutate_diagnostics),
    ("adjudication-gold", "GOLD_CLAIM", _mutate_adjudication_gold),
    ("contract-authority", "AUTHORITY_CLAIM", _mutate_contract_authority),
    ("contract-diagnostics", "DIAGNOSTIC_TABLE_DRIFT", _mutate_contract_diagnostics),
    ("contract-order", "SCHEMA_KEY_DRIFT", _mutate_contract_order),
)


def _selftest_baselines(
    root: Path, protocol_rel: str, schemas_rel: str
) -> tuple[dict[str, Any], dict[str, Any], list[str]] | None:
    protocol_path = root / protocol_rel
    schemas_path = root / schemas_rel
    if not protocol_path.is_file() or not schemas_path.is_file():
        return None
    protocol_text = protocol_path.read_text(encoding="utf-8")
    schema = load_json(schemas_path, "S02 schemas document")
    contract = extract_contract(protocol_text, CONTRACT_HEADING, "S02 protocol contract")
    return schema, contract, protocol_headings(protocol_text)


def run_selftest(root: Path, protocol_rel: str, schemas_rel: str) -> int:
    baselines = _selftest_baselines(root, protocol_rel, schemas_rel)
    if baselines is None:
        print("FAIL SELFTEST_BASELINE: S02 protocol or schemas missing", file=sys.stderr)
        return 1
    schema0, contract0, headings = baselines

    problems: list[str] = []
    for name, diagnostic, mutator in SELFTEST_CASES:
        schema = copy.deepcopy(schema0)
        contract = copy.deepcopy(contract0)
        mutator(schema, contract)
        failures: Failures = []
        check_schema_document(schema, failures)
        check_contract(contract, schema, headings, failures)
        seen = {diag for diag, _ in failures}
        if diagnostic not in seen:
            problems.append(
                f"hostile case {name!r} did not raise {diagnostic} (saw {sorted(seen) or 'nothing'})"
            )

    frozen_problem = _selftest_frozen_source_drift(root, protocol_rel, schemas_rel)
    if frozen_problem:
        problems.append(frozen_problem)

    alternative_problem = _selftest_alternative_drift(root, schemas_rel)
    if alternative_problem:
        problems.append(alternative_problem)

    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(
            f"FAIL M207_S02_SCHEMAS_SELFTEST: {len(problems)} hostile path(s) not proven",
            file=sys.stderr,
        )
        return 1
    print(SELFTEST_MARKER)
    return 0


def _selftest_alternative_drift(root: Path, schemas_rel: str) -> str | None:
    """Prove ALTERNATIVE_DRIFT: a moved codebook pole must break the resolution space."""
    schemas_path = root / schemas_rel
    codebook_path = root / S01_CODEBOOK_REL
    if not schemas_path.is_file() or not codebook_path.is_file():
        return "alternative-drift selftest could not read its inputs"
    schema = load_json(schemas_path, "S02 schemas document")
    try:
        codebook_contract = extract_contract(
            codebook_path.read_text(encoding="utf-8"),
            "Machine-readable codebook contract",
            "S01 codebook contract",
        )
    except GateError as exc:
        return f"alternative-drift selftest could not parse the S01 codebook: {exc}"
    clean: Failures = []
    check_resolution_against_codebook(schema, codebook_contract, clean)
    if clean:
        return (
            "alternative-drift selftest: the unmutated codebook raised "
            f"{sorted({diag for diag, _ in clean})}"
        )
    mutated = copy.deepcopy(codebook_contract)
    for row in mutated.get("alternative_axes", []):
        if isinstance(row, dict) and row.get("axis") == "reference_decision":
            row["values"] = ["reference", "maybe"]
    failures: Failures = []
    check_resolution_against_codebook(schema, mutated, failures)
    seen = {diag for diag, _ in failures}
    if "ALTERNATIVE_DRIFT" not in seen:
        return (
            "alternative-drift selftest: a moved codebook pole did not raise "
            f"ALTERNATIVE_DRIFT (saw {sorted(seen) or 'nothing'})"
        )
    return None


def _selftest_frozen_source_drift(root: Path, protocol_rel: str, schemas_rel: str) -> str | None:
    """Prove FROZEN_SOURCE_DRIFT against a mutated copy of a frozen S01 input."""
    rels = [protocol_rel, schemas_rel, *(rel for rel, _ in FROZEN_SOURCES.values())]
    with tempfile.TemporaryDirectory(prefix="m207-s02-drift-") as tmp:
        tmp_root = Path(tmp)
        for rel in dict.fromkeys(rels):
            source = root / rel
            if not source.is_file():
                return f"frozen-drift selftest could not read {rel}"
            target = tmp_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        mutated = tmp_root / S01_SCHEMAS_REL
        mutated.write_bytes(mutated.read_bytes() + b" ")
        seen = {diag for diag, _ in collect_failures(tmp_root, protocol_rel, schemas_rel)}
    if "FROZEN_SOURCE_DRIFT" not in seen:
        return (
            "frozen-drift selftest: a mutated S01 schemas copy did not raise "
            f"FROZEN_SOURCE_DRIFT (saw {sorted(seen) or 'nothing'})"
        )
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "selftest"],
        help="'check' verifies the frozen contract read-only; 'selftest' additionally "
        "proves the hostile paths",
    )
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="repository root the artifact paths are resolved against",
    )
    parser.add_argument("--protocol", default=PROTOCOL_REL, help="protocol path relative to root")
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="schema path relative to root")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"FAIL MISSING_ARTIFACT: root {root} is not a directory", file=sys.stderr)
        return 1
    if args.mode == "selftest":
        return run_selftest(root, args.protocol, args.schemas)
    return report(collect_failures(root, args.protocol, args.schemas), MARKER)


if __name__ == "__main__":
    raise SystemExit(main())
