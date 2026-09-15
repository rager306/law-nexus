#!/usr/bin/env python3
"""Frozen-codebook and closed-schema gate for the M207 S01 annotation pilot (T01).

This is an offline, fail-closed evidence gate.  It binds three artifacts:

* the frozen M199 annotation protocol (sha256-pinned) whose section 5 fixes the
  closed slot space of the Layer-2 sample;
* ``prd/annotation/m207-s01-codebook.md`` -- the coder-facing instruction sheet
  carrying a machine-readable contract;
* ``prd/annotation/m207-s01-schemas.json`` -- the three closed pilot schemas
  (case manifest, coding submission, prompt packet) with hand-rolled closed key
  sets.

The gate proves, against the frozen sources rather than against prose:

* the declared slot space is exactly the M199 section-5 set plus the
  ``not_a_reference`` binary outcome -- no ninth slot, no ``schema_version`` bump;
* no closed key set, at any nesting depth, mints a predicted-answer key
  (``label``/``expected``/``answer``/``prediction``/``gold``/``capture``) or a
  rule-seed span field;
* abstention stays a coder outcome, disjoint from the reference decision;
* the prompt-packet contract fixes ``AnnotationSuggestion`` with
  ``authority: none`` and ``suggestion_status: none-provided``, and never invokes
  a model in this slice;
* the codebook keeps its required sections, non-claims and lifecycle markers.

No annotation is created, inferred or repaired here: this gate only reads the
frozen artifacts and rejects drift.  Success prints exactly the marker
``M207_S01_SCHEMAS_OK``.  Every failure is a non-zero exit with a named
diagnostic on stderr (``LEAK_FORBIDDEN_KEY``, ``NINTH_SLOT``, ``SLOT_SET_DRIFT``,
``MISSING_ARTIFACT``, ``FROZEN_SOURCE_DRIFT``, ``UNSAFE_PATH``, ...).
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

MARKER = "M207_S01_SCHEMAS_OK"

PILOT_SCHEMA = "m207-s01-annotation-schemas/v1"
PILOT_SCHEMA_VERSION = 1
M199_SCHEMA = "npa-lawref-sample/v1"
M199_PROTOCOL_REL = "prd/migration/rust-evidence/m199-s01-annotation-protocol.md"
M199_PROTOCOL_SHA256 = "eed922b02c1b89b8e51e8b342b1a9f113a8029b8a2fe0a1bee84f9f2035c6e3d"
M199_SLOT_SECTION = "## 5. Closed slot set"
CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
ANNOTATION_PREFIX = "prd/annotation/"
SLOT_SPACE_SOURCE = "prd/migration/rust-evidence/m199-s01-annotation-protocol.md#5"
CONTRACT_HEADING = "Machine-readable codebook contract"

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
CASE_COUNT_RANGE = (20, 40)
WORK_FAMILY_CAP = 4

OUTPUT_CONTRACT = {
    "output_type": "AnnotationSuggestion",
    "authority": "none",
    "suggestion_status": "none-provided",
    "model_invoked": False,
}
BOUNDARIES = {
    "human_coding": "S02",
    "adjudication": "S02",
    "agreement": "S02",
    "per_aspect_rates": "S03",
}
REQUIRED_MARKERS = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}
REQUIRED_SECTIONS = (
    "1. Unit of coding",
    "2. Closed slot space",
    "3. Alternatives are a closed decision space",
    "4. Abstention is a coder outcome",
    "5. As-written discipline",
    "6. Coder submission schema",
    "7. Lifecycle markers and non-claims",
    "8. Boundary: S02 and S03 own adjudication, agreement and rates",
    "Machine-readable codebook contract",
)
REQUIRED_NON_CLAIMS = (
    "official-publication",
    "R070",
    "LawRef",
    "N2-gate",
    "legal interpretation",
    "gold",
)
ALTERNATIVE_AXES = (
    ("reference_decision", ("reference", "not_a_reference")),
    ("slot_presence", ("slot_present", "slot_absent")),
    ("scope", ("scope_local", "scope_inherited")),
    ("binding", ("binding_explicit", "binding_unresolved")),
)

FORBIDDEN_KEYS_CANONICAL = ("label", "expected", "answer", "prediction", "gold", "capture")
FORBIDDEN_SEED_KEYS_CANONICAL = (
    "seed_span",
    "rule_seed_span",
    "rule_seed",
    "ds_span",
    "seed_slots",
)
# Token-level check: ``gold_label``, ``predicted_answer`` and ``answer_key`` are
# rejected exactly like the bare ``label`` key.
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
# Whole-key check for rule-seed fields, whose tokens (``seed``, ``span``) are
# otherwise legitimate vocabulary in this contract.
FORBIDDEN_EXACT_KEYS = frozenset(FORBIDDEN_SEED_KEYS_CANONICAL)
# The deny-list fields themselves legitimately hold the forbidden names.
EXEMPT_KEY_LISTS = frozenset({"forbidden_keys", "forbidden_seed_keys"})

SCHEMA_ROOT_KEYS = (
    "schema",
    "schema_version",
    "codebook",
    "slot_space_source",
    "parent_schema",
    "m199_schema_version_bump",
    "slot_space",
    "alternative_axes",
    "vocabularies",
    "schemas",
    "non_claims",
    "lifecycle",
)
REQUIRED_SUBSCHEMAS = ("case_manifest", "coding_submission", "prompt_packet")
VOCABULARY_EXPECTATIONS = {
    "families": ["npa", "courts", "fas", "xml"],
    "note_kinds": ["enacting", "provider_note", "hostile-control", "pattern-boost"],
    "metadata_sources": ["validated-manifest", "unknown"],
    "provenance": [PROVENANCE_VALUE],
    "authority": ["none"],
    "suggestion_status": ["none-provided"],
    "output_type": ["AnnotationSuggestion"],
    "decision_values": list(DECISION_VALUES),
    "abstention_values": list(ABSTENTION_VALUES),
}

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
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError(
            "SCHEMA_PARSE_ERROR",
            f"{label} is not closed JSON (YAML, comments, merged or truncated "
            f"documents are rejected): {exc}",
        ) from exc


def parse_protocol_slots(text: str) -> tuple[tuple[str, ...], str | None, int]:
    """Return the frozen M199 section-5 slot space as declared by the protocol."""
    if M199_SLOT_SECTION not in text:
        return (), None, 0
    section = text.split(M199_SLOT_SECTION, 1)[1].split("\n## 6.", 1)[0]
    names = SLOT_ROW_RE.findall(section)
    outcome = names[-1] if names and names[-1] == M199_BINARY_OUTCOME else None
    slots = tuple(names[:-1]) if outcome else tuple(names)
    return slots, outcome, len(names)


def codebook_headings(text: str) -> list[str]:
    return [match.group(1).strip() for match in HEADING_RE.finditer(text)]


def extract_contract(text: str) -> dict[str, Any]:
    index = text.find(f"## {CONTRACT_HEADING}")
    if index < 0:
        raise GateError("MISSING_SECTION", f"codebook section '## {CONTRACT_HEADING}' is absent")
    block = FENCE_RE.search(text[index:])
    if block is None:
        raise GateError(
            "MISSING_SECTION",
            f"codebook section '## {CONTRACT_HEADING}' has no fenced json block",
        )
    contract = load_json_text(block.group(1), "codebook contract")
    if not isinstance(contract, dict):
        raise GateError("SCHEMA_PARSE_ERROR", "codebook contract must be a JSON object")
    return contract


def load_json_text(text: str, label: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not closed JSON: {exc}") from exc


def key_tokens(key: str) -> list[str]:
    spaced = CAMEL_BOUNDARY_RE.sub("_", key)
    return [token for token in TOKEN_SEPARATOR_RE.split(spaced.lower()) if token]


def forbidden_key_hit(name: str) -> str | None:
    """Return the forbidden-field class for a candidate key name, if any."""
    if set(key_tokens(name)) & FORBIDDEN_KEY_TOKENS:
        return "predicted-answer"
    if name.strip().lower() in FORBIDDEN_EXACT_KEYS:
        return "rule-seed-span"
    return None


def scan_forbidden_keys(
    node: Any, pointer: str, failures: Failures, *, key_list: bool = False
) -> None:
    """Reject predicted-answer and rule-seed keys at any nesting depth.

    Closed key sets are JSON arrays of key names, so a forbidden name such as
    ``label`` arrives as an element of a ``*_keys`` list rather than as a dict
    key.  Both surfaces are checked; the canonical ``forbidden_*_keys`` lists
    are exempt because they are the deny-list itself and are pinned by value.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            hit = forbidden_key_hit(key)
            if hit:
                _fail(
                    failures,
                    "LEAK_FORBIDDEN_KEY",
                    f"key {key!r} at {pointer or '$'} mints a {hit} field",
                )
            nested_key_list = key.endswith("_keys") and key not in EXEMPT_KEY_LISTS
            scan_forbidden_keys(value, f"{pointer}.{key}", failures, key_list=nested_key_list)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            if key_list and isinstance(item, str):
                element_hit = forbidden_key_hit(item)
                if element_hit:
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"closed key {item!r} at {pointer}[{index}] mints a {element_hit} field",
                    )
            scan_forbidden_keys(item, f"{pointer}[{index}]", failures)


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def _close_keys(label: str, keys: Any, failures: Failures) -> tuple[str, ...]:
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) for k in keys):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} must be a non-empty list of string keys")
        return ()
    if len(set(keys)) != len(keys):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} carries duplicate keys")
    return tuple(keys)


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


def _check_non_claims(label: str, claims: Any, failures: Failures) -> None:
    if not isinstance(claims, list) or not all(isinstance(c, str) for c in claims):
        _fail(failures, "MISSING_NON_CLAIM", f"{label} must be a list of non-claim strings")
        return
    blob = "\n".join(claims)
    for required in REQUIRED_NON_CLAIMS:
        if required not in blob:
            _fail(
                failures,
                "MISSING_NON_CLAIM",
                f"{label} is missing the required non-claim substring {required!r}",
            )


def _check_lifecycle(label: str, markers: Any, failures: Failures) -> None:
    if markers != REQUIRED_MARKERS:
        _fail(
            failures,
            "MISSING_LIFECYCLE_MARKER",
            f"{label}={markers!r} != required lifecycle markers {REQUIRED_MARKERS!r}",
        )


def expected_alternative_axes() -> list[dict[str, Any]]:
    return [{"axis": axis, "values": list(values)} for axis, values in ALTERNATIVE_AXES]


def check_schema_document(schema: Any, failures: Failures) -> None:
    if not isinstance(schema, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "schemas document must be a JSON object")
        return
    scan_forbidden_keys(schema, "$", failures)
    if set(schema) != set(SCHEMA_ROOT_KEYS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$ keys differ: extra="
            f"{sorted(set(schema) - set(SCHEMA_ROOT_KEYS))} missing="
            f"{sorted(set(SCHEMA_ROOT_KEYS) - set(schema))}",
        )
    if schema.get("schema") != PILOT_SCHEMA:
        _fail(
            failures, "SCHEMA_KEY_DRIFT", f"$.schema={schema.get('schema')!r} != {PILOT_SCHEMA!r}"
        )
    if schema.get("schema") == M199_SCHEMA:
        _fail(failures, "SCHEMA_KEY_DRIFT", "pilot schema may not reuse the M199 schema id")
    if schema.get("schema_version") != PILOT_SCHEMA_VERSION:
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.schema_version must be 1")
    if schema.get("m199_schema_version_bump") is not False:
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.m199_schema_version_bump must be false (D467)")
    if schema.get("slot_space_source") != SLOT_SPACE_SOURCE:
        _fail(
            failures,
            "SLOT_SET_DRIFT",
            f"$.slot_space_source={schema.get('slot_space_source')!r} != {SLOT_SPACE_SOURCE!r}",
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

    if schema.get("alternative_axes") != expected_alternative_axes():
        _fail(
            failures,
            "ALTERNATIVE_DRIFT",
            "$.alternative_axes must equal the closed codebook decision space",
        )

    vocabularies = schema.get("vocabularies")
    if not isinstance(vocabularies, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.vocabularies must be an object")
    else:
        for name, expected in VOCABULARY_EXPECTATIONS.items():
            if vocabularies.get(name) != expected:
                _fail(
                    failures,
                    "VOCABULARY_DRIFT",
                    f"$.vocabularies.{name}={vocabularies.get(name)!r} != {expected!r}",
                )

    subschemas = schema.get("schemas")
    if not isinstance(subschemas, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.schemas must be an object")
    else:
        for name in REQUIRED_SUBSCHEMAS:
            if name not in subschemas:
                _fail(failures, "MISSING_SCHEMA", f"$.schemas.{name} is absent")
        _check_case_manifest(subschemas.get("case_manifest"), failures)
        _check_coding_submission(subschemas.get("coding_submission"), failures)
        _check_prompt_packet(subschemas.get("prompt_packet"), failures)

    _check_non_claims("$.non_claims", schema.get("non_claims"), failures)
    _check_lifecycle("$.lifecycle", schema.get("lifecycle"), failures)


def _check_case_manifest(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    closed = _close_keys("$.schemas.case_manifest.closed_keys", sub.get("closed_keys"), failures)
    required = _close_keys(
        "$.schemas.case_manifest.required_keys", sub.get("required_keys"), failures
    )
    for key in required:
        if key not in closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"case_manifest required key {key!r} is not in its closed key set",
            )
    case_closed = _close_keys(
        "$.schemas.case_manifest.case_closed_keys", sub.get("case_closed_keys"), failures
    )
    for banned in ("slots", *FORBIDDEN_SEED_KEYS_CANONICAL):
        if banned in case_closed:
            _fail(
                failures,
                "LEAK_FORBIDDEN_KEY",
                f"case_manifest case key {banned!r} would publish predicted answers",
            )
    if sub.get("case_count_range") != list(CASE_COUNT_RANGE):
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case_manifest.case_count_range={sub.get('case_count_range')!r} != "
            f"{list(CASE_COUNT_RANGE)}",
        )
    cap = sub.get("work_family_cap")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap != WORK_FAMILY_CAP:
        _fail(
            failures,
            "WORK_FAMILY_DOMINANCE",
            f"case_manifest.work_family_cap={cap!r} != {WORK_FAMILY_CAP}",
        )
    if (
        sub.get("abstention_available") is not True
        or sub.get("span_offered_for_coding") is not True
    ):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "case_manifest must offer abstention and a span for every case",
        )
    if sub.get("unknown_metadata_value") != "unknown":
        _fail(
            failures,
            "METADATA_PATH_DERIVED",
            "case_manifest.unknown_metadata_value must be 'unknown'",
        )


def _check_coding_submission(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    closed = _close_keys(
        "$.schemas.coding_submission.closed_keys", sub.get("closed_keys"), failures
    )
    required = _close_keys(
        "$.schemas.coding_submission.required_keys", sub.get("required_keys"), failures
    )
    for key in required:
        if key not in closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"coding_submission required key {key!r} is not in its closed key set",
            )
    _close_keys(
        "$.schemas.coding_submission.case_closed_keys", sub.get("case_closed_keys"), failures
    )
    _close_keys(
        "$.schemas.coding_submission.span_closed_keys", sub.get("span_closed_keys"), failures
    )
    declared_slots = _close_keys(
        "$.schemas.coding_submission.slot_closed_keys", sub.get("slot_closed_keys"), failures
    )
    if declared_slots:
        if len(declared_slots) > len(M199_SLOT_SPACE):
            _fail(
                failures,
                "NINTH_SLOT",
                f"coding_submission.slot_closed_keys declares {len(declared_slots)} slots",
            )
        elif declared_slots != M199_SLOT_SPACE:
            _fail(
                failures,
                "SLOT_SET_DRIFT",
                "coding_submission.slot_closed_keys != M199 §5 slot space",
            )
    if sub.get("decision_values") != list(DECISION_VALUES):
        _fail(failures, "SCHEMA_KEY_DRIFT", "coding_submission.decision_values drifted")
    abstention = sub.get("abstention_values")
    if abstention != list(ABSTENTION_VALUES):
        _fail(failures, "ABSTENTION_COLLAPSE", "coding_submission.abstention_values drifted")
    elif set(abstention) & set(DECISION_VALUES):
        _fail(
            failures,
            "ABSTENTION_COLLAPSE",
            "abstention values may not reuse reference-decision values",
        )
    if sub.get("abstention_distinct_from") != M199_BINARY_OUTCOME:
        _fail(
            failures,
            "ABSTENTION_COLLAPSE",
            "coding_submission must keep abstention distinct from not_a_reference",
        )
    if sub.get("provenance_value") != PROVENANCE_VALUE:
        _fail(
            failures,
            "PROVENANCE_DRIFT",
            f"coding_submission.provenance_value must be {PROVENANCE_VALUE!r}",
        )
    if sub.get("coder_pass_values") != list(CODER_PASS_VALUES):
        _fail(failures, "SCHEMA_KEY_DRIFT", "coding_submission.coder_pass_values must be [1, 2]")


def _check_prompt_packet(sub: Any, failures: Failures) -> None:
    if not isinstance(sub, dict):
        return
    closed = _close_keys("$.schemas.prompt_packet.closed_keys", sub.get("closed_keys"), failures)
    required = _close_keys(
        "$.schemas.prompt_packet.required_keys", sub.get("required_keys"), failures
    )
    for key in required:
        if key not in closed:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"prompt_packet required key {key!r} is not in its closed key set",
            )
    anchor = _close_keys(
        "$.schemas.prompt_packet.anchor_closed_keys", sub.get("anchor_closed_keys"), failures
    )
    for key in ("source_sha256", "byte_len"):
        if anchor and key not in anchor:
            _fail(failures, "SCHEMA_KEY_DRIFT", f"prompt_packet anchor must carry {key!r}")
    _close_keys("$.schemas.prompt_packet.span_closed_keys", sub.get("span_closed_keys"), failures)
    if sub.get("output_type") != OUTPUT_CONTRACT["output_type"]:
        _fail(
            failures,
            "AUTHORITY_CLAIM",
            "prompt_packet.output_type must be AnnotationSuggestion",
        )
    if sub.get("authority_values") != ["none"]:
        _fail(
            failures, "AUTHORITY_CLAIM", "prompt_packet.authority_values must be exactly ['none']"
        )
    if sub.get("suggestion_status_values") != ["none-provided"]:
        _fail(
            failures,
            "AUTHORITY_CLAIM",
            "prompt_packet.suggestion_status_values must be exactly ['none-provided']",
        )
    if sub.get("model_invoked") is not False:
        _fail(failures, "AUTHORITY_CLAIM", "prompt_packet.model_invoked must be false in S01")


def check_contract(
    contract: dict[str, Any],
    schema: Any,
    protocol_slots: tuple[str, ...],
    headings: list[str],
    failures: Failures,
) -> None:
    scan_forbidden_keys(contract, "contract$", failures)
    if contract.get("codebook_id") != "m207-s01-codebook/v1":
        _fail(failures, "MISSING_SECTION", "contract.codebook_id must be m207-s01-codebook/v1")
    if contract.get("schema_id") != PILOT_SCHEMA:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"contract.schema_id must be {PILOT_SCHEMA!r}")
    if contract.get("slot_space_source") != SLOT_SPACE_SOURCE:
        _fail(failures, "SLOT_SET_DRIFT", "contract.slot_space_source drifted")
    if contract.get("m199_schema_version_bump") is not False:
        _fail(failures, "SLOT_SET_DRIFT", "contract must record no M199 schema_version bump")

    slot_space = contract.get("slot_space")
    if not isinstance(slot_space, dict):
        _fail(failures, "SLOT_SET_DRIFT", "contract.slot_space must be an object")
    else:
        _check_slot_space("contract.slot_space", slot_space.get("closed_keys"), failures)
        if isinstance(schema, dict) and slot_space != schema.get("slot_space"):
            _fail(
                failures,
                "SLOT_SET_DRIFT",
                "codebook contract slot space differs from the schema slot space",
            )

    if protocol_slots and isinstance(schema, dict):
        declared = schema.get("slot_space", {}).get("closed_keys")
        if declared is not None and tuple(declared) != protocol_slots:
            _fail(
                failures,
                "SLOT_SET_DRIFT",
                f"schema slot space {declared!r} != frozen M199 §5 {list(protocol_slots)!r}",
            )

    if contract.get("alternative_axes") != expected_alternative_axes():
        _fail(
            failures,
            "ALTERNATIVE_DRIFT",
            "contract.alternative_axes must equal the closed codebook decision space",
        )
    abstention = contract.get("abstention")
    if not isinstance(abstention, dict) or abstention.get("values") != list(ABSTENTION_VALUES):
        _fail(failures, "ABSTENTION_COLLAPSE", "contract.abstention.values drifted")
    elif abstention.get("distinct_from") != M199_BINARY_OUTCOME:
        _fail(
            failures,
            "ABSTENTION_COLLAPSE",
            "contract.abstention.distinct_from must be not_a_reference",
        )
    if contract.get("case_count_range") != list(CASE_COUNT_RANGE):
        _fail(failures, "CASE_COUNT_OUT_OF_RANGE", "contract.case_count_range drifted")
    cap = contract.get("work_family_cap")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap != WORK_FAMILY_CAP:
        _fail(failures, "WORK_FAMILY_DOMINANCE", f"contract.work_family_cap={cap!r} drifted")
    if contract.get("output_contract") != OUTPUT_CONTRACT:
        _fail(
            failures,
            "AUTHORITY_CLAIM",
            "contract.output_contract drifted from AnnotationSuggestion",
        )
    if contract.get("boundaries") != BOUNDARIES:
        _fail(failures, "OWNERSHIP_DRIFT", "contract.boundaries must keep S02/S03 ownership")
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
            _fail(failures, "MISSING_SECTION", f"codebook heading '## {section}' is absent")
    _check_non_claims("contract.non_claims", contract.get("non_claims"), failures)
    _check_lifecycle("contract.lifecycle", contract.get("lifecycle"), failures)


def report(failures: Failures) -> int:
    if not failures:
        print(MARKER)
        return 0
    seen: set[str] = set()
    for diagnostic, detail in failures:
        line = f"{diagnostic}: {detail}"
        if line in seen:
            continue
        seen.add(line)
        print(f"FAIL {line}", file=sys.stderr)
    print(
        f"FAIL M207_S01_SCHEMAS_GATE: {len(seen)} finding(s); the frozen pilot "
        "contract is not satisfied",
        file=sys.stderr,
    )
    return 1


def run_check(root: Path, codebook_rel: str, schemas_rel: str) -> int:
    failures: Failures = []
    try:
        protocol = resolve_artifact(
            root,
            M199_PROTOCOL_REL,
            "protocol",
            suffix=".md",
            prefix="prd/migration/rust-evidence/",
        )
        codebook = resolve_artifact(
            root, codebook_rel, "codebook", suffix=".md", prefix=ANNOTATION_PREFIX
        )
        schemas_path = resolve_artifact(
            root, schemas_rel, "schemas", suffix=".json", prefix=ANNOTATION_PREFIX
        )
    except GateError as exc:
        return report([(exc.diagnostic, exc.detail)])

    protocol_slots: tuple[str, ...] = ()
    if not protocol.is_file():
        _fail(
            failures, "FROZEN_SOURCE_DRIFT", f"frozen M199 protocol missing at {M199_PROTOCOL_REL}"
        )
    else:
        digest = sha256_file(protocol)
        if digest != M199_PROTOCOL_SHA256:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"M199 protocol sha256 {digest} != pinned {M199_PROTOCOL_SHA256}",
            )
        slots, outcome, row_count = parse_protocol_slots(protocol.read_text(encoding="utf-8"))
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

    contract: dict[str, Any] | None = None
    headings: list[str] = []
    if not codebook.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"codebook missing at {codebook}")
    else:
        text = codebook.read_text(encoding="utf-8")
        headings = codebook_headings(text)
        try:
            contract = extract_contract(text)
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    schema: Any = None
    if not schemas_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"schemas missing at {schemas_path}")
    else:
        try:
            schema = load_json(schemas_path, "schemas document")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    if schema is not None:
        check_schema_document(schema, failures)
    if contract is not None:
        check_contract(contract, schema, protocol_slots, headings, failures)

    return report(failures)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check"],
        help="only 'check' exists: verify the frozen contract read-only",
    )
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="repository root the artifact paths are resolved against",
    )
    parser.add_argument("--codebook", default=CODEBOOK_REL, help="codebook path relative to root")
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="schema path relative to root")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        return report([("MISSING_ARTIFACT", f"root {root} is not a directory")])
    return run_check(root, args.codebook, args.schemas)


if __name__ == "__main__":
    raise SystemExit(main())
