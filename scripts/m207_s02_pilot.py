#!/usr/bin/env python3
"""Independent slice verifier for the M207 S02 two-coding human pilot (T06).

The five per-task gates (``m207_s02_schemas.py``, ``m207_s02_coder_kit.py``,
``m207_s02_intake.py``, ``m207_s02_agreement.py``, ``m207_s02_adjudicate.py``)
each prove their own contour.  This verifier proves the *slice boundary*: that
the frozen S01 and S02 artifacts still agree with the pins recorded here, that
the declared counters and lifecycle markers are intact, that no predicted answer
or promotion claim leaked into the S02 surface, that the product crates gained
no reader of the codebook or of a human-pilot artifact, that the five gates and
the whole S01 closeout chain are green as real subprocesses, and that the
harness fabricates no human coding.

It deliberately does **not** import the gate modules (no oracle collapse, D472):
the pins, the counters, the leakage scan and the claim guards are re-derived
here from bytes, and every gate is invoked as a subprocess whose own named
diagnostics are re-emitted verbatim.

What it proves, against the frozen sources rather than against prose:

* frozen-source pins -- sha256 of ``m207-s01-codebook.md``,
  ``m207-s01-schemas.json``, ``m207-s01-pilot-cases.json``,
  ``m207-s01-prompt-packets.jsonl``, ``m207-s01-battery.json`` and of the S02
  ``m207-s02-coder-protocol.md``, ``m207-s02-schemas.json`` and both coder kits;
* counters -- 40 frozen cases in the manifest and in both kits, the
  ``work_family_cap`` of 4, and no Work family contributing more than the cap;
* the closed diagnostic table -- every name this tool may speak must exist in
  the frozen ``$.diagnostics`` list (``DIAGNOSTIC_TABLE_DRIFT`` otherwise), so a
  red run is machine-distinguishable from a green one;
* lifecycle honesty -- ``human_adoption=pending``, ``runtime_stop_active=true``,
  ``selected_d388_gates=none``, ``requirement_status_effect=unchanged``,
  ``review_disposition_effect=unchanged`` in the protocol, the schemas and both
  kits;
* no promotion and no threshold -- the pinned claim values
  (``classification=not-authorized``, ``promotion=none``, ``threshold=null``,
  ``authority=none``, ``suggestion_status=none-provided``,
  ``model_invoked=false``, ``is_gold=false``) are re-checked by *value*, and the
  R035/R070/R074/R038 guardrails are not claimed closed;
* no leaked answer -- a recursive key and substring scan of the coder kits and
  of the machine-readable contract blocks, so a coder never sees a predicted
  answer, decoded legal text or a Work family (``LEAK_FORBIDDEN_KEY`` /
  ``KIT_TEXT_INLINED``);
* the 180-fragment seed is neither enlarged nor edited (count, extra files and
  a name+content rollup equal to the pin);
* prompt isolation -- no ``crates/**`` ``.rs``, ``build.rs`` or ``Cargo.toml``
  references ``m207-s02`` or ``prd/annotation`` (``PROMPT_ISOLATION_VIOLATION``;
  D466/R064);
* the human gate is *not* claimed -- the tool prints ``M207_S02_MACHINERY_OK``
  **if and only if** the contour is green and no human pilot exists
  (``human_pilot_performed=false``), prints
  ``M207_S02_MACHINERY_HUMAN_DATA_PRESENT`` instead once a real pilot receipt
  exists, and **never** prints the human-gate marker ``M207_S02_VERIFY_OK``
  (which only the T07 chain may emit, and only over two real human codings).

The derived pilot artifacts are scanned when they exist: closed-key shape,
claim values, lifecycle markers, counters (``coder_count=2``, ``case_count=40``,
honest per-axis denominators, no ``alpha=1.0`` without backing) and the freeze
order -- the adjudication record's ``pre_adjudication_agreement_sha256`` must
equal the sha256 of the agreement report on disk, so re-pinning a mutated report
after adjudication is ``FROZEN_SOURCE_DRIFT``.

``battery`` mode assembles ``prd/migration/rust-evidence/m207-s02-battery.json``
from a tab-separated result table (``id<TAB>status<TAB>durationMs<TAB>command``)
produced by the T07 chain, refusing a table whose rows are missing, malformed,
duplicated, unexpected or still failing.  The tracked battery carries exactly
the frozen closed keys (``checks``, ``human_pilot_performed``, ``lifecycle``,
``model_invoked``, ``non_claims``, ``pins``, ``schema``, ``schema_version``),
never hashes itself, and never persists wall-clock data -- durations are printed
to stdout as ``M207_S02_BATTERY_TIMINGS`` so the durable exec log keeps them
while the battery stays a pure function of the observed checks (D473).  The mode
is **read-only by default** (byte comparison, ``BATTERY_STALE``); ``--write``
(driven only by ``M207_S02_WRITE_BATTERY=1``) is the single opt-in that touches
the tracked artifact, and it skips the write when the bytes already match.

The T07 chain must emit a result table whose ``check_id`` values are exactly
``CHAIN_CHECKS`` below; anything else is ``SCHEMA_KEY_DRIFT`` naming the diff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MARKER = "M207_S02_MACHINERY_OK"
HUMAN_DATA_MARKER = "M207_S02_MACHINERY_HUMAN_DATA_PRESENT"
BATTERY_MARKER = "M207_S02_BATTERY_OK"
BATTERY_TIMINGS = "M207_S02_BATTERY_TIMINGS"
ABSENT_TOKEN = "MACHINERY_GREEN_HUMAN_ABSENT"
# The human gate marker: this tool must never print it (T07 owns it).
HUMAN_GATE_MARKER = "M207_S02_VERIFY_OK"
S01_CHAIN_MARKER = "M207_S01_VERIFY_OK"

BATTERY_SCHEMA_ID = "m207-s02-battery/v1"
SCHEMA_VERSION = 1
FAIL_EXIT = 1

# Artifacts.
CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
S01_SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
S02_PROTOCOL_REL = "prd/annotation/m207-s02-coder-protocol.md"
S02_SCHEMAS_REL = "prd/annotation/m207-s02-schemas.json"
CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
PACKETS_REL = "prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl"
S01_BATTERY_REL = "prd/migration/rust-evidence/m207-s01-battery.json"
KIT_PASS1_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json"
KIT_PASS2_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass2.json"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
S01_CHAIN_REL = "scripts/m207_s01_t04_verify.sh"

# Derived pilot artifacts (unpinned: they do not exist until a human pilot runs).
INTAKE_RECORD_REL = "prd/migration/rust-evidence/m207-s02-intake-record.json"
AGREEMENT_REPORT_REL = "prd/migration/rust-evidence/m207-s02-agreement-report.json"
INVENTORY_REL = "prd/migration/rust-evidence/m207-s02-disagreement-inventory.json"
ADJUDICATION_RECORD_REL = "prd/migration/rust-evidence/m207-s02-adjudication-record.json"
RECEIPT_REL = "prd/migration/rust-evidence/m207-s02-pilot-receipt.json"
S02_BATTERY_REL = "prd/migration/rust-evidence/m207-s02-battery.json"
SUBMISSION_STORE_REL = "prd/annotation/m207-s02-submissions"
ADJUDICATION_STORE_REL = "prd/annotation/m207-s02-adjudications"

# Frozen-source pins: content sha256, never a git revision.
PINS: dict[str, tuple[str, str]] = {
    "codebook": (
        CODEBOOK_REL,
        "1a1bfe944207e69cb5fb507e94d680384dadecf7ac98ac29b1de4932d7cb76c6",
    ),
    "s01_schemas": (
        S01_SCHEMAS_REL,
        "63a4bc6629bade752f9fa02d1dd5fa6bbf21238e20772d2ba5b74f88ecca3682",
    ),
    "cases": (CASES_REL, "9b0b6bc6bd8eadf9eb86886e45eb756ebade654e96ac3a84132ed9452bdeb9ad"),
    "packets": (PACKETS_REL, "d9d30bf24d40ab8abebb28c1a22692ae99ca029e1b4e2b032a4dae1137cc6b77"),
    "s01_battery": (
        S01_BATTERY_REL,
        "5d3eb65860f902fb8b7109a5a620c2b7af2b26e34531cbeddb92da294d6a9a5d",
    ),
    "s02_protocol": (
        S02_PROTOCOL_REL,
        "763de0f998b772afd85373e438da0b1b6b2a6435d761e67f06177f4b0b1fbc32",
    ),
    "s02_schemas": (
        S02_SCHEMAS_REL,
        "ef438bb5171a8b58f43a8bc4bc2d9a875877da40943ef28e1337b8741a1cab97",
    ),
    "kit_pass1": (
        KIT_PASS1_REL,
        "e23b25d9ce45f72263d9630b47c096a7463b95dbcbfda9233c750e7bf39418c5",
    ),
    "kit_pass2": (
        KIT_PASS2_REL,
        "52be89f0f72f46c7f4503c7912508868f92e1e8501c848b2907c59330e192380",
    ),
}

# (name, label, default, suffix, prefix, directory)
ARTIFACT_SPECS: tuple[tuple[str, str, str, str, str, bool], ...] = (
    ("codebook", "S01 codebook", CODEBOOK_REL, ".md", "prd/annotation/", False),
    ("s01_schemas", "S01 schemas", S01_SCHEMAS_REL, ".json", "prd/annotation/", False),
    (
        "s02_protocol",
        "S02 protocol",
        S02_PROTOCOL_REL,
        ".md",
        "prd/annotation/",
        False,
    ),
    ("s02_schemas", "S02 schemas", S02_SCHEMAS_REL, ".json", "prd/annotation/", False),
    ("cases", "case manifest", CASES_REL, ".json", "prd/migration/rust-evidence/", False),
    ("packets", "prompt packets", PACKETS_REL, ".jsonl", "prd/migration/rust-evidence/", False),
    (
        "s01_battery",
        "S01 battery",
        S01_BATTERY_REL,
        ".json",
        "prd/migration/rust-evidence/",
        False,
    ),
    (
        "kit_pass1",
        "pass-1 kit",
        KIT_PASS1_REL,
        ".json",
        "prd/migration/rust-evidence/",
        False,
    ),
    (
        "kit_pass2",
        "pass-2 kit",
        KIT_PASS2_REL,
        ".json",
        "prd/migration/rust-evidence/",
        False,
    ),
    ("fixture_dir", "fixture dir", FIXTURE_DIR_REL, "", "crates/", True),
    (
        "intake_record",
        "intake record",
        INTAKE_RECORD_REL,
        ".json",
        "prd/migration/rust-evidence/",
        False,
    ),
    (
        "agreement_report",
        "agreement report",
        AGREEMENT_REPORT_REL,
        ".json",
        "prd/migration/rust-evidence/",
        False,
    ),
    (
        "inventory",
        "disagreement inventory",
        INVENTORY_REL,
        ".json",
        "prd/migration/rust-evidence/",
        False,
    ),
    (
        "adjudication_record",
        "adjudication record",
        ADJUDICATION_RECORD_REL,
        ".json",
        "prd/migration/rust-evidence/",
        False,
    ),
    ("receipt", "pilot receipt", RECEIPT_REL, ".json", "prd/migration/rust-evidence/", False),
    (
        "s02_battery",
        "S02 battery",
        S02_BATTERY_REL,
        ".json",
        "prd/migration/rust-evidence/",
        False,
    ),
    (
        "submission_store",
        "submission store",
        SUBMISSION_STORE_REL,
        "",
        "prd/annotation/",
        True,
    ),
    (
        "adjudication_store",
        "adjudication store",
        ADJUDICATION_STORE_REL,
        "",
        "prd/annotation/",
        True,
    ),
)

# The five slice gates, invoked as subprocesses with their own markers.
GATES: tuple[tuple[str, str, str], ...] = (
    ("gate-schemas", "scripts/m207_s02_schemas.py", "M207_S02_SCHEMAS_OK"),
    ("gate-coder-kit", "scripts/m207_s02_coder_kit.py", "M207_S02_CODER_KIT_OK"),
    ("gate-intake", "scripts/m207_s02_intake.py", "M207_S02_INTAKE_OK"),
    ("gate-agreement", "scripts/m207_s02_agreement.py", "M207_S02_AGREEMENT_OK"),
    ("gate-adjudication", "scripts/m207_s02_adjudicate.py", "M207_S02_ADJUDICATION_OK"),
)

# The check ids the T07 chain must report; they are the battery's frozen check set.
CHAIN_CHECKS: tuple[str, ...] = (
    "gate-schemas",
    "gate-coder-kit",
    "gate-intake",
    "gate-agreement",
    "gate-adjudication",
    "adversarial-suite",
    "verifier-pilot",
    "s01-regression",
    "ruff-format-check",
    "ruff-lint",
    "adr-conformance",
)

# The closed diagnostic vocabulary this tool may speak; every entry must exist
# in the frozen ``$.diagnostics`` list (checked in ``check_diagnostic_table``).
LOCAL_DIAGNOSTICS: tuple[str, ...] = (
    "UNSAFE_PATH",
    "MISSING_ARTIFACT",
    "MISSING_SCHEMA",
    "FROZEN_SOURCE_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "DUPLICATE_JSON_KEY",
    "SCHEMA_KEY_DRIFT",
    "DIAGNOSTIC_TABLE_DRIFT",
    "MISSING_LIFECYCLE_MARKER",
    "CASE_COUNT_OUT_OF_RANGE",
    "WORK_FAMILY_DOMINANCE",
    "SEED_ENLARGED",
    "LEAK_FORBIDDEN_KEY",
    "KIT_TEXT_INLINED",
    "PROMPT_ISOLATION_VIOLATION",
    "THRESHOLD_REQUESTED",
    "CLASSIFICATION_REQUESTED",
    "GOLD_CLAIM",
    "PROMOTION_CLAIM",
    "MODEL_INVOKED",
    "AUTHORITY_CLAIM",
    "DENOMINATOR_MISMATCH",
    "PERFECT_AGREEMENT_UNCOMPUTED",
    "AGREEMENT_UNDEFINED",
    "UNKNOWN_CASE_ID",
    "DUPLICATE_CODER_ID",
    "ONE_CODER_ONLY",
    "UNRESOLVED_NONZERO",
    "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
    "VOCABULARY_DRIFT",
    "HUMAN_PILOT_ABSENT",
    "SUBCLI_FAILURE",
    "S01_REGRESSION_FAILED",
    "EMPTY_SUITE",
    "BATTERY_STALE",
    "BATTERY_WALLCLOCK_FORBIDDEN",
)

CASE_COUNT = 40
WORK_FAMILY_CAP = 4
FIXTURE_TXT_COUNT = 180
FIXTURE_ALLOWED_ENTRIES = frozenset({"lawref_seed.json"})
FIXTURE_ROLLUP_SHA256 = "50b48668cba5b89d75af0604a78004404310e36377679984273fa0a883053c9d"
CODER_COUNT = 2
UNITS_TOTAL = 40
MEASUREMENT_STATUSES = ("computed", "undefined")

LIFECYCLE: dict[str, Any] = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}

# Claim keys are re-checked by VALUE, never by name alone: the frozen schemas
# legitimately *declare* these keys with pinned values, so a name-only scan
# would reject the contract it is supposed to protect.
CLAIM_VALUE_RULES: tuple[tuple[str, tuple[Any, ...], str], ...] = (
    ("threshold", (None,), "THRESHOLD_REQUESTED"),
    ("classification", ("not-authorized",), "CLASSIFICATION_REQUESTED"),
    ("promotion", ("none",), "PROMOTION_CLAIM"),
    ("authority", ("none",), "AUTHORITY_CLAIM"),
    ("suggestion_status", ("none-provided",), "AUTHORITY_CLAIM"),
    ("model_invoked", (False,), "MODEL_INVOKED"),
    ("is_gold", (False,), "GOLD_CLAIM"),
)
# Keys that may only ever be absent (or pinned false): a present, truthy value is
# a fabricated classification or gold claim.
CLAIM_ABSENT_KEYS: dict[str, str] = {
    "gold_labels": "GOLD_CLAIM",
    "gold_label": "GOLD_CLAIM",
    "pass_fail": "CLASSIFICATION_REQUESTED",
    "per_aspect_rate": "CLASSIFICATION_REQUESTED",
    "per_aspect_rates": "CLASSIFICATION_REQUESTED",
    "precision": "CLASSIFICATION_REQUESTED",
    "recall": "CLASSIFICATION_REQUESTED",
    "f1": "CLASSIFICATION_REQUESTED",
    "accuracy": "CLASSIFICATION_REQUESTED",
    "verdict": "CLASSIFICATION_REQUESTED",
    "agreement_threshold": "THRESHOLD_REQUESTED",
}
# Declaration containers whose own wording enumerates a forbidden token; they are
# pinned by value, so matching their content is not a leak.  ``is_gold`` is
# exempt because the frozen contract legitimately declares it pinned false -- a
# fabricated gold claim is caught by the claim guard instead.
EXEMPT_KEYS = frozenset(
    {
        "non_claims",
        "diagnostics",
        "forbidden_substrings",
        "forbidden_keys",
        "forbidden_seed_keys",
        "forbidden_battery_keys",
        "forbidden_case_keys",
        "is_gold",
    }
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
FORBIDDEN_EXACT_KEYS = frozenset(
    {"seed_span", "rule_seed_span", "rule_seed", "ds_span", "seed_slots"}
)
# The coder kit *must* carry the fragment path and digest (D478: the decoded
# text is not duplicated), so a path is not a leak signal here.
FORBIDDEN_VALUE_SUBSTRINGS = (
    "rule_seed",
    "seed_span",
    "ds_span",
    "lawref_seed",
    "AnnotationSuggestion:",
)
PROMOTION_PROSE_RE = re.compile(
    r"\bR0(?:35|38|70|74)\b[^.\n]{0,60}\b(?:closed|validated|promoted|complete|accepted)\b",
    re.IGNORECASE,
)

ISOLATION_TOKENS = ("m207-s02", "m207_s02", "prd/annotation")
ISOLATION_SKIP_PARTS = frozenset({"target", ".git", "node_modules", "__pycache__", ".venv"})
ISOLATION_MAX_BYTES = 4 * 1024 * 1024

BATTERY_CLOSED_KEYS = frozenset(
    {
        "checks",
        "human_pilot_performed",
        "lifecycle",
        "model_invoked",
        "non_claims",
        "pins",
        "schema",
        "schema_version",
    }
)
BATTERY_CHECK_CLOSED_KEYS = frozenset({"check_id", "command", "diagnostic", "exit_code", "status"})
BATTERY_FORBIDDEN_KEY_TOKENS = frozenset(
    {"duration_ms", "elapsed_ms", "generated_at", "wall_clock"}
)
BATTERY_DIAGNOSTIC_NONE = "none"

FENCE_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
GATE_DIAGNOSTIC_RE = re.compile(r"FAIL ([A-Z][A-Z0-9_]+):")
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
TOKEN_SEPARATOR_RE = re.compile(r"[^A-Za-z0-9]+")

# The derived pilot artifacts this verifier scans when they exist, and the frozen
# schema block each one is bound to (the schema id and closed keys are read from
# the pinned schemas file, never restated here).
DERIVED_ARTIFACTS: tuple[str, ...] = (
    "intake_record",
    "agreement_report",
    "inventory",
    "adjudication_record",
    "receipt",
)
SCHEMA_BLOCK_NAMES: dict[str, str] = {
    "intake_record": "intake_record",
    "agreement_report": "agreement_report",
    "inventory": "disagreement_inventory",
    "adjudication_record": "adjudication_record",
    "receipt": "pilot_receipt",
}

Failures = list[tuple[str, str]]


class VerificationError(Exception):
    """A fail-closed condition carrying a named diagnostic."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def _fail(failures: Failures, diagnostic: str, detail: str) -> None:
    failures.append((diagnostic, detail))


def guard_output(text: str) -> str:
    """This tool may never emit the human-gate marker (T07 owns it)."""
    if HUMAN_GATE_MARKER in text:
        raise VerificationError(
            "AUTHORITY_CLAIM",
            "the machinery verifier would emit the human-gate marker; only the closing chain "
            "may print it, and only over two real human codings",
        )
    return text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_artifact(
    root: Path,
    raw: str,
    label: str,
    *,
    suffix: str,
    prefix: str | None,
    directory: bool = False,
) -> Path:
    """Resolve a repository-relative artifact path, fail-closed on escapes."""
    if (
        not raw
        or "\x00" in raw
        or raw.startswith("/")
        or "\\" in raw
        or (len(raw) > 1 and raw[1] == ":")
    ):
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} must be a POSIX relative path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} may not escape the repository")
    if not directory and suffix and relative.suffix != suffix:
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} must have suffix {suffix}")
    if prefix and not relative.as_posix().startswith(prefix):
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} must live under {prefix}")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise VerificationError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def chain_path(root: Path, raw: str) -> Path:
    """Resolve the S01 closeout chain: read-only, so an absolute stub is allowed.

    The chain is executed, never written, so a temp-directory stub is accepted
    exactly as the intake's single-submission probe accepts one; every *artifact*
    path stays locked to its declared prefix.
    """
    if raw.startswith("/"):
        path = Path(raw)
        if "\\" in raw or "\x00" in raw or path.suffix != ".sh":
            raise VerificationError("UNSAFE_PATH", f"chain={raw!r} must be an absolute .sh path")
        return path
    return resolve_artifact(root, raw, "chain", suffix=".sh", prefix=None)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise VerificationError("DUPLICATE_JSON_KEY", f"duplicate object key {key!r}")
        seen[key] = value
    return seen


def read_text(path: Path, label: str) -> str:
    if not path.is_file():
        raise VerificationError("MISSING_ARTIFACT", f"{label} not found at {path}")
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError("SCHEMA_PARSE_ERROR", f"{label} is not UTF-8: {exc}") from exc


def load_json(path: Path, label: str) -> Any:
    text = read_text(path, label)
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except VerificationError:
        raise
    except json.JSONDecodeError as exc:
        raise VerificationError("SCHEMA_PARSE_ERROR", f"{label} is not closed JSON: {exc}") from exc


def fenced_contracts(path: Path, label: str) -> list[Any]:
    blocks: list[Any] = []
    for index, block in enumerate(FENCE_RE.findall(read_text(path, label))):
        try:
            blocks.append(json.loads(block, object_pairs_hook=_reject_duplicate_keys))
        except VerificationError:
            raise
        except json.JSONDecodeError as exc:
            raise VerificationError(
                "SCHEMA_PARSE_ERROR", f"{label} fenced block {index} is not closed JSON: {exc}"
            ) from exc
    return blocks


def key_tokens(key: str) -> list[str]:
    return [token for token in TOKEN_SEPARATOR_RE.split(CAMEL_BOUNDARY_RE.sub("_", key)) if token]


def forbidden_key_hit(name: str) -> str | None:
    if set(key_tokens(name)) & FORBIDDEN_KEY_TOKENS:
        return "predicted-answer"
    if name.strip().lower() in FORBIDDEN_EXACT_KEYS:
        return "rule-seed-span"
    return None


# --------------------------------------------------------------------------- #
# Frozen pins and the closed diagnostic table.
# --------------------------------------------------------------------------- #


def check_pins(artifacts: dict[str, Path | None], failures: Failures) -> int:
    pinned = 0
    for name, (rel, pin) in PINS.items():
        path = artifacts.get(name)
        if path is None:
            continue
        if not path.is_file():
            _fail(failures, "MISSING_ARTIFACT", f"{rel} not found at {path}")
            continue
        digest = sha256_file(path)
        if digest != pin:
            _fail(failures, "FROZEN_SOURCE_DRIFT", f"{rel} sha256 {digest} != pinned {pin}")
        else:
            pinned += 1
    return pinned


def check_diagnostic_table(schemas: Any, failures: Failures) -> int:
    """Every name this tool may speak must exist in the frozen table."""
    if not isinstance(schemas, dict):
        _fail(failures, "MISSING_SCHEMA", "the S02 schemas block is not a JSON object")
        return 0
    table = schemas.get("diagnostics")
    if not isinstance(table, list) or not all(isinstance(name, str) for name in table):
        _fail(failures, "MISSING_SCHEMA", "schemas carry no closed $.diagnostics list")
        return 0
    if len(set(table)) != len(table):
        _fail(failures, "DIAGNOSTIC_TABLE_DRIFT", "the frozen diagnostic table repeats a name")
    missing = sorted(set(LOCAL_DIAGNOSTICS) - set(table))
    if missing:
        _fail(
            failures,
            "DIAGNOSTIC_TABLE_DRIFT",
            f"this verifier would speak name(s) absent from the frozen table: {missing}",
        )
    return len(table)


# --------------------------------------------------------------------------- #
# Counters, lifecycle markers and claim guards.
# --------------------------------------------------------------------------- #


def check_counters(manifest: Any, kits: dict[str, Any], failures: Failures) -> dict[str, int]:
    cases = manifest.get("cases") if isinstance(manifest, dict) else None
    rows = cases if isinstance(cases, list) else []
    if len(rows) != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case manifest holds {len(rows)} case(s), expected {CASE_COUNT}",
        )
    if isinstance(manifest, dict) and manifest.get("case_count") != len(rows):
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"case_count {manifest.get('case_count')!r} != len(cases) {len(rows)}",
        )
    families: dict[str, int] = {}
    for index, case in enumerate(rows):
        if not isinstance(case, dict):
            _fail(failures, "SCHEMA_KEY_DRIFT", f"cases[{index}] is not a JSON object")
            continue
        family = case.get("work_family")
        if isinstance(family, str) and family:
            families[family] = families.get(family, 0) + 1
    cap = manifest.get("work_family_cap") if isinstance(manifest, dict) else None
    if cap != WORK_FAMILY_CAP:
        _fail(
            failures,
            "WORK_FAMILY_DOMINANCE",
            f"case manifest declares work_family_cap={cap!r}, expected {WORK_FAMILY_CAP}",
        )
    for family, weight in sorted(families.items()):
        if weight > WORK_FAMILY_CAP:
            _fail(
                failures,
                "WORK_FAMILY_DOMINANCE",
                f"work family {family!r} contributes {weight} cases, cap is {WORK_FAMILY_CAP}",
            )
    for name, kit in sorted(kits.items()):
        if not isinstance(kit, dict):
            continue
        kit_cases = kit.get("cases")
        if not isinstance(kit_cases, list) or len(kit_cases) != CASE_COUNT:
            _fail(
                failures,
                "CASE_COUNT_OUT_OF_RANGE",
                f"kit {name} carries {len(kit_cases) if isinstance(kit_cases, list) else 'no'} "
                f"case(s), expected {CASE_COUNT}",
            )
        if kit.get("case_count") != CASE_COUNT:
            _fail(
                failures,
                "CASE_COUNT_OUT_OF_RANGE",
                f"kit {name} declares case_count={kit.get('case_count')!r}, expected {CASE_COUNT}",
            )
        if kit.get("work_family_cap") != WORK_FAMILY_CAP:
            _fail(
                failures,
                "WORK_FAMILY_DOMINANCE",
                f"kit {name} declares work_family_cap={kit.get('work_family_cap')!r}, "
                f"expected {WORK_FAMILY_CAP}",
            )
    return {
        "cases": len(rows),
        "work_family_cap": int(cap) if isinstance(cap, int) else 0,
        "work_families": len(families),
    }


def lifecycle_blocks(
    artifacts: dict[str, Path | None], failures: Failures
) -> list[tuple[str, Any]]:
    blocks: list[tuple[str, Any]] = []
    protocol = artifacts.get("s02_protocol")
    if protocol is not None and protocol.is_file():
        try:
            for index, block in enumerate(fenced_contracts(protocol, "S02 protocol")):
                blocks.append((f"protocol[fence {index}]", block))
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    for name, label in (
        ("s02_schemas", "S02 schemas"),
        ("kit_pass1", "kit-pass1"),
        ("kit_pass2", "kit-pass2"),
    ):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            blocks.append((label, load_json(path, label)))
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    return blocks


def check_lifecycle(artifacts: dict[str, Path | None], failures: Failures) -> int:
    observed = 0
    for label, block in lifecycle_blocks(artifacts, failures):
        if not isinstance(block, dict) or "lifecycle" not in block:
            _fail(
                failures,
                "MISSING_LIFECYCLE_MARKER",
                f"{label} carries no lifecycle marker block",
            )
            continue
        lifecycle = block["lifecycle"]
        if not isinstance(lifecycle, dict) or set(lifecycle) != set(LIFECYCLE):
            _fail(
                failures,
                "MISSING_LIFECYCLE_MARKER",
                f"{label}.lifecycle keys "
                f"{sorted(lifecycle) if isinstance(lifecycle, dict) else lifecycle!r} differ "
                f"from {sorted(LIFECYCLE)}",
            )
            continue
        observed += 1
        for marker, expected in LIFECYCLE.items():
            if lifecycle[marker] != expected:
                _fail(
                    failures,
                    "MISSING_LIFECYCLE_MARKER",
                    f"{label}.lifecycle.{marker} {lifecycle[marker]!r} != {expected!r}",
                )
    return observed


def claim_values_ok(key: str, value: Any) -> bool:
    """A pinned claim key may hold its pinned value, or a list of that value."""
    if isinstance(value, list):
        return bool(value) and all(claim_values_ok(key, item) for item in value)
    return value in dict((name, allowed) for name, allowed, _ in CLAIM_VALUE_RULES)[key]


def scan_claims(node: Any, pointer: str, failures: Failures) -> None:
    """Re-check the pinned claim values by value, at any nesting depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            if name in EXEMPT_KEYS or name.endswith("_keys"):
                continue
            rule = next((entry for entry in CLAIM_VALUE_RULES if entry[0] == name), None)
            if rule is not None and not claim_values_ok(name, value):
                _fail(
                    failures,
                    rule[2],
                    f"{pointer}/{key}={value!r} is not the pinned {name} value",
                )
            if name in CLAIM_ABSENT_KEYS and value not in (None, False, [], {}):
                _fail(
                    failures,
                    CLAIM_ABSENT_KEYS[name],
                    f"{pointer}/{key}={value!r} introduces a claim the slice forbids",
                )
            scan_claims(value, f"{pointer}/{key}", failures)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_claims(item, f"{pointer}[{index}]", failures)


def check_claims(artifacts: dict[str, Path | None], failures: Failures) -> int:
    scanned = 0
    for label, block in lifecycle_blocks(artifacts, failures):
        scan_claims(block, label.replace(" ", "-"), failures)
        scanned += 1
    for name in ("cases",):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            scan_claims(load_json(path, name), "cases", failures)
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
        scanned += 1
    for name in ("codebook", "s02_protocol", "s02_schemas"):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            text = read_text(path, name)
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        scanned += 1
        for match in PROMOTION_PROSE_RE.findall(text):
            _fail(
                failures,
                "PROMOTION_CLAIM",
                f"{name} claims a guardrail promotion: {match!r}",
            )
    return scanned


# --------------------------------------------------------------------------- #
# Leakage and seed integrity.
# --------------------------------------------------------------------------- #


def scan_payload(
    node: Any,
    pointer: str,
    failures: Failures,
    *,
    exempt: bool = False,
    key_list: bool = False,
    needles: tuple[str, ...] = FORBIDDEN_VALUE_SUBSTRINGS,
) -> None:
    """Reject predicted-answer keys and substrings at any nesting depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            if not exempt and name not in EXEMPT_KEYS:
                hit = forbidden_key_hit(name)
                if hit:
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"{pointer}/{key} is a forbidden {hit} field",
                    )
            scan_payload(
                value,
                f"{pointer}/{key}",
                failures,
                exempt=exempt or name in EXEMPT_KEYS,
                key_list=name.endswith("_keys") and name not in EXEMPT_KEYS,
                needles=needles,
            )
    elif isinstance(node, list):
        for index, value in enumerate(node):
            if key_list and not exempt and isinstance(value, str) and value not in EXEMPT_KEYS:
                hit = forbidden_key_hit(value)
                if hit:
                    _fail(
                        failures,
                        "LEAK_FORBIDDEN_KEY",
                        f"{pointer}[{index}] declares {value!r}, a forbidden {hit} field",
                    )
            scan_payload(
                value,
                f"{pointer}[{index}]",
                failures,
                exempt=exempt,
                needles=needles,
            )
    elif isinstance(node, str) and not exempt:
        for needle in needles:
            if needle in node:
                _fail(
                    failures,
                    "LEAK_FORBIDDEN_KEY",
                    f"{pointer} contains forbidden substring {needle!r}",
                )
                return


def check_leakage(artifacts: dict[str, Path | None], schemas: Any, failures: Failures) -> int:
    before = len(failures)
    forbidden_case_keys = frozenset({"fragment_text", "slot_values", "slots", "work_family"})
    if isinstance(schemas, dict):
        declared = schemas.get("schemas", {}).get("coder_kit", {}).get("forbidden_case_keys")
        if isinstance(declared, list) and declared:
            forbidden_case_keys = frozenset(str(name) for name in declared)
    for name, label in (("kit_pass1", "kit-pass1"), ("kit_pass2", "kit-pass2")):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            kit = load_json(path, label)
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        scan_payload(kit, label, failures)
        for case in kit.get("cases", []) if isinstance(kit, dict) else []:
            if not isinstance(case, dict):
                continue
            case_id = str(case.get("case_id"))
            for key in sorted(set(case) & forbidden_case_keys):
                diagnostic = "KIT_TEXT_INLINED" if key == "fragment_text" else "LEAK_FORBIDDEN_KEY"
                _fail(
                    failures,
                    diagnostic,
                    f"{label}/{case_id} carries {key!r}, which the frozen kit schema forbids",
                )
        template = kit.get("submission_template") if isinstance(kit, dict) else None
        if isinstance(template, dict) and template.get("cases"):
            _fail(
                failures,
                "KIT_TEXT_INLINED",
                f"{label}.submission_template ships coded cases: a kit is not a submission",
            )
    for name, label in (("s02_protocol", "S02 protocol"), ("s02_schemas", "S02 schemas")):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            blocks = fenced_contracts(path, label) if path.suffix == ".md" else []
            if path.suffix == ".json":
                blocks = [load_json(path, label)]
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        for index, block in enumerate(blocks):
            scan_payload(block, f"{label}[{index}]", failures)
    return len(failures) - before


def check_seed(artifacts: dict[str, Path | None], failures: Failures) -> tuple[int, str]:
    fixture_dir = artifacts.get("fixture_dir")
    if fixture_dir is None:
        return 0, ""
    if not fixture_dir.is_dir():
        _fail(failures, "MISSING_ARTIFACT", f"fixture dir not found at {fixture_dir}")
        return 0, ""
    entries = sorted(fixture_dir.iterdir())
    stray_dirs = [entry.name for entry in entries if entry.is_dir()]
    if stray_dirs:
        _fail(failures, "SEED_ENLARGED", f"fixture dir gained directorie(s): {stray_dirs[:3]}")
    extra = [
        entry.name
        for entry in entries
        if entry.is_file() and entry.suffix != ".txt" and entry.name not in FIXTURE_ALLOWED_ENTRIES
    ]
    if extra:
        _fail(failures, "SEED_ENLARGED", f"new non-fragment fixture file(s): {extra[:3]}")
    txt = [entry for entry in entries if entry.is_file() and entry.suffix == ".txt"]
    if len(txt) != FIXTURE_TXT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"fixture dir holds {len(txt)} .txt file(s), expected {FIXTURE_TXT_COUNT}",
        )
    digest = hashlib.sha256()
    for entry in txt:
        digest.update(entry.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(entry).encode("utf-8"))
        digest.update(b"\n")
    rollup = digest.hexdigest()
    if rollup != FIXTURE_ROLLUP_SHA256:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"fixture rollup {rollup} != pinned {FIXTURE_ROLLUP_SHA256}",
        )
    return len(txt), rollup


# --------------------------------------------------------------------------- #
# Prompt isolation.
# --------------------------------------------------------------------------- #


def check_prompt_isolation(root: Path, failures: Failures) -> int:
    crates = root / "crates"
    if not crates.is_dir():
        return 0
    scanned = 0
    for path in sorted(crates.rglob("*")):
        if not path.is_file():
            continue
        if ISOLATION_SKIP_PARTS.intersection(path.parts):
            continue
        if path.suffix != ".rs" and path.name not in ("build.rs", "Cargo.toml"):
            continue
        try:
            if path.stat().st_size > ISOLATION_MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _fail(failures, "MISSING_ARTIFACT", f"cannot read {path}: {exc}")
            continue
        scanned += 1
        for token in ISOLATION_TOKENS:
            if token in text:
                _fail(
                    failures,
                    "PROMPT_ISOLATION_VIOLATION",
                    f"{path.relative_to(root)} references human-pilot artifact token {token!r}",
                )
                break
    return scanned


# --------------------------------------------------------------------------- #
# Derived pilot artifacts (unpinned by design: absent until a human pilot runs).
# --------------------------------------------------------------------------- #


def is_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def derived_shape(schemas: Any, name: str, failures: Failures) -> tuple[str, tuple[str, ...]]:
    """Read the frozen schema id and closed-key set for one derived artifact."""
    block_name = SCHEMA_BLOCK_NAMES[name]
    block = schemas.get("schemas", {}).get(block_name) if isinstance(schemas, dict) else None
    if not isinstance(block, dict):
        _fail(failures, "MISSING_SCHEMA", f"the S02 schemas carry no {block_name} block")
        return "", ()
    closed = block.get("closed_keys")
    if not isinstance(closed, list) or not closed:
        _fail(failures, "MISSING_SCHEMA", f"{block_name} declares no closed key set")
        return str(block.get("schema_id") or ""), ()
    return str(block.get("schema_id") or ""), tuple(str(key) for key in closed)


def check_closed(
    label: str,
    doc: Any,
    schema_id: str,
    closed: tuple[str, ...],
    failures: Failures,
) -> bool:
    """A derived artifact must carry exactly the frozen schema id and key set."""
    if not isinstance(doc, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label} is not a JSON object")
        return False
    if schema_id and doc.get("schema") != schema_id:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"{label}.schema={doc.get('schema')!r} != the frozen {schema_id!r}",
        )
    if closed and set(doc) != set(closed):
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label} keys {sorted(set(doc) ^ set(closed))} differ from the frozen closed set",
        )
        return False
    return True


def check_derived(
    artifacts: dict[str, Path | None],
    schemas: Any,
    families: dict[str, str],
    failures: Failures,
) -> dict[str, Any]:
    """Scan every derived pilot artifact that exists, and the freeze order."""
    docs: dict[str, Any] = {}
    for name in DERIVED_ARTIFACTS:
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            docs[name] = load_json(path, name)
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    for name, doc in sorted(docs.items()):
        schema_id, closed = derived_shape(schemas, name, failures)
        check_closed(name, doc, schema_id, closed, failures)
        scan_claims(doc, name, failures)
        scan_payload(doc, name, failures)
        if not isinstance(doc, dict) or doc.get("lifecycle") != LIFECYCLE:
            _fail(
                failures,
                "MISSING_LIFECYCLE_MARKER",
                f"{name}.lifecycle is not the frozen marker set",
            )

    intake = docs.get("intake_record")
    if isinstance(intake, dict):
        universe = intake.get("case_universe")
        covered = intake.get("cases_covered")
        subs = intake.get("submissions")
        rows = subs if isinstance(subs, list) else []
        if len(universe or []) != CASE_COUNT or len(covered or []) != CASE_COUNT:
            _fail(
                failures,
                "CASE_COUNT_OUT_OF_RANGE",
                f"the intake record covers {len(universe or [])}/{len(covered or [])} cases, "
                f"expected {CASE_COUNT}",
            )
        if sorted(universe or []) != sorted(covered or []):
            _fail(failures, "SCHEMA_KEY_DRIFT", "cases_covered != case_universe")
        if len(set(universe or [])) != len(universe or []):
            _fail(failures, "UNKNOWN_CASE_ID", "case_universe repeats a case id")
        if len(rows) != CODER_COUNT or intake.get("submission_count") != CODER_COUNT:
            _fail(
                failures,
                "ONE_CODER_ONLY",
                f"the intake record admits {len(rows)} submission(s); agreement needs exactly "
                f"{CODER_COUNT} independent codings (RC28-F01)",
            )
        else:
            passes = [row.get("coder_pass") for row in rows if isinstance(row, dict)]
            ids = [row.get("coder_id") for row in rows if isinstance(row, dict)]
            digests = [row.get("sha256") for row in rows if isinstance(row, dict)]
            if sorted(passes) != [1, 2]:
                _fail(failures, "ONE_CODER_ONLY", f"admitted coder passes {passes} != [1, 2]")
            if len(set(ids)) != CODER_COUNT:
                _fail(
                    failures,
                    "DUPLICATE_CODER_ID",
                    "both admitted passes carry the same coder_id: there is no second coder",
                )
            if len(set(digests)) != CODER_COUNT:
                _fail(failures, "ONE_CODER_ONLY", "both admitted passes are the same bytes")

    report = docs.get("agreement_report")
    if isinstance(report, dict):
        if report.get("pre_adjudication") is not True:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                "the agreement report is not marked pre-adjudication",
            )
        if report.get("units_total") != UNITS_TOTAL:
            _fail(
                failures,
                "CASE_COUNT_OUT_OF_RANGE",
                f"the agreement report declares units_total={report.get('units_total')!r}, "
                f"expected {UNITS_TOTAL}",
            )
        top_alpha = report.get("alpha")
        if top_alpha == 1.0:
            _fail(
                failures,
                "PERFECT_AGREEMENT_UNCOMPUTED",
                "the report publishes a pooled top-level alpha=1.0",
            )
        elif top_alpha is not None:
            _fail(
                failures,
                "CLASSIFICATION_REQUESTED",
                "the report publishes a pooled top-level alpha; alpha is defined per axis only "
                "(D483), and per-aspect aggregates belong to S03",
            )
        axes = report.get("axes")
        if not isinstance(axes, list) or not axes:
            _fail(failures, "SCHEMA_KEY_DRIFT", "the agreement report carries no axis rows")
        else:
            for index, row in enumerate(axes):
                if not isinstance(row, dict):
                    _fail(failures, "SCHEMA_KEY_DRIFT", f"axes[{index}] is not a JSON object")
                    continue
                total = row.get("units_total")
                used = row.get("units_used")
                excluded = row.get("units_excluded")
                if total != UNITS_TOTAL:
                    _fail(
                        failures,
                        "CASE_COUNT_OUT_OF_RANGE",
                        f"axes[{index}].units_total={total!r} != the frozen {UNITS_TOTAL}",
                    )
                if not all(isinstance(value, int) for value in (used, excluded)):
                    _fail(
                        failures,
                        "DENOMINATOR_MISMATCH",
                        f"axes[{index}] carries non-integer units_used/units_excluded",
                    )
                elif used + excluded != total:
                    _fail(
                        failures,
                        "DENOMINATOR_MISMATCH",
                        f"axes[{index}] units_used({used}) + units_excluded({excluded}) != "
                        f"units_total({total!r})",
                    )
                status = row.get("measurement_status")
                if status not in MEASUREMENT_STATUSES:
                    _fail(
                        failures,
                        "VOCABULARY_DRIFT",
                        f"axes[{index}].measurement_status={status!r} is outside "
                        f"{list(MEASUREMENT_STATUSES)}",
                    )
                alpha = row.get("alpha")
                if alpha == 1.0 and (not isinstance(used, int) or used < 2):
                    _fail(
                        failures,
                        "PERFECT_AGREEMENT_UNCOMPUTED",
                        f"axes[{index}] claims alpha=1 without coincident codings "
                        f"(units_used={used!r})",
                    )
                if status in MEASUREMENT_STATUSES and (alpha is None) != (status == "undefined"):
                    _fail(
                        failures,
                        "DENOMINATOR_MISMATCH",
                        f"axes[{index}] alpha={alpha!r} disagrees with measurement_status={status!r}",
                    )
            if isinstance(intake, dict):
                admitted = {
                    str(row.get("submission_id")): row.get("sha256")
                    for row in intake.get("submissions") or []
                    if isinstance(row, dict)
                }
                refs = report.get("submission_refs")
                if not isinstance(refs, list) or len(refs) != CODER_COUNT:
                    _fail(
                        failures,
                        "ONE_CODER_ONLY",
                        "the agreement report does not name two submission refs",
                    )
                else:
                    for index, ref in enumerate(refs):
                        if not isinstance(ref, dict):
                            continue
                        pinned = admitted.get(str(ref.get("submission_id")))
                        if pinned is None or pinned != ref.get("sha256"):
                            _fail(
                                failures,
                                "FROZEN_SOURCE_DRIFT",
                                f"submission_refs[{index}] does not match the admitted bytes: "
                                "the frozen score is not pinned to the admitted codings",
                            )

    inventory = docs.get("inventory")
    if isinstance(inventory, dict):
        entries = inventory.get("entries")
        if not isinstance(entries, list):
            _fail(failures, "SCHEMA_KEY_DRIFT", "the inventory carries no entries list")
        else:
            if inventory.get("disagreement_count") != len(entries):
                _fail(
                    failures,
                    "SCHEMA_KEY_DRIFT",
                    f"disagreement_count={inventory.get('disagreement_count')!r} != "
                    f"len(entries)={len(entries)}",
                )
            weights: dict[str, int] = {}
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    _fail(failures, "SCHEMA_KEY_DRIFT", f"entries[{index}] is not a JSON object")
                    continue
                case_id = str(entry.get("case_id"))
                family = families.get(case_id)
                if family is None:
                    _fail(
                        failures,
                        "UNKNOWN_CASE_ID",
                        f"entries[{index}].case_id={case_id!r} is not one of the {CASE_COUNT} "
                        "frozen cases",
                    )
                    continue
                if entry.get("work_family") != family:
                    _fail(
                        failures,
                        "FROZEN_SOURCE_DRIFT",
                        f"entries[{index}].work_family={entry.get('work_family')!r} is not the "
                        f"frozen manifest join {family!r}",
                    )
                weights[family] = weights.get(family, 0) + 1
            for family, weight in sorted(weights.items()):
                if weight > WORK_FAMILY_CAP:
                    _fail(
                        failures,
                        "WORK_FAMILY_DOMINANCE",
                        f"work family {family!r} contributes {weight} disagreements, cap is "
                        f"{WORK_FAMILY_CAP}",
                    )

    report_path = artifacts.get("agreement_report")
    record_digest = ""
    record_path = artifacts.get("adjudication_record")
    if record_path is not None and record_path.is_file():
        record_digest = sha256_file(record_path)
    record = docs.get("adjudication_record")
    if isinstance(record, dict):
        if record.get("append_only") is not True:
            _fail(failures, "FROZEN_SOURCE_DRIFT", "the adjudication record is not append-only")
        if record.get("adjudicator_provenance") != "human-reviewed":
            _fail(
                failures,
                "ADJUDICATOR_PROVENANCE_NOT_HUMAN",
                f"the record attests adjudicator_provenance="
                f"{record.get('adjudicator_provenance')!r}",
            )
        if record.get("unresolved_count") != 0:
            _fail(
                failures,
                "UNRESOLVED_NONZERO",
                f"the record leaves {record.get('unresolved_count')!r} inventoried "
                "disagreement(s) unresolved",
            )
        entries = record.get("entries")
        if isinstance(entries, list) and (
            record.get("entry_count") != len(entries)
            or record.get("resolved_count") != len(entries)
        ):
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                "entry_count/resolved_count disagree with len(entries)",
            )
        digest = record.get("pre_adjudication_agreement_sha256")
        if not is_digest(digest):
            _fail(failures, "SCHEMA_KEY_DRIFT", "the record carries no pre-adjudication digest")
        elif report_path is not None and report_path.is_file():
            on_disk = sha256_file(report_path)
            if on_disk != digest:
                _fail(
                    failures,
                    "FROZEN_SOURCE_DRIFT",
                    "the adjudication record pins a pre-adjudication score that is not the "
                    "agreement report on disk: the report was re-pinned after adjudication",
                )

    receipt = docs.get("receipt")
    human_pilot_performed = False
    if isinstance(receipt, dict):
        if receipt.get("human_pilot_performed") is not True:
            _fail(
                failures,
                "HUMAN_PILOT_ABSENT",
                "a pilot receipt exists but does not attest a performed human pilot",
            )
        else:
            human_pilot_performed = True
        if receipt.get("coder_count") != CODER_COUNT:
            _fail(
                failures,
                "ONE_CODER_ONLY",
                f"the receipt declares coder_count={receipt.get('coder_count')!r}, expected "
                f"{CODER_COUNT}",
            )
        adjudicators = receipt.get("adjudicator_count")
        if not isinstance(adjudicators, int) or adjudicators < 1:
            _fail(
                failures,
                "HUMAN_PILOT_ABSENT",
                "the receipt attests no human adjudicator",
            )
        if receipt.get("case_count") != CASE_COUNT:
            _fail(
                failures,
                "CASE_COUNT_OUT_OF_RANGE",
                f"the receipt declares case_count={receipt.get('case_count')!r}, expected "
                f"{CASE_COUNT}",
            )
        for field in ("pre_adjudication_agreement_sha256", "adjudication_record_sha256"):
            if not is_digest(receipt.get(field)):
                _fail(failures, "SCHEMA_KEY_DRIFT", f"the receipt carries no {field} digest")
        if record_digest and receipt.get("adjudication_record_sha256") != record_digest:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                "the receipt pins an adjudication record that is not the record on disk",
            )
        for name in ("agreement_report", "adjudication_record"):
            path = artifacts.get(name)
            if path is None or not path.is_file():
                _fail(
                    failures,
                    "MISSING_ARTIFACT",
                    f"a pilot receipt exists but {name} is missing: the pair is incomplete",
                )
    return {"present": len(docs), "human_pilot_performed": human_pilot_performed}


# --------------------------------------------------------------------------- #
# The tracked battery.
# --------------------------------------------------------------------------- #


def wallclock_hits(node: Any, pointer: str = "$") -> list[str]:
    """Every key that would persist wall-clock data into the battery."""
    hits: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            normalized = "_".join(key_tokens(str(key))).lower()
            if normalized in BATTERY_FORBIDDEN_KEY_TOKENS:
                hits.append(f"{pointer}/{key}")
            hits.extend(wallclock_hits(value, f"{pointer}/{key}"))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            hits.extend(wallclock_hits(item, f"{pointer}[{index}]"))
    return hits


def check_battery_rows(rows: Any, label: str, failures: Failures) -> int:
    """The battery's check rows must be exactly the chain's closed check set."""
    if not isinstance(rows, list) or not rows:
        _fail(failures, "EMPTY_SUITE", f"{label} holds no check row")
        return 0
    seen: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != BATTERY_CHECK_CLOSED_KEYS:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"{label}[{index}] is not a closed battery check row",
            )
            continue
        identifier = str(row.get("check_id"))
        seen.append(identifier)
        if row.get("status") != "pass" or row.get("exit_code") != 0:
            _fail(failures, "SUBCLI_FAILURE", f"battery check {identifier!r} is not green")
    if len(set(seen)) != len(seen):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the battery repeats a check_id")
    missing = sorted(set(CHAIN_CHECKS) - set(seen))
    unexpected = sorted(set(seen) - set(CHAIN_CHECKS))
    if missing or unexpected:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"the battery check set differs from the chain: missing={missing} "
            f"unexpected={unexpected}",
        )
    return len(rows)


def check_tracked_battery(path: Path | None, failures: Failures) -> int:
    """Validate the tracked S02 battery when it exists (it never hashes itself)."""
    if path is None or not path.is_file():
        return 0
    try:
        doc = load_json(path, "S02 battery")
    except VerificationError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return 0
    if not isinstance(doc, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the S02 battery is not a JSON object")
        return 0
    if set(doc) != BATTERY_CLOSED_KEYS:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"S02 battery keys {sorted(set(doc) ^ BATTERY_CLOSED_KEYS)} differ from the frozen "
            "closed set",
        )
    if doc.get("schema") != BATTERY_SCHEMA_ID:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"S02 battery schema={doc.get('schema')!r} != {BATTERY_SCHEMA_ID!r}",
        )
    for hit in wallclock_hits(doc):
        _fail(
            failures,
            "BATTERY_WALLCLOCK_FORBIDDEN",
            f"the tracked battery persists wall-clock data at {hit}",
        )
    if doc.get("model_invoked") is not False:
        _fail(failures, "MODEL_INVOKED", "the battery claims a model was invoked")
    if doc.get("lifecycle") != LIFECYCLE:
        _fail(failures, "MISSING_LIFECYCLE_MARKER", "battery lifecycle is not the frozen set")
    return check_battery_rows(doc.get("checks"), "battery.checks", failures)


# --------------------------------------------------------------------------- #
# Subprocesses: the five gates and the S01 closeout chain.
# --------------------------------------------------------------------------- #


def run_gates(root: Path, failures: Failures) -> tuple[int, list[dict[str, Any]]]:
    passed = 0
    rows: list[dict[str, Any]] = []
    for name, relative, marker in GATES:
        command = [sys.executable, str(ROOT / relative), "check", "--root", str(root)]
        try:
            completed = subprocess.run(
                command, cwd=str(ROOT), text=True, capture_output=True, timeout=180, check=False
            )
        except subprocess.TimeoutExpired:
            _fail(failures, "SUBCLI_FAILURE", f"{relative} timed out after 180s")
            rows.append({"check_id": name, "exit_code": None})
            continue
        except OSError as exc:
            _fail(failures, "SUBCLI_FAILURE", f"{relative} could not be spawned: {exc}")
            rows.append({"check_id": name, "exit_code": None})
            continue
        rows.append({"check_id": name, "exit_code": completed.returncode})
        if completed.returncode == 0:
            if marker not in completed.stdout:
                _fail(
                    failures,
                    "SUBCLI_FAILURE",
                    f"{relative} exited 0 without the {marker} marker",
                )
            else:
                passed += 1
            continue
        diagnostics = GATE_DIAGNOSTIC_RE.findall(completed.stderr)
        if diagnostics:
            for diagnostic in sorted(set(diagnostics)):
                _fail(failures, diagnostic, f"{relative} reported {diagnostic}")
        else:
            _fail(
                failures,
                "SUBCLI_FAILURE",
                f"{relative} exited {completed.returncode} without a named diagnostic",
            )
    return passed, rows


def check_s01_regression(root: Path, chain: Path | None, failures: Failures) -> int:
    """The S01 closeout chain must still be green, as a real subprocess."""
    if chain is None:
        return 0
    if not chain.is_file():
        _fail(
            failures,
            "S01_REGRESSION_FAILED",
            f"the S01 closeout chain is missing at {chain}",
        )
        return 0
    try:
        completed = subprocess.run(
            ["bash", str(chain)],
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=900,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _fail(failures, "S01_REGRESSION_FAILED", f"{chain} timed out after 900s")
        return 0
    except OSError as exc:
        _fail(failures, "S01_REGRESSION_FAILED", f"{chain} could not be spawned: {exc}")
        return 0
    if completed.returncode != 0 or S01_CHAIN_MARKER not in completed.stdout:
        _fail(
            failures,
            "S01_REGRESSION_FAILED",
            f"{chain} exited {completed.returncode} without {S01_CHAIN_MARKER}: the S01 pilot "
            "boundary regressed",
        )
        return 0
    return 1


def describe(path: Path | None, root: Path) -> str:
    if path is None:
        return "none"
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


# --------------------------------------------------------------------------- #
# Modes.
# --------------------------------------------------------------------------- #


def resolve_all(root: Path, args: argparse.Namespace) -> tuple[dict[str, Path | None], Failures]:
    failures: Failures = []
    artifacts: dict[str, Path | None] = {}
    for name, label, default, suffix, prefix, directory in ARTIFACT_SPECS:
        raw = getattr(args, name, default)
        try:
            artifacts[name] = resolve_artifact(
                root, raw, label, suffix=suffix, prefix=prefix, directory=directory
            )
        except VerificationError as exc:
            artifacts[name] = None
            _fail(failures, exc.diagnostic, exc.detail)
    return artifacts, failures


def run(root: Path, args: argparse.Namespace) -> tuple[Failures, str, dict[str, Any]]:
    artifacts, failures = resolve_all(root, args)
    try:
        chain: Path | None = chain_path(root, args.s01_chain)
    except VerificationError as exc:
        chain = None
        _fail(failures, exc.diagnostic, exc.detail)

    pinned = check_pins(artifacts, failures)

    schemas: Any = None
    path = artifacts.get("s02_schemas")
    if path is not None and path.is_file():
        try:
            schemas = load_json(path, "S02 schemas")
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    manifest: Any = None
    path = artifacts.get("cases")
    if path is not None and path.is_file():
        try:
            manifest = load_json(path, "case manifest")
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    kits: dict[str, Any] = {}
    for name in ("kit_pass1", "kit_pass2"):
        path = artifacts.get(name)
        if path is None or not path.is_file():
            continue
        try:
            kits[name] = load_json(path, name)
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)

    diagnostics = check_diagnostic_table(schemas, failures)
    counters = check_counters(manifest, kits, failures)
    lifecycle = check_lifecycle(artifacts, failures)
    check_claims(artifacts, failures)
    check_leakage(artifacts, schemas, failures)
    fixture_txt, rollup = check_seed(artifacts, failures)
    isolation = check_prompt_isolation(root, failures)
    families = {
        str(case.get("case_id")): str(case.get("work_family"))
        for case in (manifest.get("cases") if isinstance(manifest, dict) else []) or []
        if isinstance(case, dict)
    }
    derived = check_derived(artifacts, schemas, families, failures)
    battery_rows = check_tracked_battery(artifacts.get("s02_battery"), failures)
    gates_passed, gate_rows = run_gates(root, failures)
    s01_ok = check_s01_regression(root, chain, failures)

    human = bool(derived.get("human_pilot_performed"))
    base = (
        f"cases={counters['cases']} work_family_cap={counters['work_family_cap']} "
        f"work_families={counters['work_families']} pinned={pinned}/{len(PINS)} "
        f"fixture_txt={fixture_txt} fixture_rollup={rollup[:16]} "
        f"isolation_files={isolation} lifecycle_blocks={lifecycle} diagnostics={diagnostics} "
        f"gates={gates_passed}/{len(GATES)} "
        f"s01_regression={'ok' if s01_ok else 'red'} "
        f"s01_chain={describe(chain, root)} derived_artifacts={derived['present']} "
        f"battery_checks={battery_rows}"
    )
    if human:
        summary = f"{HUMAN_DATA_MARKER} {base} human_pilot_performed=true"
    else:
        summary = f"{MARKER} {base} human_pilot_performed=false human={ABSENT_TOKEN}"
    details = {
        "cases": counters["cases"],
        "work_families": counters["work_families"],
        "pinned": pinned,
        "fixture_txt": fixture_txt,
        "fixture_rollup": rollup,
        "isolation_files": isolation,
        "lifecycle_blocks": lifecycle,
        "diagnostics": diagnostics,
        "gates": gate_rows,
        "s01_regression": s01_ok,
        "derived": derived,
        "battery_checks": battery_rows,
    }
    return failures, summary, details


def report(failures: Failures, summary: str) -> int:
    if failures:
        seen: set[tuple[str, str]] = set()
        for diagnostic, detail in failures:
            entry = (diagnostic, detail)
            if entry in seen:
                continue
            seen.add(entry)
            try:
                print(guard_output(f"FAIL {diagnostic}: {detail}"), file=sys.stderr)
            except VerificationError as exc:
                print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        print(f"FAIL M207_S02_PILOT_GATE: {len(seen)} finding(s)", file=sys.stderr)
        return FAIL_EXIT
    if not summary:
        return 0
    try:
        print(guard_output(summary))
    except VerificationError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return FAIL_EXIT
    return 0


def battery(
    results: Path,
    out: Path,
    artifacts: dict[str, Path | None],
    failures: Failures,
    *,
    write: bool,
) -> int:
    """Assemble the tracked slice battery; read-only unless explicitly told otherwise."""
    if not results.is_file():
        _fail(failures, "EMPTY_SUITE", f"result table {results} does not exist")
        return report(failures, "")
    text = read_text(results, "result table")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 4:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"result row {number} does not have 4 columns",
            )
            continue
        identifier, status, duration, command = parts
        try:
            status_code = int(status)
            duration_ms = int(duration)
        except ValueError:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"result row {number} has non-numeric status/duration",
            )
            continue
        if status_code != 0:
            _fail(
                failures,
                "SUBCLI_FAILURE",
                f"check {identifier} still fails with status {status_code}",
            )
        rows.append(
            {
                "check_id": identifier,
                "command": command,
                "diagnostic": BATTERY_DIAGNOSTIC_NONE,
                "exit_code": status_code,
                "status": "pass" if status_code == 0 else "fail",
                "durationMs": duration_ms,
            }
        )
    if not rows:
        _fail(failures, "EMPTY_SUITE", "the result table holds no check row")
    else:
        seen = [row["check_id"] for row in rows]
        missing = sorted(set(CHAIN_CHECKS) - set(seen))
        unexpected = sorted(set(seen) - set(CHAIN_CHECKS))
        if missing or unexpected:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"the result table does not carry the chain's check set: missing={missing} "
                f"unexpected={unexpected}",
            )
        if len(set(seen)) != len(seen):
            _fail(failures, "SCHEMA_KEY_DRIFT", "the result table repeats a check_id")

    schemas: Any = None
    path = artifacts.get("s02_schemas")
    if path is not None and path.is_file():
        try:
            schemas = load_json(path, "S02 schemas")
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
    if not isinstance(schemas, dict) or schemas.get("non_claims") is None:
        _fail(
            failures, "MISSING_ARTIFACT", "the frozen non-claims could not be read for the battery"
        )
    if failures:
        return report(failures, "")

    receipt_path = artifacts.get("receipt")
    human = False
    if receipt_path is not None and receipt_path.is_file():
        try:
            receipt = load_json(receipt_path, "pilot receipt")
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            return report(failures, "")
        human = isinstance(receipt, dict) and receipt.get("human_pilot_performed") is True

    lifecycle = (
        schemas.get("lifecycle") if isinstance(schemas.get("lifecycle"), dict) else LIFECYCLE
    )
    payload = {
        "schema": BATTERY_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "human_pilot_performed": human,
        "model_invoked": False,
        "lifecycle": dict(lifecycle),
        "non_claims": list(schemas.get("non_claims") or []),
        "pins": [{"path": rel, "sha256": pin} for rel, pin in sorted(PINS.values())],
        "checks": [
            {key: value for key, value in row.items() if key != "durationMs"} for row in rows
        ],
    }
    for hit in wallclock_hits(payload):
        _fail(
            failures,
            "BATTERY_WALLCLOCK_FORBIDDEN",
            f"the assembled battery would persist wall-clock data at {hit}",
        )
    if set(payload) != BATTERY_CLOSED_KEYS:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"the assembled battery keys {sorted(set(payload) ^ BATTERY_CLOSED_KEYS)} differ "
            "from the frozen closed set",
        )
    if failures:
        return report(failures, "")

    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    rendered_bytes = rendered.encode("utf-8")
    timings = " ".join(f"{row['check_id']}={row['durationMs']}ms" for row in rows)
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        current = out.read_bytes() if out.is_file() else None
        if current == rendered_bytes:
            outcome = "unchanged"
        else:
            out.write_bytes(rendered_bytes)
            outcome = "written"
    elif not out.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"battery missing at {out}")
        return report(failures, "")
    elif out.read_bytes() != rendered_bytes:
        _fail(
            failures,
            "BATTERY_STALE",
            "assembled battery differs from the tracked battery; regenerate once with "
            "M207_S02_WRITE_BATTERY=1 before host verification",
        )
        return report(failures, "")
    else:
        outcome = "current"
    print(f"{BATTERY_MARKER} checks={len(rows)} path={out.name} {outcome}")
    print(f"{BATTERY_TIMINGS} {timings}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "mode",
        nargs="?",
        default="check",
        choices=["check", "battery"],
        help="'check' verifies the slice boundary; 'battery' assembles the slice battery",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    for name, _label, default, _suffix, _prefix, _directory in ARTIFACT_SPECS:
        parser.add_argument(f"--{name.replace('_', '-')}", dest=name, default=default)
    parser.add_argument(
        "--s01-chain",
        dest="s01_chain",
        default=S01_CHAIN_REL,
        help="the S01 closeout chain this verifier re-runs as a subprocess",
    )
    parser.add_argument("--results", default="", help="battery mode: tab-separated result table")
    parser.add_argument("--out", default=S02_BATTERY_REL, help="battery mode: battery output path")
    parser.add_argument(
        "--write",
        action="store_true",
        help="battery mode: regenerate the tracked battery (default is read-only compare)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        return report([("MISSING_ARTIFACT", f"root {root} is not a directory")], "")

    if args.mode == "battery":
        failures: Failures = []
        if not args.results:
            return report([("EMPTY_SUITE", "battery mode needs --results")], "")
        try:
            out = resolve_artifact(
                root, args.out, "battery", suffix=".json", prefix="prd/migration/rust-evidence/"
            )
        except VerificationError as exc:
            return report([(exc.diagnostic, exc.detail)], "")
        artifacts, resolve_failures = resolve_all(root, args)
        failures.extend(resolve_failures)
        write = args.write or os.environ.get("M207_S02_WRITE_BATTERY") == "1"
        return battery(Path(args.results), out, artifacts, failures, write=write)

    failures, summary, _details = run(root, args)
    return report(failures, summary)


if __name__ == "__main__":
    raise SystemExit(main())
