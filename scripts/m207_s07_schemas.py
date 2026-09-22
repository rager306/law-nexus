#!/usr/bin/env python3
"""Frozen S07 operational successor contract and fail-closed gate for M207/S07 (T01).

This is an offline, read-only, fail-closed evidence gate. It binds the frozen S07 successor
contract to the artifacts it rests on:

* ``prd/annotation/m207-s07-c4-protocol.md`` -- the frozen protocol, including the closed
  diagnostic vocabulary between the ``s07-diagnostics`` markers;
* ``prd/annotation/m207-s07-schemas.json`` -- the closed schema document (``m207-s07-schemas/v1``);
* the eight frozen S04/M204/S03/M199 sources, re-hashed against the live tree;
* the declared corpus pins (43785 consultant XML, 12 Garant files) and the 180-fragment seed.

The gate proves, against the frozen sources rather than against prose:

* the schema document carries exactly the declared top-level key set;
* ``receipt_schema_id`` is ``m207-s07-c4-operational-successor/v1`` and ``sidecar_schema_id`` is
  the reused-verbatim ``npa-contour-failure-trace/v1``;
* ``full_walk`` and ``timeout`` are independent, recomputable predicates over terminal facts and
  the JSONL header/payload, and ``duration_ms`` is recorded but absent from both predicate bodies
  -- a duration floor that reappears as acceptance is ``DURATION_FLOOR_AS_ACCEPTANCE``;
* ``promotion`` stays ``none``, ``classification`` stays ``not-authorized``, ``human_acceptance``
  stays ``null`` and ``is_gold`` stays ``false``;
* the failure policy keeps the sidecar key set, the provider/class allowlist and the
  ``acceptance_effect = none`` rule closed;
* the marker contract keeps ``M207_S07_SCHEMAS_OK`` / ``M207_S07_SCHEMAS_SELFTEST_OK`` as
  integrity statements, never acceptance;
* the schema diagnostic set equals the protocol marker block in both directions;
* every frozen source still hashes to its pin and the corpus/seed counts still match.

No walk is launched and no artifact is produced here: this gate only reads the frozen documents
and re-counts the declared corpus and seed, and rejects drift. ``check`` prints exactly the marker
``M207_S07_SCHEMAS_OK``; ``selftest`` additionally proves the named negative paths and prints
``M207_S07_SCHEMAS_SELFTEST_OK``. Every failure is a non-zero exit with a named diagnostic on
stderr.
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

MARKER = "M207_S07_SCHEMAS_OK"
SELFTEST_MARKER = "M207_S07_SCHEMAS_SELFTEST_OK"

SCHEMA_ID = "m207-s07-schemas/v1"
SCHEMA_VERSION = 1
PROTOCOL_ID = "m207-s07-c4-protocol/v1"
PROTOCOL_REL = "prd/annotation/m207-s07-c4-protocol.md"
SCHEMAS_REL = "prd/annotation/m207-s07-schemas.json"
ANNOTATION_PREFIX = "prd/annotation/"
RECEIPT_SCHEMA_ID = "m207-s07-c4-operational-successor/v1"
SIDECAR_SCHEMA_ID = "npa-contour-failure-trace/v1"
DIGEST_FORMAT = "bare lowercase hex sha256, no algorithm prefix"

SCHEMA_ROOT_KEYS = (
    "schema",
    "schema_version",
    "protocol",
    "receipt_schema_id",
    "sidecar_schema_id",
    "digest_format",
    "frozen_sources",
    "corpus_pins",
    "predicates",
    "failure_policy",
    "new_attempt_policy",
    "promotion_contract",
    "s03_isolation",
    "marker_contract",
    "vocabularies",
    "diagnostics",
    "non_claims",
    "lifecycle",
)

REQUIRED_SECTIONS = (
    "1. Scope, boundaries and frozen inputs",
    "2. Predicates: full walk and timeout",
    "3. Kill ceiling: budget is a ceiling, not an achievement",
    "4. New attempt: identity, paths and write-once",
    "5. Failure policy: sidecar, allowlist and named refusals",
    "6. Promotion contract: nothing is promoted",
    "7. Human pilot is not a gate (D519)",
    "8. Markers and what they do not mean",
    "9. Non-claims",
    "10. Requirement bindings",
    "11. Fail-closed diagnostics",
)

DIAGNOSTICS_BEGIN = "<!-- s07-diagnostics:begin -->"
DIAGNOSTICS_END = "<!-- s07-diagnostics:end -->"
_DIAGNOSTIC_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)

EXPECTED_DIAGNOSTICS = (
    "MISSING_ARTIFACT",
    "MISSING_SECTION",
    "UNSAFE_PATH",
    "SCHEMA_PARSE_ERROR",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_VERSION_DRIFT",
    "MARKER_CONTRACT_DRIFT",
    "C4_RECEIPT_DRIFT",
    "CORPUS_COUNT_DRIFT",
    "TERMINAL_OUTCOME_DRIFT",
    "PREDICATE_CONTRADICTION",
    "DURATION_FLOOR_AS_ACCEPTANCE",
    "PROMOTION_CLAIM",
    "GOLD_CLAIM",
    "PROTOCOL_DIAGNOSTIC_DRIFT",
    "SEED_ENLARGE",
    "GATE_INTERNAL_ERROR",
)

EXPECTED_FROZEN_SOURCES: dict[str, dict[str, str]] = {
    "m207_s04_c4_protocol": {
        "path": "prd/annotation/m207-s04-c4-protocol.md",
        "sha256": "11dd5e0bbd29ecd398469be95321fc854d3da323bed2b3b0042c1c6f595642fb",
    },
    "m207_s04_schemas": {
        "path": "prd/annotation/m207-s04-schemas.json",
        "sha256": "7d494b55f5bd7b5a6ee5dd7818f4ca3aa61a26dcfb81d1b1c4d2de27df217293",
    },
    "m207_s04_c4_operational_receipt": {
        "path": "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json",
        "sha256": "423d30de06080fce1c3da255d1d03cc3f19548d29e4338c74d913f4771e9e935",
    },
    "m204_s06_c4_operational_receipt": {
        "path": "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
        "sha256": "04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c",
    },
    "m207_s04_battery": {
        "path": "prd/migration/rust-evidence/m207-s04-battery.json",
        "sha256": "cc6dbb3933bc8e5d91c3cf7866ed28e40061a5740c77429b923d4e487ade91fc",
    },
    "m207_s03_battery": {
        "path": "prd/migration/rust-evidence/m207-s03-battery.json",
        "sha256": "76b9a78e3e83772be3ca3e46b83a89b3b3baaf690ffe6aa0c72f77aa6d56b533",
    },
    "m199_s01_sample_manifest": {
        "path": "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json",
        "sha256": "134751f49db1858329248be1857ada669097f1860609090028c7b5af8975574f",
    },
    "m199_seed_sidecar": {
        "path": "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json",
        "sha256": "b88e5af14bcc9496c4d35627afda058d58956f459106c147f1cc7959a6930f28",
    },
}

EXPECTED_CORPUS_PINS: dict[str, Any] = {
    "consultant_root": "consru_export/consru_export/exports",
    "consultant_root_is_declared_not_derived": True,
    "consultant_xml_suffix": ".xml",
    "consultant_xml_count": 43785,
    "garant_root": "law-source/garant",
    "garant_file_count": 12,
    "count_basis": "recursive file count under the declared root, identical to the M204/S06 basis",
    "count_is_a_corpus_pin_not_promotion_evidence": True,
    "drift_diagnostic": "CORPUS_COUNT_DRIFT",
}

EXPECTED_OUTCOMES = ("full_walk", "timeout", "nonzero", "launch_error")

_BUDGET_SECONDS_MINIMUM = 3600

EXPECTED_FULL_WALK: dict[str, Any] = {
    "requires_no_limit_flag": True,
    "header_limit_is_null": True,
    "canonical_payload_limit_is_null": True,
    "corpus_consultant_xml_count": 43785,
    "corpus_garant_file_count": 12,
    "aggregate_files_equals": 43797,
    "terminal_outcome": "complete",
    "terminal_exit_code": 0,
    "terminal_timeout": False,
    "terminal_signal_is_null": True,
}

EXPECTED_TIMEOUT: dict[str, Any] = {
    "terminal_outcome": "timeout",
    "terminal_exit_code_is_null": True,
    "terminal_signal": "SIGTERM",
    "terminal_timeout": True,
}

EXPECTED_PREDICATE_FLAGS_TRUE = (
    "duration_ms_is_recorded",
    "duration_ms_is_not_a_predicate_input",
    "duration_floor_is_not_acceptance",
    "short_complete_is_lawful_full_walk",
    "budget_seconds_is_a_kill_ceiling",
    "outcome_is_recomputed_not_read_from_a_claim",
    "run_status_is_not_terminal_evidence",
)

# Flags whose reversal would smuggle the S04 duration floor back in as acceptance.
DURATION_FLOOR_FLAGS = (
    "duration_ms_is_not_a_predicate_input",
    "duration_floor_is_not_acceptance",
    "short_complete_is_lawful_full_walk",
)

DURATION_TOKENS = ("duration", "elapsed", "wall_clock")

EXPECTED_SIDECAR_KEYS = ("record_kind", "schema", "provider", "path", "class")
EXPECTED_PROVIDERS = ("consultant", "garant")
EXPECTED_CLASSES = ("read", "digest", "decode", "toctou")
EXPECTED_PROVIDER_ROOTS = {
    "consultant": "consru_export/consru_export/exports/",
    "garant": "law-source/garant/",
}
_EXIT_OUT_UNWRITABLE = 3

EXPECTED_FAILURE_POLICY_FLAGS_TRUE = (
    "sidecar_schema_reused_verbatim",
    "path_must_be_repo_relative_under_provider_root",
    "sidecar_count_must_equal_aggregate_failed",
    "empty_sidecar_is_lawful_only_when_failed_zero",
    "missing_sidecar_with_positive_failed_is_named_refusal",
    "allowlist_refusal_is_lawful_nonzero_without_sidecar",
    "sidecar_is_write_once",
    "failure_identity_is_not_stored_in_the_receipt",
    "historical_failed_file_is_not_recoverable",
    "retry_or_last_error_surface_forbidden",
)

ATTEMPT_DIR_PREFIX = "prd/migration/rust-evidence/m207-s07-c4-attempts/"
RECEIPT_PATH = "prd/migration/rust-evidence/m207-s07-c4-operational-receipt.json"
SIDECAR_ARG = "--failures-out"

EXPECTED_FORBIDDEN_WRITE_PATHS = (
    "prd/annotation/m207-s04-c4-protocol.md",
    "prd/annotation/m207-s04-schemas.json",
    "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json",
    "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
    "prd/migration/rust-evidence/m207-s04-battery.json",
    "prd/migration/rust-evidence/m207-s03-battery.json",
    "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json",
    "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json",
    "prd/migration/rust-evidence/m207-s03-evaluation-report.json",
)
EXPECTED_FORBIDDEN_WRITE_PREFIXES = ("prd/migration/rust-evidence/m207-s04-c4-attempts/",)

EXPECTED_NEW_ATTEMPT_POLICY_FLAGS_TRUE = (
    "limit_flag_forbidden",
    "write_once",
    "new_argv_changes_identity",
    "old_argv_must_not_be_edited",
    "receipt_written_only_after_terminal_facts",
    "receipt_is_never_reconstructed_from_logs",
)

EXPECTED_PROMOTION: dict[str, Any] = {
    "promotion": "none",
    "classification": "not-authorized",
    "threshold": None,
    "human_acceptance": None,
    "is_gold": False,
    "model_invoked": False,
    "legal_claim": "forbidden",
    "rate_publication": "forbidden",
    "measurement_status_publication": "forbidden",
    "acceptance_effect_of_failures": "none",
    "corpus_complete_is_not_acceptance": True,
    "marker_is_not_acceptance": True,
}

EXPECTED_SEED_ROOT = "crates/ln-decode/tests/fixtures/npa-lawref"
EXPECTED_SEED_GLOB = "*.txt"
EXPECTED_SEED_COUNT = 180
EXPECTED_SEED_DIGEST = "50b48668cba5b89d75af0604a78004404310e36377679984273fa0a883053c9d"
EXPECTED_SEED_SIDECAR = "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json"
EXPECTED_SEED_SIDECAR_SHA256 = "b88e5af14bcc9496c4d35627afda058d58956f459106c147f1cc7959a6930f28"
EXPECTED_CRATES_PATTERNS = (
    "m207-s03",
    "m207_s03",
    "m207-s04",
    "m207_s04",
    "m207-s07",
    "m207_s07",
)
EXPECTED_EVALUATION_REPORT_PATH = "prd/migration/rust-evidence/m207-s03-evaluation-report.json"
EXPECTED_S03_BATTERY_PATH = "prd/migration/rust-evidence/m207-s03-battery.json"

EXPECTED_NON_CLAIMS = (
    "not gold: no S07 artifact, predicate, sidecar row or marker is a gold label",
    "not a promotion: promotion stays none, classification stays not-authorized, "
    "human_acceptance stays null",
    "not a threshold: no rate threshold, pass/fail cut-off or accept/reject decision is introduced",
    "not a classification: no classifier is fitted, no D388 gate is selected and no gate is scored",
    "not independent-measured: S07 runs no human pilot and publishes no measured rate",
    "not a rewrite of S04/M204: the frozen receipt, its logs, its claims and the M204 timeout "
    "receipt stay byte-identical",
    "not a timeout redefinition: a short complete walk is not renamed timeout and a timeout is "
    "never renamed complete",
    "not a budget achievement: budget_seconds is a kill ceiling, not evidence the corpus "
    "envelope was exercised",
    "not a product surface: S07 is an offline Python harness and crates/** gains no reader and "
    "no new Rust type",
    "not a requirement status change: status_effect stays unchanged and R035/R070 stay HOLD",
    "not a failure identity for the historical run: the S04 failed = 1 file stays unidentified",
    "not a human gate: the human pilot is not a gate (D519)",
    "not a second measurement convention: no S03 aspect or stratum rate is imported or re-derived",
    "not a seed enlargement: the 180 frozen fragments stay 180",
)

EXPECTED_LIFECYCLE: dict[str, Any] = {
    "human_adoption": "pending",
    "human_pilot_is_not_a_gate": True,
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}

Failures = list[tuple[str, str]]

_MISSING = object()


class GateError(Exception):
    """A named, machine-distinguishable gate failure."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def _is_bare_digest(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def resolve_artifact(root: Path, raw: Any, label: str, suffix: str, prefix: str) -> Path:
    """Resolve a declared annotation path, refusing escapes and the wrong class of file."""
    if not isinstance(raw, str) or not raw:
        raise GateError("MISSING_ARTIFACT", f"{label} path must be a non-empty string")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or ".." in rel.parts:
        raise GateError("UNSAFE_PATH", f"{label} path {raw!r} escapes the repository root")
    if not raw.startswith(prefix) or not raw.endswith(suffix):
        raise GateError(
            "UNSAFE_PATH",
            f"{label} path {raw!r} must be a {suffix} artifact under {prefix}",
        )
    return root / raw


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GateError("SCHEMA_PARSE_ERROR", f"duplicate JSON key {key!r}")
        seen[key] = value
    return seen


def load_json_text(text: str, label: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except ValueError as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label} is not valid JSON: {exc}") from exc


def load_json(path: Path, label: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError("MISSING_ARTIFACT", f"{label} at {path} is unreadable: {exc}") from exc
    return load_json_text(text, label)


def protocol_headings(text: str) -> list[str]:
    return [match.group(1).strip() for match in _HEADING_RE.finditer(text)]


def parse_protocol_diagnostics(text: str) -> set[str]:
    """Extract the closed S07 diagnostic set from the protocol document.

    Exactly one marker block is expected, with one upper-case code per line. A missing or
    duplicated marker, an out-of-order block, an empty block, a duplicate code or a non-code
    line is a hard failure -- never a silent skip.
    """
    lines = text.splitlines()
    begins = [index for index, line in enumerate(lines) if line.strip() == DIAGNOSTICS_BEGIN]
    ends = [index for index, line in enumerate(lines) if line.strip() == DIAGNOSTICS_END]
    if len(begins) != 1 or len(ends) != 1:
        raise GateError(
            "PROTOCOL_DIAGNOSTIC_DRIFT",
            f"expected exactly one diagnostic block, begin={len(begins)} end={len(ends)}",
        )
    if begins[0] >= ends[0]:
        raise GateError("PROTOCOL_DIAGNOSTIC_DRIFT", "diagnostic block markers are out of order")
    codes: list[str] = []
    for line in lines[begins[0] + 1 : ends[0]]:
        stripped = line.strip()
        if not stripped:
            continue
        if not _DIAGNOSTIC_CODE_RE.match(stripped):
            raise GateError(
                "PROTOCOL_DIAGNOSTIC_DRIFT", f"non-code line in diagnostic block: {stripped!r}"
            )
        codes.append(stripped)
    if not codes:
        raise GateError("PROTOCOL_DIAGNOSTIC_DRIFT", "diagnostic block is empty")
    if len(codes) != len(set(codes)):
        raise GateError("PROTOCOL_DIAGNOSTIC_DRIFT", "diagnostic block contains duplicate codes")
    return set(codes)


def _nested_keys(node: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            keys.append(str(key))
            keys.extend(_nested_keys(value))
    elif isinstance(node, list):
        for item in node:
            keys.extend(_nested_keys(item))
    return keys


# --------------------------------------------------------------------------- #
# Document checks (no filesystem access)
# --------------------------------------------------------------------------- #


def check_schema_root_keys(schema: dict[str, Any], failures: Failures) -> None:
    declared = set(schema)
    expected = set(SCHEMA_ROOT_KEYS)
    for key in sorted(declared - expected):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"$.{key} is not part of the closed S07 key set")
    for key in sorted(expected - declared):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"$.{key} is missing from the closed S07 key set")


def check_schema_identity(schema: dict[str, Any], failures: Failures) -> None:
    if schema.get("schema") != SCHEMA_ID:
        _fail(failures, "SCHEMA_VERSION_DRIFT", f"$.schema must be {SCHEMA_ID!r}")
    if schema.get("schema_version") != SCHEMA_VERSION:
        _fail(failures, "SCHEMA_VERSION_DRIFT", f"$.schema_version must be {SCHEMA_VERSION}")
    if schema.get("protocol") != PROTOCOL_REL:
        _fail(failures, "SCHEMA_VERSION_DRIFT", f"$.protocol must be {PROTOCOL_REL!r}")
    if schema.get("receipt_schema_id") != RECEIPT_SCHEMA_ID:
        _fail(
            failures,
            "SCHEMA_VERSION_DRIFT",
            f"$.receipt_schema_id must be {RECEIPT_SCHEMA_ID!r}, not "
            f"{schema.get('receipt_schema_id')!r}",
        )
    if schema.get("sidecar_schema_id") != SIDECAR_SCHEMA_ID:
        _fail(
            failures,
            "SCHEMA_VERSION_DRIFT",
            f"$.sidecar_schema_id must be the reused-verbatim {SIDECAR_SCHEMA_ID!r}",
        )
    if schema.get("digest_format") != DIGEST_FORMAT:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"$.digest_format must be {DIGEST_FORMAT!r}")


def check_frozen_sources_declared(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "C4_RECEIPT_DRIFT", "$.frozen_sources must be an object")
        return
    for name, expected in EXPECTED_FROZEN_SOURCES.items():
        entry = declared.get(name)
        if not isinstance(entry, dict):
            _fail(failures, "C4_RECEIPT_DRIFT", f"$.frozen_sources.{name} is missing")
            continue
        if entry.get("path") != expected["path"]:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                f"$.frozen_sources.{name}.path must be {expected['path']!r}",
            )
        if entry.get("sha256") != expected["sha256"]:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                f"$.frozen_sources.{name}.sha256 no longer matches the frozen pin",
            )
    for name in sorted(set(declared) - set(EXPECTED_FROZEN_SOURCES)):
        _fail(failures, "C4_RECEIPT_DRIFT", f"$.frozen_sources.{name} is not a frozen S07 source")


def check_corpus_pins_declared(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "CORPUS_COUNT_DRIFT", "$.corpus_pins must be an object")
        return
    for key, expected in EXPECTED_CORPUS_PINS.items():
        if declared.get(key, _MISSING) != expected:
            _fail(
                failures,
                "CORPUS_COUNT_DRIFT",
                f"$.corpus_pins.{key} must be {expected!r}, not {declared.get(key)!r}",
            )


def check_predicates(predicates: Any, failures: Failures) -> None:
    if not isinstance(predicates, dict):
        _fail(failures, "PREDICATE_CONTRADICTION", "$.predicates must be an object")
        return
    outcomes = predicates.get("outcomes")
    if not isinstance(outcomes, list) or tuple(outcomes) != EXPECTED_OUTCOMES:
        _fail(
            failures,
            "TERMINAL_OUTCOME_DRIFT",
            f"$.predicates.outcomes must be exactly {list(EXPECTED_OUTCOMES)!r}",
        )
    for name, expected_block in (("full_walk", EXPECTED_FULL_WALK), ("timeout", EXPECTED_TIMEOUT)):
        block = predicates.get(name)
        if not isinstance(block, dict):
            _fail(failures, "PREDICATE_CONTRADICTION", f"$.predicates.{name} is missing")
            continue
        for key, expected in expected_block.items():
            if block.get(key, _MISSING) != expected:
                _fail(
                    failures,
                    "PREDICATE_CONTRADICTION",
                    f"$.predicates.{name}.{key} must be {expected!r}, not {block.get(key)!r}",
                )
        for key in sorted(set(block) - set(expected_block)):
            _fail(
                failures,
                "PREDICATE_CONTRADICTION",
                f"$.predicates.{name}.{key} is not part of the closed {name} predicate",
            )
        for key in _nested_keys(block):
            if any(token in key.lower() for token in DURATION_TOKENS):
                _fail(
                    failures,
                    "DURATION_FLOOR_AS_ACCEPTANCE",
                    f"$.predicates.{name}.{key} makes a duration a predicate input; the S04 "
                    "duration floor is not an S07 acceptance test",
                )
    for flag in EXPECTED_PREDICATE_FLAGS_TRUE:
        if predicates.get(flag) is True:
            continue
        if flag in DURATION_FLOOR_FLAGS:
            _fail(
                failures,
                "DURATION_FLOOR_AS_ACCEPTANCE",
                f"$.predicates.{flag} must be true: the S04 duration floor is not an S07 "
                "acceptance test",
            )
        else:
            _fail(failures, "PREDICATE_CONTRADICTION", f"$.predicates.{flag} must be true")
    if predicates.get("budget_seconds_minimum") != _BUDGET_SECONDS_MINIMUM:
        _fail(
            failures,
            "PREDICATE_CONTRADICTION",
            f"$.predicates.budget_seconds_minimum must be {_BUDGET_SECONDS_MINIMUM}",
        )


def check_failure_policy(policy: Any, failures: Failures) -> None:
    label = "$.failure_policy"
    if not isinstance(policy, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} must be an object")
        return
    if policy.get("sidecar_schema_id") != SIDECAR_SCHEMA_ID:
        _fail(
            failures, "SCHEMA_KEY_DRIFT", f"{label}.sidecar_schema_id must be {SIDECAR_SCHEMA_ID!r}"
        )
    if not isinstance(policy.get("sidecar_keys"), list) or tuple(policy["sidecar_keys"]) != (
        EXPECTED_SIDECAR_KEYS
    ):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.sidecar_keys must be closed and exact")
    if policy.get("record_kind_value") != "failure":
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.record_kind_value must be 'failure'")
    if (
        not isinstance(policy.get("provider_allowlist"), list)
        or tuple(policy["provider_allowlist"]) != EXPECTED_PROVIDERS
    ):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.provider_allowlist must be {EXPECTED_PROVIDERS!r}",
        )
    if not isinstance(policy.get("class_allowlist"), list) or tuple(policy["class_allowlist"]) != (
        EXPECTED_CLASSES
    ):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.class_allowlist must be {EXPECTED_CLASSES!r}")
    if policy.get("provider_roots") != EXPECTED_PROVIDER_ROOTS:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.provider_roots must be {EXPECTED_PROVIDER_ROOTS!r}",
        )
    for flag in EXPECTED_FAILURE_POLICY_FLAGS_TRUE:
        if policy.get(flag) is not True:
            _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.{flag} must be true")
    if policy.get("exit_out_unwritable_code") != _EXIT_OUT_UNWRITABLE:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.exit_out_unwritable_code must be {_EXIT_OUT_UNWRITABLE}",
        )
    if policy.get("allowlist_refusal_outcome") != "nonzero":
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.allowlist_refusal_outcome must be 'nonzero'")
    if policy.get("allowlist_refusal_reason") != "allowlist_refusal":
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.allowlist_refusal_reason must be named")
    if policy.get("acceptance_effect") != "none":
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.acceptance_effect must stay 'none'")


def check_new_attempt_policy(policy: Any, failures: Failures) -> None:
    label = "$.new_attempt_policy"
    if not isinstance(policy, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} must be an object")
        return
    if policy.get("attempt_dir_prefix") != ATTEMPT_DIR_PREFIX:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.attempt_dir_prefix must be {ATTEMPT_DIR_PREFIX!r}",
        )
    if policy.get("receipt_path") != RECEIPT_PATH:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.receipt_path must be {RECEIPT_PATH!r}")
    if policy.get("sidecar_arg") != SIDECAR_ARG:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.sidecar_arg must be {SIDECAR_ARG!r}")
    if not isinstance(policy.get("attempt_id_slug_pattern"), str) or not policy.get(
        "attempt_id_slug_pattern"
    ):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.attempt_id_slug_pattern must be a pattern")
    for flag in EXPECTED_NEW_ATTEMPT_POLICY_FLAGS_TRUE:
        if policy.get(flag) is not True:
            _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.{flag} must be true")
    declared_paths = policy.get("forbidden_write_paths")
    if (
        not isinstance(declared_paths, list)
        or tuple(declared_paths) != EXPECTED_FORBIDDEN_WRITE_PATHS
    ):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.forbidden_write_paths must name every frozen path plus the evaluation report",
        )
    declared_prefixes = policy.get("forbidden_write_prefixes")
    if not isinstance(declared_prefixes, list) or tuple(declared_prefixes) != (
        EXPECTED_FORBIDDEN_WRITE_PREFIXES
    ):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.forbidden_write_prefixes must be {EXPECTED_FORBIDDEN_WRITE_PREFIXES!r}",
        )
    if policy.get("forbidden_write_diagnostic") != "C4_RECEIPT_DRIFT":
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.forbidden_write_diagnostic must be 'C4_RECEIPT_DRIFT'",
        )


def check_promotion(contract: Any, failures: Failures) -> None:
    if not isinstance(contract, dict):
        _fail(failures, "PROMOTION_CLAIM", "$.promotion_contract must be an object")
        return
    if contract.get("promotion") != "none" or contract.get("classification") != "not-authorized":
        _fail(
            failures,
            "PROMOTION_CLAIM",
            "$.promotion_contract.promotion/classification must stay none / not-authorized",
        )
    if contract.get("threshold") is not None:
        _fail(failures, "PROMOTION_CLAIM", "$.promotion_contract.threshold must stay null")
    if contract.get("human_acceptance") is not None or contract.get("is_gold") is not False:
        _fail(
            failures,
            "GOLD_CLAIM",
            "$.promotion_contract.human_acceptance must stay null and is_gold must stay false",
        )
    if contract.get("model_invoked") is not False:
        _fail(failures, "PROMOTION_CLAIM", "$.promotion_contract.model_invoked must stay false")
    if (
        contract.get("legal_claim") != "forbidden"
        or contract.get("rate_publication") != "forbidden"
    ):
        _fail(
            failures,
            "PROMOTION_CLAIM",
            "$.promotion_contract.legal_claim/rate_publication must stay forbidden",
        )
    if contract.get("acceptance_effect_of_failures") != "none":
        _fail(
            failures,
            "PROMOTION_CLAIM",
            "$.promotion_contract.acceptance_effect_of_failures must stay none",
        )
    for flag in ("corpus_complete_is_not_acceptance", "marker_is_not_acceptance"):
        if contract.get(flag) is not True:
            _fail(failures, "PROMOTION_CLAIM", f"$.promotion_contract.{flag} must be true")


def check_s03_isolation_declared(isolation: Any, failures: Failures) -> None:
    label = "$.s03_isolation"
    if not isinstance(isolation, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} must be an object")
        return
    if isolation.get("seed_fragment_count") != EXPECTED_SEED_COUNT:
        _fail(
            failures,
            "SEED_ENLARGE",
            f"{label}.seed_fragment_count must stay {EXPECTED_SEED_COUNT}, not "
            f"{isolation.get('seed_fragment_count')!r}",
        )
    if isolation.get("seed_aggregate_sha256") != EXPECTED_SEED_DIGEST:
        _fail(failures, "SEED_ENLARGE", f"{label}.seed_aggregate_sha256 no longer matches the pin")
    if isolation.get("seed_sidecar_sha256") != EXPECTED_SEED_SIDECAR_SHA256:
        _fail(failures, "SEED_ENLARGE", f"{label}.seed_sidecar_sha256 no longer matches the pin")
    if isolation.get("seed_fragment_root") != EXPECTED_SEED_ROOT:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.seed_fragment_root must be {EXPECTED_SEED_ROOT!r}",
        )
    if isolation.get("seed_fragment_glob") != EXPECTED_SEED_GLOB:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.seed_fragment_glob must be {EXPECTED_SEED_GLOB!r}",
        )
    if isolation.get("seed_sidecar_path") != EXPECTED_SEED_SIDECAR:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.seed_sidecar_path must be {EXPECTED_SEED_SIDECAR!r}",
        )
    if isolation.get("evaluation_report_path") != EXPECTED_EVALUATION_REPORT_PATH:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.evaluation_report_path must be {EXPECTED_EVALUATION_REPORT_PATH!r}",
        )
    if isolation.get("evaluation_report_must_be_absent") is not True:
        _fail(
            failures, "SCHEMA_KEY_DRIFT", f"{label}.evaluation_report_must_be_absent must be true"
        )
    if isolation.get("s03_battery_path") != EXPECTED_S03_BATTERY_PATH:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.s03_battery_path must be {EXPECTED_S03_BATTERY_PATH!r}",
        )
    if isolation.get("s03_battery_human_pilot_performed_required") is not False:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.s03_battery_human_pilot_performed_required must be false",
        )
    if isolation.get("s03_rates_required_status") != "not-measured":
        _fail(
            failures, "SCHEMA_KEY_DRIFT", f"{label}.s03_rates_required_status must be not-measured"
        )
    if isolation.get("rate_import_forbidden") is not True:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.rate_import_forbidden must be true")
    if isolation.get("crates_reference_forbidden") is not True:
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.crates_reference_forbidden must be true")
    patterns = isolation.get("crates_reference_patterns")
    if not isinstance(patterns, list) or set(patterns) != set(EXPECTED_CRATES_PATTERNS):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.crates_reference_patterns must be exactly {list(EXPECTED_CRATES_PATTERNS)!r}",
        )
    if isolation.get("seed_enlarge_diagnostic") != "SEED_ENLARGE":
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.seed_enlarge_diagnostic must be SEED_ENLARGE")


def check_marker_contract(marker: Any, failures: Failures) -> None:
    label = "$.marker_contract"
    if not isinstance(marker, dict):
        _fail(failures, "MARKER_CONTRACT_DRIFT", f"{label} must be an object")
        return
    if marker.get("marker") != MARKER:
        _fail(
            failures,
            "MARKER_CONTRACT_DRIFT",
            f"{label}.marker must be {MARKER!r}, not {marker.get('marker')!r}",
        )
    if marker.get("selftest_marker") != SELFTEST_MARKER:
        _fail(
            failures,
            "MARKER_CONTRACT_DRIFT",
            f"{label}.selftest_marker must be {SELFTEST_MARKER!r}",
        )
    values = marker.get("marker_values")
    if not isinstance(values, list) or set(values) != {MARKER, SELFTEST_MARKER}:
        _fail(failures, "MARKER_CONTRACT_DRIFT", f"{label}.marker_values must be the two markers")
    if marker.get("marker_is_not_acceptance") is not True:
        _fail(failures, "MARKER_CONTRACT_DRIFT", f"{label}.marker_is_not_acceptance must be true")
    if not isinstance(marker.get("meaning"), str) or not marker["meaning"]:
        _fail(failures, "MARKER_CONTRACT_DRIFT", f"{label}.meaning must be a non-empty string")
    does_not_mean = marker.get("does_not_mean")
    if not isinstance(does_not_mean, list) or not all(
        isinstance(item, str) and item for item in does_not_mean
    ):
        _fail(failures, "MARKER_CONTRACT_DRIFT", f"{label}.does_not_mean must be a non-empty list")


def check_vocabularies(vocabularies: Any, failures: Failures) -> None:
    label = "$.vocabularies"
    if not isinstance(vocabularies, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} must be an object")
        return
    expected = {
        "outcome_values": list(EXPECTED_OUTCOMES),
        "predicate_values": ["full_walk", "timeout"],
        "promotion_values": ["none"],
        "classification_values": ["not-authorized"],
        "provider_values": list(EXPECTED_PROVIDERS),
        "failure_class_values": list(EXPECTED_CLASSES),
        "marker_values": [MARKER, SELFTEST_MARKER],
        "digest_format": DIGEST_FORMAT,
        "requirement_status_effect_values": ["unchanged"],
    }
    for key, value in expected.items():
        if vocabularies.get(key) != value:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"{label}.{key} must be {value!r}, not {vocabularies.get(key)!r}",
            )


def check_diagnostics(
    declared: Any, protocol_diagnostics: set[str] | None, failures: Failures
) -> None:
    if not isinstance(declared, list) or not declared:
        _fail(failures, "PROTOCOL_DIAGNOSTIC_DRIFT", "$.diagnostics must be a non-empty list")
        return
    for code in declared:
        if not isinstance(code, str) or not _DIAGNOSTIC_CODE_RE.match(code):
            _fail(
                failures, "PROTOCOL_DIAGNOSTIC_DRIFT", f"$.diagnostics entry {code!r} is not a code"
            )
    if len(declared) != len(set(declared)):
        _fail(failures, "PROTOCOL_DIAGNOSTIC_DRIFT", "$.diagnostics contains duplicate codes")
    declared_set = {code for code in declared if isinstance(code, str)}
    if declared_set != set(EXPECTED_DIAGNOSTICS):
        missing = sorted(set(EXPECTED_DIAGNOSTICS) - declared_set)
        extra = sorted(declared_set - set(EXPECTED_DIAGNOSTICS))
        _fail(
            failures,
            "PROTOCOL_DIAGNOSTIC_DRIFT",
            f"$.diagnostics differs from the code vocabulary (missing={missing}, extra={extra})",
        )
    if protocol_diagnostics is not None and declared_set != protocol_diagnostics:
        missing = sorted(protocol_diagnostics - declared_set)
        extra = sorted(declared_set - protocol_diagnostics)
        _fail(
            failures,
            "PROTOCOL_DIAGNOSTIC_DRIFT",
            f"$.diagnostics and the protocol marker block disagree (missing={missing}, extra={extra})",
        )


def check_non_claims(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, list) or not all(
        isinstance(claim, str) and claim for claim in declared
    ):
        _fail(failures, "MISSING_SECTION", "$.non_claims must be a non-empty list of strings")
        return
    if set(declared) != set(EXPECTED_NON_CLAIMS):
        missing = sorted(set(EXPECTED_NON_CLAIMS) - set(declared))
        _fail(failures, "MISSING_SECTION", f"$.non_claims is missing {missing!r}")


def check_lifecycle(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "MISSING_SECTION", "$.lifecycle must be an object")
        return
    for key, expected in EXPECTED_LIFECYCLE.items():
        if declared.get(key, _MISSING) != expected:
            _fail(
                failures,
                "MISSING_SECTION",
                f"$.lifecycle.{key} must be {expected!r}, not {declared.get(key)!r}",
            )


def check_document(
    schema: dict[str, Any], protocol_diagnostics: set[str] | None, failures: Failures
) -> None:
    check_schema_root_keys(schema, failures)
    check_schema_identity(schema, failures)
    check_frozen_sources_declared(schema.get("frozen_sources"), failures)
    check_corpus_pins_declared(schema.get("corpus_pins"), failures)
    check_predicates(schema.get("predicates"), failures)
    check_failure_policy(schema.get("failure_policy"), failures)
    check_new_attempt_policy(schema.get("new_attempt_policy"), failures)
    check_promotion(schema.get("promotion_contract"), failures)
    check_s03_isolation_declared(schema.get("s03_isolation"), failures)
    check_marker_contract(schema.get("marker_contract"), failures)
    check_vocabularies(schema.get("vocabularies"), failures)
    check_diagnostics(schema.get("diagnostics"), protocol_diagnostics, failures)
    check_non_claims(schema.get("non_claims"), failures)
    check_lifecycle(schema.get("lifecycle"), failures)


# --------------------------------------------------------------------------- #
# Live-tree checks
# --------------------------------------------------------------------------- #


def check_live_frozen_sources(root: Path, declared: Any, failures: Failures) -> None:
    """Every declared frozen source must still hash to its pin on the live tree."""
    if not isinstance(declared, dict):
        return
    for name in sorted(EXPECTED_FROZEN_SOURCES):
        entry = declared.get(name)
        if not isinstance(entry, dict):
            _fail(failures, "C4_RECEIPT_DRIFT", f"$.frozen_sources.{name} is missing")
            continue
        rel = entry.get("path")
        pin = entry.get("sha256")
        if not isinstance(rel, str) or not isinstance(pin, str):
            _fail(failures, "C4_RECEIPT_DRIFT", f"$.frozen_sources.{name} is malformed")
            continue
        path = PurePosixPath(rel)
        if path.is_absolute() or ".." in path.parts:
            _fail(failures, "UNSAFE_PATH", f"$.frozen_sources.{name}.path {rel!r} escapes the root")
            continue
        target = root / rel
        if not target.is_file():
            _fail(failures, "C4_RECEIPT_DRIFT", f"frozen source {rel} is missing")
            continue
        if not _is_bare_digest(pin):
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                f"$.frozen_sources.{name}.sha256 is not a bare hex digest",
            )
            continue
        actual = sha256_file(target)
        if actual != pin:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                f"{rel} hashes to {actual}, pinned {pin}: the frozen source drifted",
            )


def check_live_corpus(root: Path, declared: Any, failures: Failures) -> None:
    """Re-count the declared corpus; a pin or tree drift is CORPUS_COUNT_DRIFT."""
    if not isinstance(declared, dict):
        return
    consultant_rel = declared.get("consultant_root")
    garant_rel = declared.get("garant_root")
    suffix = declared.get("consultant_xml_suffix", ".xml")
    for label, rel in (("consultant", consultant_rel), ("garant", garant_rel)):
        if not isinstance(rel, str) or not rel:
            _fail(failures, "CORPUS_COUNT_DRIFT", f"$.corpus_pins.{label}_root must be a path")
            continue
        path = PurePosixPath(rel)
        if path.is_absolute() or ".." in path.parts:
            _fail(failures, "UNSAFE_PATH", f"$.corpus_pins.{label}_root {rel!r} escapes the root")
            continue
        target = root / rel
        if not target.is_dir():
            _fail(
                failures,
                "CORPUS_COUNT_DRIFT",
                f"declared {label} root {rel} is not a directory",
            )
            continue
        if label == "consultant":
            actual = sum(1 for candidate in target.rglob(f"*{suffix}") if candidate.is_file())
            expected = declared.get("consultant_xml_count")
            if actual != expected:
                _fail(
                    failures,
                    "CORPUS_COUNT_DRIFT",
                    f"consultant XML count {actual} != declared {expected} under {rel}",
                )
        else:
            actual = sum(1 for candidate in target.rglob("*") if candidate.is_file())
            expected = declared.get("garant_file_count")
            if actual != expected:
                _fail(
                    failures,
                    "CORPUS_COUNT_DRIFT",
                    f"Garant file count {actual} != declared {expected} under {rel}",
                )


def seed_aggregate(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def check_live_seed(root: Path, declared: Any, failures: Failures) -> None:
    """The 180-fragment seed is frozen by count and by aggregate digest."""
    if not isinstance(declared, dict):
        return
    rel = declared.get("seed_fragment_root")
    if not isinstance(rel, str) or not rel:
        _fail(failures, "SEED_ENLARGE", "$.s03_isolation.seed_fragment_root must be a path")
        return
    path = PurePosixPath(rel)
    if path.is_absolute() or ".." in path.parts:
        _fail(
            failures, "UNSAFE_PATH", f"$.s03_isolation.seed_fragment_root {rel!r} escapes the root"
        )
        return
    seed_root = root / rel
    if not seed_root.is_dir():
        _fail(failures, "SEED_ENLARGE", f"seed fragment root {rel} is not a directory")
        return
    glob = declared.get("seed_fragment_glob", "*.txt")
    files = sorted(candidate for candidate in seed_root.glob(glob) if candidate.is_file())
    expected = declared.get("seed_fragment_count")
    if len(files) > expected:
        _fail(
            failures,
            "SEED_ENLARGE",
            f"seed carries {len(files)} fragments, declared {expected}: the seed was enlarged",
        )
    elif len(files) < expected:
        _fail(
            failures,
            "SEED_ENLARGE",
            f"seed carries {len(files)} fragments, declared {expected}: fragments are missing",
        )
    digest = seed_aggregate(files)
    if digest != declared.get("seed_aggregate_sha256"):
        _fail(
            failures,
            "SEED_ENLARGE",
            f"seed aggregate digest {digest} != pinned {declared.get('seed_aggregate_sha256')}",
        )


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


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
    except GateError as exc:
        return [(exc.diagnostic, exc.detail)]

    protocol_diagnostics: set[str] | None = None
    if not protocol_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"S07 protocol missing at {protocol_rel}")
    else:
        protocol_text = protocol_path.read_text(encoding="utf-8")
        headings = protocol_headings(protocol_text)
        for section in REQUIRED_SECTIONS:
            if section not in headings:
                _fail(failures, "MISSING_SECTION", f"S07 protocol is missing section {section!r}")
        try:
            protocol_diagnostics = parse_protocol_diagnostics(protocol_text)
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    schema: Any = None
    if not schemas_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"S07 schemas missing at {schemas_rel}")
    else:
        try:
            schema = load_json(schemas_path, "S07 schema document")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    if schema is not None:
        if not isinstance(schema, dict):
            _fail(failures, "SCHEMA_KEY_DRIFT", "the S07 schema document must be a JSON object")
            return failures
        check_document(schema, protocol_diagnostics, failures)
        check_live_frozen_sources(root, schema.get("frozen_sources"), failures)
        check_live_corpus(root, schema.get("corpus_pins"), failures)
        check_live_seed(root, schema.get("s03_isolation"), failures)
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
        f"FAIL M207_S07_SCHEMAS_GATE: {len(seen)} finding(s); the frozen S07 successor "
        "contract is not satisfied",
        file=sys.stderr,
    )
    return 1


# --------------------------------------------------------------------------- #
# Negative proof: every hostile mutation must produce its named diagnostic.
# --------------------------------------------------------------------------- #

DocMutator = Callable[[dict[str, Any]], None]
FsCase = Callable[[Path, dict[str, Any]], Failures]


def _mutate_predicate_removed(schema: dict[str, Any]) -> None:
    del schema["predicates"]["full_walk"]


def _mutate_duration_in_predicate(schema: dict[str, Any]) -> None:
    schema["predicates"]["full_walk"]["duration_ms_minimum"] = 3_600_000


def _mutate_duration_floor_flag(schema: dict[str, Any]) -> None:
    schema["predicates"]["duration_floor_is_not_acceptance"] = False


def _mutate_promotion(schema: dict[str, Any]) -> None:
    schema["promotion_contract"]["promotion"] = "pass"


def _mutate_is_gold(schema: dict[str, Any]) -> None:
    schema["promotion_contract"]["is_gold"] = True


def _mutate_diagnostics(schema: dict[str, Any]) -> None:
    schema["diagnostics"].remove("SEED_ENLARGE")


def _mutate_pin(schema: dict[str, Any]) -> None:
    name = sorted(schema["frozen_sources"])[0]
    schema["frozen_sources"][name]["sha256"] = "0" * 64


def _mutate_seed(schema: dict[str, Any]) -> None:
    schema["s03_isolation"]["seed_fragment_count"] = 181


def _mutate_corpus(schema: dict[str, Any]) -> None:
    schema["corpus_pins"]["consultant_xml_count"] = 1


def _mutate_outcomes(schema: dict[str, Any]) -> None:
    schema["predicates"]["outcomes"].remove("timeout")


def _mutate_receipt_schema(schema: dict[str, Any]) -> None:
    schema["receipt_schema_id"] = "m207-s07-c4-operational-receipt/v1"


def _mutate_marker(schema: dict[str, Any]) -> None:
    schema["marker_contract"]["marker"] = "M207_S07_VERIFY_OK"


def _mutate_root_key(schema: dict[str, Any]) -> None:
    schema["extra_root_key"] = "x"


def _mutate_sidecar_class(schema: dict[str, Any]) -> None:
    schema["failure_policy"]["class_allowlist"].append("retry")


DOC_SELFTEST_CASES: tuple[tuple[str, str, DocMutator], ...] = (
    ("full-walk-removed", "PREDICATE_CONTRADICTION", _mutate_predicate_removed),
    ("duration-in-predicate", "DURATION_FLOOR_AS_ACCEPTANCE", _mutate_duration_in_predicate),
    ("duration-floor-flag", "DURATION_FLOOR_AS_ACCEPTANCE", _mutate_duration_floor_flag),
    ("promotion-pass", "PROMOTION_CLAIM", _mutate_promotion),
    ("is-gold", "GOLD_CLAIM", _mutate_is_gold),
    ("diagnostic-removed", "PROTOCOL_DIAGNOSTIC_DRIFT", _mutate_diagnostics),
    ("pin-swapped", "C4_RECEIPT_DRIFT", _mutate_pin),
    ("seed-raised", "SEED_ENLARGE", _mutate_seed),
    ("corpus-pin", "CORPUS_COUNT_DRIFT", _mutate_corpus),
    ("outcome-removed", "TERMINAL_OUTCOME_DRIFT", _mutate_outcomes),
    ("receipt-schema-id", "SCHEMA_VERSION_DRIFT", _mutate_receipt_schema),
    ("marker-moved", "MARKER_CONTRACT_DRIFT", _mutate_marker),
    ("extra-root-key", "SCHEMA_KEY_DRIFT", _mutate_root_key),
    ("sidecar-class-opened", "SCHEMA_KEY_DRIFT", _mutate_sidecar_class),
)


def _fs_frozen_drift(root: Path, schema: dict[str, Any]) -> Failures:
    """Plant a byte-mutated frozen source in a temp tree; the live hash must refuse it."""
    failures: Failures = []
    with tempfile.TemporaryDirectory(prefix="m207-s07-drift-") as tmp:
        tmp_root = Path(tmp)
        for entry in EXPECTED_FROZEN_SOURCES.values():
            source = root / entry["path"]
            if not source.is_file():
                return [("MISSING_ARTIFACT", f"selftest could not read {entry['path']}")]
            target = tmp_root / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        name = sorted(EXPECTED_FROZEN_SOURCES)[0]
        mutated = tmp_root / EXPECTED_FROZEN_SOURCES[name]["path"]
        mutated.write_bytes(mutated.read_bytes() + b" ")
        check_live_frozen_sources(tmp_root, schema.get("frozen_sources"), failures)
    return failures


def _fs_corpus_drift(root: Path, schema: dict[str, Any]) -> Failures:
    failures: Failures = []
    pins = copy.deepcopy(schema.get("corpus_pins"))
    pins["consultant_xml_count"] = 1
    check_live_corpus(root, pins, failures)
    return failures


def _fs_seed_drift(root: Path, schema: dict[str, Any]) -> Failures:
    failures: Failures = []
    isolation = copy.deepcopy(schema.get("s03_isolation"))
    isolation["seed_fragment_count"] = 1
    check_live_seed(root, isolation, failures)
    return failures


def _fs_protocol_diagnostic_missing(root: Path, schema: dict[str, Any]) -> Failures:
    """Drop one code from the protocol marker block; the doc-code sets must disagree."""
    failures: Failures = []
    text = (root / PROTOCOL_REL).read_text(encoding="utf-8")
    mutated = text.replace("SEED_ENLARGE\n", "", 1)
    if mutated == text:
        return [("MISSING_ARTIFACT", "selftest could not mutate the protocol marker block")]
    check_document(schema, parse_protocol_diagnostics(mutated), failures)
    return failures


def _fs_missing_protocol(root: Path, schema: dict[str, Any]) -> Failures:
    del schema
    with tempfile.TemporaryDirectory(prefix="m207-s07-missing-") as tmp:
        return collect_failures(Path(tmp), PROTOCOL_REL, SCHEMAS_REL)


def _fs_unsafe_path(root: Path, schema: dict[str, Any]) -> Failures:
    del schema
    failures: Failures = []
    try:
        resolve_artifact(root, "../escape.md", "protocol", suffix=".md", prefix=ANNOTATION_PREFIX)
    except GateError as exc:
        failures.append((exc.diagnostic, exc.detail))
    return failures


FS_SELFTEST_CASES: tuple[tuple[str, str, FsCase], ...] = (
    ("live-frozen-drift", "C4_RECEIPT_DRIFT", _fs_frozen_drift),
    ("live-corpus-count", "CORPUS_COUNT_DRIFT", _fs_corpus_drift),
    ("live-seed-count", "SEED_ENLARGE", _fs_seed_drift),
    ("protocol-diagnostic-missing", "PROTOCOL_DIAGNOSTIC_DRIFT", _fs_protocol_diagnostic_missing),
    ("missing-protocol", "MISSING_ARTIFACT", _fs_missing_protocol),
    ("unsafe-path", "UNSAFE_PATH", _fs_unsafe_path),
)


def _selftest_baselines(
    root: Path, protocol_rel: str, schemas_rel: str
) -> tuple[dict[str, Any], set[str]] | None:
    protocol_path = root / protocol_rel
    schemas_path = root / schemas_rel
    if not protocol_path.is_file() or not schemas_path.is_file():
        return None
    protocol_diagnostics = parse_protocol_diagnostics(protocol_path.read_text(encoding="utf-8"))
    schema = load_json(schemas_path, "S07 schema document")
    if not isinstance(schema, dict):
        return None
    return schema, protocol_diagnostics


def run_selftest(root: Path, protocol_rel: str, schemas_rel: str) -> int:
    try:
        baselines = _selftest_baselines(root, protocol_rel, schemas_rel)
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return 1
    if baselines is None:
        print("FAIL SELFTEST_BASELINE: S07 protocol or schemas missing", file=sys.stderr)
        return 1
    schema0, protocol_diagnostics = baselines

    problems: list[str] = []
    baseline = collect_failures(root, protocol_rel, schemas_rel)
    if baseline:
        problems.append(
            "selftest baseline is not green: "
            + ", ".join(sorted({diagnostic for diagnostic, _ in baseline}))
        )

    for name, diagnostic, mutator in DOC_SELFTEST_CASES:
        schema = copy.deepcopy(schema0)
        mutator(schema)
        failures: Failures = []
        check_document(schema, protocol_diagnostics, failures)
        seen = {diag for diag, _ in failures}
        if diagnostic not in seen:
            problems.append(
                f"hostile case {name!r} did not raise {diagnostic} (saw {sorted(seen) or 'nothing'})"
            )

    for name, diagnostic, runner in FS_SELFTEST_CASES:
        schema = copy.deepcopy(schema0)
        seen = {diag for diag, _ in runner(root, schema)}
        if diagnostic not in seen:
            problems.append(
                f"hostile case {name!r} did not raise {diagnostic} (saw {sorted(seen) or 'nothing'})"
            )

    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(
            f"FAIL M207_S07_SCHEMAS_SELFTEST: {len(problems)} hostile path(s) not proven",
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
        help="'check' verifies the frozen contract read-only; 'selftest' additionally proves "
        "the hostile paths",
    )
    parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="repository root the artifact paths are resolved against (default: the cwd)",
    )
    parser.add_argument("--protocol", default=PROTOCOL_REL, help="protocol path relative to root")
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="schema path relative to root")
    args = parser.parse_args(argv)
    root = Path(args.repo_root)
    if not root.is_dir():
        print(f"FAIL MISSING_ARTIFACT: root {root} is not a directory", file=sys.stderr)
        return 1
    try:
        if args.mode == "selftest":
            return run_selftest(root, args.protocol, args.schemas)
        return report(collect_failures(root, args.protocol, args.schemas), MARKER)
    except Exception as exc:  # noqa: BLE001 - fail-closed: never a bare traceback
        print("GATE_INTERNAL_ERROR")
        print(f"FAIL GATE_INTERNAL_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
