#!/usr/bin/env python3
"""Separately recorded human adjudication and the pilot receipt (M207 S02 T05).

The codebook (§8) and the S02 protocol (§3) fix the order of operations: two
independent human codings, then a **frozen** pre-adjudication agreement score,
then adjudication recorded as a **separate** artifact pinned to that frozen
score.  RC28-F01 is the defect this task exists to prevent: an adjudicated set
promoted as gold, or a pre-adjudication score recomputed after adjudication.

Invariants (each enforced in code, not merely documented):

* **Agreement freezes before adjudication.**  ``run`` reads the frozen agreement
  report (``m207-s02-agreement-report/v1``) and the separate disagreement
  inventory (``m207-s02-disagreement-inventory/v1``) written by the T04 contour,
  and pins the sha256 of the report bytes into the record
  (``pre_adjudication_agreement_sha256``).  A report mutated after the record was
  frozen is detected as pin drift (``FROZEN_SOURCE_DRIFT``) and the contour
  refuses to re-pin.  Adjudication never rewrites a pre-adjudication score.
* **Adjudication resolves an inventoried disagreement, nothing else.**  Every
  human adjudication input names one ``(case_id, axis)`` that the disagreement
  inventory lists; anything else is ``ADJUDICATION_NOT_A_DISAGREEMENT``.
  ``resolution`` must come from the closed per-axis space derived from the S01
  codebook decision poles (``RESOLUTION_OUT_OF_SPACE``); on ``span_exact`` the
  resolution names one of the two already-committed coder spans
  (``span_pass_1`` / ``span_pass_2``) and never mints a third.
* **Humans only, never gold.**  ``provenance`` is exactly ``human-reviewed``
  (``ADJUDICATOR_PROVENANCE_NOT_HUMAN``); the record pins ``is_gold: false``,
  ``promotion: "none"`` and ``append_only: true``; a document claiming gold is
  ``IS_GOLD_CLAIM`` / ``GOLD_CLAIM``.
* **Append-only supersession.**  Supersession is an explicit ``supersedes``
  reference to an existing adjudication id (``SUPERSEDES_UNKNOWN`` otherwise,
  ``SCHEMA_KEY_DRIFT`` for a self reference, a cycle or a link across
  disagreements).  Superseded entries are retained in the record — history is
  never rewritten.  An adjudication id that disappears from the human corpus
  while a record already exists is ``FROZEN_SOURCE_DRIFT``.
* **Open disagreements stay visible and are counted.**  ``resolved_count`` and
  ``unresolved_count`` are computed over the full inventory.  The contour
  publishes a record only when every inventoried disagreement carries a human
  resolution: a partial corpus exits non-zero with ``UNRESOLVED_NONZERO``,
  enumerates each still-open ``case_id × axis`` on stderr, and writes **no**
  artifact.  A half-resolved pilot is never passed off as a performed pilot
  (``human_pilot_performed`` is therefore a positive fact, not a claim).
* **The harness never writes an adjudication.**  The only writes are the two
  derived evidence artifacts under ``prd/migration/rust-evidence`` (atomic
  tmp+replace with rollback of the pair).  Every target under ``prd/annotation/``
  is refused with ``UNSAFE_PATH`` and the ``--store`` prefix lock keeps the human
  drop box inside ``prd/annotation/`` (D480/D474/D476).
* **Rationale is a bounded free-text channel.**  At most 280 characters, single
  line, no forbidden leakage tokens (``RATIONALE_NOT_BOUNDED`` /
  ``LEAK_FORBIDDEN_KEY``); this is the schema-level mitigation for the free-text
  residual of the S02 threat surface.

Modes:

* ``check`` -- offline self-check of the contour, with no human data: the frozen
  contract binding (resolution space derived from the S01 codebook decision
  poles, input/record/receipt closed keys, diagnostic table), the claim guards,
  the supersession rules, the bound on ``rationale``, the annotation-write
  refusal and the absent-store contract.  Prints ``M207_S02_ADJUDICATION_OK``.
  With ``--allow-test-fixtures`` it additionally runs the whole ``run`` contour
  against a synthetic store outside the repository.
* ``run`` -- read the human adjudication drop box
  (``prd/annotation/m207-s02-adjudications``), resolve the inventoried
  disagreements against the frozen agreement report and write
  ``prd/migration/rust-evidence/m207-s02-adjudication-record.json``
  (``m207-s02-adjudication-record/v1``) plus
  ``prd/migration/rust-evidence/m207-s02-pilot-receipt.json``
  (``m207-s02-pilot-receipt/v1``).  With no human adjudication the run exits
  ``3`` with ``HUMAN_PILOT_ABSENT`` (no agreement yet) or
  ``NO_ADJUDICATION_INPUT`` (agreement frozen, adjudication missing) and writes
  nothing.

The diagnostic names are exactly the ones frozen in ``$.diagnostics``; the closed
candidate list this tool may speak is ``LOCAL_DIAGNOSTICS`` below, and ``check``
fails closed if any of them leaves the frozen table.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_sibling(module_name: str) -> Any:
    """Load a sibling harness module by path (``scripts/`` is not a package).

    The agreement contour is loaded first and its already-registered intake
    module is reused, so ``GateError`` keeps a single identity across all three
    contours (a second import of the same file would mint a second class and
    every ``except GateError`` would silently stop matching).
    """
    path = Path(__file__).resolve().parent / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - import machinery guard
        raise RuntimeError(f"cannot load sibling module {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(module_name, module)
    spec.loader.exec_module(module)
    return module


try:
    AGREEMENT = _load_sibling("m207_s02_agreement")
except Exception as exc:  # pragma: no cover - only a repository defect reaches this
    print(
        "FAIL MISSING_ARTIFACT: cannot load the sibling agreement contour "
        f"scripts/m207_s02_agreement.py: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

# The agreement contour owns submission binding, path policy, rendering and the
# claim guards; reusing them keeps one implementation of each rule.
INTAKE = AGREEMENT.INTAKE
GateError = INTAKE.GateError
Failures = list[tuple[str, str]]

MARKER = "M207_S02_ADJUDICATION_OK"
RUN_MARKER = "M207_S02_ADJUDICATION_RECORDED"

ABSENT_EXIT = 3
FAIL_EXIT = 1

SCHEMA_VERSION = 1
ADJ_INPUT_SCHEMA_ID = "m207-s02-adjudication-input/v1"
ADJ_RECORD_SCHEMA_ID = "m207-s02-adjudication-record/v1"
PILOT_RECEIPT_SCHEMA_ID = "m207-s02-pilot-receipt/v1"
AGREEMENT_REPORT_SCHEMA_ID = "m207-s02-agreement-report/v1"
DISAGREEMENT_INVENTORY_SCHEMA_ID = "m207-s02-disagreement-inventory/v1"

STORE_REL = "prd/annotation/m207-s02-adjudications"
RECORD_REL = "prd/migration/rust-evidence/m207-s02-adjudication-record.json"
RECEIPT_REL = "prd/migration/rust-evidence/m207-s02-pilot-receipt.json"

CASE_COUNT = 40
CODER_COUNT = 2
MIN_ADJUDICATOR_COUNT = 1
RATIONALE_MAX_CHARS = 280

ADJUDICATOR_PROVENANCE = "human-reviewed"
PROMOTION_NONE = "none"

REFERENCE_DECISION_AXIS = AGREEMENT.REFERENCE_DECISION_AXIS
SPAN_EXACT_AXIS = AGREEMENT.SPAN_EXACT_AXIS
ABSTENTION_AXIS = AGREEMENT.ABSTENTION_AXIS
SLOT_AXIS_PREFIX = AGREEMENT.SLOT_AXIS_PREFIX
SPAN_PASS_ONE = "span_pass_1"
SPAN_PASS_TWO = "span_pass_2"
SLOT_PASS_VALUES = ("slot_present", "slot_absent")
INVENTORY_ENTRY_CLOSED_KEYS = ("axis", "case_id", "pass_1_value", "pass_2_value", "work_family")

# The closed set of names this tool may speak; ``check`` proves every one of them
# is in the frozen ``$.diagnostics`` table.
LOCAL_DIAGNOSTICS = (
    "ADJUDICATION_NOT_A_DISAGREEMENT",
    "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
    "AUTHORITY_CLAIM",
    "CLASSIFICATION_REQUESTED",
    "DENOMINATOR_MISMATCH",
    "DIAGNOSTIC_TABLE_DRIFT",
    "DUPLICATE_JSON_KEY",
    "FROZEN_SOURCE_DRIFT",
    "GOLD_CLAIM",
    "HUMAN_PILOT_ABSENT",
    "IS_GOLD_CLAIM",
    "LEAK_FORBIDDEN_KEY",
    "MISSING_ARTIFACT",
    "MISSING_LIFECYCLE_MARKER",
    "MISSING_NON_CLAIM",
    "MODEL_INVOKED",
    "NO_ADJUDICATION_INPUT",
    "ONE_CODER_ONLY",
    "PROMOTION_CLAIM",
    "RATIONALE_NOT_BOUNDED",
    "RESOLUTION_OUT_OF_SPACE",
    "RESOLUTION_SPACE_DRIFT",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "SLOT_SET_DRIFT",
    "SUPERSEDES_UNKNOWN",
    "TEST_FIXTURE_IN_STORE",
    "THRESHOLD_REQUESTED",
    "UNRESOLVED_NONZERO",
    "UNSAFE_PATH",
    "VOCABULARY_DRIFT",
)

# Claim keys whose *value* is pinned by the frozen contract.  A document that
# carries the key with any other value is asking for something this task may not
# produce.
CLAIM_PINS: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("threshold", lambda value: value is None, "THRESHOLD_REQUESTED"),
    ("classification", lambda value: value == "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("promotion", lambda value: value == PROMOTION_NONE, "PROMOTION_CLAIM"),
    ("is_gold", lambda value: value is False, "IS_GOLD_CLAIM"),
)

# Scalar claim rules for an adjudication input: the key is only ever allowed to
# state the value this slice forbids.
SCALAR_CLAIM_RULES: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("authority", lambda value: value == "none", "AUTHORITY_CLAIM"),
    ("suggestion_status", lambda value: value == "none-provided", "AUTHORITY_CLAIM"),
    ("model_invoked", lambda value: value is False, "MODEL_INVOKED"),
    ("threshold", lambda value: value is None, "THRESHOLD_REQUESTED"),
    ("classification", lambda value: value == "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("promotion", lambda value: value == PROMOTION_NONE, "PROMOTION_CLAIM"),
    ("is_gold", lambda value: value is False, "IS_GOLD_CLAIM"),
)


class ProbeFailure(Exception):
    """An in-script probe did not behave as the contour requires."""


@dataclass(frozen=True)
class Adjudication:
    """One validated human adjudication entry, as read from the drop box."""

    adjudication_id: str
    adjudicator_id: str
    axis: str
    case_id: str
    provenance: str
    rationale: str
    resolution: str
    supersedes: str | None
    source_name: str


# --------------------------------------------------------------------------- #
# Frozen contract binding.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Contract:
    """The adjudication contract as declared by the frozen S02 schemas."""

    axes: tuple[str, ...]
    resolution_space: dict[str, tuple[str, ...]]
    input_closed_keys: tuple[str, ...]
    input_required_keys: tuple[str, ...]
    record_closed_keys: tuple[str, ...]
    record_entry_closed_keys: tuple[str, ...]
    receipt_closed_keys: tuple[str, ...]
    units_total: int
    work_family_cap: int
    rationale_max_chars: int
    store_rel: str

    @property
    def allowed_keys(self) -> frozenset[str]:
        """Every key name the frozen adjudication contract already declares."""
        return frozenset(
            self.input_closed_keys
            + self.record_closed_keys
            + self.record_entry_closed_keys
            + self.receipt_closed_keys
        )

    def space_for(self, axis: str) -> tuple[str, ...]:
        return self.resolution_space.get(axis, ())


def _closed_keys(
    sub: dict[str, Any], label: str, diagnostic: str, *, key: str = ""
) -> tuple[str, ...]:
    name = f"{key}_closed_keys" if key else "closed_keys"
    value = sub.get(name)
    if not isinstance(value, list) or not value:
        raise GateError(diagnostic, f"$.schemas.{label}.{name} is not a closed key list")
    return tuple(str(item) for item in value)


def derive_resolution_space(
    axes: Sequence[str], s01_schemas: dict[str, Any]
) -> dict[str, tuple[str, ...]]:
    """Re-derive the closed per-axis resolution space from the S01 decision poles.

    ``reference_decision`` comes from the S01 ``alternative_axes`` axis of the
    same name, every ``slot_*`` axis from the S01 ``slot_presence`` axis,
    ``abstention`` from the frozen abstention vocabulary, and ``span_exact`` from
    the protocol rule that names one of the two committed coder spans.  New
    values are never allowed: a drift here is ``RESOLUTION_SPACE_DRIFT``.
    """
    alternatives = {
        str(entry.get("axis")): tuple(str(value) for value in entry.get("values") or ())
        for entry in s01_schemas.get("alternative_axes") or ()
        if isinstance(entry, dict)
    }
    decision = alternatives.get(REFERENCE_DECISION_AXIS) or ()
    slot_presence = alternatives.get("slot_presence") or ()
    abstention = tuple(
        str(value)
        for value in (s01_schemas.get("vocabularies") or {}).get("abstention_values") or ()
    )
    for name, values in (
        (REFERENCE_DECISION_AXIS, decision),
        ("slot_presence", slot_presence),
        (ABSTENTION_AXIS, abstention),
    ):
        if not values:
            raise GateError(
                "RESOLUTION_SPACE_DRIFT",
                f"the S01 codebook declares no closed decision poles for {name!r}",
            )
    space: dict[str, tuple[str, ...]] = {}
    for axis in axes:
        if axis == REFERENCE_DECISION_AXIS:
            space[axis] = decision
        elif axis == ABSTENTION_AXIS:
            space[axis] = abstention
        elif axis == SPAN_EXACT_AXIS:
            space[axis] = (SPAN_PASS_ONE, SPAN_PASS_TWO)
        elif axis.startswith(SLOT_AXIS_PREFIX):
            space[axis] = slot_presence
        else:
            raise GateError(
                "RESOLUTION_SPACE_DRIFT",
                f"agreement axis {axis!r} has no derivation rule for its resolution space",
            )
    return space


def load_contract(world: Any) -> Contract:
    """Bind the adjudication contour to the frozen S02 schema document."""
    agreement = AGREEMENT.load_contract(world)
    axes = agreement.axes
    schemas = world.schemas
    resolution_space = schemas.get("resolution_space") or {}
    declared = resolution_space.get("by_axis") or {}
    derived = derive_resolution_space(axes, world.s01_schemas)
    if sorted(derived) != sorted(declared):
        raise GateError(
            "RESOLUTION_SPACE_DRIFT",
            f"$.resolution_space.by_axis covers {sorted(declared)} but the agreement axes are "
            f"{sorted(derived)}",
        )
    for axis, values in derived.items():
        observed = tuple(str(value) for value in declared.get(axis) or ())
        if observed != values:
            raise GateError(
                "RESOLUTION_SPACE_DRIFT",
                f"$.resolution_space.by_axis[{axis!r}]={list(observed)} != the closed space "
                f"derived from the frozen codebook {list(values)}",
            )
    if resolution_space.get("new_values_allowed") is not False:
        raise GateError(
            "RESOLUTION_SPACE_DRIFT",
            "$.resolution_space.new_values_allowed must be false: an adjudicator never mints a "
            "new decision value",
        )
    store = schemas.get("store_paths") or {}
    if store.get("adjudications") != STORE_REL:
        raise GateError(
            "UNSAFE_PATH",
            f"$.store_paths.adjudications={store.get('adjudications')!r} != {STORE_REL!r} (D480)",
        )
    if (
        store.get("allowed_prefix") != INTAKE.ANNOTATION_PREFIX
        or store.get("store_prefix_lock") is not True
    ):
        raise GateError(
            "UNSAFE_PATH",
            "$.store_paths.allowed_prefix / store_prefix_lock must keep the human store inside "
            f"{INTAKE.ANNOTATION_PREFIX} (D480)",
        )
    sub = schemas.get("schemas") or {}
    input_schema = sub.get("adjudication_input") or {}
    record_schema = sub.get("adjudication_record") or {}
    receipt_schema = sub.get("pilot_receipt") or {}
    for label, schema, expected in (
        ("adjudication_input", input_schema, ADJ_INPUT_SCHEMA_ID),
        ("adjudication_record", record_schema, ADJ_RECORD_SCHEMA_ID),
        ("pilot_receipt", receipt_schema, PILOT_RECEIPT_SCHEMA_ID),
    ):
        if schema.get("schema_id") != expected:
            raise GateError(
                "SCHEMA_KEY_DRIFT",
                f"$.schemas.{label}.schema_id={schema.get('schema_id')!r} != {expected!r}",
            )
    input_closed = _closed_keys(input_schema, "adjudication_input", "SCHEMA_KEY_DRIFT")
    input_required = tuple(str(key) for key in input_schema.get("required_keys") or ())
    if not set(input_required) <= set(input_closed):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "$.schemas.adjudication_input.required_keys is not a subset of its closed keys",
        )
    record_closed = _closed_keys(record_schema, "adjudication_record", "SCHEMA_KEY_DRIFT")
    if sorted(record_closed) != sorted(record_schema.get("required_keys") or []):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "$.schemas.adjudication_record.required_keys != its closed keys",
        )
    entry_closed = _closed_keys(
        record_schema, "adjudication_record", "SCHEMA_KEY_DRIFT", key="entry"
    )
    entry_required = tuple(str(key) for key in record_schema.get("entry_required_keys") or ())
    if not entry_required or not set(entry_required) <= set(entry_closed):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "$.schemas.adjudication_record.entry_required_keys is not a non-empty subset of its "
            "closed keys",
        )
    receipt_closed = _closed_keys(receipt_schema, "pilot_receipt", "SCHEMA_KEY_DRIFT")
    if sorted(receipt_closed) != sorted(receipt_schema.get("required_keys") or []):
        raise GateError(
            "SCHEMA_KEY_DRIFT", "$.schemas.pilot_receipt.required_keys != its closed keys"
        )
    if input_schema.get("rationale_max_chars") != RATIONALE_MAX_CHARS:
        raise GateError(
            "RATIONALE_NOT_BOUNDED",
            "$.schemas.adjudication_input.rationale_max_chars="
            f"{input_schema.get('rationale_max_chars')!r} != {RATIONALE_MAX_CHARS}",
        )
    if input_schema.get("rationale_single_line") is not True:
        raise GateError(
            "RATIONALE_NOT_BOUNDED",
            "$.schemas.adjudication_input.rationale_single_line must be true",
        )
    if input_schema.get("adjudicator_provenance") != ADJUDICATOR_PROVENANCE:
        raise GateError(
            "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
            "$.schemas.adjudication_input.adjudicator_provenance="
            f"{input_schema.get('adjudicator_provenance')!r} != {ADJUDICATOR_PROVENANCE!r}",
        )
    if (
        record_schema.get("append_only") is not True
        or record_schema.get("is_gold") is not False
        or record_schema.get("promotion") != PROMOTION_NONE
        or record_schema.get("adjudicator_provenance") != ADJUDICATOR_PROVENANCE
    ):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "$.schemas.adjudication_record must pin append_only=true, is_gold=false, "
            f"promotion={PROMOTION_NONE!r} and adjudicator_provenance={ADJUDICATOR_PROVENANCE!r}",
        )
    if receipt_schema.get("case_count") != CASE_COUNT:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"$.schemas.pilot_receipt.case_count={receipt_schema.get('case_count')!r} != "
            f"{CASE_COUNT}",
        )
    if receipt_schema.get("coder_count") != CODER_COUNT:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"$.schemas.pilot_receipt.coder_count={receipt_schema.get('coder_count')!r} != "
            f"{CODER_COUNT}",
        )
    if receipt_schema.get("adjudicator_count_min") != MIN_ADJUDICATOR_COUNT:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            "$.schemas.pilot_receipt.adjudicator_count_min="
            f"{receipt_schema.get('adjudicator_count_min')!r} != {MIN_ADJUDICATOR_COUNT}",
        )
    if receipt_schema.get("promotion") != PROMOTION_NONE:
        raise GateError(
            "PROMOTION_CLAIM",
            f"$.schemas.pilot_receipt.promotion={receipt_schema.get('promotion')!r} != "
            f"{PROMOTION_NONE!r}",
        )
    table = schemas.get("diagnostics")
    frozen = table if isinstance(table, list) else []
    for name in LOCAL_DIAGNOSTICS:
        if name not in frozen:
            raise GateError(
                "DIAGNOSTIC_TABLE_DRIFT",
                f"adjudication diagnostic {name!r} is not in the frozen $.diagnostics table",
            )
    return Contract(
        axes=axes,
        resolution_space=derived,
        input_closed_keys=input_closed,
        input_required_keys=input_required,
        record_closed_keys=record_closed,
        record_entry_closed_keys=entry_closed,
        receipt_closed_keys=receipt_closed,
        units_total=agreement.units_total,
        work_family_cap=agreement.work_family_cap,
        rationale_max_chars=RATIONALE_MAX_CHARS,
        store_rel=STORE_REL,
    )


# --------------------------------------------------------------------------- #
# Claim guards, closure checks and the human store.
# --------------------------------------------------------------------------- #


def guard_no_claims(node: Any, allowed_keys: frozenset[str], pointer: str = "$") -> None:
    """Refuse a document that asks for gold, a promotion, a threshold or a verdict."""
    if isinstance(node, dict):
        for key, value in node.items():
            for pinned, predicate, diagnostic in CLAIM_PINS:
                if key == pinned and not predicate(value):
                    raise GateError(
                        diagnostic,
                        f"{pointer}.{key}={value!r} is a claim this task may not make",
                    )
            if str(key) not in allowed_keys:
                for token in INTAKE.key_tokens(str(key)):
                    hit = AGREEMENT.FORBIDDEN_KEY_TOKENS.get(token)
                    if hit is not None:
                        raise GateError(
                            hit,
                            f"{pointer}.{key} asks for {token!r}, which is outside adjudication "
                            "validation (S03 owns per-aspect rates, S04 the threshold)",
                        )
            guard_no_claims(value, allowed_keys, f"{pointer}.{key}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            guard_no_claims(item, allowed_keys, f"{pointer}[{index}]")


def scan_scalar_claims(node: Any, pointer: str) -> None:
    """Refuse authority, model, threshold, verdict, promotion and gold claims."""
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            if isinstance(value, (dict, list)):
                scan_scalar_claims(value, f"{pointer}.{name}")
                continue
            for pinned, is_legal, diagnostic in SCALAR_CLAIM_RULES:
                if name == pinned and not is_legal(value):
                    raise GateError(
                        diagnostic,
                        f"{pointer}.{name}={value!r} claims what this slice forbids",
                    )
            scan_scalar_claims(value, f"{pointer}.{name}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_scalar_claims(item, f"{pointer}[{index}]")


def scan_leak_tokens(node: Any, pointer: str, *, exempt: bool = False) -> None:
    """Reject predicted-answer and rule-seed fields, including in rationale text."""
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            if name not in INTAKE.EXEMPT_KEYS:
                hit = INTAKE.forbidden_key_hit(name, value)
                if hit == "gold-claim":
                    raise GateError("GOLD_CLAIM", f"key {name!r} at {pointer} claims gold")
                if hit:
                    raise GateError(
                        "LEAK_FORBIDDEN_KEY",
                        f"key {name!r} at {pointer} mints a {hit} field",
                    )
            scan_leak_tokens(
                value,
                f"{pointer}.{name}",
                exempt=exempt or name in INTAKE.EXEMPT_KEYS,
            )
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_leak_tokens(item, f"{pointer}[{index}]", exempt=exempt)
    elif isinstance(node, str) and not exempt:
        for needle in INTAKE.FORBIDDEN_SUBSTRINGS:
            if needle in node:
                raise GateError(
                    "LEAK_FORBIDDEN_KEY",
                    f"{pointer} carries the forbidden substring {needle!r}",
                )


def check_closed_keys(document: Any, expected: Sequence[str], pointer: str) -> None:
    if not isinstance(document, dict):
        raise GateError("SCHEMA_KEY_DRIFT", f"{pointer} is not a JSON object")
    keys = sorted(document.keys())
    if keys != sorted(expected):
        missing = [key for key in expected if key not in document]
        extra = [key for key in document if key not in expected]
        raise GateError(
            "SCHEMA_KEY_DRIFT", f"{pointer} keys drift: missing={missing} extra={extra}"
        )


def check_allowed_keys(document: Any, closed: Sequence[str], pointer: str) -> None:
    """No key outside the closed set; the required subset is checked separately.

    An adjudication input declares optional keys (``is_gold``, ``lifecycle``,
    ``non_claims``): the closed set bounds what may appear, the required set
    bounds what must.
    """
    if not isinstance(document, dict):
        raise GateError("SCHEMA_KEY_DRIFT", f"{pointer} is not a JSON object")
    extra = [key for key in document if key not in closed]
    if extra:
        raise GateError("SCHEMA_KEY_DRIFT", f"{pointer} carries undeclared key(s) {extra}")


def check_rationale(value: Any, pointer: str, *, max_chars: int) -> str:
    """The free-text channel is bounded by the frozen contract (§8)."""
    if not isinstance(value, str) or not value.strip():
        raise GateError("RATIONALE_NOT_BOUNDED", f"{pointer} must be a non-empty string")
    if "\n" in value or "\r" in value:
        raise GateError("RATIONALE_NOT_BOUNDED", f"{pointer} must be a single line")
    if len(value) > max_chars:
        raise GateError(
            "RATIONALE_NOT_BOUNDED",
            f"{pointer} carries {len(value)} characters, above the frozen bound {max_chars}",
        )
    return value


def discover_adjudications(store: Path, *, agreement_frozen: bool) -> list[INTAKE.StoreFile]:
    """Read the human adjudication drop box, or refuse: no input is not success.

    ``HUMAN_PILOT_ABSENT`` means no human evidence exists at all; once the
    pre-adjudication score is frozen, a missing adjudication corpus is the more
    precise ``NO_ADJUDICATION_INPUT``.  Both exit ``3`` and write nothing.
    """
    if agreement_frozen:
        diagnostic = "NO_ADJUDICATION_INPUT"
        hint = (
            "the pre-adjudication agreement is frozen but no human adjudication exists yet "
            "(the harness never creates one)"
        )
    else:
        diagnostic = "HUMAN_PILOT_ABSENT"
        hint = "no human submission or adjudication exists yet (the harness never creates one)"
    if not store.exists():
        raise GateError(diagnostic, f"store {store} does not exist; {hint}")
    if not store.is_dir():
        raise GateError(diagnostic, f"store {store} is not a directory; {hint}")
    candidates = sorted(
        (path for path in store.iterdir() if path.is_file() and path.suffix == ".json"),
        key=lambda path: path.name,
    )
    if not candidates:
        raise GateError(diagnostic, f"store {store} holds no *.json adjudication; {hint}")
    return [
        INTAKE.StoreFile(name=path.name, path=path, raw=path.read_bytes()) for path in candidates
    ]


def load_family_map(root: Path, cases_raw: str, universe: tuple[str, ...]) -> dict[str, str]:
    """Join ``work_family`` from the frozen S01 case manifest (used by ``check``)."""
    return AGREEMENT.load_families(root, cases_raw, universe)


# --------------------------------------------------------------------------- #
# Adjudication input validation.
# --------------------------------------------------------------------------- #


def validate_adjudication(
    envelope: Any,
    *,
    label: str,
    file_name: str,
    contract: Contract,
    inventory_keys: frozenset[tuple[str, str]],
    universe: tuple[str, ...],
    world: Any,
    allow_test_fixtures: bool,
) -> Adjudication:
    """Validate one human adjudication input, fail-closed and read-only."""
    if not isinstance(envelope, dict):
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} is not a JSON object")
    if envelope.get("schema") != ADJ_INPUT_SCHEMA_ID:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"{label} schema={envelope.get('schema')!r} != {ADJ_INPUT_SCHEMA_ID!r}",
        )
    scan_scalar_claims(envelope, label)
    marker = INTAKE.fixture_marker_hit(
        envelope,
        file_name,
        Path(file_name).stem,
        str(envelope.get("adjudication_id") or ""),
        str(envelope.get("adjudicator_id") or ""),
    )
    if marker and not allow_test_fixtures:
        raise GateError(
            "TEST_FIXTURE_IN_STORE",
            f"{label} carries the fixture marker {marker!r}; a synthetic adjudication may never "
            "enter a product store (pass --allow-test-fixtures outside prd/annotation/)",
        )
    scan_leak_tokens(envelope, label)
    check_allowed_keys(envelope, contract.input_closed_keys, label)
    missing = [key for key in contract.input_required_keys if key not in envelope]
    if missing:
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} misses required key(s) {missing}")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"{label}.schema_version={envelope.get('schema_version')!r} != {SCHEMA_VERSION}",
        )
    provenance = envelope.get("provenance")
    if provenance != ADJUDICATOR_PROVENANCE:
        raise GateError(
            "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
            f"{label}.provenance={provenance!r} != {ADJUDICATOR_PROVENANCE!r}: only a human "
            "adjudicator may resolve a disagreement",
        )
    if "lifecycle" in envelope and envelope["lifecycle"] != world.lifecycle:
        raise GateError(
            "MISSING_LIFECYCLE_MARKER",
            f"{label}.lifecycle differs from the frozen lifecycle markers",
        )
    if "non_claims" in envelope and list(envelope["non_claims"] or []) != list(world.non_claims):
        raise GateError(
            "MISSING_NON_CLAIM",
            f"{label}.non_claims differs from the frozen non-claims list",
        )
    adjudication_id = envelope.get("adjudication_id")
    adjudicator_id = envelope.get("adjudicator_id")
    if not isinstance(adjudication_id, str) or not adjudication_id.strip():
        raise GateError("SCHEMA_KEY_DRIFT", f"{label}.adjudication_id must be a non-empty string")
    if not isinstance(adjudicator_id, str) or not adjudicator_id.strip():
        raise GateError("SCHEMA_KEY_DRIFT", f"{label}.adjudicator_id must be a non-empty string")
    axis = envelope.get("axis")
    if axis not in contract.axes:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"{label}.axis={axis!r} is not one of the frozen agreement axes",
        )
    case_id = envelope.get("case_id")
    if case_id not in universe:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"{label}.case_id={case_id!r} is not one of the {len(universe)} frozen cases",
        )
    if (case_id, axis) not in inventory_keys:
        raise GateError(
            "ADJUDICATION_NOT_A_DISAGREEMENT",
            f"{label} resolves ({case_id!r}, {axis!r}), which the frozen disagreement inventory "
            "does not list: adjudication resolves disagreements and nothing else",
        )
    resolution = envelope.get("resolution")
    space = contract.space_for(str(axis))
    if resolution not in space:
        raise GateError(
            "RESOLUTION_OUT_OF_SPACE",
            f"{label}.resolution={resolution!r} is outside the closed space {list(space)} for "
            f"axis {axis!r}: an adjudicator never mints a new value",
        )
    rationale = check_rationale(
        envelope.get("rationale"), f"{label}.rationale", max_chars=contract.rationale_max_chars
    )
    supersedes = envelope.get("supersedes")
    if supersedes is not None and (not isinstance(supersedes, str) or not supersedes.strip()):
        raise GateError(
            "SUPERSEDES_UNKNOWN",
            f"{label}.supersedes={supersedes!r} must be null or an existing adjudication id",
        )
    return Adjudication(
        adjudication_id=adjudication_id,
        adjudicator_id=adjudicator_id,
        axis=str(axis),
        case_id=str(case_id),
        provenance=str(provenance),
        rationale=rationale,
        resolution=str(resolution),
        supersedes=supersedes,
        source_name=file_name,
    )


def evaluate_store(
    files: Sequence[INTAKE.StoreFile],
    *,
    contract: Contract,
    inventory_keys: frozenset[tuple[str, str]],
    universe: tuple[str, ...],
    world: Any,
    allow_test_fixtures: bool,
    failures: Failures,
) -> list[Adjudication]:
    """Validate every adjudication input and the cross-entry identity rules."""
    entries: list[Adjudication] = []
    seen: dict[str, str] = {}
    for store_file in files:
        label = store_file.name
        try:
            envelope = INTAKE.load_json_text(store_file.raw.decode("utf-8"), label)
        except GateError as exc:
            failures.append((exc.diagnostic, exc.detail))
            continue
        try:
            entry = validate_adjudication(
                envelope,
                label=label,
                file_name=store_file.name,
                contract=contract,
                inventory_keys=inventory_keys,
                universe=universe,
                world=world,
                allow_test_fixtures=allow_test_fixtures,
            )
        except GateError as exc:
            failures.append((exc.diagnostic, exc.detail))
            continue
        previous = seen.get(entry.adjudication_id)
        if previous is not None:
            failures.append(
                (
                    "SCHEMA_KEY_DRIFT",
                    f"adjudication_id {entry.adjudication_id!r} appears in both {previous} and "
                    f"{label}: an adjudication id is an identity, never a label to reuse",
                )
            )
            continue
        seen[entry.adjudication_id] = label
        entries.append(entry)
    if failures:
        return []
    try:
        check_supersession(entries)
    except GateError as exc:
        failures.append((exc.diagnostic, exc.detail))
        return []
    return entries


def check_supersession(entries: Sequence[Adjudication]) -> None:
    """Supersession is an explicit, acyclic, same-disagreement reference."""
    by_id = {entry.adjudication_id: entry for entry in entries}
    for entry in entries:
        target_id = entry.supersedes
        if target_id is None:
            continue
        if target_id == entry.adjudication_id:
            raise GateError("SUPERSEDES_UNKNOWN", f"{entry.adjudication_id!r} supersedes itself")
        target = by_id.get(target_id)
        if target is None:
            raise GateError(
                "SUPERSEDES_UNKNOWN",
                f"{entry.adjudication_id!r} supersedes {target_id!r}, which no human adjudication "
                "in the store defines",
            )
        if (target.case_id, target.axis) != (entry.case_id, entry.axis):
            raise GateError(
                "SCHEMA_KEY_DRIFT",
                f"{entry.adjudication_id!r} supersedes {target_id!r} for a different disagreement "
                f"({target.case_id!r}, {target.axis!r})",
            )
    for entry in entries:
        seen: set[str] = set()
        cursor: Adjudication | None = entry
        while cursor is not None and cursor.supersedes is not None:
            if cursor.adjudication_id in seen:
                raise GateError(
                    "SCHEMA_KEY_DRIFT",
                    f"supersession cycle detected at {cursor.adjudication_id!r}",
                )
            seen.add(cursor.adjudication_id)
            cursor = by_id.get(cursor.supersedes)


def resolution_tips(entries: Sequence[Adjudication]) -> dict[tuple[str, str], Adjudication]:
    """The tip of each ``(case_id, axis)`` supersession chain.

    Every entry is retained (append-only); a disagreement counts as resolved only
    when its chain has a tip that nothing supersedes.
    """
    superseded = {entry.supersedes for entry in entries if entry.supersedes is not None}
    tips: dict[tuple[str, str], Adjudication] = {}
    for entry in entries:
        if entry.adjudication_id in superseded:
            continue
        tips[(entry.case_id, entry.axis)] = entry
    return tips


# --------------------------------------------------------------------------- #
# Artifact builders.
# --------------------------------------------------------------------------- #


def entry_row(entry: Adjudication) -> dict[str, Any]:
    """One frozen-shape record entry; ``is_gold`` is always pinned false."""
    return {
        "adjudication_id": entry.adjudication_id,
        "adjudicator_id": entry.adjudicator_id,
        "axis": entry.axis,
        "case_id": entry.case_id,
        "is_gold": False,
        "provenance": entry.provenance,
        "rationale": entry.rationale,
        "resolution": entry.resolution,
        "supersedes": entry.supersedes,
    }


def build_record(
    *,
    world: Any,
    entries: Sequence[Adjudication],
    inventory_keys: frozenset[tuple[str, str]],
    agreement_sha256: str,
) -> dict[str, Any]:
    """The append-only adjudication record, pinned to the frozen agreement score."""
    tips = resolution_tips(entries)
    resolved = [key for key in sorted(inventory_keys) if key in tips]
    unresolved = [key for key in sorted(inventory_keys) if key not in tips]
    return {
        "schema": ADJ_RECORD_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "append_only": True,
        "pre_adjudication_agreement_sha256": agreement_sha256,
        "entry_count": len(entries),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "is_gold": False,
        "promotion": PROMOTION_NONE,
        "adjudicator_provenance": ADJUDICATOR_PROVENANCE,
        "entries": [
            entry_row(entry)
            for entry in sorted(
                entries, key=lambda item: (item.case_id, item.axis, item.adjudication_id)
            )
        ],
        "non_claims": list(world.non_claims),
        "lifecycle": dict(world.lifecycle),
    }


def build_receipt(
    *,
    world: Any,
    agreement_sha256: str,
    record_sha256: str,
    coder_ids: Sequence[str],
    adjudicator_ids: Sequence[str],
    case_count: int,
) -> dict[str, Any]:
    """The pilot receipt: positive proof that two codings and an adjudication exist."""
    return {
        "schema": PILOT_RECEIPT_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "human_pilot_performed": True,
        "coder_count": len(set(coder_ids)),
        "adjudicator_count": len(set(adjudicator_ids)),
        "case_count": case_count,
        "pre_adjudication_agreement_sha256": agreement_sha256,
        "adjudication_record_sha256": record_sha256,
        "promotion": PROMOTION_NONE,
        "non_claims": list(world.non_claims),
        "lifecycle": dict(world.lifecycle),
    }


def assert_record_shape(record: dict[str, Any], contract: Contract) -> None:
    check_closed_keys(record, contract.record_closed_keys, "$record")
    if not isinstance(record.get("entries"), list):
        raise GateError("SCHEMA_KEY_DRIFT", "$record.entries is not a list")
    for index, entry in enumerate(record["entries"]):
        check_closed_keys(entry, contract.record_entry_closed_keys, f"$record.entries[{index}]")


def assert_receipt_shape(receipt: dict[str, Any], contract: Contract) -> None:
    check_closed_keys(receipt, contract.receipt_closed_keys, "$receipt")


# --------------------------------------------------------------------------- #
# The frozen pre-adjudication pair this contour is bound to.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FrozenAgreement:
    """The frozen pre-adjudication score and the separate disagreement inventory."""

    sha256: str
    report: dict[str, Any]
    inventory: dict[str, Any]
    coder_ids: tuple[str, ...]

    @property
    def inventory_keys(self) -> frozenset[tuple[str, str]]:
        return frozenset(
            (str(entry["case_id"]), str(entry["axis"])) for entry in self.inventory["entries"]
        )


def load_frozen_agreement(
    report_path: Path, inventory_path: Path, *, contract: Contract, universe: tuple[str, ...]
) -> FrozenAgreement:
    """Read the frozen T04 pair and prove it is a pre-adjudication score."""
    if not report_path.is_file():
        raise GateError(
            "MISSING_ARTIFACT",
            f"the frozen agreement report {report_path} does not exist: adjudication is pinned to "
            "a pre-adjudication score and cannot run before one is computed",
        )
    if not inventory_path.is_file():
        raise GateError(
            "MISSING_ARTIFACT",
            f"the frozen disagreement inventory {inventory_path} does not exist: adjudication "
            "resolves inventoried disagreements and needs the inventory",
        )
    report_raw = report_path.read_bytes()
    report = INTAKE.load_json_text(report_raw.decode("utf-8"), "agreement report")
    inventory = INTAKE.load_json(inventory_path, "disagreement inventory")
    if not isinstance(report, dict):
        raise GateError("SCHEMA_KEY_DRIFT", "the agreement report is not a JSON object")
    if report.get("schema") != AGREEMENT_REPORT_SCHEMA_ID:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"agreement report schema={report.get('schema')!r} != {AGREEMENT_REPORT_SCHEMA_ID!r}",
        )
    if report.get("pre_adjudication") is not True:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "the agreement report is not pre-adjudication: adjudication is pinned to a score "
            "frozen before it, never to a recomputed one",
        )
    for key, predicate, diagnostic in CLAIM_PINS:
        if key in report and not predicate(report.get(key)):
            raise GateError(
                diagnostic, f"the frozen agreement report carries {key}={report.get(key)!r}"
            )
    if report.get("alpha") is not None:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "the frozen agreement report must keep the pooled alpha pinned null (it publishes "
            "alpha per axis)",
        )
    if report.get("units_total") != contract.units_total:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"agreement report units_total={report.get('units_total')!r} != {contract.units_total}",
        )
    refs = report.get("submission_refs")
    if not isinstance(refs, list) or len(refs) != CODER_COUNT:
        raise GateError(
            "ONE_CODER_ONLY",
            "the frozen agreement report does not name two codings: adjudication over fewer than "
            "two independent coders is refused (RC28-F01)",
        )
    coder_ids = tuple(str(ref.get("coder_id")) for ref in refs if isinstance(ref, dict))
    coder_passes = sorted(int(ref.get("coder_pass") or 0) for ref in refs if isinstance(ref, dict))
    if len(set(coder_ids)) != CODER_COUNT or coder_passes != [1, 2]:
        raise GateError(
            "ONE_CODER_ONLY",
            f"the frozen agreement report names coder_ids={list(coder_ids)} passes={coder_passes}; "
            "two independent coders with distinct ids are required",
        )
    if not isinstance(inventory, dict):
        raise GateError("SCHEMA_KEY_DRIFT", "the disagreement inventory is not a JSON object")
    if inventory.get("schema") != DISAGREEMENT_INVENTORY_SCHEMA_ID:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"disagreement inventory schema={inventory.get('schema')!r} != "
            f"{DISAGREEMENT_INVENTORY_SCHEMA_ID!r}",
        )
    if inventory.get("pre_adjudication") is not True:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "the disagreement inventory is not pre-adjudication: adjudication resolves the "
            "inventory frozen before it",
        )
    entries = inventory.get("entries")
    if not isinstance(entries, list):
        raise GateError("SCHEMA_KEY_DRIFT", "$inventory.entries is not a list")
    if inventory.get("disagreement_count") != len(entries):
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"inventory disagreement_count={inventory.get('disagreement_count')!r} != "
            f"{len(entries)} entries",
        )
    for index, entry in enumerate(entries):
        pointer = f"$inventory.entries[{index}]"
        if not isinstance(entry, dict):
            raise GateError("SCHEMA_KEY_DRIFT", f"{pointer} is not a JSON object")
        check_closed_keys(entry, INVENTORY_ENTRY_CLOSED_KEYS, pointer)
        if entry["axis"] not in contract.axes:
            raise GateError(
                "SCHEMA_KEY_DRIFT",
                f"{pointer}.axis={entry['axis']!r} is not a frozen agreement axis",
            )
        if entry["case_id"] not in universe:
            raise GateError(
                "SCHEMA_KEY_DRIFT",
                f"{pointer}.case_id={entry['case_id']!r} is not a frozen case",
            )
        if entry["pass_1_value"] == entry["pass_2_value"]:
            raise GateError(
                "DENOMINATOR_MISMATCH",
                f"{pointer} records a matching pair: the inventory lists disagreements only",
            )
        if not isinstance(entry["work_family"], str) or not entry["work_family"]:
            raise GateError(
                "DENOMINATOR_MISMATCH", f"{pointer} carries no joined work_family (D480)"
            )
    return FrozenAgreement(
        sha256=INTAKE.sha256_bytes(report_raw),
        report=report,
        inventory=inventory,
        coder_ids=coder_ids,
    )


def check_append_only(
    record_path: Path, *, entries: Sequence[Adjudication], agreement_sha256: str
) -> None:
    """A frozen record may not be re-pinned, and the human corpus may not shrink."""
    if not record_path.is_file():
        return
    previous = INTAKE.load_json(record_path, "existing adjudication record")
    if not isinstance(previous, dict):
        raise GateError("SCHEMA_KEY_DRIFT", "the existing adjudication record is not an object")
    pinned = previous.get("pre_adjudication_agreement_sha256")
    if pinned != agreement_sha256:
        raise GateError(
            "FROZEN_SOURCE_DRIFT",
            f"the frozen agreement report now hashes {agreement_sha256} but the adjudication "
            f"record is pinned to {pinned!r}: a pre-adjudication score is never re-frozen after "
            "adjudication",
        )
    current = {entry.adjudication_id for entry in entries}
    previous_ids = {
        str(entry.get("adjudication_id"))
        for entry in previous.get("entries") or ()
        if isinstance(entry, dict)
    }
    vanished = sorted(previous_ids - current)
    if vanished:
        raise GateError(
            "FROZEN_SOURCE_DRIFT",
            f"the human adjudication corpus is append-only but {len(vanished)} recorded "
            f"entry/entries disappeared, e.g. {vanished[:3]}",
        )


# --------------------------------------------------------------------------- #
# Modes.
# --------------------------------------------------------------------------- #


def report_failures(failures: Failures, summary: str) -> int:
    if failures:
        for diagnostic, detail in failures:
            print(f"FAIL {diagnostic}: {detail}", file=sys.stderr)
        return FAIL_EXIT
    if summary:
        print(summary)
    return 0


def run_adjudication(
    root: Path,
    paths: Any,
    *,
    store_raw: str,
    agreement_raw: str,
    inventory_raw: str,
    record_raw: str,
    receipt_raw: str,
    allow_test_fixtures: bool,
) -> int:
    """Record the human adjudication and the pilot receipt, or refuse."""
    try:
        store = INTAKE.store_policy(root, store_raw, allow_test_fixtures=allow_test_fixtures)
        agreement_target = AGREEMENT.evidence_path(
            root, agreement_raw, "agreement", allow_test_fixtures=allow_test_fixtures
        )
        inventory_target = AGREEMENT.evidence_path(
            root, inventory_raw, "inventory", allow_test_fixtures=allow_test_fixtures
        )
        record_target = AGREEMENT.evidence_path(
            root, record_raw, "record", allow_test_fixtures=allow_test_fixtures
        )
        receipt_target = AGREEMENT.evidence_path(
            root, receipt_raw, "receipt", allow_test_fixtures=allow_test_fixtures
        )
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    # The human gate comes first: an absent drop box never reaches the machinery.
    try:
        files = discover_adjudications(store, agreement_frozen=agreement_target.is_file())
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        if exc.diagnostic in ("HUMAN_PILOT_ABSENT", "NO_ADJUDICATION_INPUT"):
            return ABSENT_EXIT
        return FAIL_EXIT

    failures: Failures = []
    world = INTAKE.load_world(root, paths, failures)
    if world is None or failures:
        return report_failures(failures, "")

    try:
        contract = load_contract(world)
        frozen = load_frozen_agreement(
            agreement_target, inventory_target, contract=contract, universe=world.universe
        )
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    entries = evaluate_store(
        files,
        contract=contract,
        inventory_keys=frozen.inventory_keys,
        universe=world.universe,
        world=world,
        allow_test_fixtures=allow_test_fixtures,
        failures=failures,
    )
    if failures:
        return report_failures(failures, "")
    if not entries:
        return report_failures(
            [("NO_ADJUDICATION_INPUT", "no human adjudication was admitted")], ""
        )

    try:
        check_append_only(record_target, entries=entries, agreement_sha256=frozen.sha256)
        record = build_record(
            world=world,
            entries=entries,
            inventory_keys=frozen.inventory_keys,
            agreement_sha256=frozen.sha256,
        )
        if record["unresolved_count"]:
            for case_id, axis in sorted(frozen.inventory_keys - set(resolution_tips(entries))):
                print(
                    f"UNRESOLVED_NONZERO case={case_id} axis={axis}: no human adjudication "
                    "resolves this inventoried disagreement",
                    file=sys.stderr,
                )
            return report_failures(
                [
                    (
                        "UNRESOLVED_NONZERO",
                        f"{record['unresolved_count']} of {len(frozen.inventory_keys)} inventoried "
                        "disagreement(s) carry no human resolution: a half-resolved pilot is not a "
                        "performed pilot and no adjudication record is published",
                    )
                ],
                "",
            )
        record_payload = AGREEMENT.render(record)
        receipt = build_receipt(
            world=world,
            agreement_sha256=frozen.sha256,
            record_sha256=INTAKE.sha256_bytes(record_payload),
            coder_ids=frozen.coder_ids,
            adjudicator_ids=[entry.adjudicator_id for entry in entries],
            case_count=len(world.universe),
        )
        assert_record_shape(record, contract)
        assert_receipt_shape(receipt, contract)
        guard_no_claims(record, contract.allowed_keys)
        guard_no_claims(receipt, contract.allowed_keys)
        receipt_payload = AGREEMENT.render(receipt)
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    try:
        _write_pair(root, record_target, record_payload, receipt_target, receipt_payload)
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    print(
        f"{RUN_MARKER} entries={record['entry_count']} resolved={record['resolved_count']} "
        f"unresolved={record['unresolved_count']} adjudicators={receipt['adjudicator_count']} "
        f"coders={receipt['coder_count']} case_count={receipt['case_count']} "
        f"agreement_sha256={frozen.sha256[:12]} record={record_raw} receipt={receipt_raw}"
    )
    return 0


def _write_pair(
    root: Path,
    record_target: Path,
    record_payload: bytes,
    receipt_target: Path,
    receipt_payload: bytes,
) -> None:
    """Write both artifacts or neither: a half-written pair is never left behind."""
    guarded_write_bytes(root, record_target, record_payload)
    try:
        guarded_write_bytes(root, receipt_target, receipt_payload)
    except Exception:
        if record_target.exists():
            record_target.unlink()
        raise


def guarded_write_bytes(root: Path, path: Path, payload: bytes) -> None:
    if INTAKE.is_under(path, root / INTAKE.ANNOTATION_PREFIX):
        raise GateError(
            "UNSAFE_PATH",
            f"refusing to write {path} under {INTAKE.ANNOTATION_PREFIX}: the harness never "
            "writes a submission or an adjudication (D474/D476)",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(payload)
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


# --------------------------------------------------------------------------- #
# Offline self-check and its probes.
# --------------------------------------------------------------------------- #


def _entry(
    *,
    adjudication_id: str,
    case_id: str,
    axis: str,
    resolution: str,
    adjudicator_id: str = "adjudicator-1",
    provenance: str = ADJUDICATOR_PROVENANCE,
    rationale: str = "resolved against the closed codebook decision space",
    supersedes: str | None = None,
) -> dict[str, Any]:
    """A well-formed adjudication input in memory (never written)."""
    return {
        "schema": ADJ_INPUT_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "adjudication_id": adjudication_id,
        "adjudicator_id": adjudicator_id,
        "axis": axis,
        "case_id": case_id,
        "resolution": resolution,
        "provenance": provenance,
        "rationale": rationale,
        "supersedes": supersedes,
    }


def _resolution_for(axis: str, contract: Contract) -> str:
    """The first value of the closed space for an axis (probe scaffolding only)."""
    space = contract.space_for(axis)
    return space[0] if space else "reference"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeFailure(message)


def expect_gate(diagnostic: str, call: Callable[[], Any]) -> None:
    try:
        call()
    except GateError as exc:
        if exc.diagnostic != diagnostic:
            raise ProbeFailure(
                f"expected {diagnostic}, raised {exc.diagnostic}: {exc.detail}"
            ) from exc
        return
    raise ProbeFailure(f"expected {diagnostic}, but the probe was accepted")


def _cleanup(root: Path) -> None:
    if not root.exists():
        return
    for child in sorted(root.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    root.rmdir()


def synthetic_inventory(root: Path, world: Any, contract: Contract) -> dict[str, Any]:
    """A deterministic in-memory inventory over the synthetic coding pair.

    Never written anywhere: it exists so the adjudication rules can be probed
    without a human pilot (which this task must not fabricate).
    """
    codings = AGREEMENT.synthetic_codings(world)
    measurements = [AGREEMENT.measure_axis(axis, codings, world.universe) for axis in contract.axes]
    families = load_family_map(root, INTAKE.CASES_REL, world.universe)
    return AGREEMENT.build_inventory(world=world, measurements=measurements, families=families)


def synthetic_report(world: Any, contract: Contract) -> dict[str, Any]:
    """A deterministic in-memory pre-adjudication report naming two coders."""
    codings = AGREEMENT.synthetic_codings(world)
    measurements = [AGREEMENT.measure_axis(axis, codings, world.universe) for axis in contract.axes]
    families = AGREEMENT.load_families(world.root, INTAKE.CASES_REL, world.universe)
    return AGREEMENT.build_report(
        world=world,
        measurements=measurements,
        refs=[
            {
                "coder_id": coder_id,
                "coder_pass": coder_pass,
                "sha256": str(coder_pass) * 64,
                "submission_id": f"m207-s02-submission-pass-{coder_pass}",
            }
            for coder_pass, coder_id in ((1, "coder-alpha"), (2, "coder-beta"))
        ],
        breakdown=AGREEMENT.family_breakdown(world.universe, families),
    )


def contract_probes(root: Path, world: Any, contract: Contract) -> list[tuple[str, str | None]]:
    """Deterministic probes of the frozen contract and the adjudication rules."""
    probes: list[tuple[str, str | None]] = []
    inventory = synthetic_inventory(root, world, contract)
    keys = frozenset((str(entry["case_id"]), str(entry["axis"])) for entry in inventory["entries"])
    ordered = sorted(keys)
    target = ordered[0]
    other = ordered[1]
    match_key = next(
        (world.universe[0], axis) for axis in contract.axes if (world.universe[0], axis) not in keys
    )

    def validate(envelope: dict[str, Any], name: str = "adjudication.json") -> Adjudication:
        return validate_adjudication(
            envelope,
            label=name,
            file_name=name,
            contract=contract,
            inventory_keys=keys,
            universe=world.universe,
            world=world,
            allow_test_fixtures=True,
        )

    def build(
        *,
        case_id: str = target[0],
        axis: str = target[1],
        resolution: str | None = None,
    ) -> dict[str, Any]:
        return _entry(
            adjudication_id="m207-s02-adjudication-probe",
            case_id=case_id,
            axis=axis,
            resolution=resolution if resolution is not None else _resolution_for(axis, contract),
        )

    def adjudication_for_axis(axis: str, resolution: str | None = None) -> dict[str, Any]:
        key = next((item for item in ordered if item[1] == axis), None)
        if key is None:
            raise ProbeFailure(f"the synthetic pair produced no {axis!r} disagreement")
        return build(case_id=key[0], axis=axis, resolution=resolution)

    def full_corpus() -> list[Adjudication]:
        return [
            validate(
                _entry(
                    adjudication_id=f"m207-s02-adjudication-{index}",
                    case_id=case_id,
                    axis=axis,
                    resolution=_resolution_for(axis, contract),
                ),
                f"adjudication-{index}.json",
            )
            for index, (case_id, axis) in enumerate(ordered, start=1)
        ]

    def run(name: str, call: Callable[[], None]) -> None:
        try:
            call()
        except ProbeFailure as exc:
            probes.append((name, str(exc)))
        except GateError as exc:
            probes.append((name, f"unexpected {exc.diagnostic}: {exc.detail}"))
        else:
            probes.append((name, None))

    def resolution_space_covers_every_axis() -> None:
        require(
            sorted(contract.resolution_space) == sorted(contract.axes),
            "the resolution space must cover exactly the frozen agreement axes",
        )
        require(
            len(contract.resolution_space) == 11,
            f"expected eleven resolution axes, saw {len(contract.resolution_space)}",
        )
        require(
            contract.space_for(SPAN_EXACT_AXIS) == (SPAN_PASS_ONE, SPAN_PASS_TWO),
            "the span axis names one of the two committed coder spans, never a third",
        )
        require(
            contract.space_for(SLOT_AXIS_PREFIX + "date") == SLOT_PASS_VALUES,
            "the slot axes carry the closed presence poles",
        )

    def rationale_bound_matches_the_protocol() -> None:
        require(
            contract.rationale_max_chars == RATIONALE_MAX_CHARS,
            f"rationale bound {contract.rationale_max_chars} != {RATIONALE_MAX_CHARS}",
        )

    def adjudication_for_a_match_is_refused() -> None:
        expect_gate(
            "ADJUDICATION_NOT_A_DISAGREEMENT",
            lambda: validate(build(case_id=match_key[0], axis=match_key[1])),
        )

    def unknown_case_is_refused() -> None:
        expect_gate("SCHEMA_KEY_DRIFT", lambda: validate(build(case_id="m207-s01-case-9999")))

    def unknown_axis_is_refused() -> None:
        expect_gate("SCHEMA_KEY_DRIFT", lambda: validate(build(axis="slot_nope")))

    def resolution_out_of_space_is_refused() -> None:
        expect_gate("RESOLUTION_OUT_OF_SPACE", lambda: validate(build(resolution="maybe")))

    def new_decision_value_is_refused() -> None:
        expect_gate(
            "RESOLUTION_OUT_OF_SPACE",
            lambda: validate(adjudication_for_axis(REFERENCE_DECISION_AXIS, "uncertain")),
        )

    def third_span_is_refused() -> None:
        expect_gate(
            "RESOLUTION_OUT_OF_SPACE",
            lambda: validate(adjudication_for_axis(SPAN_EXACT_AXIS, "span_pass_3")),
        )

    def model_adjudication_is_refused() -> None:
        expect_gate(
            "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
            lambda: validate(dict(build(), provenance="model")),
        )

    def rule_seed_adjudication_is_refused() -> None:
        expect_gate(
            "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
            lambda: validate(dict(build(), provenance="rule-seed")),
        )

    def is_gold_claim_is_refused() -> None:
        expect_gate("IS_GOLD_CLAIM", lambda: validate(dict(build(), is_gold=True)))

    def promotion_claim_is_refused() -> None:
        expect_gate("PROMOTION_CLAIM", lambda: validate(dict(build(), promotion="promoted")))

    def threshold_is_refused() -> None:
        expect_gate("THRESHOLD_REQUESTED", lambda: validate(dict(build(), threshold=0.8)))

    def classification_is_refused() -> None:
        expect_gate(
            "CLASSIFICATION_REQUESTED", lambda: validate(dict(build(), classification="pass"))
        )

    def authority_claim_is_refused() -> None:
        expect_gate("AUTHORITY_CLAIM", lambda: validate(dict(build(), authority="authoritative")))

    def suggestion_status_claim_is_refused() -> None:
        expect_gate(
            "AUTHORITY_CLAIM", lambda: validate(dict(build(), suggestion_status="provided"))
        )

    def model_invoked_is_refused() -> None:
        expect_gate("MODEL_INVOKED", lambda: validate(dict(build(), model_invoked=True)))

    def leak_token_in_rationale_is_refused() -> None:
        expect_gate(
            "LEAK_FORBIDDEN_KEY",
            lambda: validate(dict(build(), rationale="the expected reference was predictable")),
        )

    def extra_input_key_is_refused() -> None:
        document = build()
        document["confidence"] = 0.9
        expect_gate("SCHEMA_KEY_DRIFT", lambda: validate(document))

    def missing_input_key_is_refused() -> None:
        document = build()
        document.pop("resolution")
        expect_gate("SCHEMA_KEY_DRIFT", lambda: validate(document))

    def wrong_input_schema_is_refused() -> None:
        document = build()
        document["schema"] = ADJ_RECORD_SCHEMA_ID
        expect_gate("SCHEMA_KEY_DRIFT", lambda: validate(document))

    def wrong_input_schema_version_is_refused() -> None:
        document = build()
        document["schema_version"] = 2
        expect_gate("SCHEMA_KEY_DRIFT", lambda: validate(document))

    def rationale_too_long_is_refused() -> None:
        expect_gate(
            "RATIONALE_NOT_BOUNDED",
            lambda: validate(dict(build(), rationale="x" * (RATIONALE_MAX_CHARS + 1))),
        )

    def rationale_multiline_is_refused() -> None:
        expect_gate(
            "RATIONALE_NOT_BOUNDED",
            lambda: validate(dict(build(), rationale="resolved in two lines\nactually three")),
        )

    def rationale_empty_is_refused() -> None:
        expect_gate("RATIONALE_NOT_BOUNDED", lambda: validate(dict(build(), rationale="")))

    def fixture_marked_input_is_refused_in_product_mode() -> None:
        expect_gate(
            "TEST_FIXTURE_IN_STORE",
            lambda: validate_adjudication(
                build(),
                label="adjudication-probe.json",
                file_name="adjudication-probe.json",
                contract=contract,
                inventory_keys=keys,
                universe=world.universe,
                world=world,
                allow_test_fixtures=False,
            ),
        )

    def forged_lifecycle_marker_is_refused() -> None:
        expect_gate(
            "MISSING_LIFECYCLE_MARKER",
            lambda: validate(dict(build(), lifecycle={"human_adoption": "adopted"})),
        )

    def supersedes_unknown_is_refused() -> None:
        document = build()
        document["supersedes"] = "m207-s02-adjudication-nowhere"
        expect_gate("SUPERSEDES_UNKNOWN", lambda: check_supersession([validate(document)]))

    def supersedes_self_is_refused() -> None:
        document = build()
        document["supersedes"] = document["adjudication_id"]
        expect_gate("SUPERSEDES_UNKNOWN", lambda: check_supersession([validate(document)]))

    def supersedes_cycle_is_refused() -> None:
        first = build()
        second = build()
        first["adjudication_id"] = "m207-s02-adjudication-cycle-a"
        second["adjudication_id"] = "m207-s02-adjudication-cycle-b"
        first["supersedes"] = second["adjudication_id"]
        second["supersedes"] = first["adjudication_id"]
        entries = [validate(first), validate(second)]
        expect_gate("SCHEMA_KEY_DRIFT", lambda: check_supersession(entries))

    def supersedes_across_disagreements_is_refused() -> None:
        first = build(case_id=target[0], axis=target[1])
        second = build(case_id=other[0], axis=other[1])
        first["adjudication_id"] = "m207-s02-adjudication-one"
        second["adjudication_id"] = "m207-s02-adjudication-two"
        second["supersedes"] = first["adjudication_id"]
        entries = [validate(first), validate(second)]
        expect_gate("SCHEMA_KEY_DRIFT", lambda: check_supersession(entries))

    def supersede_chain_resolves_the_disagreement() -> None:
        first = build()
        first["adjudication_id"] = "m207-s02-adjudication-v1"
        second = build()
        second["adjudication_id"] = "m207-s02-adjudication-v2"
        second["supersedes"] = first["adjudication_id"]
        entries = [validate(first), validate(second)]
        check_supersession(entries)
        tips = resolution_tips(entries)
        require(
            len(entries) == 2,
            "both the superseded and the superseding entry are retained (append-only)",
        )
        require(
            tips[(target[0], target[1])].adjudication_id == "m207-s02-adjudication-v2",
            "the chain tip is the adjudication nothing supersedes",
        )

    def record_matches_the_frozen_shape() -> None:
        record = build_record(
            world=world,
            entries=full_corpus(),
            inventory_keys=keys,
            agreement_sha256="a" * 64,
        )
        assert_record_shape(record, contract)
        require(
            record["pre_adjudication_agreement_sha256"] == "a" * 64,
            "the record must pin the frozen agreement digest",
        )
        require(record["append_only"] is True, "the record must stay append-only")
        require(record["is_gold"] is False, "the record must never claim gold")
        require(record["promotion"] == PROMOTION_NONE, "the record must pin promotion none")
        require(
            record["adjudicator_provenance"] == ADJUDICATOR_PROVENANCE,
            "the record must carry the human adjudicator provenance",
        )
        require(
            record["entry_count"] == len(keys) and record["resolved_count"] == len(keys),
            "a full corpus resolves every inventoried disagreement",
        )
        require(record["unresolved_count"] == 0, "a full corpus leaves nothing unresolved")

    def partial_corpus_is_counted() -> None:
        record = build_record(
            world=world,
            entries=full_corpus()[:1],
            inventory_keys=keys,
            agreement_sha256="b" * 64,
        )
        require(
            record["unresolved_count"] == len(keys) - 1,
            f"unresolved={record['unresolved_count']} instead of {len(keys) - 1}: open "
            "disagreements are counted, never silently closed",
        )

    def receipt_matches_the_frozen_shape() -> None:
        receipt = build_receipt(
            world=world,
            agreement_sha256="a" * 64,
            record_sha256="c" * 64,
            coder_ids=["coder-alpha", "coder-beta"],
            adjudicator_ids=["adjudicator-1"],
            case_count=len(world.universe),
        )
        assert_receipt_shape(receipt, contract)
        require(receipt["human_pilot_performed"] is True, "the receipt states the pilot happened")
        require(receipt["coder_count"] == CODER_COUNT, "the receipt counts two coders")
        require(receipt["adjudicator_count"] >= MIN_ADJUDICATOR_COUNT, "at least one adjudicator")
        require(receipt["case_count"] == CASE_COUNT, "the receipt counts the frozen 40 cases")
        require(receipt["promotion"] == PROMOTION_NONE, "the receipt pins promotion none")

    def derived_documents_pass_the_claim_guards() -> None:
        record = build_record(
            world=world,
            entries=full_corpus(),
            inventory_keys=keys,
            agreement_sha256="a" * 64,
        )
        receipt = build_receipt(
            world=world,
            agreement_sha256="a" * 64,
            record_sha256="c" * 64,
            coder_ids=["coder-alpha", "coder-beta"],
            adjudicator_ids=["adjudicator-1"],
            case_count=len(world.universe),
        )
        guard_no_claims(record, contract.allowed_keys)
        guard_no_claims(receipt, contract.allowed_keys)

    def record_gold_claim_is_refused() -> None:
        record = build_record(
            world=world,
            entries=full_corpus(),
            inventory_keys=keys,
            agreement_sha256="a" * 64,
        )
        record["is_gold"] = True
        expect_gate("IS_GOLD_CLAIM", lambda: guard_no_claims(record, contract.allowed_keys))

    def record_promotion_claim_is_refused() -> None:
        record = build_record(
            world=world,
            entries=full_corpus(),
            inventory_keys=keys,
            agreement_sha256="a" * 64,
        )
        record["promotion"] = "gold"
        expect_gate("PROMOTION_CLAIM", lambda: guard_no_claims(record, contract.allowed_keys))

    def record_extra_key_is_refused() -> None:
        record = build_record(
            world=world,
            entries=full_corpus(),
            inventory_keys=keys,
            agreement_sha256="a" * 64,
        )
        record["per_aspect_rates"] = {}
        expect_gate(
            "SCHEMA_KEY_DRIFT",
            lambda: check_closed_keys(record, contract.record_closed_keys, "$record"),
        )

    def dropped_record_key_is_refused() -> None:
        record = build_record(
            world=world,
            entries=full_corpus(),
            inventory_keys=keys,
            agreement_sha256="a" * 64,
        )
        record.pop("unresolved_count")
        expect_gate(
            "SCHEMA_KEY_DRIFT",
            lambda: check_closed_keys(record, contract.record_closed_keys, "$record"),
        )

    def diagnostics_table_is_closed() -> None:
        frozen = set(world.schemas.get("diagnostics") or ())
        missing = [name for name in LOCAL_DIAGNOSTICS if name not in frozen]
        require(not missing, f"diagnostics absent from the frozen table: {missing}")

    def report_pre_adjudication_is_required() -> None:
        report = synthetic_report(world, contract)
        require(
            report["pre_adjudication"] is True and report["alpha"] is None,
            "the synthetic pre-adjudication report must stay pre-adjudication with a null alpha",
        )
        require(
            len(report["submission_refs"]) == CODER_COUNT,
            "the synthetic report must name two codings",
        )

    def annotation_write_is_refused() -> None:
        target = root / INTAKE.ANNOTATION_PREFIX / "m207-s02-adjudication-probe.json"
        expect_gate("UNSAFE_PATH", lambda: guarded_write_bytes(root, target, b"{}\n"))
        expect_gate(
            "UNSAFE_PATH",
            lambda: AGREEMENT.evidence_path(
                root, INTAKE.ANNOTATION_PREFIX + "probe.json", "record", allow_test_fixtures=False
            ),
        )
        require(not target.exists(), "the writer created a file under prd/annotation/")

    def store_prefix_lock_is_enforced() -> None:
        for raw in (
            "some/other/dir",
            "crates/probe-store",
            "prd/annotation/../annotation/m207-s02-adjudications",
            "prd\\annotation\\m207-s02-adjudications",
            "/tmp/m207-s02-adjudications",
        ):
            expect_gate(
                "UNSAFE_PATH",
                lambda raw=raw: INTAKE.store_policy(root, raw, allow_test_fixtures=False),
            )

    def absent_store_is_refused(tmp_root: Path) -> None:
        tmp_root.mkdir(parents=True, exist_ok=True)
        empty = tmp_root / "empty-store"
        empty.mkdir()
        for candidate in (empty, tmp_root / "missing-store"):
            expect_gate(
                "HUMAN_PILOT_ABSENT",
                lambda candidate=candidate: discover_adjudications(
                    candidate, agreement_frozen=False
                ),
            )
            expect_gate(
                "NO_ADJUDICATION_INPUT",
                lambda candidate=candidate: discover_adjudications(
                    candidate, agreement_frozen=True
                ),
            )

    run("resolution_space_covers_every_axis", resolution_space_covers_every_axis)
    run("rationale_bound_matches_the_protocol", rationale_bound_matches_the_protocol)
    run("adjudication_for_a_match_is_refused", adjudication_for_a_match_is_refused)
    run("unknown_case_is_refused", unknown_case_is_refused)
    run("unknown_axis_is_refused", unknown_axis_is_refused)
    run("resolution_out_of_space_is_refused", resolution_out_of_space_is_refused)
    run("new_decision_value_is_refused", new_decision_value_is_refused)
    run("third_span_is_refused", third_span_is_refused)
    run("model_adjudication_is_refused", model_adjudication_is_refused)
    run("rule_seed_adjudication_is_refused", rule_seed_adjudication_is_refused)
    run("is_gold_claim_is_refused", is_gold_claim_is_refused)
    run("promotion_claim_is_refused", promotion_claim_is_refused)
    run("threshold_is_refused", threshold_is_refused)
    run("classification_is_refused", classification_is_refused)
    run("authority_claim_is_refused", authority_claim_is_refused)
    run("suggestion_status_claim_is_refused", suggestion_status_claim_is_refused)
    run("model_invoked_is_refused", model_invoked_is_refused)
    run("leak_token_in_rationale_is_refused", leak_token_in_rationale_is_refused)
    run("extra_input_key_is_refused", extra_input_key_is_refused)
    run("missing_input_key_is_refused", missing_input_key_is_refused)
    run("wrong_input_schema_is_refused", wrong_input_schema_is_refused)
    run("wrong_input_schema_version_is_refused", wrong_input_schema_version_is_refused)
    run("rationale_too_long_is_refused", rationale_too_long_is_refused)
    run("rationale_multiline_is_refused", rationale_multiline_is_refused)
    run("rationale_empty_is_refused", rationale_empty_is_refused)
    run(
        "fixture_marked_input_is_refused_in_product_mode",
        fixture_marked_input_is_refused_in_product_mode,
    )
    run("forged_lifecycle_marker_is_refused", forged_lifecycle_marker_is_refused)
    run("supersedes_unknown_is_refused", supersedes_unknown_is_refused)
    run("supersedes_self_is_refused", supersedes_self_is_refused)
    run("supersedes_cycle_is_refused", supersedes_cycle_is_refused)
    run("supersedes_across_disagreements_is_refused", supersedes_across_disagreements_is_refused)
    run("supersede_chain_resolves_the_disagreement", supersede_chain_resolves_the_disagreement)
    run("record_matches_the_frozen_shape", record_matches_the_frozen_shape)
    run("partial_corpus_is_counted", partial_corpus_is_counted)
    run("receipt_matches_the_frozen_shape", receipt_matches_the_frozen_shape)
    run("derived_documents_pass_the_claim_guards", derived_documents_pass_the_claim_guards)
    run("record_gold_claim_is_refused", record_gold_claim_is_refused)
    run("record_promotion_claim_is_refused", record_promotion_claim_is_refused)
    run("record_extra_key_is_refused", record_extra_key_is_refused)
    run("dropped_record_key_is_refused", dropped_record_key_is_refused)
    run("diagnostics_table_is_closed", diagnostics_table_is_closed)
    run("report_pre_adjudication_is_required", report_pre_adjudication_is_required)
    run("annotation_write_is_refused", annotation_write_is_refused)
    run("store_prefix_lock_is_enforced", store_prefix_lock_is_enforced)

    tmp_root = Path(tempfile.mkdtemp(prefix="m207-s02-adjudicate-probe-"))
    try:
        run("absent_store_is_refused", lambda: absent_store_is_refused(tmp_root))
    finally:
        _cleanup(tmp_root)
    return probes


def fixture_run_probes(
    root: Path, paths: Any, world: Any, contract: Contract
) -> list[tuple[str, str | None]]:
    """Run the whole ``run`` contour on a synthetic store outside the repository."""
    probes: list[tuple[str, str | None]] = []
    tmp_root = Path(tempfile.mkdtemp(prefix="m207-s02-adjudicate-fixture-"))
    try:
        inventory = synthetic_inventory(root, world, contract)
        report = synthetic_report(world, contract)
        report_path = tmp_root / "agreement-report.json"
        inventory_path = tmp_root / "disagreement-inventory.json"
        report_path.write_bytes(AGREEMENT.render(report))
        inventory_path.write_bytes(AGREEMENT.render(inventory))
        keys = sorted((str(entry["case_id"]), str(entry["axis"])) for entry in inventory["entries"])
        if not keys:
            probes.append(
                ("fixture_pair_is_a_disagreement", "the synthetic pair produced no disagreement")
            )
            return probes
        probes.append(("fixture_pair_is_a_disagreement", None))

        def full_entries(adjudicator_id: str = "adjudicator-1") -> list[dict[str, Any]]:
            return [
                _entry(
                    adjudication_id=f"m207-s02-adjudication-{index}",
                    case_id=case_id,
                    axis=axis,
                    resolution=_resolution_for(axis, contract),
                    adjudicator_id=adjudicator_id,
                )
                for index, (case_id, axis) in enumerate(keys, start=1)
            ]

        def store_with(entries: Sequence[dict[str, Any]], name: str) -> Path:
            store = tmp_root / name
            store.mkdir(parents=True, exist_ok=True)
            for index, envelope in enumerate(entries, start=1):
                (store / f"adjudication-probe-{index}.json").write_bytes(AGREEMENT.render(envelope))
            return store

        def run_once(
            store: Path,
            record_name: str,
            receipt_name: str,
            *,
            report_source: Path | None = None,
            inventory_source: Path | None = None,
        ) -> tuple[int, Path, Path]:
            record = tmp_root / record_name
            receipt = tmp_root / receipt_name
            # The offline check prints one marker line: the refusal diagnostics a
            # probe expects are asserted by exit code, not echoed as check noise.
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                code = run_adjudication(
                    root,
                    paths,
                    store_raw=str(store),
                    agreement_raw=str(report_source or report_path),
                    inventory_raw=str(inventory_source or inventory_path),
                    record_raw=str(record),
                    receipt_raw=str(receipt),
                    allow_test_fixtures=True,
                )
            return code, record, receipt

        store = store_with(full_entries(), "full-store")
        code, record, receipt = run_once(store, "record.json", "receipt.json")
        if code != 0 or not record.is_file() or not receipt.is_file():
            probes.append(
                (
                    "fixture_full_corpus_is_recorded",
                    f"exit={code} record={record.is_file()} receipt={receipt.is_file()}",
                )
            )
            return probes
        probes.append(("fixture_full_corpus_is_recorded", None))

        first_record = record.read_bytes()
        code_again, record_again, receipt_again = run_once(
            store, "record-again.json", "receipt-again.json"
        )
        probes.append(
            (
                "fixture_run_is_deterministic",
                None
                if code_again == 0
                and record_again.is_file()
                and receipt_again.is_file()
                and record_again.read_bytes() == first_record
                else "the same human corpus produced different record bytes",
            )
        )
        record_document = json.loads(record.read_text(encoding="utf-8"))
        receipt_document = json.loads(receipt.read_text(encoding="utf-8"))
        report_digest = INTAKE.sha256_bytes(report_path.read_bytes())
        probes.append(
            (
                "fixture_record_pins_the_agreement_report",
                None
                if record_document["pre_adjudication_agreement_sha256"] == report_digest
                else "the record is not pinned to the frozen agreement report bytes",
            )
        )
        probes.append(
            (
                "fixture_receipt_pins_the_record",
                None
                if receipt_document["adjudication_record_sha256"]
                == INTAKE.sha256_bytes(first_record)
                else "the receipt does not pin the adjudication record bytes",
            )
        )
        probes.append(
            (
                "fixture_receipt_states_the_human_pilot",
                None
                if receipt_document["human_pilot_performed"] is True
                and receipt_document["coder_count"] == CODER_COUNT
                and receipt_document["adjudicator_count"] >= MIN_ADJUDICATOR_COUNT
                and receipt_document["case_count"] == CASE_COUNT
                and receipt_document["promotion"] == PROMOTION_NONE
                else f"receipt={receipt_document}",
            )
        )
        probes.append(
            (
                "fixture_record_is_append_only_and_not_gold",
                None
                if record_document["append_only"] is True
                and record_document["is_gold"] is False
                and record_document["promotion"] == PROMOTION_NONE
                and record_document["unresolved_count"] == 0
                and record_document["entry_count"] == len(keys)
                and record_document["resolved_count"] == len(keys)
                else f"record={record_document}",
            )
        )
        probes.append(
            (
                "fixture_record_resolutions_come_from_the_closed_space",
                None
                if all(
                    entry["resolution"] in contract.space_for(entry["axis"])
                    for entry in record_document["entries"]
                )
                else "a record entry left the closed per-axis resolution space",
            )
        )

        def refused(
            name: str, entries: Sequence[dict[str, Any]], suffix: str
        ) -> tuple[str, str | None]:
            code, recorded, receipted = run_once(
                store_with(entries, f"{suffix}-store"),
                f"{suffix}-record.json",
                f"{suffix}-receipt.json",
            )
            return (
                name,
                None
                if code == FAIL_EXIT and not recorded.exists() and not receipted.exists()
                else f"exit={code} record={recorded.exists()} receipt={receipted.exists()}",
            )

        probes.append(
            refused(
                "fixture_model_adjudication_is_refused",
                [dict(entry, provenance="model") for entry in full_entries()],
                "model",
            )
        )
        probes.append(
            refused(
                "fixture_is_gold_is_refused",
                [dict(entry, is_gold=True) for entry in full_entries()],
                "gold",
            )
        )
        probes.append(
            refused(
                "fixture_promotion_is_refused",
                [dict(entry, promotion="gold") for entry in full_entries()],
                "promo",
            )
        )
        probes.append(
            refused(
                "fixture_resolution_out_of_space_is_refused",
                [dict(entry, resolution="maybe") for entry in full_entries()],
                "space",
            )
        )
        probes.append(
            refused(
                "fixture_not_a_disagreement_is_refused",
                [
                    dict(entry, case_id=world.universe[0], axis=REFERENCE_DECISION_AXIS)
                    for entry in full_entries()[:1]
                ],
                "match",
            )
        )
        probes.append(
            refused(
                "fixture_supersedes_unknown_is_refused",
                [
                    dict(entry, supersedes="m207-s02-adjudication-nowhere")
                    for entry in full_entries()[:1]
                ],
                "supersedes",
            )
        )
        probes.append(
            refused("fixture_unresolved_corpus_is_refused", full_entries()[:1], "partial")
        )

        # Append-only: a corpus that no longer carries a recorded entry is refused.
        shrink_store = store_with(full_entries()[:-1], "shrunken-store")
        code, recorded, receipted = run_once(shrink_store, "record.json", "receipt.json")
        probes.append(
            (
                "fixture_shrunk_corpus_is_refused",
                None
                if code == FAIL_EXIT and record.read_bytes() == first_record
                else f"exit={code}: a recorded adjudication disappeared without being refused",
            )
        )

        # Pin drift: the frozen pre-adjudication score is mutated after adjudication.
        drifted_report = tmp_root / "report-drifted.json"
        drifted_report.write_bytes(report_path.read_bytes())
        code, drifted_record, drifted_receipt = run_once(
            store, "drift-record.json", "drift-receipt.json", report_source=drifted_report
        )
        first_drift_record = drifted_record.read_bytes() if drifted_record.is_file() else b""
        first_drift_receipt = drifted_receipt.read_bytes() if drifted_receipt.is_file() else b""
        drifted_report.write_bytes(drifted_report.read_bytes() + b"\n")
        code_after, drifted_record_after, drifted_receipt_after = run_once(
            store, "drift-record.json", "drift-receipt.json", report_source=drifted_report
        )
        probes.append(
            (
                "fixture_frozen_report_drift_is_refused",
                None
                if code == 0
                and first_drift_record
                and first_drift_receipt
                and code_after == FAIL_EXIT
                and drifted_record_after.read_bytes() == first_drift_record
                and drifted_receipt_after.read_bytes() == first_drift_receipt
                else f"first={code} second={code_after}: a mutated agreement report re-pinned the "
                "frozen adjudication",
            )
        )

        empty = tmp_root / "empty-store"
        empty.mkdir()
        code, recorded, receipted = run_once(empty, "empty-record.json", "empty-receipt.json")
        probes.append(
            (
                "fixture_empty_store_is_absent",
                None
                if code == ABSENT_EXIT and not recorded.exists() and not receipted.exists()
                else f"exit={code}: an empty adjudication store must write nothing",
            )
        )
        missing = tmp_root / "missing-store"
        code, recorded, receipted = run_once(missing, "missing-record.json", "missing-receipt.json")
        probes.append(
            (
                "fixture_missing_store_is_absent",
                None
                if code == ABSENT_EXIT and not recorded.exists() and not receipted.exists()
                else f"exit={code}: a missing adjudication store must write nothing",
            )
        )
    finally:
        _cleanup(tmp_root)
    return probes


def run_check(root: Path, paths: Any, *, allow_test_fixtures: bool) -> int:
    failures: Failures = []
    world = INTAKE.load_world(root, paths, failures)
    if world is None or failures:
        return report_failures(failures, "")
    try:
        contract = load_contract(world)
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    probes = contract_probes(root, world, contract)
    if allow_test_fixtures:
        probes.extend(fixture_run_probes(root, paths, world, contract))
    failed = [(name, detail) for name, detail in probes if detail is not None]
    if failed:
        for name, detail in failed:
            print(f"FAIL PROBE_FAILED: probe {name} failed: {detail}", file=sys.stderr)
        return FAIL_EXIT

    print(
        f"{MARKER} axes={len(contract.axes)} units_total={contract.units_total} "
        f"diagnostics={len(LOCAL_DIAGNOSTICS)} probes={len(probes)} "
        f"resolution_axes={len(contract.resolution_space)} "
        f"rationale_max_chars={contract.rationale_max_chars} "
        f"fixtures={'run' if allow_test_fixtures else 'in-memory'} store=product-locked"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "run"],
        help="'check' self-checks the contour read-only; 'run' records the human adjudication "
        "against the frozen pre-adjudication score",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--store", default=STORE_REL, help="human adjudication drop box (D480)")
    parser.add_argument(
        "--agreement",
        default=AGREEMENT.REPORT_REL,
        help="frozen pre-adjudication agreement report",
    )
    parser.add_argument(
        "--inventory",
        default=AGREEMENT.INVENTORY_REL,
        help="frozen disagreement inventory the adjudication resolves",
    )
    parser.add_argument("--record", default=RECORD_REL, help="derived adjudication record path")
    parser.add_argument("--receipt", default=RECEIPT_REL, help="derived pilot receipt path")
    parser.add_argument(
        "--allow-test-fixtures",
        action="store_true",
        help="run synthetic fixtures outside the product tree (never inside it)",
    )
    parser.add_argument("--cases", default=INTAKE.CASES_REL, help="frozen S01 pilot case manifest")
    parser.add_argument("--kit-pass1", default=INTAKE.KIT_PASS1_REL, help="frozen pass-1 coder kit")
    parser.add_argument("--kit-pass2", default=INTAKE.KIT_PASS2_REL, help="frozen pass-2 coder kit")
    parser.add_argument("--schemas", default=INTAKE.SCHEMAS_REL, help="frozen S02 closed schemas")
    parser.add_argument(
        "--s01-schemas", default=INTAKE.S01_SCHEMAS_REL, help="frozen S01 closed schemas"
    )
    parser.add_argument(
        "--fixture-dir", default=INTAKE.FIXTURE_DIR_REL, help="frozen fragment fixture dir"
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"FAIL MISSING_ARTIFACT: root {root} is not a directory", file=sys.stderr)
        return FAIL_EXIT
    paths = INTAKE.PathsLike(
        cases=args.cases,
        kit_pass1=args.kit_pass1,
        kit_pass2=args.kit_pass2,
        schemas=args.schemas,
        s01_schemas=args.s01_schemas,
        fixture_dir=args.fixture_dir,
    )
    if args.mode == "run":
        return run_adjudication(
            root,
            paths,
            store_raw=args.store,
            agreement_raw=args.agreement,
            inventory_raw=args.inventory,
            record_raw=args.record,
            receipt_raw=args.receipt,
            allow_test_fixtures=args.allow_test_fixtures,
        )
    return run_check(root, paths, allow_test_fixtures=args.allow_test_fixtures)


if __name__ == "__main__":
    raise SystemExit(main())
