#!/usr/bin/env python3
"""M207 S03 per-aspect rate engine: frozen denominators, typed publication, fail-closed.

Read ``prd/annotation/m207-s03-eval-protocol.md`` (T01) and
``prd/annotation/m207-s03-schemas.json`` first: the aspect table, the denominator rule
(D489), the strata rule and the publication contract there are the authority this engine
implements, and it re-verifies them at run time.

WHY.  S02 proves honest denominators for alpha but publishes no rate; S03 owns the derived
per-aspect rates and the provider/Work-family strata.  This engine computes a fully frozen
evaluation report from an independent human reference *only* and never publishes a number
without a positive denominator: ``denominator == 0`` yields ``value: null`` with
``measurement_status: "not-measured"`` (D489 / RC28-F01), never ``0.0`` and never ``1.0``.
A ``1.0`` is lawful only as a computed result with ``measured > 0`` and full coverage of the
declared denominator; anything else is ``COMPUTED_PERFECT_UNBACKED``.

HUMAN GATE.  With no human reference this tool exits 3 with ``HUMAN_PILOT_ABSENT`` and writes
no metric artifact at all.  It never creates a submission, an adjudication or any S02 derived
artifact: the two human stores and the five S02 derived artifacts are read-only inputs and
their absence is the expected state, not a configuration error.

WHAT IS MEASURED.  Each aspect compares one pass's coding with the resolved human reference,
pooled over the two mutually blind passes (one observation per unit and pass).  The per-pass
confusion matrix needs a positive class, fixed as follows:

===============  ==============================================  ==========================
aspect           positive class (the pass's claim)               truth
===============  ==============================================  ==========================
span             the pass's ``span_exact`` value is supported    the resolved span value
slot             ``slot_present`` for one of the eight keys      resolved presence per key
scope            ``scope_inherited``                             derived reference scope
binding          ``binding_unresolved``                          derived reference binding
abstention       abstained (any value but ``not-abstained``)     resolved abstention value
false_authority  the pass asserted ``reference``                 resolved decision
===============  ==============================================  ==========================

``span`` is a matching aspect: in its denominator the reference always names one of the two
committed spans, so ``false_negative``/``true_negative`` are structurally ``0`` and precision is
the supported-claim share while recall is ``1.0`` whenever a claim is supported.
``false_authority``'s denominator is the population in which authority *can* be false, so its
``false_positive`` count **is** the false-authority numerator, its precision is ``0.0`` (or
``null``) and its recall is ``null``.  The published aspect ``value`` is always the frozen
table's literal numerator over denominator: for ``false_authority`` the defect rate, for the
other five the agreement rate.  ``slot`` aggregates eight independent per-key units, so its
denominator is the sum over the eight closed slot keys, exactly as the frozen table declares.

STRATA.  Every ``provider x work_family x draw_stratum x family_scope`` stratum the frozen T02
manifest carries is published for all six aspects, and so is every declared provider that
attributes no case (today ``garant``): an empty stratum is published ``not-measured`` with
``value: null`` and never dropped (``PROVIDER_STRATUM_DROPPED``).  The holdout slice is the
evaluation; the dev slice is published separately as ``development-only`` (``proxy-measured``
rows) and never as independent evidence (``DEVELOPMENT_SLICE_NOT_EVALUATION``).

MODES.  ``check`` read-only self-check of the frozen contract, the diagnostic table, the
manifest strata, the formulas and the report/human invariant.  ``run`` computes and publishes
the report, or exits 3 with no artifact when the human reference is absent.  ``selftest``
proves every named refusal path on synthetic copies outside the product paths.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# Sibling contours: one validator, not a second divergent copy.
# --------------------------------------------------------------------------- #


def _load_sibling(module_name: str) -> Any:
    """Load a sibling harness module by path (``scripts/`` is not a package)."""
    path = Path(__file__).resolve().parent / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - import machinery guard
        raise RuntimeError(f"cannot load sibling module {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    # Register before executing: ``dataclass`` resolves ``cls.__module__`` through
    # ``sys.modules``, so an unregistered module breaks every dataclass it defines.
    sys.modules.setdefault(module_name, module)
    spec.loader.exec_module(module)
    return module


try:
    ADJ = _load_sibling("m207_s02_adjudicate")
except Exception as exc:  # pragma: no cover - only a repository defect reaches this
    print(
        "FAIL MISSING_ARTIFACT: cannot load the sibling adjudication contour "
        f"scripts/m207_s02_adjudicate.py: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

AGREEMENT = ADJ.AGREEMENT
INTAKE = ADJ.INTAKE
GateError = INTAKE.GateError
Failures = list[tuple[str, str]]

MARKER = "M207_S03_METRICS_OK"
SELFTEST_MARKER = "M207_S03_METRICS_SELFTEST_OK"
WRITTEN_LINE = "m207_s03_evaluation_report=written"
ABSENT_TOKEN = "MACHINERY_GREEN_HUMAN_ABSENT"

OK_EXIT = 0
FAIL_EXIT = 1
ABSENT_EXIT = 3

SCHEMA_VERSION = 1
REPORT_SCHEMA_ID = "m207-s03-evaluation-report/v1"
MANIFEST_SCHEMA_ID = "m207-s03-eval-manifest/v1"
EVAL_SCHEMAS_ID = "m207-s03-eval-schemas/v1"
INTAKE_RECORD_SCHEMA_ID = "m207-s02-intake-record/v1"
AGREEMENT_REPORT_SCHEMA_ID = "m207-s02-agreement-report/v1"
INVENTORY_SCHEMA_ID = "m207-s02-disagreement-inventory/v1"
ADJUDICATION_RECORD_SCHEMA_ID = "m207-s02-adjudication-record/v1"
PILOT_RECEIPT_SCHEMA_ID = "m207-s02-pilot-receipt/v1"
ADJUDICATION_INPUT_SCHEMA_ID = "m207-s02-adjudication-input/v1"

CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
KIT_PASS1_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json"
KIT_PASS2_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass2.json"
S02_SCHEMAS_REL = "prd/annotation/m207-s02-schemas.json"
S01_SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
S03_SCHEMAS_REL = "prd/annotation/m207-s03-schemas.json"
PROTOCOL_REL = "prd/annotation/m207-s03-eval-protocol.md"
CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
S02_PROTOCOL_REL = "prd/annotation/m207-s02-coder-protocol.md"
M199_PROTOCOL_REL = "prd/migration/rust-evidence/m199-s01-annotation-protocol.md"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
MANIFEST_REL = "prd/migration/rust-evidence/m207-s03-eval-manifest.json"
SUBMISSIONS_REL = "prd/annotation/m207-s02-submissions"
ADJUDICATIONS_REL = "prd/annotation/m207-s02-adjudications"
INTAKE_RECORD_REL = "prd/migration/rust-evidence/m207-s02-intake-record.json"
AGREEMENT_REPORT_REL = "prd/migration/rust-evidence/m207-s02-agreement-report.json"
INVENTORY_REL = "prd/migration/rust-evidence/m207-s02-disagreement-inventory.json"
ADJUDICATION_RECORD_REL = "prd/migration/rust-evidence/m207-s02-adjudication-record.json"
PILOT_RECEIPT_REL = "prd/migration/rust-evidence/m207-s02-pilot-receipt.json"
REPORT_REL = "prd/migration/rust-evidence/m207-s03-evaluation-report.json"

ANNOTATION_PREFIX = "prd/annotation/"
EVIDENCE_PREFIX = "prd/migration/rust-evidence/"
SEED_SIDECAR_NAME = "lawref_seed.json"

CASE_COUNT = 40
PASSES = (1, 2)
CODER_PASS_ONE = 1
CODER_PASS_TWO = 2
REFERENCE_DECISION_AXIS = "reference_decision"
SPAN_EXACT_AXIS = "span_exact"
ABSTENTION_AXIS = "abstention"
SLOT_AXIS_PREFIX = "slot_"
SLOT_PRESENT = "slot_present"
SLOT_ABSENT = "slot_absent"
NON_ABSTAINED = "not-abstained"
NOT_A_REFERENCE = "not_a_reference"
REFERENCE = "reference"
ABSTAINED = "abstained"
UNDISPUTED_MISSING = "undisputed_missing"
UNRESOLVED = "unresolved"
NOT_DERIVABLE = "not_derivable"

ASPECTS = ("span", "slot", "scope", "binding", "abstention", "false_authority")
EXCLUDED_REASONS = (ABSTAINED, UNDISPUTED_MISSING, UNRESOLVED, NOT_DERIVABLE)
DENOMINATOR_UNITS = (
    "committed_coding_with_resolved_reference_span",
    "committed_coding_with_resolved_reference",
    "resolved_reference_with_derived_scope",
    "resolved_reference_with_derived_binding",
    "committed_coding_pair",
    "resolved_reference_is_not_a_reference",
)
# Abstention *is* the measured outcome there: listing `abstained` would collapse it away.
ASPECT_WITHOUT_ABSTAINED_EXCLUSION = "abstention"
# The one aspect whose numerator is a defect count rather than an agreement count.
DEFECT_ASPECT = "false_authority"

SCOPE_LOCAL = "scope_local"
SCOPE_INHERITED = "scope_inherited"
BINDING_EXPLICIT = "binding_explicit"
BINDING_UNRESOLVED = "binding_unresolved"

PROVIDER_ORDER = ("consultant", "garant", "unknown")
FAMILY_SCOPES = ("holdout", "dev")
EMPTY_STRATUM_WORK_FAMILY = "unassigned"
EMPTY_STRATUM_DRAW = "unassigned"

MEASUREMENT_NOT_MEASURED = "not-measured"
MEASUREMENT_PROXY = "proxy-measured"
MEASUREMENT_INDEPENDENT = "independent-measured"
MEASUREMENT_STATUS_VALUES = (MEASUREMENT_NOT_MEASURED, MEASUREMENT_PROXY, MEASUREMENT_INDEPENDENT)

HOLDOUT_EVALUATION_STATUS = "evaluation"
DEV_EVALUATION_STATUS = "development-only"
DEV_NON_CLAIM_MARKER = "DEVELOPMENT_SLICE_NOT_EVALUATION"

SLICE_REQUIRED_KEYS = (
    "family_scope",
    "evaluation_status",
    "measurement_status",
    "units_total",
    "aspects",
    "units_excluded",
)
SLICE_OPTIONAL_KEYS = ("non_claim",)

RATE_TOLERANCE = 1e-9

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
FORBIDDEN_EXACT_KEYS = frozenset(
    {"seed_span", "rule_seed_span", "rule_seed", "ds_span", "seed_slots"}
)
FORBIDDEN_VALUE_SUBSTRINGS = ("rule_seed", "seed_span", "ds_span", "lawref_seed")
EXEMPT_KEYS = frozenset({"non_claims", "forbidden_keys", "forbidden_seed_keys"})
EXEMPT_KEY_PREFIX = "forbidden_"

# Claim guards (protocol §7): each entry pins one key to its only lawful value.
CLAIM_PINS: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("is_gold", lambda value: value is False, "IS_GOLD_CLAIM"),
    ("human_acceptance", lambda value: value is None, "GOLD_CLAIM"),
    ("promotion", lambda value: value == "none", "PROMOTION_CLAIM"),
    ("threshold", lambda value: value is None, "THRESHOLD_REQUESTED"),
    ("classification", lambda value: value == "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("authority", lambda value: value == "none", "AUTHORITY_CLAIM"),
    ("suggestion_status", lambda value: value == "none-provided", "AUTHORITY_CLAIM"),
    ("legal_claim", lambda value: value == "forbidden", "AUTHORITY_CLAIM"),
    ("n2_claim", lambda value: value == "forbidden", "AUTHORITY_CLAIM"),
    ("model_invoked", lambda value: value is False, "MODEL_INVOKED"),
)
GUARD_KEYS = (
    "is_gold",
    "human_acceptance",
    "promotion",
    "threshold",
    "classification",
    "model_invoked",
)
GUARD_DIAGNOSTIC = {pinned: diagnostic for pinned, _, diagnostic in CLAIM_PINS}
# Keys owned by the pinned claim guard. The leak scanner must not re-report them under a
# second name: ``is_gold`` carries the forbidden token ``gold``, yet it is a lawful key
# whose only lawful value is ``False`` and ``scan_claims`` pins it (IS_GOLD_CLAIM).
# S02 ``INTAKE.forbidden_key_hit`` applies the same exemption.
GUARDED_CLAIM_KEYS = frozenset(pinned for pinned, _, _ in CLAIM_PINS)

DIAGNOSTICS_FROM_INPUT_CONTOUR = (
    "TEST_FIXTURE_IN_STORE",
    "UNFILLED_SUBMISSION",
    "PROVENANCE_NOT_HUMAN",
    "CODER_PASS_INVALID",
    "DUPLICATE_CODER_ID",
    "DUPLICATE_SUBMISSION_ID",
    "UNKNOWN_CASE_ID",
    "SUBMISSION_CONFLICT",
    "SUBMISSION_SCHEMA_DRIFT",
    "NINTH_SLOT",
    "SLOT_SET_DRIFT",
    "SPAN_BEYOND_EOF",
    "SPAN_NOT_UTF8_BOUNDARY",
    "SPAN_NOT_ORIGIN",
    "FRAGMENT_PIN_DRIFT",
    "ABSTENTION_COLLAPSE",
    "VOCABULARY_DRIFT",
    "MISSING_NON_CLAIM",
    "MISSING_LIFECYCLE_MARKER",
    "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
    "ADJUDICATION_NOT_A_DISAGREEMENT",
    "RESOLUTION_OUT_OF_SPACE",
    "RESOLUTION_SPACE_DRIFT",
    "RATIONALE_NOT_BOUNDED",
    "SUPERSEDES_UNKNOWN",
    "ONE_CODER_ONLY",
    "FROZEN_SOURCE_DRIFT",
    "SCHEMA_KEY_DRIFT",
)

MY_DIAGNOSTICS = frozenset(
    {
        "HUMAN_PILOT_ABSENT",
        "MACHINERY_GREEN_HUMAN_ABSENT",
        "NO_ADJUDICATION_INPUT",
        "PROXY_INPUT_REFUSED",
        "UNRESOLVED_NONZERO",
        "RATE_UNDEFINED",
        "COMPUTED_PERFECT_UNBACKED",
        "DENOMINATOR_MISMATCH",
        "MEASUREMENT_STATUS_DRIFT",
        "DEVELOPMENT_SLICE_NOT_EVALUATION",
        "REPORT_WITHOUT_HUMAN_DATA",
        "REPORT_MISSING_WITH_HUMAN_DATA",
        "PROVIDER_STRATUM_DROPPED",
        "PROVIDER_MISATTRIBUTED",
        "PROVIDER_QUOTA_UNJUSTIFIED",
        "ASPECT_TABLE_DRIFT",
        "STRATUM_TABLE_DRIFT",
        "CASE_COUNT_OUT_OF_RANGE",
        "WORK_FAMILY_DOMINANCE",
        "HOLDOUT_LEAKAGE",
        "METADATA_REDERIVED",
        "DIAGNOSTIC_TABLE_DRIFT",
        "GOLD_CLAIM",
        "IS_GOLD_CLAIM",
        "THRESHOLD_REQUESTED",
        "CLASSIFICATION_REQUESTED",
        "PROMOTION_CLAIM",
        "AUTHORITY_CLAIM",
        "MODEL_INVOKED",
        "LEAK_FORBIDDEN_KEY",
        "UNSAFE_PATH",
        "MISSING_ARTIFACT",
        "MISSING_SCHEMA",
        "SCHEMA_PARSE_ERROR",
        "DUPLICATE_JSON_KEY",
    }
) | frozenset(DIAGNOSTICS_FROM_INPUT_CONTOUR)

# The hostile paths this task must make reachable.
HOSTILE_DIAGNOSTICS = (
    "RATE_UNDEFINED",
    "COMPUTED_PERFECT_UNBACKED",
    "PROXY_INPUT_REFUSED",
    "PROVENANCE_NOT_HUMAN",
    "UNRESOLVED_NONZERO",
    "DENOMINATOR_MISMATCH",
    "PROVIDER_STRATUM_DROPPED",
    "DEVELOPMENT_SLICE_NOT_EVALUATION",
    "REPORT_WITHOUT_HUMAN_DATA",
    "REPORT_MISSING_WITH_HUMAN_DATA",
    "GOLD_CLAIM",
    "IS_GOLD_CLAIM",
    "THRESHOLD_REQUESTED",
    "CLASSIFICATION_REQUESTED",
    "PROMOTION_CLAIM",
    "HUMAN_PILOT_ABSENT",
)


# --------------------------------------------------------------------------- #
# Paths and small helpers.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Paths:
    cases: str = CASES_REL
    kit_pass1: str = KIT_PASS1_REL
    kit_pass2: str = KIT_PASS2_REL
    s02_schemas: str = S02_SCHEMAS_REL
    s01_schemas: str = S01_SCHEMAS_REL
    s03_schemas: str = S03_SCHEMAS_REL
    protocol: str = PROTOCOL_REL
    fixture_dir: str = FIXTURE_DIR_REL
    manifest: str = MANIFEST_REL
    submissions: str = SUBMISSIONS_REL
    adjudications: str = ADJUDICATIONS_REL
    intake_record: str = INTAKE_RECORD_REL
    agreement_report: str = AGREEMENT_REPORT_REL
    inventory: str = INVENTORY_REL
    adjudication_record: str = ADJUDICATION_RECORD_REL
    pilot_receipt: str = PILOT_RECEIPT_REL
    report: str = REPORT_REL

    def world(self) -> "_WorldPaths":
        return _WorldPaths(
            cases=self.cases,
            kit_pass1=self.kit_pass1,
            kit_pass2=self.kit_pass2,
            schemas=self.s02_schemas,
            s01_schemas=self.s01_schemas,
            fixture_dir=self.fixture_dir,
        )

    def frozen_source_paths(self) -> tuple[str, ...]:
        return (
            CODEBOOK_REL,
            self.s01_schemas,
            self.cases,
            S02_PROTOCOL_REL,
            self.s02_schemas,
            M199_PROTOCOL_REL,
        )

    def derived_inputs(self) -> tuple[tuple[str, str, str], ...]:
        """``(label, relative path, expected schema id)`` of the five S02 artifacts."""
        return (
            ("intake_record", self.intake_record, INTAKE_RECORD_SCHEMA_ID),
            ("agreement_report", self.agreement_report, AGREEMENT_REPORT_SCHEMA_ID),
            ("disagreement_inventory", self.inventory, INVENTORY_SCHEMA_ID),
            ("adjudication_record", self.adjudication_record, ADJUDICATION_RECORD_SCHEMA_ID),
            ("pilot_receipt", self.pilot_receipt, PILOT_RECEIPT_SCHEMA_ID),
        )


@dataclass(frozen=True)
class _WorldPaths:
    """The ``PathsLike`` bundle ``INTAKE.load_world`` expects."""

    cases: str
    kit_pass1: str
    kit_pass2: str
    schemas: str
    s01_schemas: str
    fixture_dir: str


def sha256_bytes(data: bytes) -> str:
    return INTAKE.sha256_bytes(data)


def sha256_file(path: Path) -> str:
    return INTAKE.sha256_file(path)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GateError("DUPLICATE_JSON_KEY", f"duplicate JSON key {key!r}")
        seen[key] = value
    return seen


def load_json_text(text: str, label: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not valid JSON: {exc}") from exc


def load_json_bytes(raw: bytes, label: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not UTF-8: {exc}") from exc
    return load_json_text(text, label)


def resolve_artifact(
    root: Path, raw: str, label: str, *, suffix: str | None = None, prefix: str | None = None
) -> Path:
    if raw.startswith("/"):
        raise GateError("UNSAFE_PATH", f"{label} {raw!r} must be repository-relative")
    if "\\" in raw or "\x00" in raw:
        raise GateError("UNSAFE_PATH", f"{label} {raw!r} carries an unsafe character")
    relative = PurePosixPath(raw)
    if ".." in relative.parts:
        raise GateError("UNSAFE_PATH", f"{label} {raw!r} may not escape the repository")
    if suffix is not None and not raw.endswith(suffix):
        raise GateError("UNSAFE_PATH", f"{label} {raw!r} must end with {suffix!r}")
    if prefix is not None and not raw.startswith(prefix):
        raise GateError("UNSAFE_PATH", f"{label} {raw!r} must live under {prefix!r}")
    return root / Path(relative)


def read_json(root: Path, raw: str, label: str, *, prefix: str | None = None) -> Any:
    path = resolve_artifact(root, raw, label, suffix=".json", prefix=prefix)
    if not path.is_file():
        raise GateError("MISSING_ARTIFACT", f"{label} not found at {raw}")
    return load_json_bytes(path.read_bytes(), raw)


def is_under(path: Path, parent: Path) -> bool:
    return INTAKE.is_under(path, parent)


def resolve_store(root: Path, raw: str, *, allow_test_fixtures: bool, label: str) -> Path:
    """Resolve a human drop box; synthetic stores live outside the product paths."""
    if allow_test_fixtures:
        if raw.startswith("/"):
            path = Path(raw)
        else:
            relative = PurePosixPath(raw)
            if ".." in relative.parts or "\\" in raw:
                raise GateError("UNSAFE_PATH", f"{label} {raw!r} may not escape the repository")
            path = root / Path(relative)
        if is_under(path, root / ANNOTATION_PREFIX):
            raise GateError(
                "UNSAFE_PATH",
                f"synthetic {label} may never target the product store {ANNOTATION_PREFIX}",
            )
        return path
    path = resolve_artifact(root, raw, label)
    if not is_under(path, root / ANNOTATION_PREFIX):
        raise GateError(
            "UNSAFE_PATH",
            f"{label} {raw!r} must live under {ANNOTATION_PREFIX} (D480 prefix lock)",
        )
    return path


def guard_writable(root: Path, path: Path, label: str) -> None:
    """The engine never writes a store, an input or anything under ``prd/annotation/``."""
    if is_under(path, root / ANNOTATION_PREFIX):
        raise GateError(
            "UNSAFE_PATH",
            f"refusing to write {label} {path} under {ANNOTATION_PREFIX}: the harness never "
            "writes a submission, an adjudication or any annotation input",
        )


def serialize(doc: Any) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json_atomic(root: Path, path: Path, doc: Any, label: str) -> None:
    guard_writable(root, path, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(serialize(doc))
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def check_closed_keys(label: str, node: Any, expected: Sequence[str]) -> None:
    if not isinstance(node, dict):
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} is not an object")
    if sorted(node) != sorted(expected):
        missing = [key for key in expected if key not in node]
        extra = [key for key in node if key not in expected]
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} key drift: missing={missing} extra={extra}")


def require_keys(label: str, node: Any, expected: Sequence[str]) -> None:
    if not isinstance(node, dict):
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} is not an object")
    missing = [key for key in expected if key not in node]
    if missing:
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} misses required key(s) {missing}")


# --------------------------------------------------------------------------- #
# Claim and leak guards.
# --------------------------------------------------------------------------- #


def scan_claims(node: Any, pointer: str = "$", exempt: bool = False) -> None:
    """Refuse a gold / threshold / classification / promotion / authority claim."""
    if isinstance(node, dict):
        for key, value in node.items():
            child_exempt = exempt or key in EXEMPT_KEYS or key.startswith(EXEMPT_KEY_PREFIX)
            if not child_exempt:
                for pinned, predicate, diagnostic in CLAIM_PINS:
                    if key == pinned and not predicate(value):
                        raise GateError(
                            diagnostic,
                            f"{pointer}.{key}={value!r} is a claim this contour may not make",
                        )
            scan_claims(value, f"{pointer}.{key}", child_exempt)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_claims(item, f"{pointer}[{index}]", exempt)


def scan_leak_tokens(node: Any, pointer: str = "$", exempt: bool = False) -> None:
    """Refuse a predicted-answer or rule-seed key anywhere in a document."""
    if isinstance(node, dict):
        for key, value in node.items():
            child_exempt = exempt or key in EXEMPT_KEYS or key.startswith(EXEMPT_KEY_PREFIX)
            if not child_exempt and key not in GUARDED_CLAIM_KEYS:
                tokens = INTAKE.key_tokens(key)
                if key in FORBIDDEN_EXACT_KEYS or any(
                    token in FORBIDDEN_KEY_TOKENS for token in tokens
                ):
                    raise GateError(
                        "LEAK_FORBIDDEN_KEY",
                        f"{pointer}.{key} is a predicted-answer or rule-seed key",
                    )
                if isinstance(value, str) and any(
                    needle in value for needle in FORBIDDEN_VALUE_SUBSTRINGS
                ):
                    raise GateError(
                        "LEAK_FORBIDDEN_KEY",
                        f"{pointer}.{key} carries a rule-seed token in its value",
                    )
            scan_leak_tokens(value, f"{pointer}.{key}", child_exempt)
    elif isinstance(node, list):
        if not exempt and any(
            isinstance(item, str) and item in FORBIDDEN_EXACT_KEYS for item in node
        ):
            raise GateError(
                "LEAK_FORBIDDEN_KEY", f"{pointer} lists a rule-seed key among its elements"
            )
        for index, item in enumerate(node):
            scan_leak_tokens(item, f"{pointer}[{index}]", exempt)


# --------------------------------------------------------------------------- #
# The frozen contract.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Contract:
    schemas: dict[str, Any]
    aspect_names: tuple[str, ...]
    aspect_table: dict[str, dict[str, Any]]
    aspect_closed_keys: tuple[str, ...]
    aspect_excluded: dict[str, tuple[str, ...]]
    denominator_rule: dict[str, Any]
    strata_rule: dict[str, Any]
    publication_contract: dict[str, Any]
    output_contract: dict[str, Any]
    vocabularies: dict[str, Any]
    diagnostics: frozenset[str]
    non_claims: tuple[str, ...]
    lifecycle: dict[str, Any]
    evaluation_report: dict[str, Any]
    stratum_table: dict[str, Any]
    input_admissibility: dict[str, Any]
    slot_keys: tuple[str, ...]
    axes: tuple[str, ...]


def _verify_frozen_sources(root: Path, paths: Paths, schemas: dict[str, Any]) -> None:
    declared = schemas.get("frozen_sources")
    if not isinstance(declared, dict) or not declared:
        raise GateError("MISSING_SCHEMA", "$.frozen_sources is not a frozen source map")
    pinned = {
        entry.get("path"): (key, entry)
        for key, entry in declared.items()
        if isinstance(entry, dict)
    }
    for rel in paths.frozen_source_paths():
        match = pinned.get(rel)
        if match is None:
            raise GateError("FROZEN_SOURCE_DRIFT", f"{rel} is not pinned by $.frozen_sources")
        key, entry = match
        path = resolve_artifact(root, rel, f"frozen source {key}")
        if not path.is_file():
            raise GateError("MISSING_ARTIFACT", f"frozen source {key} not found at {rel}")
        observed = sha256_file(path)
        if observed != entry.get("sha256"):
            raise GateError(
                "FROZEN_SOURCE_DRIFT",
                f"{key} sha256 {observed} != pinned {entry.get('sha256')}",
            )


def _subschema(schemas: dict[str, Any], name: str) -> dict[str, Any]:
    block = (schemas.get("schemas") or {}).get(name)
    if not isinstance(block, dict):
        raise GateError("MISSING_SCHEMA", f"$.schemas.{name} is missing")
    return block


def validate_aspect_table(
    entries: Sequence[Any], closed_keys: tuple[str, ...], axes: tuple[str, ...]
) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[str, ...]]]:
    names = tuple(str(entry.get("aspect")) for entry in entries if isinstance(entry, dict))
    if names != ASPECTS:
        raise GateError(
            "ASPECT_TABLE_DRIFT",
            f"$.aspect_table names {list(names)} instead of the six frozen aspects",
        )
    coverage: set[str] = set()
    table: dict[str, dict[str, Any]] = {}
    excluded_by_aspect: dict[str, tuple[str, ...]] = {}
    for entry in entries:
        name = str(entry.get("aspect"))
        check_closed_keys(f"$.aspect_table[{name}]", entry, closed_keys)
        denominator = entry.get("denominator")
        if not isinstance(denominator, str) or not denominator.strip():
            raise GateError("ASPECT_TABLE_DRIFT", f"aspect {name} declares no denominator")
        if entry.get("value_kind") != "rate":
            raise GateError("ASPECT_TABLE_DRIFT", f"aspect {name} value_kind != 'rate'")
        if entry.get("denominator_units") not in DENOMINATOR_UNITS:
            raise GateError(
                "ASPECT_TABLE_DRIFT",
                f"aspect {name} denominator_units {entry.get('denominator_units')!r} is not frozen",
            )
        excluded = tuple(str(reason) for reason in entry.get("units_excluded_reasons") or ())
        unknown = [reason for reason in excluded if reason not in EXCLUDED_REASONS]
        if unknown:
            raise GateError("ASPECT_TABLE_DRIFT", f"aspect {name} excludes with unknown {unknown}")
        if name == ASPECT_WITHOUT_ABSTAINED_EXCLUSION and ABSTAINED in excluded:
            raise GateError(
                "ABSTENTION_COLLAPSE",
                "the abstention aspect lists 'abstained' among its exclusion reasons: abstention "
                "is the measured outcome there and is never folded away",
            )
        source_axes = tuple(str(axis) for axis in entry.get("source_axes") or ())
        if not source_axes:
            raise GateError("ASPECT_TABLE_DRIFT", f"aspect {name} declares no source axes")
        coverage.update(source_axes)
        table[name] = dict(entry)
        excluded_by_aspect[name] = excluded
    missing = sorted(set(axes) - coverage)
    invented = sorted(coverage - set(axes))
    if missing or invented:
        raise GateError(
            "ASPECT_TABLE_DRIFT",
            f"aspect source axes drift: unconsumed={missing} invented={invented}",
        )
    return table, excluded_by_aspect


def load_contract(root: Path, paths: Paths) -> Contract:
    """Bind the metric contour to the frozen S03 schema document."""
    schemas = read_json(root, paths.s03_schemas, "m207-s03 schemas", prefix=ANNOTATION_PREFIX)
    if schemas.get("schema") != EVAL_SCHEMAS_ID:
        raise GateError(
            "MISSING_SCHEMA",
            f"{paths.s03_schemas} declares schema={schemas.get('schema')!r} != {EVAL_SCHEMAS_ID!r}",
        )
    _verify_frozen_sources(root, paths, schemas)

    diagnostics = schemas.get("diagnostics")
    if not isinstance(diagnostics, list) or not diagnostics:
        raise GateError("MISSING_SCHEMA", "$.diagnostics is not a frozen list")
    table = frozenset(str(name) for name in diagnostics)
    unknown = sorted(name for name in MY_DIAGNOSTICS if name not in table)
    if unknown:
        raise GateError(
            "DIAGNOSTIC_TABLE_DRIFT",
            f"this contour speaks {unknown[:6]} outside the frozen diagnostic table",
        )

    world = _load_world(root, paths)
    axen = tuple(str(axis) for axis in AGREEMENT.load_contract(world).axes)
    slot_keys = tuple(
        axis[len(SLOT_AXIS_PREFIX) :] for axis in axen if axis.startswith(SLOT_AXIS_PREFIX)
    )
    if len(slot_keys) != 8:
        raise GateError("SLOT_SET_DRIFT", f"the frozen axis space carries {len(slot_keys)} slots")

    closed = schemas.get("aspect_closed_keys")
    if not isinstance(closed, list):
        raise GateError("ASPECT_TABLE_DRIFT", "$.aspect_closed_keys is not a list")
    entries = schemas.get("aspect_table")
    if not isinstance(entries, list):
        raise GateError("ASPECT_TABLE_DRIFT", "$.aspect_table is not a list")
    aspect_table, aspect_excluded = validate_aspect_table(
        entries, tuple(str(key) for key in closed), axen
    )

    for key in (
        "denominator_rule",
        "strata_rule",
        "publication_contract",
        "output_contract",
        "vocabularies",
        "non_claims",
        "lifecycle",
        "input_admissibility",
    ):
        if not schemas.get(key):
            raise GateError("MISSING_SCHEMA", f"$.{key} is missing from the frozen contract")

    denominator_rule = schemas["denominator_rule"]
    if denominator_rule.get("zero_denominator_value", "missing") is not None:
        raise GateError("DENOMINATOR_MISMATCH", "$.denominator_rule zero value must be null")
    if denominator_rule.get("zero_denominator_measurement_status") != MEASUREMENT_NOT_MEASURED:
        raise GateError(
            "MEASUREMENT_STATUS_DRIFT",
            "$.denominator_rule zero-denominator status is not 'not-measured'",
        )
    if denominator_rule.get("zero_denominator_diagnostic") != "RATE_UNDEFINED":
        raise GateError("MISSING_SCHEMA", "$.denominator_rule names no zero-denominator diagnostic")
    if denominator_rule.get("imputed_zero_value_forbidden") is not True:
        raise GateError(
            "MISSING_SCHEMA", "$.denominator_rule does not forbid an imputed zero value"
        )

    return Contract(
        schemas=schemas,
        aspect_names=ASPECTS,
        aspect_table=aspect_table,
        aspect_closed_keys=tuple(str(key) for key in closed),
        aspect_excluded=aspect_excluded,
        denominator_rule=denominator_rule,
        strata_rule=schemas["strata_rule"],
        publication_contract=schemas["publication_contract"],
        output_contract=schemas["output_contract"],
        vocabularies=schemas["vocabularies"],
        diagnostics=table,
        non_claims=tuple(str(claim) for claim in schemas["non_claims"]),
        lifecycle=dict(schemas["lifecycle"]),
        evaluation_report=_subschema(schemas, "evaluation_report"),
        stratum_table=_subschema(schemas, "stratum_table"),
        input_admissibility=schemas["input_admissibility"],
        slot_keys=slot_keys,
        axes=axen,
    )


# --------------------------------------------------------------------------- #
# The frozen T02 manifest (holdout split, provider strata).
# --------------------------------------------------------------------------- #


def stratum_id(provider: str, work_family: str, draw_stratum: str, family_scope: str) -> str:
    return f"{provider}|{work_family}|{draw_stratum}|{family_scope}"


@dataclass(frozen=True)
class CaseMeta:
    case_id: str
    work_family: str
    provider: str
    draw_stratum: str
    family_scope: str

    @property
    def stratum_id(self) -> str:
        return stratum_id(self.provider, self.work_family, self.draw_stratum, self.family_scope)


@dataclass(frozen=True)
class Manifest:
    seed: int
    cases: dict[str, CaseMeta]
    holdout_families: tuple[str, ...]
    dev_families: tuple[str, ...]
    declared_providers: tuple[str, ...]
    provider_rows: dict[str, dict[str, Any]]


def stratum_inventory(manifest: Manifest) -> dict[str, dict[str, str]]:
    """Every stratum the report carries: observed combinations plus empty providers.

    A declared provider that attributes no case (today ``garant``) still owns a stratum: it is
    published once per ``family_scope`` with a placeholder Work family and draw stratum, zero
    units and ``value: null``.  Dropping it is ``PROVIDER_STRATUM_DROPPED``.
    """
    inventory: dict[str, dict[str, str]] = {
        case.stratum_id: {
            "stratum_id": case.stratum_id,
            "provider": case.provider,
            "work_family": case.work_family,
            "draw_stratum": case.draw_stratum,
            "family_scope": case.family_scope,
        }
        for case in manifest.cases.values()
    }
    present = {case.provider for case in manifest.cases.values()}
    for provider in manifest.declared_providers:
        if provider in present:
            continue
        for scope in FAMILY_SCOPES:
            identifier = stratum_id(provider, EMPTY_STRATUM_WORK_FAMILY, EMPTY_STRATUM_DRAW, scope)
            inventory.setdefault(
                identifier,
                {
                    "stratum_id": identifier,
                    "provider": provider,
                    "work_family": EMPTY_STRATUM_WORK_FAMILY,
                    "draw_stratum": EMPTY_STRATUM_DRAW,
                    "family_scope": scope,
                },
            )
    return inventory


def load_manifest(root: Path, paths: Paths, universe: Sequence[str]) -> Manifest:
    doc = read_json(root, paths.manifest, "m207-s03 evaluation manifest", prefix=EVIDENCE_PREFIX)
    if doc.get("schema") != MANIFEST_SCHEMA_ID:
        raise GateError(
            "MISSING_ARTIFACT",
            f"{paths.manifest} declares schema={doc.get('schema')!r} != {MANIFEST_SCHEMA_ID!r}",
        )
    raw_cases = doc.get("cases")
    if not isinstance(raw_cases, list) or len(raw_cases) != CASE_COUNT:
        raise GateError(
            "CASE_COUNT_OUT_OF_RANGE",
            "the manifest carries "
            f"{len(raw_cases) if isinstance(raw_cases, list) else 'no'} cases, expected "
            f"{CASE_COUNT}",
        )
    cases: dict[str, CaseMeta] = {}
    for entry in raw_cases:
        case_id = entry.get("case_id")
        if case_id not in universe:
            raise GateError("UNKNOWN_CASE_ID", f"manifest case {case_id!r} is not a frozen case")
        provider = entry.get("provider")
        if provider not in PROVIDER_ORDER:
            raise GateError("PROVIDER_MISATTRIBUTED", f"case {case_id} provider {provider!r}")
        scope = entry.get("family_scope")
        if scope not in FAMILY_SCOPES:
            raise GateError("HOLDOUT_LEAKAGE", f"case {case_id} family_scope {scope!r}")
        family = entry.get("work_family")
        draw = entry.get("draw_stratum")
        if not isinstance(family, str) or not family.strip():
            raise GateError("WORK_FAMILY_DOMINANCE", f"case {case_id} carries no Work family")
        if not isinstance(draw, str) or not draw.strip():
            raise GateError("SCHEMA_KEY_DRIFT", f"case {case_id} carries no draw_stratum")
        if str(entry.get("metadata_source")) != "unknown":
            raise GateError(
                "METADATA_REDERIVED",
                f"case {case_id} carries metadata_source={entry.get('metadata_source')!r}: S03 "
                "never re-derives frozen case metadata",
            )
        cases[str(case_id)] = CaseMeta(
            case_id=str(case_id),
            work_family=family,
            provider=str(provider),
            draw_stratum=draw,
            family_scope=str(scope),
        )
    if len(cases) != CASE_COUNT:
        raise GateError(
            "CASE_COUNT_OUT_OF_RANGE", f"the manifest names {len(cases)} distinct cases"
        )

    holdout = tuple(str(name) for name in doc.get("holdout_families") or ())
    dev = tuple(str(name) for name in doc.get("dev_families") or ())
    if not holdout or not dev:
        raise GateError("HOLDOUT_LEAKAGE", "the frozen manifest declares no holdout/dev split")
    overlap = sorted(set(holdout) & set(dev))
    if overlap:
        raise GateError("HOLDOUT_LEAKAGE", f"families in both slices: {overlap[:4]}")
    for case in cases.values():
        expected = "holdout" if case.work_family in holdout else "dev"
        if case.family_scope != expected:
            raise GateError(
                "HOLDOUT_LEAKAGE",
                f"case {case.case_id} ({case.work_family}) is published {case.family_scope} but "
                f"the frozen family split says {expected}: a Work family is never split",
            )
    family_counts = Counter(case.work_family for case in cases.values())
    biggest = max(family_counts.values()) if family_counts else 0
    if biggest > AGREEMENT.WORK_FAMILY_CAP:
        raise GateError(
            "WORK_FAMILY_DOMINANCE",
            f"a Work family carries {biggest} cases, above the ceiling {AGREEMENT.WORK_FAMILY_CAP}",
        )

    rows = doc.get("provider_strata")
    if not isinstance(rows, list) or not rows:
        raise GateError("PROVIDER_STRATUM_DROPPED", "the manifest declares no provider stratum")
    provider_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        provider = row.get("provider")
        if provider not in PROVIDER_ORDER:
            raise GateError("PROVIDER_MISATTRIBUTED", f"manifest stratum provider {provider!r}")
        availability = row.get("availability")
        quota = row.get("quota")
        if not isinstance(availability, int) or not isinstance(quota, int):
            raise GateError(
                "PROVIDER_QUOTA_UNJUSTIFIED",
                f"stratum {provider} availability/quota must be integers",
            )
        if quota > availability:
            raise GateError(
                "PROVIDER_QUOTA_UNJUSTIFIED",
                f"stratum {provider} quota={quota} > availability={availability}",
            )
        attributed = sum(1 for case in cases.values() if case.provider == provider)
        if attributed != availability:
            raise GateError(
                "PROVIDER_MISATTRIBUTED",
                f"stratum {provider} declares availability={availability} but attributes "
                f"{attributed} frozen cases",
            )
        provider_rows[str(provider)] = dict(row)
    for provider in PROVIDER_ORDER:
        if provider not in provider_rows:
            raise GateError(
                "PROVIDER_STRATUM_DROPPED",
                f"the declared provider vocabulary member {provider!r} has no stratum row",
            )
    seed = doc.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise GateError("SCHEMA_PARSE_ERROR", f"manifest seed={seed!r} is not an integer")
    return Manifest(
        seed=seed,
        cases=cases,
        holdout_families=holdout,
        dev_families=dev,
        declared_providers=tuple(str(row["provider"]) for row in rows),
        provider_rows=provider_rows,
    )


# --------------------------------------------------------------------------- #
# Human inputs and the five derived S02 artifacts.
# --------------------------------------------------------------------------- #


REFUSED_SCHEMA_IDS = frozenset(
    {"npa-quality-receipts/v1", "npa-lawref-seed/v1", "law-nexus-npa-corpus-manifest/v1"}
)
REFUSED_SCHEMA_PREFIXES = ("npa-c5-",)
REFUSED_PROVENANCE = frozenset({"rule-seed"})
REFUSED_FILE_NAMES = frozenset({SEED_SIDECAR_NAME})


@dataclass
class HumanInputs:
    summaries: list[dict[str, Any]]
    codings: dict[int, dict[str, dict[str, Any]]]
    entries: list[Any]
    tips: dict[tuple[str, str], Any]
    inventory_keys: frozenset[tuple[str, str]]
    agreement_sha256: str
    record_sha256: str
    unresolved_count: int

    def submission_refs(self) -> list[dict[str, Any]]:
        return [
            {
                "coder_id": summary["coder_id"],
                "coder_pass": summary["coder_pass"],
                "sha256": summary["sha256"],
                "submission_id": summary["submission_id"],
            }
            for summary in sorted(self.summaries, key=lambda item: item["coder_pass"])
        ]


def refused_schema(schema: Any) -> bool:
    if not isinstance(schema, str):
        return False
    if schema in REFUSED_SCHEMA_IDS:
        return True
    return any(schema.startswith(prefix) for prefix in REFUSED_SCHEMA_PREFIXES)


def proxy_guard(label: str, name: str, doc: Any) -> None:
    """A proxy or machine artifact is never an evaluation input (PROXY_INPUT_REFUSED)."""
    if Path(name).name in REFUSED_FILE_NAMES:
        raise GateError(
            "PROXY_INPUT_REFUSED",
            f"{label} is the rule-seed sidecar {name!r}: a producer surface is never consumed",
        )
    if not isinstance(doc, dict):
        return
    schema = doc.get("schema")
    if refused_schema(schema):
        raise GateError("PROXY_INPUT_REFUSED", f"{label} declares refused schema {schema!r}")
    provenance = doc.get("provenance")
    if provenance in REFUSED_PROVENANCE:
        raise GateError(
            "PROXY_INPUT_REFUSED", f"{label} declares refused provenance {provenance!r}"
        )
    if doc.get("measurement_status") == MEASUREMENT_PROXY:
        raise GateError(
            "PROXY_INPUT_REFUSED",
            f"{label} declares measurement_status='{MEASUREMENT_PROXY}': a proxy measurement is "
            "never an independent human reference",
        )


def load_derived(root: Path, paths: Paths) -> dict[str, Any]:
    """Load the five frozen S02 derived artifacts, fail-closed and claim-guarded."""
    loaded: dict[str, Any] = {}
    for label, rel, expected in paths.derived_inputs():
        path = resolve_artifact(root, rel, label, suffix=".json", prefix=EVIDENCE_PREFIX)
        if not path.is_file():
            raise GateError(
                "REPORT_MISSING_WITH_HUMAN_DATA",
                f"the human reference exists but {rel} is missing: the evaluation chain is "
                "incomplete and no S03 number may be published",
            )
        doc = load_json_bytes(path.read_bytes(), rel)
        proxy_guard(label, Path(rel).name, doc)
        schema = doc.get("schema") if isinstance(doc, dict) else None
        if schema != expected:
            raise GateError(
                "SCHEMA_KEY_DRIFT",
                f"{rel} declares schema={schema!r} != the frozen {expected!r}",
            )
        scan_claims(doc)
        scan_leak_tokens(doc)
        loaded[label] = doc
        loaded[f"{label}_sha256"] = sha256_file(path)
    if loaded["adjudication_record"].get("adjudicator_provenance") != "human-reviewed":
        raise GateError(
            "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
            "the adjudication record was not produced by a human adjudicator",
        )
    receipt = loaded["pilot_receipt"]
    if receipt.get("human_pilot_performed") is not True:
        raise GateError(
            "HUMAN_PILOT_ABSENT", "the pilot receipt does not attest a performed human pilot"
        )
    if int(receipt.get("coder_count") or 0) < len(PASSES):
        raise GateError("ONE_CODER_ONLY", "the pilot receipt attests fewer than two coders")
    if int(receipt.get("adjudicator_count") or 0) < 1:
        raise GateError("NO_ADJUDICATION_INPUT", "the pilot receipt attests no human adjudicator")
    return loaded


def discover_human_inputs(root: Path, paths: Paths, *, allow_test_fixtures: bool) -> HumanInputs:
    """Read the two human stores; an absent or empty store is a blockage, not a defect."""
    submissions_store = resolve_store(
        root, paths.submissions, allow_test_fixtures=allow_test_fixtures, label="submission store"
    )
    submission_files = INTAKE.discover_submissions(submissions_store)
    adjudications_store = resolve_store(
        root,
        paths.adjudications,
        allow_test_fixtures=allow_test_fixtures,
        label="adjudication store",
    )
    adjudication_files = ADJ.discover_adjudications(adjudications_store, agreement_frozen=True)
    for store_file in list(submission_files) + list(adjudication_files):
        try:
            doc = load_json_text(store_file.raw.decode("utf-8"), store_file.name)
        except GateError:
            continue
        proxy_guard(store_file.name, store_file.name, doc)

    world = _load_world(root, paths)
    failures: Failures = []
    summaries = INTAKE.evaluate_store(
        submission_files, world, allow_test_fixtures=allow_test_fixtures, failures=failures
    )
    if failures:
        raise GateError(failures[0][0], failures[0][1])
    codings: dict[int, dict[str, dict[str, Any]]] = {1: {}, 2: {}}
    by_name = {store_file.name: store_file for store_file in submission_files}
    for summary in summaries:
        store_file = by_name.get(summary["name"])
        if store_file is None:  # pragma: no cover - defensive
            raise GateError("MISSING_ARTIFACT", f"admitted submission {summary['name']} vanished")
        envelope = load_json_text(store_file.raw.decode("utf-8"), store_file.name)
        for case in envelope.get("cases") or ():
            codings[int(summary["coder_pass"])][str(case.get("case_id"))] = case
    for coder_pass in PASSES:
        if not codings[coder_pass]:
            raise GateError("ONE_CODER_ONLY", f"pass {coder_pass} admitted no coding")
    coder_ids = {summary["coder_pass"]: summary["coder_id"] for summary in summaries}
    if len(set(coder_ids.values())) != len(coder_ids):
        raise GateError("DUPLICATE_CODER_ID", "both passes carry the same coder_id")

    derived = load_derived(root, paths)
    agreement_sha = sha256_file(
        resolve_artifact(
            root, paths.agreement_report, "agreement report", suffix=".json", prefix=EVIDENCE_PREFIX
        )
    )
    record_sha = sha256_file(
        resolve_artifact(
            root,
            paths.adjudication_record,
            "adjudication record",
            suffix=".json",
            prefix=EVIDENCE_PREFIX,
        )
    )
    if derived["adjudication_record"].get("pre_adjudication_agreement_sha256") != agreement_sha:
        raise GateError(
            "FROZEN_SOURCE_DRIFT",
            "the adjudication record is not pinned to the sha256 of the frozen pre-adjudication "
            "agreement report",
        )
    if derived["pilot_receipt"].get("adjudication_record_sha256") != record_sha:
        raise GateError(
            "FROZEN_SOURCE_DRIFT", "the pilot receipt is not pinned to the adjudication record"
        )
    for coder_pass in PASSES:
        pinned = {
            row.get("submission_id"): row.get("sha256")
            for row in derived["intake_record"].get("submissions") or ()
            if row.get("coder_pass") == coder_pass
        }
        actual = {
            summary["submission_id"]: summary["sha256"]
            for summary in summaries
            if summary["coder_pass"] == coder_pass
        }
        if pinned != actual:
            raise GateError(
                "FROZEN_SOURCE_DRIFT",
                f"the intake record pins pass {coder_pass} digests that no longer match the store",
            )

    inventory_keys = frozenset(
        (str(entry.get("case_id")), str(entry.get("axis")))
        for entry in derived["disagreement_inventory"].get("entries") or ()
    )
    entries, failures = _validate_adjudications(
        root,
        paths,
        adjudication_files,
        inventory_keys=inventory_keys,
        allow_test_fixtures=allow_test_fixtures,
    )
    if failures:
        raise GateError(failures[0][0], failures[0][1])
    tips = ADJ.resolution_tips(entries)
    unresolved_count = derived["adjudication_record"].get("unresolved_count")
    if unresolved_count != 0:
        raise GateError(
            "UNRESOLVED_NONZERO",
            f"the human adjudication record leaves unresolved_count={unresolved_count}: a "
            "partially resolved reference is a refusal, not a low rate",
        )
    missing = sorted(inventory_keys - frozenset(tips))
    if missing:
        raise GateError(
            "UNRESOLVED_NONZERO",
            f"{len(missing)} frozen disagreement(s) have no adjudication tip, e.g. {missing[:3]}",
        )
    return HumanInputs(
        summaries=list(summaries),
        codings=codings,
        entries=list(entries),
        tips=tips,
        inventory_keys=inventory_keys,
        agreement_sha256=agreement_sha,
        record_sha256=record_sha,
        unresolved_count=int(unresolved_count),
    )


def _load_world(root: Path, paths: Paths) -> Any:
    failures: Failures = []
    world = INTAKE.load_world(root, paths.world(), failures)
    if world is None or failures:
        raise GateError(
            "MISSING_ARTIFACT", f"the frozen S01/S02 world could not be bound: {failures[:2]}"
        )
    return world


def _validate_adjudications(
    root: Path,
    paths: Paths,
    files: Sequence[Any],
    *,
    inventory_keys: frozenset[tuple[str, str]],
    allow_test_fixtures: bool,
) -> tuple[list[Any], Failures]:
    failures: Failures = []
    world = _load_world(root, paths)
    contract = ADJ.load_contract(world)
    entries = ADJ.evaluate_store(
        files,
        contract=contract,
        inventory_keys=inventory_keys,
        universe=world.universe,
        world=world,
        allow_test_fixtures=allow_test_fixtures,
        failures=failures,
    )
    return entries, failures


def human_data_present(root: Path, paths: Paths, *, allow_test_fixtures: bool) -> bool:
    """Cheap presence probe: both human stores hold at least one ``*.json``."""
    for raw, label in ((paths.submissions, "submission"), (paths.adjudications, "adjudication")):
        try:
            store = resolve_store(
                root, raw, allow_test_fixtures=allow_test_fixtures, label=f"{label} store"
            )
        except GateError:
            return False
        if not store.is_dir():
            return False
        if not any(path.is_file() and path.suffix == ".json" for path in store.iterdir()):
            return False
    return True


def report_path(root: Path, paths: Paths) -> Path:
    return resolve_artifact(
        root, paths.report, "evaluation report", suffix=".json", prefix=EVIDENCE_PREFIX
    )


def enforce_human_report_invariant(
    *, human_present: bool, report_present: bool, writing: bool
) -> None:
    """The machine-checked invariant: a report exists iff a human reference exists."""
    if report_present and not human_present:
        raise GateError(
            "REPORT_WITHOUT_HUMAN_DATA",
            "an evaluation report exists without a validated human reference: a metric without a "
            "human reference is never lawful",
        )
    if human_present and not report_present and not writing:
        raise GateError(
            "REPORT_MISSING_WITH_HUMAN_DATA",
            "the human reference exists and is validated but no evaluation report is published",
        )


# --------------------------------------------------------------------------- #
# Reference resolution: the only lawful source of a measured value.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Pairing:
    """One case's two codings, the resolved reference per axis and the exclusion reasons."""

    case_id: str
    raw_cases: dict[int, dict[str, Any]]
    observations: dict[int, dict[str, str | None]]
    resolved: dict[str, str]
    reasons: dict[str, str]

    def reason(self, axis: str) -> str:
        return self.reasons.get(axis, UNRESOLVED)

    def decision(self) -> str | None:
        return self.resolved.get(REFERENCE_DECISION_AXIS)

    def resolved_present(self, key: str) -> bool:
        return self.resolved.get(f"{SLOT_AXIS_PREFIX}{key}") == SLOT_PRESENT

    def pass_present(self, coder_pass: int, key: str) -> bool:
        return AGREEMENT.slot_is_present(self.raw_cases[coder_pass].get("slots"), key)

    def scope_label(self) -> str | None:
        return scope_label(self.resolved_present)

    def binding_label(self) -> str | None:
        return binding_label(self.resolved_present)

    def span_value(self) -> str | None:
        return self.resolved.get(SPAN_EXACT_AXIS)


def map_resolution(axis: str, resolution: str, left: str, right: str) -> str:
    """Turn an adjudicated resolution into the axis value it names."""
    if axis == SPAN_EXACT_AXIS:
        if resolution == "span_pass_1":
            return left
        if resolution == "span_pass_2":
            return right
        raise GateError(
            "RESOLUTION_OUT_OF_SPACE",
            f"span resolution {resolution!r} is not one of the two committed coder spans",
        )
    return resolution


def scope_label(present: Callable[[str], bool]) -> str | None:
    """D490 scope derivation over the frozen slots (no ninth slot, no schema bump)."""
    if present("hier_nums") or present("doc_no") or present("law_code"):
        return SCOPE_LOCAL
    if present("marker_chain"):
        return SCOPE_INHERITED
    return None


def binding_label(present: Callable[[str], bool]) -> str | None:
    """D490 binding derivation over the frozen slots."""
    if present("anaphora") or present("range"):
        return BINDING_UNRESOLVED
    if present("hier_nums") or present("doc_no") or present("law_code") or present("marker_chain"):
        return BINDING_EXPLICIT
    return None


def resolve_reference(
    contract: Contract,
    codings: dict[int, dict[str, dict[str, Any]]],
    universe: Sequence[str],
    tips: dict[tuple[str, str], Any],
) -> dict[str, Pairing]:
    """Resolve one value per ``case_id x axis``; an unresolved axis excludes its units."""
    pairings: dict[str, Pairing] = {}
    for case_id in universe:
        observations: dict[int, dict[str, str | None]] = {}
        raw_cases: dict[int, dict[str, Any]] = {}
        for coder_pass in PASSES:
            case = codings[coder_pass][case_id]
            raw_cases[coder_pass] = dict(case)
            observations[coder_pass] = {
                axis: AGREEMENT.case_observation(case, axis) for axis in contract.axes
            }
        resolved: dict[str, str] = {}
        reasons: dict[str, str] = {}
        for axis in contract.axes:
            left = observations[CODER_PASS_ONE][axis]
            right = observations[CODER_PASS_TWO][axis]
            if left is None or right is None:
                reasons[axis] = ABSTAINED
                continue
            if left == right:
                resolved[axis] = left
                continue
            tip = tips.get((case_id, axis))
            if tip is None:
                reasons[axis] = UNRESOLVED
                continue
            resolved[axis] = map_resolution(axis, tip.resolution, left, right)
        pairings[case_id] = Pairing(
            case_id=case_id,
            raw_cases=raw_cases,
            observations=observations,
            resolved=resolved,
            reasons=reasons,
        )
    return pairings


# --------------------------------------------------------------------------- #
# The measurement core: units, confusion matrices, honest rates.
# --------------------------------------------------------------------------- #

Cell = tuple[bool, bool, bool, bool]


def span_cell(match: bool) -> Cell:
    return (match, not match, False, False)


def presence_cell(pass_positive: bool, truth_positive: bool) -> Cell:
    return (
        pass_positive and truth_positive,
        pass_positive and not truth_positive,
        (not pass_positive) and truth_positive,
        (not pass_positive) and not truth_positive,
    )


def label_cell(pass_label: str | None, truth_label: str | None, positive: str) -> Cell:
    """A pass label that cannot be derived is a negative prediction, never a silent match."""
    return presence_cell(pass_label == positive, truth_label == positive)


@dataclass(frozen=True)
class UnitRecord:
    """One classifiable unit: one case (eight keys for ``slot``) and one pass observation."""

    case_id: str
    subkey: str | None
    meta: CaseMeta
    labels: dict[int, str]
    matches: dict[int, bool]
    cells: dict[int, Cell]
    defect: dict[int, int]

    def numerator(self, coder_pass: int, aspect: str) -> int:
        if aspect == DEFECT_ASPECT:
            return self.defect[coder_pass]
        return int(self.matches[coder_pass])


@dataclass
class PassStats:
    population: int = 0
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0
    true_negative: int = 0
    numerator: int = 0

    def precision(self) -> Fraction | None:
        denominator = self.true_positive + self.false_positive
        return Fraction(self.true_positive, denominator) if denominator else None

    def recall(self) -> Fraction | None:
        denominator = self.true_positive + self.false_negative
        return Fraction(self.true_positive, denominator) if denominator else None

    @property
    def covered(self) -> bool:
        return (
            self.true_positive + self.false_positive + self.false_negative + self.true_negative
            == self.population
        )


@dataclass
class Aggregate:
    stats: dict[int, PassStats]
    measured: int
    denominator: int


def aggregate_units(units: Sequence[UnitRecord], aspect: str) -> Aggregate:
    stats = {coder_pass: PassStats() for coder_pass in PASSES}
    measured = 0
    denominator = 0
    for unit in units:
        for coder_pass in PASSES:
            stat = stats[coder_pass]
            cell = unit.cells[coder_pass]
            stat.population += 1
            stat.true_positive += int(cell[0])
            stat.false_positive += int(cell[1])
            stat.false_negative += int(cell[2])
            stat.true_negative += int(cell[3])
            numerator = unit.numerator(coder_pass, aspect)
            stat.numerator += numerator
            measured += numerator
            denominator += 1
    aggregate = Aggregate(stats=stats, measured=measured, denominator=denominator)
    check_denominator_consistency(aspect, aggregate)
    return aggregate


def check_denominator_consistency(aspect: str, aggregate: Aggregate) -> None:
    """The published denominator must be exactly the population it claims to describe."""
    total = sum(stat.population for stat in aggregate.stats.values())
    if total != aggregate.denominator:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"aspect {aspect}: per-pass populations sum to {total} != denominator "
            f"{aggregate.denominator}",
        )
    if aggregate.measured < 0 or aggregate.measured > aggregate.denominator:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"aspect {aspect}: measured={aggregate.measured} is outside "
            f"[0, {aggregate.denominator}]",
        )
    for coder_pass, stat in aggregate.stats.items():
        if stat.numerator > stat.population:
            raise GateError(
                "DENOMINATOR_MISMATCH",
                f"aspect {aspect} pass {coder_pass}: numerator {stat.numerator} exceeds its "
                f"population {stat.population}",
            )


def assert_value_backed(
    value: Fraction | None, measured: int, denominator: int, covered: bool
) -> None:
    """A 1.0 is lawful only as a computed value with a positive numerator and full coverage."""
    if value is None or value != 1:
        return
    if measured <= 0:
        raise GateError(
            "COMPUTED_PERFECT_UNBACKED",
            "a perfect value is published with measured=0: emptiness is not coverage",
        )
    if not covered:
        raise GateError(
            "COMPUTED_PERFECT_UNBACKED",
            "a perfect value is published without full coverage of the declared denominator",
        )


@dataclass(frozen=True)
class Rate:
    measured: int
    denominator: int
    value: Fraction | None
    measurement_status: str
    note: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "measured": self.measured,
            "denominator": self.denominator,
            "value": None if self.value is None else float(self.value),
            "measurement_status": self.measurement_status,
        }


def rate_of(aggregate: Aggregate, status_when_measured: str) -> Rate:
    """D489: no value without a positive denominator, and never an imputed 0.0 or 1.0."""
    denominator = aggregate.denominator
    if denominator == 0:
        return Rate(
            measured=0,
            denominator=0,
            value=None,
            measurement_status=MEASUREMENT_NOT_MEASURED,
            note="RATE_UNDEFINED",
        )
    value = Fraction(aggregate.measured, denominator)
    covered = all(stat.covered for stat in aggregate.stats.values())
    assert_value_backed(value, aggregate.measured, denominator, covered)
    return Rate(
        measured=aggregate.measured,
        denominator=denominator,
        value=value,
        measurement_status=status_when_measured,
        note=None,
    )


def aspect_units(
    aspect: str,
    contract: Contract,
    manifest: Manifest,
    pairings: dict[str, Pairing],
    universe: Sequence[str],
) -> tuple[list[UnitRecord], list[tuple[str, str]]]:
    """Every classifiable unit of one aspect, plus every excluded case with its reason."""
    units: list[UnitRecord] = []
    excluded: list[tuple[str, str]] = []
    source_axes = tuple(str(axis) for axis in contract.aspect_table[aspect]["source_axes"])
    for case_id in universe:
        pairing = pairings[case_id]
        meta = manifest.cases[case_id]
        if aspect != ASPECT_WITHOUT_ABSTAINED_EXCLUSION and any(
            pairing.observations[coder_pass][axis] is None
            for coder_pass in PASSES
            for axis in source_axes
        ):
            excluded.append((case_id, ABSTAINED))
            continue
        if aspect == "slot":
            produced, reason = _slot_units(case_id, meta, contract, pairing)
        else:
            produced, reason = _single_unit(aspect, case_id, meta, pairing)
        if not produced:
            excluded.append((case_id, reason))
            continue
        units.extend(produced)
    return units, excluded


def _single_unit(
    aspect: str, case_id: str, meta: CaseMeta, pairing: Pairing
) -> tuple[list[UnitRecord], str]:
    decision = pairing.decision()
    if aspect == "abstention":
        truth = pairing.resolved.get(ABSTENTION_AXIS)
        if truth is None:
            return [], pairing.reason(ABSTENTION_AXIS)
        labels = {
            coder_pass: str(pairing.observations[coder_pass][ABSTENTION_AXIS])
            for coder_pass in PASSES
        }
        if any(label == "None" for label in labels.values()):  # pragma: no cover - defensive
            return [], ABSTAINED
        return [
            UnitRecord(
                case_id=case_id,
                subkey=None,
                meta=meta,
                labels=labels,
                matches={coder_pass: label == truth for coder_pass, label in labels.items()},
                cells={
                    coder_pass: presence_cell(label != NON_ABSTAINED, truth != NON_ABSTAINED)
                    for coder_pass, label in labels.items()
                },
                defect={},
            )
        ], ""
    if decision is None:
        return [], pairing.reason(REFERENCE_DECISION_AXIS)
    if aspect == DEFECT_ASPECT:
        if decision != NOT_A_REFERENCE:
            return [], NOT_DERIVABLE
        labels = {
            coder_pass: str(pairing.observations[coder_pass][REFERENCE_DECISION_AXIS])
            for coder_pass in PASSES
        }
        return [
            UnitRecord(
                case_id=case_id,
                subkey=None,
                meta=meta,
                labels=labels,
                matches={coder_pass: False for coder_pass in PASSES},
                cells={
                    coder_pass: (False, label == REFERENCE, False, label != REFERENCE)
                    for coder_pass, label in labels.items()
                },
                defect={
                    coder_pass: int(label == REFERENCE) for coder_pass, label in labels.items()
                },
            )
        ], ""
    if decision != REFERENCE:
        return [], UNDISPUTED_MISSING
    if aspect == "span":
        truth = pairing.span_value()
        if truth is None:
            return [], pairing.reason(SPAN_EXACT_AXIS)
        committed = {pairing.observations[coder_pass][SPAN_EXACT_AXIS] for coder_pass in PASSES}
        if truth not in committed:
            return [], NOT_DERIVABLE
        labels = {
            coder_pass: str(pairing.observations[coder_pass][SPAN_EXACT_AXIS])
            for coder_pass in PASSES
        }
        matches = {coder_pass: label == truth for coder_pass, label in labels.items()}
        return [
            UnitRecord(
                case_id=case_id,
                subkey=None,
                meta=meta,
                labels=labels,
                matches=matches,
                cells={coder_pass: span_cell(match) for coder_pass, match in matches.items()},
                defect={},
            )
        ], ""
    if aspect == "scope":
        truth = pairing.scope_label()
        if truth is None:
            return [], NOT_DERIVABLE
        labels = {
            coder_pass: scope_label(
                lambda key, coder_pass=coder_pass: pairing.pass_present(coder_pass, key)
            )
            for coder_pass in PASSES
        }
        return [
            UnitRecord(
                case_id=case_id,
                subkey=None,
                meta=meta,
                labels={
                    coder_pass: label if label is not None else "not-derivable"
                    for coder_pass, label in labels.items()
                },
                matches={coder_pass: label == truth for coder_pass, label in labels.items()},
                cells={
                    coder_pass: label_cell(label, truth, SCOPE_INHERITED)
                    for coder_pass, label in labels.items()
                },
                defect={},
            )
        ], ""
    if aspect == "binding":
        truth = pairing.binding_label()
        if truth is None:
            return [], NOT_DERIVABLE
        labels = {
            coder_pass: binding_label(
                lambda key, coder_pass=coder_pass: pairing.pass_present(coder_pass, key)
            )
            for coder_pass in PASSES
        }
        return [
            UnitRecord(
                case_id=case_id,
                subkey=None,
                meta=meta,
                labels={
                    coder_pass: label if label is not None else "not-derivable"
                    for coder_pass, label in labels.items()
                },
                matches={coder_pass: label == truth for coder_pass, label in labels.items()},
                cells={
                    coder_pass: label_cell(label, truth, BINDING_UNRESOLVED)
                    for coder_pass, label in labels.items()
                },
                defect={},
            )
        ], ""
    raise GateError("ASPECT_TABLE_DRIFT", f"no measurement rule for aspect {aspect!r}")


def _slot_units(
    case_id: str, meta: CaseMeta, contract: Contract, pairing: Pairing
) -> tuple[list[UnitRecord], str]:
    """The ``slot`` aspect is eight independent per-key units, as the frozen table declares."""
    decision = pairing.decision()
    if decision is None:
        return [], pairing.reason(REFERENCE_DECISION_AXIS)
    if decision != REFERENCE:
        return [], UNDISPUTED_MISSING
    units: list[UnitRecord] = []
    for key in contract.slot_keys:
        axis = f"{SLOT_AXIS_PREFIX}{key}"
        truth = pairing.resolved.get(axis)
        if truth is None:
            return [], pairing.reason(axis)
        labels = {coder_pass: str(pairing.observations[coder_pass][axis]) for coder_pass in PASSES}
        if any(label == "None" for label in labels.values()):  # pragma: no cover - defensive
            return [], ABSTAINED
        units.append(
            UnitRecord(
                case_id=case_id,
                subkey=key,
                meta=meta,
                labels=labels,
                matches={coder_pass: label == truth for coder_pass, label in labels.items()},
                cells={
                    coder_pass: presence_cell(label == SLOT_PRESENT, truth == SLOT_PRESENT)
                    for coder_pass, label in labels.items()
                },
                defect={},
            )
        )
    return units, ""


@dataclass
class AspectMeasurement:
    aspect: str
    units: list[UnitRecord]
    excluded: list[tuple[str, str]]

    def aggregate(self, *, scope: str | None = None) -> Aggregate:
        selected = (
            self.units
            if scope is None
            else [unit for unit in self.units if unit.meta.family_scope == scope]
        )
        return aggregate_units(selected, self.aspect)

    def excluded_for(self, manifest: Manifest, *, scope: str | None = None) -> list[dict[str, str]]:
        rows = []
        for case_id, reason in self.excluded:
            if scope is not None and manifest.cases[case_id].family_scope != scope:
                continue
            rows.append({"case_id": case_id, "aspect": self.aspect, "reason": reason})
        return rows


def measure_all(
    contract: Contract, manifest: Manifest, pairings: dict[str, Pairing], universe: Sequence[str]
) -> dict[str, AspectMeasurement]:
    return {
        aspect: AspectMeasurement(
            aspect=aspect,
            units=(produced := aspect_units(aspect, contract, manifest, pairings, universe))[0],
            excluded=produced[1],
        )
        for aspect in contract.aspect_names
    }


# --------------------------------------------------------------------------- #
# The evaluation report.
# --------------------------------------------------------------------------- #


def per_pass_rows(aggregate: Aggregate) -> list[dict[str, Any]]:
    rows = []
    for coder_pass in PASSES:
        stat = aggregate.stats[coder_pass]
        precision = stat.precision()
        recall = stat.recall()
        rows.append(
            {
                "coder_pass": coder_pass,
                "true_positive": stat.true_positive,
                "false_positive": stat.false_positive,
                "false_negative": stat.false_negative,
                "true_negative": stat.true_negative,
                "precision": None if precision is None else float(precision),
                "recall": None if recall is None else float(recall),
            }
        )
    return rows


def stratum_rows(
    measurement: AspectMeasurement,
    inventory: dict[str, dict[str, str]],
    status_when_measured: str,
) -> list[dict[str, Any]]:
    rows = []
    for identifier in sorted(inventory):
        selected = [unit for unit in measurement.units if unit.meta.stratum_id == identifier]
        rate = rate_of(aggregate_units(selected, measurement.aspect), status_when_measured)
        rows.append({"stratum_id": identifier, "aspect": measurement.aspect, **rate.as_dict()})
    return rows


def aspect_row(
    contract: Contract,
    measurement: AspectMeasurement,
    manifest: Manifest,
    *,
    scope: str | None,
    status_when_measured: str,
    strata: list[dict[str, Any]],
) -> dict[str, Any]:
    rate = rate_of(measurement.aggregate(scope=scope), status_when_measured)
    return {
        "aspect": measurement.aspect,
        **rate.as_dict(),
        "per_pass": per_pass_rows(measurement.aggregate(scope=scope)),
        "strata": strata,
        "units_excluded": len(measurement.excluded_for(manifest, scope=scope)),
        "units_excluded_reasons": list(contract.aspect_excluded[measurement.aspect]),
    }


def build_slice(
    contract: Contract,
    measurements: dict[str, AspectMeasurement],
    manifest: Manifest,
    inventory: dict[str, dict[str, str]],
    *,
    scope: str,
    units_total: int,
) -> dict[str, Any]:
    """The holdout slice is the evaluation; the dev slice is never independent evidence."""
    if scope == "holdout":
        status = MEASUREMENT_INDEPENDENT
        evaluation_status = HOLDOUT_EVALUATION_STATUS
        extra: dict[str, Any] = {}
    else:
        status = MEASUREMENT_PROXY
        evaluation_status = DEV_EVALUATION_STATUS
        extra = {"non_claim": DEV_NON_CLAIM_MARKER}
    excluded: list[dict[str, str]] = []
    aspects = []
    for aspect in contract.aspect_names:
        measurement = measurements[aspect]
        excluded.extend(measurement.excluded_for(manifest, scope=scope))
        aspects.append(
            aspect_row(
                contract,
                measurement,
                manifest,
                scope=scope,
                status_when_measured=status,
                strata=stratum_rows(measurement, inventory, status),
            )
        )
    return {
        "family_scope": scope,
        "evaluation_status": evaluation_status,
        "measurement_status": status,
        "units_total": units_total,
        "aspects": aspects,
        "units_excluded": sorted(excluded, key=lambda row: (row["case_id"], row["aspect"])),
        **extra,
    }


def build_report(
    contract: Contract,
    manifest: Manifest,
    measurements: dict[str, AspectMeasurement],
    human: HumanInputs,
    universe: Sequence[str],
) -> tuple[dict[str, Any], list[str]]:
    """The frozen evaluation report: typed publication, honest denominators, no claims."""
    inventory = stratum_inventory(manifest)
    notes: list[str] = []
    aspects: list[dict[str, Any]] = []
    strata: list[dict[str, Any]] = []
    for aspect in contract.aspect_names:
        measurement = measurements[aspect]
        rows = stratum_rows(measurement, inventory, MEASUREMENT_INDEPENDENT)
        strata.extend(rows)
        aspects.append(
            aspect_row(
                contract,
                measurement,
                manifest,
                scope=None,
                status_when_measured=MEASUREMENT_INDEPENDENT,
                strata=rows,
            )
        )
        if measurement.aggregate().denominator == 0:
            notes.append("RATE_UNDEFINED")
    excluded: list[dict[str, str]] = []
    for aspect in contract.aspect_names:
        excluded.extend(measurements[aspect].excluded_for(manifest))
    excluded.sort(key=lambda row: (row["aspect"], row["case_id"]))
    report = {
        "schema": REPORT_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "framing": contract.publication_contract.get("framing"),
        "model_invoked": False,
        "measurement_status": contract.publication_contract.get("admissible_measurement_status"),
        "is_gold": False,
        "promotion": "none",
        "threshold": None,
        "classification": "not-authorized",
        "human_acceptance": None,
        "independent_reference": {
            "submission_refs": human.submission_refs(),
            "adjudication_sha256": human.record_sha256,
            "unresolved_count": human.unresolved_count,
            "pre_adjudication_agreement_sha256": human.agreement_sha256,
        },
        "aspects": aspects,
        "strata": sorted(strata, key=lambda row: (row["stratum_id"], row["aspect"])),
        "holdout": build_slice(
            contract,
            measurements,
            manifest,
            inventory,
            scope="holdout",
            units_total=sum(
                1 for case in manifest.cases.values() if case.family_scope == "holdout"
            ),
        ),
        "dev": build_slice(
            contract,
            measurements,
            manifest,
            inventory,
            scope="dev",
            units_total=sum(1 for case in manifest.cases.values() if case.family_scope == "dev"),
        ),
        "units_total": len(universe),
        "units_excluded": excluded,
        "lifecycle": dict(contract.lifecycle),
        "non_claims": list(contract.non_claims),
    }
    return report, sorted(set(notes))


# --------------------------------------------------------------------------- #
# Report validation: shape, guards and recomputation.
# --------------------------------------------------------------------------- #


def check_published_rate(
    label: str,
    row: dict[str, Any],
    *,
    allowed_statuses: Sequence[str],
    not_measured_status: str = MEASUREMENT_NOT_MEASURED,
) -> None:
    measured = row.get("measured")
    denominator = row.get("denominator")
    value = row.get("value")
    status = row.get("measurement_status")
    if not isinstance(measured, int) or isinstance(measured, bool):
        raise GateError("DENOMINATOR_MISMATCH", f"{label}.measured is not an integer")
    if not isinstance(denominator, int) or isinstance(denominator, bool):
        raise GateError("DENOMINATOR_MISMATCH", f"{label}.denominator is not an integer")
    if status not in MEASUREMENT_STATUS_VALUES:
        raise GateError("MEASUREMENT_STATUS_DRIFT", f"{label}.measurement_status={status!r}")
    if denominator == 0:
        if value is not None:
            raise GateError(
                "RATE_UNDEFINED",
                f"{label} publishes value={value!r} with denominator=0: an absent denominator is "
                "not a measurement and must never read like 0.0 or 1.0",
            )
        if measured != 0:
            raise GateError("DENOMINATOR_MISMATCH", f"{label} measures {measured} of zero units")
        if status != not_measured_status:
            raise GateError(
                "MEASUREMENT_STATUS_DRIFT",
                f"{label} has no denominator but claims measurement_status={status!r}",
            )
        return
    if value is None:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"{label} carries denominator={denominator} but publishes no value",
        )
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GateError("DENOMINATOR_MISMATCH", f"{label}.value={value!r} is not a number")
    if not 0.0 <= float(value) <= 1.0:
        raise GateError("DENOMINATOR_MISMATCH", f"{label}.value={value!r} is outside [0, 1]")
    expected = measured / denominator
    if abs(float(value) - expected) > RATE_TOLERANCE:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"{label} publishes value={value!r} but {measured}/{denominator}={expected!r}",
        )
    if status not in allowed_statuses:
        raise GateError(
            "MEASUREMENT_STATUS_DRIFT",
            f"{label} claims measurement_status={status!r}, allowed {list(allowed_statuses)}",
        )
    assert_value_backed(Fraction(measured, denominator), measured, denominator, True)


def check_provider_coverage(doc: dict[str, Any], manifest: Manifest) -> None:
    observed = {str(row.get("stratum_id", "")).split("|")[0] for row in doc.get("strata") or ()}
    declared = set(manifest.declared_providers)
    dropped = sorted(declared - observed)
    if dropped:
        raise GateError(
            "PROVIDER_STRATUM_DROPPED",
            f"the report drops the declared provider stratum(s) {dropped}: an empty stratum is "
            "published not-measured and is never deleted",
        )
    invented = sorted(observed - declared)
    if invented:
        raise GateError(
            "PROVIDER_MISATTRIBUTED",
            f"the report carries provider stratum(s) {invented} that the frozen manifest does not "
            "declare",
        )


def validate_report_shape(doc: Any, contract: Contract, manifest: Manifest) -> None:
    """Structural, vocabulary and claim validation of a published report."""
    check_closed_keys(
        "$report", doc, tuple(str(key) for key in contract.evaluation_report["closed_keys"])
    )
    scan_claims(doc)
    scan_leak_tokens(doc)
    if doc.get("schema") != REPORT_SCHEMA_ID:
        raise GateError("SCHEMA_KEY_DRIFT", f"$report.schema={doc.get('schema')!r}")
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise GateError("SCHEMA_KEY_DRIFT", f"$report.schema_version={doc.get('schema_version')!r}")
    output = contract.output_contract
    for key in GUARD_KEYS:
        if key in output and doc.get(key) != output.get(key):
            raise GateError(
                GUARD_DIAGNOSTIC.get(key, "SCHEMA_KEY_DRIFT"),
                f"$report.{key}={doc.get(key)!r} != the frozen {output.get(key)!r}",
            )
    if doc.get("framing") != contract.publication_contract.get("framing"):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"$report.framing={doc.get('framing')!r} != the frozen "
            f"{contract.publication_contract.get('framing')!r}",
        )
    if doc.get("measurement_status") != contract.publication_contract.get(
        "admissible_measurement_status"
    ):
        raise GateError(
            "MEASUREMENT_STATUS_DRIFT",
            f"$report.measurement_status={doc.get('measurement_status')!r} is not the admissible "
            "status for a published value",
        )
    if list(doc.get("non_claims") or ()) != list(contract.non_claims):
        raise GateError("MISSING_NON_CLAIM", "$report.non_claims differs from the frozen list")
    if doc.get("lifecycle") != contract.lifecycle:
        raise GateError("MISSING_LIFECYCLE_MARKER", "$report.lifecycle is not the frozen lifecycle")

    reference = doc.get("independent_reference")
    check_closed_keys(
        "$report.independent_reference",
        reference,
        tuple(str(key) for key in contract.evaluation_report["independent_reference_closed_keys"]),
    )
    if reference.get("unresolved_count") != 0:
        raise GateError(
            "UNRESOLVED_NONZERO",
            f"$report.independent_reference.unresolved_count={reference.get('unresolved_count')!r}",
        )
    if not isinstance(reference.get("pre_adjudication_agreement_sha256"), str):
        raise GateError("SCHEMA_KEY_DRIFT", "the reference is not pinned to the agreement report")

    per_pass_keys = tuple(str(key) for key in contract.evaluation_report["per_pass_closed_keys"])
    stratum_keys = tuple(
        str(key) for key in contract.evaluation_report["stratum_result_closed_keys"]
    )
    excluded_keys = tuple(
        str(key) for key in contract.evaluation_report["units_excluded_closed_keys"]
    )
    aspect_keys = tuple(str(key) for key in contract.evaluation_report["aspect_result_closed_keys"])

    aspects = doc.get("aspects")
    if not isinstance(aspects, list) or sorted(str(row.get("aspect")) for row in aspects) != sorted(
        ASPECTS
    ):
        raise GateError("ASPECT_TABLE_DRIFT", "$report.aspects is not the six frozen aspects")
    for row in aspects:
        aspect = str(row.get("aspect"))
        check_closed_keys(f"$report.aspects[{aspect}]", row, aspect_keys)
        check_published_rate(
            f"$report.aspects[{aspect}]",
            row,
            allowed_statuses=(MEASUREMENT_NOT_MEASURED, MEASUREMENT_INDEPENDENT),
        )
        if sorted(str(key) for key in row.get("units_excluded_reasons") or ()) != sorted(
            contract.aspect_excluded.get(aspect, ())
        ):
            raise GateError(
                "ASPECT_TABLE_DRIFT",
                f"$report.aspects[{aspect}].units_excluded_reasons differs from the frozen table",
            )
        for index, pass_row in enumerate(row.get("per_pass") or ()):
            check_closed_keys(
                f"$report.aspects[{aspect}].per_pass[{index}]", pass_row, per_pass_keys
            )
        for index, stratum_row in enumerate(row.get("strata") or ()):
            check_closed_keys(
                f"$report.aspects[{aspect}].strata[{index}]", stratum_row, stratum_keys
            )
            check_published_rate(
                f"$report.aspects[{aspect}].strata[index={index}]",
                stratum_row,
                allowed_statuses=(MEASUREMENT_NOT_MEASURED, MEASUREMENT_INDEPENDENT),
            )
    for index, stratum_row in enumerate(doc.get("strata") or ()):
        check_closed_keys(f"$report.strata[{index}]", stratum_row, stratum_keys)
        check_published_rate(
            f"$report.strata[{index}]",
            stratum_row,
            allowed_statuses=(MEASUREMENT_NOT_MEASURED, MEASUREMENT_INDEPENDENT),
        )
    for index, excluded_row in enumerate(doc.get("units_excluded") or ()):
        check_closed_keys(f"$report.units_excluded[{index}]", excluded_row, excluded_keys)
        if excluded_row.get("reason") not in EXCLUDED_REASONS:
            raise GateError(
                "DENOMINATOR_MISMATCH",
                f"$report.units_excluded[{index}].reason={excluded_row.get('reason')!r}",
            )
    for scope in FAMILY_SCOPES:
        validate_slice_shape(doc.get(scope), scope, contract, aspect_keys)
    check_provider_coverage(doc, manifest)


def validate_slice_shape(
    slice_doc: Any, scope: str, contract: Contract, aspect_keys: Sequence[str]
) -> None:
    if not isinstance(slice_doc, dict):
        raise GateError("SCHEMA_KEY_DRIFT", f"$report.{scope} is not an object")
    missing = [key for key in SLICE_REQUIRED_KEYS if key not in slice_doc]
    extra = [key for key in slice_doc if key not in SLICE_REQUIRED_KEYS + SLICE_OPTIONAL_KEYS]
    if missing or extra:
        raise GateError(
            "SCHEMA_KEY_DRIFT", f"$report.{scope} key drift: missing={missing} extra={extra}"
        )
    if slice_doc.get("family_scope") != scope:
        raise GateError("SCHEMA_KEY_DRIFT", f"$report.{scope}.family_scope is not {scope!r}")
    expected_evaluation = HOLDOUT_EVALUATION_STATUS if scope == "holdout" else DEV_EVALUATION_STATUS
    if slice_doc.get("evaluation_status") != expected_evaluation:
        raise GateError(
            "DEVELOPMENT_SLICE_NOT_EVALUATION",
            f"$report.{scope}.evaluation_status={slice_doc.get('evaluation_status')!r} != "
            f"{expected_evaluation!r}: the dev slice is development-only and is never an evaluation",
        )
    if scope == "dev" and slice_doc.get("non_claim") != DEV_NON_CLAIM_MARKER:
        raise GateError(
            "DEVELOPMENT_SLICE_NOT_EVALUATION",
            f"$report.dev.non_claim={slice_doc.get('non_claim')!r} != {DEV_NON_CLAIM_MARKER!r}",
        )
    expected_status = MEASUREMENT_INDEPENDENT if scope == "holdout" else MEASUREMENT_PROXY
    if slice_doc.get("measurement_status") != expected_status:
        raise GateError(
            "DEVELOPMENT_SLICE_NOT_EVALUATION" if scope == "dev" else "MEASUREMENT_STATUS_DRIFT",
            f"$report.{scope}.measurement_status={slice_doc.get('measurement_status')!r} != "
            f"{expected_status!r}",
        )
    allowed_statuses = (
        (MEASUREMENT_NOT_MEASURED, MEASUREMENT_INDEPENDENT)
        if scope == "holdout"
        else (MEASUREMENT_NOT_MEASURED, MEASUREMENT_PROXY)
    )
    aspects = slice_doc.get("aspects")
    if not isinstance(aspects, list) or sorted(str(row.get("aspect")) for row in aspects) != sorted(
        ASPECTS
    ):
        raise GateError("ASPECT_TABLE_DRIFT", f"$report.{scope}.aspects is not the six aspects")
    for row in aspects:
        aspect = str(row.get("aspect"))
        check_closed_keys(f"$report.{scope}.aspects[{aspect}]", row, aspect_keys)
        check_published_rate(
            f"$report.{scope}.aspects[{aspect}]", row, allowed_statuses=allowed_statuses
        )


def validate_report_invariants(doc: dict[str, Any]) -> None:
    """No published value without a positive denominator; empty strata stay not-measured."""
    rows: list[tuple[str, dict[str, Any]]] = []
    rows.extend((f"$report.aspects[{row.get('aspect')}]", row) for row in doc.get("aspects") or ())
    rows.extend(
        (f"$report.strata[{index}]", row) for index, row in enumerate(doc.get("strata") or ())
    )
    for scope in FAMILY_SCOPES:
        slice_doc = doc.get(scope) or {}
        rows.extend(
            (f"$report.{scope}.aspects[{row.get('aspect')}]", row)
            for row in slice_doc.get("aspects") or ()
        )
    for label, row in rows:
        denominator = row.get("denominator")
        value = row.get("value")
        if int(denominator or 0) == 0 and value is not None:
            raise GateError("RATE_UNDEFINED", f"{label} publishes {value!r} without a denominator")
        if int(denominator or 0) > 0 and value is None:
            raise GateError("DENOMINATOR_MISMATCH", f"{label} has a denominator but no value")


def _rate_triplet(row: dict[str, Any]) -> tuple[int, int, float | None]:
    value = row.get("value")
    return (
        int(row.get("measured", 0)),
        int(row.get("denominator", 0)),
        None if value is None else float(value),
    )


def _compare_rates(label: str, observed: dict[str, Any], expected: dict[str, Any]) -> None:
    if _rate_triplet(observed) != _rate_triplet(expected):
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"{label} publishes {_rate_triplet(observed)} but the recomputed population is "
            f"{_rate_triplet(expected)}",
        )
    if observed.get("measurement_status") != expected.get("measurement_status"):
        raise GateError(
            "MEASUREMENT_STATUS_DRIFT",
            f"{label}.measurement_status={observed.get('measurement_status')!r} != "
            f"{expected.get('measurement_status')!r}",
        )


def validate_report_against_recomputation(doc: dict[str, Any], expected: dict[str, Any]) -> None:
    """Every published number must equal the number the frozen rules recompute."""
    validate_report_invariants(doc)
    by_aspect = {str(row.get("aspect")): row for row in doc.get("aspects") or ()}
    exp_aspects = {str(row.get("aspect")): row for row in expected.get("aspects") or ()}
    if sorted(by_aspect) != sorted(exp_aspects):
        raise GateError("ASPECT_TABLE_DRIFT", f"$report.aspects names {sorted(by_aspect)}")
    for aspect, row in by_aspect.items():
        exp = exp_aspects[aspect]
        _compare_rates(f"$report.aspects[{aspect}]", row, exp)
        for index, pass_row in enumerate(row.get("per_pass") or ()):
            exp_pass = (exp.get("per_pass") or ())[index]
            for key in (
                "coder_pass",
                "true_positive",
                "false_positive",
                "false_negative",
                "true_negative",
            ):
                if pass_row.get(key) != exp_pass.get(key):
                    raise GateError(
                        "DENOMINATOR_MISMATCH",
                        f"$report.aspects[{aspect}].per_pass[{index}].{key}="
                        f"{pass_row.get(key)!r} != {exp_pass.get(key)!r}",
                    )
            for key in ("precision", "recall"):
                observed = pass_row.get(key)
                target = exp_pass.get(key)
                if (observed is None) != (target is None) or (
                    observed is not None and abs(float(observed) - float(target)) > RATE_TOLERANCE
                ):
                    raise GateError(
                        "DENOMINATOR_MISMATCH",
                        f"$report.aspects[{aspect}].per_pass[{index}].{key}={observed!r} != "
                        f"{target!r}",
                    )
    observed_strata = {
        (str(row.get("stratum_id")), str(row.get("aspect"))): row for row in doc.get("strata") or ()
    }
    expected_strata = {
        (str(row.get("stratum_id")), str(row.get("aspect"))): row
        for row in expected.get("strata") or ()
    }
    if sorted(observed_strata) != sorted(expected_strata):
        raise GateError(
            "STRATUM_TABLE_DRIFT",
            "$report.strata does not carry exactly the frozen stratum x aspect table (observed "
            f"{len(observed_strata)} rows, expected {len(expected_strata)})",
        )
    for key, row in observed_strata.items():
        _compare_rates(f"$report.strata[{key[0]},{key[1]}]", row, expected_strata[key])
    if (doc.get("units_excluded") or []) != (expected.get("units_excluded") or []):
        raise GateError(
            "DENOMINATOR_MISMATCH",
            "$report.units_excluded does not match the recomputed unit accounting",
        )
    if doc.get("units_total") != expected.get("units_total"):
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"$report.units_total={doc.get('units_total')!r} != {expected.get('units_total')!r}",
        )
    for scope in FAMILY_SCOPES:
        observed_slice = doc.get(scope) or {}
        expected_slice = expected.get(scope) or {}
        if observed_slice.get("units_total") != expected_slice.get("units_total"):
            raise GateError(
                "DENOMINATOR_MISMATCH",
                f"$report.{scope}.units_total={observed_slice.get('units_total')!r}",
            )
        if (observed_slice.get("units_excluded") or []) != (
            expected_slice.get("units_excluded") or []
        ):
            raise GateError(
                "DENOMINATOR_MISMATCH", f"$report.{scope}.units_excluded does not match"
            )
        observed_aspects = {
            str(row.get("aspect")): row for row in observed_slice.get("aspects") or ()
        }
        expected_aspects = {
            str(row.get("aspect")): row for row in expected_slice.get("aspects") or ()
        }
        if sorted(observed_aspects) != sorted(expected_aspects):
            raise GateError("ASPECT_TABLE_DRIFT", f"$report.{scope}.aspects drift")
        for aspect, row in observed_aspects.items():
            _compare_rates(f"$report.{scope}.aspects[{aspect}]", row, expected_aspects[aspect])
    if (doc.get("independent_reference") or {}) != (expected.get("independent_reference") or {}):
        raise GateError(
            "FROZEN_SOURCE_DRIFT",
            "$report.independent_reference does not match the human reference it was computed from",
        )


# --------------------------------------------------------------------------- #
# Pipelines (raising) and the mode wrappers (exit codes).
# --------------------------------------------------------------------------- #


def build_evaluation(
    root: Path, paths: Paths, *, allow_test_fixtures: bool
) -> tuple[dict[str, Any], list[str]]:
    """Compute the frozen report from the human reference; never writes anything."""
    contract = load_contract(root, paths)
    world = _load_world(root, paths)
    manifest = load_manifest(root, paths, world.universe)
    human = discover_human_inputs(root, paths, allow_test_fixtures=allow_test_fixtures)
    pairings = resolve_reference(contract, human.codings, world.universe, human.tips)
    measurements = measure_all(contract, manifest, pairings, world.universe)
    report, notes = build_report(contract, manifest, measurements, human, world.universe)
    validate_report_shape(report, contract, manifest)
    validate_report_against_recomputation(report, report)
    return report, notes


def publish_report(root: Path, paths: Paths, *, allow_test_fixtures: bool) -> list[str]:
    """Write the evaluation report, or refuse with a named diagnostic and no artifact."""
    target = report_path(root, paths)
    report_present = target.is_file()
    human_present = human_data_present(root, paths, allow_test_fixtures=allow_test_fixtures)
    enforce_human_report_invariant(
        human_present=human_present, report_present=report_present, writing=True
    )
    if not human_present:
        raise GateError(
            "HUMAN_PILOT_ABSENT",
            "no human submission exists yet, so no denominator exists and no S03 rate may be "
            "published (the harness never creates a human input)",
        )
    report, notes = build_evaluation(root, paths, allow_test_fixtures=allow_test_fixtures)
    guard_writable(root, target, "evaluation report")
    write_json_atomic(root, target, report, "evaluation report")
    return notes


def check_pipeline(root: Path, paths: Paths, *, allow_test_fixtures: bool) -> dict[str, Any]:
    """Read-only self-check; returns the counters the marker prints."""
    contract = load_contract(root, paths)
    world = _load_world(root, paths)
    manifest = load_manifest(root, paths, world.universe)
    inventory = stratum_inventory(manifest)
    report_present = report_path(root, paths).is_file()
    human_present = human_data_present(root, paths, allow_test_fixtures=allow_test_fixtures)
    enforce_human_report_invariant(
        human_present=human_present, report_present=report_present, writing=False
    )
    if human_present and report_present:
        report, _ = build_evaluation(root, paths, allow_test_fixtures=allow_test_fixtures)
        tracked = load_json_bytes(report_path(root, paths).read_bytes(), paths.report)
        validate_report_shape(tracked, contract, manifest)
        validate_report_against_recomputation(tracked, report)
    results = formula_probes(contract, manifest)
    failures = [name for name, ok, _, _ in results if not ok]
    if failures:
        raise GateError("SCHEMA_KEY_DRIFT", f"offline formula probe(s) failed: {failures}")
    return {
        "aspects": len(contract.aspect_names),
        "strata": len(inventory),
        "diagnostics": len(contract.diagnostics),
        "probes": len(results),
        "human": "present" if human_present else "absent",
        "report": "present" if report_present else "absent",
    }


def validate_pipeline(root: Path, paths: Paths, *, allow_test_fixtures: bool) -> None:
    """Recompute from the human reference and validate the tracked report against it."""
    contract = load_contract(root, paths)
    world = _load_world(root, paths)
    manifest = load_manifest(root, paths, world.universe)
    report, _ = build_evaluation(root, paths, allow_test_fixtures=allow_test_fixtures)
    tracked = load_json_bytes(report_path(root, paths).read_bytes(), paths.report)
    validate_report_shape(tracked, contract, manifest)
    validate_report_against_recomputation(tracked, report)


def run_write(root: Path, paths: Paths, *, allow_test_fixtures: bool) -> int:
    try:
        notes = publish_report(root, paths, allow_test_fixtures=allow_test_fixtures)
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        if exc.diagnostic in ("HUMAN_PILOT_ABSENT", "NO_ADJUDICATION_INPUT"):
            print(f"{ABSENT_TOKEN} {exc.diagnostic}", file=sys.stderr)
            return ABSENT_EXIT
        return FAIL_EXIT
    print(f"{WRITTEN_LINE} path={paths.report} notes={','.join(notes) if notes else 'none'}")
    return OK_EXIT


def run_check(root: Path, paths: Paths, *, allow_test_fixtures: bool) -> int:
    try:
        counters = check_pipeline(root, paths, allow_test_fixtures=allow_test_fixtures)
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return FAIL_EXIT
    print(
        f"{MARKER} aspects={counters['aspects']} strata={counters['strata']} "
        f"reasons={len(EXCLUDED_REASONS)} diagnostics={counters['diagnostics']} "
        f"probes={counters['probes']} human={counters['human']} report={counters['report']}"
    )
    return OK_EXIT


# --------------------------------------------------------------------------- #
# Offline formula probes: ``check`` proves the rules without any human data.
# --------------------------------------------------------------------------- #


def _probe(label: str, call: Callable[[], None], diagnostic: str) -> tuple[str, bool, str]:
    try:
        call()
    except GateError as exc:
        if exc.diagnostic != diagnostic:
            return (
                label,
                False,
                f"raised {exc.diagnostic}, expected {diagnostic}: {exc.detail}",
            )
        return (label, True, f"{exc.diagnostic}: {exc.detail}"[:160])
    except Exception as exc:  # pragma: no cover - probe harness guard
        return (label, False, f"raised {type(exc).__name__}: {exc}")
    return (label, False, f"accepted the hostile input (expected {diagnostic})")


def formula_probes(contract: Contract, manifest: Manifest) -> list[tuple[str, bool, str, str]]:
    """Deterministic probes of the denominator rule, the guards and the table rules.

    Each result carries the diagnostic the probe proves (``""`` when the probe asserts a
    successful computation rather than a refusal), so the selftest can derive hostile
    coverage from evidence instead of restating a list of names.
    """
    results: list[tuple[str, bool, str, str]] = []

    def zero_denominator_is_not_a_measurement() -> None:
        aggregate = Aggregate(stats={1: PassStats(), 2: PassStats()}, measured=0, denominator=0)
        rate = rate_of(aggregate, MEASUREMENT_INDEPENDENT)
        if rate.value is not None or rate.measurement_status != MEASUREMENT_NOT_MEASURED:
            raise GateError("RATE_UNDEFINED", f"zero denominator produced value={rate.value!r}")
        if rate.note != "RATE_UNDEFINED":
            raise GateError("RATE_UNDEFINED", "the zero-denominator note is missing")

    results.append(
        (
            "zero_denominator_is_not_a_measurement",
            *_probe_outcome(
                "zero_denominator_is_not_a_measurement",
                zero_denominator_is_not_a_measurement,
                True,
            ),
        )
    )

    def imputed_zero_is_refused() -> None:
        check_published_rate(
            "$probe",
            {"measured": 0, "denominator": 0, "value": 0.0, "measurement_status": "not-measured"},
            allowed_statuses=(MEASUREMENT_NOT_MEASURED,),
        )

    results.append(
        (
            "imputed_zero_value_refused",
            *_probe_outcome(
                "imputed_zero_value_refused", imputed_zero_is_refused, None, "RATE_UNDEFINED"
            ),
        )
    )

    results.append(
        (
            "computed_perfect_unbacked_measured_zero",
            *_probe_pair(
                "computed_perfect_unbacked_measured_zero",
                lambda: assert_value_backed(Fraction(1, 1), 0, 5, True),
                "COMPUTED_PERFECT_UNBACKED",
            ),
        )
    )
    results.append(
        (
            "computed_perfect_unbacked_partial_coverage",
            *_probe_pair(
                "computed_perfect_unbacked_partial_coverage",
                lambda: assert_value_backed(Fraction(1, 1), 3, 5, False),
                "COMPUTED_PERFECT_UNBACKED",
            ),
        )
    )
    results.append(
        (
            "denominator_mismatch_refused",
            *_probe_pair(
                "denominator_mismatch_refused",
                lambda: check_published_rate(
                    "$probe",
                    {
                        "measured": 4,
                        "denominator": 2,
                        "value": 0.5,
                        "measurement_status": MEASUREMENT_INDEPENDENT,
                    },
                    allowed_statuses=(MEASUREMENT_INDEPENDENT,),
                ),
                "DENOMINATOR_MISMATCH",
            ),
        )
    )
    for key, value, diagnostic in (
        ("is_gold", True, "IS_GOLD_CLAIM"),
        ("human_acceptance", "accepted", "GOLD_CLAIM"),
        ("promotion", "promoted", "PROMOTION_CLAIM"),
        ("threshold", 0.5, "THRESHOLD_REQUESTED"),
        ("classification", "accepted", "CLASSIFICATION_REQUESTED"),
        ("authority", "binding", "AUTHORITY_CLAIM"),
        ("model_invoked", True, "MODEL_INVOKED"),
    ):
        results.append(
            (
                f"claim_{key}_refused",
                *_probe_pair(
                    f"claim_{key}_refused",
                    lambda key=key, value=value: scan_claims({"nested": {key: value}}),
                    diagnostic,
                ),
            )
        )
    results.append(
        (
            "predicted_answer_key_refused",
            *_probe_pair(
                "predicted_answer_key_refused",
                lambda: scan_leak_tokens({"nested": [{"expected": "x"}]}),
                "LEAK_FORBIDDEN_KEY",
            ),
        )
    )

    def abstention_collapse_is_refused() -> None:
        entries = [
            (
                {
                    **entry,
                    "units_excluded_reasons": list(entry["units_excluded_reasons"]) + [ABSTAINED],
                }
                if entry["aspect"] == ASPECT_WITHOUT_ABSTAINED_EXCLUSION
                else entry
            )
            for entry in contract.aspect_table.values()
        ]
        validate_aspect_table(entries, contract.aspect_closed_keys, contract.axes)

    results.append(
        (
            "abstention_collapse_refused",
            *_probe_pair(
                "abstention_collapse_refused", abstention_collapse_is_refused, "ABSTENTION_COLLAPSE"
            ),
        )
    )

    def aspect_drift_is_refused() -> None:
        entries = [entry for entry in contract.aspect_table.values() if entry["aspect"] != "scope"]
        validate_aspect_table(entries, contract.aspect_closed_keys, contract.axes)

    results.append(
        (
            "aspect_table_drift_refused",
            *_probe_pair(
                "aspect_table_drift_refused", aspect_drift_is_refused, "ASPECT_TABLE_DRIFT"
            ),
        )
    )

    def stratum_drop_is_refused() -> None:
        provider = manifest.declared_providers[0]
        check_provider_coverage({"strata": [{"stratum_id": f"{provider}|f|d|holdout"}]}, manifest)

    results.append(
        (
            "provider_stratum_dropped_refused",
            *_probe_pair(
                "provider_stratum_dropped_refused",
                stratum_drop_is_refused,
                "PROVIDER_STRATUM_DROPPED",
            ),
        )
    )

    def provider_invented_is_refused() -> None:
        rows = [
            {"stratum_id": f"{provider}|f|d|holdout"} for provider in manifest.declared_providers
        ]
        rows.append({"stratum_id": "acme|f|d|holdout"})
        check_provider_coverage({"strata": rows}, manifest)

    results.append(
        (
            "provider_misattributed_refused",
            *_probe_pair(
                "provider_misattributed_refused",
                provider_invented_is_refused,
                "PROVIDER_MISATTRIBUTED",
            ),
        )
    )
    return results


def _probe_pair(label: str, call: Callable[[], None], diagnostic: str) -> tuple[bool, str, str]:
    outcome = _probe(label, call, diagnostic)
    return outcome[1], outcome[2], diagnostic


def _probe_outcome(
    label: str,
    call: Callable[[], None],
    expect_success: bool,
    diagnostic: str | None = None,
) -> tuple[bool, str, str]:
    if expect_success:
        try:
            call()
        except Exception as exc:  # pragma: no cover - probe harness guard
            return (False, f"raised {type(exc).__name__}: {exc}", "")
        return (
            True,
            "denominator=0 -> value null, status not-measured, note RATE_UNDEFINED",
            "",
        )
    return _probe_pair(label, call, diagnostic or "")


# --------------------------------------------------------------------------- #
# Selftest: synthetic human world, then every named refusal path.
# --------------------------------------------------------------------------- #

SELFTEST_FROZEN_FILES = (
    CASES_REL,
    KIT_PASS1_REL,
    KIT_PASS2_REL,
    S02_SCHEMAS_REL,
    S01_SCHEMAS_REL,
    S03_SCHEMAS_REL,
    PROTOCOL_REL,
    CODEBOOK_REL,
    S02_PROTOCOL_REL,
    M199_PROTOCOL_REL,
    MANIFEST_REL,
)

SYNTHETIC_SUBMISSIONS_REL = "synthetic-store/submissions"
SYNTHETIC_ADJUDICATIONS_REL = "synthetic-store/adjudications"


def synthetic_paths(paths: Paths) -> Paths:
    """The selftest world keeps its synthetic human stores outside ``prd/annotation/``."""
    return replace(
        paths,
        submissions=SYNTHETIC_SUBMISSIONS_REL,
        adjudications=SYNTHETIC_ADJUDICATIONS_REL,
    )


def _copy_frozen(source: Path, target: Path, paths: Paths) -> None:
    for rel in SELFTEST_FROZEN_FILES:
        src = resolve_artifact(source, rel, f"selftest copy {rel}")
        if src.is_file():
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    fixture_src = source / paths.fixture_dir
    if fixture_src.is_dir():
        shutil.copytree(fixture_src, target / paths.fixture_dir, dirs_exist_ok=True)


def alternative_span(world: Any, binding: Any) -> tuple[int, int] | None:
    """A second lawful span for the same fragment: the offered region minus its last char."""
    data = INTAKE.fragment_bytes(world, binding)
    if data is None:  # pragma: no cover - the frozen fragments are pinned
        return None
    region = data[binding.offered_start : binding.offered_end]
    try:
        text = region.decode("utf-8")
    except UnicodeDecodeError:  # pragma: no cover - the offered region is char-aligned
        return None
    if len(text) < 2:
        return None
    end = binding.offered_start + len(text[:-1].encode("utf-8"))
    if end <= binding.offered_start:  # pragma: no cover - defensive
        return None
    return binding.offered_start, min(end, binding.offered_end)


def design_case(
    case_id: str, binding: Any, coder_pass: int, rule: int, alt: tuple[int, int] | None
) -> dict[str, Any]:
    """One synthetic coding.  Ten rules cover every aspect, both slices and both outcomes."""
    span = {"start": binding.offered_start, "end": binding.offered_end}
    decision = REFERENCE
    abstention = NON_ABSTAINED
    slots: dict[str, Any] = {}
    if rule == 0:
        decision = NOT_A_REFERENCE
    elif rule == 1:
        slots["hier_nums"] = "ст. 5 части 1"
        if coder_pass == CODER_PASS_TWO:
            slots["marker_chain"] = "п. 3"
    elif rule == 2:
        slots["marker_chain"] = "п. 2"
    elif rule == 3:
        slots["anaphora"] = "указанный документ"
    elif rule == 4:
        slots["doc_no"] = "558"
        if coder_pass == CODER_PASS_TWO:
            abstention = "ambiguous"
    elif rule == 5:
        if coder_pass == CODER_PASS_TWO and alt is not None:
            span = {"start": alt[0], "end": alt[1]}
        slots["law_code"] = "44-ФЗ"
    elif rule == 6:
        slots["hier_nums"] = "ст. 7"
        if coder_pass == CODER_PASS_TWO:
            decision = NOT_A_REFERENCE
    elif rule == 7:
        slots["doc_no"] = "77"
        if coder_pass == CODER_PASS_TWO:
            abstention = "insufficient-context"
    elif rule == 8:
        if coder_pass == CODER_PASS_ONE:
            slots["hier_nums"] = "ст. 9"
        else:
            slots["marker_chain"] = "п. 9"
    else:
        slots["law_code"] = "44-ФЗ"
        if coder_pass == CODER_PASS_TWO:
            decision = NOT_A_REFERENCE
    return {
        "case_id": case_id,
        "decision": decision,
        "span": span,
        "slots": slots,
        "abstention": abstention,
    }


def synthetic_resolution(rule: int, axis: str, left: str, right: str) -> str:
    """The synthetic adjudicator's lawful choice inside the frozen resolution space."""
    if axis == SPAN_EXACT_AXIS:
        return "span_pass_2"
    if axis == REFERENCE_DECISION_AXIS:
        return NOT_A_REFERENCE if rule == 9 else REFERENCE
    if axis == ABSTENTION_AXIS:
        return NON_ABSTAINED
    if axis.startswith(SLOT_AXIS_PREFIX):
        return left
    raise GateError("RESOLUTION_SPACE_DRIFT", f"no synthetic resolution rule for axis {axis!r}")


def synthetic_codings(
    world: Any, paths: Paths, root: Path
) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    codings: dict[int, dict[str, dict[str, Any]]] = {1: {}, 2: {}}
    rules: dict[str, int] = {}
    for index, case_id in enumerate(world.universe):
        rule = index % 10
        rules[case_id] = rule
        binding = world.cases[case_id]
        alt = alternative_span(world, binding)
        for coder_pass in PASSES:
            codings[coder_pass][case_id] = design_case(case_id, binding, coder_pass, rule, alt)
    return codings, rules


def build_synthetic_world(base: Path, paths: Paths) -> dict[str, Any]:
    """Write a synthetic two-pass human world and its five derived S02 artifacts."""
    world = _load_world(base, paths)
    codings, rules = synthetic_codings(world, paths, base)
    submissions_store = base / paths.submissions
    adjudications_store = base / paths.adjudications
    submissions_store.mkdir(parents=True, exist_ok=True)
    adjudications_store.mkdir(parents=True, exist_ok=True)
    for coder_pass in PASSES:
        envelope = INTAKE.synthetic_submission(world, coder_pass, f"coder-{coder_pass}")
        envelope["cases"] = [codings[coder_pass][case_id] for case_id in world.universe]
        (submissions_store / f"submission-pass-{coder_pass}.json").write_bytes(serialize(envelope))
    submission_files = INTAKE.discover_submissions(submissions_store)
    failures: Failures = []
    summaries = INTAKE.evaluate_store(
        submission_files, world, allow_test_fixtures=True, failures=failures
    )
    if failures:
        raise GateError(failures[0][0], f"synthetic submission rejected: {failures[0][1]}")
    axes = tuple(str(axis) for axis in AGREEMENT.load_contract(world).axes)
    adjudication_inputs = []
    for case_id in world.universe:
        for axis in axes:
            left = AGREEMENT.case_observation(codings[CODER_PASS_ONE][case_id], axis)
            right = AGREEMENT.case_observation(codings[CODER_PASS_TWO][case_id], axis)
            if left is None or right is None or left == right:
                continue
            resolution = synthetic_resolution(rules[case_id], axis, left, right)
            adjudication_inputs.append(
                {
                    "schema": ADJUDICATION_INPUT_SCHEMA_ID,
                    "schema_version": SCHEMA_VERSION,
                    "adjudication_id": f"m207-s02-adjudication-{case_id}-{axis}",
                    "adjudicator_id": "adjudicator-1",
                    "axis": axis,
                    "case_id": case_id,
                    "provenance": "human-reviewed",
                    "rationale": f"synthetic resolution of {axis}",
                    "resolution": resolution,
                    "supersedes": None,
                    "is_gold": False,
                    "lifecycle": dict(world.lifecycle),
                    "non_claims": list(world.non_claims),
                }
            )
    for index, envelope in enumerate(adjudication_inputs):
        (adjudications_store / f"adjudication-{index:03d}.json").write_bytes(serialize(envelope))

    measurements = [AGREEMENT.measure_axis(axis, codings, world.universe) for axis in axes]
    families = AGREEMENT.load_families(base, paths.cases, world.universe)
    agreement_report = AGREEMENT.build_report(
        world=world,
        measurements=measurements,
        refs=[
            {
                "coder_id": summary["coder_id"],
                "coder_pass": summary["coder_pass"],
                "sha256": summary["sha256"],
                "submission_id": summary["submission_id"],
            }
            for summary in summaries
        ],
        breakdown=AGREEMENT.family_breakdown(world.universe, families),
    )
    inventory = AGREEMENT.build_inventory(world=world, measurements=measurements, families=families)
    intake_record = INTAKE.build_record(world, summaries)
    agreement_path = base / paths.agreement_report
    inventory_path = base / paths.inventory
    write_json_atomic(base, agreement_path, agreement_report, "synthetic agreement report")
    write_json_atomic(base, inventory_path, inventory, "synthetic disagreement inventory")
    agreement_sha = sha256_file(agreement_path)

    inventory_keys = frozenset(
        (str(entry["case_id"]), str(entry["axis"])) for entry in inventory["entries"]
    )
    adjudication_contract = ADJ.load_contract(world)
    entries = ADJ.evaluate_store(
        ADJ.discover_adjudications(adjudications_store, agreement_frozen=True),
        contract=adjudication_contract,
        inventory_keys=inventory_keys,
        universe=world.universe,
        world=world,
        allow_test_fixtures=True,
        failures=failures,
    )
    if failures:
        raise GateError(failures[0][0], f"synthetic adjudication rejected: {failures[0][1]}")
    record = ADJ.build_record(
        world=world,
        entries=entries,
        inventory_keys=inventory_keys,
        agreement_sha256=agreement_sha,
    )
    record_path = base / paths.adjudication_record
    write_json_atomic(base, record_path, record, "synthetic adjudication record")
    receipt = ADJ.build_receipt(
        world=world,
        agreement_sha256=agreement_sha,
        record_sha256=sha256_file(record_path),
        coder_ids=[summary["coder_id"] for summary in summaries],
        adjudicator_ids=[entry.adjudicator_id for entry in entries],
        case_count=len(world.universe),
    )
    write_json_atomic(base, base / paths.pilot_receipt, receipt, "synthetic pilot receipt")
    write_json_atomic(base, base / paths.intake_record, intake_record, "synthetic intake record")
    return {
        "summaries": summaries,
        "entries": entries,
        "inventory": inventory,
        "rules": rules,
        "codings": codings,
    }


def _artifact_digest(root: Path, paths: Paths) -> dict[str, str]:
    digests: dict[str, str] = {}
    for rel in (
        paths.report,
        paths.intake_record,
        paths.agreement_report,
        paths.inventory,
        paths.adjudication_record,
        paths.pilot_receipt,
    ):
        path = resolve_artifact(root, rel, "artifact", suffix=".json")
        digests[rel] = sha256_file(path) if path.is_file() else "<absent>"
    for rel in (paths.submissions, paths.adjudications):
        store = root / rel
        files = sorted(path.name for path in store.iterdir()) if store.is_dir() else []
        digests[rel] = ",".join(files)
    return digests


def _rewrite_json(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    mutate(doc)
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _probe_store_proxy(root: Path, paths: Paths) -> None:
    path = root / paths.submissions / "proxy-receipt.json"
    path.write_bytes(
        serialize(
            {
                "schema": "npa-quality-receipts/v1",
                "schema_version": 1,
                "measurement_status": MEASUREMENT_PROXY,
            }
        )
    )


def _probe_receipt_proxy(root: Path, paths: Paths) -> None:
    _rewrite_json(
        root / paths.pilot_receipt,
        lambda doc: doc.update({"measurement_status": MEASUREMENT_PROXY}),
    )


def _probe_provenance(root: Path, paths: Paths) -> None:
    store = root / paths.submissions
    first = sorted(path for path in store.iterdir() if path.suffix == ".json")[0]
    _rewrite_json(first, lambda doc: doc.update({"provenance": "machine-pass"}))


def _probe_unresolved(root: Path, paths: Paths) -> None:
    """A self-consistent world whose only defect is a partially resolved reference.

    The rewritten record is re-pinned in the receipt first: a mutated pinned artifact without
    a matching re-pin is ``FROZEN_SOURCE_DRIFT`` (proved by its own probe), not the
    unresolved-reference refusal this probe must reach.
    """
    record = root / paths.adjudication_record
    _rewrite_json(record, lambda doc: doc.update({"unresolved_count": 1}))
    _rewrite_json(
        root / paths.pilot_receipt,
        lambda doc: doc.update({"adjudication_record_sha256": sha256_file(record)}),
    )


def _probe_pin_drift(root: Path, paths: Paths) -> None:
    _rewrite_json(
        root / paths.adjudication_record,
        lambda doc: doc.update({"pre_adjudication_agreement_sha256": "0" * 64}),
    )


def _probe_report_without_human(root: Path, paths: Paths) -> None:
    shutil.rmtree(root / paths.submissions)
    shutil.rmtree(root / paths.adjudications)


def _probe_report_missing(root: Path, paths: Paths) -> None:
    (root / paths.report).unlink()


def _probe_denominator_doubled(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        for row in doc["strata"]:
            if row["denominator"] > 0:
                row["measured"] *= 2
                row["denominator"] *= 2
                return

    _rewrite_json(root / paths.report, mutate)


def _probe_stratum_dropped(root: Path, paths: Paths) -> None:
    _rewrite_json(
        root / paths.report,
        lambda doc: doc.update(
            {
                "strata": [
                    row for row in doc["strata"] if not row["stratum_id"].startswith("garant|")
                ]
            }
        ),
    )


def _probe_provider_invented(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        for row in doc["strata"]:
            provider, rest = row["stratum_id"].split("|", 1)
            if provider == "garant":
                row["stratum_id"] = f"acme|{rest}"
                return

    _rewrite_json(root / paths.report, mutate)


def _probe_dev_slice(root: Path, paths: Paths) -> None:
    _rewrite_json(
        root / paths.report,
        lambda doc: doc["dev"].update({"evaluation_status": HOLDOUT_EVALUATION_STATUS}),
    )


def _probe_status_drift(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        for row in doc["aspects"]:
            if row["denominator"] > 0:
                row["measurement_status"] = MEASUREMENT_PROXY
                return

    _rewrite_json(root / paths.report, mutate)


def _probe_rate_undefined(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        for row in doc["strata"]:
            if row["denominator"] == 0:
                row["value"] = 0.0
                return

    _rewrite_json(root / paths.report, mutate)


def _probe_aspect_dropped(root: Path, paths: Paths) -> None:
    _rewrite_json(
        root / paths.report,
        lambda doc: doc.update(
            {"aspects": [row for row in doc["aspects"] if row["aspect"] != "scope"]}
        ),
    )


def _probe_claim(key: str, value: Any) -> Callable[[Path, Paths], None]:
    def mutate(root: Path, paths: Paths) -> None:
        _rewrite_json(root / paths.report, lambda doc: doc.update({key: value}))

    return mutate


SELFTEST_PROBES: tuple[tuple[str, str, str, Callable[[Path, Paths], None]], ...] = (
    ("proxy_input_refused_store", "run", "PROXY_INPUT_REFUSED", _probe_store_proxy),
    ("proxy_input_refused_receipt", "run", "PROXY_INPUT_REFUSED", _probe_receipt_proxy),
    ("provenance_not_human", "run", "PROVENANCE_NOT_HUMAN", _probe_provenance),
    ("unresolved_nonzero", "run", "UNRESOLVED_NONZERO", _probe_unresolved),
    ("frozen_source_drift_pin", "run", "FROZEN_SOURCE_DRIFT", _probe_pin_drift),
    (
        "report_without_human_data",
        "check",
        "REPORT_WITHOUT_HUMAN_DATA",
        _probe_report_without_human,
    ),
    (
        "report_missing_with_human_data",
        "check",
        "REPORT_MISSING_WITH_HUMAN_DATA",
        _probe_report_missing,
    ),
    ("denominator_mismatch", "validate", "DENOMINATOR_MISMATCH", _probe_denominator_doubled),
    ("provider_stratum_dropped", "validate", "PROVIDER_STRATUM_DROPPED", _probe_stratum_dropped),
    ("provider_misattributed", "validate", "PROVIDER_MISATTRIBUTED", _probe_provider_invented),
    (
        "development_slice_not_evaluation",
        "validate",
        "DEVELOPMENT_SLICE_NOT_EVALUATION",
        _probe_dev_slice,
    ),
    ("measurement_status_drift", "validate", "MEASUREMENT_STATUS_DRIFT", _probe_status_drift),
    ("rate_undefined", "validate", "RATE_UNDEFINED", _probe_rate_undefined),
    ("aspect_table_drift", "validate", "ASPECT_TABLE_DRIFT", _probe_aspect_dropped),
    ("gold_claim", "validate", "GOLD_CLAIM", _probe_claim("human_acceptance", "accepted")),
    ("is_gold_claim", "validate", "IS_GOLD_CLAIM", _probe_claim("is_gold", True)),
    ("threshold_requested", "validate", "THRESHOLD_REQUESTED", _probe_claim("threshold", 0.5)),
    (
        "classification_requested",
        "validate",
        "CLASSIFICATION_REQUESTED",
        _probe_claim("classification", "accepted"),
    ),
    ("promotion_claim", "validate", "PROMOTION_CLAIM", _probe_claim("promotion", "promoted")),
)


def _run_entry(entry: str, root: Path, paths: Paths) -> None:
    if entry == "run":
        publish_report(root, paths, allow_test_fixtures=True)
    elif entry == "check":
        check_pipeline(root, paths, allow_test_fixtures=True)
    elif entry == "validate":
        validate_pipeline(root, paths, allow_test_fixtures=True)
    else:  # pragma: no cover - defensive
        raise GateError("SCHEMA_KEY_DRIFT", f"unknown selftest entry {entry!r}")


def _expect_refusal(entry: str, root: Path, paths: Paths, diagnostic: str) -> tuple[bool, str]:
    before = _artifact_digest(root, paths)
    try:
        _run_entry(entry, root, paths)
    except GateError as exc:
        after = _artifact_digest(root, paths)
        if exc.diagnostic != diagnostic:
            return False, f"{entry} refused with {exc.diagnostic}, expected {diagnostic}"
        if entry != "validate" and after != before:
            return False, f"{entry} mutated a tracked artifact while refusing"
        return True, f"{entry} refused with {exc.diagnostic}: {exc.detail}"[:160]
    return False, f"{entry} accepted the hostile input (expected {diagnostic})"


def selftest_invariants(doc: dict[str, Any], manifest: Manifest) -> list[tuple[str, bool, str]]:
    """The DONE-WHEN invariants that must hold on the synthetic report."""
    checks: list[tuple[str, bool, str]] = []
    try:
        validate_report_invariants(doc)
        checks.append(("no_value_without_denominator", True, "every value carries a denominator"))
    except GateError as exc:
        checks.append(("no_value_without_denominator", False, f"{exc.diagnostic}: {exc.detail}"))
    empty = [
        row for row in doc.get("strata") or () if row["denominator"] == 0 and row["value"] is None
    ]
    empty_providers = {
        row["stratum_id"].split("|")[0]
        for row in doc.get("strata") or ()
        if row["denominator"] == 0
    }
    missing = sorted(set(manifest.declared_providers) - empty_providers)
    checks.append(
        (
            "empty_stratum_is_not_measured",
            bool(empty) and not missing,
            f"not-measured rows={len(empty)} empty declaring providers={sorted(empty_providers)}",
        )
    )
    abstention_rows = [
        row for row in doc["aspects"] if row["aspect"] == ASPECT_WITHOUT_ABSTAINED_EXCLUSION
    ]
    checks.append(
        (
            "abstention_keeps_its_own_denominator",
            bool(abstention_rows) and abstention_rows[0]["denominator"] > 0,
            f"abstention denominator={abstention_rows[0]['denominator'] if abstention_rows else None}",
        )
    )
    defect_rows = [row for row in doc["aspects"] if row["aspect"] == DEFECT_ASPECT]
    defect_fp = sum(
        row["false_positive"] for row in (defect_rows[0]["per_pass"] if defect_rows else ())
    )
    checks.append(
        (
            "false_authority_numerator_is_a_defect_count",
            bool(defect_rows) and defect_fp > 0,
            f"false_authority per-pass false positives={defect_fp}",
        )
    )
    dev_slice = doc.get("dev") or {}
    checks.append(
        (
            "dev_slice_is_not_an_evaluation",
            dev_slice.get("evaluation_status") == DEV_EVALUATION_STATUS
            and dev_slice.get("non_claim") == DEV_NON_CLAIM_MARKER,
            f"dev evaluation_status={dev_slice.get('evaluation_status')!r}",
        )
    )
    holdout_rows = [row for row in (doc.get("holdout") or {}).get("aspects") or ()]
    measured = [row for row in holdout_rows if row["denominator"] > 0]
    checks.append(
        (
            "holdout_slice_is_measured",
            bool(measured),
            f"holdout measured aspects={len(measured)}/{len(holdout_rows)}",
        )
    )
    return checks


def run_selftest(root: Path, paths: Paths) -> int:
    """Prove every named refusal path on synthetic copies outside the product paths."""
    workspace = Path(tempfile.mkdtemp(prefix="m207-s03-metrics-"))
    failures: list[str] = []
    try:
        base = workspace / "world"
        _copy_frozen(root, base, paths)
        synthetic = synthetic_paths(paths)
        absent_refused = False
        try:
            publish_report(base, synthetic, allow_test_fixtures=True)
        except GateError as exc:
            if exc.diagnostic != "HUMAN_PILOT_ABSENT":
                failures.append(
                    f"empty store refused with {exc.diagnostic}, expected HUMAN_PILOT_ABSENT"
                )
            elif (base / synthetic.report).exists():
                failures.append("the absent-human run created an evaluation report")
            else:
                absent_refused = True
                print(
                    "selftest_probe=human_pilot_absent exit=3 diagnostic=HUMAN_PILOT_ABSENT ok=true"
                )
        else:
            failures.append("the absent-human run published a report (expected HUMAN_PILOT_ABSENT)")

        build_synthetic_world(base, synthetic)
        notes = publish_report(base, synthetic, allow_test_fixtures=True)
        report = json.loads((base / synthetic.report).read_text(encoding="utf-8"))
        world = _load_world(base, synthetic)
        manifest = load_manifest(base, synthetic, world.universe)
        print(
            "selftest_synthetic report=written notes="
            f"{','.join(notes) if notes else 'none'} "
            f"strata_rows={len(report['strata'])} units_total={report['units_total']}"
        )
        for name, ok, detail in selftest_invariants(report, manifest):
            print(f"selftest_invariant={name} ok={str(ok).lower()} detail={detail}")
            if not ok:
                failures.append(f"invariant {name}: {detail}")

        for probe_id, entry, diagnostic, mutate in SELFTEST_PROBES:
            scenario = workspace / probe_id
            shutil.copytree(base, scenario)
            mutate(scenario, synthetic)
            ok, detail = _expect_refusal(entry, scenario, synthetic, diagnostic)
            print(
                f"selftest_probe={probe_id} entry={entry} expected={diagnostic} "
                f"ok={str(ok).lower()} detail={detail}"
            )
            if not ok:
                failures.append(f"{probe_id}: {detail}")

        covered = {diagnostic for _, _, diagnostic, _ in SELFTEST_PROBES}
        covered.discard("")
        if absent_refused:
            # The empty-store run above is the probe for HUMAN_PILOT_ABSENT: it is the one
            # hostile path that has no synthetic world to mutate.
            covered.add("HUMAN_PILOT_ABSENT")
        contract = load_contract(base, synthetic)
        formula = formula_probes(contract, manifest)
        for name, ok, detail, diagnostic in formula:
            print(f"selftest_formula={name} ok={str(ok).lower()} detail={detail}")
            if not ok:
                failures.append(f"formula {name}: {detail}")
            if diagnostic:
                covered.add(diagnostic)
        missing = [name for name in HOSTILE_DIAGNOSTICS if name not in covered]
        print(f"selftest_hostile_coverage missing={missing}")
        if missing:
            failures.append(f"hostile diagnostics without a world probe: {missing}")
        if (root / paths.report).exists():
            failures.append("the selftest published a report inside the product tree")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    if failures:
        for failure in failures:
            print(f"FAIL SELFTEST: {failure}", file=sys.stderr)
        return FAIL_EXIT
    total = len(SELFTEST_PROBES) + 1
    print(f"{SELFTEST_MARKER} probes={total}")
    return OK_EXIT


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "run", "selftest"],
        help="'check' self-checks the frozen contour read-only, 'run' publishes the evaluation "
        "report from the human reference, 'selftest' proves the refusal paths on temp copies",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--cases", default=CASES_REL, help="frozen S01 pilot case manifest")
    parser.add_argument("--kit-pass1", default=KIT_PASS1_REL, help="frozen pass-1 coder kit")
    parser.add_argument("--kit-pass2", default=KIT_PASS2_REL, help="frozen pass-2 coder kit")
    parser.add_argument("--s02-schemas", default=S02_SCHEMAS_REL, help="frozen S02 closed schemas")
    parser.add_argument("--s01-schemas", default=S01_SCHEMAS_REL, help="frozen S01 closed schemas")
    parser.add_argument("--s03-schemas", default=S03_SCHEMAS_REL, help="frozen S03 closed schemas")
    parser.add_argument("--protocol", default=PROTOCOL_REL, help="frozen S03 evaluation protocol")
    parser.add_argument("--fixture-dir", default=FIXTURE_DIR_REL, help="frozen fragment seed dir")
    parser.add_argument("--manifest", default=MANIFEST_REL, help="frozen T02 evaluation manifest")
    parser.add_argument("--submissions", default=SUBMISSIONS_REL, help="human submission drop box")
    parser.add_argument("--adjudications", default=ADJUDICATIONS_REL, help="human adjudication box")
    parser.add_argument(
        "--intake-record", default=INTAKE_RECORD_REL, help="derived S02 intake record"
    )
    parser.add_argument(
        "--agreement-report", default=AGREEMENT_REPORT_REL, help="derived S02 report"
    )
    parser.add_argument("--inventory", default=INVENTORY_REL, help="derived S02 inventory")
    parser.add_argument(
        "--adjudication-record",
        default=ADJUDICATION_RECORD_REL,
        help="derived S02 adjudication record",
    )
    parser.add_argument(
        "--pilot-receipt", default=PILOT_RECEIPT_REL, help="derived S02 pilot receipt"
    )
    parser.add_argument("--report", default=REPORT_REL, help="frozen evaluation report path")
    parser.add_argument(
        "--allow-test-fixtures",
        action="store_true",
        help="run/check against synthetic stores outside prd/annotation (selftest only)",
    )
    return parser


def paths_from(args: argparse.Namespace) -> Paths:
    return Paths(
        cases=args.cases,
        kit_pass1=args.kit_pass1,
        kit_pass2=args.kit_pass2,
        s02_schemas=args.s02_schemas,
        s01_schemas=args.s01_schemas,
        s03_schemas=args.s03_schemas,
        protocol=args.protocol,
        fixture_dir=args.fixture_dir,
        manifest=args.manifest,
        submissions=args.submissions,
        adjudications=args.adjudications,
        intake_record=args.intake_record,
        agreement_report=args.agreement_report,
        inventory=args.inventory,
        adjudication_record=args.adjudication_record,
        pilot_receipt=args.pilot_receipt,
        report=args.report,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"FAIL MISSING_ARTIFACT: root {root} is not a directory", file=sys.stderr)
        return FAIL_EXIT
    paths = paths_from(args)
    if args.mode == "selftest":
        return run_selftest(root, paths)
    if args.mode == "run":
        return run_write(root, paths, allow_test_fixtures=args.allow_test_fixtures)
    if args.allow_test_fixtures:
        print(
            "FAIL UNSAFE_PATH: --allow-test-fixtures is only meaningful for run/selftest",
            file=sys.stderr,
        )
        return FAIL_EXIT
    return run_check(root, paths, allow_test_fixtures=False)


if __name__ == "__main__":
    raise SystemExit(main())
