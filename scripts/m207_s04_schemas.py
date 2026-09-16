#!/usr/bin/env python3
"""Frozen C4 operational contract and fail-closed gate for the M207 S04 contour (T01).

This is an offline, fail-closed evidence gate.  It binds the S04 operational contract to
the artifacts it rests on:

* ``prd/annotation/m207-s04-c4-protocol.md`` -- the frozen protocol, including the
  machine-readable contract block parsed by this gate;
* ``prd/annotation/m207-s04-schemas.json`` -- the closed S04 schema document;
* ``prd/architecture/npa-acceptance-contract.yaml`` -- the runtime contract the C4 walk
  runs against (``c4-live-check``, mode ``runtime``);
* ``prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json`` -- the pinned prior
  non-pass attempt (D444);
* ``prd/migration/rust-evidence/m207-s03-battery.json`` -- the current S03 integrity
  battery, which must still record ``human_pilot_performed = false``;
* ``prd/annotation/m207-s03-schemas.json`` -- the frozen S03 evaluation contract;
* ``prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json`` -- 40 documents /
  180 fragments of the frozen seed;
* ``crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json`` -- the rule-seed sidecar
  refused as an evaluation input.

The gate proves, against the frozen sources rather than against prose:

* the receipt shape is exactly ``m204-s06-c4-operational-receipt/v1`` reused verbatim --
  root closure, nested closure, required fields, binary/toolchain/source/contract pins,
  corpus counts, duration, budget and log hashes;
* ``budget_seconds`` is pinned at ``>= 3600`` and is a ceiling, never an achievement;
* a terminal outcome is published as-is: ``timeout`` / ``nonzero`` / ``launch_error`` are
  non-pass, ``complete`` cannot be minted from a rewrite, and the M204/S06 timeout receipt
  stays a prior non-pass;
* no surface promotes a label, requests a classification, sets a threshold or claims gold,
  human acceptance or model invocation;
* the live corpus is re-counted (43785 consultant XML, 12 Garant files); a drift of the
  declared pin or of the tree is ``CORPUS_COUNT_DRIFT``;
* the S03 evaluation report stays absent, the S03 battery keeps
  ``human_pilot_performed = false``, no S03 rate is imported and the 180-fragment seed is
  frozen by count and by aggregate digest;
* no tracked ``crates/`` file references the offline M207 harness;
* the diagnostic vocabulary, the non-claims and the lifecycle markers are present and
  exact.

No walk is launched and no receipt is produced here: this gate only reads the frozen
artifacts and re-counts the declared corpus, and rejects drift.  ``check`` prints exactly
the marker ``M207_S04_SCHEMAS_OK``; ``selftest`` additionally proves the named negative
paths and prints ``M207_S04_SCHEMAS_SELFTEST_OK``.  Every failure is a non-zero exit with a
named diagnostic on stderr.
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

MARKER = "M207_S04_SCHEMAS_OK"
SELFTEST_MARKER = "M207_S04_SCHEMAS_SELFTEST_OK"

SCHEMA_ID = "m207-s04-c4-schemas/v1"
SCHEMA_VERSION = 1
PROTOCOL_ID = "m207-s04-c4-protocol/v1"
RECEIPT_SCHEMA_ID = "m204-s06-c4-operational-receipt/v1"
RECEIPT_SCHEMA_REUSED = True
RECEIPT_REBUILD_FORBIDDEN = True
DIGEST_FORMAT = "bare lowercase hex sha256, no algorithm prefix"

PROTOCOL_REL = "prd/annotation/m207-s04-c4-protocol.md"
SCHEMAS_REL = "prd/annotation/m207-s04-schemas.json"
ANNOTATION_PREFIX = "prd/annotation/"
CONTRACT_HEADING = "Machine-readable protocol contract"
BOUNDED_TAG = "[bounded]"

BATTERY_SCHEMA_ID = "m207-s04-battery/v1"
S03_BATTERY_SCHEMA_ID = "m207-s03-battery/v1"

REQUIRED_SECTIONS = (
    "1. Scope, framing and ownership",
    "2. Frozen inputs, pins and admissibility",
    "3. C4 receipt contract: process facts only",
    "4. Terminal outcomes: non-pass is published as-is",
    "5. Corpus pins and reproducible inputs",
    "6. Promotion contract: nothing is promoted",
    "7. S03 isolation: rates stay not-measured",
    "8. Requirement bindings and HOLD pins",
    "9. Fail-closed diagnostics",
    "10. Lifecycle markers and non-claims",
    "11. Boundaries",
    "Machine-readable protocol contract",
)

SCHEMA_ROOT_KEYS = (
    "schema",
    "schema_version",
    "protocol",
    "receipt_schema_id",
    "receipt_schema_reused_verbatim",
    "digest_format",
    "frozen_sources",
    "prior_non_pass_pin",
    "receipt_contract",
    "corpus_pins",
    "promotion_contract",
    "s03_isolation",
    "requirement_bindings",
    "integrity_marker",
    "vocabularies",
    "diagnostics",
    "schemas",
    "non_claims",
    "lifecycle",
)

CONTRACT_ROOT_KEYS = (
    "protocol_id",
    "schema_id",
    "receipt_schema_id",
    "receipt_schema_reused_verbatim",
    "frozen_sources",
    "prior_non_pass_pin",
    "receipt_contract",
    "corpus_pins",
    "promotion_contract",
    "s03_isolation",
    "requirement_bindings",
    "integrity_marker",
    "diagnostics",
    "required_sections",
    "non_claims",
    "lifecycle",
)

# Blocks the protocol contract and the schema document must agree on, field by field.
SHARED_BLOCKS = (
    "receipt_schema_id",
    "receipt_schema_reused_verbatim",
    "frozen_sources",
    "prior_non_pass_pin",
    "receipt_contract",
    "corpus_pins",
    "promotion_contract",
    "s03_isolation",
    "requirement_bindings",
    "integrity_marker",
    "diagnostics",
    "non_claims",
    "lifecycle",
)

WALL_CLOCK_KEY_TOKENS = ("duration_ms", "elapsed_ms", "generated_at", "wall_clock")

# The receipt *is* a process record, so its wall-clock fields are the evidence it exists to
# carry; the battery is a byte-stable projection, so it may carry none.  One rule per
# artifact class: the wall-clock scan skips these two subtrees and applies everywhere else.
WALL_CLOCK_SKIP_PREFIXES = ("$.receipt_contract", "$.schemas.receipt")

EXPECTED_BATTERY_FORBIDDEN_KEYS = list(WALL_CLOCK_KEY_TOKENS)

TEXT_SUFFIXES = frozenset(
    {".rs", ".toml", ".md", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".lock", ".py", ".sql"}
)
SKIP_DIR_TOKENS = frozenset({"target", ".git", "__pycache__", ".tox", "node_modules", ".venv"})

FROZEN_JSON = r"""
{
  "frozen_sources": {
    "npa_acceptance_contract": {
      "path": "prd/architecture/npa-acceptance-contract.yaml",
      "sha256": "34e8a38a4bd7619d35e8bc2c1294e3a9bc77179b3385d9b5d9161157220d51e3"
    },
    "m204_s06_c4_operational_receipt": {
      "path": "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
      "sha256": "04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c"
    },
    "m207_s03_battery": {
      "path": "prd/migration/rust-evidence/m207-s03-battery.json",
      "sha256": "76b9a78e3e83772be3ca3e46b83a89b3b3baaf690ffe6aa0c72f77aa6d56b533"
    },
    "m207_s03_schemas": {
      "path": "prd/annotation/m207-s03-schemas.json",
      "sha256": "34d874e59b16e356e5658b7eec45d3fef01a4342592728f10f122b0126903456"
    },
    "m199_s01_sample_manifest": {
      "path": "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json",
      "sha256": "134751f49db1858329248be1857ada669097f1860609090028c7b5af8975574f"
    },
    "m199_seed_sidecar": {
      "path": "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json",
      "sha256": "b88e5af14bcc9496c4d35627afda058d58956f459106c147f1cc7959a6930f28"
    }
  },
  "prior_non_pass_pin": {
    "path": "prd/migration/rust-evidence/m204-s06-c4-operational-receipt.json",
    "sha256": "04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c",
    "attempt_id_pin": "full-walk-timeout-001",
    "terminal_outcome_pin": "timeout",
    "terminal_signal_pin": "SIGTERM",
    "timeout_flag_pin": true,
    "operational_acceptance_pin": "non-pass",
    "may_be_rewritten": false,
    "diagnostic": "C4_TIMEOUT_AS_PASS"
  },
  "receipt_contract": {
    "schema_id": "m204-s06-c4-operational-receipt/v1",
    "schema_reused_verbatim": true,
    "binary_path_pin": "target/release/npa-contour-diagnostics",
    "receipt_path": "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json",
    "attempt_log_dir": "prd/migration/rust-evidence/m207-s04-c4-attempts",
    "attempt_log_files": [
      "stdout.log",
      "stderr.log"
    ],
    "new_attempt_policy": "a later attempt is a new receipt under a new attempt_id; an existing receipt and its logs are never overwritten in place",
    "closed_keys": [
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
      "non_claims"
    ],
    "required_keys": [
      "schema",
      "attempt_id",
      "immutable_attempt_identity",
      "argv",
      "binary",
      "build_inputs",
      "toolchain",
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
      "non_claims"
    ],
    "nested_closed_keys": {
      "immutable_attempt_identity": [
        "attempt_id",
        "argv_sha256"
      ],
      "binary": [
        "path",
        "sha256"
      ],
      "build_inputs": [
        "binary_sha256",
        "contract_sha256",
        "parser_source_sha256"
      ],
      "toolchain": [
        "rustc",
        "cargo",
        "commands_exit_code"
      ],
      "contract": [
        "path",
        "sha256",
        "version",
        "check_id",
        "mode"
      ],
      "corpus": [
        "consultant_xml_count",
        "consultant_root",
        "garant_file_count",
        "garant_root"
      ],
      "observed_output": [
        "stdout_sha256",
        "inventory_digest"
      ],
      "c4_binding": [
        "profile",
        "limit",
        "jobs",
        "inventory_scope",
        "baseline_sha256"
      ],
      "terminal": [
        "outcome",
        "exit_code",
        "signal",
        "timeout"
      ],
      "logs": [
        "stdout",
        "stderr",
        "stdout_sha256",
        "stderr_sha256",
        "inventory_digest"
      ],
      "claims": [
        "operational_acceptance",
        "receipt_is_runtime_attempt"
      ]
    },
    "identity_fields": [
      "attempt_id",
      "argv_sha256"
    ],
    "argv_sha256_basis": "sha256 over json.dumps(argv, separators=(',', ':')), reused verbatim from the M204/S06 emitter",
    "argv_required_flags": [
      "--root",
      "--garant-root",
      "--profile",
      "--jobs",
      "--acceptance-contract",
      "--source-revision"
    ],
    "argv_forbidden_flags": [
      "--limit"
    ],
    "profile_pin": "contour",
    "jobs_pin": 0,
    "limit_pin": null,
    "contract_version_pin": "npa-acceptance-contract/v1",
    "contract_check_id_pin": "c4-live-check",
    "contract_mode_pin": "runtime",
    "binary_hash_fields": [
      "binary.sha256",
      "build_inputs.binary_sha256"
    ],
    "binary_hash_fields_must_be_equal": true,
    "contract_hash_fields": [
      "contract.sha256",
      "build_inputs.contract_sha256"
    ],
    "contract_hash_fields_must_be_equal": true,
    "source_revision_basis": "caller pin recorded by the caller; never a GSD aggregate and never a sha256 digest",
    "source_revision_digest_forbidden": true,
    "log_path_fields": [
      "logs.stdout",
      "logs.stderr"
    ],
    "log_hash_fields": [
      "logs.stdout_sha256",
      "logs.stderr_sha256"
    ],
    "duration_field": "duration_ms",
    "budget_field": "budget_seconds",
    "budget_seconds_minimum": 3600,
    "budget_is_a_ceiling_not_an_achievement": true,
    "terminal_closed_keys": [
      "outcome",
      "exit_code",
      "signal",
      "timeout"
    ],
    "terminal_required_keys": [
      "outcome",
      "exit_code",
      "signal",
      "timeout"
    ],
    "outcome_values": [
      "complete",
      "nonzero",
      "timeout",
      "launch_error",
      "not-run"
    ],
    "accepted_outcomes": [
      "complete"
    ],
    "non_pass_outcomes": [
      "nonzero",
      "timeout",
      "launch_error",
      "not-run"
    ],
    "acceptance_values": [
      "pass",
      "non-pass"
    ],
    "acceptance_rule": "operational_acceptance is pass only when terminal.outcome is complete, terminal.exit_code is 0 and duration_ms >= budget_seconds * 1000; every other combination is non-pass",
    "acceptance_rule_source": "m204-s06-c4-operational-receipt/v1, reused verbatim; S04 does not relax it",
    "timeout_is_never_accepted": true,
    "outcome_rewrite_forbidden": true,
    "process_group_kill": {
      "signal": "SIGTERM",
      "scope": "process group of the launched walk",
      "timeout_flag": true,
      "exit_code_on_timeout": null
    },
    "immutable_attempt_identity": true,
    "attempt_identity_rebuild_forbidden": true,
    "receipt_rebuild_forbidden": true
  },
  "corpus_pins": {
    "consultant_root": "consru_export/consru_export/exports",
    "consultant_root_is_declared_not_derived": true,
    "consultant_xml_suffix": ".xml",
    "consultant_xml_count": 43785,
    "garant_root": "law-source/garant",
    "garant_file_count": 12,
    "count_basis": "recursive file count under the declared root, identical to the M204/S06 basis",
    "count_is_a_corpus_pin_not_promotion_evidence": true,
    "drift_diagnostic": "CORPUS_COUNT_DRIFT"
  },
  "promotion_contract": {
    "promotion": "none",
    "classification": "not-authorized",
    "threshold": null,
    "human_acceptance": null,
    "is_gold": false,
    "model_invoked": false,
    "legal_claim": "forbidden",
    "n2_claim": "forbidden",
    "rate_publication": "forbidden",
    "measurement_status_publication": "forbidden",
    "corpus_complete_is_not_acceptance": true,
    "integrity_marker_is_not_acceptance": true
  },
  "s03_isolation": {
    "evaluation_report_path": "prd/migration/rust-evidence/m207-s03-evaluation-report.json",
    "evaluation_report_must_be_absent": true,
    "s03_battery_path": "prd/migration/rust-evidence/m207-s03-battery.json",
    "s03_battery_human_pilot_performed_required": false,
    "s03_rates_required_status": "not-measured",
    "rate_import_forbidden": true,
    "seed_fragment_root": "crates/ln-decode/tests/fixtures/npa-lawref",
    "seed_fragment_glob": "*.txt",
    "seed_fragment_count": 180,
    "seed_aggregate_sha256": "50b48668cba5b89d75af0604a78004404310e36377679984273fa0a883053c9d",
    "seed_aggregate_basis": "sha256 over sorted lines '<file name>\\0<file sha256>\\n'",
    "seed_sidecar_path": "crates/ln-decode/tests/fixtures/npa-lawref/lawref_seed.json",
    "seed_sidecar_sha256": "b88e5af14bcc9496c4d35627afda058d58956f459106c147f1cc7959a6930f28",
    "crates_reference_forbidden": true,
    "crates_reference_patterns": [
      "m207-s03",
      "m207_s03",
      "m207-s04",
      "m207_s04"
    ],
    "crates_reference_scope": "every tracked file under crates/, excluding target/ and .git/",
    "seed_enlarge_diagnostic": "SEED_ENLARGED",
    "seed_drift_diagnostic": "SEED_DRIFT"
  },
  "requirement_bindings": {
    "supporting_ids": [
      "R038",
      "R063",
      "R064",
      "R071",
      "R077"
    ],
    "hold_pin_ids": [
      "R035",
      "R070"
    ],
    "hold_pin_commands": [
      "cargo test -p ln-kb-ontology --offline --test r035_proof_gate",
      "cargo test -p ln-temporal --offline --test r070_proof_gate",
      "cargo test -p ln-decode --offline --test npa_lawref_sample_contract"
    ],
    "validated_ids": [],
    "invalidated_ids": [],
    "status_effect": "unchanged",
    "requirement_closure_forbidden": true,
    "evaluation_report_forbidden": true,
    "decisions_reaffirmed": [
      "D444",
      "D466",
      "D487"
    ],
    "decisions_untouched": [
      "D388",
      "D416",
      "D430",
      "D495"
    ]
  },
  "integrity_marker": {
    "marker": "M207_S04_VERIFY_OK",
    "meaning": "the S04 integrity battery ran and every check passed",
    "does_not_mean": [
      "C4 pass",
      "operational acceptance",
      "independent-measured rates",
      "gold",
      "requirement closure"
    ],
    "marker_is_not_acceptance": true,
    "marker_values": [
      "M207_S04_VERIFY_OK"
    ],
    "battery_path": "prd/migration/rust-evidence/m207-s04-battery.json",
    "diagnostic": "INTEGRITY_MARKER_AS_ACCEPTANCE"
  },
  "vocabularies": {
    "promotion_values": [
      "none"
    ],
    "classification_values": [
      "not-authorized"
    ],
    "acceptance_values": [
      "pass",
      "non-pass"
    ],
    "outcome_values": [
      "complete",
      "nonzero",
      "timeout",
      "launch_error",
      "not-run"
    ],
    "accepted_outcomes": [
      "complete"
    ],
    "non_pass_outcomes": [
      "nonzero",
      "timeout",
      "launch_error",
      "not-run"
    ],
    "profile_values": [
      "contour"
    ],
    "contract_version_values": [
      "npa-acceptance-contract/v1"
    ],
    "contract_check_id_values": [
      "c4-live-check"
    ],
    "contract_mode_values": [
      "runtime"
    ],
    "battery_status_values": [
      "pass",
      "fail"
    ],
    "marker_values": [
      "M207_S04_VERIFY_OK"
    ],
    "digest_format": "bare lowercase hex sha256, no algorithm prefix",
    "requirement_status_effect_values": [
      "unchanged"
    ]
  },
  "diagnostics": [
    "PROMOTION_CLAIM",
    "GOLD_CLAIM",
    "IS_GOLD_CLAIM",
    "THRESHOLD_REQUESTED",
    "CLASSIFICATION_REQUESTED",
    "MODEL_INVOKED",
    "AUTHORITY_CLAIM",
    "LEAK_FORBIDDEN_KEY",
    "C4_RECEIPT_MISSING",
    "C4_RECEIPT_DRIFT",
    "C4_TIMEOUT_AS_PASS",
    "INTEGRITY_MARKER_AS_ACCEPTANCE",
    "BUDGET_BELOW_MINIMUM",
    "TERMINAL_OUTCOME_DRIFT",
    "ARGV_PIN_DRIFT",
    "CORPUS_COUNT_DRIFT",
    "LOG_HASH_MISSING",
    "ATTEMPT_LOG_MISSING",
    "IMMUTABLE_IDENTITY_MISSING",
    "BINARY_HASH_MISSING",
    "TOOLCHAIN_PIN_MISSING",
    "SOURCE_REVISION_MISSING",
    "DURATION_MISSING",
    "PROXY_INPUT_REFUSED",
    "REPORT_WITHOUT_HUMAN_DATA",
    "S03_RATE_IMPORTED",
    "S03_BATTERY_PILOT_PERFORMED",
    "S03_REGRESSION_FAILED",
    "SEED_ENLARGED",
    "SEED_DRIFT",
    "HOLD_PIN_FAILED",
    "REQUIREMENT_STATUS_CLAIM",
    "BATTERY_STALE",
    "BATTERY_WALLCLOCK_FORBIDDEN",
    "EMPTY_SUITE",
    "SUBCLI_FAILURE",
    "HOSTILE_CASE_MISSING",
    "MACHINERY_MARKER_MISSING",
    "FROZEN_SOURCE_DRIFT",
    "MISSING_ARTIFACT",
    "MISSING_SECTION",
    "MISSING_NON_CLAIM",
    "MISSING_LIFECYCLE_MARKER",
    "MISSING_SCHEMA",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "DUPLICATE_JSON_KEY",
    "DIAGNOSTIC_TABLE_DRIFT",
    "VOCABULARY_DRIFT",
    "UNSAFE_PATH"
  ],
  "non_claims": [
    "not gold: no S04 artifact, receipt field or terminal outcome is a gold label",
    "not a promotion: promotion stays none, classification stays not-authorized and threshold stays null",
    "not a threshold: no rate threshold, pass/fail cut-off or accept/reject decision is introduced",
    "not a classification: no classifier is fitted, no gate is selected and no D388 gate is scored",
    "not independent-measured: S04 performs no human pilot and publishes no independently measured rate",
    "not an S03 rate publication: the S03 evaluation report stays absent and no S03 aspect or stratum rate is imported or synthesized",
    "not a seed enlargement: the 180 frozen fragments, the M199 sample manifest and the rule-seed sidecar stay frozen",
    "not an R035 closure: a corpus walk is operational diagnostics, not GATE-PILOT-SCALE-READINESS",
    "not an R070 closure: a corpus walk is not edition provenance and not an amending-act chain",
    "not a requirement status change: requirement_status_effect stays unchanged and R038/R063/R064/R071/R077 stay supporting-only",
    "not human acceptance: human_acceptance stays null",
    "not system quality: operational completion is a process fact, never product, legal or N2 quality",
    "not a product surface: S04 stays an offline Python harness under scripts/ and no crates file references it",
    "not a terminal-outcome rewrite: timeout, nonzero and launch_error are published as-is and never rewritten to complete",
    "not a marker promotion: M207_S04_VERIFY_OK means the integrity battery ran, not a C4 pass",
    "not a budget achievement: budget_seconds is a ceiling, not evidence that the walk reached it",
    "not a second measurement convention: npa-quality-receipts/v1, npa-c5-* and npa-lawref-seed/v1 inputs are refused"
  ],
  "lifecycle": {
    "human_adoption": "pending",
    "runtime_stop_active": true,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged"
  }
}
"""

FENCE_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
TOKEN_SEPARATOR_RE = re.compile(r"[^A-Za-z0-9]+")

Failures = list[tuple[str, str]]


class GateError(Exception):
    """Fatal, named gate failure that stops the check immediately."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GateError("DUPLICATE_JSON_KEY", f"duplicate object key {key!r}")
        seen[key] = value
    return seen


# The frozen expectation of every block the protocol and the schema must carry.  This blob
# is the executable authority: a byte of drift in either artifact -- or between them -- stops
# the gate.  Edit the protocol block, the schema document and this blob together, or not at
# all (``selftest`` proves the hostile paths).
FROZEN: dict[str, Any] = json.loads(FROZEN_JSON, object_pairs_hook=_reject_duplicate_keys)

FROZEN_SOURCES: dict[str, Any] = FROZEN["frozen_sources"]
PRIOR_NON_PASS_PIN: dict[str, Any] = FROZEN["prior_non_pass_pin"]
RECEIPT_CONTRACT: dict[str, Any] = FROZEN["receipt_contract"]
CORPUS_PINS: dict[str, Any] = FROZEN["corpus_pins"]
PROMOTION_CONTRACT: dict[str, Any] = FROZEN["promotion_contract"]
S03_ISOLATION: dict[str, Any] = FROZEN["s03_isolation"]
REQUIREMENT_BINDINGS: dict[str, Any] = FROZEN["requirement_bindings"]
INTEGRITY_MARKER: dict[str, Any] = FROZEN["integrity_marker"]
VOCABULARIES: dict[str, Any] = FROZEN["vocabularies"]
EXPECTED_DIAGNOSTICS = tuple(FROZEN["diagnostics"])
EXPECTED_NON_CLAIMS = tuple(FROZEN["non_claims"])
REQUIRED_MARKERS: dict[str, Any] = FROZEN["lifecycle"]

EXPECTED_CLAIM_VALUES: tuple[tuple[str, Any, str], ...] = (
    ("promotion", "none", "PROMOTION_CLAIM"),
    ("classification", "not-authorized", "CLASSIFICATION_REQUESTED"),
    ("threshold", None, "THRESHOLD_REQUESTED"),
    ("human_acceptance", None, "GOLD_CLAIM"),
    ("is_gold", False, "IS_GOLD_CLAIM"),
    ("model_invoked", False, "MODEL_INVOKED"),
    ("legal_claim", "forbidden", "AUTHORITY_CLAIM"),
    ("n2_claim", "forbidden", "AUTHORITY_CLAIM"),
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
# ``is_gold`` is admitted where it is declared, and admitting it is legal only when it is
# pinned ``false``: declaring it ``true`` is the claim itself.
GUARDED_FALSE_CLAIM_KEYS = frozenset({"is_gold"})
# The deny-lists themselves legitimately hold the forbidden names.
EXEMPT_KEY_PREFIX = "forbidden_"

_MISSING = object()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def _is_bare_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


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
    if suffix and relative.suffix != suffix:
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must have suffix {suffix}")
    if prefix and not relative.as_posix().startswith(prefix):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must live under {prefix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def resolve_directory(root: Path, raw: Any, label: str, prefix: str) -> Path:
    if not isinstance(raw, str):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} must be a string path")
    return resolve_artifact(root, raw, label, suffix="", prefix=prefix)


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

    Closed key sets are JSON arrays of key names, so a forbidden name arrives as an element of
    a ``*_keys`` list at least as often as it arrives as a dict key.  Both surfaces are
    checked; the ``forbidden_*`` deny-lists are exempt because they are the deny-list itself.
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

    Scalars only: a *list* of legal values (``$.vocabularies.promotion_values``) states the
    closed set, while a scalar states the choice.  Only a scalar can claim.
    """
    rules = {name: (expected, diagnostic) for name, expected, diagnostic in EXPECTED_CLAIM_VALUES}
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                scan_forbidden_values(value, f"{pointer}.{key}", failures)
                continue
            rule = rules.get(key)
            if rule is not None and value != rule[0]:
                _fail(
                    failures,
                    rule[1],
                    f"{pointer}.{key}={value!r} claims what this slice forbids",
                )
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_forbidden_values(item, f"{pointer}[{index}]", failures)


def scan_wall_clock_keys(node: Any, pointer: str, failures: Failures) -> None:
    """Reject wall-clock keys in any closed key set outside the process receipt.

    The receipt records a process, so ``duration_ms`` / ``started_at`` / ``finished_at`` are
    lawful there.  The tracked battery must stay byte-stable, so a wall-clock field in a
    battery key list is ``BATTERY_WALLCLOCK_FORBIDDEN``.
    """
    if any(pointer.startswith(prefix) for prefix in WALL_CLOCK_SKIP_PREFIXES):
        return
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
# Frozen-block checks
# --------------------------------------------------------------------------- #


def check_frozen_sources(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "FROZEN_SOURCE_DRIFT", "$.frozen_sources must be an object")
        return
    for name, entry in declared.items():
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"$.frozen_sources.{name} must declare exactly path and sha256",
            )
        elif not _is_bare_digest(entry.get("sha256")):
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"$.frozen_sources.{name}.sha256 must be a bare sha256 digest",
            )
    if declared != FROZEN_SOURCES:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            "$.frozen_sources must pin every frozen input "
            f"(declared={sorted(declared) if isinstance(declared, dict) else declared!r})",
        )


def check_prior_non_pass_pin(declared: Any, failures: Failures) -> None:
    """The pinned M204/S06 attempt stays a prior non-pass forever."""
    if not isinstance(declared, dict):
        _fail(failures, "C4_TIMEOUT_AS_PASS", "$.prior_non_pass_pin must be an object")
        return
    if declared.get("terminal_outcome_pin") != "timeout":
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "$.prior_non_pass_pin.terminal_outcome_pin must stay the timeout non-pass",
        )
    if declared.get("operational_acceptance_pin") != "non-pass":
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "$.prior_non_pass_pin.operational_acceptance_pin must stay non-pass",
        )
    if declared.get("timeout_flag_pin") is not True:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "$.prior_non_pass_pin.timeout_flag_pin must stay true",
        )
    if declared.get("may_be_rewritten") is not False:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "$.prior_non_pass_pin.may_be_rewritten must stay false",
        )
    if not _is_bare_digest(declared.get("sha256")):
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            "$.prior_non_pass_pin.sha256 must be a bare sha256 digest",
        )
    if declared != PRIOR_NON_PASS_PIN:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "$.prior_non_pass_pin drifted from the frozen prior non-pass pin",
        )


def check_receipt_contract(declared: Any, failures: Failures) -> None:
    """The receipt shape is the M204/S06 form reused verbatim."""
    if not isinstance(declared, dict):
        _fail(failures, "C4_RECEIPT_DRIFT", "$.receipt_contract must be an object")
        return
    if (
        declared.get("schema_id") != RECEIPT_SCHEMA_ID
        or declared.get("schema_reused_verbatim") is not RECEIPT_SCHEMA_REUSED
    ):
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"$.receipt_contract must declare {RECEIPT_SCHEMA_ID!r} reused verbatim",
        )
    closed = _close_keys("$.receipt_contract.closed_keys", declared.get("closed_keys"), failures)
    required = _close_keys(
        "$.receipt_contract.required_keys", declared.get("required_keys"), failures
    )
    for key in required:
        if key not in closed:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                f"$.receipt_contract required key {key!r} is not closed",
            )
    nested = declared.get("nested_closed_keys")
    if not isinstance(nested, dict) or not nested:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "$.receipt_contract.nested_closed_keys must close every container object",
        )
    else:
        for name, keys in nested.items():
            if name not in closed:
                _fail(
                    failures,
                    "C4_RECEIPT_DRIFT",
                    f"nested closure {name!r} is not a closed receipt key",
                )
            _close_keys(f"$.receipt_contract.nested_closed_keys.{name}", keys, failures)
    if not _close_keys(
        "$.receipt_contract.identity_fields", declared.get("identity_fields"), failures
    ):
        _fail(
            failures,
            "IMMUTABLE_IDENTITY_MISSING",
            "$.receipt_contract must name the immutable attempt identity fields",
        )
    if declared.get("immutable_attempt_identity") is not True:
        _fail(
            failures,
            "IMMUTABLE_IDENTITY_MISSING",
            "$.receipt_contract.immutable_attempt_identity must be true",
        )
    if declared.get("attempt_identity_rebuild_forbidden") is not True:
        _fail(
            failures,
            "IMMUTABLE_IDENTITY_MISSING",
            "$.receipt_contract.attempt_identity_rebuild_forbidden must be true",
        )
    if declared.get("receipt_rebuild_forbidden") is not True:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "$.receipt_contract.receipt_rebuild_forbidden must be true",
        )
    if declared.get("binary_path_pin") != "target/release/npa-contour-diagnostics":
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "$.receipt_contract.binary_path_pin must be the release contour diagnostic",
        )
    for label in ("receipt_path", "attempt_log_dir"):
        value = declared.get(label)
        if not isinstance(value, str) or not value.startswith("prd/migration/rust-evidence/"):
            _fail(
                failures,
                "UNSAFE_PATH",
                f"$.receipt_contract.{label} must be a path under prd/migration/rust-evidence/",
            )
    if declared.get("attempt_log_files") != ["stdout.log", "stderr.log"]:
        _fail(
            failures,
            "ATTEMPT_LOG_MISSING",
            "$.receipt_contract.attempt_log_files must be the stdout/stderr pair",
        )
    if (
        not isinstance(declared.get("new_attempt_policy"), str)
        or not declared["new_attempt_policy"].strip()
    ):
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "$.receipt_contract.new_attempt_policy must state the no-overwrite rule",
        )
    argv_required = declared.get("argv_required_flags")
    argv_forbidden = declared.get("argv_forbidden_flags")
    if argv_forbidden != ["--limit"]:
        _fail(
            failures,
            "ARGV_PIN_DRIFT",
            "$.receipt_contract.argv_forbidden_flags must be exactly ['--limit']",
        )
    if not isinstance(argv_required, list) or "--limit" in (argv_required or []):
        _fail(
            failures,
            "ARGV_PIN_DRIFT",
            "$.receipt_contract.argv_required_flags must be a list without --limit",
        )
    if (
        declared.get("profile_pin") != "contour"
        or declared.get("jobs_pin") != 0
        or declared.get("limit_pin") is not None
    ):
        _fail(
            failures,
            "ARGV_PIN_DRIFT",
            "$.receipt_contract must pin profile=contour, jobs=0 and limit=null",
        )
    if (
        declared.get("contract_version_pin") != "npa-acceptance-contract/v1"
        or declared.get("contract_check_id_pin") != "c4-live-check"
        or declared.get("contract_mode_pin") != "runtime"
    ):
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "$.receipt_contract must pin the runtime c4-live-check contract",
        )
    if declared.get("budget_field") != "budget_seconds" or not isinstance(
        declared.get("budget_seconds_minimum"), int
    ):
        _fail(
            failures,
            "BUDGET_BELOW_MINIMUM",
            "$.receipt_contract must declare the integer budget_seconds floor",
        )
    elif declared["budget_seconds_minimum"] < 3600:
        _fail(
            failures,
            "BUDGET_BELOW_MINIMUM",
            f"$.receipt_contract.budget_seconds_minimum={declared['budget_seconds_minimum']} "
            "is below the frozen 3600s floor",
        )
    if declared.get("duration_field") != "duration_ms":
        _fail(
            failures,
            "DURATION_MISSING",
            "$.receipt_contract.duration_field must be duration_ms",
        )
    if declared.get("budget_is_a_ceiling_not_an_achievement") is not True:
        _fail(
            failures,
            "BUDGET_BELOW_MINIMUM",
            "$.receipt_contract.budget_is_a_ceiling_not_an_achievement must be true",
        )
    if (
        declared.get("outcome_values") != VOCABULARIES["outcome_values"]
        or declared.get("accepted_outcomes") != ["complete"]
        or declared.get("non_pass_outcomes") != VOCABULARIES["non_pass_outcomes"]
        or declared.get("acceptance_values") != ["pass", "non-pass"]
    ):
        _fail(
            failures,
            "TERMINAL_OUTCOME_DRIFT",
            "$.receipt_contract terminal vocabulary drifted from the frozen taxonomy",
        )
    if declared.get("terminal_closed_keys") != [
        "outcome",
        "exit_code",
        "signal",
        "timeout",
    ] or declared.get("terminal_required_keys") != ["outcome", "exit_code", "signal", "timeout"]:
        _fail(
            failures,
            "TERMINAL_OUTCOME_DRIFT",
            "$.receipt_contract terminal keys drifted from the frozen closure",
        )
    if declared.get("timeout_is_never_accepted") is not True:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "$.receipt_contract.timeout_is_never_accepted must be true",
        )
    if declared.get("outcome_rewrite_forbidden") is not True:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "$.receipt_contract.outcome_rewrite_forbidden must be true",
        )
    if not _close_keys(
        "$.receipt_contract.log_hash_fields", declared.get("log_hash_fields"), failures
    ):
        _fail(
            failures,
            "LOG_HASH_MISSING",
            "$.receipt_contract must name the log hash fields",
        )
    if not _close_keys(
        "$.receipt_contract.log_path_fields", declared.get("log_path_fields"), failures
    ):
        _fail(
            failures,
            "ATTEMPT_LOG_MISSING",
            "$.receipt_contract must name the attempt log paths",
        )
    if (
        not _close_keys(
            "$.receipt_contract.binary_hash_fields", declared.get("binary_hash_fields"), failures
        )
        or declared.get("binary_hash_fields_must_be_equal") is not True
    ):
        _fail(
            failures,
            "BINARY_HASH_MISSING",
            "$.receipt_contract must pin the binary hash fields and their equality",
        )
    if (
        not _close_keys(
            "$.receipt_contract.contract_hash_fields",
            declared.get("contract_hash_fields"),
            failures,
        )
        or declared.get("contract_hash_fields_must_be_equal") is not True
    ):
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "$.receipt_contract must pin the contract hash fields and their equality",
        )
    if declared.get("source_revision_digest_forbidden") is not True:
        _fail(
            failures,
            "SOURCE_REVISION_MISSING",
            "$.receipt_contract.source_revision_digest_forbidden must be true",
        )
    kill = declared.get("process_group_kill")
    if (
        not isinstance(kill, dict)
        or kill.get("signal") != "SIGTERM"
        or kill.get("timeout_flag") is not True
        or kill.get("exit_code_on_timeout") is not None
    ):
        _fail(
            failures,
            "TERMINAL_OUTCOME_DRIFT",
            "$.receipt_contract.process_group_kill must describe the SIGTERM group kill",
        )
    if declared != RECEIPT_CONTRACT:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "$.receipt_contract drifted from the frozen M204/S06 receipt contract",
        )


def check_corpus_pins(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "CORPUS_COUNT_DRIFT", "$.corpus_pins must be an object")
        return
    if declared.get("consultant_xml_count") != 43785:
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            f"$.corpus_pins.consultant_xml_count={declared.get('consultant_xml_count')!r} "
            "is not the frozen 43785",
        )
    if declared.get("garant_file_count") != 12:
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            f"$.corpus_pins.garant_file_count={declared.get('garant_file_count')!r} "
            "is not the frozen 12",
        )
    if declared.get("drift_diagnostic") != "CORPUS_COUNT_DRIFT":
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            "$.corpus_pins.drift_diagnostic must be CORPUS_COUNT_DRIFT",
        )
    if declared != CORPUS_PINS:
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            "$.corpus_pins drifted from the frozen corpus pins",
        )


def check_promotion_contract(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "PROMOTION_CLAIM", "$.promotion_contract must be an object")
        return
    for field, expected, diagnostic in EXPECTED_CLAIM_VALUES:
        if declared.get(field) != expected:
            _fail(
                failures,
                diagnostic,
                f"$.promotion_contract.{field}={declared.get(field)!r} must be {expected!r}",
            )
    for field in (
        "rate_publication",
        "measurement_status_publication",
    ):
        if declared.get(field) != "forbidden":
            _fail(
                failures,
                "PROMOTION_CLAIM",
                f"$.promotion_contract.{field} must be 'forbidden'",
            )
    for field in (
        "corpus_complete_is_not_acceptance",
        "integrity_marker_is_not_acceptance",
    ):
        if declared.get(field) is not True:
            _fail(
                failures,
                "INTEGRITY_MARKER_AS_ACCEPTANCE",
                f"$.promotion_contract.{field} must be true",
            )
    if declared != PROMOTION_CONTRACT:
        _fail(
            failures,
            "PROMOTION_CLAIM",
            "$.promotion_contract drifted from the frozen no-promotion contract",
        )


def check_s03_isolation(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "S03_RATE_IMPORTED", "$.s03_isolation must be an object")
        return
    if declared.get("evaluation_report_must_be_absent") is not True:
        _fail(
            failures,
            "REPORT_WITHOUT_HUMAN_DATA",
            "$.s03_isolation.evaluation_report_must_be_absent must be true",
        )
    if declared.get("s03_battery_human_pilot_performed_required") is not False:
        _fail(
            failures,
            "S03_BATTERY_PILOT_PERFORMED",
            "$.s03_isolation.s03_battery_human_pilot_performed_required must be false",
        )
    if declared.get("s03_rates_required_status") != "not-measured":
        _fail(
            failures,
            "S03_RATE_IMPORTED",
            "$.s03_isolation.s03_rates_required_status must be 'not-measured'",
        )
    if declared.get("rate_import_forbidden") is not True:
        _fail(
            failures,
            "S03_RATE_IMPORTED",
            "$.s03_isolation.rate_import_forbidden must be true",
        )
    if declared.get("seed_fragment_count") != 180:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"$.s03_isolation.seed_fragment_count={declared.get('seed_fragment_count')!r} "
            "is not the frozen 180",
        )
    if declared.get("seed_aggregate_sha256") != S03_ISOLATION["seed_aggregate_sha256"]:
        _fail(
            failures,
            "SEED_DRIFT",
            "$.s03_isolation.seed_aggregate_sha256 drifted from the frozen fragment digest",
        )
    if declared.get("seed_sidecar_sha256") != S03_ISOLATION["seed_sidecar_sha256"]:
        _fail(
            failures,
            "SEED_DRIFT",
            "$.s03_isolation.seed_sidecar_sha256 drifted from the frozen sidecar digest",
        )
    if declared.get("crates_reference_forbidden") is not True:
        _fail(
            failures,
            "S03_RATE_IMPORTED",
            "$.s03_isolation.crates_reference_forbidden must be true",
        )
    if declared.get("crates_reference_patterns") != S03_ISOLATION["crates_reference_patterns"]:
        _fail(
            failures,
            "S03_RATE_IMPORTED",
            "$.s03_isolation.crates_reference_patterns must be the frozen pattern list",
        )
    if declared != S03_ISOLATION:
        _fail(
            failures,
            "S03_RATE_IMPORTED",
            "$.s03_isolation drifted from the frozen isolation contract",
        )


def check_requirement_bindings(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "REQUIREMENT_STATUS_CLAIM", "$.requirement_bindings must be an object")
        return
    if declared.get("status_effect") != "unchanged":
        _fail(
            failures,
            "REQUIREMENT_STATUS_CLAIM",
            "$.requirement_bindings.status_effect must stay 'unchanged'",
        )
    for field in ("validated_ids", "invalidated_ids"):
        if declared.get(field) != []:
            _fail(
                failures,
                "REQUIREMENT_STATUS_CLAIM",
                f"$.requirement_bindings.{field} must stay empty; S04 validates no requirement",
            )
    if declared.get("requirement_closure_forbidden") is not True:
        _fail(
            failures,
            "REQUIREMENT_STATUS_CLAIM",
            "$.requirement_bindings.requirement_closure_forbidden must be true",
        )
    if declared.get("evaluation_report_forbidden") is not True:
        _fail(
            failures,
            "REPORT_WITHOUT_HUMAN_DATA",
            "$.requirement_bindings.evaluation_report_forbidden must be true",
        )
    commands = declared.get("hold_pin_commands")
    for command in REQUIREMENT_BINDINGS["hold_pin_commands"]:
        if not isinstance(commands, list) or command not in commands:
            _fail(
                failures,
                "HOLD_PIN_FAILED",
                f"$.requirement_bindings is missing the HOLD-pin command {command!r}",
            )
    if declared.get("supporting_ids") != REQUIREMENT_BINDINGS["supporting_ids"]:
        _fail(
            failures,
            "VOCABULARY_DRIFT",
            "$.requirement_bindings.supporting_ids drifted from the frozen supporting set",
        )
    if declared.get("hold_pin_ids") != REQUIREMENT_BINDINGS["hold_pin_ids"]:
        _fail(
            failures,
            "HOLD_PIN_FAILED",
            "$.requirement_bindings.hold_pin_ids drifted from the frozen HOLD set",
        )
    if declared != REQUIREMENT_BINDINGS:
        _fail(
            failures,
            "VOCABULARY_DRIFT",
            "$.requirement_bindings drifted from the frozen requirement bindings",
        )


def check_integrity_marker(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "INTEGRITY_MARKER_AS_ACCEPTANCE", "$.integrity_marker must be an object")
        return
    if declared.get("marker") != "M207_S04_VERIFY_OK":
        _fail(
            failures,
            "INTEGRITY_MARKER_AS_ACCEPTANCE",
            "$.integrity_marker.marker must be M207_S04_VERIFY_OK",
        )
    if declared.get("marker_is_not_acceptance") is not True:
        _fail(
            failures,
            "INTEGRITY_MARKER_AS_ACCEPTANCE",
            "$.integrity_marker.marker_is_not_acceptance must be true",
        )
    if declared != INTEGRITY_MARKER:
        _fail(
            failures,
            "INTEGRITY_MARKER_AS_ACCEPTANCE",
            "$.integrity_marker drifted from the frozen integrity-marker contract",
        )


def check_vocabularies(declared: Any, failures: Failures) -> None:
    if not isinstance(declared, dict):
        _fail(failures, "VOCABULARY_DRIFT", "$.vocabularies must be an object")
        return
    if declared.get("promotion_values") != ["none"]:
        _fail(failures, "PROMOTION_CLAIM", "$.vocabularies.promotion_values must be ['none']")
    if declared.get("classification_values") != ["not-authorized"]:
        _fail(
            failures,
            "CLASSIFICATION_REQUESTED",
            "$.vocabularies.classification_values must be ['not-authorized']",
        )
    if declared.get("digest_format") != DIGEST_FORMAT:
        _fail(failures, "VOCABULARY_DRIFT", "$.vocabularies.digest_format drifted")
    if declared != VOCABULARIES:
        _fail(failures, "VOCABULARY_DRIFT", "$.vocabularies drifted from the frozen vocabularies")


def check_diagnostics(declared: Any, failures: Failures) -> None:
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


def check_sub_schemas(schema: Any, failures: Failures) -> None:
    subschemas = schema.get("schemas") if isinstance(schema, dict) else None
    if not isinstance(subschemas, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "$.schemas must be an object")
        return
    expected_names = {"receipt", "battery"}
    if set(subschemas) != expected_names:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            "$.schemas keys differ: extra="
            f"{sorted(set(subschemas) - expected_names)} missing="
            f"{sorted(expected_names - set(subschemas))}",
        )
        return
    receipt = subschemas.get("receipt")
    if not isinstance(receipt, dict):
        _fail(failures, "MISSING_SCHEMA", "$.schemas.receipt must be an object")
    else:
        if receipt.get("schema_id") != RECEIPT_SCHEMA_ID:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                f"$.schemas.receipt.schema_id={receipt.get('schema_id')!r} != "
                f"{RECEIPT_SCHEMA_ID!r}",
            )
        closed = _check_closed_pair("$.schemas.receipt", receipt, failures)
        if closed and list(closed) != RECEIPT_CONTRACT["closed_keys"]:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                "$.schemas.receipt closed keys disagree with $.receipt_contract.closed_keys",
            )
        required = receipt.get("required_keys")
        if isinstance(required, list) and required != RECEIPT_CONTRACT["required_keys"]:
            _fail(
                failures,
                "C4_RECEIPT_DRIFT",
                "$.schemas.receipt required keys disagree with $.receipt_contract.required_keys",
            )
    battery = subschemas.get("battery")
    if not isinstance(battery, dict):
        _fail(failures, "MISSING_SCHEMA", "$.schemas.battery must be an object")
    else:
        if battery.get("schema_id") != BATTERY_SCHEMA_ID:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"$.schemas.battery.schema_id={battery.get('schema_id')!r} != "
                f"{BATTERY_SCHEMA_ID!r}",
            )
        _check_closed_pair("$.schemas.battery", battery, failures)
        for pair in (
            ("check_closed_keys", "check_required_keys"),
            ("pins_closed_keys", "pins_closed_keys"),
        ):
            _close_keys(f"$.schemas.battery.{pair[0]}", battery.get(pair[0]), failures)
            if pair[1] != pair[0]:
                _close_keys(f"$.schemas.battery.{pair[1]}", battery.get(pair[1]), failures)
        check_closed = battery.get("check_closed_keys") or []
        for key in ("check_id", "command", "diagnostic", "exit_code", "status"):
            if key not in check_closed:
                _fail(
                    failures,
                    "SCHEMA_KEY_DRIFT",
                    f"$.schemas.battery.check_closed_keys must declare {key!r}",
                )
        forbidden = battery.get("forbidden_battery_keys")
        if forbidden != EXPECTED_BATTERY_FORBIDDEN_KEYS:
            _fail(
                failures,
                "BATTERY_WALLCLOCK_FORBIDDEN",
                f"$.schemas.battery.forbidden_battery_keys={forbidden!r} must be the wall-clock set",
            )
        if battery.get("human_pilot_performed_required") is not False:
            _fail(
                failures,
                "S03_BATTERY_PILOT_PERFORMED",
                "$.schemas.battery.human_pilot_performed_required must be false",
            )
        if battery.get("model_invoked_required") is not False:
            _fail(
                failures,
                "MODEL_INVOKED",
                "$.schemas.battery.model_invoked_required must be false",
            )


def check_schema_document(schema: Any, failures: Failures) -> None:
    if not isinstance(schema, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "schemas document must be a JSON object")
        return
    scan_forbidden_keys(schema, "$", failures)
    scan_forbidden_values(schema, "$", failures)
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
    if schema.get("receipt_schema_id") != RECEIPT_SCHEMA_ID:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"$.receipt_schema_id={schema.get('receipt_schema_id')!r} != {RECEIPT_SCHEMA_ID!r}",
        )
    if schema.get("receipt_schema_reused_verbatim") is not RECEIPT_SCHEMA_REUSED:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "$.receipt_schema_reused_verbatim must be true",
        )
    if schema.get("digest_format") != DIGEST_FORMAT:
        _fail(failures, "VOCABULARY_DRIFT", "$.digest_format drifted from the frozen convention")
    check_frozen_sources(schema.get("frozen_sources"), failures)
    check_prior_non_pass_pin(schema.get("prior_non_pass_pin"), failures)
    check_receipt_contract(schema.get("receipt_contract"), failures)
    check_corpus_pins(schema.get("corpus_pins"), failures)
    check_promotion_contract(schema.get("promotion_contract"), failures)
    check_s03_isolation(schema.get("s03_isolation"), failures)
    check_requirement_bindings(schema.get("requirement_bindings"), failures)
    check_integrity_marker(schema.get("integrity_marker"), failures)
    check_vocabularies(schema.get("vocabularies"), failures)
    check_diagnostics(schema.get("diagnostics"), failures)
    check_sub_schemas(schema, failures)
    _check_non_claims("$.non_claims", schema.get("non_claims"), failures)
    _check_lifecycle("$.lifecycle", schema.get("lifecycle"), failures)


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
        _fail(failures, "SCHEMA_KEY_DRIFT", f"contract.schema_id must be {SCHEMA_ID!r}")
    if contract.get("receipt_schema_id") != RECEIPT_SCHEMA_ID:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"contract.receipt_schema_id must be {RECEIPT_SCHEMA_ID!r}",
        )
    if contract.get("receipt_schema_reused_verbatim") is not RECEIPT_SCHEMA_REUSED:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            "contract.receipt_schema_reused_verbatim must be true",
        )
    check_frozen_sources(contract.get("frozen_sources"), failures)
    check_prior_non_pass_pin(contract.get("prior_non_pass_pin"), failures)
    check_receipt_contract(contract.get("receipt_contract"), failures)
    check_corpus_pins(contract.get("corpus_pins"), failures)
    check_promotion_contract(contract.get("promotion_contract"), failures)
    check_s03_isolation(contract.get("s03_isolation"), failures)
    check_requirement_bindings(contract.get("requirement_bindings"), failures)
    check_integrity_marker(contract.get("integrity_marker"), failures)
    check_diagnostics(contract.get("diagnostics"), failures)
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
        for label in SHARED_BLOCKS:
            if contract.get(label) != schema.get(label):
                _fail(
                    failures,
                    "SCHEMA_KEY_DRIFT",
                    f"contract.{label} and $.{label} disagree: edit the protocol block and the "
                    "schema together",
                )


# --------------------------------------------------------------------------- #
# Live checks: the tree, the corpus and the pinned inputs
# --------------------------------------------------------------------------- #


def check_frozen_digests(root: Path, failures: Failures) -> None:
    for name, entry in sorted(FROZEN_SOURCES.items()):
        rel = entry["path"]
        try:
            path = resolve_artifact(root, rel, f"frozen source {name}", suffix="", prefix="")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        if not path.is_file():
            _fail(failures, "FROZEN_SOURCE_DRIFT", f"frozen source {name} missing at {rel}")
            continue
        digest = sha256_file(path)
        if digest != entry["sha256"]:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"frozen source {name} sha256 {digest} != pinned {entry['sha256']}",
            )


def check_live_corpus(root: Path, pins: Any, failures: Failures) -> None:
    """Re-count the declared corpus; a pin or tree drift is CORPUS_COUNT_DRIFT."""
    if not isinstance(pins, dict):
        return
    consultant_rel = pins.get("consultant_root")
    garant_rel = pins.get("garant_root")
    suffix = pins.get("consultant_xml_suffix", ".xml")
    try:
        consultant_root = resolve_directory(root, consultant_rel, "consultant root", prefix="")
        garant_root = resolve_directory(root, garant_rel, "garant root", prefix="")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    if consultant_root.is_dir():
        actual = sum(1 for path in consultant_root.rglob(f"*{suffix}") if path.is_file())
        if actual != pins.get("consultant_xml_count"):
            _fail(
                failures,
                "CORPUS_COUNT_DRIFT",
                f"consultant XML count {actual} != declared {pins.get('consultant_xml_count')} "
                f"under {consultant_rel}",
            )
    else:
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            f"declared consultant root {consultant_rel} is not a directory",
        )
    if garant_root.is_dir():
        actual_garant = sum(1 for path in garant_root.rglob("*") if path.is_file())
        if actual_garant != pins.get("garant_file_count"):
            _fail(
                failures,
                "CORPUS_COUNT_DRIFT",
                f"Garant file count {actual_garant} != declared {pins.get('garant_file_count')} "
                f"under {garant_rel}",
            )
    else:
        _fail(
            failures,
            "CORPUS_COUNT_DRIFT",
            f"declared Garant root {garant_rel} is not a directory",
        )


def seed_aggregate(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def check_live_seed(root: Path, isolation: Any, failures: Failures) -> None:
    """The 180-fragment seed is frozen by count and by aggregate digest."""
    if not isinstance(isolation, dict):
        return
    try:
        seed_root = resolve_directory(
            root, isolation.get("seed_fragment_root"), "seed fragment root", prefix=""
        )
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    if not seed_root.is_dir():
        _fail(
            failures,
            "SEED_DRIFT",
            f"seed fragment root {isolation.get('seed_fragment_root')} is not a directory",
        )
        return
    glob = isolation.get("seed_fragment_glob", "*.txt")
    files = sorted(path for path in seed_root.glob(glob) if path.is_file())
    declared = isolation.get("seed_fragment_count")
    if len(files) > declared:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"seed carries {len(files)} fragments, declared {declared}: the seed was enlarged",
        )
    elif len(files) < declared:
        _fail(
            failures,
            "SEED_DRIFT",
            f"seed carries {len(files)} fragments, declared {declared}: fragments are missing",
        )
    digest = seed_aggregate(files)
    if digest != isolation.get("seed_aggregate_sha256"):
        _fail(
            failures,
            "SEED_DRIFT",
            f"seed aggregate digest {digest} != pinned {isolation.get('seed_aggregate_sha256')}",
        )


def check_evaluation_report_absent(root: Path, isolation: Any, failures: Failures) -> None:
    """The S03 evaluation report stays absent: a report without human data is fabricated."""
    if not isinstance(isolation, dict):
        return
    rel = isolation.get("evaluation_report_path")
    try:
        path = resolve_artifact(root, rel, "s03 evaluation report", suffix=".json", prefix="")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    if path.exists():
        _fail(
            failures,
            "REPORT_WITHOUT_HUMAN_DATA",
            f"{rel} exists while the S03 battery records human_pilot_performed=false",
        )
    evidence_dir = path.parent
    if evidence_dir.is_dir():
        for candidate in sorted(evidence_dir.glob("m207-s03-evaluation-report*")):
            _fail(
                failures,
                "REPORT_WITHOUT_HUMAN_DATA",
                f"{candidate.name} exists: an S03 evaluation report is not an S04 input",
            )


def check_s03_battery_current(root: Path, failures: Failures) -> None:
    """The S03 battery stays current and keeps human_pilot_performed = false."""
    rel = S03_ISOLATION["s03_battery_path"]
    try:
        path = resolve_artifact(root, rel, "s03 battery", suffix=".json", prefix="prd/")
        battery = load_json(path, "s03 battery")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    if not isinstance(battery, dict):
        _fail(failures, "SCHEMA_PARSE_ERROR", "s03 battery must be a JSON object")
        return
    if battery.get("schema") != S03_BATTERY_SCHEMA_ID:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"s03 battery schema={battery.get('schema')!r} != {S03_BATTERY_SCHEMA_ID!r}",
        )
    if battery.get("human_pilot_performed") is not False:
        _fail(
            failures,
            "S03_BATTERY_PILOT_PERFORMED",
            "s03 battery claims the human pilot was performed; S04 must not import its rates",
        )
    if battery.get("model_invoked") is not False:
        _fail(
            failures,
            "MODEL_INVOKED",
            "s03 battery must keep model_invoked=false",
        )
    if battery.get("lifecycle") != REQUIRED_MARKERS:
        _fail(
            failures,
            "MISSING_LIFECYCLE_MARKER",
            "s03 battery lifecycle markers drifted from the frozen set",
        )


def check_prior_non_pass_receipt(root: Path, failures: Failures) -> None:
    """The pinned M204/S06 attempt stays a timeout non-pass (D444)."""
    rel = PRIOR_NON_PASS_PIN["path"]
    try:
        path = resolve_artifact(root, rel, "prior receipt", suffix=".json", prefix="prd/")
        receipt = load_json(path, "prior non-pass receipt")
    except GateError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return
    if not isinstance(receipt, dict):
        _fail(failures, "C4_TIMEOUT_AS_PASS", "prior non-pass receipt must be a JSON object")
        return
    terminal = receipt.get("terminal") if isinstance(receipt.get("terminal"), dict) else {}
    claims = receipt.get("claims") if isinstance(receipt.get("claims"), dict) else {}
    if receipt.get("schema") != RECEIPT_SCHEMA_ID:
        _fail(
            failures,
            "C4_RECEIPT_DRIFT",
            f"prior receipt schema={receipt.get('schema')!r} != {RECEIPT_SCHEMA_ID!r}",
        )
    if receipt.get("attempt_id") != PRIOR_NON_PASS_PIN["attempt_id_pin"]:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            f"prior receipt attempt_id={receipt.get('attempt_id')!r} != "
            f"{PRIOR_NON_PASS_PIN['attempt_id_pin']!r}",
        )
    if terminal.get("outcome") != PRIOR_NON_PASS_PIN["terminal_outcome_pin"]:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            f"prior receipt terminal.outcome={terminal.get('outcome')!r} != "
            f"{PRIOR_NON_PASS_PIN['terminal_outcome_pin']!r}: a timeout was rewritten",
        )
    if terminal.get("signal") != PRIOR_NON_PASS_PIN["terminal_signal_pin"]:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            f"prior receipt terminal.signal={terminal.get('signal')!r} != "
            f"{PRIOR_NON_PASS_PIN['terminal_signal_pin']!r}",
        )
    if terminal.get("timeout") is not PRIOR_NON_PASS_PIN["timeout_flag_pin"]:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            "prior receipt terminal.timeout must stay true",
        )
    if claims.get("operational_acceptance") != PRIOR_NON_PASS_PIN["operational_acceptance_pin"]:
        _fail(
            failures,
            "C4_TIMEOUT_AS_PASS",
            f"prior receipt claims.operational_acceptance="
            f"{claims.get('operational_acceptance')!r} != "
            f"{PRIOR_NON_PASS_PIN['operational_acceptance_pin']!r}",
        )


def check_crates_isolation(root: Path, isolation: Any, failures: Failures) -> None:
    """No tracked crates/ file may reference the offline M207 harness."""
    if not isinstance(isolation, dict):
        return
    patterns = isolation.get("crates_reference_patterns")
    if not isinstance(patterns, list) or not patterns:
        _fail(
            failures,
            "S03_RATE_IMPORTED",
            "$.s03_isolation.crates_reference_patterns must be a non-empty list",
        )
        return
    base = root / "crates"
    if not base.is_dir():
        _fail(failures, "MISSING_ARTIFACT", "crates/ is absent; the isolation scan cannot run")
        return
    hits: list[tuple[str, str]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        parts = path.relative_to(root).parts
        if any(part in SKIP_DIR_TOKENS for part in parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in patterns:
            if pattern in text:
                hits.append((path.relative_to(root).as_posix(), pattern))
                break
        if len(hits) >= 5:
            break
    for rel, pattern in hits:
        _fail(
            failures,
            "S03_RATE_IMPORTED",
            f"{rel} references {pattern!r}: the product runtime gains no M207 reader",
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

    check_frozen_digests(root, failures)

    headings: list[str] = []
    contract: dict[str, Any] | None = None
    if not protocol_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"S04 protocol missing at {protocol_rel}")
    else:
        protocol_text = protocol_path.read_text(encoding="utf-8")
        headings = protocol_headings(protocol_text)
        if BOUNDED_TAG not in protocol_text:
            _fail(
                failures,
                "MISSING_SECTION",
                f"S04 protocol must carry the {BOUNDED_TAG} lifecycle tag",
            )
        try:
            contract = extract_contract(protocol_text, CONTRACT_HEADING, "S04 protocol contract")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    schema: Any = None
    if not schemas_path.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"S04 schemas missing at {schemas_rel}")
    else:
        try:
            schema = load_json(schemas_path, "S04 schemas document")
        except GateError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    if schema is not None:
        check_schema_document(schema, failures)
    if contract is not None:
        check_contract(contract, schema, headings, failures)

    check_live_corpus(root, (schema or {}).get("corpus_pins"), failures)
    check_live_seed(root, (schema or {}).get("s03_isolation"), failures)
    check_evaluation_report_absent(root, (schema or {}).get("s03_isolation"), failures)
    check_crates_isolation(root, (schema or {}).get("s03_isolation"), failures)
    check_s03_battery_current(root, failures)
    check_prior_non_pass_receipt(root, failures)
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
        f"FAIL M207_S04_SCHEMAS_GATE: {len(seen)} finding(s); the frozen S04 contract "
        "is not satisfied",
        file=sys.stderr,
    )
    return 1


# --------------------------------------------------------------------------- #
# Negative proof: every hostile mutation must produce its named diagnostic.
# --------------------------------------------------------------------------- #

DocMutator = Callable[[dict[str, Any], dict[str, Any]], None]
FsCase = Callable[[Path], Failures]


def _mirror(schema: dict[str, Any], contract: dict[str, Any], label: str) -> None:
    """Keep the contract and the schema in step for a mutation aimed at the schema."""
    contract[label] = copy.deepcopy(schema[label])


def _mutate_promotion(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["promotion_contract"]["promotion"] = "adopted"
    _mirror(schema, contract, "promotion_contract")


def _mutate_classification(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["promotion_contract"]["classification"] = "authorized"
    _mirror(schema, contract, "promotion_contract")


def _mutate_threshold(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["promotion_contract"]["threshold"] = 0.9
    _mirror(schema, contract, "promotion_contract")


def _mutate_human_acceptance(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["promotion_contract"]["human_acceptance"] = "accepted"
    _mirror(schema, contract, "promotion_contract")


def _mutate_is_gold(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["promotion_contract"]["is_gold"] = True
    _mirror(schema, contract, "promotion_contract")


def _mutate_model_invoked(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["promotion_contract"]["model_invoked"] = True
    _mirror(schema, contract, "promotion_contract")


def _mutate_legal_claim(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["promotion_contract"]["legal_claim"] = "asserted"
    _mirror(schema, contract, "promotion_contract")


def _mutate_leak_key(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["promotion_contract"]["label"] = "reference"
    _mirror(schema, contract, "promotion_contract")


def _mutate_battery_wall_clock(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["schemas"]["battery"]["check_closed_keys"].append("duration_ms")


def _mutate_receipt_required(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["receipt_contract"]["required_keys"].remove("budget_seconds")
    _mirror(schema, contract, "receipt_contract")


def _mutate_budget(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["receipt_contract"]["budget_seconds_minimum"] = 60
    _mirror(schema, contract, "receipt_contract")


def _mutate_outcomes(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["receipt_contract"]["non_pass_outcomes"].append("complete")
    _mirror(schema, contract, "receipt_contract")


def _mutate_argv(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["receipt_contract"]["argv_forbidden_flags"] = []
    _mirror(schema, contract, "receipt_contract")


def _mutate_log_hashes(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["receipt_contract"]["log_hash_fields"] = []
    _mirror(schema, contract, "receipt_contract")


def _mutate_identity(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["receipt_contract"]["identity_fields"] = []
    _mirror(schema, contract, "receipt_contract")


def _mutate_receipt_schema_id(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["receipt_schema_id"] = "m207-s04-receipt/v1"
    contract["receipt_schema_id"] = "m207-s04-receipt/v1"


def _mutate_corpus_pin(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["corpus_pins"]["consultant_xml_count"] = 1
    _mirror(schema, contract, "corpus_pins")


def _mutate_evaluation_report_required(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["s03_isolation"]["evaluation_report_must_be_absent"] = False
    _mirror(schema, contract, "s03_isolation")


def _mutate_seed_count(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["s03_isolation"]["seed_fragment_count"] = 181
    _mirror(schema, contract, "s03_isolation")


def _mutate_seed_digest(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["s03_isolation"]["seed_aggregate_sha256"] = "0" * 64
    _mirror(schema, contract, "s03_isolation")


def _mutate_crates_isolation(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["s03_isolation"]["crates_reference_forbidden"] = False
    _mirror(schema, contract, "s03_isolation")


def _mutate_integrity_marker(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["integrity_marker"]["marker_is_not_acceptance"] = False
    _mirror(schema, contract, "integrity_marker")


def _mutate_prior_pin(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["prior_non_pass_pin"]["operational_acceptance_pin"] = "pass"
    _mirror(schema, contract, "prior_non_pass_pin")


def _mutate_requirement_status(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["requirement_bindings"]["status_effect"] = "validated"
    _mirror(schema, contract, "requirement_bindings")


def _mutate_hold_pin_command(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["requirement_bindings"]["hold_pin_commands"] = []
    _mirror(schema, contract, "requirement_bindings")


def _mutate_frozen_sources(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    name = sorted(schema["frozen_sources"])[0]
    schema["frozen_sources"][name]["sha256"] = "0" * 64
    _mirror(schema, contract, "frozen_sources")


def _mutate_diagnostics(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["diagnostics"].remove("C4_TIMEOUT_AS_PASS")
    _mirror(schema, contract, "diagnostics")


def _mutate_non_claim(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["non_claims"][0] = "gold: the C4 receipt is an adopted gold label"
    _mirror(schema, contract, "non_claims")


def _mutate_lifecycle(schema: dict[str, Any], contract: dict[str, Any]) -> None:
    schema["lifecycle"]["requirement_status_effect"] = "validated"
    _mirror(schema, contract, "lifecycle")


def _mutate_schema_root_key(schema: dict[str, Any], _contract: dict[str, Any]) -> None:
    schema["extra_root_key"] = "x"


def _mutate_contract_sections(_schema: dict[str, Any], contract: dict[str, Any]) -> None:
    contract["required_sections"] = ["1. Scope, framing and ownership"]


def _mutate_contract_disagreement(_schema: dict[str, Any], contract: dict[str, Any]) -> None:
    contract["corpus_pins"] = copy.deepcopy(contract["corpus_pins"])
    contract["corpus_pins"]["garant_file_count"] = 13


SELFTEST_CASES: tuple[tuple[str, str, DocMutator], ...] = (
    ("promotion", "PROMOTION_CLAIM", _mutate_promotion),
    ("classification", "CLASSIFICATION_REQUESTED", _mutate_classification),
    ("threshold", "THRESHOLD_REQUESTED", _mutate_threshold),
    ("human-acceptance", "GOLD_CLAIM", _mutate_human_acceptance),
    ("is-gold", "IS_GOLD_CLAIM", _mutate_is_gold),
    ("model-invoked", "MODEL_INVOKED", _mutate_model_invoked),
    ("legal-claim", "AUTHORITY_CLAIM", _mutate_legal_claim),
    ("predicted-answer-key", "LEAK_FORBIDDEN_KEY", _mutate_leak_key),
    ("battery-wall-clock", "BATTERY_WALLCLOCK_FORBIDDEN", _mutate_battery_wall_clock),
    ("receipt-required-key", "C4_RECEIPT_DRIFT", _mutate_receipt_required),
    ("budget-floor", "BUDGET_BELOW_MINIMUM", _mutate_budget),
    ("terminal-outcomes", "TERMINAL_OUTCOME_DRIFT", _mutate_outcomes),
    ("argv-pins", "ARGV_PIN_DRIFT", _mutate_argv),
    ("log-hashes", "LOG_HASH_MISSING", _mutate_log_hashes),
    ("immutable-identity", "IMMUTABLE_IDENTITY_MISSING", _mutate_identity),
    ("receipt-schema-id", "C4_RECEIPT_DRIFT", _mutate_receipt_schema_id),
    ("corpus-pin", "CORPUS_COUNT_DRIFT", _mutate_corpus_pin),
    ("report-required", "REPORT_WITHOUT_HUMAN_DATA", _mutate_evaluation_report_required),
    ("seed-count", "SEED_ENLARGED", _mutate_seed_count),
    ("seed-digest", "SEED_DRIFT", _mutate_seed_digest),
    ("crates-isolation", "S03_RATE_IMPORTED", _mutate_crates_isolation),
    ("integrity-marker", "INTEGRITY_MARKER_AS_ACCEPTANCE", _mutate_integrity_marker),
    ("prior-non-pass", "C4_TIMEOUT_AS_PASS", _mutate_prior_pin),
    ("requirement-status", "REQUIREMENT_STATUS_CLAIM", _mutate_requirement_status),
    ("hold-pin-command", "HOLD_PIN_FAILED", _mutate_hold_pin_command),
    ("frozen-sources", "FROZEN_SOURCE_DRIFT", _mutate_frozen_sources),
    ("diagnostics", "DIAGNOSTIC_TABLE_DRIFT", _mutate_diagnostics),
    ("non-claims", "MISSING_NON_CLAIM", _mutate_non_claim),
    ("lifecycle", "MISSING_LIFECYCLE_MARKER", _mutate_lifecycle),
    ("schema-root-key", "SCHEMA_KEY_DRIFT", _mutate_schema_root_key),
    ("required-sections", "MISSING_SECTION", _mutate_contract_sections),
    ("contract-schema-disagreement", "SCHEMA_KEY_DRIFT", _mutate_contract_disagreement),
)


def _fs_corpus_count(root: Path) -> Failures:
    failures: Failures = []
    pins = copy.deepcopy(CORPUS_PINS)
    pins["consultant_xml_count"] = 1
    check_live_corpus(root, pins, failures)
    return failures


def _fs_seed_enlarged(root: Path) -> Failures:
    failures: Failures = []
    isolation = copy.deepcopy(S03_ISOLATION)
    isolation["seed_fragment_count"] = 1
    check_live_seed(root, isolation, failures)
    return failures


def _fs_seed_digest(root: Path) -> Failures:
    failures: Failures = []
    isolation = copy.deepcopy(S03_ISOLATION)
    isolation["seed_aggregate_sha256"] = "0" * 64
    check_live_seed(root, isolation, failures)
    return failures


def _fs_crates_isolation(root: Path) -> Failures:
    failures: Failures = []
    with tempfile.TemporaryDirectory(prefix="m207-s04-crates-") as tmp:
        planted = Path(tmp) / "crates/ln-decode/src/leak.rs"
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_text("// reads m207-s03 rates\n", encoding="utf-8")
        check_crates_isolation(Path(tmp), S03_ISOLATION, failures)
    del root
    return failures


def _fs_evaluation_report(root: Path) -> Failures:
    failures: Failures = []
    with tempfile.TemporaryDirectory(prefix="m207-s04-report-") as tmp:
        planted = Path(tmp) / S03_ISOLATION["evaluation_report_path"]
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_text("{}\n", encoding="utf-8")
        check_evaluation_report_absent(Path(tmp), S03_ISOLATION, failures)
    del root
    return failures


def _fs_prior_rewritten(root: Path) -> Failures:
    failures: Failures = []
    with tempfile.TemporaryDirectory(prefix="m207-s04-prior-") as tmp:
        rel = PRIOR_NON_PASS_PIN["path"]
        source = root / rel
        if not source.is_file():
            return [("MISSING_ARTIFACT", "selftest could not read the pinned prior receipt")]
        planted = Path(tmp) / rel
        planted.parent.mkdir(parents=True, exist_ok=True)
        receipt = json.loads(source.read_text(encoding="utf-8"))
        receipt["terminal"]["outcome"] = "complete"
        receipt["terminal"]["timeout"] = False
        receipt["claims"]["operational_acceptance"] = "pass"
        planted.write_text(json.dumps(receipt), encoding="utf-8")
        check_prior_non_pass_receipt(Path(tmp), failures)
    return failures


def _fs_s03_pilot_claimed(root: Path) -> Failures:
    failures: Failures = []
    with tempfile.TemporaryDirectory(prefix="m207-s04-s03-") as tmp:
        rel = S03_ISOLATION["s03_battery_path"]
        source = root / rel
        if not source.is_file():
            return [("MISSING_ARTIFACT", "selftest could not read the pinned S03 battery")]
        planted = Path(tmp) / rel
        planted.parent.mkdir(parents=True, exist_ok=True)
        battery = json.loads(source.read_text(encoding="utf-8"))
        battery["human_pilot_performed"] = True
        planted.write_text(json.dumps(battery), encoding="utf-8")
        check_s03_battery_current(Path(tmp), failures)
    return failures


def _fs_frozen_source_drift(root: Path) -> Failures:
    failures: Failures = []
    with tempfile.TemporaryDirectory(prefix="m207-s04-drift-") as tmp:
        tmp_root = Path(tmp)
        for entry in FROZEN_SOURCES.values():
            rel = entry["path"]
            source = root / rel
            if not source.is_file():
                return [("MISSING_ARTIFACT", f"selftest could not read {rel}")]
            target = tmp_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        name = sorted(FROZEN_SOURCES)[0]
        mutated = tmp_root / FROZEN_SOURCES[name]["path"]
        mutated.write_bytes(mutated.read_bytes() + b" ")
        check_frozen_digests(tmp_root, failures)
    return failures


FS_SELFTEST_CASES: tuple[tuple[str, str, FsCase], ...] = (
    ("live-corpus-count", "CORPUS_COUNT_DRIFT", _fs_corpus_count),
    ("live-seed-enlarged", "SEED_ENLARGED", _fs_seed_enlarged),
    ("live-seed-digest", "SEED_DRIFT", _fs_seed_digest),
    ("live-crates-isolation", "S03_RATE_IMPORTED", _fs_crates_isolation),
    ("live-evaluation-report", "REPORT_WITHOUT_HUMAN_DATA", _fs_evaluation_report),
    ("live-prior-rewrite", "C4_TIMEOUT_AS_PASS", _fs_prior_rewritten),
    ("live-s03-pilot-claim", "S03_BATTERY_PILOT_PERFORMED", _fs_s03_pilot_claimed),
    ("live-frozen-drift", "FROZEN_SOURCE_DRIFT", _fs_frozen_source_drift),
)


def _selftest_baselines(
    root: Path, protocol_rel: str, schemas_rel: str
) -> tuple[dict[str, Any], dict[str, Any], list[str]] | None:
    protocol_path = root / protocol_rel
    schemas_path = root / schemas_rel
    if not protocol_path.is_file() or not schemas_path.is_file():
        return None
    protocol_text = protocol_path.read_text(encoding="utf-8")
    schema = load_json(schemas_path, "S04 schemas document")
    contract = extract_contract(protocol_text, CONTRACT_HEADING, "S04 protocol contract")
    return schema, contract, protocol_headings(protocol_text)


def run_selftest(root: Path, protocol_rel: str, schemas_rel: str) -> int:
    baselines = _selftest_baselines(root, protocol_rel, schemas_rel)
    if baselines is None:
        print("FAIL SELFTEST_BASELINE: S04 protocol or schemas missing", file=sys.stderr)
        return 1
    schema0, contract0, headings = baselines

    problems: list[str] = []
    baseline = collect_failures(root, protocol_rel, schemas_rel)
    if baseline:
        problems.append(
            "selftest baseline is not green: "
            + ", ".join(sorted({diagnostic for diagnostic, _ in baseline}))
        )

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

    for name, diagnostic, runner in FS_SELFTEST_CASES:
        seen = {diag for diag, _ in runner(root)}
        if diagnostic not in seen:
            problems.append(
                f"hostile case {name!r} did not raise {diagnostic} (saw {sorted(seen) or 'nothing'})"
            )

    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        print(
            f"FAIL M207_S04_SCHEMAS_SELFTEST: {len(problems)} hostile path(s) not proven",
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
