#!/usr/bin/env python3
"""Pre-adjudication agreement over two independent human codings (M207 S02 T04).

Agreement is **computed, never asserted**.  RC28-F01 found the gold ladder
assigning ``DoubleCodedAccepted``, ``alpha=1.0`` and perfect counts while
consuming zero coder units (``coder_profiles=[]``, ``units=0``, ``alpha=null``).
This tool exists so that the S02 contour cannot repeat that defect: on an empty
human store it refuses with ``HUMAN_PILOT_ABSENT`` instead of reporting zero
codings as success, on a single submission it refuses publication with
``ONE_CODER_ONLY``, and a degenerate measurement becomes ``alpha=null`` with
``AGREEMENT_UNDEFINED`` rather than ``1.0``.

Invariants (each enforced in code, not merely documented):

* **Two raters, nothing less.**  ``run`` reads exactly the two submissions the
  intake record admits (``m207-s02-intake-record/v1``, T03) and re-binds them to
  the store bytes by sha256.  Anything other than one pass-1 plus one pass-2
  submission from distinct coder ids is a refusal, so a missing second coding
  can never be published as agreement (RC28-F01).
* **Honest denominators.**  ``units_total = 40`` is the frozen case universe;
  ``units_used`` is the number of units on which both passes gave a usable
  value, ``units_excluded`` the rest and ``abstained_units`` the subset where a
  coder declined to commit.  A unit where either pass abstained is excluded from
  the affected axis and reported — never silently dropped and never counted as
  agreement (RC28-F15).  The accounting is asserted, not implied
  (``DENOMINATOR_MISMATCH``).
* **α is computed or undefined.**  Krippendorff α (nominal, exactly two raters,
  Artstein & Poesio 2008) is evaluated as an exact rational from the coincidence
  matrix.  When ``units_used < 2`` or the expected disagreement ``De = 0`` the
  result is ``null`` with ``measurement_status = undefined`` and the
  ``AGREEMENT_UNDEFINED`` diagnostic; ``1.0`` is only ever the computed outcome
  of matching codings, and ``PERFECT_AGREEMENT_UNCOMPUTED`` rejects any claim of
  perfect agreement that the coincidences do not back.
* **Agreement freezes before adjudication.**  Both artifacts are written with
  ``pre_adjudication: true`` and the disagreement inventory is a *separate*
  artifact listing each disagreeing ``case_id × axis`` with the joined
  ``work_family``; adjudication (T05) resolves those entries and never rewrites
  these scores.
* **No threshold, no classification, no gold, no per-aspect rate.**  The report
  pins ``threshold: null``, ``classification: not-authorized``, ``promotion:
  none``; a document that tries to introduce a threshold, a pass/fail verdict, a
  promotion, a gold claim or a per-aspect rate is refused with
  ``THRESHOLD_REQUESTED`` / ``CLASSIFICATION_REQUESTED`` / ``PROMOTION_CLAIM`` /
  ``GOLD_CLAIM`` (those belong to S03/S04).
* **The harness never writes a submission.**  The only writes are the two
  derived evidence artifacts under ``prd/migration/rust-evidence`` (atomic
  tmp+replace); every target under ``prd/annotation/`` is refused with
  ``UNSAFE_PATH`` (D474/D476), and ``work_family`` is joined from the frozen S01
  case manifest by ``case_id`` — a coder never declares it (D480), and the
  ceiling of 4 cases per Work family stays enforced
  (``WORK_FAMILY_DOMINANCE``).

Modes:

* ``check`` -- offline self-check of the contour: the frozen contract binding
  (axes, report/inventory closed keys, diagnostic table), a deterministic
  in-memory probe of the α formula (perfect agreement, the counted mix pinned by
  the Rust contract, ``De = 0``, a single unit, one coder, denominator drift,
  an unbacked perfect agreement), the claim guards, the annotation-write
  refusal and the absent-store contract.  Prints ``M207_S02_AGREEMENT_OK``.
  With ``--allow-test-fixtures`` it additionally runs the whole ``run`` contour
  against a synthetic store outside the repository.
* ``run`` -- compute agreement over the two admitted human submissions and write
  ``prd/migration/rust-evidence/m207-s02-agreement-report.json``
  (``m207-s02-agreement-report/v1``) and
  ``prd/migration/rust-evidence/m207-s02-disagreement-inventory.json``
  (``m207-s02-disagreement-inventory/v1``).  Nothing is written unless both
  admissions validate; an empty store exits ``3`` with ``HUMAN_PILOT_ABSENT``.

The diagnostic names are exactly the ones frozen in ``$.diagnostics``; the
closed candidate list this tool may speak is ``LOCAL_DIAGNOSTICS`` below, and
``check`` fails closed if any of them leaves the frozen table.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


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


# The intake contour (T03) owns submission validation, path policy and the
# frozen-source binding.  Reusing it keeps one validator instead of a second
# divergent copy: the agreement contour reads only what the intake contour
# already admitted.
try:
    INTAKE = _load_sibling("m207_s02_intake")
except Exception as exc:  # pragma: no cover - only a repository defect reaches this
    print(
        "FAIL MISSING_ARTIFACT: cannot load the sibling intake contour "
        f"scripts/m207_s02_intake.py: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

GateError = INTAKE.GateError
Failures = list[tuple[str, str]]

MARKER = "M207_S02_AGREEMENT_OK"
RUN_MARKER = "M207_S02_AGREEMENT_COMPUTED"

ABSENT_EXIT = 3
FAIL_EXIT = 1

SCHEMA_VERSION = 1
REPORT_SCHEMA_ID = "m207-s02-agreement-report/v1"
INVENTORY_SCHEMA_ID = "m207-s02-disagreement-inventory/v1"
INTAKE_SCHEMA_ID = "m207-s02-intake-record/v1"

REPORT_REL = "prd/migration/rust-evidence/m207-s02-agreement-report.json"
INVENTORY_REL = "prd/migration/rust-evidence/m207-s02-disagreement-inventory.json"

CASE_COUNT = 40
WORK_FAMILY_CAP = 4
MIN_UNITS_FOR_ALPHA = 2

REFERENCE_DECISION_AXIS = "reference_decision"
SPAN_EXACT_AXIS = "span_exact"
ABSTENTION_AXIS = "abstention"
SLOT_AXIS_PREFIX = "slot_"
SLOT_PRESENT = "slot_present"
SLOT_ABSENT = "slot_absent"
NON_ABSTAINED = "not-abstained"
MEASUREMENT_COMPUTED = "computed"
MEASUREMENT_UNDEFINED = "undefined"

REASON_BELOW_TWO_UNITS = "below-two-units"
REASON_ZERO_EXPECTED_DISAGREEMENT = "zero-expected-disagreement"

CODER_PASS_ONE = 1
CODER_PASS_TWO = 2
CODER_PASSES = (CODER_PASS_ONE, CODER_PASS_TWO)

# The closed per-axis value encodings this tool emits.  ``span_exact`` is the
# M199 §8 triple ``(start, end, decision)``: the agreement axis compares whole
# codings, not just offsets (protocol §4).
SPAN_VALUE_TEMPLATE = "{start}:{end}:{decision}"

# The closed set of names this tool may speak; ``check`` proves every one of
# them is in the frozen ``$.diagnostics`` table.
LOCAL_DIAGNOSTICS = (
    "AGREEMENT_UNDEFINED",
    "CLASSIFICATION_REQUESTED",
    "DENOMINATOR_MISMATCH",
    "DIAGNOSTIC_TABLE_DRIFT",
    "DUPLICATE_JSON_KEY",
    "FROZEN_SOURCE_DRIFT",
    "GOLD_CLAIM",
    "HUMAN_PILOT_ABSENT",
    "LEAK_FORBIDDEN_KEY",
    "MISSING_ARTIFACT",
    "ONE_CODER_ONLY",
    "PERFECT_AGREEMENT_UNCOMPUTED",
    "PROMOTION_CLAIM",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "SLOT_SET_DRIFT",
    "SUBMISSION_CONFLICT",
    "THRESHOLD_REQUESTED",
    "UNSAFE_PATH",
    "VOCABULARY_DRIFT",
    "WORK_FAMILY_DOMINANCE",
)

# Claim keys whose *value* is pinned by the frozen contract.  A document that
# carries the key with any other value is asking for something this task may not
# produce.
CLAIM_PINS: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("threshold", lambda value: value is None, "THRESHOLD_REQUESTED"),
    ("classification", lambda value: value == "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("promotion", lambda value: value == "none", "PROMOTION_CLAIM"),
    ("is_gold", lambda value: value is False, "GOLD_CLAIM"),
)

# Key tokens that must never appear in a derived agreement artifact.  Tokens are
# compared against the tokenized key of any key outside the frozen closed key
# sets, so ``pass_1_value`` (a frozen entry key) is never mistaken for a
# pass/fail verdict.
FORBIDDEN_KEY_TOKENS: dict[str, str] = {
    "gold": "GOLD_CLAIM",
    "golden": "GOLD_CLAIM",
    "label": "LEAK_FORBIDDEN_KEY",
    "labels": "LEAK_FORBIDDEN_KEY",
    "expected": "LEAK_FORBIDDEN_KEY",
    "answer": "LEAK_FORBIDDEN_KEY",
    "answers": "LEAK_FORBIDDEN_KEY",
    "prediction": "LEAK_FORBIDDEN_KEY",
    "predictions": "LEAK_FORBIDDEN_KEY",
    "predicted": "LEAK_FORBIDDEN_KEY",
    "capture": "LEAK_FORBIDDEN_KEY",
    "captures": "LEAK_FORBIDDEN_KEY",
    "threshold": "THRESHOLD_REQUESTED",
    "cutoff": "THRESHOLD_REQUESTED",
    "percentile": "THRESHOLD_REQUESTED",
    "rate": "CLASSIFICATION_REQUESTED",
    "rates": "CLASSIFICATION_REQUESTED",
    "pass": "CLASSIFICATION_REQUESTED",
    "fail": "CLASSIFICATION_REQUESTED",
    "precision": "CLASSIFICATION_REQUESTED",
    "recall": "CLASSIFICATION_REQUESTED",
    "f1": "CLASSIFICATION_REQUESTED",
    "accuracy": "CLASSIFICATION_REQUESTED",
    "verdict": "CLASSIFICATION_REQUESTED",
    "promoted": "PROMOTION_CLAIM",
}


class ProbeFailure(Exception):
    """An in-script probe did not behave as the contour requires."""


# --------------------------------------------------------------------------- #
# Frozen contract binding.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Contract:
    """The agreement contract as declared by the frozen S02 schemas."""

    axes: tuple[str, ...]
    report_closed_keys: tuple[str, ...]
    axis_closed_keys: tuple[str, ...]
    submission_ref_closed_keys: tuple[str, ...]
    inventory_closed_keys: tuple[str, ...]
    entry_closed_keys: tuple[str, ...]
    units_total: int
    work_family_cap: int

    @property
    def allowed_keys(self) -> frozenset[str]:
        """Every key name the frozen agreement contract already declares."""
        return frozenset(
            self.report_closed_keys
            + self.axis_closed_keys
            + self.submission_ref_closed_keys
            + self.inventory_closed_keys
            + self.entry_closed_keys
        )


def derived_axes(schemas: dict[str, Any]) -> tuple[str, ...]:
    """Re-derive the agreement axes from the frozen slot space and codebook."""
    slots = (schemas.get("slot_space") or {}).get("closed_keys")
    if not isinstance(slots, list) or not slots:
        raise GateError("SLOT_SET_DRIFT", "$.slot_space.closed_keys is not the frozen slot list")
    return (
        REFERENCE_DECISION_AXIS,
        SPAN_EXACT_AXIS,
        ABSTENTION_AXIS,
        *(f"{SLOT_AXIS_PREFIX}{slot}" for slot in slots),
    )


def load_contract(world: Any) -> Contract:
    """Bind the agreement contour to the frozen S02 schema document."""
    schemas = world.schemas
    declared = schemas.get("agreement_axes")
    axes = derived_axes(schemas)
    if list(axes) != (declared if isinstance(declared, list) else []):
        raise GateError(
            "VOCABULARY_DRIFT",
            f"$.agreement_axes={declared!r} != the axes derived from the frozen slot space {list(axes)!r}",
        )
    slot_axes = [axis for axis in axes if axis.startswith(SLOT_AXIS_PREFIX)]
    frozen_slots = (schemas.get("slot_space") or {}).get("closed_keys") or []
    if len(slot_axes) != len(frozen_slots):
        raise GateError(
            "SLOT_SET_DRIFT",
            f"{len(slot_axes)} slot axes != the {len(frozen_slots)} frozen slots",
        )
    sub = schemas.get("schemas") or {}
    report = sub.get("agreement_report") or {}
    inventory = sub.get("disagreement_inventory") or {}
    if report.get("schema_id") != REPORT_SCHEMA_ID:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"$.schemas.agreement_report.schema_id={report.get('schema_id')!r} != {REPORT_SCHEMA_ID!r}",
        )
    if inventory.get("schema_id") != INVENTORY_SCHEMA_ID:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "$.schemas.disagreement_inventory.schema_id="
            f"{inventory.get('schema_id')!r} != {INVENTORY_SCHEMA_ID!r}",
        )
    report_closed = _closed_keys(report, "agreement_report", "SCHEMA_KEY_DRIFT")
    if sorted(report_closed) != sorted(report.get("required_keys") or []):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "$.schemas.agreement_report.required_keys != its closed keys",
        )
    inventory_closed = _closed_keys(inventory, "disagreement_inventory", "SCHEMA_KEY_DRIFT")
    if sorted(inventory_closed) != sorted(inventory.get("required_keys") or []):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "$.schemas.disagreement_inventory.required_keys != its closed keys",
        )
    entry_closed = _closed_keys(
        inventory, "disagreement_inventory", "SCHEMA_KEY_DRIFT", key="entry"
    )
    if sorted(entry_closed) != sorted(inventory.get("entry_required_keys") or []):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            "$.schemas.disagreement_inventory.entry_required_keys != its closed keys",
        )
    if report.get("pre_adjudication") is not True or inventory.get("pre_adjudication") is not True:
        raise GateError("SCHEMA_KEY_DRIFT", "both S02 agreement schemas must stay pre-adjudication")
    units_total = report.get("units_total")
    if units_total != CASE_COUNT:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"$.schemas.agreement_report.units_total={units_total!r} != {CASE_COUNT}",
        )
    cap = report.get("work_family_cap")
    if cap != WORK_FAMILY_CAP:
        raise GateError(
            "WORK_FAMILY_DOMINANCE",
            f"$.schemas.agreement_report.work_family_cap={cap!r} != {WORK_FAMILY_CAP}",
        )
    diagnostics = schemas.get("diagnostics")
    table = diagnostics if isinstance(diagnostics, list) else []
    for name in LOCAL_DIAGNOSTICS:
        if name not in table:
            raise GateError(
                "DIAGNOSTIC_TABLE_DRIFT",
                f"agreement diagnostic {name!r} is not in the frozen $.diagnostics table",
            )
    return Contract(
        axes=axes,
        report_closed_keys=report_closed,
        axis_closed_keys=_closed_keys(report, "agreement_report", "SCHEMA_KEY_DRIFT", key="axis"),
        submission_ref_closed_keys=_closed_keys(
            report, "agreement_report", "SCHEMA_KEY_DRIFT", key="submission_ref"
        ),
        inventory_closed_keys=inventory_closed,
        entry_closed_keys=entry_closed,
        units_total=int(units_total),
        work_family_cap=int(cap),
    )


def _closed_keys(
    sub: dict[str, Any], label: str, diagnostic: str, *, key: str = ""
) -> tuple[str, ...]:
    name = f"{key}_closed_keys" if key else "closed_keys"
    value = sub.get(name)
    if not isinstance(value, list) or not value:
        raise GateError(diagnostic, f"$.schemas.{label}.{name} is not a closed key list")
    return tuple(str(item) for item in value)


def load_families(root: Path, cases_raw: str, universe: tuple[str, ...]) -> dict[str, str]:
    """Join ``work_family`` from the frozen S01 case manifest by ``case_id`` (D480)."""
    path = INTAKE.resolve_artifact(root, cases_raw, "cases", suffix=".json")
    digest = INTAKE.sha256_file(path)
    if digest != INTAKE.CASES_SHA256:
        raise GateError(
            "FROZEN_SOURCE_DRIFT",
            f"case manifest sha256 {digest} != pinned {INTAKE.CASES_SHA256}",
        )
    manifest = INTAKE.load_json(path, "case manifest")
    families: dict[str, str] = {}
    for case in manifest.get("cases") or []:
        family = case.get("work_family")
        if not isinstance(family, str) or not family:
            raise GateError(
                "DENOMINATOR_MISMATCH",
                f"frozen case {case.get('case_id')!r} carries no work_family to join",
            )
        families[str(case.get("case_id"))] = family
    missing = [case_id for case_id in universe if case_id not in families]
    if missing:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"the work_family join does not cover {len(missing)} frozen case(s), e.g. {missing[:4]}",
        )
    return families


def family_breakdown(universe: tuple[str, ...], families: dict[str, str]) -> dict[str, Any]:
    """Count cases per Work family and enforce the frozen ceiling."""
    missing = [case_id for case_id in universe if case_id not in families]
    if missing:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"the work_family join misses {len(missing)} case(s), e.g. {missing[:4]}",
        )
    counts = Counter(families[case_id] for case_id in universe)
    biggest = max(counts.values()) if counts else 0
    if biggest > WORK_FAMILY_CAP:
        raise GateError(
            "WORK_FAMILY_DOMINANCE",
            f"a Work family carries {biggest} of {len(universe)} cases, above the ceiling "
            f"{WORK_FAMILY_CAP}",
        )
    return {
        "cap": WORK_FAMILY_CAP,
        "family_count": len(counts),
        "max_family_size": biggest,
        "families": [{"work_family": name, "case_count": counts[name]} for name in sorted(counts)],
    }


# --------------------------------------------------------------------------- #
# Axis observations and the α formula.
# --------------------------------------------------------------------------- #


def slot_is_present(slots: Any, name: str) -> bool:
    """A slot is present when it carries a written (non-empty) value.

    An absent key, an explicit ``null``, an empty string and an empty container
    all mean the coder did not write the slot; only a non-empty value is
    ``slot_present``.
    """
    if not isinstance(slots, dict) or name not in slots:
        return False
    value = slots[name]
    if value is None:
        return False
    if isinstance(value, (str, list, dict, tuple)) and len(value) == 0:
        return False
    return True


def case_observation(case: dict[str, Any], axis: str) -> str | None:
    """The value this coding contributes to ``axis``, or ``None`` when it abstains.

    ``abstention`` is its own axis and is therefore always observable; every
    other axis excludes a unit where either pass abstained (protocol §5).
    """
    if axis == ABSTENTION_AXIS:
        return case.get("abstention")
    if case.get("abstention") != NON_ABSTAINED:
        return None
    if axis == REFERENCE_DECISION_AXIS:
        return case.get("decision")
    if axis == SPAN_EXACT_AXIS:
        span = case.get("span") or {}
        return SPAN_VALUE_TEMPLATE.format(
            start=span.get("start"), end=span.get("end"), decision=case.get("decision")
        )
    if axis.startswith(SLOT_AXIS_PREFIX):
        slot = axis[len(SLOT_AXIS_PREFIX) :]
        return SLOT_PRESENT if slot_is_present(case.get("slots"), slot) else SLOT_ABSENT
    raise GateError("VOCABULARY_DRIFT", f"unknown agreement axis {axis!r}")


@dataclass(frozen=True)
class AlphaResult:
    """Exact two-rater nominal α plus the coincidence facts behind it."""

    alpha: Fraction | None
    expected_disagreement_zero: bool
    observed_disagreement_zero: bool


def krippendorff_alpha(pairs: Sequence[tuple[str, str]]) -> AlphaResult:
    """Krippendorff α (nominal, exactly two raters; Artstein & Poesio 2008).

    The coincidence matrix counts every unit once per rater, so ``n = 2 * units``
    and ``α = 1 - Do/De`` reduces to the exact rational
    ``(De_num - Do_num * (n - 1)) / De_num``.  ``De_num = 0`` means the expected
    disagreement is undefined and the caller must report ``null`` rather than
    ``1.0``.
    """
    codes = sorted({value for pair in pairs for value in pair})
    index = {code: position for position, code in enumerate(codes)}
    width = len(codes)
    coincidence = [[0] * width for _ in range(width)]
    for left, right in pairs:
        i, j = index[left], index[right]
        coincidence[i][j] += 1
        coincidence[j][i] += 1
    totals = [sum(row) for row in coincidence]
    n = sum(totals)
    diagonal = sum(coincidence[i][i] for i in range(width))
    expected = n * n - sum(total * total for total in totals)
    observed = n - diagonal
    if expected == 0:
        return AlphaResult(None, True, observed == 0)
    return AlphaResult(Fraction(expected - observed * (n - 1), expected), False, observed == 0)


@dataclass(frozen=True)
class AxisMeasurement:
    """One agreement axis with its honest denominators and its exact α."""

    axis: str
    units_total: int
    units_used: int
    units_excluded: int
    abstained_units: int
    matches: int
    alpha: Fraction | None
    expected_disagreement_zero: bool
    status: str
    reason: str | None
    pairs: tuple[tuple[str, str, str], ...]

    @property
    def observed(self) -> Fraction:
        """Observed agreement over the used units (``0`` when nothing compared)."""
        if self.units_used == 0:
            return Fraction(0, 1)
        return Fraction(self.matches, self.units_used)


def measure_axis(
    axis: str, coder_cases: dict[int, dict[str, dict[str, Any]]], universe: tuple[str, ...]
) -> AxisMeasurement:
    """Compare both passes on one axis over the frozen case universe."""
    pairs: list[tuple[str, str, str]] = []
    abstained = 0
    for case_id in universe:
        left_case = coder_cases[CODER_PASS_ONE][case_id]
        right_case = coder_cases[CODER_PASS_TWO][case_id]
        if (
            left_case.get("abstention") != NON_ABSTAINED
            or right_case.get("abstention") != NON_ABSTAINED
        ):
            abstained += 1
        left = case_observation(left_case, axis)
        right = case_observation(right_case, axis)
        if left is None or right is None:
            continue
        pairs.append((case_id, left, right))
    units_total = len(universe)
    units_used = len(pairs)
    matches = sum(1 for _, left, right in pairs if left == right)
    result = krippendorff_alpha([(left, right) for _, left, right in pairs])
    if units_used < MIN_UNITS_FOR_ALPHA:
        alpha, expected_zero, reason = (
            None,
            result.expected_disagreement_zero,
            REASON_BELOW_TWO_UNITS,
        )
    elif result.alpha is None:
        alpha, expected_zero, reason = None, True, REASON_ZERO_EXPECTED_DISAGREEMENT
    else:
        alpha, expected_zero, reason = result.alpha, False, None
    measurement = AxisMeasurement(
        axis=axis,
        units_total=units_total,
        units_used=units_used,
        units_excluded=units_total - units_used,
        abstained_units=abstained,
        matches=matches,
        alpha=alpha,
        expected_disagreement_zero=expected_zero,
        status=MEASUREMENT_COMPUTED if alpha is not None else MEASUREMENT_UNDEFINED,
        reason=reason,
        pairs=tuple(pairs),
    )
    check_denominators(measurement)
    assert_alpha_is_backed(measurement)
    return measurement


def check_denominators(measurement: AxisMeasurement) -> None:
    """The printed denominators must account for every frozen unit.

    On the abstention axis nothing is excluded (abstention *is* the measured
    outcome); on every other axis the only admissible exclusion reason is a pass
    that abstained, so ``units_excluded`` must equal ``abstained_units`` exactly.
    """
    axis = measurement.axis
    if measurement.units_total != CASE_COUNT:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"axis {axis}: units_total={measurement.units_total} != {CASE_COUNT}",
        )
    if measurement.units_used + measurement.units_excluded != measurement.units_total:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"axis {axis}: units_used={measurement.units_used} + "
            f"units_excluded={measurement.units_excluded} != units_total={measurement.units_total}",
        )
    if measurement.matches > measurement.units_used:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"axis {axis}: matches={measurement.matches} > units_used={measurement.units_used}",
        )
    if axis == ABSTENTION_AXIS:
        if measurement.units_excluded != 0 or measurement.units_used != measurement.units_total:
            raise GateError(
                "DENOMINATOR_MISMATCH",
                f"axis {axis}: abstention is measured over every unit "
                f"(used={measurement.units_used}, excluded={measurement.units_excluded})",
            )
    elif measurement.units_excluded != measurement.abstained_units:
        raise GateError(
            "DENOMINATOR_MISMATCH",
            f"axis {axis}: units_excluded={measurement.units_excluded} != "
            f"abstained_units={measurement.abstained_units}: a unit left the axis for a "
            "reason other than abstention",
        )


def assert_alpha_is_backed(measurement: AxisMeasurement) -> None:
    """``α = 1.0`` is legal only as the computed outcome of matching codings."""
    if measurement.alpha is None:
        return
    backed = (
        measurement.units_used >= MIN_UNITS_FOR_ALPHA
        and not measurement.expected_disagreement_zero
        and measurement.matches == measurement.units_used
    )
    if measurement.alpha == 1 and not backed:
        raise GateError(
            "PERFECT_AGREEMENT_UNCOMPUTED",
            f"axis {measurement.axis} reports α=1 over "
            f"{measurement.units_used} used unit(s) with {measurement.matches} match(es): "
            "perfect agreement must be computed from coincidences",
        )


# --------------------------------------------------------------------------- #
# Artifact builders.
# --------------------------------------------------------------------------- #


def axis_row(measurement: AxisMeasurement) -> dict[str, Any]:
    return {
        "axis": measurement.axis,
        "alpha": None if measurement.alpha is None else float(measurement.alpha),
        "observed_agreement": float(measurement.observed),
        "units_total": measurement.units_total,
        "units_used": measurement.units_used,
        "units_excluded": measurement.units_excluded,
        "abstained_units": measurement.abstained_units,
        "measurement_status": measurement.status,
    }


def submission_refs(passes: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "coder_id": passes[coder_pass]["coder_id"],
            "coder_pass": coder_pass,
            "sha256": passes[coder_pass]["sha256"],
            "submission_id": passes[coder_pass]["submission_id"],
        }
        for coder_pass in CODER_PASSES
    ]


def build_report(
    *,
    world: Any,
    measurements: Sequence[AxisMeasurement],
    refs: Sequence[dict[str, Any]],
    breakdown: dict[str, Any],
) -> dict[str, Any]:
    """The pre-adjudication agreement report.

    ``alpha`` at the top level is pinned ``null``: α is defined per axis and a
    single pooled number over heterogeneous axes (an abstention axis plus eight
    slot axes) would be a fabricated measurement, which is exactly the RC28-F01
    defect.  The top-level ``units_*`` counters describe the case universe; the
    per-axis rows carry the abstention-adjusted denominators.
    """
    statuses = {measurement.status for measurement in measurements}
    return {
        "schema": REPORT_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "pre_adjudication": True,
        "units_total": len(world.universe),
        "units_used": len(world.universe),
        "units_excluded": 0,
        "alpha": None,
        "measurement_status": (
            MEASUREMENT_COMPUTED if MEASUREMENT_COMPUTED in statuses else MEASUREMENT_UNDEFINED
        ),
        "threshold": None,
        "classification": "not-authorized",
        "promotion": "none",
        "submission_refs": list(refs),
        "axes": [axis_row(measurement) for measurement in measurements],
        "work_family_cap": WORK_FAMILY_CAP,
        "work_family_breakdown": breakdown,
        "non_claims": list(world.non_claims),
        "lifecycle": dict(world.lifecycle),
    }


def build_inventory(
    *,
    world: Any,
    measurements: Sequence[AxisMeasurement],
    families: dict[str, str],
) -> dict[str, Any]:
    """The disagreement inventory: every disagreeing ``case_id × axis``.

    It is deliberately a separate artifact written before adjudication, so an
    adjudicator resolves exactly the entries it lists and never rewrites the
    pre-adjudication scores.
    """
    entries = [
        {
            "axis": measurement.axis,
            "case_id": case_id,
            "pass_1_value": left,
            "pass_2_value": right,
            "work_family": families[case_id],
        }
        for measurement in measurements
        for case_id, left, right in measurement.pairs
        if left != right
    ]
    return {
        "schema": INVENTORY_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "pre_adjudication": True,
        "disagreement_count": len(entries),
        "entries": entries,
        "non_claims": list(world.non_claims),
        "lifecycle": dict(world.lifecycle),
    }


# --------------------------------------------------------------------------- #
# Claim guards, closure checks and writing.
# --------------------------------------------------------------------------- #


def guard_no_claims(node: Any, allowed_keys: frozenset[str], pointer: str = "$") -> None:
    """Refuse a document that asks for a threshold, a verdict, a promotion or gold."""
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
                    hit = FORBIDDEN_KEY_TOKENS.get(token)
                    if hit is not None:
                        raise GateError(
                            hit,
                            f"{pointer}.{key} asks for {token!r}, which is outside agreement "
                            "validation (S03 owns per-aspect rates, S04 the threshold)",
                        )
            guard_no_claims(value, allowed_keys, f"{pointer}.{key}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            guard_no_claims(item, allowed_keys, f"{pointer}[{index}]")


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


def assert_artifact_shape(
    report: dict[str, Any], inventory: dict[str, Any], contract: Contract
) -> None:
    """Both artifacts must match the frozen closed-key contract exactly."""
    check_closed_keys(report, contract.report_closed_keys, "$report")
    if not isinstance(report.get("axes"), list):
        raise GateError("SCHEMA_KEY_DRIFT", "$report.axes is not a list")
    for index, row in enumerate(report["axes"]):
        check_closed_keys(row, contract.axis_closed_keys, f"$report.axes[{index}]")
    if not isinstance(report.get("submission_refs"), list):
        raise GateError("SCHEMA_KEY_DRIFT", "$report.submission_refs is not a list")
    for index, ref in enumerate(report["submission_refs"]):
        check_closed_keys(
            ref, contract.submission_ref_closed_keys, f"$report.submission_refs[{index}]"
        )
    check_closed_keys(inventory, contract.inventory_closed_keys, "$inventory")
    if not isinstance(inventory.get("entries"), list):
        raise GateError("SCHEMA_KEY_DRIFT", "$inventory.entries is not a list")
    for index, entry in enumerate(inventory["entries"]):
        check_closed_keys(entry, contract.entry_closed_keys, f"$inventory.entries[{index}]")


def render(document: Any) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def evidence_path(root: Path, raw: str, label: str, *, allow_test_fixtures: bool) -> Path:
    """Resolve a derived-evidence target; the harness never writes a submission."""
    if raw.startswith("/"):
        if not allow_test_fixtures:
            raise GateError("UNSAFE_PATH", f"--{label}={raw!r} must be repository-relative")
        path = Path(raw)
    else:
        path = INTAKE.resolve_artifact(
            root,
            raw,
            label,
            suffix=".json",
            prefix=None if allow_test_fixtures else INTAKE.EVIDENCE_PREFIX,
        )
    if INTAKE.is_under(path, root / INTAKE.ANNOTATION_PREFIX):
        raise GateError(
            "UNSAFE_PATH",
            f"--{label}={raw!r} is under the product store prefix: the harness never writes "
            "a submission or an adjudication (D474/D476)",
        )
    if allow_test_fixtures and INTAKE.inside_product_tree(root, path):
        raise GateError(
            "UNSAFE_PATH",
            f"--{label}={raw!r} is inside the product tree: synthetic evidence lives outside "
            "the repository and its state directory",
        )
    return path


def guarded_write(root: Path, path: Path, document: dict[str, Any]) -> None:
    """The only writer in this tool; it can never touch a product store."""
    if INTAKE.is_under(path, root / INTAKE.ANNOTATION_PREFIX):
        raise GateError(
            "UNSAFE_PATH",
            f"refusing to write {path} under {INTAKE.ANNOTATION_PREFIX}: the harness never "
            "writes a submission or an adjudication (D474/D476)",
        )
    payload = render(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(payload)
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


# --------------------------------------------------------------------------- #
# Intake-record binding.
# --------------------------------------------------------------------------- #


def load_intake_record(path: Path) -> dict[str, Any]:
    """Read the T03 admission record this contour is bound to."""
    record = INTAKE.load_json(path, "intake record")
    if not isinstance(record, dict):
        raise GateError("SCHEMA_KEY_DRIFT", "the intake record is not a JSON object")
    if record.get("schema") != INTAKE_SCHEMA_ID:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"intake record schema={record.get('schema')!r} != {INTAKE_SCHEMA_ID!r}",
        )
    check_closed_keys(record, INTAKE.RECORD_CLOSED_KEYS, "$intake")
    refs = record.get("submissions")
    if not isinstance(refs, list) or not refs:
        raise GateError("SCHEMA_KEY_DRIFT", "$intake.submissions is not a non-empty list")
    for index, ref in enumerate(refs):
        check_closed_keys(
            ref, INTAKE.RECORD_SUBMISSION_CLOSED_KEYS, f"$intake.submissions[{index}]"
        )
    return record


def bind_admitted(
    record: dict[str, Any], summaries: Sequence[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    """Bind the admitted submissions to the store bytes: exactly two coders."""
    refs = record["submissions"]
    if len(refs) != 2:
        raise GateError(
            "ONE_CODER_ONLY",
            f"the intake record admits {len(refs)} submission(s): agreement is published only "
            "over two independent codings (RC28-F01)",
        )
    by_submission = {summary["submission_id"]: summary for summary in summaries}
    passes: dict[int, dict[str, Any]] = {}
    for ref in refs:
        summary = by_submission.get(ref["submission_id"])
        if summary is None:
            raise GateError(
                "SUBMISSION_CONFLICT",
                f"admitted submission {ref['submission_id']!r} is not in the store",
            )
        if ref["sha256"] != summary["sha256"]:
            raise GateError(
                "FROZEN_SOURCE_DRIFT",
                f"admitted submission {ref['submission_id']!r} hashes {summary['sha256']} but the "
                f"intake pin records {ref['sha256']}: the admitted bytes changed after intake",
            )
        if ref["coder_pass"] != summary["coder_pass"] or ref["coder_id"] != summary["coder_id"]:
            raise GateError(
                "SUBMISSION_CONFLICT",
                f"admitted submission {ref['submission_id']!r} carries coder_pass="
                f"{summary['coder_pass']!r}/coder_id={summary['coder_id']!r}, not the admitted "
                f"{ref['coder_pass']!r}/{ref['coder_id']!r}",
            )
        passes[summary["coder_pass"]] = summary
    if sorted(passes) != list(CODER_PASSES):
        raise GateError(
            "ONE_CODER_ONLY",
            f"the admitted submissions cover coder_pass={sorted(passes)}; both passes are required",
        )
    if len({passes[coder_pass]["sha256"] for coder_pass in CODER_PASSES}) != 2:
        raise GateError(
            "ONE_CODER_ONLY", "both passes are the same bytes: there is no second coder"
        )
    if passes[CODER_PASS_ONE]["coder_id"] == passes[CODER_PASS_TWO]["coder_id"]:
        raise GateError(
            "SUBMISSION_CONFLICT",
            f"both passes carry coder_id={passes[CODER_PASS_ONE]['coder_id']!r}: the two codings "
            "are not independent",
        )
    return passes


def coder_cases(
    passes: dict[int, dict[str, Any]],
    envelopes: dict[str, dict[str, Any]],
    universe: tuple[str, ...],
) -> dict[int, dict[str, dict[str, Any]]]:
    """Index every admitted coding by ``case_id`` and prove it covers the universe."""
    by_coder: dict[int, dict[str, dict[str, Any]]] = {}
    for coder_pass in CODER_PASSES:
        envelope = envelopes[passes[coder_pass]["name"]]
        cases = {
            str(case["case_id"]): case
            for case in envelope.get("cases") or []
            if isinstance(case, dict)
        }
        missing = [case_id for case_id in universe if case_id not in cases]
        if missing:
            raise GateError(
                "DENOMINATOR_MISMATCH",
                f"coder_pass={coder_pass} does not code {len(missing)} frozen case(s), e.g. "
                f"{missing[:4]}",
            )
        by_coder[coder_pass] = cases
    return by_coder


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


def run_agreement(
    root: Path,
    paths: Any,
    *,
    store_raw: str,
    intake_raw: str,
    report_raw: str,
    inventory_raw: str,
    cases_raw: str,
    allow_test_fixtures: bool,
) -> int:
    """Compute and freeze the pre-adjudication agreement over the human store."""
    try:
        store = INTAKE.store_policy(root, store_raw, allow_test_fixtures=allow_test_fixtures)
        intake_target = evidence_path(
            root, intake_raw, "intake", allow_test_fixtures=allow_test_fixtures
        )
        report_target = evidence_path(
            root, report_raw, "report", allow_test_fixtures=allow_test_fixtures
        )
        inventory_target = evidence_path(
            root, inventory_raw, "inventory", allow_test_fixtures=allow_test_fixtures
        )
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    # The human gate comes first: an absent store never reaches the machinery.
    try:
        files = INTAKE.discover_submissions(store)
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return ABSENT_EXIT if exc.diagnostic == "HUMAN_PILOT_ABSENT" else FAIL_EXIT

    failures: Failures = []
    world = INTAKE.load_world(root, paths, failures)
    if world is None or failures:
        return report_failures(failures, "")
    INTAKE.check_fragment_pins(world, failures)
    if failures:
        return report_failures(failures, "")

    summaries = INTAKE.evaluate_store(
        files, world, allow_test_fixtures=allow_test_fixtures, failures=failures
    )
    if failures:
        return report_failures(failures, "")
    if not summaries:
        return report_failures([("HUMAN_PILOT_ABSENT", "no submission was admitted")], "")

    envelopes: dict[str, dict[str, Any]] = {}
    for store_file in files:
        try:
            envelope = INTAKE.load_json_text(store_file.raw.decode("utf-8"), store_file.name)
        except GateError as exc:  # pragma: no cover - evaluate_store already parsed these bytes
            return report_failures([(exc.diagnostic, exc.detail)], "")
        envelopes[store_file.name] = envelope

    try:
        contract = load_contract(world)
        record = load_intake_record(intake_target)
        admitted = bind_admitted(record, summaries)
        if sorted(record.get("case_universe") or []) != sorted(world.universe):
            raise GateError(
                "DENOMINATOR_MISMATCH",
                "$intake.case_universe differs from the frozen case universe",
            )
        if sorted(record.get("cases_covered") or []) != sorted(world.universe):
            raise GateError(
                "DENOMINATOR_MISMATCH",
                "the admitted submissions do not cover the frozen case universe exactly once",
            )
        codings = coder_cases(admitted, envelopes, world.universe)
        families = load_families(root, cases_raw, world.universe)
        breakdown = family_breakdown(world.universe, families)
        measurements = [measure_axis(axis, codings, world.universe) for axis in contract.axes]
        report = build_report(
            world=world,
            measurements=measurements,
            refs=submission_refs(admitted),
            breakdown=breakdown,
        )
        inventory = build_inventory(world=world, measurements=measurements, families=families)
        assert_artifact_shape(report, inventory, contract)
        guard_no_claims(report, contract.allowed_keys)
        guard_no_claims(inventory, contract.allowed_keys)
        report_payload = render(report)
        inventory_payload = render(inventory)
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    try:
        _write_pair(root, report_target, report_payload, inventory_target, inventory_payload)
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    computed = [
        measurement for measurement in measurements if measurement.status == MEASUREMENT_COMPUTED
    ]
    for measurement in measurements:
        if measurement.status == MEASUREMENT_UNDEFINED:
            print(
                f"AGREEMENT_UNDEFINED axis={measurement.axis} units_used={measurement.units_used} "
                f"reason={measurement.reason}",
                file=sys.stderr,
            )
    print(
        f"{RUN_MARKER} submissions={len(admitted)} units_total={report['units_total']} "
        f"axes={len(measurements)} computed={len(computed)} "
        f"undefined={len(measurements) - len(computed)} "
        f"disagreements={inventory['disagreement_count']} report={report_raw} "
        f"inventory={inventory_raw}"
    )
    return 0


def _write_pair(
    root: Path,
    report_target: Path,
    report_payload: bytes,
    inventory_target: Path,
    inventory_payload: bytes,
) -> None:
    """Write both artifacts or neither: a half-written pair is never left behind."""
    guarded_write_bytes(root, report_target, report_payload)
    try:
        guarded_write_bytes(root, inventory_target, inventory_payload)
    except Exception:
        if report_target.exists():
            report_target.unlink()
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


def synthetic_codings(world: Any) -> dict[int, dict[str, dict[str, Any]]]:
    """Two in-memory synthetic codings with a controlled, known disagreement pattern.

    Never written anywhere: it exists so the formula, the denominators and the
    inventory can be probed without a human pilot (which this task must not
    fabricate).
    """
    pass_one = INTAKE.synthetic_submission(world, CODER_PASS_ONE, "coder-alpha")["cases"]
    pass_two = INTAKE.synthetic_submission(world, CODER_PASS_TWO, "coder-beta")["cases"]
    pass_two[1]["decision"] = "reference"
    pass_two[1]["slots"] = {"date": "01.01.2020"}
    return {
        CODER_PASS_ONE: {str(case["case_id"]): case for case in pass_one},
        CODER_PASS_TWO: {str(case["case_id"]): case for case in pass_two},
    }


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


def build_pair(
    world: Any, contract: Contract, families: dict[str, str]
) -> tuple[dict, dict, list[AxisMeasurement]]:
    codings = synthetic_codings(world)
    measurements = [measure_axis(axis, codings, world.universe) for axis in contract.axes]
    report = build_report(
        world=world,
        measurements=measurements,
        refs=[
            {
                "coder_id": coder_id,
                "coder_pass": coder_pass,
                "sha256": "0" * 64,
                "submission_id": f"m207-s02-submission-pass-{coder_pass}",
            }
            for coder_pass, coder_id in ((1, "coder-alpha"), (2, "coder-beta"))
        ],
        breakdown=family_breakdown(world.universe, families),
    )
    inventory = build_inventory(world=world, measurements=measurements, families=families)
    return report, inventory, measurements


def formula_probes(
    world: Any, contract: Contract, families: dict[str, str]
) -> list[tuple[str, str | None]]:
    """Deterministic probes of the α formula, the denominators and the guards."""
    probes: list[tuple[str, str | None]] = []
    codings = synthetic_codings(world)
    measurements = [measure_axis(axis, codings, world.universe) for axis in contract.axes]
    by_axis = {measurement.axis: measurement for measurement in measurements}
    report, inventory, _ = build_pair(world, contract, families)

    def run(name: str, call: Callable[[], None]) -> None:
        try:
            call()
        except ProbeFailure as exc:
            probes.append((name, str(exc)))
        except GateError as exc:
            probes.append((name, f"unexpected {exc.diagnostic}: {exc.detail}"))
        else:
            probes.append((name, None))

    def perfect_agreement_is_one() -> None:
        result = krippendorff_alpha(
            [("reference", "reference"), ("not_a_reference", "not_a_reference")]
        )
        require(result.alpha == Fraction(1, 1), f"α={result.alpha!r} instead of the computed 1")
        require(result.expected_disagreement_zero is False, "De must not be degenerate here")

    def counted_mix_matches_the_rust_pin() -> None:
        # Four pairs (A,A), (A,A), (A,B), (B,B): D_o = 1/4, D_e = 15/28, α = 8/15.
        # The same rational is pinned by the Rust C5 contract
        # (crates/ln-decode/tests/npa_lawref_acceptance_contract.rs).
        result = krippendorff_alpha([("A", "A"), ("A", "A"), ("A", "B"), ("B", "B")])
        require(result.alpha == Fraction(8, 15), f"α={result.alpha!r} instead of 8/15")

    def alpha_shortcut_equals_the_definition() -> None:
        # The coincidence-matrix shortcut must equal the definition
        # α = 1 - D_o/D_e, evaluated with an independent exact-rational code path.
        samples = [
            [("A", "A"), ("A", "A"), ("A", "B"), ("B", "B")],
            [("N", "N")] * (CASE_COUNT - 1) + [("N", "R")],
            [("x", "y"), ("y", "y"), ("z", "x"), ("z", "z"), ("y", "z")],
            [("a", "a"), ("b", "b"), ("c", "c")],
            [("p", "q"), ("q", "p")],
        ]
        for pairs in samples:
            counts = Counter()
            for left, right in pairs:
                counts[left] += 1
                counts[right] += 1
            n = sum(counts.values())
            de = Fraction(n * n - sum(value * value for value in counts.values()), n * (n - 1))
            if de == 0:
                continue
            disagreeing = sum(1 for left, right in pairs if left != right)
            definition = 1 - Fraction(2 * disagreeing, n) / de
            shortcut = krippendorff_alpha(pairs).alpha
            require(
                shortcut == definition,
                f"α={shortcut!r} != the definition {definition!r} over {len(pairs)} pair(s)",
            )

    def zero_expected_disagreement_is_undefined() -> None:
        result = krippendorff_alpha([("A", "A"), ("A", "A")])
        require(result.alpha is None, "De = 0 must not become a number")
        require(result.expected_disagreement_zero, "De = 0 must be reported as degenerate")

    def single_unit_is_undefined() -> None:
        measurement = measure_axis(
            REFERENCE_DECISION_AXIS,
            _codings_with_idle_passes(world),
            world.universe,
        )
        require(measurement.alpha is None, "a one-unit axis must not report an α")
        require(
            measurement.status == MEASUREMENT_UNDEFINED,
            f"status={measurement.status!r} instead of undefined",
        )
        require(
            measurement.reason == REASON_BELOW_TWO_UNITS,
            f"reason={measurement.reason!r} instead of {REASON_BELOW_TWO_UNITS!r}",
        )

    def one_coder_is_refused() -> None:
        record = {
            "submissions": [
                _ref("m207-s02-submission-pass-1", 1, "coder-alpha"),
            ]
        }
        expect_gate(
            "ONE_CODER_ONLY",
            lambda: bind_admitted(
                record, [_summary("m207-s02-submission-pass-1", 1, "coder-alpha")]
            ),
        )

    def denominator_drift_is_refused() -> None:
        measurement = AxisMeasurement(
            axis=REFERENCE_DECISION_AXIS,
            units_total=CASE_COUNT,
            units_used=CASE_COUNT - 1,
            units_excluded=0,
            abstained_units=0,
            matches=10,
            alpha=Fraction(1, 2),
            expected_disagreement_zero=False,
            status=MEASUREMENT_COMPUTED,
            reason=None,
            pairs=(),
        )
        expect_gate("DENOMINATOR_MISMATCH", lambda: check_denominators(measurement))

    def exclusion_without_abstention_is_refused() -> None:
        measurement = AxisMeasurement(
            axis=REFERENCE_DECISION_AXIS,
            units_total=CASE_COUNT,
            units_used=CASE_COUNT - 2,
            units_excluded=2,
            abstained_units=1,
            matches=10,
            alpha=Fraction(1, 2),
            expected_disagreement_zero=False,
            status=MEASUREMENT_COMPUTED,
            reason=None,
            pairs=(),
        )
        expect_gate("DENOMINATOR_MISMATCH", lambda: check_denominators(measurement))

    def unbacked_perfect_agreement_is_refused() -> None:
        measurement = AxisMeasurement(
            axis=SLOT_AXIS_PREFIX + "date",
            units_total=CASE_COUNT,
            units_used=CASE_COUNT,
            units_excluded=0,
            abstained_units=0,
            matches=CASE_COUNT,
            alpha=Fraction(1, 1),
            expected_disagreement_zero=True,
            status=MEASUREMENT_COMPUTED,
            reason=None,
            pairs=(),
        )
        expect_gate("PERFECT_AGREEMENT_UNCOMPUTED", lambda: assert_alpha_is_backed(measurement))

    def agreement_without_matches_is_refused() -> None:
        measurement = AxisMeasurement(
            axis=REFERENCE_DECISION_AXIS,
            units_total=CASE_COUNT,
            units_used=CASE_COUNT,
            units_excluded=0,
            abstained_units=0,
            matches=CASE_COUNT - 1,
            alpha=Fraction(1, 1),
            expected_disagreement_zero=False,
            status=MEASUREMENT_COMPUTED,
            reason=None,
            pairs=(),
        )
        expect_gate("PERFECT_AGREEMENT_UNCOMPUTED", lambda: assert_alpha_is_backed(measurement))

    def threshold_request_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document["agreement_threshold"] = 0.8
        expect_gate("THRESHOLD_REQUESTED", lambda: guard_no_claims(document, contract.allowed_keys))

    def threshold_claim_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document["threshold"] = 0.8
        expect_gate("THRESHOLD_REQUESTED", lambda: guard_no_claims(document, contract.allowed_keys))

    def per_aspect_rate_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document["axes"][0]["precision"] = 0.9
        expect_gate(
            "CLASSIFICATION_REQUESTED",
            lambda: guard_no_claims(document, contract.allowed_keys),
        )

    def pass_fail_verdict_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document["pass_fail"] = "pass"
        expect_gate(
            "CLASSIFICATION_REQUESTED",
            lambda: guard_no_claims(document, contract.allowed_keys),
        )

    def classification_claim_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document["classification"] = "accepted"
        expect_gate(
            "CLASSIFICATION_REQUESTED",
            lambda: guard_no_claims(document, contract.allowed_keys),
        )

    def gold_claim_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document["gold_labels"] = []
        expect_gate("GOLD_CLAIM", lambda: guard_no_claims(document, contract.allowed_keys))

    def is_gold_claim_is_refused() -> None:
        document = json.loads(json.dumps(inventory))
        document["is_gold"] = True
        expect_gate("GOLD_CLAIM", lambda: guard_no_claims(document, contract.allowed_keys))

    def prediction_key_is_refused() -> None:
        document = json.loads(json.dumps(inventory))
        document["entries"][0]["expected_answer"] = "reference"
        expect_gate("LEAK_FORBIDDEN_KEY", lambda: guard_no_claims(document, contract.allowed_keys))

    def promotion_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document["promotion"] = "promoted"
        expect_gate("PROMOTION_CLAIM", lambda: guard_no_claims(document, contract.allowed_keys))

    def built_pair_matches_the_contract() -> None:
        assert_artifact_shape(report, inventory, contract)
        guard_no_claims(report, contract.allowed_keys)
        guard_no_claims(inventory, contract.allowed_keys)
        require(
            report["pre_adjudication"] is True and inventory["pre_adjudication"] is True,
            "both artifacts must stay pre-adjudication",
        )
        require(report["threshold"] is None, "the report must pin threshold: null")
        require(
            report["classification"] == "not-authorized",
            "the report must pin classification: not-authorized",
        )
        require(report["promotion"] == "none", "the report must pin promotion: none")
        require(report["alpha"] is None, "no pooled α may be fabricated at the top level")

    def dropped_report_key_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document.pop("threshold")
        expect_gate(
            "SCHEMA_KEY_DRIFT",
            lambda: check_closed_keys(document, contract.report_closed_keys, "$report"),
        )

    def extra_report_key_is_refused() -> None:
        document = json.loads(json.dumps(report))
        document["per_aspect_rates"] = {}
        expect_gate(
            "SCHEMA_KEY_DRIFT",
            lambda: check_closed_keys(document, contract.report_closed_keys, "$report"),
        )

    def extra_inventory_entry_key_is_refused() -> None:
        document = json.loads(json.dumps(inventory))
        document["entries"][0]["span_exact"] = True
        expect_gate(
            "SCHEMA_KEY_DRIFT",
            lambda: check_closed_keys(document["entries"][0], contract.entry_closed_keys, "$entry"),
        )

    def axes_match_the_frozen_schema() -> None:
        require(
            tuple(measurement.axis for measurement in measurements) == contract.axes,
            "the measured axes must be exactly the frozen agreement axes, in order",
        )
        slot_axes = [axis for axis in contract.axes if axis.startswith(SLOT_AXIS_PREFIX)]
        require(len(slot_axes) == 8, f"expected eight slot axes, saw {len(slot_axes)}")

    def synthetic_pair_measurements_are_known() -> None:
        reference = by_axis[REFERENCE_DECISION_AXIS]
        require(reference.units_used == CASE_COUNT, "every case is comparable on the decision axis")
        require(
            reference.matches == CASE_COUNT - 1, "exactly one decision disagrees by construction"
        )
        require(reference.alpha == Fraction(0, 1), f"α={reference.alpha!r} instead of 0")
        require(
            reference.observed == Fraction(CASE_COUNT - 1, CASE_COUNT),
            f"observed={reference.observed!r} instead of 39/40",
        )
        abstention = by_axis[ABSTENTION_AXIS]
        require(
            abstention.alpha is None and abstention.status == MEASUREMENT_UNDEFINED,
            "an all-not-abstained pair has De = 0 and must be undefined",
        )
        require(
            abstention.observed == Fraction(1, 1),
            "observed agreement stays 1.0 even when α is undefined",
        )
        require(
            by_axis[SPAN_EXACT_AXIS].alpha is not None,
            "a differing decision makes the span_exact axis computable",
        )
        undefined = [m.axis for m in measurements if m.status == MEASUREMENT_UNDEFINED]
        require(len(undefined) == 8, f"expected eight degenerate synthetic axes, saw {undefined}")

    def inventory_lists_every_disagreement() -> None:
        require(inventory["disagreement_count"] == len(inventory["entries"]), "count must match")
        keys = {(entry["axis"], entry["case_id"]) for entry in inventory["entries"]}
        require(
            (REFERENCE_DECISION_AXIS, world.universe[1]) in keys,
            "the constructed decision disagreement must be inventoried",
        )
        require(
            (SPAN_EXACT_AXIS, world.universe[1]) in keys,
            "the constructed span disagreement must be inventoried",
        )
        require(
            (SLOT_AXIS_PREFIX + "date", world.universe[1]) in keys,
            "the constructed slot disagreement must be inventoried",
        )
        require(
            all(entry["work_family"] for entry in inventory["entries"]),
            "every inventory entry carries the joined work_family",
        )
        require(
            all(entry["pass_1_value"] != entry["pass_2_value"] for entry in inventory["entries"]),
            "the inventory lists disagreements only",
        )

    def abstention_is_its_own_axis() -> None:
        codings_with_abstention = {
            CODER_PASS_ONE: {
                case["case_id"]: case
                for case in INTAKE.synthetic_submission(world, 1, "coder-alpha")["cases"]
            },
            CODER_PASS_TWO: {
                case["case_id"]: case
                for case in INTAKE.synthetic_submission(world, 2, "coder-beta")["cases"]
            },
        }
        target = world.universe[0]
        codings_with_abstention[CODER_PASS_ONE][target]["abstention"] = "ambiguous"
        decision = measure_axis(REFERENCE_DECISION_AXIS, codings_with_abstention, world.universe)
        abstention = measure_axis(ABSTENTION_AXIS, codings_with_abstention, world.universe)
        require(
            decision.units_used == CASE_COUNT - 1 and decision.units_excluded == 1,
            f"an abstaining pass must leave the decision axis (used={decision.units_used})",
        )
        require(
            decision.abstained_units == 1,
            "the excluded unit must be attributed to abstention, not to a silent drop",
        )
        require(
            abstention.units_used == CASE_COUNT and abstention.units_excluded == 0,
            "the abstention axis keeps every unit",
        )
        require(
            abstention.abstained_units == 1,
            "the abstention axis still reports how many units abstained",
        )
        require(
            abstention.matches == CASE_COUNT - 1,
            "the abstaining coder disagrees with the committing coder on the abstention axis",
        )

    def slot_presence_rule() -> None:
        require(slot_is_present({"date": "01.01.2020"}, "date"), "a written value is present")
        require(not slot_is_present({"date": None}, "date"), "an explicit null is absent")
        require(
            not slot_is_present({"marker_chain": []}, "marker_chain"), "an empty list is absent"
        )
        require(not slot_is_present({"date": ""}, "date"), "an empty string is absent")
        require(not slot_is_present({}, "date"), "a missing key is absent")
        require(
            not slot_is_present({"marker_chain": ["st", "pp"]}, "hier_nums"),
            "a slot the coder did not write is absent",
        )
        require(
            slot_is_present({"range": {"start": "1", "end": "4.1"}}, "range"),
            "a written range object is present",
        )

    def span_axis_compares_whole_codings() -> None:
        left = {
            "span": {"start": 0, "end": 71},
            "decision": "reference",
            "abstention": NON_ABSTAINED,
        }
        same = {
            "span": {"start": 0, "end": 71},
            "decision": "reference",
            "abstention": NON_ABSTAINED,
        }
        shifted = {
            "span": {"start": 0, "end": 70},
            "decision": "reference",
            "abstention": NON_ABSTAINED,
        }
        other_decision = {
            "span": {"start": 0, "end": 71},
            "decision": "not_a_reference",
            "abstention": NON_ABSTAINED,
        }
        require(
            case_observation(left, SPAN_EXACT_AXIS) == case_observation(same, SPAN_EXACT_AXIS),
            "identical triples must match",
        )
        require(
            case_observation(left, SPAN_EXACT_AXIS) != case_observation(shifted, SPAN_EXACT_AXIS),
            "shifted boundaries must be a disagreement",
        )
        require(
            case_observation(left, SPAN_EXACT_AXIS)
            != case_observation(other_decision, SPAN_EXACT_AXIS),
            "a different decision must be a disagreement",
        )
        require(
            case_observation(left, SPAN_EXACT_AXIS) == "0:71:reference",
            "the span value is the documented M199 §8 triple",
        )

    def work_family_ceiling_is_enforced() -> None:
        crowded = {
            f"case-{index}": ("stem:same" if index < 5 else f"stem:{index}")
            for index in range(CASE_COUNT)
        }
        expect_gate(
            "WORK_FAMILY_DOMINANCE",
            lambda: family_breakdown(tuple(crowded), crowded),
        )

    def work_family_join_must_cover_the_universe() -> None:
        expect_gate(
            "DENOMINATOR_MISMATCH",
            lambda: family_breakdown(("m207-s01-case-999",), {}),
        )

    def annotation_write_is_refused() -> None:
        target = ROOT / INTAKE.ANNOTATION_PREFIX / "m207-s02-agreement-probe.json"
        expect_gate(
            "UNSAFE_PATH",
            lambda: guarded_write(
                ROOT,
                target,
                build_report(
                    world=world,
                    measurements=measurements,
                    refs=[],
                    breakdown=family_breakdown(world.universe, families),
                ),
            ),
        )
        require(not target.exists(), "the writer created a file under prd/annotation/")

    def absent_store_is_refused(tmp_root: Path) -> None:
        tmp_root.mkdir(parents=True, exist_ok=True)
        empty = tmp_root / "empty-store"
        empty.mkdir()
        for candidate in (empty, tmp_root / "missing-store"):
            expect_gate("HUMAN_PILOT_ABSENT", lambda: INTAKE.discover_submissions(candidate))

    run("alpha_perfect_agreement_is_one", perfect_agreement_is_one)
    run("alpha_counted_mix_matches_the_rust_pin", counted_mix_matches_the_rust_pin)
    run("alpha_shortcut_equals_the_definition", alpha_shortcut_equals_the_definition)
    run("alpha_zero_expected_disagreement_is_undefined", zero_expected_disagreement_is_undefined)
    run("alpha_single_unit_is_undefined", single_unit_is_undefined)
    run("one_coder_is_refused", one_coder_is_refused)
    run("denominator_drift_is_refused", denominator_drift_is_refused)
    run("exclusion_without_abstention_is_refused", exclusion_without_abstention_is_refused)
    run("unbacked_perfect_agreement_is_refused", unbacked_perfect_agreement_is_refused)
    run("agreement_without_matches_is_refused", agreement_without_matches_is_refused)
    run("threshold_request_is_refused", threshold_request_is_refused)
    run("threshold_claim_is_refused", threshold_claim_is_refused)
    run("per_aspect_rate_is_refused", per_aspect_rate_is_refused)
    run("pass_fail_verdict_is_refused", pass_fail_verdict_is_refused)
    run("classification_claim_is_refused", classification_claim_is_refused)
    run("gold_claim_is_refused", gold_claim_is_refused)
    run("is_gold_claim_is_refused", is_gold_claim_is_refused)
    run("prediction_key_is_refused", prediction_key_is_refused)
    run("promotion_is_refused", promotion_is_refused)
    run("built_pair_matches_the_contract", built_pair_matches_the_contract)
    run("dropped_report_key_is_refused", dropped_report_key_is_refused)
    run("extra_report_key_is_refused", extra_report_key_is_refused)
    run("extra_inventory_entry_key_is_refused", extra_inventory_entry_key_is_refused)
    run("axes_match_the_frozen_schema", axes_match_the_frozen_schema)
    run("synthetic_pair_measurements_are_known", synthetic_pair_measurements_are_known)
    run("inventory_lists_every_disagreement", inventory_lists_every_disagreement)
    run("abstention_is_its_own_axis", abstention_is_its_own_axis)
    run("slot_presence_rule", slot_presence_rule)
    run("span_axis_compares_whole_codings", span_axis_compares_whole_codings)
    run("work_family_ceiling_is_enforced", work_family_ceiling_is_enforced)
    run("work_family_join_must_cover_the_universe", work_family_join_must_cover_the_universe)

    tmp_root = Path(tempfile.mkdtemp(prefix="m207-s02-agreement-probe-"))
    try:
        run("annotation_write_is_refused", annotation_write_is_refused)
        run("absent_store_is_refused", lambda: absent_store_is_refused(tmp_root))
    finally:
        _cleanup(tmp_root)
    return probes


def _codings_with_idle_passes(world: Any) -> dict[int, dict[str, dict[str, Any]]]:
    """Both passes abstain on every case except the first: a one-unit axis."""
    idle = {
        coder_pass: {
            str(case["case_id"]): dict(case, abstention="ambiguous")
            for case in INTAKE.synthetic_submission(world, coder_pass, f"coder-{coder_pass}")[
                "cases"
            ]
        }
        for coder_pass in CODER_PASSES
    }
    first = world.universe[0]
    for coder_pass in CODER_PASSES:
        idle[coder_pass][first]["abstention"] = NON_ABSTAINED
        idle[coder_pass][first]["decision"] = "reference"
    return idle


def _ref(submission_id: str, coder_pass: int, coder_id: str) -> dict[str, Any]:
    return {
        "case_count": CASE_COUNT,
        "coder_id": coder_id,
        "coder_pass": coder_pass,
        "provenance": "human-reviewed",
        "sha256": "0" * 64,
        "submission_id": submission_id,
    }


def _summary(submission_id: str, coder_pass: int, coder_id: str) -> dict[str, Any]:
    summary = _ref(submission_id, coder_pass, coder_id)
    summary["name"] = f"{submission_id}.json"
    return summary


def _cleanup(root: Path) -> None:
    if not root.exists():
        return
    for child in sorted(root.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    root.rmdir()


def fixture_run_probes(root: Path, paths: Any, world: Any) -> list[tuple[str, str | None]]:
    """Run the whole ``run`` contour on a synthetic store outside the repository."""
    probes: list[tuple[str, str | None]] = []
    tmp_root = Path(tempfile.mkdtemp(prefix="m207-s02-agreement-fixture-"))
    try:
        store = tmp_root / "store"
        store.mkdir(parents=True)
        codings = synthetic_codings(world)
        envelopes = {
            CODER_PASS_ONE: INTAKE.synthetic_submission(world, CODER_PASS_ONE, "coder-alpha"),
            CODER_PASS_TWO: INTAKE.synthetic_submission(world, CODER_PASS_TWO, "coder-beta"),
        }
        envelopes[CODER_PASS_ONE]["cases"] = [
            codings[CODER_PASS_ONE][case_id] for case_id in world.universe
        ]
        envelopes[CODER_PASS_TWO]["cases"] = [
            codings[CODER_PASS_TWO][case_id] for case_id in world.universe
        ]
        files = []
        for coder_pass in CODER_PASSES:
            name = f"submission-pass-{coder_pass}.json"
            payload = (
                json.dumps(envelopes[coder_pass], ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8")
            (store / name).write_bytes(payload)
            files.append(INTAKE.StoreFile(name=name, path=store / name, raw=payload))
        failures: Failures = []
        summaries = INTAKE.evaluate_store(files, world, allow_test_fixtures=True, failures=failures)
        if failures or len(summaries) != 2:
            probes.append(("fixture_pair_admits", f"the synthetic pair was refused: {failures}"))
            return probes
        probes.append(("fixture_pair_admits", None))
        record_path = tmp_root / "intake.json"
        INTAKE.write_record(record_path, INTAKE.build_record(world, summaries))

        def run_once(report_name: str, inventory_name: str) -> tuple[int, Path, Path]:
            report = tmp_root / report_name
            inventory = tmp_root / inventory_name
            code = run_agreement(
                root,
                paths,
                store_raw=str(store),
                intake_raw=str(record_path),
                report_raw=str(report),
                inventory_raw=str(inventory),
                cases_raw=paths.cases,
                allow_test_fixtures=True,
            )
            return code, report, inventory

        code, report, inventory = run_once("report.json", "inventory.json")
        probes.append(
            (
                "fixture_run_writes_both_artifacts",
                None
                if code == 0 and report.is_file() and inventory.is_file()
                else f"exit={code} report={report.is_file()} inventory={inventory.is_file()}",
            )
        )
        first = report.read_bytes()
        code_again, report_again, _ = run_once("report-again.json", "inventory-again.json")
        probes.append(
            (
                "fixture_run_is_deterministic",
                None
                if code_again == 0 and report_again.read_bytes() == first
                else "the same inputs produced different report bytes",
            )
        )
        document = json.loads(report.read_text(encoding="utf-8"))
        inventory_document = json.loads(inventory.read_text(encoding="utf-8"))
        probes.append(
            (
                "fixture_run_report_is_pre_adjudication",
                None
                if document["pre_adjudication"] is True
                and document["threshold"] is None
                and document["classification"] == "not-authorized"
                and document["promotion"] == "none"
                and document["alpha"] is None
                else "the produced report left the pre-adjudication pins",
            )
        )
        probes.append(
            (
                "fixture_run_inventory_lists_the_disagreements",
                None
                if inventory_document["disagreement_count"] == len(inventory_document["entries"])
                and inventory_document["disagreement_count"] > 0
                else "the produced inventory is empty or its count drifted",
            )
        )
        degraded = json.loads(record_path.read_text(encoding="utf-8"))
        degraded["submissions"][0]["sha256"] = "f" * 64
        degraded_path = tmp_root / "intake-drifted.json"
        degraded_path.write_bytes(
            (json.dumps(degraded, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
        code = run_agreement(
            root,
            paths,
            store_raw=str(store),
            intake_raw=str(degraded_path),
            report_raw=str(tmp_root / "report-drifted.json"),
            inventory_raw=str(tmp_root / "inventory-drifted.json"),
            cases_raw=paths.cases,
            allow_test_fixtures=True,
        )
        probes.append(
            (
                "fixture_intake_pin_drift_is_refused",
                None
                if code == FAIL_EXIT and not (tmp_root / "report-drifted.json").exists()
                else f"exit={code} but a drifted admission was not refused",
            )
        )
        one_coder = tmp_root / "one-coder-store"
        one_coder.mkdir()
        (one_coder / "submission-pass-1.json").write_bytes(files[0].raw)
        code = run_agreement(
            root,
            paths,
            store_raw=str(one_coder),
            intake_raw=str(record_path),
            report_raw=str(tmp_root / "report-one.json"),
            inventory_raw=str(tmp_root / "inventory-one.json"),
            cases_raw=paths.cases,
            allow_test_fixtures=True,
        )
        probes.append(
            (
                "fixture_one_coder_only_is_refused",
                None
                if code == FAIL_EXIT
                and not (tmp_root / "report-one.json").exists()
                and not (tmp_root / "inventory-one.json").exists()
                else f"exit={code}: a single coding must never be published as agreement",
            )
        )
        empty = tmp_root / "empty-store"
        empty.mkdir()
        code = run_agreement(
            root,
            paths,
            store_raw=str(empty),
            intake_raw=str(record_path),
            report_raw=str(tmp_root / "report-empty.json"),
            inventory_raw=str(tmp_root / "inventory-empty.json"),
            cases_raw=paths.cases,
            allow_test_fixtures=True,
        )
        probes.append(
            (
                "fixture_empty_store_is_absent",
                None
                if code == ABSENT_EXIT
                and not (tmp_root / "report-empty.json").exists()
                and not (tmp_root / "inventory-empty.json").exists()
                else f"exit={code}: an empty store must exit {ABSENT_EXIT} and write nothing",
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
        families = load_families(root, paths.cases, world.universe)
    except GateError as exc:
        return report_failures([(exc.diagnostic, exc.detail)], "")

    probes = formula_probes(world, contract, families)
    if allow_test_fixtures:
        probes.extend(fixture_run_probes(root, paths, world))
    failed = [(name, detail) for name, detail in probes if detail is not None]
    if failed:
        for name, detail in failed:
            print(f"FAIL PROBE_FAILED: probe {name} failed: {detail}", file=sys.stderr)
        return FAIL_EXIT

    computed = sum(1 for probe_name, _ in probes if probe_name.startswith("alpha_"))
    print(
        f"{MARKER} axes={len(contract.axes)} units_total={contract.units_total} "
        f"diagnostics={len(LOCAL_DIAGNOSTICS)} probes={len(probes)} "
        f"alpha_probes={computed} work_family_cap={contract.work_family_cap} "
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
        help="'check' self-checks the contour read-only; 'run' computes agreement over the "
        "two admitted human submissions",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument(
        "--store", default=INTAKE.STORE_REL, help="human submission drop box (D480)"
    )
    parser.add_argument(
        "--intake",
        default=INTAKE.RECORD_REL,
        help="derived intake record naming the two admitted submissions",
    )
    parser.add_argument("--report", default=REPORT_REL, help="derived agreement report path")
    parser.add_argument(
        "--inventory", default=INVENTORY_REL, help="derived disagreement inventory path"
    )
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
        return run_agreement(
            root,
            paths,
            store_raw=args.store,
            intake_raw=args.intake,
            report_raw=args.report,
            inventory_raw=args.inventory,
            cases_raw=args.cases,
            allow_test_fixtures=args.allow_test_fixtures,
        )
    return run_check(root, paths, allow_test_fixtures=args.allow_test_fixtures)


if __name__ == "__main__":
    raise SystemExit(main())
