#!/usr/bin/env python3
"""Frozen-evaluation protocol and closed-schema gate for the M207 S03 contour (T01).

This is an offline, fail-closed evidence gate.  It binds six frozen inputs and two
S03 artifacts:

* the frozen M199 annotation protocol (sha256-pinned), whose section 5 fixes the
  closed slot space;
* ``prd/annotation/m207-s01-codebook.md`` and
  ``prd/annotation/m207-s01-schemas.json`` -- the frozen S01 codebook and closed
  schemas, whose ``m207-s01-coding-submission/v1`` form S03 reuses **verbatim**;
* ``prd/migration/rust-evidence/m207-s01-pilot-cases.json`` -- the 40 frozen cases;
* ``prd/annotation/m207-s02-coder-protocol.md`` and
  ``prd/annotation/m207-s02-schemas.json`` -- the frozen S02 protocol and its
  eleven-axis agreement space, from which the six S03 aspects are derived;
* ``prd/annotation/m207-s03-eval-protocol.md`` -- the frozen S03 protocol;
* ``prd/annotation/m207-s03-schemas.json`` -- the five closed S03 schemas.

The gate proves, against the frozen sources rather than against prose:

* the S03 slot space is exactly the S01 / M199 section-5 set -- no ninth slot, no
  schema-version bump, and the submission form is not redefined;
* the ``aspect_table`` measures all six RC28-F15 aspects separately, each with a
  non-empty denominator rule, a denominator unit from a closed vocabulary and
  named exclusion reasons; the union of the aspect source axes is exactly the
  eleven frozen S02 axes, so no axis is ignored and no axis is invented;
* the denominator rule (D489) cannot publish a value without a positive
  denominator, cannot impute ``0.0``/``1.0`` from an empty denominator and
  requires full coverage for a perfect value;
* every stratum is published (provider ``consultant|garant|unknown`` and
  Work-family ``holdout|dev``); an empty stratum is ``not-measured`` and may not be
  dropped;
* no closed key set, at any nesting depth or inside a ``*_keys`` array, mints a
  predicted-answer key (``label``/``expected``/``answer``/``prediction``/``gold``/
  ``capture``) or a rule-seed field, and no tracked artifact carries a wall-clock
  key;
* no surface claims authority or gold, invokes a model, requests a classification,
  sets a threshold or promotes a label; ``is_gold`` is admitted only where it is
  pinned ``false``;
* abstention stays a separate outcome, disjoint from the reference decision;
* no S03 schema id collides with an S01, S02, ``npa-c5-*`` or ``npa-quality-*`` id;
* the lifecycle markers, the non-claims and the bounded protocol tag are present
  and exact.

No metric is computed, inferred or repaired here: this gate only reads the frozen
artifacts and rejects drift.  ``check`` prints exactly the marker
``M207_S03_SCHEMAS_OK``; ``selftest`` additionally proves the named negative paths
(including a real ``FROZEN_SOURCE_DRIFT`` against a mutated frozen copy) and prints
``M207_S03_SCHEMAS_SELFTEST_OK``.  Every failure is a non-zero exit with a named
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

MARKER = "M207_S03_SCHEMAS_OK"
SELFTEST_MARKER = "M207_S03_SCHEMAS_SELFTEST_OK"

SCHEMA_ID = "m207-s03-eval-schemas/v1"
SCHEMA_VERSION = 1
PROTOCOL_ID = "m207-s03-eval-protocol/v1"
SUBMISSION_SCHEMA_ID = "m207-s01-coding-submission/v1"
SUBMISSION_SCHEMA_REUSED = True

PROTOCOL_REL = "prd/annotation/m207-s03-eval-protocol.md"
SCHEMAS_REL = "prd/annotation/m207-s03-schemas.json"
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
S02_PROTOCOL_REL = "prd/annotation/m207-s02-coder-protocol.md"
S02_SCHEMAS_REL = "prd/annotation/m207-s02-schemas.json"
S01_CODEBOOK_CONTRACT_HEADING = "Machine-readable codebook contract"

# Every frozen input S03 rests on, pinned by content digest.  A byte of drift in
# any of them stops the gate: S03 measures against a frozen reference, so the
# codebook, the S01 schemas, the case manifest, the S02 protocol, the S02 schema
# and the M199 slot space must not move underneath a measurement.
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
    "m207_s02_protocol": (
        S02_PROTOCOL_REL,
        "763de0f998b772afd85373e438da0b1b6b2a6435d761e67f06177f4b0b1fbc32",
    ),
    "m207_s02_schemas": (
        S02_SCHEMAS_REL,
        "ef438bb5171a8b58f43a8bc4bc2d9a875877da40943ef28e1337b8741a1cab97",
    ),
    "m199_protocol": (M199_PROTOCOL_REL, M199_PROTOCOL_SHA256),
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

CASE_MANIFEST_SCHEMA_ID = "m207-s01-pilot-cases/v1"
CASE_COUNT = 40
WORK_FAMILY_CAP = 4

# The eleven frozen S02 agreement axes, in their frozen order.  S03 consumes them
# and may neither drop nor invent one.
EXPECTED_INPUT_AXES = (
    "reference_decision",
    "span_exact",
    "abstention",
    "slot_marker_chain",
    "slot_hier_nums",
    "slot_date",
    "slot_doc_no",
    "slot_law_code",
    "slot_anaphora",
    "slot_range",
    "slot_quoted_enum",
)
SLOT_AXES = tuple(axis for axis in EXPECTED_INPUT_AXES if axis.startswith("slot_"))

S02_DERIVED_SCHEMA_IDS = {
    "agreement_report": "m207-s02-agreement-report/v1",
    "disagreement_inventory": "m207-s02-disagreement-inventory/v1",
    "adjudication_record": "m207-s02-adjudication-record/v1",
    "pilot_receipt": "m207-s02-pilot-receipt/v1",
}

ASPECT_NAMES = ("span", "slot", "scope", "binding", "abstention", "false_authority")
ASPECT_CLOSED_KEYS = (
    "aspect",
    "source_axes",
    "derived_from",
    "numerator",
    "denominator",
    "denominator_units",
    "units_excluded_reasons",
    "value_kind",
    "aggregate",
)
EXCLUDED_REASON_VALUES = ("abstained", "undisputed_missing", "unresolved", "not_derivable")
DENOMINATOR_UNIT_VALUES = (
    "committed_coding_with_resolved_reference_span",
    "committed_coding_with_resolved_reference",
    "resolved_reference_with_derived_scope",
    "resolved_reference_with_derived_binding",
    "committed_coding_pair",
    "resolved_reference_is_not_a_reference",
)
VALUE_KINDS = ("rate",)

ASPECT_TABLE: tuple[dict[str, Any], ...] = (
    {
        "aspect": "span",
        "source_axes": ["span_exact"],
        "derived_from": (
            "m207-s02 agreement axis span_exact; the per-pass coding is compared with "
            "the resolved reference under the frozen M199 section-8 rule (start, end and "
            "decision all equal)"
        ),
        "numerator": "units where the pass coding equals the resolved reference coding on span_exact",
        "denominator": (
            "units in which both passes committed a coding, the resolved reference is a "
            "reference, and the resolved reference names one of the two committed spans"
        ),
        "denominator_units": "committed_coding_with_resolved_reference_span",
        "units_excluded_reasons": list(EXCLUDED_REASON_VALUES),
        "value_kind": "rate",
        "aggregate": False,
    },
    {
        "aspect": "slot",
        "source_axes": list(SLOT_AXES),
        "derived_from": (
            "the eight m207-s02 slot_<key> agreement axes; per-pass slot presence is "
            "compared with the resolved reference slot presence for each closed slot key"
        ),
        "numerator": (
            "per slot key, units where the pass slot presence equals the resolved "
            "reference presence; the published aspect value is the aggregate over the "
            "eight closed slot keys"
        ),
        "denominator": (
            "per slot key, units in which both passes committed a coding and the resolved "
            "reference is a reference; the aggregate denominator is the sum over the eight "
            "closed slot keys"
        ),
        "denominator_units": "committed_coding_with_resolved_reference",
        "units_excluded_reasons": list(EXCLUDED_REASON_VALUES),
        "value_kind": "rate",
        "aggregate": True,
    },
    {
        "aspect": "scope",
        "source_axes": ["slot_hier_nums", "slot_doc_no", "slot_law_code", "slot_marker_chain"],
        "derived_from": (
            "D490 derived rule over the frozen slots (there is no ninth slot and no "
            "schema-version bump): a reference carrying its own target through hier_nums, "
            "doc_no or law_code is scope_local; a reference whose target arrives only "
            "through a non-empty marker_chain is scope_inherited; otherwise the unit is "
            "excluded"
        ),
        "numerator": (
            "units where the pass-derived scope label equals the "
            "resolved-reference-derived scope label"
        ),
        "denominator": (
            "units in which both passes committed a coding, the resolved reference is a "
            "reference, and the resolved reference derives a scope label (scope_local or "
            "scope_inherited)"
        ),
        "denominator_units": "resolved_reference_with_derived_scope",
        "units_excluded_reasons": list(EXCLUDED_REASON_VALUES),
        "value_kind": "rate",
        "aggregate": False,
    },
    {
        "aspect": "binding",
        "source_axes": ["slot_anaphora", "slot_range"],
        "derived_from": (
            "D490 derived rule over the frozen slots: anaphora and range both absent with "
            "a present target is binding_explicit; a non-empty anaphora or range is "
            "binding_unresolved; otherwise the unit is excluded"
        ),
        "numerator": (
            "units where the pass-derived binding label equals the "
            "resolved-reference-derived binding label"
        ),
        "denominator": (
            "units in which both passes committed a coding, the resolved reference is a "
            "reference, and the resolved reference derives a binding label "
            "(binding_explicit or binding_unresolved)"
        ),
        "denominator_units": "resolved_reference_with_derived_binding",
        "units_excluded_reasons": list(EXCLUDED_REASON_VALUES),
        "value_kind": "rate",
        "aggregate": False,
    },
    {
        "aspect": "abstention",
        "source_axes": ["abstention"],
        "derived_from": (
            "m207-s02 agreement axis abstention; abstention is a separate coder outcome "
            "that is never merged with not_a_reference (ABSTENTION_COLLAPSE)"
        ),
        "numerator": (
            "units where the pass abstention value equals the resolved reference abstention value"
        ),
        "denominator": (
            "all units in which both passes committed a coding, including units whose "
            "resolved decision is not_a_reference; abstention keeps its own denominator "
            "and is never folded into the other five aspects"
        ),
        "denominator_units": "committed_coding_pair",
        "units_excluded_reasons": ["undisputed_missing", "unresolved", "not_derivable"],
        "value_kind": "rate",
        "aggregate": False,
    },
    {
        "aspect": "false_authority",
        "source_axes": ["reference_decision"],
        "derived_from": (
            "derived from the m207-s02 reference_decision axis: a unit where the pass "
            "asserted reference while the resolved reference is not_a_reference, that is "
            "claimed authority with no resolved support"
        ),
        "numerator": "units where the pass asserts reference while the resolved reference is not_a_reference",
        "denominator": (
            "units in which both passes committed a coding and the resolved reference is "
            "not_a_reference, the population in which false authority can occur"
        ),
        "denominator_units": "resolved_reference_is_not_a_reference",
        "units_excluded_reasons": list(EXCLUDED_REASON_VALUES),
        "value_kind": "rate",
        "aggregate": False,
    },
)

DENOMINATOR_RULE: dict[str, Any] = {
    "publication_shape": ["measured", "denominator", "value", "measurement_status"],
    "zero_denominator_value": None,
    "zero_denominator_measurement_status": "not-measured",
    "zero_denominator_diagnostic": "RATE_UNDEFINED",
    "imputed_zero_value_forbidden": True,
    "perfect_value": 1.0,
    "perfect_value_requires_full_coverage": True,
    "perfect_value_unbacked_diagnostic": "COMPUTED_PERFECT_UNBACKED",
    "excluded_unit_reason_values": list(EXCLUDED_REASON_VALUES),
    "excluded_unit_effect": "neither increases nor decreases a measured value",
}

STRATA_RULE: dict[str, Any] = {
    "provider_strata": ["consultant", "garant", "unknown"],
    "provider_basis": (
        "declared provider roots only; an undeclared or unattributable case stays unknown "
        "and is never re-derived from a path or a file name"
    ),
    "unknown_provider_value": "unknown",
    "family_scope_values": ["holdout", "dev"],
    "draw_stratum_values_source": "frozen m207-s01-pilot-cases/v1 draw_stratum",
    "holdout_granularity": "work_family",
    "quota_rule": "quota <= availability",
    "every_stratum_present": True,
    "empty_stratum_publication": {"value": None, "measurement_status": "not-measured"},
    "stratum_drop_forbidden": True,
}

PUBLICATION_CONTRACT: dict[str, Any] = {
    "measurement_status_values": [
        "not-measured",
        "proxy-measured",
        "independent-measured",
    ],
    "admissible_measurement_status": "independent-measured",
    "independent_measured_requires": [
        "two_validated_human_submissions",
        "provenance_human-reviewed",
        "coder_pass_1_and_2",
        "distinct_coder_id",
        "separate_adjudication_record",
        "unresolved_count_zero",
        "pre_adjudication_agreement_sha256_pinned",
    ],
    "refused_input_schema_ids": [
        "npa-quality-receipts/v1",
        "npa-lawref-seed/v1",
        "law-nexus-npa-corpus-manifest/v1",
    ],
    "refused_input_schema_prefixes": ["npa-c5-"],
    "refused_input_provenance_values": ["rule-seed"],
    "refused_input_paths": ["crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json"],
    "refusal_diagnostic": "PROXY_INPUT_REFUSED",
    "framing": "rater-vs-resolved-reference",
    "framing_is_not": ["system-quality", "gold"],
}

INPUT_ADMISSIBILITY: dict[str, Any] = {
    "case_manifest_schema_id": CASE_MANIFEST_SCHEMA_ID,
    "submission_schema_id": SUBMISSION_SCHEMA_ID,
    "s02_derived_schema_ids": [S02_DERIVED_SCHEMA_IDS[name] for name in S02_DERIVED_SCHEMA_IDS],
    "human_store_paths": [
        "prd/annotation/m207-s02-submissions",
        "prd/annotation/m207-s02-adjudications",
    ],
    "stores_are_read_only": True,
    "new_slot_keys_allowed": False,
}

OUTPUT_CONTRACT: dict[str, Any] = {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": False,
    "classification": "not-authorized",
    "promotion": "none",
    "threshold": None,
    "is_gold": False,
    "human_acceptance": None,
    "legal_claim": "forbidden",
    "n2_claim": "forbidden",
}

VOCABULARY_EXPECTATIONS: dict[str, Any] = {
    "provenance": ["human-reviewed"],
    "coder_pass": [1, 2],
    "authority": ["none"],
    "suggestion_status": ["none-provided"],
    "output_type": ["AnnotationSuggestion"],
    "classification": ["not-authorized"],
    "promotion": ["none"],
    "threshold": None,
    "decision_values": ["reference", "not_a_reference"],
    "abstention_values": ["not-abstained", "ambiguous", "insufficient-context"],
    "measurement_status": ["not-measured", "proxy-measured", "independent-measured"],
    "aspect_names": list(ASPECT_NAMES),
    "provider_strata": ["consultant", "garant", "unknown"],
    "family_scope_values": ["holdout", "dev"],
    "excluded_reason_values": list(EXCLUDED_REASON_VALUES),
    "span_coordinate": ["half-open-byte-range-utf8-boundaries"],
}

SUBSCHEMA_IDS = {
    "eval_manifest": "m207-s03-eval-manifest/v1",
    "stratum_table": "m207-s03-stratum-table/v1",
    "leakage_report": "m207-s03-leakage-report/v1",
    "evaluation_report": "m207-s03-evaluation-report/v1",
    "battery": "m207-s03-battery/v1",
}
REQUIRED_SUBSCHEMAS = tuple(SUBSCHEMA_IDS)

# S03 may not become a second measurement convention: its own schema ids must not
# collide with an S01 id, an S02 id, an ``npa-c5-*`` manifest or the
# ``npa-quality-*`` receipts.  ``submission_schema_id`` is exempt by design: it is
# the S01 coding-submission form reused verbatim, not an S03-owned id.
SCHEMA_ID_DENY_PREFIXES = ("m207-s01-", "m207-s02-", "npa-c5-", "npa-quality-")
SCHEMA_ID_DENY_EXACT = ("law-nexus-npa-corpus-manifest/v1",)

WALL_CLOCK_KEY_TOKENS = ("duration_ms", "elapsed_ms", "generated_at", "wall_clock")

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
    "input_axes",
    "aspect_table",
    "aspect_closed_keys",
    "denominator_rule",
    "strata_rule",
    "publication_contract",
    "input_admissibility",
    "output_contract",
    "vocabularies",
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
    "slot_space_source",
    "slot_space",
    "input_axes",
    "aspect_table",
    "denominator_rule",
    "strata_rule",
    "publication_contract",
    "input_admissibility",
    "output_contract",
    "forbidden_keys",
    "forbidden_seed_keys",
    "required_sections",
    "non_claims",
    "lifecycle",
)

REQUIRED_SECTIONS = (
    "1. Scope, framing and ownership",
    "2. Frozen inputs and admissibility",
    "3. Aspect table: six separately measured aspects",
    "4. Denominator rule: no value without a denominator",
    "5. Strata: provider and Work-family",
    "6. Typed publication and the human reference",
    "7. Forbidden claims: gold, promotion, threshold, classification",
    "8. Fail-closed diagnostics",
    "9. Lifecycle markers and non-claims",
    "10. Boundaries",
    "Machine-readable protocol contract",
)

REQUIRED_MARKERS = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}

# The diagnostic vocabulary is closed: every S03 tool must speak exactly these
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
    "S02_REGRESSION_FAILED",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "DUPLICATE_JSON_KEY",
    "VOCABULARY_DRIFT",
    "ALTERNATIVE_DRIFT",
    "CASE_COUNT_OUT_OF_RANGE",
    "DIAGNOSTIC_TABLE_DRIFT",
    "HOLDOUT_LEAKAGE",
    "C3_ISOLATION_VIOLATION",
    "PROVIDER_STRATUM_DROPPED",
    "PROVIDER_QUOTA_UNJUSTIFIED",
    "PROVIDER_MISATTRIBUTED",
    "METADATA_REDERIVED",
    "C5_MEASUREMENT_CLAIM",
    "MANIFEST_STALE",
    "RATE_UNDEFINED",
    "COMPUTED_PERFECT_UNBACKED",
    "PROXY_INPUT_REFUSED",
    "DEVELOPMENT_SLICE_NOT_EVALUATION",
    "REPORT_WITHOUT_HUMAN_DATA",
    "REPORT_MISSING_WITH_HUMAN_DATA",
    "ASPECT_TABLE_DRIFT",
    "STRATUM_TABLE_DRIFT",
    "MEASUREMENT_STATUS_DRIFT",
)

EXPECTED_NON_CLAIMS = (
    "not gold: no S03 artifact, aspect value or stratum rate is a gold label",
    "not a promotion: classification stays not-authorized, promotion stays none and "
    "threshold stays null",
    "not a threshold: no rate threshold, pass/fail cut-off or accept/reject decision is introduced",
    "not a classification: no classifier is fitted, no gate is selected and no D388 gate is scored",
    "not system quality: the measured agreement is rater-vs-resolved-reference, never "
    "system quality",
    "not a model evaluation: no model is invoked anywhere in M207 and model_invoked stays false",
    "not human acceptance: no resolved reference becomes human-accepted truth "
    "(human_acceptance stays null)",
    "not a second measurement convention: npa-quality-receipts/v1, npa-c5-* and "
    "npa-lawref-seed/v1 inputs are refused",
    "not official-publication provenance (R070 stays open)",
    "not amendment provenance (R070 stays open)",
    "not LawRef / act-tree / clause segmentation",
    "not the N2-gate acceptance decision",
    "not legal interpretation",
    "not a product surface: S03 stays an offline Python harness under scripts/ and no "
    "crates/** file reads it",
    "not an evaluation of the dev slice: development-slice numbers are development-only, "
    "never independent evidence",
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
# ``is_gold`` is admitted where it is declared, and admitting it is only legal when
# it is pinned ``false``: declaring it ``true`` is the claim itself.
GUARDED_FALSE_CLAIM_KEYS = frozenset({"is_gold"})
# The deny-lists themselves legitimately hold the forbidden names.
EXEMPT_KEY_PREFIX = "forbidden_"

# Claim-bearing scalar keys: the value decides whether the surface is honest.
CLAIM_VALUE_RULES: tuple[tuple[str, Any, str], ...] = (
    ("authority", lambda value: value == "none", "AUTHORITY_CLAIM"),
    ("suggestion_status", lambda value: value == "none-provided", "AUTHORITY_CLAIM"),
    ("model_invoked", lambda value: value is False, "MODEL_INVOKED"),
    ("classification", lambda value: value == "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("promotion", lambda value: value == "none", "PROMOTION_CLAIM"),
    ("threshold", lambda value: value is None, "THRESHOLD_REQUESTED"),
    ("is_gold", lambda value: value is False, "IS_GOLD_CLAIM"),
    ("human_acceptance", lambda value: value is None, "GOLD_CLAIM"),
    ("legal_claim", lambda value: value == "forbidden", "AUTHORITY_CLAIM"),
    ("n2_claim", lambda value: value == "forbidden", "AUTHORITY_CLAIM"),
)

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
        return "is-gold-claim"
    if set(key_tokens(name)) & FORBIDDEN_KEY_TOKENS:
        return "predicted-answer"
    if lowered in FORBIDDEN_EXACT_KEYS:
        return "rule-seed-span"
    return None


def scan_forbidden_keys(
    node: Any, pointer: str, failures: Failures, *, key_list: bool = False
) -> None:
    """Reject predicted-answer, gold-claim and rule-seed keys at any depth.

    Closed key sets are JSON arrays of key names, so a forbidden name arrives as an
    element of a ``*_keys`` list at least as often as it arrives as a dict key.
    Both surfaces are checked; the ``forbidden_*`` deny-lists themselves are exempt
    because they are the deny-list and are pinned by value.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            hit = forbidden_key_hit(key, value)
            if hit == "is-gold-claim":
                _fail(failures, "IS_GOLD_CLAIM", f"key {key!r} at {pointer or '$'} claims gold")
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
                if element_hit and element_hit != "is-gold-claim":
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"closed key {item!r} at {pointer}[{index}] mints a {element_hit} field",
                    )
            scan_forbidden_keys(item, f"{pointer}[{index}]", failures)


def scan_forbidden_values(node: Any, pointer: str, failures: Failures) -> None:
    """Reject authority, gold, model, classification, threshold and promotion claims.

    Scalars only: a *list* of legal values (``$.vocabularies.authority``) states the
    closed set, while a scalar states the choice.  Only a scalar can claim.
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
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_forbidden_values(item, f"{pointer}[{index}]", failures)


def scan_wall_clock_keys(node: Any, pointer: str, failures: Failures) -> None:
    """Reject wall-clock keys in any closed key set: tracked JSON must be stable.

    Duration belongs in stdout (``M207_S03_BATTERY_TIMINGS``), never in a tracked
    artifact, or a byte-comparison battery can never be current.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if (
                key.endswith("_keys")
                and not key.startswith(EXEMPT_KEY_PREFIX)
                and isinstance(value, list)
            ):
                for index, item in enumerate(value):
                    if isinstance(item, str) and item.strip().lower() in WALL_CLOCK_KEY_TOKENS:
                        _fail(
                            failures,
                            "BATTERY_WALLCLOCK_FORBIDDEN",
                            f"{pointer}.{key}[{index}]={item!r} publishes a wall-clock field",
                        )
            scan_wall_clock_keys(value, f"{pointer}.{key}", failures)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_wall_clock_keys(item, f"{pointer}[{index}]", failures)


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
    appears, so it must equal the M199 section-5 space exactly.  S03 declares no
    slot list of its own, which is what keeps "no new slot key" true.
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


# --------------------------------------------------------------------------- #
# Structural checks
# --------------------------------------------------------------------------- #


def check_slot_space_block(label: str, declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "SLOT_SET_DRIFT", f"{label} must be an object")
        return
    _check_slot_space(label, declared.get("closed_keys"), failures)
    if declared.get("binary_outcome") != {"key": M199_BINARY_OUTCOME, "type": "boolean"}:
        _fail(
            failures,
            "SLOT_SET_DRIFT",
            f"{label}.binary_outcome must declare the boolean not_a_reference outcome",
        )
    expected_count = len(M199_SLOT_SPACE) + 1
    if declared.get("closed_key_count") != expected_count:
        _fail(failures, "SLOT_SET_DRIFT", f"{label}.closed_key_count must be {expected_count}")


def check_aspect_table(label: str, declared: Any, closed_keys: Any, failures: Failures) -> None:
    """Prove the six RC28-F15 aspects are measured separately, with denominators.

    The union of the aspect source axes must be exactly the eleven frozen S02 axes;
    a missing aspect, an empty denominator, an unknown denominator unit or an axis
    no aspect consumes is ``ASPECT_TABLE_DRIFT``.
    """
    # The protocol contract mirrors the aspect rows without re-declaring their
    # closed key set; the schema owns that declaration and is checked separately.
    row_keys: tuple[str, ...] = ()
    if closed_keys is not None:
        row_keys = _close_keys(f"{label}.closed_keys", closed_keys, failures)
        if row_keys and row_keys != ASPECT_CLOSED_KEYS:
            _fail(
                failures,
                "ASPECT_TABLE_DRIFT",
                f"{label} row keys {list(row_keys)} != {list(ASPECT_CLOSED_KEYS)}",
            )
    if not isinstance(declared, list):
        _fail(failures, "ASPECT_TABLE_DRIFT", f"{label} must be a list of aspect rows")
        return
    names_seen: list[str] = []
    axes_seen: set[str] = set()
    for index, row in enumerate(declared):
        if not isinstance(row, dict):
            _fail(failures, "ASPECT_TABLE_DRIFT", f"{label}[{index}] must be an object")
            continue
        if row_keys and set(row) != set(row_keys):
            _fail(
                failures,
                "ASPECT_TABLE_DRIFT",
                f"{label}[{index}] keys differ: extra="
                f"{sorted(set(row) - set(row_keys))} missing={sorted(set(row_keys) - set(row))}",
            )
        name = row.get("aspect")
        if not isinstance(name, str) or not name:
            _fail(failures, "ASPECT_TABLE_DRIFT", f"{label}[{index}].aspect must be a string")
        else:
            names_seen.append(name)
        denominator = row.get("denominator")
        if not isinstance(denominator, str) or not denominator.strip():
            _fail(
                failures,
                "ASPECT_TABLE_DRIFT",
                f"{label}[{name or index}] declares no denominator",
            )
        units = row.get("denominator_units")
        if units not in DENOMINATOR_UNIT_VALUES:
            _fail(
                failures,
                "ASPECT_TABLE_DRIFT",
                f"{label}[{name or index}].denominator_units={units!r} is outside the closed "
                f"vocabulary {list(DENOMINATOR_UNIT_VALUES)}",
            )
        if row.get("value_kind") not in VALUE_KINDS:
            _fail(
                failures,
                "ASPECT_TABLE_DRIFT",
                f"{label}[{name or index}].value_kind={row.get('value_kind')!r} must be a rate",
            )
        for field in ("derived_from", "numerator"):
            text = row.get(field)
            if not isinstance(text, str) or not text.strip():
                _fail(
                    failures,
                    "ASPECT_TABLE_DRIFT",
                    f"{label}[{name or index}].{field} must be a non-empty rule string",
                )
        reasons = row.get("units_excluded_reasons")
        if not isinstance(reasons, list) or not reasons:
            _fail(
                failures,
                "ASPECT_TABLE_DRIFT",
                f"{label}[{name or index}].units_excluded_reasons must be a non-empty list",
            )
        else:
            unknown = sorted(set(reasons) - set(EXCLUDED_REASON_VALUES))
            if unknown:
                _fail(
                    failures,
                    "ASPECT_TABLE_DRIFT",
                    f"{label}[{name or index}] names unknown exclusion reasons {unknown}",
                )
            # The anti-collapse invariant: abstention is measured over every
            # committed pair, so an abstained unit may never be excluded from the
            # abstention denominator.  Folding it out is ABSTENTION_COLLAPSE.
            if name == "abstention" and "abstained" in reasons:
                _fail(
                    failures,
                    "ABSTENTION_COLLAPSE",
                    f"{label}[abstention] excludes abstained units: abstention is the "
                    "measured outcome and is never merged away from not_a_reference",
                )
        if not isinstance(row.get("aggregate"), bool):
            _fail(
                failures,
                "ASPECT_TABLE_DRIFT",
                f"{label}[{name or index}].aggregate must be a boolean",
            )
        axes = row.get("source_axes")
        if not isinstance(axes, list) or not axes or not all(isinstance(a, str) for a in axes):
            _fail(
                failures,
                "ASPECT_TABLE_DRIFT",
                f"{label}[{name or index}].source_axes must be a non-empty list of axis names",
            )
        else:
            axes_seen.update(axes)
    if tuple(names_seen) != ASPECT_NAMES:
        _fail(
            failures,
            "ASPECT_TABLE_DRIFT",
            f"{label} aspects {names_seen} != the six frozen F15 aspects {list(ASPECT_NAMES)}",
        )
    if axes_seen != set(EXPECTED_INPUT_AXES):
        _fail(
            failures,
            "ASPECT_TABLE_DRIFT",
            f"{label} source axes differ from the frozen S02 axes: unused="
            f"{sorted(set(EXPECTED_INPUT_AXES) - axes_seen)} invented="
            f"{sorted(axes_seen - set(EXPECTED_INPUT_AXES))}",
        )


def check_denominator_rule(schema: Any, failures: Failures) -> None:
    if not isinstance(schema, dict):
        return
    if schema.get("denominator_rule") != DENOMINATOR_RULE:
        _fail(
            failures,
            "DENOMINATOR_MISMATCH",
            "$.denominator_rule drifted from the frozen D489 rule "
            f"({schema.get('denominator_rule')!r})",
        )


def check_strata_rule(schema: Any, failures: Failures) -> None:
    if not isinstance(schema, dict):
        return
    if schema.get("strata_rule") != STRATA_RULE:
        _fail(
            failures,
            "STRATUM_TABLE_DRIFT",
            f"$.strata_rule drifted from the frozen strata rule ({schema.get('strata_rule')!r})",
        )


def check_publication_contract(schema: Any, failures: Failures) -> None:
    if not isinstance(schema, dict):
        return
    declared = schema.get("publication_contract")
    if declared != PUBLICATION_CONTRACT:
        _fail(
            failures,
            "MEASUREMENT_STATUS_DRIFT",
            f"$.publication_contract drifted from the frozen typed-publication contract "
            f"({declared!r})",
        )


def check_input_admissibility(schema: Any, failures: Failures) -> None:
    if not isinstance(schema, dict):
        return
    if schema.get("input_admissibility") != INPUT_ADMISSIBILITY:
        _fail(
            failures,
            "VOCABULARY_DRIFT",
            f"$.input_admissibility drifted from the frozen admissible-input set "
            f"({schema.get('input_admissibility')!r})",
        )


def check_submission_form(schema: Any, failures: Failures) -> None:
    """The S01 coding-submission form must not be redefined under S03."""
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


def check_schema_id_collisions(schema: Any, failures: Failures) -> None:
    """S03 ids must not collide with S01, S02, npa-c5 or npa-quality ids."""
    if not isinstance(schema, dict):
        return
    declared: list[tuple[str, str]] = []
    root_id = schema.get("schema")
    if isinstance(root_id, str):
        declared.append(("$", root_id))
    subschemas = schema.get("schemas")
    if isinstance(subschemas, dict):
        for name, sub in subschemas.items():
            if isinstance(sub, dict) and isinstance(sub.get("schema_id"), str):
                declared.append((f"$.schemas.{name}", sub["schema_id"]))
    if not declared:
        _fail(failures, "SCHEMA_KEY_DRIFT", "no S03 schema id is declared")
        return
    for pointer, schema_id in declared:
        if schema_id in SCHEMA_ID_DENY_EXACT or schema_id.startswith(SCHEMA_ID_DENY_PREFIXES):
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"{pointer}.schema_id={schema_id!r} collides with a frozen S01/S02/npa-c5/"
                "npa-quality schema id (a second measurement convention is forbidden)",
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
    if isinstance(abstention, list) and set(abstention) & set(
        VOCABULARY_EXPECTATIONS["decision_values"]
    ):
        _fail(
            failures,
            "ABSTENTION_COLLAPSE",
            "abstention values may never reuse reference-decision values",
        )


def check_diagnostics(schema: Any, failures: Failures) -> None:
    if not isinstance(schema, dict):
        return
    declared = schema.get("diagnostics")
    if declared != list(EXPECTED_DIAGNOSTICS):
        extra = (
            sorted(set(declared) - set(EXPECTED_DIAGNOSTICS)) if isinstance(declared, list) else []
        )
        missing = (
            sorted(set(EXPECTED_DIAGNOSTICS) - set(declared)) if isinstance(declared, list) else []
        )
        _fail(
            failures,
            "DIAGNOSTIC_TABLE_DRIFT",
            f"$.diagnostics differs from the closed vocabulary: extra={extra} missing={missing}",
        )


def check_output_contract(schema: Any, failures: Failures) -> None:
    declared = schema.get("output_contract") if isinstance(schema, dict) else None
    if declared != OUTPUT_CONTRACT:
        _fail(
            failures,
            "AUTHORITY_CLAIM",
            f"$.output_contract drifted from the frozen no-claim contract ({declared!r})",
        )
        return
    if declared.get("classification") != "not-authorized":
        _fail(
            failures,
            "CLASSIFICATION_REQUESTED",
            "$.output_contract.classification must be 'not-authorized'",
        )
    if declared.get("promotion") != "none":
        _fail(failures, "PROMOTION_CLAIM", "$.output_contract.promotion must be 'none'")
    if declared.get("threshold") is not None:
        _fail(failures, "THRESHOLD_REQUESTED", "$.output_contract.threshold must be null")
    if declared.get("model_invoked") is not False:
        _fail(failures, "MODEL_INVOKED", "$.output_contract.model_invoked must be false")
    if declared.get("is_gold") is not False:
        _fail(failures, "IS_GOLD_CLAIM", "$.output_contract.is_gold must be false")
    if declared.get("human_acceptance") is not None:
        _fail(failures, "GOLD_CLAIM", "$.output_contract.human_acceptance must be null")


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
        if sub.get("schema_id") != SUBSCHEMA_IDS[name]:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"$.schemas.{name}.schema_id={sub.get('schema_id')!r} != {SUBSCHEMA_IDS[name]!r}",
            )
        _check_closed_pair(f"$.schemas.{name}", sub, failures)
    _check_eval_manifest(subschemas.get("eval_manifest"), failures)
    _check_stratum_table(subschemas.get("stratum_table"), failures)
    _check_leakage_report(subschemas.get("leakage_report"), failures)
    _check_evaluation_report(subschemas.get("evaluation_report"), failures)
    _check_battery(subschemas.get("battery"), failures)


def _check_eval_manifest(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    _close_keys("$.schemas.eval_manifest.case_closed_keys", sub.get("case_closed_keys"), failures)
    case_required = _close_keys(
        "$.schemas.eval_manifest.case_required_keys", sub.get("case_required_keys"), failures
    )
    case_closed = sub.get("case_closed_keys") or []
    for key in case_required:
        if key not in case_closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"eval_manifest case key {key!r} is not in its closed key set",
            )
    for key in ("work_family", "family_scope", "draw_stratum", "provider", "metadata_source"):
        if key not in case_closed:
            _fail(
                failures,
                "STRATUM_TABLE_DRIFT",
                f"eval_manifest case must declare {key!r} for provider and Work-family strata",
            )
    stratum_closed = _close_keys(
        "$.schemas.eval_manifest.provider_stratum_closed_keys",
        sub.get("provider_stratum_closed_keys"),
        failures,
    )
    for key in ("provider", "availability", "quota", "justification", "measurement_status"):
        if stratum_closed and key not in stratum_closed:
            _fail(
                failures,
                "PROVIDER_QUOTA_UNJUSTIFIED",
                f"eval_manifest provider stratum must declare {key!r}",
            )
    _close_keys(
        "$.schemas.eval_manifest.fragment_pin_closed_keys",
        sub.get("fragment_pin_closed_keys"),
        failures,
    )
    if sub.get("unknown_metadata_value") != "unknown":
        _fail(
            failures,
            "METADATA_REDERIVED",
            "eval_manifest.unknown_metadata_value must be 'unknown'",
        )
    if sub.get("case_count") != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"eval_manifest.case_count={sub.get('case_count')!r} != {CASE_COUNT}",
        )
    cap = sub.get("work_family_cap")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap != WORK_FAMILY_CAP:
        _fail(
            failures,
            "WORK_FAMILY_DOMINANCE",
            f"eval_manifest.work_family_cap={cap!r} != {WORK_FAMILY_CAP}",
        )


def _check_stratum_table(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    stratum_closed = _close_keys(
        "$.schemas.stratum_table.stratum_closed_keys",
        sub.get("stratum_closed_keys"),
        failures,
    )
    for key in (
        "provider",
        "work_family",
        "draw_stratum",
        "family_scope",
        "measurement_status",
    ):
        if stratum_closed and key not in stratum_closed:
            _fail(
                failures,
                "STRATUM_TABLE_DRIFT",
                f"stratum table row must declare {key!r}",
            )
    if sub.get("empty_stratum_retained") is not True:
        _fail(
            failures,
            "PROVIDER_STRATUM_DROPPED",
            "$.schemas.stratum_table.empty_stratum_retained must be true: an empty stratum "
            "is published not-measured and never dropped",
        )


def _check_leakage_report(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    check_closed = _close_keys(
        "$.schemas.leakage_report.check_closed_keys",
        sub.get("check_closed_keys"),
        failures,
    )
    check_required = _close_keys(
        "$.schemas.leakage_report.check_required_keys",
        sub.get("check_required_keys"),
        failures,
    )
    for key in check_required:
        if key not in check_closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"leakage check key {key!r} is not in its closed key set",
            )
    for key in ("check_id", "required", "observed", "status"):
        if check_closed and key not in check_closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"leakage check must declare {key!r}",
            )
    declared = sub.get("diagnostic_values")
    if not isinstance(declared, list) or not set(declared) <= set(EXPECTED_DIAGNOSTICS):
        _fail(
            failures,
            "DIAGNOSTIC_TABLE_DRIFT",
            "$.schemas.leakage_report.diagnostic_values must be a subset of the closed "
            "diagnostic vocabulary",
        )


def _check_evaluation_report(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    closed = sub.get("closed_keys") or []
    for key in (
        "model_invoked",
        "measurement_status",
        "is_gold",
        "promotion",
        "threshold",
        "classification",
        "human_acceptance",
        "aspects",
        "strata",
        "holdout",
        "dev",
    ):
        if key not in closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"$.schemas.evaluation_report.closed_keys must declare {key!r}",
            )
    for label in ("aspect_result_closed_keys", "stratum_result_closed_keys"):
        result_closed = _close_keys(
            f"$.schemas.evaluation_report.{label}", sub.get(label), failures
        )
        for key in ("measured", "denominator", "value", "measurement_status"):
            if result_closed and key not in result_closed:
                _fail(
                    failures,
                    "DENOMINATOR_MISMATCH",
                    f"$.schemas.evaluation_report.{label} must declare {key!r}: no value "
                    "without a denominator",
                )
    statuses = sub.get("measurement_status_values")
    if statuses != PUBLICATION_CONTRACT["measurement_status_values"]:
        _fail(
            failures,
            "MEASUREMENT_STATUS_DRIFT",
            "$.schemas.evaluation_report.measurement_status_values drifted",
        )
    forbidden = sub.get("forbidden_report_keys")
    if forbidden != list(WALL_CLOCK_KEY_TOKENS):
        _fail(
            failures,
            "BATTERY_WALLCLOCK_FORBIDDEN",
            "$.schemas.evaluation_report.forbidden_report_keys must be the wall-clock set",
        )
    _close_keys(
        "$.schemas.evaluation_report.per_pass_closed_keys",
        sub.get("per_pass_closed_keys"),
        failures,
    )
    _close_keys(
        "$.schemas.evaluation_report.independent_reference_closed_keys",
        sub.get("independent_reference_closed_keys"),
        failures,
    )
    _close_keys(
        "$.schemas.evaluation_report.units_excluded_closed_keys",
        sub.get("units_excluded_closed_keys"),
        failures,
    )


def _check_battery(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    check_closed = _close_keys(
        "$.schemas.battery.check_closed_keys", sub.get("check_closed_keys"), failures
    )
    _close_keys("$.schemas.battery.check_required_keys", sub.get("check_required_keys"), failures)
    _close_keys("$.schemas.battery.pins_closed_keys", sub.get("pins_closed_keys"), failures)
    for key in ("check_id", "command", "diagnostic", "exit_code", "status"):
        if check_closed and key not in check_closed:
            _fail(failures, "SCHEMA_KEY_DRIFT", f"battery check must declare {key!r}")
    forbidden = sub.get("forbidden_battery_keys")
    if forbidden != list(WALL_CLOCK_KEY_TOKENS):
        _fail(
            failures,
            "BATTERY_WALLCLOCK_FORBIDDEN",
            f"$.schemas.battery.forbidden_battery_keys={forbidden!r} must be the wall-clock set",
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
    scan_wall_clock_keys(schema, "$", failures)
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
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.schema_version must be 1")
    if schema.get("protocol") != PROTOCOL_REL:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"$.protocol={schema.get('protocol')!r} != {PROTOCOL_REL!r}",
        )
    if schema.get("codebook") != S01_CODEBOOK_REL:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"$.codebook={schema.get('codebook')!r} != {S01_CODEBOOK_REL!r}",
        )
    if schema.get("slot_space_source") != SLOT_SPACE_SOURCE:
        _fail(
            failures,
            "SLOT_SET_DRIFT",
            f"$.slot_space_source={schema.get('slot_space_source')!r} != {SLOT_SPACE_SOURCE!r}",
        )
    _check_frozen_sources(schema.get("frozen_sources"), failures)
    check_slot_space_block("$.slot_space", schema.get("slot_space"), failures)
    if tuple(schema.get("input_axes") or ()) != EXPECTED_INPUT_AXES:
        _fail(
            failures,
            "ASPECT_TABLE_DRIFT",
            f"$.input_axes={schema.get('input_axes')!r} != frozen S02 axes "
            f"{list(EXPECTED_INPUT_AXES)!r}",
        )
    check_aspect_table(
        "$.aspect_table", schema.get("aspect_table"), schema.get("aspect_closed_keys"), failures
    )
    check_denominator_rule(schema, failures)
    check_strata_rule(schema, failures)
    check_publication_contract(schema, failures)
    check_input_admissibility(schema, failures)
    check_output_contract(schema, failures)
    check_submission_form(schema, failures)
    check_schema_id_collisions(schema, failures)
    check_vocabularies(schema, failures)
    check_diagnostics(schema, failures)
    check_sub_schemas(schema, failures)
    _check_non_claims("$.non_claims", schema.get("non_claims"), failures)
    _check_lifecycle("$.lifecycle", schema.get("lifecycle"), failures)


def _check_frozen_sources(declared: Any, failures: Failures) -> None:
    expected = {
        key: {"path": path, "sha256": digest} for key, (path, digest) in FROZEN_SOURCES.items()
    }
    if declared != expected:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            "$.frozen_sources must pin every frozen input "
            f"(declared={sorted(declared) if isinstance(declared, dict) else declared!r})",
        )


def check_contract(
    contract: dict[str, Any], schema: Any, headings: list[str], failures: Failures
) -> None:
    scan_forbidden_keys(contract, "contract$", failures)
    scan_forbidden_values(contract, "contract$", failures)
    if set(contract) != set(CONTRACT_ROOT_KEYS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "contract$ keys differ: extra="
            f"{sorted(set(contract) - set(CONTRACT_ROOT_KEYS))} missing="
            f"{sorted(set(CONTRACT_ROOT_KEYS) - set(contract))}",
        )
    if contract.get("protocol_id") != PROTOCOL_ID:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"contract.protocol_id must be {PROTOCOL_ID!r}",
        )
    if contract.get("schema_id") != SCHEMA_ID:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"contract.schema_id must be {SCHEMA_ID!r}",
        )
    if contract.get("codebook") != S01_CODEBOOK_REL:
        _fail(failures, "SCHEMA_KEY_DRIFT", "contract.codebook must be the frozen S01 codebook")
    if contract.get("submission_schema_id") != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"contract.submission_schema_id must be {SUBMISSION_SCHEMA_ID!r}",
        )
    if contract.get("submission_schema_reused_verbatim") is not SUBMISSION_SCHEMA_REUSED:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            "contract.submission_schema_reused_verbatim must be true",
        )
    if contract.get("slot_space_source") != SLOT_SPACE_SOURCE:
        _fail(failures, "SLOT_SET_DRIFT", "contract.slot_space_source drifted")
    check_slot_space_block("contract.slot_space", contract.get("slot_space"), failures)
    if tuple(contract.get("input_axes") or ()) != EXPECTED_INPUT_AXES:
        _fail(
            failures,
            "ASPECT_TABLE_DRIFT",
            "contract.input_axes must equal the frozen S02 axes",
        )
    check_aspect_table("contract.aspect_table", contract.get("aspect_table"), None, failures)
    for label, pointer, expected in (
        ("denominator_rule", "contract.denominator_rule", DENOMINATOR_RULE),
        ("strata_rule", "contract.strata_rule", STRATA_RULE),
        ("publication_contract", "contract.publication_contract", PUBLICATION_CONTRACT),
        ("input_admissibility", "contract.input_admissibility", INPUT_ADMISSIBILITY),
        ("output_contract", "contract.output_contract", OUTPUT_CONTRACT),
    ):
        if contract.get(label) != expected:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"{pointer} differs from the frozen {label} ({contract.get(label)!r})",
            )
    if contract.get("forbidden_keys") != list(FORBIDDEN_KEYS_CANONICAL):
        _fail(failures, "LEAK_FORBIDDEN_KEY", "contract.forbidden_keys must be the canonical six")
    if contract.get("forbidden_seed_keys") != list(FORBIDDEN_SEED_KEYS_CANONICAL):
        _fail(
            failures, "LEAK_FORBIDDEN_KEY", "contract.forbidden_seed_keys must be the canonical set"
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

    if isinstance(schema, dict):
        for label, pointer in (
            ("slot_space", "contract.slot_space"),
            ("input_axes", "contract.input_axes"),
            ("aspect_table", "contract.aspect_table"),
            ("denominator_rule", "contract.denominator_rule"),
            ("strata_rule", "contract.strata_rule"),
            ("publication_contract", "contract.publication_contract"),
            ("input_admissibility", "contract.input_admissibility"),
            ("output_contract", "contract.output_contract"),
            ("non_claims", "contract.non_claims"),
            ("lifecycle", "contract.lifecycle"),
        ):
            if contract.get(label) != schema.get(label):
                _fail(
                    failures,
                    "SCHEMA_KEY_DRIFT",
                    f"{pointer} and $.{label} disagree: edit the protocol block and the "
                    "schema together",
                )


def cross_check_frozen_artifacts(
    frozen_paths: dict[str, Path],
    frozen_hashes: dict[str, str],
    schema: Any,
    protocol_slots: tuple[str, ...],
    failures: Failures,
) -> None:
    """Bind the S03 declarations to the actual frozen S01/S02 artifacts.

    The sha256 pins already prove the frozen bytes; this second, structural pass
    states the contract they carry: the slot space, the reused submission schema id
    and the eleven S02 agreement axes the six aspects are derived from.
    """
    if not isinstance(schema, dict):
        return
    declared = tuple(schema.get("slot_space", {}).get("closed_keys") or ())
    if declared and declared != M199_SLOT_SPACE:
        _fail(
            failures,
            "SLOT_SET_DRIFT",
            f"S03 slot space {list(declared)} != M199 §5 {list(M199_SLOT_SPACE)}",
        )
    if protocol_slots and declared and declared != protocol_slots:
        _fail(
            failures,
            "SLOT_SET_DRIFT",
            f"S03 slot space {list(declared)} != frozen M199 §5 {list(protocol_slots)}",
        )

    s01_path = frozen_paths.get("m207_s01_schemas")
    if s01_path is not None and s01_path.is_file():
        try:
            s01 = load_json(s01_path, "frozen S01 schemas")
        except GateError:
            s01 = None
        if isinstance(s01, dict):
            s01_slots = tuple(s01.get("slot_space", {}).get("closed_keys") or ())
            if s01_slots and declared != s01_slots:
                _fail(
                    failures,
                    "SLOT_SET_DRIFT",
                    f"S03 slot space {list(declared)} != frozen S01 {list(s01_slots)}",
                )
            submission = s01.get("schemas", {}).get("coding_submission", {})
            if isinstance(submission, dict) and submission.get("schema_id") != SUBMISSION_SCHEMA_ID:
                _fail(
                    failures,
                    "SUBMISSION_SCHEMA_DRIFT",
                    "frozen S01 coding-submission schema id moved; S03 must reuse it verbatim",
                )

    s02_path = frozen_paths.get("m207_s02_schemas")
    if s02_path is not None and s02_path.is_file():
        try:
            s02 = load_json(s02_path, "frozen S02 schemas")
        except GateError:
            s02 = None
        if isinstance(s02, dict):
            s02_axes = tuple(s02.get("agreement_axes") or ())
            if s02_axes and tuple(schema.get("input_axes") or ()) != s02_axes:
                _fail(
                    failures,
                    "ASPECT_TABLE_DRIFT",
                    f"S03 input_axes {schema.get('input_axes')!r} != frozen S02 agreement axes "
                    f"{list(s02_axes)!r}",
                )
            s02_submission = s02.get("submission_schema_id")
            if s02_submission is not None and s02_submission != schema.get("submission_schema_id"):
                _fail(
                    failures,
                    "SUBMISSION_SCHEMA_DRIFT",
                    f"S03 submission_schema_id {schema.get('submission_schema_id')!r} != frozen "
                    f"S02 {s02_submission!r}",
                )
            s02_schemas = s02.get("schemas", {})
            declared_ids = schema.get("input_admissibility", {}).get("s02_derived_schema_ids")
            actual = {
                name: s02_schemas.get(name, {}).get("schema_id")
                for name in S02_DERIVED_SCHEMA_IDS
                if isinstance(s02_schemas.get(name), dict)
            }
            expected = [actual[name] for name in S02_DERIVED_SCHEMA_IDS if name in actual]
            if declared_ids != expected:
                _fail(
                    failures,
                    "VOCABULARY_DRIFT",
                    f"S03 admissible S02 schema ids {declared_ids!r} != the frozen S02 ids "
                    f"{expected!r}",
                )

    s01_codebook_path = frozen_paths.get("m207_s01_codebook")
    if s01_codebook_path is not None and s01_codebook_path.is_file():
        try:
            codebook_contract = extract_contract(
                s01_codebook_path.read_text(encoding="utf-8"),
                S01_CODEBOOK_CONTRACT_HEADING,
                "S01 codebook contract",
            )
        except GateError:
            codebook_contract = None
        if isinstance(codebook_contract, dict):
            codebook_slots = tuple(codebook_contract.get("slot_space", {}).get("closed_keys") or ())
            if codebook_slots and declared != codebook_slots:
                _fail(
                    failures,
                    "SLOT_SET_DRIFT",
                    f"S03 slot space {list(declared)} != frozen S01 codebook {list(codebook_slots)}",
                )


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
                root, rel, f"frozen source {key}", suffix=PurePosixPath(rel).suffix, prefix="prd/"
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
    if frozen_hashes.get("m199_protocol") == M199_PROTOCOL_SHA256:
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
        _fail(failures, "MISSING_ARTIFACT", f"S03 protocol missing at {protocol_rel}")
    else:
        protocol_text = protocol_path.read_text(encoding="utf-8")
        headings = protocol_headings(protocol_text)
        if BOUNDED_TAG not in protocol_text:
            _fail(
                failures,
                "MISSING_SECTION",
                f"S03 protocol must carry the {BOUNDED_TAG} lifecycle tag",
            )
        try:
            contract = extract_contract(protocol_text, CONTRACT_HEADING, "S03 protocol contract")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    schema: Any = None
    if not schemas_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"S03 schemas missing at {schemas_rel}")
    else:
        try:
            schema = load_json(schemas_path, "S03 schemas document")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    if schema is not None:
        check_schema_document(schema, failures)
    if contract is not None:
        check_contract(contract, schema, headings, failures)
    cross_check_frozen_artifacts(frozen_paths, frozen_hashes, schema, protocol_slots, failures)
    return failures


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
        f"FAIL M207_S03_SCHEMAS_GATE: {len(seen)} finding(s); the frozen S03 contract "
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
    schema["schemas"]["eval_manifest"]["case_closed_keys"].append("label")


def _mutate_seed_key(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["eval_manifest"]["case_closed_keys"].append("seed_span")


def _mutate_wall_clock_key(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["evaluation_report"]["aspect_result_closed_keys"].append("duration_ms")


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


def _mutate_is_gold(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["is_gold"] = True


def _mutate_human_acceptance(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["human_acceptance"] = "accepted"


def _mutate_promotion(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["promotion"] = "gold"


def _mutate_legal_claim(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["output_contract"]["legal_claim"] = "authoritative"


def _mutate_submission_form(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["submission_schema_id"] = "m207-s03-coding-submission/v1"


def _mutate_abstention(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["vocabularies"]["abstention_values"] = ["not-abstained", "ambiguous", "reference"]


def _mutate_abstention_collapse_aspect(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    for row in schema["aspect_table"]:
        if row["aspect"] == "abstention":
            row["units_excluded_reasons"] = [
                "abstained",
                *row["units_excluded_reasons"],
            ]


def _mutate_lifecycle(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["lifecycle"]["human_adoption"] = "adopted"


def _mutate_non_claim(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["non_claims"].append("not a real non-claim")


def _mutate_diagnostics(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["diagnostics"].append("UNKNOWN_DIAGNOSTIC")


def _mutate_aspect_dropped(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["aspect_table"] = [row for row in schema["aspect_table"] if row["aspect"] != "scope"]


def _mutate_aspect_empty_denominator(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["aspect_table"][0]["denominator"] = ""


def _mutate_aspect_invented_axis(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["aspect_table"][0]["source_axes"].append("invented_axis")


def _mutate_denominator_rule(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["denominator_rule"]["zero_denominator_value"] = 0.0


def _mutate_strata_rule(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["strata_rule"]["provider_strata"] = ["consultant", "garant"]


def _mutate_publication_contract(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["publication_contract"]["admissible_measurement_status"] = "proxy-measured"


def _mutate_input_admissibility(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["input_admissibility"]["new_slot_keys_allowed"] = True


def _mutate_frozen_sources(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["frozen_sources"]["m207_s02_schemas"]["sha256"] = "0" * 64


def _mutate_schema_id_collision(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["evaluation_report"]["schema_id"] = "m207-s02-evaluation-report/v1"


def _mutate_schema_root_key(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["extra_root_key"] = True


def _mutate_stratum_drop(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["stratum_table"]["empty_stratum_retained"] = False


def _mutate_contract_authority(_schema: dict[str, Any], contract: dict[str, Any]) -> None:
    contract["output_contract"]["authority"] = "authoritative"


def _mutate_contract_aspect_table(_schema: dict[str, Any], contract: dict[str, Any]) -> None:
    contract["aspect_table"] = [
        row for row in contract["aspect_table"] if row["aspect"] != "binding"
    ]


def _mutate_contract_required_sections(_schema: dict[str, Any], contract: dict[str, Any]) -> None:
    contract["required_sections"] = ["1. Scope, framing and ownership"]


SELFTEST_CASES: tuple[tuple[str, str, Mutator], ...] = (
    ("ninth-slot", "NINTH_SLOT", _mutate_slot_ninth),
    ("label-key", "LEAK_FORBIDDEN_KEY", _mutate_label_key),
    ("seed-span-key", "LEAK_FORBIDDEN_KEY", _mutate_seed_key),
    ("wall-clock-key", "BATTERY_WALLCLOCK_FORBIDDEN", _mutate_wall_clock_key),
    ("authority-authoritative", "AUTHORITY_CLAIM", _mutate_authority),
    ("suggestion-provided", "AUTHORITY_CLAIM", _mutate_suggestion),
    ("model-invoked", "MODEL_INVOKED", _mutate_model),
    ("classification-pass", "CLASSIFICATION_REQUESTED", _mutate_classification),
    ("threshold-set", "THRESHOLD_REQUESTED", _mutate_threshold),
    ("is-gold-true", "IS_GOLD_CLAIM", _mutate_is_gold),
    ("human-acceptance", "GOLD_CLAIM", _mutate_human_acceptance),
    ("promotion-gold", "PROMOTION_CLAIM", _mutate_promotion),
    ("legal-claim", "AUTHORITY_CLAIM", _mutate_legal_claim),
    ("submission-form-redefined", "SUBMISSION_SCHEMA_DRIFT", _mutate_submission_form),
    ("abstention-collapse", "ABSTENTION_COLLAPSE", _mutate_abstention),
    ("abstention-collapse-aspect", "ABSTENTION_COLLAPSE", _mutate_abstention_collapse_aspect),
    ("lifecycle-drift", "MISSING_LIFECYCLE_MARKER", _mutate_lifecycle),
    ("non-claim-drift", "MISSING_NON_CLAIM", _mutate_non_claim),
    ("diagnostic-table-drift", "DIAGNOSTIC_TABLE_DRIFT", _mutate_diagnostics),
    ("aspect-dropped", "ASPECT_TABLE_DRIFT", _mutate_aspect_dropped),
    ("aspect-empty-denominator", "ASPECT_TABLE_DRIFT", _mutate_aspect_empty_denominator),
    ("aspect-invented-axis", "ASPECT_TABLE_DRIFT", _mutate_aspect_invented_axis),
    ("denominator-rule-drift", "DENOMINATOR_MISMATCH", _mutate_denominator_rule),
    ("strata-rule-drift", "STRATUM_TABLE_DRIFT", _mutate_strata_rule),
    ("publication-contract-drift", "MEASUREMENT_STATUS_DRIFT", _mutate_publication_contract),
    ("input-admissibility-drift", "VOCABULARY_DRIFT", _mutate_input_admissibility),
    ("frozen-sources-drift", "FROZEN_SOURCE_DRIFT", _mutate_frozen_sources),
    ("schema-id-collision", "SCHEMA_KEY_DRIFT", _mutate_schema_id_collision),
    ("schema-root-key", "SCHEMA_KEY_DRIFT", _mutate_schema_root_key),
    ("stratum-dropped", "PROVIDER_STRATUM_DROPPED", _mutate_stratum_drop),
    ("contract-authority", "AUTHORITY_CLAIM", _mutate_contract_authority),
    ("contract-aspect-table", "ASPECT_TABLE_DRIFT", _mutate_contract_aspect_table),
    ("contract-sections", "MISSING_SECTION", _mutate_contract_required_sections),
)


def _selftest_baselines(
    root: Path, protocol_rel: str, schemas_rel: str
) -> tuple[dict[str, Any], dict[str, Any], list[str]] | None:
    protocol_path = root / protocol_rel
    schemas_path = root / schemas_rel
    if not protocol_path.is_file() or not schemas_path.is_file():
        return None
    protocol_text = protocol_path.read_text(encoding="utf-8")
    schema = load_json(schemas_path, "S03 schemas document")
    contract = extract_contract(protocol_text, CONTRACT_HEADING, "S03 protocol contract")
    return schema, contract, protocol_headings(protocol_text)


def _selftest_frozen_source_drift(root: Path, protocol_rel: str, schemas_rel: str) -> str | None:
    """Prove FROZEN_SOURCE_DRIFT against a mutated copy of a frozen S02 input."""
    rels = [protocol_rel, schemas_rel, *(rel for rel, _ in FROZEN_SOURCES.values())]
    with tempfile.TemporaryDirectory(prefix="m207-s03-drift-") as tmp:
        tmp_root = Path(tmp)
        for rel in dict.fromkeys(rels):
            source = root / rel
            if not source.is_file():
                return f"frozen-drift selftest could not read {rel}"
            target = tmp_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        mutated = tmp_root / S02_SCHEMAS_REL
        mutated.write_bytes(mutated.read_bytes() + b" ")
        seen = {diag for diag, _ in collect_failures(tmp_root, protocol_rel, schemas_rel)}
    if "FROZEN_SOURCE_DRIFT" not in seen:
        return (
            "frozen-drift selftest: a mutated S02 schemas copy did not raise "
            f"FROZEN_SOURCE_DRIFT (saw {sorted(seen) or 'nothing'})"
        )
    return None


def run_selftest(root: Path, protocol_rel: str, schemas_rel: str) -> int:
    baselines = _selftest_baselines(root, protocol_rel, schemas_rel)
    if baselines is None:
        print("FAIL SELFTEST_BASELINE: S03 protocol or schemas missing", file=sys.stderr)
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

    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(
            f"FAIL M207_S03_SCHEMAS_SELFTEST: {len(problems)} hostile path(s) not proven",
            file=sys.stderr,
        )
        return 1
    print(SELFTEST_MARKER)
    return 0


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
