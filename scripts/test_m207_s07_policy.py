#!/usr/bin/env python3
"""Offline adversarial subprocess suite for the M207 S07 failure policy (T04).

The failure policy (``scripts/m207_s07_policy.py``) is only worth its name if it refuses the
operator files a launderer can actually write by hand: a sidecar padded with an extra key, a
sidecar bound to a foreign provider root, a path that escapes the repository, a sidecar that is
simply absent while ``aggregate.failed > 0``, a timeout re-labelled as a full walk, a duration
floor smuggled in as acceptance, an S03 rate key, a grown seed, a gold or promotion claim, an
``acceptance_effect`` other than ``none``, or a limited argv.  Each of those is a *single*
edit, so each of them gets a single-edit hostile case here.

Every case drives the real CLI (``scripts/m207_s07_policy.py check``) against a throw-away copy
of the reading surface inside ``tempfile.mkdtemp``, mutates exactly one thing, and asserts the
run fails closed with its *own* named diagnostic drawn from the frozen successor vocabulary.
Nothing is mocked, nothing is imported from the tools under test (subprocess only, D472), and
nothing here reads ``.gsd/``, ``.planning/`` or ``.audits/``.  The one read-only contact with the
repository tree is the pinned receipts whose digests are asserted before and after the run; the
real corpus is only ever *counted* when a recorder precondition must be reached.

Two invariants this suite owns:

* **every policy check is load-bearing** -- each ``# --- pcheck:<id> ---`` block is neutralised
  in a patched copy of the policy source and the mapped hostile case must stop producing its
  named diagnostic.  A suite that stayed green after a guard was deleted would be decoration.
* **no marker is ever printed on a refusal** -- ``M207_S07_POLICY_OK`` (and every other
  integrity marker) means "the contract held", so it may never appear on a hostile run, and no
  refusal may ever be read as acceptance.

An empty suite is itself a failure: ``SuiteIntegrityTests`` requires the hostile registry to stay
populated, every named diagnostic to exist in the frozen vocabulary, every declared policy check
to have a guard case, and the protocol's machine-readable diagnostic block to agree with the
module's own closed set (a drift in either direction is a failure).
"""

from __future__ import annotations

import ast
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "scripts" / "m207_s07_policy.py"
RECORDER = ROOT / "scripts" / "m207_s07_c4_run.py"

# Re-declared on purpose: this suite imports nothing from the tools under test (D472), so a
# drift between the suite's expectations and the tools' constants becomes a failing case.
PROTOCOL_REL = "prd/annotation/m207-s07-c4-protocol.md"
SCHEMAS_REL = "prd/annotation/m207-s07-schemas.json"
CONTRACT_REL = "prd/architecture/npa-acceptance-contract.yaml"
BINARY_REL = "target/release/npa-contour-diagnostics"
PARSER_SOURCE_REL = "crates/ln-consultant-parser/src/contour_diagnostics.rs"
EVIDENCE_DIR_REL = "prd/migration/rust-evidence"
RECEIPT_REL = f"{EVIDENCE_DIR_REL}/m207-s07-c4-operational-receipt.json"
ATTEMPT_DIR_REL = f"{EVIDENCE_DIR_REL}/m207-s07-c4-attempts"
ATTEMPT_ID = "m207-s07-c4-full-walk-001"
SIDECAR_NAME = "failures.jsonl"
SIDECAR_REL = f"{ATTEMPT_DIR_REL}/{ATTEMPT_ID}/{SIDECAR_NAME}"
S04_RECEIPT_REL = f"{EVIDENCE_DIR_REL}/m207-s04-c4-operational-receipt.json"
M204_RECEIPT_REL = f"{EVIDENCE_DIR_REL}/m204-s06-c4-operational-receipt.json"
S04_BATTERY_REL = f"{EVIDENCE_DIR_REL}/m207-s04-battery.json"
S03_BATTERY_REL = f"{EVIDENCE_DIR_REL}/m207-s03-battery.json"
FROZEN_S04_ATTEMPT_SIDECAR_REL = (
    f"{EVIDENCE_DIR_REL}/m207-s04-c4-attempts/m207-s04-c4-full-walk-001/{SIDECAR_NAME}"
)

RECEIPT_SCHEMA_ID = "m207-s07-c4-operational-successor/v1"
SIDECAR_SCHEMA_ID = "npa-contour-failure-trace/v1"
POLICY_MARKER = "M207_S07_POLICY_OK"
POLICY_SELFTEST_MARKER = "M207_S07_POLICY_SELFTEST_OK"
RECORDER_MARKER = "M207_S07_C4_RECEIPT_OK"
DRY_RUN_MARKER = "M207_S07_C4_DRYRUN_OK"
RECORDER_GATE_NAME = "M207_S07_C4_RECORDER"
POLICY_GATE_NAME = "M207_S07_POLICY"

# The documented frozen digests (the plan's pins, re-declared so a drift fails here).
S04_RECEIPT_SHA256 = "423d30de06080fce1c3da255d1d03cc3f19548d29e4338c74d913f4771e9e935"
M204_RECEIPT_SHA256 = "04e41f896f2bded096061d7caef2ec4abdaaf37cebf88c387d1dd011943b797c"

# Every marker that means "some integrity chain held".  None of them may appear on a refusal,
# and a refusal must never be quoted as one of them.
INTEGRITY_MARKERS = (
    POLICY_MARKER,
    POLICY_SELFTEST_MARKER,
    RECORDER_MARKER,
    DRY_RUN_MARKER,
    "M207_S07_C4_RECORDER_SELFTEST_OK",
    "M207_S07_SCHEMAS_OK",
    "M207_S07_SCHEMAS_SELFTEST_OK",
    "M207_S07_CLASSIFY_OK",
    "M207_S07_C4_CLASSIFY_SELFTEST_OK",
    "M207_S07_VERIFY_OK",
    "M207_S04_VERIFY_OK",
    "M207_S04_C4_RECEIPT_OK",
    "M207_S04_PROMOTION_NONE_OK",
)

# The report closure the lawful path must publish (re-declared, not imported).
EXPECTED_REPORT_KEYS = (
    "schema",
    "receipt",
    "attempt_id",
    "terminal",
    "aggregate",
    "sidecar_present",
    "sidecar_rows",
    "exit_class",
    "classification",
    "predicates",
    "duration_ms",
    "budget_seconds",
    "short_walk_is_not_timeout",
    "acceptance_effect",
    "promotion",
    "human_pilot_performed",
    "s03_rates_status",
    "seed_count",
    "diagnostics",
)

PIN_CONSULTANT_XML_COUNT = 43785
PIN_GARANT_FILE_COUNT = 12
PIN_AGGREGATE_FILES = 43797
PIN_SEED_FRAGMENTS = 180
REAL_CORPUS = ROOT / "consru_export" / "consru_export" / "exports"
REAL_GARANT = ROOT / "law-source" / "garant"

TIMEOUT = 300
MIN_HOSTILE_CASES = 30
DIAGNOSTICS_BEGIN = "<!-- s07-diagnostics:begin -->"
DIAGNOSTICS_END = "<!-- s07-diagnostics:end -->"
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

CHILD_ENV = {key: value for key, value in os.environ.items() if not key.startswith("M207_S07_")}

Mutator = Callable[[Path], None]


# --------------------------------------------------------------------------- #
# Small helpers: bytes, JSON, digests, subprocess.
# --------------------------------------------------------------------------- #


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def module_constants(source: str) -> dict[str, Any]:
    """Read the policy module's own constant tables without importing it (D472)."""
    constants: dict[str, Any] = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            constants[target.id] = ast.literal_eval(node.value)
        except (ValueError, SyntaxError, TypeError):
            continue
    return constants


POLICY_SOURCE = POLICY.read_text(encoding="utf-8")
POLICY_CONSTANTS = module_constants(POLICY_SOURCE)
DIAGNOSTIC_CODES = tuple(POLICY_CONSTANTS["DIAGNOSTIC_CODES"])
POLICY_CODES = set(POLICY_CONSTANTS["POLICY_CODES"])
DECLARED_CHECKS = tuple(POLICY_CONSTANTS["POLICY_CHECK_IDS"])


def parse_protocol_diagnostics(text: str) -> set[str]:
    """Read the frozen protocol's machine-readable diagnostic block, fail-closed."""
    lines = text.splitlines()
    begins = [index for index, line in enumerate(lines) if line.strip() == DIAGNOSTICS_BEGIN]
    ends = [index for index, line in enumerate(lines) if line.strip() == DIAGNOSTICS_END]
    if len(begins) != 1 or len(ends) != 1 or ends[0] <= begins[0]:
        raise AssertionError("the protocol's diagnostic block is not a single ordered block")
    codes = {line.strip() for line in lines[begins[0] + 1 : ends[0]] if line.strip()}
    if not codes or any(not _CODE_RE.match(code) for code in codes):
        raise AssertionError("the protocol's diagnostic block carries a non-code line")
    return codes


# --------------------------------------------------------------------------- #
# Fixtures: one lawful attempt, planted inside a throw-away root.
# --------------------------------------------------------------------------- #


def fixture_rows(
    *,
    failed: int = 1,
    files: int = PIN_AGGREGATE_FILES,
    limit: Any = None,
) -> list[dict[str, Any]]:
    return [
        {
            "record_kind": "header",
            "schema": "npa-contour-inventory/v1",
            "limit": limit,
            "argv": ["--root", "consru_export/consru_export/exports"],
        },
        {"record_kind": "aggregate", "files": files, "decoded": files - failed, "failed": failed},
        {"record_kind": "inventory", "consultant_xml": PIN_CONSULTANT_XML_COUNT},
        {"record_kind": "canonical_payload", "limit": limit, "jobs": 0},
        {"record_kind": "operational_envelope", "run_status": "complete"},
    ]


def fixture_sidecar(provider: str = "consultant", klass: str = "decode") -> list[dict[str, Any]]:
    roots = {
        "consultant": "consru_export/consru_export/exports/",
        "garant": "law-source/garant/",
    }
    return [
        {
            "record_kind": "failure",
            "schema": SIDECAR_SCHEMA_ID,
            "provider": provider,
            "path": f"{roots[provider]}2026/file.xml",
            "class": klass,
        }
    ]


def fixture_receipt(
    *,
    attempt_id: str = ATTEMPT_ID,
    terminal: dict[str, Any] | None = None,
    duration_ms: int = 387174,
    budget_seconds: int = 3600,
    failed: int = 1,
    sidecar_rows: int = 1,
    classification: str = "full_walk",
) -> dict[str, Any]:
    """The exactly-23-key successor receipt closure, built here rather than imported."""
    if terminal is None:
        terminal = {"outcome": "complete", "exit_code": 0, "signal": None, "timeout": False}
    sidecar_rel = f"{ATTEMPT_DIR_REL}/{attempt_id}/{SIDECAR_NAME}"
    stdout_rel = f"{ATTEMPT_DIR_REL}/{attempt_id}/stdout.log"
    argv = [
        "--root",
        "consru_export/consru_export/exports",
        "--garant-root",
        "law-source/garant",
        "--profile",
        "contour",
        "--jobs",
        "0",
        "--acceptance-contract",
        CONTRACT_REL,
        "--source-revision",
        "m207-s07-c4-caller-pin-2026-09-22",
        "--failures-out",
        sidecar_rel,
    ]
    return {
        "schema": RECEIPT_SCHEMA_ID,
        "attempt_id": attempt_id,
        "immutable_attempt_identity": {"attempt_id": attempt_id, "argv_sha256": "0" * 64},
        "argv": argv,
        "binary": {"path": BINARY_REL, "sha256": "1" * 64},
        "build_inputs": {
            "binary_sha256": "1" * 64,
            "parser_source_sha256": "2" * 64,
            "protocol_sha256": "3" * 64,
            "schemas_sha256": "4" * 64,
        },
        "toolchain": {"rustc": "rustc 1.0.0", "cargo": "cargo 1.0.0", "commands_exit_code": 0},
        "parser_revision": "PARSER_REVISION",
        "source_revision": "m207-s07-c4-caller-pin-2026-09-22",
        "contract": {"path": CONTRACT_REL, "sha256": "5" * 64, "version": "npa-acceptance/v1"},
        "corpus": {
            "consultant_xml_count": PIN_CONSULTANT_XML_COUNT,
            "consultant_root": "consru_export/consru_export/exports",
            "garant_file_count": PIN_GARANT_FILE_COUNT,
            "garant_root": "law-source/garant",
        },
        "observed_output": {"stdout_sha256": "6" * 64, "inventory_digest": "7" * 64},
        "binding": {
            "profile": "contour",
            "limit": None,
            "jobs": 0,
            "inventory_scope": "consultant XML plus separate Garant files",
        },
        "started_at": "2026-09-22T00:00:00Z",
        "finished_at": "2026-09-22T00:06:27Z",
        "duration_ms": duration_ms,
        "budget_seconds": budget_seconds,
        "terminal": terminal,
        "logs": {
            "stdout": stdout_rel,
            "stderr": f"{ATTEMPT_DIR_REL}/{attempt_id}/stderr.log",
            "stdout_sha256": "6" * 64,
            "stderr_sha256": "8" * 64,
            "inventory_digest": "7" * 64,
        },
        "failure_policy": {
            "failures_out_path": sidecar_rel,
            "failures_sha256": "9" * 64 if sidecar_rows else None,
            "sidecar_rows": sidecar_rows,
            "aggregate_failed": failed,
            "acceptance_effect": "none",
        },
        "predicates": {
            "full_walk": classification == "full_walk",
            "timeout": classification == "timeout",
            "outcome": classification,
        },
        "claims": {
            "operational_classification": classification,
            "acceptance_effect": "none",
            "receipt_is_runtime_attempt": True,
        },
        "non_claims": ["not an acceptance: the policy gate publishes no verdict over the walk"],
    }


def plant_attempt(
    root: Path,
    *,
    receipt: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    sidecar: list[dict[str, Any]] | None = None,
    attempt_id: str = ATTEMPT_ID,
) -> Path:
    """Plant one lawful attempt fixture under a root; returns the receipt path."""
    attempt_dir = root / ATTEMPT_DIR_REL / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)
    if rows is None:
        rows = fixture_rows()
    (attempt_dir / "stdout.log").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    (attempt_dir / "stderr.log").write_text("", encoding="utf-8")
    if sidecar is not None:
        (attempt_dir / SIDECAR_NAME).write_text(
            "".join(json.dumps(row) + "\n" for row in sidecar), encoding="utf-8"
        )
    if receipt is None:
        receipt = fixture_receipt(attempt_id=attempt_id)
    return _write_receipt(root, receipt)


def _write_receipt(root: Path, receipt: dict[str, Any]) -> Path:
    path = root / RECEIPT_REL
    dump_json(path, receipt)
    return path


def _edit_receipt(root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = root / RECEIPT_REL
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    dump_json(path, document)


def _edit_sidecar(root: Path, **updates: Any) -> None:
    path = root / SIDECAR_REL
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    row.update(updates)
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# The hostile mutations: one edit, one named diagnostic.
# --------------------------------------------------------------------------- #


def _timeout_as_full_walk(root: Path) -> None:
    _edit_receipt(
        root,
        lambda document: document.update(
            {
                "terminal": {
                    "outcome": "timeout",
                    "exit_code": None,
                    "signal": "SIGTERM",
                    "timeout": True,
                }
            }
        ),
    )


def _duration_floor_as_timeout(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["predicates"] = {"full_walk": False, "timeout": True, "outcome": "timeout"}

    _edit_receipt(root, mutate)


def _receipt_duration_floor_key(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"duration_floor_ms": 3600000}))


def _missing_sidecar(root: Path) -> None:
    (root / SIDECAR_REL).unlink()

    def mutate(document: dict[str, Any]) -> None:
        document["failure_policy"].update({"sidecar_rows": 0, "failures_sha256": None})

    _edit_receipt(root, mutate)


def _empty_sidecar_with_failed(root: Path) -> None:
    """An empty sidecar is not "no failures" while the attempt's own aggregate says failed=1."""
    (root / SIDECAR_REL).write_text("", encoding="utf-8")

    def mutate(document: dict[str, Any]) -> None:
        document["failure_policy"].update({"sidecar_rows": 0, "failures_sha256": None})

    _edit_receipt(root, mutate)


def _extra_sidecar_key(root: Path) -> None:
    _edit_sidecar(root, payload="boom")


def _sidecar_path_escape(root: Path) -> None:
    _edit_sidecar(root, path="../outside/secret.xml")


def _sidecar_absolute_path(root: Path) -> None:
    _edit_sidecar(root, path="/etc/passwd")


def _sidecar_provider_path_mismatch(root: Path) -> None:
    _edit_sidecar(root, provider="garant", path="consru_export/consru_export/exports/2026/f.xml")


def _sidecar_provider_drift(root: Path) -> None:
    _edit_sidecar(root, provider="falkor")


def _sidecar_class_drift(root: Path) -> None:
    _edit_sidecar(root, **{"class": "retry"})


def _sidecar_schema_drift(root: Path) -> None:
    _edit_sidecar(root, schema="npa-contour-failure-trace/v2")


def _sidecar_record_kind_drift(root: Path) -> None:
    _edit_sidecar(root, record_kind="aggregate")


def _sidecar_not_json(root: Path) -> None:
    (root / SIDECAR_REL).write_text("{not json\n", encoding="utf-8")


def _sidecar_duplicate_key(root: Path) -> None:
    (root / SIDECAR_REL).write_text(
        json.dumps(fixture_sidecar()[0])[:-1] + ', "provider": "garant"}\n', encoding="utf-8"
    )


def _sidecar_declared_in_frozen_s04_path(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["failure_policy"]["failures_out_path"] = FROZEN_S04_ATTEMPT_SIDECAR_REL
        document["argv"] = [
            FROZEN_S04_ATTEMPT_SIDECAR_REL if item.endswith(SIDECAR_NAME) else item
            for item in document["argv"]
        ]

    _edit_receipt(root, mutate)


def _sidecar_binding_drift(root: Path) -> None:
    other = f"{ATTEMPT_DIR_REL}/m207-s07-other-002/{SIDECAR_NAME}"

    def mutate(document: dict[str, Any]) -> None:
        document["failure_policy"]["failures_out_path"] = other
        document["argv"] = [
            other if item.endswith(SIDECAR_NAME) else item for item in document["argv"]
        ]

    _edit_receipt(root, mutate)


def _receipt_operational_acceptance(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"operational_acceptance": "pass"}))


def _receipt_promotion_claim(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"promotion": "pass"}))


def _receipt_gold_claim(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"is_gold": True}))


def _receipt_marker_as_acceptance(root: Path) -> None:
    _edit_receipt(
        root, lambda document: document.update({"acceptance_marker": "M207_S07_VERIFY_OK"})
    )


def _receipt_acceptance_effect_not_none(root: Path) -> None:
    _edit_receipt(
        root,
        lambda document: document["failure_policy"].update({"acceptance_effect": "pass"}),
    )


def _receipt_s03_rate_import(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"aspect_rate": 0.5}))


def _receipt_s03_rate_import_nested(root: Path) -> None:
    """The S03 rate ban holds at every depth, not only at the receipt root."""

    def mutate(document: dict[str, Any]) -> None:
        document["claims"]["agreement_rate"] = 0.5

    _edit_receipt(root, mutate)


def _receipt_seed_enlarge(root: Path) -> None:
    _edit_receipt(
        root, lambda document: document.update({"seed_fragments": PIN_SEED_FRAGMENTS + 1})
    )


def _receipt_extra_key(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"unexpected_extra": True}))


def _receipt_key_dropped(root: Path) -> None:
    _edit_receipt(root, lambda document: document.pop("non_claims", None))


def _receipt_schema_drift(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"schema": "m207-s07-c4-successor/v2"}))


def _receipt_not_an_object(root: Path) -> None:
    (root / RECEIPT_REL).write_text("[]\n", encoding="utf-8")


def _receipt_malformed_json(root: Path) -> None:
    (root / RECEIPT_REL).write_text("{not json\n", encoding="utf-8")


def _receipt_missing(root: Path) -> None:
    (root / RECEIPT_REL).unlink()


def _limit_in_argv(root: Path) -> None:
    _edit_receipt(root, lambda document: document["argv"].extend(["--limit", "5"]))


def _binding_limit_not_null(root: Path) -> None:
    _edit_receipt(root, lambda document: document["binding"].update({"limit": 5}))


def _argv_missing_sidecar_flag(root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        argv = document["argv"]
        index = argv.index("--failures-out")
        document["argv"] = argv[:index] + argv[index + 2 :]

    _edit_receipt(root, mutate)


def _argv_not_a_list(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"argv": "--root corpus"}))


def _sidecar_count_mismatch(root: Path) -> None:
    _edit_receipt(
        root,
        lambda document: document["failure_policy"].update(
            {"sidecar_rows": 1, "aggregate_failed": 2}
        ),
    )


def _sidecar_unexpected(root: Path) -> None:
    stdout_path = root / ATTEMPT_DIR_REL / ATTEMPT_ID / "stdout.log"
    rows = [json.loads(line) for line in stdout_path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row.get("record_kind") == "aggregate":
            row["failed"] = 0
    stdout_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    _edit_receipt(
        root,
        lambda document: document["failure_policy"].update(
            {"aggregate_failed": 0, "sidecar_rows": 1}
        ),
    )


def _allowlist_refusal_with_sidecar(root: Path) -> None:
    _edit_receipt(
        root,
        lambda document: document.update(
            {
                "terminal": {
                    "outcome": "nonzero",
                    "exit_code": 3,
                    "signal": None,
                    "timeout": False,
                },
                "predicates": {"full_walk": False, "timeout": False, "outcome": "nonzero"},
                "claims": {
                    "operational_classification": "nonzero",
                    "acceptance_effect": "none",
                    "receipt_is_runtime_attempt": True,
                },
            }
        ),
    )


def _aggregate_missing(root: Path) -> None:
    (root / ATTEMPT_DIR_REL / ATTEMPT_ID / "stdout.log").write_text(
        json.dumps({"record_kind": "header", "limit": None}) + "\n", encoding="utf-8"
    )


def _stdout_log_missing(root: Path) -> None:
    (root / ATTEMPT_DIR_REL / ATTEMPT_ID / "stdout.log").unlink()


def _stdout_log_not_json(root: Path) -> None:
    (root / ATTEMPT_DIR_REL / ATTEMPT_ID / "stdout.log").write_text("{not json\n", encoding="utf-8")


def _terminal_outcome_drift(root: Path) -> None:
    _edit_receipt(root, lambda document: document["terminal"].update({"outcome": "finished"}))


def _budget_below_minimum(root: Path) -> None:
    _edit_receipt(root, lambda document: document.update({"budget_seconds": 60}))


def _protocol_diagnostic_drift(root: Path) -> None:
    path = root / PROTOCOL_REL
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("SEED_ENLARGE\n", "", 1), encoding="utf-8")


def _schemas_missing(root: Path) -> None:
    (root / SCHEMAS_REL).unlink()


def _schema_document_receipt_id_drift(root: Path) -> None:
    path = root / SCHEMAS_REL
    document = load_json(path)
    document["receipt_schema_id"] = "m207-s07-c4-operational-successor/v2"
    dump_json(path, document)


def _schema_document_sidecar_keys_opened(root: Path) -> None:
    path = root / SCHEMAS_REL
    document = load_json(path)
    document["failure_policy"]["sidecar_keys"] = [
        *document["failure_policy"]["sidecar_keys"],
        "payload",
    ]
    dump_json(path, document)


@dataclass(frozen=True)
class HostileCase:
    """One mutation, one expected diagnostic, and the policy check that must speak it."""

    name: str
    diagnostic: str
    mutator: Mutator | None = None
    extra_args: tuple[str, ...] = field(default_factory=tuple)


HOSTILE_CASES: tuple[HostileCase, ...] = (
    HostileCase("timeout-as-full-walk", "PREDICATE_CONTRADICTION", _timeout_as_full_walk),
    HostileCase("duration-floor-as-timeout", "PREDICATE_CONTRADICTION", _duration_floor_as_timeout),
    HostileCase(
        "receipt-duration-floor-key", "DURATION_FLOOR_AS_ACCEPTANCE", _receipt_duration_floor_key
    ),
    HostileCase("missing-sidecar", "MISSING_SIDECAR", _missing_sidecar),
    HostileCase("empty-sidecar-with-failed", "MISSING_SIDECAR", _empty_sidecar_with_failed),
    HostileCase("extra-sidecar-key", "SIDECAR_KEY_DRIFT", _extra_sidecar_key),
    HostileCase("sidecar-path-escape", "SIDECAR_PATH_ESCAPE", _sidecar_path_escape),
    HostileCase("sidecar-absolute-path", "SIDECAR_PATH_ESCAPE", _sidecar_absolute_path),
    HostileCase(
        "sidecar-provider-path-mismatch", "SIDECAR_PATH_ESCAPE", _sidecar_provider_path_mismatch
    ),
    HostileCase("sidecar-provider-drift", "SIDECAR_PROVIDER_DRIFT", _sidecar_provider_drift),
    HostileCase("sidecar-class-drift", "SIDECAR_CLASS_DRIFT", _sidecar_class_drift),
    HostileCase("sidecar-schema-drift", "SCHEMA_VERSION_DRIFT", _sidecar_schema_drift),
    HostileCase("sidecar-record-kind-drift", "SIDECAR_KEY_DRIFT", _sidecar_record_kind_drift),
    HostileCase("sidecar-not-json", "MALFORMED_RECEIPT", _sidecar_not_json),
    HostileCase("sidecar-duplicate-key", "MALFORMED_RECEIPT", _sidecar_duplicate_key),
    HostileCase(
        "sidecar-declared-in-frozen-s04-path",
        "C4_RECEIPT_DRIFT",
        _sidecar_declared_in_frozen_s04_path,
    ),
    HostileCase("sidecar-binding-drift", "C4_RECEIPT_DRIFT", _sidecar_binding_drift),
    HostileCase(
        "receipt-operational-acceptance", "SCHEMA_KEY_DRIFT", _receipt_operational_acceptance
    ),
    HostileCase("receipt-promotion-claim", "PROMOTION_CLAIM", _receipt_promotion_claim),
    HostileCase("receipt-gold-claim", "GOLD_CLAIM", _receipt_gold_claim),
    HostileCase("receipt-marker-as-acceptance", "PROMOTION_CLAIM", _receipt_marker_as_acceptance),
    HostileCase(
        "receipt-acceptance-effect-not-none",
        "PROMOTION_CLAIM",
        _receipt_acceptance_effect_not_none,
    ),
    HostileCase("receipt-s03-rate-import", "S03_RATE_IMPORT", _receipt_s03_rate_import),
    HostileCase(
        "receipt-s03-rate-import-nested", "S03_RATE_IMPORT", _receipt_s03_rate_import_nested
    ),
    HostileCase("receipt-seed-enlarge", "SEED_ENLARGE", _receipt_seed_enlarge),
    HostileCase("receipt-extra-key", "SCHEMA_KEY_DRIFT", _receipt_extra_key),
    HostileCase("receipt-key-dropped", "SCHEMA_KEY_DRIFT", _receipt_key_dropped),
    HostileCase("receipt-schema-drift", "SCHEMA_VERSION_DRIFT", _receipt_schema_drift),
    HostileCase("receipt-not-an-object", "SCHEMA_KEY_DRIFT", _receipt_not_an_object),
    HostileCase("receipt-malformed-json", "MALFORMED_RECEIPT", _receipt_malformed_json),
    HostileCase("receipt-missing", "MISSING_INPUT", _receipt_missing),
    HostileCase("limit-in-argv", "ARGV_PIN_DRIFT", _limit_in_argv),
    HostileCase("binding-limit-not-null", "ARGV_PIN_DRIFT", _binding_limit_not_null),
    HostileCase("argv-missing-sidecar-flag", "ARGV_PIN_DRIFT", _argv_missing_sidecar_flag),
    HostileCase("argv-not-a-list", "ARGV_PIN_DRIFT", _argv_not_a_list),
    HostileCase("sidecar-count-mismatch", "SIDECAR_COUNT_MISMATCH", _sidecar_count_mismatch),
    HostileCase("sidecar-unexpected", "SIDECAR_UNEXPECTED", _sidecar_unexpected),
    HostileCase(
        "allowlist-refusal-with-sidecar", "ALLOWLIST_REFUSAL", _allowlist_refusal_with_sidecar
    ),
    HostileCase("aggregate-missing", "MALFORMED_RECEIPT", _aggregate_missing),
    HostileCase("stdout-log-missing", "MALFORMED_RECEIPT", _stdout_log_missing),
    HostileCase("stdout-log-not-json", "MALFORMED_RECEIPT", _stdout_log_not_json),
    HostileCase("terminal-outcome-drift", "TERMINAL_OUTCOME_DRIFT", _terminal_outcome_drift),
    HostileCase("budget-below-minimum", "PREDICATE_CONTRADICTION", _budget_below_minimum),
    HostileCase(
        "protocol-diagnostic-drift", "PROTOCOL_DIAGNOSTIC_DRIFT", _protocol_diagnostic_drift
    ),
    HostileCase("schemas-missing", "MISSING_ARTIFACT", _schemas_missing),
    HostileCase(
        "schema-document-receipt-id-drift",
        "SCHEMA_VERSION_DRIFT",
        _schema_document_receipt_id_drift,
    ),
    HostileCase(
        "schema-document-sidecar-keys-opened",
        "SIDECAR_KEY_DRIFT",
        _schema_document_sidecar_keys_opened,
    ),
    HostileCase("receipt-traversal", "UNSAFE_PATH", None, ("--receipt", "../../etc/passwd")),
    HostileCase("receipt-absolute", "UNSAFE_PATH", None, ("--receipt", "/etc/passwd")),
    HostileCase("sidecar-traversal", "UNSAFE_PATH", None, ("--sidecar", "../../etc/passwd")),
)

CASES_BY_NAME = {case.name: case for case in HOSTILE_CASES}

# One load-bearing guard per declared policy check: neutralising the check must silence the code.
CHECK_GUARDS: dict[str, str] = {
    "protocol-vocabulary": "protocol-diagnostic-drift",
    "receipt-load": "receipt-missing",
    "schema-document": "schema-document-receipt-id-drift",
    "acceptance-keys": "receipt-promotion-claim",
    "duration-floor": "receipt-duration-floor-key",
    "s03-isolation": "receipt-s03-rate-import",
    "schema-id": "receipt-schema-drift",
    "closed-keys": "receipt-extra-key",
    "argv-binding": "limit-in-argv",
    "sidecar-binding": "sidecar-binding-drift",
    "sidecar-rows": "extra-sidecar-key",
    "sidecar-count": "sidecar-count-mismatch",
    "predicates": "timeout-as-full-walk",
    "exit-class": "allowlist-refusal-with-sidecar",
}


# --------------------------------------------------------------------------- #
# The throw-away base root: frozen documents plus the recorder's reading surface.
# --------------------------------------------------------------------------- #


def _copy_surface(root: Path) -> None:
    """A faithful, minimal copy of the surface both tools read."""
    for relative in (PROTOCOL_REL, SCHEMAS_REL, CONTRACT_REL):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    # The recorder checks these roots exist before it checks the write surface; their counts are
    # only ever compared in the two cases that run against the real corpus.
    (root / "consru_export" / "consru_export" / "exports").mkdir(parents=True, exist_ok=True)
    (root / "law-source" / "garant").mkdir(parents=True, exist_ok=True)
    binary = root / BINARY_REL
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_bytes(b"#!/bin/sh\nexit 0\n")
    parser_source = root / PARSER_SOURCE_REL
    parser_source.parent.mkdir(parents=True, exist_ok=True)
    parser_source.write_text('pub const PARSER_REVISION: &str = "test";\n', encoding="utf-8")


def _build_base_root() -> Path:
    holder = Path(tempfile.mkdtemp(prefix="m207-s07-policy-suite-base-"))
    atexit.register(shutil.rmtree, holder, ignore_errors=True)
    root = holder / "root"
    _copy_surface(root)
    return root


BASE_ROOT = _build_base_root()
BASE_DIGEST = tree_digest(BASE_ROOT)

TEMP_HOLDER = Path(tempfile.mkdtemp(prefix="m207-s07-policy-suite-"))
atexit.register(shutil.rmtree, TEMP_HOLDER, ignore_errors=True)
USED_ROOTS: list[Path] = []


def temp_root(prefix: str = "case") -> Path:
    root = Path(tempfile.mkdtemp(prefix=f"{prefix}-", dir=str(TEMP_HOLDER)))
    USED_ROOTS.append(root)
    shutil.copytree(BASE_ROOT, root / "root")
    return root / "root"


class SuiteBase(unittest.TestCase):
    """Shared temp-root and subprocess helpers."""

    def run_tool(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(ROOT),
            env=CHILD_ENV,
            text=True,
            capture_output=True,
            check=False,
            timeout=TIMEOUT,
        )

    def run_policy(
        self, root: Path, *extra: str, script: Path = POLICY
    ) -> subprocess.CompletedProcess[str]:
        self.assertNotEqual(
            Path(root).resolve(), ROOT.resolve(), "the suite never drives the real repository root"
        )
        return self.run_tool(script, "check", "--repo-root", str(root), *extra)

    def refusal(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        self.assertEqual(result.returncode, 1, msg=f"{result.stdout}\n{result.stderr}")
        self.assertNotIn("Traceback", result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "refused")
        self.assertEqual(payload["acceptance_effect"], "none")
        self.assert_no_marker(result, payload.get("detail", ""))
        self.assertIn(f"FAIL {payload['diagnostic']}:", result.stderr)
        return payload

    def assert_no_marker(self, result: subprocess.CompletedProcess[str], detail: str = "") -> None:
        """No marker may be *printed*; a refusal may still quote the marker it refuses."""
        escaped = json.dumps(detail)[1:-1] if detail else ""
        stdout = result.stdout.replace(escaped, "") if escaped else result.stdout
        stderr = result.stderr.replace(detail, "") if detail else result.stderr
        for marker in INTEGRITY_MARKERS:
            self.assertNotIn(marker, stdout)
            self.assertNotIn(marker, stderr)

    def assert_refused_with(
        self, result: subprocess.CompletedProcess[str], diagnostic: str
    ) -> dict[str, Any]:
        payload = self.refusal(result)
        self.assertEqual(payload["diagnostic"], diagnostic, msg=result.stdout)
        return payload

    def assert_lawful(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(POLICY_MARKER, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(set(report), set(EXPECTED_REPORT_KEYS))
        self.assertEqual(report["acceptance_effect"], "none")
        self.assertEqual(report["promotion"], "none")
        self.assertIs(report["human_pilot_performed"], False)
        self.assertEqual(report["s03_rates_status"], "not-measured")
        self.assertEqual(report["seed_count"], PIN_SEED_FRAGMENTS)
        self.assertEqual(report["diagnostics"], [])
        return report

    def plant_lawful(self, root: Path) -> None:
        plant_attempt(root, sidecar=fixture_sidecar())
        self.assertNotEqual(
            tree_digest(root), BASE_DIGEST, msg="the fixture did not mutate the root"
        )


# --------------------------------------------------------------------------- #
# Positive controls: the lawful classes must pass, including the short full walk.
# --------------------------------------------------------------------------- #


class PositiveControlTests(SuiteBase):
    def test_short_full_walk_under_the_ceiling_is_lawful(self) -> None:
        """387174 ms under a 3600 s ceiling is a complete full walk, not a timeout."""
        root = temp_root()
        self.plant_lawful(root)
        report = self.assert_lawful(self.run_policy(root))
        self.assertEqual(report["classification"], "full_walk")
        self.assertEqual(report["exit_class"], "zero")
        self.assertIs(report["short_walk_is_not_timeout"], True)
        self.assertEqual(report["sidecar_rows"], 1)
        self.assertEqual(report["aggregate"]["failed"], 1)
        self.assertEqual(report["duration_ms"], 387174)
        self.assertEqual(report["budget_seconds"], 3600)

    def test_timeout_is_lawful_and_carries_no_sidecar(self) -> None:
        root = temp_root()
        receipt = fixture_receipt(
            terminal={
                "outcome": "timeout",
                "exit_code": None,
                "signal": "SIGTERM",
                "timeout": True,
            },
            duration_ms=3600000,
            failed=0,
            sidecar_rows=0,
            classification="timeout",
        )
        plant_attempt(root, receipt=receipt, rows=fixture_rows(failed=0), sidecar=None)
        report = self.assert_lawful(self.run_policy(root))
        self.assertEqual(report["classification"], "timeout")
        self.assertEqual(report["exit_class"], "timeout")
        self.assertEqual(report["sidecar_rows"], 0)
        self.assertIs(report["sidecar_present"], False)

    def test_exit_three_allowlist_refusal_is_lawful_without_a_sidecar(self) -> None:
        root = temp_root()
        receipt = fixture_receipt(
            terminal={"outcome": "nonzero", "exit_code": 3, "signal": None, "timeout": False},
            failed=1,
            sidecar_rows=0,
            classification="nonzero",
        )
        plant_attempt(root, receipt=receipt, rows=fixture_rows(failed=1), sidecar=None)
        report = self.assert_lawful(self.run_policy(root))
        self.assertEqual(report["classification"], "nonzero")
        self.assertEqual(report["exit_class"], "allowlist_refusal")
        self.assertEqual(report["sidecar_rows"], 0)

    def test_empty_sidecar_with_failed_zero_is_lawful(self) -> None:
        """An empty sidecar is lawful exactly when the attempt's own aggregate says failed=0."""
        root = temp_root()
        receipt = fixture_receipt(failed=0, sidecar_rows=0, classification="full_walk")
        plant_attempt(root, receipt=receipt, rows=fixture_rows(failed=0), sidecar=[])
        report = self.assert_lawful(self.run_policy(root))
        self.assertEqual(report["sidecar_rows"], 0)
        self.assertIs(report["sidecar_present"], True)

    def test_garant_provider_row_is_lawful(self) -> None:
        root = temp_root()
        plant_attempt(root, sidecar=fixture_sidecar(provider="garant", klass="read"))
        report = self.assert_lawful(self.run_policy(root))
        self.assertEqual(report["classification"], "full_walk")


# --------------------------------------------------------------------------- #
# The hostile registry: every case fails closed with its own named diagnostic.
# --------------------------------------------------------------------------- #


class HostileCaseTests(SuiteBase):
    def test_every_hostile_case_fails_closed_with_its_named_diagnostic(self) -> None:
        for case in HOSTILE_CASES:
            with self.subTest(case=case.name):
                root = temp_root(case.name)
                self.plant_lawful(root)
                if case.mutator is not None:
                    case.mutator(root)
                    self.assertNotEqual(
                        tree_digest(root),
                        BASE_DIGEST,
                        msg=f"hostile case {case.name!r} did not mutate its root",
                    )
                result = self.run_policy(root, *case.extra_args)
                self.assert_refused_with(result, case.diagnostic)

    def test_a_lawful_attempt_is_reachable_after_every_hostile_case(self) -> None:
        """The registry must not be refused by plant-time noise: the control still passes."""
        root = temp_root("control")
        self.plant_lawful(root)
        self.assert_lawful(self.run_policy(root))


# --------------------------------------------------------------------------- #
# Guard removal: the policy is only enforcement if a deleted check is detectable.
# --------------------------------------------------------------------------- #


def _patch_source(source: str, check_id: str) -> str:
    """Neutralise one ``# --- pcheck:<id> ---`` block, keeping the module importable."""
    begin = f"# --- pcheck:{check_id} ---"
    end = f"# --- /pcheck:{check_id} ---"
    lines = source.splitlines(keepends=True)
    begins = [index for index, line in enumerate(lines) if line.strip() == begin]
    ends = [index for index, line in enumerate(lines) if line.strip() == end]
    if len(begins) != 1 or len(ends) != 1 or ends[0] <= begins[0]:
        raise AssertionError(f"check {check_id!r} is not a single ordered marker block")
    body = "".join(lines[begins[0] : ends[0]])
    match = re.search(r"^def ([A-Za-z_][A-Za-z0-9_]*)", body, re.MULTILINE)
    if match is None:
        raise AssertionError(f"check {check_id!r} declares no function to neutralise")
    stub = f"def {match.group(1)}(ctx: dict[str, Any]) -> None:\n    return None\n"
    return "".join(lines[: begins[0] + 1]) + stub + "".join(lines[ends[0] :])


class CheckRemovalTests(SuiteBase):
    """Neutralise each policy check in a patched copy and prove its guard case goes silent."""

    def _patched_policy(self, check_id: str) -> Path:
        holder = Path(tempfile.mkdtemp(prefix=f"patched-{check_id}-", dir=str(TEMP_HOLDER)))
        USED_ROOTS.append(holder)
        patched = holder / "m207_s07_policy_patched.py"
        patched.write_text(_patch_source(POLICY_SOURCE, check_id), encoding="utf-8")
        return patched

    def test_every_declared_check_has_a_guard_case(self) -> None:
        self.assertEqual(set(CHECK_GUARDS), set(DECLARED_CHECKS))
        for check_id, case_name in CHECK_GUARDS.items():
            with self.subTest(check=check_id):
                self.assertIn(case_name, CASES_BY_NAME)
                self.assertTrue(DECLARED_CHECKS)
        marker_ids = {
            match.group(1)
            for match in re.finditer(r"^# --- pcheck:([a-z0-9-]+) ---", POLICY_SOURCE, re.MULTILINE)
        }
        self.assertEqual(marker_ids, set(DECLARED_CHECKS))

    def test_removing_any_single_check_silences_its_named_diagnostic(self) -> None:
        for check_id, case_name in CHECK_GUARDS.items():
            with self.subTest(check=check_id):
                case = CASES_BY_NAME[case_name]
                root = temp_root(f"remove-{check_id}")
                self.plant_lawful(root)
                if case.mutator is not None:
                    case.mutator(root)

                intact = self.run_policy(root, *case.extra_args)
                self.assert_refused_with(intact, case.diagnostic)

                patched = self._patched_policy(check_id)
                result = self.run_policy(root, *case.extra_args, script=patched)
                self.assertNotIn(
                    f"FAIL {case.diagnostic}:",
                    result.stderr,
                    msg=f"check {check_id!r} is not load-bearing: {case.diagnostic} survived its "
                    f"removal\n{result.stdout}\n{result.stderr}",
                )
                self.assertNotIn("Traceback", result.stderr)

    def test_a_patched_copy_still_refuses_an_unrelated_hostile_case(self) -> None:
        """Neutralising one check must not turn the gate into a rubber stamp."""
        case = CASES_BY_NAME["receipt-gold-claim"]
        root = temp_root("patched-unrelated")
        self.plant_lawful(root)
        assert case.mutator is not None
        case.mutator(root)
        patched = self._patched_policy("duration-floor")
        result = self.run_policy(root, *case.extra_args, script=patched)
        self.assert_refused_with(result, "GOLD_CLAIM")


# --------------------------------------------------------------------------- #
# Recorder boundaries: the write surface is reached only through the public CLI.
# --------------------------------------------------------------------------- #


class RecorderBoundaryTests(SuiteBase):
    """The recorder's named refusals, driven through ``run`` inside a temp root."""

    def run_recorder(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return self.run_tool(RECORDER, "run", "--repo-root", str(root), *args)

    def test_limit_flag_is_refused_before_any_write(self) -> None:
        root = temp_root("recorder-limit")
        before = tree_digest(root)
        result = self.run_recorder(root, "--attempt-id", ATTEMPT_ID, "--limit", "5")
        self.assert_refused_with(result, "ARGV_PIN_DRIFT")
        self.assertEqual(tree_digest(root), before)

    def test_attempt_id_outside_the_slug_namespace_is_usage(self) -> None:
        root = temp_root("recorder-slug")
        before = tree_digest(root)
        result = self.run_recorder(root, "--attempt-id", "Not-A-Slug")
        self.assert_refused_with(result, "USAGE")
        self.assertEqual(tree_digest(root), before)

    def test_budget_below_the_kill_ceiling_is_refused(self) -> None:
        root = temp_root("recorder-budget")
        result = self.run_recorder(root, "--attempt-id", ATTEMPT_ID, "--budget-seconds", "60")
        self.assert_refused_with(result, "BUDGET_BELOW_MINIMUM")

    def test_source_revision_digest_is_refused(self) -> None:
        root = temp_root("recorder-revision")
        result = self.run_recorder(root, "--attempt-id", ATTEMPT_ID, "--source-revision", "a" * 64)
        self.assert_refused_with(result, "MISSING_INPUT")

    def test_out_outside_the_evidence_dir_is_unsafe(self) -> None:
        root = temp_root("recorder-out")
        before = tree_digest(root)
        result = self.run_recorder(
            root, "--attempt-id", ATTEMPT_ID, "--out", "prd/annotation/scratch.json"
        )
        self.assert_refused_with(result, "UNSAFE_PATH")
        self.assertEqual(tree_digest(root), before)

    def test_frozen_receipt_path_is_c4_receipt_drift(self) -> None:
        """``--out`` may point at the frozen receipt, and then the write is refused."""
        root = temp_root("recorder-frozen")
        before = tree_digest(root)
        result = self.run_recorder(
            root, "--attempt-id", ATTEMPT_ID, "--out", str(root / S04_RECEIPT_REL)
        )
        self.assert_refused_with(result, "C4_RECEIPT_DRIFT")
        self.assertEqual(tree_digest(root), before)

    def test_frozen_attempt_dir_in_the_schema_is_c4_receipt_drift(self) -> None:
        """An attempt log directory declared under a frozen prefix is refused, not written."""
        root = temp_root("recorder-frozen-logs")
        target = root / EVIDENCE_DIR_REL / "m207-s04-c4-attempts" / "m207-s04-c4-full-walk-001"
        target.mkdir(parents=True, exist_ok=True)
        (target / "stdout.log").write_text("published\n", encoding="utf-8")
        schema_path = root / SCHEMAS_REL
        schema = load_json(schema_path)
        schema["new_attempt_policy"]["attempt_dir_prefix"] = (
            f"{EVIDENCE_DIR_REL}/m207-s04-c4-attempts/"
        )
        dump_json(schema_path, schema)
        before = tree_digest(root)
        result = self.run_recorder(root, "--attempt-id", ATTEMPT_ID)
        self.assert_refused_with(result, "C4_RECEIPT_DRIFT")
        self.assertEqual(tree_digest(root), before)
        self.assertEqual((target / "stdout.log").read_text(encoding="utf-8"), "published\n")

    @unittest.skipUnless(
        REAL_CORPUS.is_dir() and REAL_GARANT.is_dir(), "the declared corpus is not present"
    )
    def test_write_once_existing_receipt_is_refused(self) -> None:
        root = temp_root("recorder-write-once")
        dump_json(root / RECEIPT_REL, {"schema": "published-earlier"})
        before = tree_digest(root)
        result = self.run_recorder(
            root,
            "--attempt-id",
            ATTEMPT_ID,
            "--consultant-root",
            str(REAL_CORPUS),
            "--garant-root",
            str(REAL_GARANT),
        )
        self.assert_refused_with(result, "C4_RECEIPT_DRIFT")
        self.assertEqual(tree_digest(root), before)

    @unittest.skipUnless(
        REAL_CORPUS.is_dir() and REAL_GARANT.is_dir(), "the declared corpus is not present"
    )
    def test_nonempty_attempt_dir_without_resume_is_refused(self) -> None:
        root = temp_root("recorder-orphan")
        attempt_dir = root / ATTEMPT_DIR_REL / ATTEMPT_ID
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "stdout.log").write_text("interrupted\n", encoding="utf-8")
        before = tree_digest(root)
        result = self.run_recorder(
            root,
            "--attempt-id",
            ATTEMPT_ID,
            "--consultant-root",
            str(REAL_CORPUS),
            "--garant-root",
            str(REAL_GARANT),
        )
        self.assert_refused_with(result, "ATTEMPT_LOG_MISSING")
        self.assertEqual(tree_digest(root), before)

    @unittest.skipUnless(
        REAL_CORPUS.is_dir() and REAL_GARANT.is_dir(), "the declared corpus is not present"
    )
    def test_dry_run_is_write_free_and_carries_failures_out(self) -> None:
        root = temp_root("recorder-dry-run")
        before = tree_digest(root)
        result = self.run_recorder(
            root,
            "--attempt-id",
            ATTEMPT_ID,
            "--dry-run",
            "--consultant-root",
            str(REAL_CORPUS),
            "--garant-root",
            str(REAL_GARANT),
        )
        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertIn(DRY_RUN_MARKER, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        preview = json.loads(result.stdout)
        self.assertIs(preview["dry_run"], True)
        self.assertIn("--failures-out", preview["argv"])
        self.assertNotIn("--limit", preview["argv"])
        self.assertEqual(preview["acceptance_effect"], "none")
        self.assertIs(preview["receipt_exists"], False)
        self.assertIs(preview["attempt_dir_nonempty"], False)
        self.assertEqual(tree_digest(root), before)

    def test_no_recorder_refusal_prints_an_integrity_marker(self) -> None:
        root = temp_root("recorder-markers")
        result = self.run_recorder(root, "--attempt-id", ATTEMPT_ID, "--limit", "1")
        self.assert_refused_with(result, "ARGV_PIN_DRIFT")
        self.assertNotIn(RECORDER_MARKER, result.stderr)


# --------------------------------------------------------------------------- #
# Document ↔ code agreement, and the vocabulary boundary.
# --------------------------------------------------------------------------- #


class DocCodeAgreementTests(unittest.TestCase):
    def test_protocol_block_equals_the_module_diagnostic_set(self) -> None:
        declared = parse_protocol_diagnostics((ROOT / PROTOCOL_REL).read_text(encoding="utf-8"))
        self.assertEqual(declared, set(DIAGNOSTIC_CODES))

    def test_every_policy_code_is_a_member_of_the_frozen_vocabulary(self) -> None:
        self.assertEqual(sorted(POLICY_CODES - set(DIAGNOSTIC_CODES)), [])
        self.assertNotEqual(POLICY_CODES, set())

    def test_every_registered_diagnostic_is_declared_and_speakable(self) -> None:
        named = {case.diagnostic for case in HOSTILE_CASES}
        self.assertEqual(sorted(named - set(DIAGNOSTIC_CODES)), [])
        self.assertEqual(sorted(named - POLICY_CODES), [])

    def test_every_guard_case_speaks_a_speakable_code(self) -> None:
        """Each guard case must exist and its diagnostic must be one the policy can emit."""
        for check_id, case_name in CHECK_GUARDS.items():
            self.assertIn(case_name, CASES_BY_NAME)
            diagnostic = CASES_BY_NAME[case_name].diagnostic
            self.assertIn(diagnostic, DIAGNOSTIC_CODES, msg=check_id)
            self.assertIn(diagnostic, POLICY_CODES, msg=check_id)

    def test_schema_contract_carries_the_successor_ids_and_the_honesty_terms(self) -> None:
        schema = load_json(ROOT / SCHEMAS_REL)
        self.assertEqual(schema["receipt_schema_id"], RECEIPT_SCHEMA_ID)
        self.assertEqual(schema["sidecar_schema_id"], SIDECAR_SCHEMA_ID)
        contract = schema["promotion_contract"]
        self.assertEqual(contract["promotion"], "none")
        self.assertEqual(contract["classification"], "not-authorized")
        self.assertIsNone(contract["human_acceptance"])
        self.assertIs(contract["is_gold"], False)
        self.assertIs(contract["model_invoked"], False)
        self.assertIs(contract["marker_is_not_acceptance"], True)
        self.assertEqual(schema["failure_policy"]["acceptance_effect"], "none")

    def test_protocol_states_that_a_marker_is_not_acceptance(self) -> None:
        text = (ROOT / PROTOCOL_REL).read_text(encoding="utf-8")
        self.assertIn("A marker is a statement about the tool that printed it", text)

    def test_the_policy_declares_only_honest_report_terms(self) -> None:
        """The policy's own constants are the source of both self-audit claims."""
        constants = POLICY_CONSTANTS
        self.assertEqual(constants["ACCEPTANCE_EFFECT_NONE"], "none")
        self.assertEqual(constants["PROMOTION_NONE"], "none")
        self.assertIs(constants["HUMAN_PILOT_PERFORMED"], False)
        self.assertEqual(constants["S03_RATES_STATUS"], "not-measured")
        self.assertEqual(constants["PIN_SEED_FRAGMENTS"], PIN_SEED_FRAGMENTS)
        self.assertEqual(set(constants["REPORT_KEYS"]), set(EXPECTED_REPORT_KEYS))


# --------------------------------------------------------------------------- #
# Read-only guarantees: the repository tree is never written by this suite.
# --------------------------------------------------------------------------- #


class ReadOnlyTests(unittest.TestCase):
    def test_pinned_receipts_keep_their_documented_digests(self) -> None:
        self.assertEqual(sha256_file(ROOT / S04_RECEIPT_REL), S04_RECEIPT_SHA256)
        self.assertEqual(sha256_file(ROOT / M204_RECEIPT_REL), M204_RECEIPT_SHA256)

    def test_this_suite_never_names_a_gitignored_planning_tree(self) -> None:
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        docstring = ast.get_docstring(tree, clean=False)
        literals = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        forbidden = tuple(f".{stem}/" for stem in ("gsd", "planning", "audits"))
        offenders = [
            value
            for value in literals
            if value != docstring and any(token in value for token in forbidden)
        ]
        self.assertEqual(offenders, [])


# --------------------------------------------------------------------------- #
# Suite integrity: an empty or toothless suite is a failure.
# --------------------------------------------------------------------------- #


class SuiteIntegrityTests(unittest.TestCase):
    def test_registry_is_populated_and_names_are_unique(self) -> None:
        self.assertGreaterEqual(len(HOSTILE_CASES), MIN_HOSTILE_CASES)
        names = [case.name for case in HOSTILE_CASES]
        self.assertEqual(len(names), len(set(names)))
        for case in HOSTILE_CASES:
            self.assertTrue(case.name)
            self.assertTrue(case.diagnostic)
            self.assertIn(case.diagnostic, DIAGNOSTIC_CODES)

    def test_registry_covers_every_policy_check(self) -> None:
        self.assertEqual(len(set(CHECK_GUARDS.values())), len(CHECK_GUARDS))
        self.assertEqual(sorted(CHECK_GUARDS), sorted(DECLARED_CHECKS))
        for case_name in CHECK_GUARDS.values():
            self.assertIn(case_name, CASES_BY_NAME)

    def test_registry_discriminates_more_than_a_few_codes(self) -> None:
        self.assertGreaterEqual(len({case.diagnostic for case in HOSTILE_CASES}), 20)

    def test_every_case_changes_something(self) -> None:
        for case in HOSTILE_CASES:
            self.assertTrue(case.mutator is not None or case.extra_args)

    def test_gate_names_are_never_confused_with_markers(self) -> None:
        self.assertNotEqual(POLICY_GATE_NAME, POLICY_MARKER)
        self.assertNotEqual(RECORDER_GATE_NAME, RECORDER_MARKER)
        self.assertNotIn(POLICY_MARKER, POLICY_GATE_NAME)
        self.assertNotIn(RECORDER_MARKER, RECORDER_GATE_NAME)

    def test_sources_declare_the_markers_the_suite_asserts(self) -> None:
        source = POLICY.read_text(encoding="utf-8")
        self.assertIn(f'MARKER = "{POLICY_MARKER}"', source)
        self.assertIn(f'SELFTEST_MARKER = "{POLICY_SELFTEST_MARKER}"', source)


def setUpModule() -> None:
    """Capture the frozen digests the whole run must leave untouched."""
    ReadOnlyTests._before = {
        relative: sha256_file(ROOT / relative)
        for relative in (S04_RECEIPT_REL, M204_RECEIPT_REL, S04_BATTERY_REL, S03_BATTERY_REL)
    }


def tearDownModule() -> None:
    """No case may write inside the repository, and no fixture may live outside a temp root."""
    for relative, digest in ReadOnlyTests._before.items():
        current = sha256_file(ROOT / relative)
        assert current == digest, f"the suite modified the repository file {relative}"
    for root in USED_ROOTS:
        assert str(root).startswith(str(TEMP_HOLDER)), f"fixture escaped the temp holder: {root}"


if __name__ == "__main__":
    unittest.main()
