#!/usr/bin/env python3
"""Fail-closed intake of human coder submissions for M207 S02 (T03).

A human submission is **untrusted hand-authored input**.  This tool is the only
way the S02 harness admits one, and its first duty is to refuse: it validates
every candidate against the frozen contract and exits non-zero with a named
diagnostic instead of guessing, repairing or fabricating anything.

Invariants (each enforced in code, not merely documented):

* **The harness never writes a submission.**  ``write_record`` refuses any
  target under ``prd/annotation/`` (``UNSAFE_PATH``), so the product stores are
  structurally read-only to this tool (D474/D476).  It does not create, edit,
  truncate or delete a submission file; the only file it can write is the
  derived evidence record under ``prd/migration/rust-evidence`` (D480).
* **Zero codings is never success.**  A missing store, a store with no
  ``*.json`` submission, or an unreadable store exits with ``HUMAN_PILOT_ABSENT``
  and a distinct exit code (``3``); no record is written.  ``1`` is a red
  contour (a submission was read and refused), so a green machinery run can
  never be confused with an absent human pilot.
* **The frozen contract is read, not restated.**  The submission form
  (``m207-s01-coding-submission/v1``, reused verbatim per D475), the closed slot
  space, the vocabularies, the store prefix lock and the diagnostic table are
  re-derived from ``prd/annotation/m207-s02-schemas.json`` and
  ``prd/annotation/m207-s01-schemas.json`` at run time; drift is
  ``SLOT_SET_DRIFT`` / ``VOCABULARY_DRIFT`` / ``SUBMISSION_SCHEMA_DRIFT`` /
  ``DIAGNOSTIC_TABLE_DRIFT`` / ``SCHEMA_KEY_DRIFT``.
* **Spans are checked against frozen bytes.**  Every case binds to the fragment
  file named by the frozen coder kit (existence, byte length and sha256), and a
  span must satisfy ``0 <= start < end <= byte_len`` inside the case's offered
  region; the slice must decode as UTF-8, so both endpoints are code-point
  boundaries (``SPAN_BEYOND_EOF`` / ``SPAN_NOT_UTF8_BOUNDARY`` /
  ``SPAN_NOT_ORIGIN``).
* **Test fixtures never enter a product store.**  A candidate whose file name,
  ``submission_id``, ``coder_id`` or key names carry a fixture marker token
  (``fixture``/``synthetic``/``example``/``dummy``/``placeholder``/``mock``/
  ``fake``/``toy``/``test``/``probe``/``selftest``) is ``TEST_FIXTURE_IN_STORE``
  unless ``--allow-test-fixtures`` is passed -- and that flag in turn forbids the
  product store entirely (``UNSAFE_PATH``), so synthetic data can only ever be
  admitted outside ``prd/annotation/``.

Modes:

* ``check`` -- offline self-check of the contour, read-only and without reading
  any human data: case-universe equality (manifest vs both kits vs fragment
  bytes), the closed diagnostic table, the schema binding, a synthetic pair that
  must validate clean in memory, the fixture refusal on the product store, the
  annotation-write refusal and the absent-store contract.  Prints
  ``M207_S02_INTAKE_OK`` with counters.
* ``run [--store ...] [--record ...]`` -- admit the human store, then write
  ``prd/migration/rust-evidence/m207-s02-intake-record.json``
  (``m207-s02-intake-record/v1``) carrying each submission's sha256 pin,
  ``submission_count`` and ``cases_covered``.  Nothing is written unless every
  submission is admitted.
* ``selftest --allow-test-fixtures [tmp]`` -- the hostile suite (see
  ``run_selftest``) on synthetic stores outside the repository; prints
  ``M207_S02_SELFTEST_OK``.

The diagnostic names are exactly the ones frozen in ``$.diagnostics``; the
closed candidate list this tool may speak is ``LOCAL_DIAGNOSTICS`` below, and
``check`` fails closed if any of them leaves the frozen table.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S02_INTAKE_OK"
SELFTEST_MARKER = "M207_S02_SELFTEST_OK"
ACCEPT_MARKER = "M207_S02_INTAKE_ACCEPTED"

ABSENT_EXIT = 3
FAIL_EXIT = 1

INTAKE_SCHEMA_ID = "m207-s02-intake-record/v1"
SCHEMA_VERSION = 1
SUBMISSION_SCHEMA_ID = "m207-s01-coding-submission/v1"
KIT_SCHEMA_ID = "m207-s02-coder-kit/v1"

CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
KIT_PASS1_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json"
KIT_PASS2_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass2.json"
SCHEMAS_REL = "prd/annotation/m207-s02-schemas.json"
S01_SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
STORE_REL = "prd/annotation/m207-s02-submissions"
RECORD_REL = "prd/migration/rust-evidence/m207-s02-intake-record.json"
ANNOTATION_PREFIX = "prd/annotation/"
EVIDENCE_PREFIX = "prd/migration/rust-evidence/"

CASES_SHA256 = "9b0b6bc6bd8eadf9eb86886e45eb756ebade654e96ac3a84132ed9452bdeb9ad"

CASE_COUNT = 40
CODER_PASSES = (1, 2)
PROVENANCE_VALUE = "human-reviewed"
SCHEMA_VERSION_VALUE = 1

M199_SLOTS = (
    "marker_chain",
    "hier_nums",
    "date",
    "doc_no",
    "law_code",
    "anaphora",
    "range",
    "quoted_enum",
)
DECISION_VALUES = ("reference", "not_a_reference")
ABSTENTION_VALUES = ("not-abstained", "ambiguous", "insufficient-context")

# The frozen S01 submission form (``m207-s01-coding-submission/v1``), re-checked
# structurally against ``prd/annotation/m207-s01-schemas.json`` at run time.
HEADER_CLOSED_KEYS = (
    "schema",
    "schema_version",
    "codebook",
    "submission_id",
    "coder_id",
    "coder_pass",
    "provenance",
    "cases",
    "non_claims",
    "lifecycle",
)
CASE_CLOSED_KEYS = ("case_id", "decision", "span", "slots", "abstention")
SPAN_CLOSED_KEYS = ("start", "end")

RECORD_CLOSED_KEYS = (
    "case_universe",
    "cases_covered",
    "diagnostics",
    "lifecycle",
    "non_claims",
    "schema",
    "schema_version",
    "submission_count",
    "submissions",
)
RECORD_SUBMISSION_CLOSED_KEYS = (
    "case_count",
    "coder_id",
    "coder_pass",
    "provenance",
    "sha256",
    "submission_id",
)

# Predicted-answer and rule-seed fields (D471): a human submission may carry
# neither, at any nesting depth, as a key, as an element of a ``*_keys`` list or
# as a substring of a value.
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
    {
        "seed_span",
        "rule_seed_span",
        "rule_seed",
        "ds_span",
        "seed_slots",
    }
)
FORBIDDEN_SUBSTRINGS = (
    "label",
    "expected",
    "answer",
    "prediction",
    "predicted",
    "gold",
    "capture",
    "rule_seed",
    "seed_span",
    "ds_span",
    "lawref_seed",
)
# ``non_claims`` and the ``forbidden_*`` deny-lists enumerate forbidden wording
# by design, so they are exempt (S01/D471).
EXEMPT_KEYS = frozenset({"non_claims", "forbidden_keys", "forbidden_seed_keys"})
GUARDED_FALSE_CLAIM_KEYS = frozenset({"is_gold"})

CLAIM_VALUE_RULES: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("authority", lambda value: value == "none", "AUTHORITY_CLAIM"),
    ("suggestion_status", lambda value: value == "none-provided", "AUTHORITY_CLAIM"),
    ("model_invoked", lambda value: value is False, "MODEL_INVOKED"),
    ("classification", lambda value: value == "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("promotion", lambda value: value == "none", "PROMOTION_CLAIM"),
)

# Closed marker vocabulary: any of these tokens in a submission's file name, ids
# or key names marks it as synthetic, and a synthetic submission may only be
# admitted with ``--allow-test-fixtures`` outside the product store.
FIXTURE_MARKER_TOKENS = frozenset(
    {
        "fixture",
        "fixtures",
        "synthetic",
        "dummy",
        "example",
        "examples",
        "placeholder",
        "mock",
        "fake",
        "toy",
        "test",
        "tests",
        "probe",
        "selftest",
    }
)

# The closed set of names this tool is allowed to speak; ``check`` proves every
# one of them is in the frozen ``$.diagnostics`` table.
LOCAL_DIAGNOSTICS = (
    "ABSTENTION_COLLAPSE",
    "AUTHORITY_CLAIM",
    "CASE_COUNT_OUT_OF_RANGE",
    "CLASSIFICATION_REQUESTED",
    "CODER_PASS_INVALID",
    "DIAGNOSTIC_TABLE_DRIFT",
    "DUPLICATE_CODER_ID",
    "DUPLICATE_JSON_KEY",
    "DUPLICATE_SUBMISSION_ID",
    "FRAGMENT_PIN_DRIFT",
    "FROZEN_SOURCE_DRIFT",
    "GOLD_CLAIM",
    "HUMAN_PILOT_ABSENT",
    "KIT_CROSS_PASS_INVARIANT",
    "LEAK_FORBIDDEN_KEY",
    "MISSING_ARTIFACT",
    "MISSING_LIFECYCLE_MARKER",
    "MISSING_NON_CLAIM",
    "MODEL_INVOKED",
    "NINTH_SLOT",
    "PROMOTION_CLAIM",
    "PROVENANCE_NOT_HUMAN",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "SLOT_SET_DRIFT",
    "SPAN_BEYOND_EOF",
    "SPAN_NOT_ORIGIN",
    "SPAN_NOT_UTF8_BOUNDARY",
    "SUBMISSION_CONFLICT",
    "SUBMISSION_SCHEMA_DRIFT",
    "TEST_FIXTURE_IN_STORE",
    "THRESHOLD_REQUESTED",
    "UNFILLED_SUBMISSION",
    "UNKNOWN_CASE_ID",
    "UNSAFE_PATH",
    "VOCABULARY_DRIFT",
)

Failures = list[tuple[str, str]]

CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
TOKEN_SEPARATOR_RE = re.compile(r"[^A-Za-z0-9]+")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_MISSING = object()


class GateError(Exception):
    """Fatal, named gate failure that stops the run immediately."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


# --------------------------------------------------------------------------- #
# Frozen-source loading, path safety and closed JSON.
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def resolve_artifact(
    root: Path, raw: str, label: str, *, suffix: str | None = None, prefix: str | None = None
) -> Path:
    """Resolve a repository-relative path, fail-closed on escapes."""
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
    if suffix is not None and relative.suffix != suffix:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must have suffix {suffix}")
    if prefix is not None and not relative.as_posix().startswith(prefix):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must live under {prefix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def is_under(path: Path, parent: Path) -> bool:
    try:
        return path.resolve(strict=False).is_relative_to(parent.resolve(strict=False))
    except OSError:  # pragma: no cover - defensive
        return False


def inside_product_tree(root: Path, path: Path) -> bool:
    """True when a path is lexically or physically inside the repo or its .gsd state.

    The repository's ``.gsd`` is a symlink out of the checkout, so a purely
    physical check would miss ``.gsd/<tmp>``; both the lexical and the resolved
    forms are compared, against the checkout and against the symlink target.
    """
    candidates = [path.resolve(strict=False)]
    if not path.is_absolute():
        candidates.append(root / path)
        candidates.append((root / path).resolve(strict=False))
    state = (root / ".gsd").resolve(strict=False)
    return any(is_under(candidate, root) or is_under(candidate, state) for candidate in candidates)


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
    node: Any, pointer: str, failures: Failures, *, key_list: bool = False, exempt: bool = False
) -> None:
    """Reject predicted-answer, gold-claim and rule-seed fields at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            if name not in EXEMPT_KEYS:
                hit = forbidden_key_hit(name, value)
                if hit == "gold-claim":
                    _fail(failures, "GOLD_CLAIM", f"key {name!r} at {pointer} claims gold")
                elif hit:
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"key {name!r} at {pointer} mints a {hit} field",
                    )
            scan_forbidden_keys(
                value,
                f"{pointer}.{name}",
                failures,
                key_list=name.endswith("_keys"),
                exempt=exempt or name in EXEMPT_KEYS,
            )
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
            scan_forbidden_keys(item, f"{pointer}[{index}]", failures, exempt=exempt)
    elif isinstance(node, str) and not exempt:
        for needle in FORBIDDEN_SUBSTRINGS:
            if needle in node:
                _fail(
                    failures,
                    "LEAK_FORBIDDEN_KEY",
                    f"{pointer} carries the forbidden substring {needle!r}",
                )
                return


def scan_claim_values(node: Any, pointer: str, failures: Failures) -> None:
    """Reject authority, model, classification, threshold and promotion claims.

    Scalars only: a list of legal values states the closed set, a scalar states
    the choice.  A submission that carries one of these keys at all already
    drifts from the closed form, but the claim diagnostic is more specific and
    is reported first.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                scan_claim_values(value, f"{pointer}.{key}", failures)
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
            scan_claim_values(item, f"{pointer}[{index}]", failures)


def fixture_marker_hit(node: Any, *extra: str) -> str | None:
    """Return the fixture marker token that marks a candidate as synthetic."""
    for text in extra:
        for token in key_tokens(text):
            if token in FIXTURE_MARKER_TOKENS:
                return token
    return _marker_in_keys(node, "$")


def _marker_in_keys(node: Any, pointer: str) -> str | None:
    if isinstance(node, dict):
        for key, value in node.items():
            for token in key_tokens(str(key)):
                if token in FIXTURE_MARKER_TOKENS:
                    return token
            hit = _marker_in_keys(value, f"{pointer}.{key}")
            if hit:
                return hit
    elif isinstance(node, list):
        for index, item in enumerate(node):
            hit = _marker_in_keys(item, f"{pointer}[{index}]")
            if hit:
                return hit
    return None


# --------------------------------------------------------------------------- #
# The frozen world: case universe, kits, schema binding.
# --------------------------------------------------------------------------- #


@dataclass
class CaseBinding:
    case_id: str
    fragment_id: str
    fragment_path: str
    fragment_sha256: str
    byte_len: int
    offered_start: int
    offered_end: int


@dataclass
class World:
    root: Path
    cases: dict[str, CaseBinding]
    universe: tuple[str, ...]
    kits: dict[int, dict[str, Any]]
    non_claims: tuple[str, ...]
    lifecycle: dict[str, Any]
    codebook_rel: str
    fragment_dir: Path
    schemas: dict[str, Any]
    s01_schemas: dict[str, Any]
    span_offered: int = 0
    fragments_pinned: int = 0
    frag_cache: dict[str, bytes] = field(default_factory=dict)


@dataclass(frozen=True)
class StoreFile:
    name: str
    path: Path
    raw: bytes


def _expect_equal(
    failures: Failures, diagnostic: str, label: str, observed: Any, expected: Any
) -> None:
    if observed != expected:
        _fail(failures, diagnostic, f"{label}={observed!r} != {expected!r}")


def check_schema_binding(
    schemas: Any, s01_schemas: Any, failures: Failures
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Bind the intake contour to the frozen S02/S01 closed schemas."""
    if not isinstance(schemas, dict) or not isinstance(s01_schemas, dict):
        return (), {}
    diagnostics = schemas.get("diagnostics")
    if not isinstance(diagnostics, list):
        _fail(failures, "DIAGNOSTIC_TABLE_DRIFT", "$.diagnostics is not a list")
        diagnostics = []
    for name in LOCAL_DIAGNOSTICS:
        if name not in diagnostics:
            _fail(
                failures,
                "DIAGNOSTIC_TABLE_DRIFT",
                f"intake diagnostic {name!r} is not in the frozen $.diagnostics table",
            )
    store = schemas.get("store_paths") or {}
    _expect_equal(
        failures, "UNSAFE_PATH", "$.store_paths.submissions", store.get("submissions"), STORE_REL
    )
    _expect_equal(
        failures,
        "UNSAFE_PATH",
        "$.store_paths.allowed_prefix",
        store.get("allowed_prefix"),
        ANNOTATION_PREFIX,
    )
    _expect_equal(
        failures,
        "UNSAFE_PATH",
        "$.store_paths.prefix_diagnostic",
        store.get("prefix_diagnostic"),
        "UNSAFE_PATH",
    )
    if store.get("store_prefix_lock") is not True:
        _fail(failures, "UNSAFE_PATH", "$.store_paths.store_prefix_lock must be true (D480)")
    slot_space = (schemas.get("slot_space") or {}).get("closed_keys")
    if list(M199_SLOTS) != (slot_space if isinstance(slot_space, list) else []):
        _fail(
            failures,
            "SLOT_SET_DRIFT",
            f"$.slot_space.closed_keys={slot_space!r} != the frozen eight M199 slots",
        )
    vocab = schemas.get("vocabularies") or {}
    _expect_equal(
        failures,
        "VOCABULARY_DRIFT",
        "$.vocabularies.provenance",
        vocab.get("provenance"),
        [PROVENANCE_VALUE],
    )
    _expect_equal(
        failures,
        "VOCABULARY_DRIFT",
        "$.vocabularies.coder_pass",
        vocab.get("coder_pass"),
        list(CODER_PASSES),
    )
    _expect_equal(
        failures,
        "VOCABULARY_DRIFT",
        "$.vocabularies.decision_values",
        vocab.get("decision_values"),
        list(DECISION_VALUES),
    )
    _expect_equal(
        failures,
        "VOCABULARY_DRIFT",
        "$.vocabularies.abstention_values",
        vocab.get("abstention_values"),
        list(ABSTENTION_VALUES),
    )
    _expect_equal(
        failures,
        "SUBMISSION_SCHEMA_DRIFT",
        "$.submission_schema_id",
        schemas.get("submission_schema_id"),
        SUBMISSION_SCHEMA_ID,
    )
    intake_schema = (schemas.get("schemas") or {}).get("intake_record") or {}
    if intake_schema.get("store_read_only") is not True:
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.schemas.intake_record.store_read_only must be true")
    _expect_equal(
        failures,
        "SCHEMA_KEY_DRIFT",
        "$.schemas.intake_record.closed_keys",
        sorted(intake_schema.get("closed_keys") or []),
        sorted(RECORD_CLOSED_KEYS),
    )
    _expect_equal(
        failures,
        "SCHEMA_KEY_DRIFT",
        "$.schemas.intake_record.submission_closed_keys",
        sorted(intake_schema.get("submission_closed_keys") or []),
        sorted(RECORD_SUBMISSION_CLOSED_KEYS),
    )
    _expect_equal(
        failures,
        "SCHEMA_KEY_DRIFT",
        "$.schemas.intake_record.submission_required_keys",
        sorted(intake_schema.get("submission_required_keys") or []),
        sorted(RECORD_SUBMISSION_CLOSED_KEYS),
    )
    _expect_equal(
        failures,
        "SUBMISSION_SCHEMA_DRIFT",
        "$.schemas.intake_record.submission_schema_id",
        intake_schema.get("submission_schema_id"),
        SUBMISSION_SCHEMA_ID,
    )
    form = (s01_schemas.get("schemas") or {}).get("coding_submission") or {}
    _expect_equal(
        failures,
        "SUBMISSION_SCHEMA_DRIFT",
        "s01 coding_submission.closed_keys",
        sorted(form.get("closed_keys") or []),
        sorted(HEADER_CLOSED_KEYS),
    )
    _expect_equal(
        failures,
        "SCHEMA_KEY_DRIFT",
        "s01 coding_submission.case_closed_keys",
        sorted(form.get("case_closed_keys") or []),
        sorted(CASE_CLOSED_KEYS),
    )
    _expect_equal(
        failures,
        "SCHEMA_KEY_DRIFT",
        "s01 coding_submission.span_closed_keys",
        sorted(form.get("span_closed_keys") or []),
        sorted(SPAN_CLOSED_KEYS),
    )
    _expect_equal(
        failures,
        "SLOT_SET_DRIFT",
        "s01 coding_submission.slot_closed_keys",
        sorted(form.get("slot_closed_keys") or []),
        sorted(M199_SLOTS),
    )
    _expect_equal(
        failures,
        "VOCABULARY_DRIFT",
        "s01 coding_submission.provenance_value",
        form.get("provenance_value"),
        PROVENANCE_VALUE,
    )
    _expect_equal(
        failures,
        "VOCABULARY_DRIFT",
        "s01 coding_submission.coder_pass_values",
        form.get("coder_pass_values"),
        list(CODER_PASSES),
    )
    non_claims = tuple(schemas.get("non_claims") or ())
    lifecycle = schemas.get("lifecycle") or {}
    if not non_claims or not isinstance(lifecycle, dict):
        _fail(failures, "MISSING_NON_CLAIM", "$.non_claims / $.lifecycle must be present")
    return non_claims, dict(lifecycle)


def _kit_cases(kit: Any, label: str, failures: Failures) -> list[dict[str, Any]]:
    if not isinstance(kit, dict):
        _fail(failures, "MISSING_ARTIFACT", f"{label} is not an object")
        return []
    if kit.get("schema") != KIT_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"{label} schema={kit.get('schema')!r} != {KIT_SCHEMA_ID}",
        )
    cases = kit.get("cases")
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"{label} carries {len(cases) if isinstance(cases, list) else 'no'} cases, expected {CASE_COUNT}",
        )
        return []
    return cases


def check_frozen_binding(
    manifest: Any, kits: dict[int, dict[str, Any]], failures: Failures
) -> tuple[dict[str, CaseBinding], tuple[str, ...], int]:
    """Prove the case universe, the kit cross-pass invariant and the fragment pins."""
    if not isinstance(manifest, dict):
        return {}, (), 0
    manifest_cases = manifest.get("cases")
    if not isinstance(manifest_cases, list) or len(manifest_cases) != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case manifest holds {len(manifest_cases) if isinstance(manifest_cases, list) else 'no'} cases",
        )
        return {}, (), 0
    manifest_ids = [str(case.get("case_id")) for case in manifest_cases]
    universe = tuple(sorted(manifest_ids))
    if len(set(universe)) != CASE_COUNT:
        _fail(failures, "UNKNOWN_CASE_ID", "the case manifest repeats a case_id")
    bindings: dict[str, CaseBinding] = {}
    for case in manifest_cases:
        case_id = str(case.get("case_id"))
        bindings[case_id] = CaseBinding(
            case_id=case_id,
            fragment_id=str(case.get("fragment_id")),
            fragment_path="",
            fragment_sha256="",
            byte_len=int(case.get("byte_len") or 0),
            offered_start=int(case.get("start") or 0),
            offered_end=int(case.get("end") or 0),
        )
    pinned = 0
    for coder_pass, kit in sorted(kits.items()):
        label = f"kit-pass-{coder_pass}"
        kit_cases = _kit_cases(kit, label, failures)
        if not kit_cases:
            continue
        if sorted(str(case.get("case_id")) for case in kit_cases) != list(universe):
            _fail(
                failures,
                "UNKNOWN_CASE_ID",
                f"{label} case universe differs from the frozen case manifest",
            )
            continue
        for case in kit_cases:
            case_id = str(case.get("case_id"))
            binding = bindings[case_id]
            byte_len = case.get("byte_len")
            if byte_len != binding.byte_len:
                _fail(
                    failures,
                    "FRAGMENT_PIN_DRIFT",
                    f"{label}/{case_id} byte_len={byte_len!r} != manifest {binding.byte_len}",
                )
            fragment_path = str(case.get("fragment_path") or "")
            fragment_sha256 = str(case.get("fragment_sha256") or "")
            if not SHA256_RE.match(fragment_sha256):
                _fail(
                    failures,
                    "FRAGMENT_PIN_DRIFT",
                    f"{label}/{case_id} fragment_sha256={fragment_sha256!r} is not a digest",
                )
            if case.get("span_offered_for_coding") is not True:
                _fail(
                    failures,
                    "FRAGMENT_PIN_DRIFT",
                    f"{label}/{case_id} does not offer a span for coding",
                )
            if coder_pass == CODER_PASSES[0]:
                binding.fragment_path = fragment_path
                binding.fragment_sha256 = fragment_sha256
                binding.byte_len = int(byte_len or 0)
            elif (
                fragment_path != binding.fragment_path or fragment_sha256 != binding.fragment_sha256
            ):
                _fail(
                    failures,
                    "KIT_CROSS_PASS_INVARIANT",
                    f"{label}/{case_id} fragment binding differs from pass-1",
                )
            else:
                pinned += 1
    for coder_pass in CODER_PASSES:
        kit = kits.get(coder_pass)
        if kit is None:
            continue
        other = kits.get(CODER_PASSES[1] if coder_pass == CODER_PASSES[0] else CODER_PASSES[0])
        if other is None:
            continue
        left = [{k: v for k, v in case.items()} for case in kit.get("cases") or []]
        right = [{k: v for k, v in case.items()} for case in other.get("cases") or []]
        if left != right:
            _fail(
                failures,
                "KIT_CROSS_PASS_INVARIANT",
                f"kit-pass-{coder_pass} case payloads differ from the other pass",
            )
    return bindings, universe, pinned


def load_world(root: Path, paths: PathsLike, failures: Failures) -> World | None:
    """Load and bind every frozen input the intake rests on."""
    try:
        cases_path = resolve_artifact(root, paths.cases, "cases", suffix=".json")
        kit1_path = resolve_artifact(root, paths.kit_pass1, "kit-pass1", suffix=".json")
        kit2_path = resolve_artifact(root, paths.kit_pass2, "kit-pass2", suffix=".json")
        schemas_path = resolve_artifact(
            root, paths.schemas, "schemas", suffix=".json", prefix=ANNOTATION_PREFIX
        )
        s01_path = resolve_artifact(
            root, paths.s01_schemas, "s01-schemas", suffix=".json", prefix=ANNOTATION_PREFIX
        )
        fixture_dir = resolve_artifact(root, paths.fixture_dir, "fixture-dir")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None
    if not cases_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"frozen case manifest not found at {paths.cases}")
        return None
    digest = sha256_file(cases_path)
    if digest != CASES_SHA256:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"case manifest sha256 {digest} != pinned {CASES_SHA256}",
        )
        return None
    manifest = kits = schemas = s01_schemas = None
    try:
        manifest = load_json(cases_path, "case manifest")
        kits = {
            coder_pass: load_json(
                kit1_path if coder_pass == CODER_PASSES[0] else kit2_path, f"kit-pass-{coder_pass}"
            )
            for coder_pass in CODER_PASSES
        }
        schemas = load_json(schemas_path, "S02 schemas")
        s01_schemas = load_json(s01_path, "S01 schemas")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None
    non_claims, lifecycle = check_schema_binding(schemas, s01_schemas, failures)
    bindings, universe, pinned = check_frozen_binding(manifest, kits, failures)
    if not bindings:
        return None
    return World(
        root=root,
        cases=bindings,
        universe=universe,
        kits=kits,
        non_claims=non_claims,
        lifecycle=lifecycle,
        codebook_rel=str(schemas.get("codebook") or CODEBOOK_REL),
        fragment_dir=fixture_dir,
        schemas=schemas,
        s01_schemas=s01_schemas,
        fragments_pinned=pinned,
    )


def fragment_bytes(world: World, binding: CaseBinding) -> bytes | None:
    """Frozen fragment bytes for a case, pinned by the kit's digest."""
    cached = world.frag_cache.get(binding.fragment_id)
    if cached is not None:
        return cached
    if not binding.fragment_path:
        return None
    try:
        path = fragment_path(world, binding)
    except GateError:
        return None
    if path is None or not path.is_file():
        return None
    data = path.read_bytes()
    if sha256_bytes(data) != binding.fragment_sha256 or len(data) != binding.byte_len:
        return None
    world.frag_cache[binding.fragment_id] = data
    return data


def fragment_path(world: World, binding: CaseBinding) -> Path:
    """Resolve the kit's fragment path inside the frozen fixture directory.

    The kit path must be exactly a flat ``.txt`` file declared under
    ``FIXTURE_DIR_REL``; it is then resolved through the configured fixture
    directory, so ``--fixture-dir`` stays meaningful and safety-checked.
    """
    prefix = f"{FIXTURE_DIR_REL}/"
    raw = binding.fragment_path
    if not raw.startswith(prefix) or ".." in raw.split("/"):
        raise GateError(
            "UNSAFE_PATH",
            f"fragment path {raw!r} is not declared under {FIXTURE_DIR_REL}",
        )
    name = raw[len(prefix) :]
    if not name or "/" in name:
        raise GateError("UNSAFE_PATH", f"fragment path {raw!r} is not a flat fixture file")
    return resolve_artifact(world.fragment_dir, name, "fragment", suffix=".txt")


def check_fragment_pins(world: World, failures: Failures) -> int:
    """Prove every case's fragment file exists and matches the frozen pin."""
    pinned = 0
    for case_id in world.universe:
        binding = world.cases[case_id]
        if not binding.fragment_path:
            _fail(failures, "FRAGMENT_PIN_DRIFT", f"{case_id} carries no fragment_path")
            continue
        try:
            path = fragment_path(world, binding)
        except GateError as exc:
            _fail(failures, exc.diagnostic, f"{case_id}: {exc.detail}")
            continue
        if not path.is_file():
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{case_id} fragment {binding.fragment_path} not found",
            )
            continue
        data = path.read_bytes()
        if len(data) != binding.byte_len:
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{case_id} fragment is {len(data)} bytes, kit pins {binding.byte_len}",
            )
            continue
        if sha256_bytes(data) != binding.fragment_sha256:
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{case_id} fragment sha256 differs from the kit pin",
            )
            continue
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            _fail(failures, "FRAGMENT_PIN_DRIFT", f"{case_id} fragment is not UTF-8: {exc}")
            continue
        world.frag_cache[binding.fragment_id] = data
        pinned += 1
    return pinned


# --------------------------------------------------------------------------- #
# Store discovery and policy.
# --------------------------------------------------------------------------- #


def store_policy(root: Path, store_raw: str, *, allow_test_fixtures: bool) -> Path:
    """Resolve the store path, enforcing the frozen D480 prefix lock."""
    if allow_test_fixtures:
        if store_raw.startswith("/"):
            store = Path(store_raw)
        else:
            relative = PurePosixPath(store_raw)
            if ".." in relative.parts or "\\" in store_raw:
                raise GateError(
                    "UNSAFE_PATH", f"--store={store_raw!r} may not escape the repository"
                )
            store = root / relative
        if is_under(store, root / ANNOTATION_PREFIX):
            raise GateError(
                "UNSAFE_PATH",
                "test fixtures may never target the product store prd/annotation/",
            )
        if inside_product_tree(root, store):
            raise GateError(
                "UNSAFE_PATH",
                f"--store={store_raw!r} is inside the product tree: synthetic fixtures live "
                "outside the repository and its state directory",
            )
        return store
    store = resolve_artifact(root, store_raw, "store")
    if not is_under(store, root / ANNOTATION_PREFIX):
        raise GateError(
            "UNSAFE_PATH",
            f"--store={store_raw!r} must live under {ANNOTATION_PREFIX} (D480 prefix lock)",
        )
    return store


def record_path(root: Path, record_raw: str, *, allow_test_fixtures: bool) -> Path:
    """Resolve the derived record path; the harness may never write a store."""
    if record_raw.startswith("/"):
        if not allow_test_fixtures:
            raise GateError("UNSAFE_PATH", f"--record={record_raw!r} must be repository-relative")
        path = Path(record_raw)
    else:
        path = resolve_artifact(
            root,
            record_raw,
            "record",
            suffix=".json",
            prefix=None if allow_test_fixtures else EVIDENCE_PREFIX,
        )
    if is_under(path, root / ANNOTATION_PREFIX):
        raise GateError(
            "UNSAFE_PATH",
            f"--record={record_raw!r} is under the product store prefix: the harness "
            "never writes a submission (D474/D476)",
        )
    if allow_test_fixtures and inside_product_tree(root, path):
        raise GateError(
            "UNSAFE_PATH",
            f"--record={record_raw!r} is inside the product tree: synthetic evidence lives "
            "outside the repository and its state directory",
        )
    return path


def probe_path(root: Path, raw: str) -> Path:
    """Resolve the read-only single-submission probe path.

    The probe only ever reads, so an explicitly named absolute file is accepted
    (that is how a hostile envelope is fed in from a temp directory); every
    *write* path stays locked to its declared prefix.
    """
    if raw.startswith("/"):
        path = Path(raw)
        if "\\" in raw or "\x00" in raw or path.suffix != ".json":
            raise GateError("UNSAFE_PATH", f"--submission={raw!r} must be an absolute .json path")
        return path
    return resolve_artifact(root, raw, "submission", suffix=".json")


def discover_submissions(store: Path, *, label: str = "store") -> list[StoreFile]:
    """Read the human drop box, or refuse: zero codings is not success."""
    if not store.exists():
        raise GateError(
            "HUMAN_PILOT_ABSENT",
            f"{label} {store} does not exist; no human submission exists yet "
            "(the harness never creates one)",
        )
    if not store.is_dir():
        raise GateError("HUMAN_PILOT_ABSENT", f"{label} {store} is not a directory")
    candidates = sorted(
        (path for path in store.iterdir() if path.is_file() and path.suffix == ".json"),
        key=lambda path: path.name,
    )
    if not candidates:
        raise GateError(
            "HUMAN_PILOT_ABSENT",
            f"{label} {store} holds no *.json submission; zero codings is never reported as success",
        )
    return [StoreFile(name=path.name, path=path, raw=path.read_bytes()) for path in candidates]


# --------------------------------------------------------------------------- #
# Submission validation.
# --------------------------------------------------------------------------- #


def check_span(
    label: str, case: dict[str, Any], binding: CaseBinding, world: World, failures: Failures
) -> bool:
    span = case.get("span")
    if not isinstance(span, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.span must be an object")
        return False
    if sorted(span.keys()) != sorted(SPAN_CLOSED_KEYS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.span keys {sorted(span.keys())} != {sorted(SPAN_CLOSED_KEYS)}",
        )
        return False
    start, end = span.get("start"), span.get("end")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
    ):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.span coordinates must be integers")
        return False
    if start < 0 or end <= start:
        _fail(
            failures,
            "SPAN_NOT_ORIGIN",
            f"{label}.span=[{start}, {end}) is not a positive-width span at or after the origin",
        )
        return False
    if end > binding.byte_len or start >= binding.byte_len:
        _fail(
            failures,
            "SPAN_BEYOND_EOF",
            f"{label}.span=[{start}, {end}) is outside the fragment (byte_len={binding.byte_len})",
        )
        return False
    if start < binding.offered_start or end > binding.offered_end:
        _fail(
            failures,
            "SPAN_NOT_ORIGIN",
            f"{label}.span=[{start}, {end}) leaves the offered region "
            f"[{binding.offered_start}, {binding.offered_end})",
        )
        return False
    data = fragment_bytes(world, binding)
    if data is None:
        _fail(
            failures,
            "FRAGMENT_PIN_DRIFT",
            f"{label} cannot be checked: fragment {binding.fragment_id} bytes are not pinned",
        )
        return False
    try:
        data[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(
            failures,
            "SPAN_NOT_UTF8_BOUNDARY",
            f"{label}.span=[{start}, {end}) splits a UTF-8 code point: {exc}",
        )
        return False
    return True


def check_case(label: str, case: Any, world: World, failures: Failures) -> str | None:
    """Validate one coded case; return its case_id when structurally sound."""
    if not isinstance(case, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} is not an object")
        return None
    keys = sorted(case.keys())
    if keys != sorted(CASE_CLOSED_KEYS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label} keys {keys} != {sorted(CASE_CLOSED_KEYS)}",
        )
        return None
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or case_id not in world.cases:
        _fail(
            failures,
            "UNKNOWN_CASE_ID",
            f"{label}.case_id={case_id!r} is not one of the {CASE_COUNT} frozen cases",
        )
        return None
    binding = world.cases[case_id]
    decision = case.get("decision")
    if decision not in DECISION_VALUES:
        if decision in ABSTENTION_VALUES:
            _fail(
                failures,
                "ABSTENTION_COLLAPSE",
                f"{label}.decision={decision!r} reuses the abstention vocabulary",
            )
        else:
            _fail(
                failures,
                "VOCABULARY_DRIFT",
                f"{label}.decision={decision!r} is outside the codebook decision poles",
            )
    abstention = case.get("abstention")
    if abstention not in ABSTENTION_VALUES:
        _fail(
            failures,
            "ABSTENTION_COLLAPSE",
            f"{label}.abstention={abstention!r} is not one of "
            f"{list(ABSTENTION_VALUES)}; abstention is never the reference decision",
        )
    slots = case.get("slots")
    if not isinstance(slots, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.slots must be an object")
    else:
        ninth = sorted(set(slots) - set(M199_SLOTS))
        if ninth:
            _fail(
                failures,
                "NINTH_SLOT",
                f"{label}.slots declares {ninth} outside the closed eight slots "
                "(the binary outcome is not a slot)",
            )
    check_span(f"{label}[{case_id}]", case, binding, world, failures)
    return case_id


def check_coverage(
    label: str, case_ids: list[str], universe: tuple[str, ...], failures: Failures
) -> None:
    counts = Counter(case_ids)
    missing = [case_id for case_id in universe if case_id not in counts]
    repeated = sorted(case_id for case_id, count in counts.items() if count > 1)
    unknown = sorted(case_id for case_id in counts if case_id not in universe)
    if missing or repeated or unknown:
        _fail(
            failures,
            "SUBMISSION_CONFLICT",
            f"{label} does not cover the frozen {CASE_COUNT} cases exactly once: "
            f"missing={missing[:4]} repeated={repeated[:4]} unknown={unknown[:4]}",
        )


def validate_submission(
    envelope: Any,
    *,
    label: str,
    file_name: str,
    world: World,
    allow_test_fixtures: bool,
    failures: Failures,
) -> dict[str, Any] | None:
    """Validate one human submission envelope, fail-closed and read-only."""
    if not isinstance(envelope, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} is not a JSON object")
        return None
    scan_claim_values(envelope, label, failures)
    marker = fixture_marker_hit(
        envelope,
        file_name,
        Path(file_name).stem,
        str(envelope.get("submission_id") or ""),
        str(envelope.get("coder_id") or ""),
    )
    if marker and not allow_test_fixtures:
        _fail(
            failures,
            "TEST_FIXTURE_IN_STORE",
            f"{label} carries the fixture marker {marker!r}; a synthetic submission may "
            "never enter a product store (pass --allow-test-fixtures outside prd/annotation/)",
        )
        return None
    schema = envelope.get("schema")
    if schema == KIT_SCHEMA_ID:
        _fail(
            failures,
            "UNFILLED_SUBMISSION",
            f"{label} carries the coder-kit schema id {KIT_SCHEMA_ID!r}: a kit is not a submission",
        )
        return None
    if schema != SUBMISSION_SCHEMA_ID:
        _fail(
            failures,
            "SUBMISSION_SCHEMA_DRIFT",
            f"{label} schema={schema!r} != {SUBMISSION_SCHEMA_ID}",
        )
        return None
    scan_forbidden_keys(envelope, label, failures)
    keys = sorted(envelope.keys())
    if keys != sorted(HEADER_CLOSED_KEYS):
        missing = [key for key in HEADER_CLOSED_KEYS if key not in envelope]
        extra = [key for key in envelope if key not in HEADER_CLOSED_KEYS]
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label} header drift: missing={missing} extra={extra}",
        )
        return None
    if envelope.get("schema_version") != SCHEMA_VERSION_VALUE:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.schema_version={envelope.get('schema_version')!r} != {SCHEMA_VERSION_VALUE}",
        )
    if envelope.get("codebook") != world.codebook_rel:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"{label}.codebook={envelope.get('codebook')!r} != frozen {world.codebook_rel!r}",
        )
    submission_id = envelope.get("submission_id")
    coder_id = envelope.get("coder_id")
    cases = envelope.get("cases")
    empty: list[str] = []
    if not isinstance(submission_id, str) or not submission_id.strip():
        empty.append("submission_id")
    if not isinstance(coder_id, str) or not coder_id.strip():
        empty.append("coder_id")
    if not isinstance(cases, list) or not cases:
        empty.append("cases")
    if empty:
        _fail(
            failures,
            "UNFILLED_SUBMISSION",
            f"{label} is unfilled: empty {', '.join(empty)} (a kit or its blank template is "
            "not a submission)",
        )
        return None
    provenance = envelope.get("provenance")
    if provenance != PROVENANCE_VALUE:
        _fail(
            failures,
            "PROVENANCE_NOT_HUMAN",
            f"{label}.provenance={provenance!r} != {PROVENANCE_VALUE!r}: a machine pass is "
            "never submitted in this format",
        )
    coder_pass = envelope.get("coder_pass")
    if coder_pass not in CODER_PASSES:
        _fail(
            failures,
            "CODER_PASS_INVALID",
            f"{label}.coder_pass={coder_pass!r} is not one of {list(CODER_PASSES)}",
        )
    non_claims = envelope.get("non_claims")
    if list(non_claims or []) != list(world.non_claims):
        _fail(
            failures,
            "MISSING_NON_CLAIM",
            f"{label}.non_claims differs from the frozen non-claims list "
            f"(observed {len(non_claims) if isinstance(non_claims, list) else 'no'} entries)",
        )
    if envelope.get("lifecycle") != world.lifecycle:
        _fail(
            failures,
            "MISSING_LIFECYCLE_MARKER",
            f"{label}.lifecycle={envelope.get('lifecycle')!r} != the frozen lifecycle markers",
        )
    case_ids: list[str] = []
    for index, case in enumerate(cases):
        case_id = check_case(f"{label}.cases[{index}]", case, world, failures)
        if case_id is not None:
            case_ids.append(case_id)
    if not failure_for(failures, label):
        check_coverage(label, case_ids, world.universe, failures)
    if failure_for(failures, label):
        return None
    return {
        "case_count": len(case_ids),
        "cases": sorted(case_ids),
        "coder_id": coder_id,
        "coder_pass": coder_pass,
        "provenance": provenance,
        "submission_id": submission_id,
    }


def failure_for(failures: Failures, label: str) -> bool:
    """True when at least one recorded failure belongs to this submission."""
    return any(
        detail.startswith(f"{label}.") or detail.startswith(f"{label} ") for _, detail in failures
    )


def evaluate_store(
    files: list[StoreFile],
    world: World,
    *,
    allow_test_fixtures: bool,
    failures: Failures,
) -> list[dict[str, Any]]:
    """Validate every submission and the cross-submission uniqueness rules."""
    summaries: list[dict[str, Any]] = []
    pins: list[dict[str, Any]] = []
    for store_file in files:
        label = store_file.name
        try:
            envelope = load_json_text(store_file.raw.decode("utf-8"), label)
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        summary = validate_submission(
            envelope,
            label=label,
            file_name=store_file.name,
            world=world,
            allow_test_fixtures=allow_test_fixtures,
            failures=failures,
        )
        if summary is None:
            continue
        summary.update({"sha256": sha256_bytes(store_file.raw), "name": store_file.name})
        summaries.append(summary)
        pins.append(summary)
    if failures:
        return []
    seen_coders: dict[str, str] = {}
    seen_submissions: dict[str, str] = {}
    seen_passes: dict[int, str] = {}
    for summary in pins:
        coder_id = summary["coder_id"]
        submission_id = summary["submission_id"]
        if coder_id in seen_coders:
            _fail(
                failures,
                "DUPLICATE_CODER_ID",
                f"coder_id {coder_id!r} appears in both {seen_coders[coder_id]} and {summary['name']}",
            )
        else:
            seen_coders[coder_id] = summary["name"]
        if submission_id in seen_submissions:
            _fail(
                failures,
                "DUPLICATE_SUBMISSION_ID",
                f"submission_id {submission_id!r} is replayed in {summary['name']} "
                f"(already admitted from {seen_submissions[submission_id]})",
            )
        else:
            seen_submissions[submission_id] = summary["name"]
        coder_pass = summary["coder_pass"]
        if coder_pass in seen_passes:
            _fail(
                failures,
                "SUBMISSION_CONFLICT",
                f"coder_pass {coder_pass} arrives twice ({seen_passes[coder_pass]} and "
                f"{summary['name']}): one submission per pass",
            )
        else:
            seen_passes[coder_pass] = summary["name"]
    if failures:
        return []
    return sorted(summaries, key=lambda item: (item["coder_pass"], item["submission_id"]))


# --------------------------------------------------------------------------- #
# Derived evidence record.
# --------------------------------------------------------------------------- #


def build_record(world: World, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    covered = sorted({case_id for summary in summaries for case_id in summary.get("cases", [])})
    return {
        "schema": INTAKE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "case_universe": list(world.universe),
        "cases_covered": covered,
        "submission_count": len(summaries),
        "submissions": [
            {
                "case_count": summary["case_count"],
                "coder_id": summary["coder_id"],
                "coder_pass": summary["coder_pass"],
                "provenance": summary["provenance"],
                "sha256": summary["sha256"],
                "submission_id": summary["submission_id"],
            }
            for summary in summaries
        ],
        "diagnostics": [],
        "non_claims": list(world.non_claims),
        "lifecycle": world.lifecycle,
    }


def render_record(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_record(path: Path, record: dict[str, Any]) -> None:
    """Write the derived record to its target, atomically and unchanged."""
    payload = render_record(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(payload)
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def guarded_write_record(root: Path, path: Path, record: dict[str, Any]) -> None:
    """The only writer in this tool; it can never touch a submission."""
    if is_under(path, root / ANNOTATION_PREFIX):
        raise GateError(
            "UNSAFE_PATH",
            f"refusing to write {path} under {ANNOTATION_PREFIX}: the harness never writes "
            "a submission or an adjudication (D474/D476)",
        )
    write_record(path, record)


# --------------------------------------------------------------------------- #
# Synthetic controls (used by ``check`` and ``selftest``).
# --------------------------------------------------------------------------- #


def synthetic_submission(
    world: World,
    coder_pass: int,
    coder_id: str,
    *,
    decision: str = "not_a_reference",
    abstention: str = "not-abstained",
) -> dict[str, Any]:
    """Build a fully formed synthetic submission in memory (never written)."""
    kit = world.kits[coder_pass]
    template = json.loads(json.dumps(kit.get("submission_template") or {}))
    cases = []
    for index, case_id in enumerate(world.universe):
        binding = world.cases[case_id]
        slots: dict[str, Any] = {}
        if index == 0:
            slots = {name: None for name in M199_SLOTS}
        cases.append(
            {
                "case_id": case_id,
                "decision": decision,
                "span": {"start": binding.offered_start, "end": binding.offered_end},
                "slots": slots,
                "abstention": abstention,
            }
        )
    envelope = dict(template)
    envelope["coder_id"] = coder_id
    envelope["provenance"] = PROVENANCE_VALUE
    envelope["coder_pass"] = coder_pass
    envelope["submission_id"] = f"m207-s02-submission-pass-{coder_pass}"
    envelope["cases"] = cases
    return envelope


def synthetic_files(
    world: World,
    *,
    prefix: str = "submission",
    coder_ids: tuple[str, str] = ("coder-1", "coder-2"),
) -> list[StoreFile]:
    files = []
    for coder_pass, coder_id in zip(CODER_PASSES, coder_ids, strict=True):
        envelope = synthetic_submission(world, coder_pass, coder_id)
        name = f"{prefix}-pass-{coder_pass}.json"
        files.append(
            StoreFile(
                name=name,
                path=Path("memory") / name,
                raw=(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            )
        )
    return files


def mutate(
    envelope: dict[str, Any], mutate_case: Callable[[dict[str, Any]], None]
) -> dict[str, Any]:
    clone = json.loads(json.dumps(envelope))
    mutate_case(clone)
    return clone


def _as_file(envelope: dict[str, Any], name: str) -> StoreFile:
    return StoreFile(
        name=name,
        path=Path("memory") / name,
        raw=(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def _first_leaf_name(raw: bytes) -> int | None:
    """Index of the first byte that starts a multi-byte UTF-8 sequence."""
    for index, byte in enumerate(raw):
        if byte >= 0xC0:
            return index
    return None


# --------------------------------------------------------------------------- #
# Modes.
# --------------------------------------------------------------------------- #


def report(failures: Failures, summary: str) -> int:
    if failures:
        for diagnostic, detail in failures:
            print(f"FAIL {diagnostic}: {detail}", file=sys.stderr)
        return FAIL_EXIT
    if summary:
        print(summary)
    return 0


def run_check(root: Path, paths: PathsLike, *, allow_test_fixtures: bool) -> int:
    failures: Failures = []
    world = load_world(root, paths, failures)
    if world is None or failures:
        return report(failures, "")
    pinned = check_fragment_pins(world, failures)
    if failures:
        return report(failures, "")
    cross_pass = "identical"
    prefix_lock = "product-locked"

    # Positive control: a synthetic pair must validate clean in memory.
    synth_failures: Failures = []
    summaries = evaluate_store(
        synthetic_files(world),
        world,
        allow_test_fixtures=allow_test_fixtures,
        failures=synth_failures,
    )
    if synth_failures:
        return report(synth_failures, "")
    if len(summaries) != len(CODER_PASSES):
        print(
            "FAIL SCHEMA_KEY_DRIFT: the synthetic control did not produce two admitted submissions",
            file=sys.stderr,
        )
        return FAIL_EXIT

    # Negative control: a fixture marker may not reach a product store.
    refused_failures: Failures = []
    fixture_env = synthetic_submission(world, CODER_PASSES[0], "test-coder-1")
    evaluate_store(
        [_as_file(fixture_env, "fixture-submission-pass-1.json")],
        world,
        allow_test_fixtures=False,
        failures=refused_failures,
    )
    if "TEST_FIXTURE_IN_STORE" not in {diagnostic for diagnostic, _ in refused_failures}:
        print(
            "FAIL TEST_FIXTURE_IN_STORE: a fixture-marked submission was not refused in a "
            f"product store (saw {sorted({d for d, _ in refused_failures}) or 'nothing'})",
            file=sys.stderr,
        )
        return FAIL_EXIT

    # The product store is unreachable with --allow-test-fixtures, and the
    # record writer refuses every annotation-prefix target.
    try:
        store_policy(root, STORE_REL, allow_test_fixtures=True)
    except GateError as exc:
        if exc.diagnostic != "UNSAFE_PATH":
            return report([(exc.diagnostic, exc.detail)], "")
    else:
        print(
            "FAIL UNSAFE_PATH: --allow-test-fixtures did not lock out the product store",
            file=sys.stderr,
        )
        return FAIL_EXIT
    annotation_target = root / ANNOTATION_PREFIX / "m207-s02-intake-probe.json"
    try:
        guarded_write_record(root, annotation_target, build_record(world, summaries))
    except GateError as exc:
        if exc.diagnostic != "UNSAFE_PATH":
            return report([(exc.diagnostic, exc.detail)], "")
    else:
        print(
            "FAIL UNSAFE_PATH: the record writer accepted a product-store target",
            file=sys.stderr,
        )
        return FAIL_EXIT
    if annotation_target.exists():
        print(
            "FAIL UNSAFE_PATH: the record writer created a file under prd/annotation/",
            file=sys.stderr,
        )
        return FAIL_EXIT

    # Absent human pilot: empty and missing stores must refuse, not succeed.
    absent_probe = Path(tempfile.mkdtemp(prefix="m207-s02-intake-"))
    try:
        empty_store = absent_probe / "empty-store"
        empty_store.mkdir()
        for store in (absent_probe / "missing-store", empty_store):
            try:
                discover_submissions(store)
            except GateError as exc:
                if exc.diagnostic != "HUMAN_PILOT_ABSENT":
                    return report([(exc.diagnostic, exc.detail)], "")
            else:
                print(
                    f"FAIL HUMAN_PILOT_ABSENT: {store} was accepted as a human store",
                    file=sys.stderr,
                )
                return FAIL_EXIT
    finally:
        if absent_probe.exists():
            for child in sorted(absent_probe.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            absent_probe.rmdir()

    print(
        f"{MARKER} cases={len(world.universe)} kits={len(world.kits)} cross_pass={cross_pass} "
        f"fragments_pinned={pinned} diagnostics={len(LOCAL_DIAGNOSTICS)} "
        f"synthetic_ok=1 synthetic_refused=1 store={prefix_lock}"
    )
    return 0


def run_intake(
    root: Path,
    paths: PathsLike,
    *,
    store_raw: str,
    record_raw: str,
    allow_test_fixtures: bool,
    submission_raw: str | None,
) -> int:
    failures: Failures = []
    try:
        store = store_policy(root, store_raw, allow_test_fixtures=allow_test_fixtures)
        record = record_path(root, record_raw, allow_test_fixtures=allow_test_fixtures)
        probe = probe_path(root, submission_raw) if submission_raw else None
    except GateError as exc:
        return report([(exc.diagnostic, exc.detail)], "")
    world = load_world(root, paths, failures)
    if world is None or failures:
        return report(failures, "")
    check_fragment_pins(world, failures)
    if failures:
        return report(failures, "")
    if probe is not None:
        envelope_failures: Failures = []
        envelope = None
        try:
            envelope = load_json(probe, "submission")
        except GateError as exc:
            envelope_failures.append((exc.diagnostic, exc.detail))
        if envelope is not None:
            validate_submission(
                envelope,
                label=probe.name,
                file_name=probe.name,
                world=world,
                allow_test_fixtures=allow_test_fixtures,
                failures=envelope_failures,
            )
        if envelope_failures:
            return report(envelope_failures, "")
        print(f"{ACCEPT_MARKER} submission={probe.name} form=ok store_written=0")
        return 0
    try:
        files = discover_submissions(store)
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return ABSENT_EXIT if exc.diagnostic == "HUMAN_PILOT_ABSENT" else FAIL_EXIT
    summaries = evaluate_store(
        files, world, allow_test_fixtures=allow_test_fixtures, failures=failures
    )
    if failures or not summaries:
        return report(failures or [("HUMAN_PILOT_ABSENT", "no submission was admitted")], "")
    record_doc = build_record(world, summaries)
    try:
        guarded_write_record(root, record, record_doc)
    except GateError as exc:
        return report([(exc.diagnostic, exc.detail)], "")
    print(
        f"{ACCEPT_MARKER} submissions={len(summaries)} cases_covered={len(record_doc['cases_covered'])} "
        f"store={store_raw} record={record_raw}"
    )
    return 0


def run_selftest(root: Path, paths: PathsLike, tmp_raw: str | None) -> int:
    """The hostile suite: every refusal path plus the positive control."""
    failures: Failures = []
    world = load_world(root, paths, failures)
    if world is None or failures:
        return report(failures, "")
    check_fragment_pins(world, failures)
    if failures:
        return report(failures, "")
    if tmp_raw:
        tmp_root = Path(tmp_raw)
    else:
        tmp_root = Path(tempfile.mkdtemp(prefix="m207-s02-intake-selftest-"))
    if inside_product_tree(root, tmp_root):
        print(
            f"FAIL UNSAFE_PATH: selftest fixtures may not live inside the repository ({tmp_root})",
            file=sys.stderr,
        )
        return FAIL_EXIT
    tmp_root.mkdir(parents=True, exist_ok=True)

    def green(tmp: Path) -> str | None:
        """Positive control: a well-formed pair is admitted and pinned."""
        store = _fresh_store(tmp, "green")
        good = synthetic_files(world)
        _write(store, good)
        probe_failures: Failures = []
        summaries = evaluate_store(
            discover_submissions(store),
            world,
            allow_test_fixtures=True,
            failures=probe_failures,
        )
        if probe_failures:
            return (
                f"green: the synthetic pair was refused ({sorted({d for d, _ in probe_failures})})"
            )
        if len(summaries) != 2:
            return f"green: expected 2 admitted submissions, got {len(summaries)}"
        record = build_record(world, summaries)
        if len(record["submissions"]) != 2 or record["submission_count"] != 2:
            return "green: the record lost a submission"
        if record["diagnostics"]:
            return "green: the record carries diagnostics"
        for summary, store_file in zip(summaries, good, strict=True):
            if summary["sha256"] != sha256_bytes(store_file.raw):
                return f"green: sha256 pin mismatch for {store_file.name}"
        record_path_ = tmp / "evidence" / "m207-s02-intake-record.json"
        guarded_write_record(root, record_path_, record)
        if not record_path_.is_file():
            return "green: the record was not written"
        if json.loads(record_path_.read_text(encoding="utf-8")) != record:
            return "green: the written record differs from the built record"
        return None

    def hostile(
        label: str,
        diagnostic: str,
        build: Callable[[Path], None],
        *,
        allow_test_fixtures: bool = True,
    ) -> str | None:
        store = _fresh_store(tmp_root, label)
        build(store)
        probe_failures: Failures = []
        try:
            files = discover_submissions(store)
        except GateError as exc:
            probe_failures.append((exc.diagnostic, exc.detail))
            files = []
        summaries = (
            evaluate_store(
                files,
                world,
                allow_test_fixtures=allow_test_fixtures,
                failures=probe_failures,
            )
            if files
            else []
        )
        seen = {name for name, _ in probe_failures}
        if diagnostic not in seen:
            details = "; ".join(detail for _, detail in probe_failures)
            return f"{label}: expected {diagnostic}, saw {sorted(seen) or 'nothing'} ({details})"
        if summaries:
            return f"{label}: a submission was admitted despite {diagnostic}"
        return None

    def write_good(store: Path, *, prefix: str = "submission", **kwargs: Any) -> None:
        _write(store, synthetic_files(world, prefix=prefix, **kwargs))

    def one_file(store: Path, envelope: dict[str, Any], name: str) -> None:
        _write(store, [_as_file(envelope, name)])

    problems: list[str] = []
    checks: list[tuple[str, Callable[[], str | None]]] = []

    checks.append(("green", lambda: green(tmp_root)))
    checks.append(
        (
            "absent-missing-store",
            lambda: _expect(
                lambda: discover_submissions(tmp_root / "does-not-exist"), "HUMAN_PILOT_ABSENT"
            ),
        )
    )
    checks.append(
        (
            "absent-empty-store",
            lambda: _expect(
                lambda: discover_submissions(_fresh_store(tmp_root, "absent-empty")),
                "HUMAN_PILOT_ABSENT",
            ),
        )
    )

    def non_json_dir(store: Path) -> None:
        (store / "notes.md").write_text("no submission here\n", encoding="utf-8")

    checks.append(
        (
            "absent-no-json",
            lambda: _expect_store(tmp_root, "absent-no-json", non_json_dir, "HUMAN_PILOT_ABSENT"),
        )
    )

    def malformed(store: Path) -> None:
        (store / "submission-pass-1.json").write_text("{not json", encoding="utf-8")

    checks.append(
        (
            "malformed-json",
            lambda: hostile("malformed-json", "SCHEMA_PARSE_ERROR", malformed),
        )
    )

    def duplicate_keys(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        text = json.dumps(envelope, ensure_ascii=False)
        text = text.replace(
            '"coder_id": "coder-1"', '"coder_id": "coder-1", "coder_id": "coder-2"', 1
        )
        (store / "submission-pass-1.json").write_text(text, encoding="utf-8")

    checks.append(
        (
            "duplicate-json-key",
            lambda: hostile("duplicate-json-key", "DUPLICATE_JSON_KEY", duplicate_keys),
        )
    )

    def not_an_object(store: Path) -> None:
        (store / "submission-pass-1.json").write_text("[1, 2, 3]", encoding="utf-8")

    checks.append(
        ("not-an-object", lambda: hostile("not-an-object", "SCHEMA_KEY_DRIFT", not_an_object))
    )

    def kit_as_submission(store: Path) -> None:
        one_file(store, dict(world.kits[1]), "submission-pass-1.json")

    checks.append(
        (
            "kit-as-submission",
            lambda: hostile("kit-as-submission", "UNFILLED_SUBMISSION", kit_as_submission),
        )
    )

    def unfilled_template(store: Path) -> None:
        one_file(
            store, dict(world.kits[1].get("submission_template") or {}), "submission-pass-1.json"
        )

    checks.append(
        (
            "unfilled-template",
            lambda: hostile("unfilled-template", "UNFILLED_SUBMISSION", unfilled_template),
        )
    )

    def unfilled_template_exact() -> str | None:
        """The shipped template is diagnosed as unfilled and nothing else."""
        store = _fresh_store(tmp_root, "unfilled-exact")
        one_file(
            store,
            dict(world.kits[CODER_PASSES[0]].get("submission_template") or {}),
            "submission-pass-1.json",
        )
        probe_failures: Failures = []
        evaluate_store(
            discover_submissions(store),
            world,
            allow_test_fixtures=True,
            failures=probe_failures,
        )
        seen = sorted({diagnostic for diagnostic, _ in probe_failures})
        if seen != ["UNFILLED_SUBMISSION"]:
            return f"unfilled-template-exact: saw {seen}"
        return None

    checks.append(("unfilled-template-exact", unfilled_template_exact))

    def foreign_form(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["schema"] = "m207-s02-coding-submission/v1"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "foreign-form",
            lambda: hostile("foreign-form", "SUBMISSION_SCHEMA_DRIFT", foreign_form),
        )
    )

    def header_drift(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["note"] = "extra"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        ("header-drift", lambda: hostile("header-drift", "SCHEMA_KEY_DRIFT", header_drift))
    )

    def non_human(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["provenance"] = "rule-seed"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "provenance-not-human",
            lambda: hostile("provenance-not-human", "PROVENANCE_NOT_HUMAN", non_human),
        )
    )

    def bad_pass(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["coder_pass"] = 3
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "coder-pass-invalid",
            lambda: hostile("coder-pass-invalid", "CODER_PASS_INVALID", bad_pass),
        )
    )

    def duplicate_coder(store: Path) -> None:
        _write(store, synthetic_files(world, coder_ids=("coder-1", "coder-1")))

    checks.append(
        (
            "duplicate-coder-id",
            lambda: hostile("duplicate-coder-id", "DUPLICATE_CODER_ID", duplicate_coder),
        )
    )

    def replayed_submission(store: Path) -> None:
        first = synthetic_files(world)[0]
        second = StoreFile(
            name="submission-replay.json", path=first.path.with_name("replay.json"), raw=first.raw
        )
        _write(store, [first, second])

    checks.append(
        (
            "replayed-submission",
            lambda: hostile("replayed-submission", "DUPLICATE_SUBMISSION_ID", replayed_submission),
        )
    )

    def duplicate_pass(store: Path) -> None:
        first = synthetic_files(world)[0]
        second = synthetic_files(world, prefix="second", coder_ids=("coder-9", "coder-9"))[0]
        _write(store, [first, second])

    checks.append(
        (
            "duplicate-pass",
            lambda: hostile("duplicate-pass", "SUBMISSION_CONFLICT", duplicate_pass),
        )
    )

    def unknown_case(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][3]["case_id"] = "m207-s01-case-999"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        ("unknown-case-id", lambda: hostile("unknown-case-id", "UNKNOWN_CASE_ID", unknown_case))
    )

    def missing_case(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"].pop()
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "submission-conflict-missing",
            lambda: hostile("submission-conflict-missing", "SUBMISSION_CONFLICT", missing_case),
        )
    )

    def repeated_case(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][1] = json.loads(json.dumps(envelope["cases"][0]))
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "submission-conflict-repeat",
            lambda: hostile("submission-conflict-repeat", "SUBMISSION_CONFLICT", repeated_case),
        )
    )

    def ninth_slot(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["slots"]["scope"] = "scope_local"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(("ninth-slot", lambda: hostile("ninth-slot", "NINTH_SLOT", ninth_slot)))

    def case_key_drift(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["comment"] = "extra"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        ("case-key-drift", lambda: hostile("case-key-drift", "SCHEMA_KEY_DRIFT", case_key_drift))
    )

    def abstention_collapse(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["abstention"] = "not_a_reference"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "abstention-collapse",
            lambda: hostile("abstention-collapse", "ABSTENTION_COLLAPSE", abstention_collapse),
        )
    )

    def decision_as_abstention(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["decision"] = "ambiguous"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "decision-abstention-collapse",
            lambda: hostile(
                "decision-abstention-collapse", "ABSTENTION_COLLAPSE", decision_as_abstention
            ),
        )
    )

    def beyond_eof(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        binding = world.cases[envelope["cases"][0]["case_id"]]
        envelope["cases"][0]["span"]["end"] = binding.byte_len + 1
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        ("span-beyond-eof", lambda: hostile("span-beyond-eof", "SPAN_BEYOND_EOF", beyond_eof))
    )

    def zero_width(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["span"]["end"] = 0
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        ("span-not-origin", lambda: hostile("span-not-origin", "SPAN_NOT_ORIGIN", zero_width))
    )

    def negative_start(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["span"]["start"] = -1
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "span-not-origin-negative",
            lambda: hostile("span-not-origin-negative", "SPAN_NOT_ORIGIN", negative_start),
        )
    )

    boundary_case = None
    for case_id in world.universe:
        binding = world.cases[case_id]
        data = fragment_bytes(world, binding)
        if data is None:
            continue
        index = _first_leaf_name(data)
        if index is not None and index + 1 < binding.byte_len:
            boundary_case = (case_id, index)
            break
    if boundary_case is None:
        problems.append("no multi-byte fragment was found for the UTF-8 boundary case")
    else:
        boundary_id, boundary_index = boundary_case

        def split_codepoint(store: Path) -> None:
            envelope = synthetic_submission(world, 1, "coder-1")
            for case in envelope["cases"]:
                if case["case_id"] == boundary_id:
                    case["span"] = {
                        "start": boundary_index + 1,
                        "end": world.cases[boundary_id].byte_len,
                    }
                    break
            one_file(store, envelope, "submission-pass-1.json")

        checks.append(
            (
                "span-not-utf8-boundary",
                lambda: hostile(
                    "span-not-utf8-boundary", "SPAN_NOT_UTF8_BOUNDARY", split_codepoint
                ),
            )
        )

    def authority_claim(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["authority"] = "authoritative"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        ("authority-claim", lambda: hostile("authority-claim", "AUTHORITY_CLAIM", authority_claim))
    )

    def model_invoked(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["model_invoked"] = True
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        ("model-invoked", lambda: hostile("model-invoked", "MODEL_INVOKED", model_invoked))
    )

    def classification_requested(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["classification"] = "gold"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "classification-requested",
            lambda: hostile(
                "classification-requested", "CLASSIFICATION_REQUESTED", classification_requested
            ),
        )
    )

    def gold_claim(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["is_gold"] = True
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(("gold-claim", lambda: hostile("gold-claim", "GOLD_CLAIM", gold_claim)))

    def promotion_claim(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["promotion"] = "authorized"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        ("promotion-claim", lambda: hostile("promotion-claim", "PROMOTION_CLAIM", promotion_claim))
    )

    def threshold_requested(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["threshold"] = 0.8
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "threshold-requested",
            lambda: hostile("threshold-requested", "THRESHOLD_REQUESTED", threshold_requested),
        )
    )

    def label_key(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["label"] = "reference"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "leak-forbidden-key",
            lambda: hostile("leak-forbidden-key", "LEAK_FORBIDDEN_KEY", label_key),
        )
    )

    def seed_span_key(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["cases"][0]["rule_seed_span"] = {"start": 0, "end": 1}
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "leak-rule-seed-key",
            lambda: hostile("leak-rule-seed-key", "LEAK_FORBIDDEN_KEY", seed_span_key),
        )
    )

    def doomed_non_claims(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["non_claims"] = ["not gold: trimmed"]
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "missing-non-claim",
            lambda: hostile("missing-non-claim", "MISSING_NON_CLAIM", doomed_non_claims),
        )
    )

    def drifted_lifecycle(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["lifecycle"]["human_adoption"] = "adopted"
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "missing-lifecycle-marker",
            lambda: hostile(
                "missing-lifecycle-marker", "MISSING_LIFECYCLE_MARKER", drifted_lifecycle
            ),
        )
    )

    def blank_coder(store: Path) -> None:
        envelope = synthetic_submission(world, 1, "coder-1")
        envelope["coder_id"] = "   "
        one_file(store, envelope, "submission-pass-1.json")

    checks.append(
        (
            "unfilled-coder-id",
            lambda: hostile("unfilled-coder-id", "UNFILLED_SUBMISSION", blank_coder),
        )
    )

    def fixture_file_name(store: Path) -> None:
        write_good(store, prefix="fixture-submission")

    checks.append(
        (
            "fixture-in-product-store",
            lambda: hostile(
                "fixture-in-product-store",
                "TEST_FIXTURE_IN_STORE",
                fixture_file_name,
                allow_test_fixtures=False,
            ),
        )
    )

    def fixture_coder_id(store: Path) -> None:
        write_good(store, coder_ids=("test-coder-1", "coder-2"))

    checks.append(
        (
            "fixture-coder-id",
            lambda: hostile(
                "fixture-coder-id",
                "TEST_FIXTURE_IN_STORE",
                fixture_coder_id,
                allow_test_fixtures=False,
            ),
        )
    )

    def store_untouched() -> str | None:
        """The harness never creates, edits or deletes a submission."""
        store = _fresh_store(tmp_root, "untouched")
        write_good(store)
        probe_failures: Failures = []
        hostile_env = synthetic_submission(world, CODER_PASSES[0], "coder-1")
        hostile_env["provenance"] = "rule-seed"
        _write(store, [_as_file(hostile_env, "submission-pass-1.json")])
        before = {path.name: path.read_bytes() for path in sorted(store.iterdir())}
        evaluate_store(
            discover_submissions(store),
            world,
            allow_test_fixtures=True,
            failures=probe_failures,
        )
        after = {path.name: path.read_bytes() for path in sorted(store.iterdir())}
        if not probe_failures:
            return "store-untouched: the corrupted store was admitted"
        if before != after:
            return "store-untouched: the intake changed the store while it ran"
        return None

    checks.append(("store-untouched", store_untouched))

    def annotation_write_refused() -> str | None:
        target = root / ANNOTATION_PREFIX / "m207-s02-intake-selftest-probe.json"
        try:
            guarded_write_record(root, target, build_record(world, []))
        except GateError as exc:
            if exc.diagnostic != "UNSAFE_PATH":
                return f"annotation-write-refused: expected UNSAFE_PATH, got {exc.diagnostic}"
        else:
            return "annotation-write-refused: the record writer accepted a product-store target"
        if target.exists():
            return "annotation-write-refused: a file appeared under prd/annotation/"
        return None

    checks.append(("annotation-write-refused", annotation_write_refused))

    def prefix_locked() -> str | None:
        try:
            store_policy(root, "tmp/m207-s02-store", allow_test_fixtures=False)
        except GateError as exc:
            if exc.diagnostic != "UNSAFE_PATH":
                return f"prefix-locked: expected UNSAFE_PATH, got {exc.diagnostic}"
        else:
            return "prefix-locked: a store outside prd/annotation/ was accepted"
        try:
            store_policy(root, STORE_REL, allow_test_fixtures=True)
        except GateError as exc:
            if exc.diagnostic != "UNSAFE_PATH":
                return f"prefix-locked: expected UNSAFE_PATH, got {exc.diagnostic}"
        else:
            return "prefix-locked: --allow-test-fixtures unlocked the product store"
        if inside_product_tree(root, Path(tempfile.gettempdir()) / "m207-s02-probe"):
            return "prefix-locked: a system temp path was treated as a product-tree path"
        if not inside_product_tree(root, root / ".gsd" / "probe"):
            return "prefix-locked: the .gsd state directory is not treated as a product path"
        if not inside_product_tree(root, Path("tmp/probe")):
            return "prefix-locked: a lexical repository path is not treated as a product path"
        return None

    checks.append(("prefix-locked", prefix_locked))

    def run_intake_probe(store: Path, record: Path) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_intake(
                root,
                paths,
                store_raw=str(store),
                record_raw=str(record),
                allow_test_fixtures=True,
                submission_raw=None,
            )
        return code, err.getvalue()

    def no_artifact_on_refusal() -> str | None:
        """A refused store writes no record and is left byte-for-byte alone."""
        store = _fresh_store(tmp_root, "no-artifact")
        envelope = synthetic_submission(world, CODER_PASSES[0], "coder-1")
        envelope["provenance"] = "rule-seed"
        _write(store, [_as_file(envelope, "submission-pass-1.json")])
        before = {path.name: path.read_bytes() for path in sorted(store.iterdir())}
        record = tmp_root / "no-artifact-record.json"
        code, err = run_intake_probe(store, record)
        if code == 0:
            return "no-artifact-on-refusal: the red store was accepted"
        if "PROVENANCE_NOT_HUMAN" not in err:
            return f"no-artifact-on-refusal: wrong diagnostic ({err.strip()[:160]})"
        if record.exists():
            return "no-artifact-on-refusal: a record was written for a refused store"
        after = {path.name: path.read_bytes() for path in sorted(store.iterdir())}
        if before != after:
            return "no-artifact-on-refusal: the refusal changed the store"
        return None

    checks.append(("no-artifact-on-refusal", no_artifact_on_refusal))

    def absent_store_exit_code() -> str | None:
        """An absent human pilot exits with the dedicated code and writes nothing."""
        record = tmp_root / "absent-record.json"
        code, err = run_intake_probe(tmp_root / "store-does-not-exist", record)
        if code != ABSENT_EXIT:
            return f"absent-store-exit-code: expected exit {ABSENT_EXIT}, got {code}"
        if "HUMAN_PILOT_ABSENT" not in err:
            return f"absent-store-exit-code: wrong diagnostic ({err.strip()[:160]})"
        if record.exists():
            return "absent-store-exit-code: an artifact was written for an absent pilot"
        return None

    checks.append(("absent-store-exit-code", absent_store_exit_code))

    for label, probe in checks:
        problem = probe()
        if problem:
            problems.append(problem)

    for problem in problems:
        print(f"FAIL SELFTEST: {problem}", file=sys.stderr)
    if problems:
        return FAIL_EXIT
    print(
        f"{SELFTEST_MARKER} checks={len(checks)} synthetic_ok=1 hostile_refusals={len(checks) - 1}"
    )
    return 0


def _fresh_store(tmp_root: Path, label: str) -> Path:
    store = tmp_root / f"store-{label}"
    store.mkdir(parents=True, exist_ok=True)
    for stale in store.iterdir():
        stale.unlink()
    return store


def _write(store: Path, files: list[StoreFile]) -> None:
    for store_file in files:
        (store / store_file.name).write_bytes(store_file.raw)


def _expect(call: Callable[[], Any], diagnostic: str) -> str | None:
    try:
        call()
    except GateError as exc:
        if exc.diagnostic != diagnostic:
            return f"expected {diagnostic}, got {exc.diagnostic}"
        return None
    return f"expected {diagnostic}, the call succeeded"


def _expect_store(
    tmp_root: Path, label: str, build: Callable[[Path], None], diagnostic: str
) -> str | None:
    store = _fresh_store(tmp_root, label)
    build(store)
    return _expect(lambda: discover_submissions(store), diagnostic)


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PathsLike:
    cases: str
    kit_pass1: str
    kit_pass2: str
    schemas: str
    s01_schemas: str
    fixture_dir: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "run", "selftest"],
        help="'check' self-checks the contour read-only; 'run' admits the human store; "
        "'selftest' runs the hostile suite outside the repository",
    )
    parser.add_argument("tmpdir", nargs="?", default=None, help="selftest tmp root (optional)")
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--store", default=STORE_REL, help="human submission drop box (D480)")
    parser.add_argument("--record", default=RECORD_REL, help="derived evidence record path")
    parser.add_argument(
        "--submission",
        default=None,
        help="probe one candidate submission envelope against the frozen form (read-only)",
    )
    parser.add_argument(
        "--allow-test-fixtures",
        action="store_true",
        help="admit synthetic fixtures outside prd/annotation/ (never inside it)",
    )
    parser.add_argument("--cases", default=CASES_REL, help="frozen S01 pilot case manifest")
    parser.add_argument("--kit-pass1", default=KIT_PASS1_REL, help="frozen pass-1 coder kit")
    parser.add_argument("--kit-pass2", default=KIT_PASS2_REL, help="frozen pass-2 coder kit")
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="frozen S02 closed schemas")
    parser.add_argument("--s01-schemas", default=S01_SCHEMAS_REL, help="frozen S01 closed schemas")
    parser.add_argument(
        "--fixture-dir", default=FIXTURE_DIR_REL, help="frozen fragment fixture dir"
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"FAIL MISSING_ARTIFACT: root {root} is not a directory", file=sys.stderr)
        return FAIL_EXIT
    paths = PathsLike(
        cases=args.cases,
        kit_pass1=args.kit_pass1,
        kit_pass2=args.kit_pass2,
        schemas=args.schemas,
        s01_schemas=args.s01_schemas,
        fixture_dir=args.fixture_dir,
    )
    if args.mode == "selftest":
        if not args.allow_test_fixtures:
            print(
                "FAIL UNSAFE_PATH: selftest requires --allow-test-fixtures; synthetic fixtures "
                "may never touch a product path",
                file=sys.stderr,
            )
            return FAIL_EXIT
        tmp_raw = args.tmpdir
        if tmp_raw is None:
            tmp_raw = tempfile.mkdtemp(prefix="m207-s02-intake-selftest-")
        return run_selftest(root, paths, tmp_raw)
    if args.mode == "run":
        return run_intake(
            root,
            paths,
            store_raw=args.store,
            record_raw=args.record,
            allow_test_fixtures=args.allow_test_fixtures,
            submission_raw=args.submission,
        )
    return run_check(root, paths, allow_test_fixtures=args.allow_test_fixtures)


if __name__ == "__main__":
    raise SystemExit(main())
