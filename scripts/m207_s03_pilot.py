#!/usr/bin/env python3
"""Independent slice verifier for the M207 S03 frozen evaluation contour (T04).

S01 proved that a human pilot is not fabricated.  S02 proved that a two-coding
human pilot is not fabricated.  S03 adds the surface that is *easiest* to
fabricate: the metric.  A rate only means something when its denominator is
real, its input is an independent human reference, and a missing reference
publishes ``not-measured`` instead of ``0.0`` or ``1.0``.  This verifier exists
**before** any human data exists, so that the contour is machine-checkable while
the human gate is still shut.

It deliberately does **not** import ``m207_s03_schemas``,
``m207_s03_eval_manifest`` or ``m207_s03_metrics`` (no oracle collapse, D472):
the pins, the counters, the strata, the leakage scan, the claim guards, the seed
and the isolation scan are re-derived here from bytes, and the S02 closeout
chain is invoked as a real subprocess whose exit status is the only thing read.
The S03 gate modules are deliberately **not** re-run here: T06's closing chain
runs them as its nine battery rows, and the slice boundary is proven here by
re-derivation rather than by delegation.

What it proves, against the frozen sources rather than against prose:

* frozen-source pins -- content sha256 of the five frozen S01 inputs (codebook,
  schemas, case manifest, prompt packets, battery), the five frozen S02 inputs
  (coder protocol, schemas, both coder kits, battery) and the four frozen S03
  inputs (evaluation protocol, eval schemas, eval manifest, leakage report).
  Any disagreement is ``FROZEN_SOURCE_DRIFT``; a missing pinned input is
  ``MISSING_ARTIFACT``.  The tracked battery is *derived* and is never a pin.
* manifest-declared source pins -- every ``pins.sources`` entry of the frozen
  eval manifest is re-hashed from disk, so a manifest that names a drifted
  upstream source is ``FROZEN_SOURCE_DRIFT`` even though the manifest itself is
  pinned and therefore unchanged;
* counters -- 40 cases, 24 Work families, the frozen ``work_family_cap`` of 4,
  8 holdout / 16 dev families, 14 holdout / 26 dev cases, provider strata
  ``consultant:40 garant:0 unknown:0`` with ``quota <= availability`` and every
  declared stratum retained, exactly 180 ``.txt`` fragments whose per-fragment
  sha256 still matches the manifest, and exactly six aspects named in the frozen
  order.  The ``pins.split`` block is re-derived from the case rows rather than
  trusted;
* the closed diagnostic table -- every name this tool may speak must exist in the
  frozen ``$.diagnostics`` list, whose size is frozen at 80
  (``DIAGNOSTIC_TABLE_DRIFT`` otherwise), so a red run is machine-distinguishable
  from a green one and the vocabulary cannot silently grow;
* lifecycle honesty -- ``human_adoption=pending``, ``runtime_stop_active=true``,
  ``selected_d388_gates=none``, ``requirement_status_effect=unchanged``,
  ``review_disposition_effect=unchanged`` in the protocol contract block, the
  schemas, the manifest, the leakage report and the tracked battery;
* no gold, promotion, threshold, classification or human acceptance -- the
  frozen ``output_contract`` is re-checked key by key *by value* (so a claimed
  ``threshold=0.8``, ``classification=pass``, ``promotion=gold``, ``is_gold=true``
  or ``human_acceptance=<something>`` is ``THRESHOLD_REQUESTED`` /
  ``CLASSIFICATION_REQUESTED`` / ``PROMOTION_CLAIM`` / ``GOLD_CLAIM``), and the
  same claim keys are value-guarded everywhere else in the S03 surface;
* no leaked predicted answer -- a recursive key scan of the S03 artifacts against
  the frozen ``forbidden_keys`` / ``forbidden_seed_keys`` contract
  (``LEAK_FORBIDDEN_KEY``).  The declaration containers that legitimately *name*
  a forbidden token (``non_claims``, ``forbidden_*``, ``output_contract`` holding
  ``is_gold`` pinned false, and the ``pins`` roster that names the refused
  ``m204-s02-c5-gold-*`` manifests) are exempt from the token scan because they
  are guarded by value instead (D471/D492);
* prompt isolation -- no ``crates/**`` ``.rs``, ``build.rs`` or ``Cargo.toml``
  references ``m207-s03``, ``m207_s03`` or ``prd/annotation``
  (``PROMPT_ISOLATION_VIOLATION``; this is the structural proof of D466/D487:
  no Rust is introduced and the product runtime gains no reader of the
  codebook);
* no artifact without a human -- ``m207-s03-evaluation-report.json`` exists **if
  and only if** the fixed human stores hold an independent reference (two
  submissions plus a separate adjudication).  The report is *not* an input of
  this verifier: it is never read, only tested for existence, so a fabricated
  report can never become evidence here (``REPORT_WITHOUT_HUMAN_DATA`` /
  ``REPORT_MISSING_WITH_HUMAN_DATA``);
* the 180-fragment seed is neither enlarged nor edited -- count, undeclared
  entries and a per-fragment sha256 rollup against the manifest
  (``SEED_ENLARGED`` / ``FRAGMENT_PIN_DRIFT``).  The manifest's own
  ``fragment_rollup`` digest is not recomputed here because its mixing formula
  belongs to the eval-manifest gate; it is instead protected transitively: the
  manifest is pinned byte for byte, and every fragment it declares is re-hashed
  individually;
* the S02 boundary is still green as a real subprocess -- ``bash
  scripts/m207_s02_t07_verify.sh`` may exit 0 (a human pilot happened) or 3
  (honest ``HUMAN_PILOT_ABSENT``); anything else is ``S02_REGRESSION_FAILED``.
  The S01 chain is reached through S02's chain and is not duplicated here;
* the human gate is *not* claimed -- the tool prints ``M207_S03_MACHINERY_OK``
  **if and only if** the contour is green and no human reference exists
  (``human_pilot_performed=false``), prints
  ``M207_S03_MACHINERY_HUMAN_DATA_PRESENT`` instead once a real human reference
  exists, and **never** prints ``M207_S03_VERIFY_OK`` (``guard_output`` raises
  ``AUTHORITY_CLAIM`` if any printed line would carry it; only T06's closing
  chain may emit it, and only over two real human codings).

``battery`` mode assembles ``prd/migration/rust-evidence/m207-s03-battery.json``
from a tab-separated result table (``id<TAB>status<TAB>durationMs<TAB>command``)
produced by the T06 chain, refusing a table whose rows are missing, malformed,
duplicated, unexpected or still failing.  The tracked battery carries exactly the
frozen closed keys (``schema``, ``schema_version``, ``checks``,
``human_pilot_performed``, ``model_invoked``, ``lifecycle``, ``non_claims``,
``pins``), never hashes itself, and never persists wall-clock data -- durations
are printed to stdout as ``M207_S03_BATTERY_TIMINGS`` so the durable exec log
keeps them while the battery stays a pure function of the observed checks (D473).
The mode is **read-only by default** (byte comparison, ``BATTERY_STALE``); the
single opt-in that may touch the tracked artifact is ``M207_S03_WRITE_BATTERY=1``
plus ``--write``, and the write is skipped when the bytes already match.

The T06 chain must emit a result table whose ``check_id`` values are exactly the
nine frozen ids in ``CHAIN_CHECKS`` below -- ``s03_schemas``,
``s03_eval_manifest``, ``s03_metrics``, ``s03_hostile_suite``,
``s03_machinery_verifier``, ``s02_regression``, ``ruff_format``, ``ruff_check``,
``adr_conformance``.  Anything else is ``SCHEMA_KEY_DRIFT`` naming the diff.

Hostile cases that exercise this verifier point ``--s02-chain`` at a stub script
instead of paying for the real S02 chain (a read-only stub path is accepted
exactly as a real one is).
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

MARKER = "M207_S03_MACHINERY_OK"
HUMAN_DATA_MARKER = "M207_S03_MACHINERY_HUMAN_DATA_PRESENT"
BATTERY_MARKER = "M207_S03_BATTERY_OK"
BATTERY_TIMINGS = "M207_S03_BATTERY_TIMINGS"
ABSENT_TOKEN = "MACHINERY_GREEN_HUMAN_ABSENT"
# The human gate marker: this tool must never print it (T06 owns it).
HUMAN_GATE_MARKER = "M207_S03_VERIFY_OK"

BATTERY_SCHEMA_ID = "m207-s03-battery/v1"
SCHEMA_VERSION = 1
OK_EXIT = 0
FAIL_EXIT = 1

REQUIRED_SECTIONS_DIAGNOSTIC = "MISSING_SECTION"

# Artifacts.
S01_CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
S01_SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
S01_CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
S01_PACKETS_REL = "prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl"
S01_BATTERY_REL = "prd/migration/rust-evidence/m207-s01-battery.json"
S02_PROTOCOL_REL = "prd/annotation/m207-s02-coder-protocol.md"
S02_SCHEMAS_REL = "prd/annotation/m207-s02-schemas.json"
S02_KIT_PASS1_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json"
S02_KIT_PASS2_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass2.json"
S02_BATTERY_REL = "prd/migration/rust-evidence/m207-s02-battery.json"
S03_PROTOCOL_REL = "prd/annotation/m207-s03-eval-protocol.md"
S03_SCHEMAS_REL = "prd/annotation/m207-s03-schemas.json"
S03_MANIFEST_REL = "prd/migration/rust-evidence/m207-s03-eval-manifest.json"
S03_LEAKAGE_REL = "prd/migration/rust-evidence/m207-s03-leakage-report.json"
# Derived artifacts: never pinned, never trusted as an input.
REPORT_REL = "prd/migration/rust-evidence/m207-s03-evaluation-report.json"
BATTERY_REL = "prd/migration/rust-evidence/m207-s03-battery.json"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
SUBMISSION_STORE_REL = "prd/annotation/m207-s02-submissions"
ADJUDICATION_STORE_REL = "prd/annotation/m207-s02-adjudications"
S02_CHAIN_REL = "scripts/m207_s02_t07_verify.sh"
SEED_SIDECAR_NAME = "lawref_seed.json"

ANNOTATION_PREFIX = "prd/annotation/"
EVIDENCE_PREFIX = "prd/migration/rust-evidence/"

# Frozen content pins: sha256 of the file bytes, never a git revision.
PINS: dict[str, tuple[str, str]] = {
    "s01_codebook": (
        "prd/annotation/m207-s01-codebook.md",
        "1a1bfe944207e69cb5fb507e94d680384dadecf7ac98ac29b1de4932d7cb76c6",
    ),
    "s01_schemas": (
        "prd/annotation/m207-s01-schemas.json",
        "63a4bc6629bade752f9fa02d1dd5fa6bbf21238e20772d2ba5b74f88ecca3682",
    ),
    "s01_cases": (
        "prd/migration/rust-evidence/m207-s01-pilot-cases.json",
        "9b0b6bc6bd8eadf9eb86886e45eb756ebade654e96ac3a84132ed9452bdeb9ad",
    ),
    "s01_packets": (
        "prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl",
        "d9d30bf24d40ab8abebb28c1a22692ae99ca029e1b4e2b032a4dae1137cc6b77",
    ),
    "s01_battery": (
        "prd/migration/rust-evidence/m207-s01-battery.json",
        "5d3eb65860f902fb8b7109a5a620c2b7af2b26e34531cbeddb92da294d6a9a5d",
    ),
    "s02_protocol": (
        "prd/annotation/m207-s02-coder-protocol.md",
        "763de0f998b772afd85373e438da0b1b6b2a6435d761e67f06177f4b0b1fbc32",
    ),
    "s02_schemas": (
        "prd/annotation/m207-s02-schemas.json",
        "ef438bb5171a8b58f43a8bc4bc2d9a875877da40943ef28e1337b8741a1cab97",
    ),
    "s02_kit_pass1": (
        "prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json",
        "e23b25d9ce45f72263d9630b47c096a7463b95dbcbfda9233c750e7bf39418c5",
    ),
    "s02_kit_pass2": (
        "prd/migration/rust-evidence/m207-s02-coder-kit-pass2.json",
        "52be89f0f72f46c7f4503c7912508868f92e1e8501c848b2907c59330e192380",
    ),
    "s02_battery": (
        "prd/migration/rust-evidence/m207-s02-battery.json",
        "621c49a3d80345a21ce6577999d928adbf1b0144d6fec2ac26bb49f46e11b409",
    ),
    "s03_protocol": (
        "prd/annotation/m207-s03-eval-protocol.md",
        "e60029d01e9f20ecc84b157ed39e0f8339fc6931f16cc12db171017273457d84",
    ),
    "s03_schemas": (
        "prd/annotation/m207-s03-schemas.json",
        "34d874e59b16e356e5658b7eec45d3fef01a4342592728f10f122b0126903456",
    ),
    "s03_manifest": (
        "prd/migration/rust-evidence/m207-s03-eval-manifest.json",
        "3a6cf44ffae97b3f7b865eba2463bda80eadfaaba169b82e9e6382988d948807",
    ),
    "s03_leakage": (
        "prd/migration/rust-evidence/m207-s03-leakage-report.json",
        "ae644dad845794e81b81d4be6fbe37c061b913bb3fd00d1ce1675582f7dbdfaf",
    ),
}

# name -> (label, default path, suffix, required prefix, is directory)
ARTIFACT_SPECS: tuple[tuple[str, str, str, str, str | None, bool], ...] = (
    ("s01_codebook", "frozen S01 codebook", S01_CODEBOOK_REL, ".md", ANNOTATION_PREFIX, False),
    ("s01_schemas", "frozen S01 schemas", S01_SCHEMAS_REL, ".json", ANNOTATION_PREFIX, False),
    ("s01_cases", "frozen S01 case manifest", S01_CASES_REL, ".json", EVIDENCE_PREFIX, False),
    ("s01_packets", "frozen S01 prompt packets", S01_PACKETS_REL, ".jsonl", EVIDENCE_PREFIX, False),
    ("s01_battery", "frozen S01 battery", S01_BATTERY_REL, ".json", EVIDENCE_PREFIX, False),
    (
        "s02_protocol",
        "frozen S02 coder protocol",
        S02_PROTOCOL_REL,
        ".md",
        ANNOTATION_PREFIX,
        False,
    ),
    ("s02_schemas", "frozen S02 schemas", S02_SCHEMAS_REL, ".json", ANNOTATION_PREFIX, False),
    ("s02_kit_pass1", "frozen S02 pass-1 kit", S02_KIT_PASS1_REL, ".json", EVIDENCE_PREFIX, False),
    ("s02_kit_pass2", "frozen S02 pass-2 kit", S02_KIT_PASS2_REL, ".json", EVIDENCE_PREFIX, False),
    ("s02_battery", "frozen S02 battery", S02_BATTERY_REL, ".json", EVIDENCE_PREFIX, False),
    ("s03_protocol", "frozen S03 protocol", S03_PROTOCOL_REL, ".md", ANNOTATION_PREFIX, False),
    ("s03_schemas", "frozen S03 schemas", S03_SCHEMAS_REL, ".json", ANNOTATION_PREFIX, False),
    ("s03_manifest", "frozen S03 eval manifest", S03_MANIFEST_REL, ".json", EVIDENCE_PREFIX, False),
    ("s03_leakage", "frozen S03 leakage report", S03_LEAKAGE_REL, ".json", EVIDENCE_PREFIX, False),
    ("fixture_dir", "frozen fragment seed", FIXTURE_DIR_REL, "", "crates/", True),
    (
        "submissions",
        "S02 human submission store",
        SUBMISSION_STORE_REL,
        "",
        ANNOTATION_PREFIX,
        True,
    ),
    (
        "adjudications",
        "S02 human adjudication store",
        ADJUDICATION_STORE_REL,
        "",
        ANNOTATION_PREFIX,
        True,
    ),
    ("report", "derived S03 evaluation report", REPORT_REL, ".json", EVIDENCE_PREFIX, False),
    ("battery", "derived S03 tracked battery", BATTERY_REL, ".json", EVIDENCE_PREFIX, False),
)
ARTIFACT_REL: dict[str, str] = {name: default for name, _l, default, _s, _p, _d in ARTIFACT_SPECS}

# Frozen counters and vocabularies.
CASE_COUNT = 40
FAMILY_COUNT = 24
WORK_FAMILY_CAP = 4
HOLDOUT_FAMILY_COUNT = 8
DEV_FAMILY_COUNT = 16
HOLDOUT_CASE_COUNT = 14
DEV_CASE_COUNT = 26
FIXTURE_TXT_COUNT = 180
ASPECT_COUNT = 6
DIAGNOSTIC_COUNT_FROZEN = 80
HUMAN_SUBMISSION_COUNT = 2
HUMAN_ADJUDICATION_COUNT = 1
SEED_SIDECAR_COUNT = 1
FIXTURE_ALLOWED_ENTRIES = frozenset({SEED_SIDECAR_NAME})
ASPECTS = ("span", "slot", "scope", "binding", "abstention", "false_authority")
PROVIDER_ORDER = ("consultant", "garant", "unknown")
PROVIDER_CASE_COUNTS: dict[str, int] = {"consultant": 40, "garant": 0}
FAMILY_SCOPES = ("holdout", "dev")
MEASUREMENT_NOT_MEASURED = "not-measured"
LIFECYCLE: dict[str, Any] = {
    "human_adoption": "pending",
    "runtime_stop_active": True,
    "selected_d388_gates": "none",
    "requirement_status_effect": "unchanged",
    "review_disposition_effect": "unchanged",
}

# Frozen claim values: the S03 artifacts legitimately *declare* these keys, so
# they are guarded by VALUE, never by name alone (the same lesson as S01/S02).
OUTPUT_CONTRACT_PINS: dict[str, Any] = {
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
CLAIM_KEY_DIAGNOSTICS: dict[str, str] = {
    "threshold": "THRESHOLD_REQUESTED",
    "classification": "CLASSIFICATION_REQUESTED",
    "promotion": "PROMOTION_CLAIM",
    "authority": "AUTHORITY_CLAIM",
    "suggestion_status": "AUTHORITY_CLAIM",
    "model_invoked": "MODEL_INVOKED",
    "is_gold": "GOLD_CLAIM",
    "human_acceptance": "GOLD_CLAIM",
}
# Keys that may only ever be absent: a present, truthy value is a fabricated
# classification or a fabricated gold label.
CLAIM_ABSENT_KEYS: dict[str, str] = {
    "gold_labels": "GOLD_CLAIM",
    "gold_label": "GOLD_CLAIM",
    "pass_fail": "CLASSIFICATION_REQUESTED",
    "precision": "CLASSIFICATION_REQUESTED",
    "recall": "CLASSIFICATION_REQUESTED",
    "f1": "CLASSIFICATION_REQUESTED",
    "accuracy": "CLASSIFICATION_REQUESTED",
    "verdict": "CLASSIFICATION_REQUESTED",
    "agreement_threshold": "THRESHOLD_REQUESTED",
}
# Containers whose own wording enumerates a forbidden token; they are pinned by
# value (``output_contract``), guard the pins themselves (``pins``), or are
# declaration lists (``non_claims``, ``forbidden_*``).
EXEMPT_KEYS = frozenset(
    {
        "non_claims",
        "forbidden_keys",
        "forbidden_seed_keys",
        "forbidden_substrings",
        "forbidden_battery_keys",
        "forbidden_case_keys",
        "output_contract",
        "vocabularies",
        "pins",
        "is_gold",
    }
)
CLAIM_SKIP_KEYS = frozenset({"output_contract", "vocabularies"})

ISOLATION_TOKENS = ("m207-s03", "m207_s03", "prd/annotation")
ISOLATION_SUFFIXES = (".rs",)
ISOLATION_NAMES = frozenset({"build.rs", "Cargo.toml"})
ISOLATION_SKIP_PARTS = frozenset({"target", ".git", "node_modules", "__pycache__", ".venv"})
ISOLATION_MAX_BYTES = 4 * 1024 * 1024

BATTERY_CHECK_CLOSED_KEYS = frozenset({"check_id", "command", "diagnostic", "exit_code", "status"})
BATTERY_FORBIDDEN_KEY_TOKENS = frozenset(
    {"duration_ms", "elapsed_ms", "generated_at", "wall_clock"}
)
BATTERY_DIAGNOSTIC_NONE = "none"
BATTERY_WRITE_ENV = "M207_S03_WRITE_BATTERY"

# The frozen battery check set: exactly the nine gates T06's chain must run.
CHAIN_CHECKS: tuple[str, ...] = (
    "s03_schemas",
    "s03_eval_manifest",
    "s03_metrics",
    "s03_hostile_suite",
    "s03_machinery_verifier",
    "s02_regression",
    "ruff_format",
    "ruff_check",
    "adr_conformance",
)

FAILURE_DIAGNOSTICS = frozenset(
    {
        "UNSAFE_PATH",
        "DUPLICATE_JSON_KEY",
        "SCHEMA_PARSE_ERROR",
        "SCHEMA_KEY_DRIFT",
        "MISSING_ARTIFACT",
        "MISSING_SCHEMA",
        "MISSING_SECTION",
        "MISSING_LIFECYCLE_MARKER",
        "FROZEN_SOURCE_DRIFT",
        "DIAGNOSTIC_TABLE_DRIFT",
        "CASE_COUNT_OUT_OF_RANGE",
        "VOCABULARY_DRIFT",
        "WORK_FAMILY_DOMINANCE",
        "HOLDOUT_LEAKAGE",
        "STRATUM_TABLE_DRIFT",
        "PROVIDER_MISATTRIBUTED",
        "PROVIDER_STRATUM_DROPPED",
        "PROVIDER_QUOTA_UNJUSTIFIED",
        "MEASUREMENT_STATUS_DRIFT",
        "SEED_ENLARGED",
        "FRAGMENT_PIN_DRIFT",
        "ASPECT_TABLE_DRIFT",
        "LEAK_FORBIDDEN_KEY",
        "PROMPT_ISOLATION_VIOLATION",
        "REPORT_WITHOUT_HUMAN_DATA",
        "REPORT_MISSING_WITH_HUMAN_DATA",
        "S02_REGRESSION_FAILED",
        "SUBCLI_FAILURE",
        "EMPTY_SUITE",
        "BATTERY_STALE",
        "BATTERY_WALLCLOCK_FORBIDDEN",
        "AUTHORITY_CLAIM",
        "GOLD_CLAIM",
        "PROMOTION_CLAIM",
        "THRESHOLD_REQUESTED",
        "CLASSIFICATION_REQUESTED",
        "MODEL_INVOKED",
    }
)

S02_CHAIN_TIMEOUT = 2400

FENCE_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
TOKEN_SEPARATOR_RE = re.compile(r"[^A-Za-z0-9]+")

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
    """This tool may never emit the human-gate marker (T06 owns it)."""
    if HUMAN_GATE_MARKER in text:
        raise VerificationError(
            "AUTHORITY_CLAIM",
            "the machinery verifier would emit the human-gate marker; only the closing chain "
            "may print it, and only over two real human codings",
        )
    return text


def emit(text: str, stream: Any = None) -> None:
    print(guard_output(text), file=stream or sys.stdout)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_digest(raw: Any) -> str:
    """Accept ``sha256:<hex>`` and bare ``<hex>`` alike, lowercased."""
    text = str(raw).strip().lower()
    if text.startswith("sha256:"):
        text = text[len("sha256:") :]
    return text


def relative_posix(path: Path, root: Path) -> str:
    """Repository-relative name of ``path``, immune to the ``.gsd`` symlink trap.

    Resolving both sides can disagree when the root is reached through a symlink
    (``/root/law-nexus/.gsd`` is one), so both orders are tried and the plain file
    name is the last resort.  A verifier must speak a named diagnostic, never a
    traceback.
    """
    for candidate_root, candidate in ((root.resolve(), path.resolve()), (root, path)):
        try:
            return candidate.relative_to(candidate_root).as_posix()
        except ValueError:
            continue
    return path.name


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
    """Resolve the S02 closeout chain: executed read-only, so a stub is allowed."""
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
    return [
        token for token in TOKEN_SEPARATOR_RE.split(CAMEL_BOUNDARY_RE.sub("_", str(key))) if token
    ]


def forbidden_key_hit(name: str, tokens: frozenset[str], exact: frozenset[str]) -> str | None:
    lowered = [token.lower() for token in key_tokens(name)]
    if tokens & set(lowered):
        return "predicted-answer"
    if str(name).strip().lower() in exact:
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
    """This tool may only speak names the frozen table declares (D492)."""
    if not isinstance(schemas, dict):
        _fail(failures, "MISSING_SCHEMA", "the frozen S03 schemas could not be read")
        return 0
    names = schemas.get("diagnostics")
    if not isinstance(names, list) or not all(isinstance(item, str) for item in names):
        _fail(
            failures,
            "MISSING_SCHEMA",
            "the frozen $.diagnostics table is missing from the S03 schemas",
        )
        return 0
    if len(names) != DIAGNOSTIC_COUNT_FROZEN:
        _fail(
            failures,
            "DIAGNOSTIC_TABLE_DRIFT",
            f"the frozen table holds {len(names)} names != {DIAGNOSTIC_COUNT_FROZEN}",
        )
    if len(set(names)) != len(names):
        _fail(failures, "DIAGNOSTIC_TABLE_DRIFT", "the frozen table repeats a diagnostic name")
    missing = sorted(FAILURE_DIAGNOSTICS - set(names))
    if missing:
        _fail(
            failures,
            "DIAGNOSTIC_TABLE_DRIFT",
            f"this verifier speaks diagnostics absent from the frozen table: {missing}",
        )
    return len(names)


def check_manifest_pins(manifest: Any, root: Path, failures: Failures) -> int:
    """Re-hash every source the frozen manifest names, plus the seed rollup."""
    if not isinstance(manifest, dict):
        return 0
    pins = manifest.get("pins")
    if not isinstance(pins, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the eval manifest carries no $.pins object")
        return 0
    sources = pins.get("sources")
    if not isinstance(sources, dict) or not sources:
        _fail(failures, "SCHEMA_KEY_DRIFT", "the eval manifest declares no $.pins.sources")
        return 0
    verified = 0
    for name, entry in sorted(sources.items()):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"$.pins.sources.{name} is not a closed {{path, sha256}} record",
            )
            continue
        raw = str(entry.get("path"))
        try:
            path = resolve_artifact(
                root, raw, f"pins.sources.{name}", suffix=PurePosixPath(raw).suffix, prefix=None
            )
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        if not path.is_file():
            _fail(failures, "MISSING_ARTIFACT", f"$.pins.sources.{name} missing at {raw}")
            continue
        digest = sha256_file(path)
        if digest != normalize_digest(entry.get("sha256")):
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"$.pins.sources.{name} names {raw} but its sha256 is {digest}",
            )
        else:
            verified += 1
    rollup = pins.get("fragment_rollup")
    if not isinstance(rollup, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the eval manifest declares no $.pins.fragment_rollup")
    else:
        if rollup.get("count") != FIXTURE_TXT_COUNT:
            _fail(
                failures,
                "SEED_ENLARGED",
                f"$.pins.fragment_rollup.count={rollup.get('count')!r} != {FIXTURE_TXT_COUNT}",
            )
        if rollup.get("path") != FIXTURE_DIR_REL:
            _fail(
                failures,
                "FROZEN_SOURCE_DRIFT",
                f"$.pins.fragment_rollup.path={rollup.get('path')!r} != {FIXTURE_DIR_REL!r}",
            )
    if not isinstance(pins.get("split"), dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the eval manifest declares no $.pins.split block")
    return verified


# --------------------------------------------------------------------------- #
# Counters, strata and the Work-family split.
# --------------------------------------------------------------------------- #


def check_counters(manifest: Any, schemas: Any, failures: Failures) -> dict[str, Any]:
    counters: dict[str, Any] = {
        "cases": 0,
        "families": 0,
        "work_family_cap": WORK_FAMILY_CAP,
        "holdout_families": 0,
        "dev_families": 0,
        "holdout_cases": 0,
        "dev_cases": 0,
    }
    declared_cap = WORK_FAMILY_CAP
    if isinstance(schemas, dict):
        eval_manifest = schemas.get("schemas")
        if isinstance(eval_manifest, dict) and isinstance(eval_manifest.get("eval_manifest"), dict):
            raw_cap = eval_manifest["eval_manifest"].get("work_family_cap")
            if raw_cap != WORK_FAMILY_CAP:
                _fail(
                    failures,
                    "SCHEMA_KEY_DRIFT",
                    f"the frozen work_family_cap={raw_cap!r} != {WORK_FAMILY_CAP}",
                )
            else:
                declared_cap = int(raw_cap)
    counters["work_family_cap"] = declared_cap

    if not isinstance(manifest, dict):
        _fail(failures, "MISSING_ARTIFACT", "the frozen eval manifest could not be read")
        return counters

    cases = manifest.get("cases")
    if not isinstance(cases, list):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the eval manifest carries no $.cases list")
        return counters
    counters["cases"] = len(cases)
    if len(cases) != CASE_COUNT:
        _fail(
            failures,
            "CASE_COUNT_OUT_OF_RANGE",
            f"the eval manifest carries {len(cases)} cases != {CASE_COUNT}",
        )

    family_rows = manifest.get("families")
    if not isinstance(family_rows, list):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the eval manifest carries no $.families list")
        family_rows = []
    counters["families"] = len(family_rows)
    if len(family_rows) != FAMILY_COUNT:
        _fail(
            failures,
            "VOCABULARY_DRIFT",
            f"the Work-family roster holds {len(family_rows)} families != {FAMILY_COUNT}",
        )

    holdout = manifest.get("holdout_families")
    dev = manifest.get("dev_families")
    holdout = holdout if isinstance(holdout, list) else []
    dev = dev if isinstance(dev, list) else []
    counters["holdout_families"] = len(holdout)
    counters["dev_families"] = len(dev)
    if len(holdout) != HOLDOUT_FAMILY_COUNT:
        _fail(
            failures,
            "VOCABULARY_DRIFT",
            f"$.holdout_families holds {len(holdout)} families != {HOLDOUT_FAMILY_COUNT}",
        )
    if len(dev) != DEV_FAMILY_COUNT:
        _fail(
            failures,
            "VOCABULARY_DRIFT",
            f"$.dev_families holds {len(dev)} families != {DEV_FAMILY_COUNT}",
        )
    overlap = sorted(set(holdout) & set(dev))
    if overlap:
        _fail(
            failures,
            "HOLDOUT_LEAKAGE",
            f"$\\.holdout_families and $.dev_families intersect: {overlap[:5]}",
        )

    per_family: dict[str, int] = {}
    per_scope: dict[str, str] = {}
    scope_families: dict[str, set[str]] = {scope: set() for scope in FAMILY_SCOPES}
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            _fail(failures, "SCHEMA_KEY_DRIFT", f"$.cases[{index}] is not an object")
            continue
        family = str(case.get("work_family"))
        scope = str(case.get("family_scope"))
        per_family[family] = per_family.get(family, 0) + 1
        if scope not in FAMILY_SCOPES:
            _fail(
                failures,
                "VOCABULARY_DRIFT",
                f"$.cases[{index}].family_scope={scope!r} is outside {list(FAMILY_SCOPES)}",
            )
            continue
        per_scope[family] = scope
        scope_families[scope].add(family)
        counters[f"{scope}_cases"] += 1
    if counters["holdout_cases"] != HOLDOUT_CASE_COUNT:
        _fail(
            failures,
            "HOLDOUT_LEAKAGE",
            f"the holdout scope carries {counters['holdout_cases']} cases != {HOLDOUT_CASE_COUNT}",
        )
    if counters["dev_cases"] != DEV_CASE_COUNT:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"the dev scope carries {counters['dev_cases']} cases != {DEV_CASE_COUNT}",
        )
    for family, counts in sorted(per_family.items()):
        if counts > counters["work_family_cap"]:
            _fail(
                failures,
                "WORK_FAMILY_DOMINANCE",
                f"Work family {family!r} carries {counts} cases > cap "
                f"{counters['work_family_cap']}",
            )
    for family in sorted(per_family):
        scope = per_scope.get(family)
        if scope is None:
            continue
        other = "dev" if scope == "holdout" else "holdout"
        if family in scope_families[other]:
            _fail(
                failures,
                "HOLDOUT_LEAKAGE",
                f"Work family {family!r} is split across {scope} and {other}",
            )
    declared_holdout = set(holdout)
    declared_dev = set(dev)
    observed_holdout = scope_families["holdout"]
    observed_dev = scope_families["dev"]
    if declared_holdout != observed_holdout or declared_dev != observed_dev:
        _fail(
            failures,
            "HOLDOUT_LEAKAGE",
            "the declared holdout/dev family lists disagree with the case rows: "
            f"holdout missing={sorted(declared_holdout ^ observed_holdout)[:5]} "
            f"dev missing={sorted(declared_dev ^ observed_dev)[:5]}",
        )

    counters["aspects"] = check_aspect_table(schemas, failures)
    counters["family_rows"] = family_rows
    return counters


def check_aspect_table(schemas: Any, failures: Failures) -> int:
    if not isinstance(schemas, dict):
        return 0
    table = schemas.get("aspect_table")
    if not isinstance(table, list):
        _fail(failures, "ASPECT_TABLE_DRIFT", "the frozen $.aspect_table is missing")
        return 0
    if len(table) != ASPECT_COUNT:
        _fail(
            failures,
            "ASPECT_TABLE_DRIFT",
            f"$.aspect_table holds {len(table)} aspects != {ASPECT_COUNT}",
        )
    names = tuple(str(row.get("aspect")) for row in table if isinstance(row, dict))
    if names != ASPECTS:
        _fail(
            failures,
            "ASPECT_TABLE_DRIFT",
            f"$.aspect_table names {list(names)} != {list(ASPECTS)}",
        )
    closed = schemas.get("aspect_closed_keys")
    if isinstance(closed, list) and closed:
        for index, row in enumerate(table):
            if not isinstance(row, dict):
                _fail(failures, "ASPECT_TABLE_DRIFT", f"$.aspect_table[{index}] is not an object")
                continue
            extra = sorted(set(row) - set(closed))
            if extra or set(closed) - set(row):
                _fail(
                    failures,
                    "ASPECT_TABLE_DRIFT",
                    f"$.aspect_table[{index}] is not a closed aspect row: extra={extra} "
                    f"missing={sorted(set(closed) - set(row))}",
                )
    return len(table)


def split_counters(manifest: Any) -> dict[str, Any]:
    pins = manifest.get("pins") if isinstance(manifest, dict) else None
    split = pins.get("split") if isinstance(pins, dict) else None
    return split if isinstance(split, dict) else {}


def check_split_block(manifest: Any, counters: dict[str, Any], failures: Failures) -> None:
    """The manifest's own split block is re-derived, not trusted."""
    split = split_counters(manifest)
    if not split:
        return
    expected = {
        "family_count": counters["families"],
        "holdout_family_count": counters["holdout_families"],
        "dev_family_count": counters["dev_families"],
        "holdout_cases": counters["holdout_cases"],
        "dev_cases": counters["dev_cases"],
    }
    for key, value in sorted(expected.items()):
        if key in split and split[key] != value:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"$.pins.split.{key}={split[key]!r} != re-derived {value!r}",
            )


def check_strata(manifest: Any, schemas: Any, failures: Failures) -> dict[str, int]:
    """Provider strata: every declared stratum present, quota honest, cases attributed."""
    observed: dict[str, int] = {provider: 0 for provider in PROVIDER_ORDER}
    if not isinstance(manifest, dict):
        return observed
    cases = manifest.get("cases") if isinstance(manifest.get("cases"), list) else []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            continue
        provider = str(case.get("provider"))
        if provider not in observed:
            _fail(
                failures,
                "PROVIDER_MISATTRIBUTED",
                f"$.cases[{index}].provider={provider!r} is outside the declared strata "
                f"{list(PROVIDER_ORDER)}",
            )
            continue
        observed[provider] += 1
    for provider, expected in sorted(PROVIDER_CASE_COUNTS.items()):
        if observed.get(provider) != expected:
            _fail(
                failures,
                "PROVIDER_MISATTRIBUTED",
                f"provider {provider!r} attributes {observed.get(provider)} cases != {expected}",
            )

    strata = manifest.get("provider_strata")
    if not isinstance(strata, list):
        _fail(failures, "STRATUM_TABLE_DRIFT", "the eval manifest carries no $.provider_strata")
        return observed
    declared = observed.keys()
    seen: set[str] = set()
    for index, row in enumerate(strata):
        if not isinstance(row, dict):
            _fail(failures, "STRATUM_TABLE_DRIFT", f"$.provider_strata[{index}] is not an object")
            continue
        closed = {"provider", "availability", "quota", "justification", "measurement_status"}
        if set(row) != closed:
            _fail(
                failures,
                "STRATUM_TABLE_DRIFT",
                f"$.provider_strata[{index}] is not closed: diff={sorted(set(row) ^ closed)}",
            )
            continue
        provider = str(row["provider"])
        seen.add(provider)
        availability, quota = row["availability"], row["quota"]
        if not isinstance(availability, int) or not isinstance(quota, int):
            _fail(
                failures,
                "STRATUM_TABLE_DRIFT",
                f"$.provider_strata[{index}] availability/quota are not integers",
            )
            continue
        if quota > availability:
            _fail(
                failures,
                "PROVIDER_QUOTA_UNJUSTIFIED",
                f"provider {provider!r} declares quota {quota} > availability {availability}",
            )
        if availability != observed.get(provider, 0):
            _fail(
                failures,
                "PROVIDER_MISATTRIBUTED",
                f"provider {provider!r} declares availability {availability} != observed "
                f"{observed.get(provider, 0)}",
            )
        if row["measurement_status"] != MEASUREMENT_NOT_MEASURED:
            _fail(
                failures,
                "MEASUREMENT_STATUS_DRIFT",
                f"provider {provider!r} declares measurement_status="
                f"{row['measurement_status']!r} while the manifest is frozen at "
                f"{MEASUREMENT_NOT_MEASURED!r}",
            )
    missing = sorted(set(declared) - seen)
    if missing:
        _fail(
            failures,
            "PROVIDER_STRATUM_DROPPED",
            f"$.provider_strata drops declared strata {missing}",
        )
    return observed


# --------------------------------------------------------------------------- #
# Lifecycle, claims and leakage.
# --------------------------------------------------------------------------- #


def check_lifecycle(documents: list[tuple[str, Any]], failures: Failures) -> int:
    blocks = 0
    for label, doc in documents:
        if not isinstance(doc, dict):
            continue
        lifecycle = doc.get("lifecycle")
        if not isinstance(lifecycle, dict):
            _fail(failures, "MISSING_LIFECYCLE_MARKER", f"{label} carries no lifecycle block")
            continue
        if dict(lifecycle) != LIFECYCLE:
            drifted = {
                key: lifecycle.get(key)
                for key in sorted(set(lifecycle) | set(LIFECYCLE))
                if lifecycle.get(key) != LIFECYCLE.get(key)
            }
            _fail(
                failures,
                "MISSING_LIFECYCLE_MARKER",
                f"{label} lifecycle drifted: {drifted}",
            )
        else:
            blocks += 1
    return blocks


def output_contract_hits(node: Any, pointer: str = "$") -> list[tuple[str, str, Any]]:
    """Every output_contract container found in an S03 artifact, with its pointer."""
    hits: list[tuple[str, str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "output_contract" and isinstance(value, dict):
                hits.append(("output_contract", f"{pointer}/{key}", value))
            else:
                hits.extend(output_contract_hits(value, f"{pointer}/{key}"))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            hits.extend(output_contract_hits(item, f"{pointer}[{index}]"))
    return hits


def check_output_contract(label: str, contract: Any, failures: Failures) -> int:
    if not isinstance(contract, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", f"{label}.output_contract is not an object")
        return 0
    extra = sorted(set(contract) - set(OUTPUT_CONTRACT_PINS))
    missing = sorted(set(OUTPUT_CONTRACT_PINS) - set(contract))
    if extra or missing:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"{label}.output_contract is not the frozen closed set: extra={extra} missing={missing}",
        )
        return 0
    for key, expected in sorted(OUTPUT_CONTRACT_PINS.items()):
        observed = contract.get(key)
        if observed != expected:
            _fail(
                failures,
                CLAIM_KEY_DIAGNOSTICS[key],
                f"{label}.output_contract.{key}={observed!r} != frozen {expected!r}",
            )
    return 1


def scan_claim_values(node: Any, pointer: str, failures: Failures, *, skip: bool = False) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if skip or key in CLAIM_SKIP_KEYS or str(key).startswith("forbidden"):
                scan_claim_values(value, f"{pointer}/{key}", failures, skip=True)
                continue
            if key in CLAIM_KEY_DIAGNOSTICS and value != OUTPUT_CONTRACT_PINS.get(key):
                _fail(
                    failures,
                    CLAIM_KEY_DIAGNOSTICS[key],
                    f"{pointer}/{key}={value!r} != frozen {OUTPUT_CONTRACT_PINS.get(key)!r}",
                )
            if key in CLAIM_ABSENT_KEYS and value:
                _fail(
                    failures,
                    CLAIM_ABSENT_KEYS[key],
                    f"{pointer}/{key} is present and truthy",
                )
            scan_claim_values(value, f"{pointer}/{key}", failures)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_claim_values(item, f"{pointer}[{index}]", failures, skip=skip)


def scan_forbidden_keys(
    node: Any,
    pointer: str,
    tokens: frozenset[str],
    exact: frozenset[str],
    failures: Failures,
    *,
    exempt: bool = False,
) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            hit = None if exempt else forbidden_key_hit(key, tokens, exact)
            if hit:
                _fail(
                    failures,
                    "LEAK_FORBIDDEN_KEY",
                    f"{pointer}/{key} carries a forbidden {hit} key",
                )
            child_exempt = exempt or str(key) in EXEMPT_KEYS
            scan_forbidden_keys(
                value, f"{pointer}/{key}", tokens, exact, failures, exempt=child_exempt
            )
    elif isinstance(node, list):
        for index, item in enumerate(node):
            scan_forbidden_keys(item, f"{pointer}[{index}]", tokens, exact, failures, exempt=exempt)


def check_leakage(documents: list[tuple[str, Any]], protocol: Any, failures: Failures) -> int:
    if not isinstance(protocol, dict):
        _fail(failures, "MISSING_SCHEMA", "the protocol contract block could not be read")
        return 0
    raw_tokens = protocol.get("forbidden_keys")
    raw_exact = protocol.get("forbidden_seed_keys")
    if not isinstance(raw_tokens, list) or not raw_tokens:
        _fail(failures, "MISSING_SCHEMA", "$.forbidden_keys is missing from the protocol block")
        return 0
    if not isinstance(raw_exact, list):
        _fail(
            failures, "MISSING_SCHEMA", "$.forbidden_seed_keys is missing from the protocol block"
        )
        return 0
    tokens = frozenset(str(item).lower() for item in raw_tokens)
    exact = frozenset(str(item).strip().lower() for item in raw_exact)
    scanned = 0
    for label, doc in documents:
        if doc is None:
            continue
        scan_forbidden_keys(doc, label, tokens, exact, failures)
        scanned += 1
    return scanned


# --------------------------------------------------------------------------- #
# The 180-fragment seed.
# --------------------------------------------------------------------------- #


def check_seed(
    artifacts: dict[str, Path | None], manifest: Any, root: Path, failures: Failures
) -> tuple[int, int]:
    fixture = artifacts.get("fixture_dir")
    if fixture is None or not fixture.is_dir():
        _fail(failures, "MISSING_ARTIFACT", f"the frozen seed is missing at {FIXTURE_DIR_REL}")
        return 0, 0
    on_disk: dict[str, Path] = {}
    for path in sorted(fixture.rglob("*")):
        if not path.is_file():
            continue
        if ISOLATION_SKIP_PARTS & set(path.parts):
            continue
        relative = relative_posix(path, root)
        on_disk[relative] = path
    txt_names = {name for name in on_disk if name.endswith(".txt")}
    sidecars = {name for name in on_disk if not name.endswith(".txt")}
    undeclared = sorted(
        name for name in sidecars if PurePosixPath(name).name not in FIXTURE_ALLOWED_ENTRIES
    )
    if undeclared:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"the seed holds undeclared entries: {undeclared[:5]}",
        )
    if len(txt_names) != FIXTURE_TXT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"the seed holds {len(txt_names)} .txt fragments != {FIXTURE_TXT_COUNT}",
        )

    declared = manifest.get("fragments") if isinstance(manifest, dict) else None
    declared = declared if isinstance(declared, list) else []
    if len(declared) != FIXTURE_TXT_COUNT:
        _fail(
            failures,
            "SEED_ENLARGED",
            f"the manifest declares {len(declared)} fragments != {FIXTURE_TXT_COUNT}",
        )
    declared_names: set[str] = set()
    drift = 0
    for index, entry in enumerate(declared):
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"$.fragments[{index}] is not a closed {{path, sha256}} record",
            )
            continue
        raw = str(entry.get("path"))
        try:
            path = resolve_artifact(
                root,
                raw,
                f"fragments[{index}]",
                suffix=".txt",
                prefix=f"{FIXTURE_DIR_REL}/",
            )
        except VerificationError as exc:
            _fail(failures, exc.diagnostic, exc.detail)
            continue
        declared_names.add(raw)
        if not path.is_file():
            _fail(failures, "MISSING_ARTIFACT", f"declared fragment {raw} is missing")
            continue
        digest = sha256_file(path)
        if digest != normalize_digest(entry.get("sha256")):
            drift += 1
            _fail(
                failures,
                "FRAGMENT_PIN_DRIFT",
                f"{raw} sha256 {digest} != manifest {normalize_digest(entry.get('sha256'))}",
            )
    if declared_names and declared_names != txt_names:
        extra = sorted(txt_names - declared_names)
        missing = sorted(declared_names - txt_names)
        if extra or missing:
            _fail(
                failures,
                "SEED_ENLARGED",
                f"the seed and the manifest disagree: undeclared={extra[:5]} missing={missing[:5]}",
            )
    return len(txt_names), drift


# --------------------------------------------------------------------------- #
# Prompt isolation: the product runtime gains no reader of the codebook.
# --------------------------------------------------------------------------- #


def isolation_candidates(root: Path) -> list[Path]:
    crates = root / "crates"
    if not crates.is_dir():
        return []
    candidates: list[Path] = []
    for path in sorted(crates.rglob("*")):
        if not path.is_file():
            continue
        if ISOLATION_SKIP_PARTS & set(path.parts):
            continue
        if path.name in ISOLATION_NAMES or path.suffix in ISOLATION_SUFFIXES:
            candidates.append(path)
    return candidates


def check_prompt_isolation(root: Path, failures: Failures) -> int:
    scanned = 0
    for path in isolation_candidates(root):
        try:
            if path.stat().st_size > ISOLATION_MAX_BYTES:
                continue
            raw = path.read_bytes()
        except OSError as exc:
            _fail(failures, "MISSING_ARTIFACT", f"isolation scan could not read {path}: {exc}")
            continue
        scanned += 1
        relative = relative_posix(path, root)
        for token in ISOLATION_TOKENS:
            if token.encode("utf-8") in raw:
                _fail(
                    failures,
                    "PROMPT_ISOLATION_VIOLATION",
                    f"{relative} references {token!r}: the product crates must stay sealed "
                    "against the codebook and the S03 surface",
                )
    return scanned


# --------------------------------------------------------------------------- #
# The human reference and the report invariant.
# --------------------------------------------------------------------------- #


def count_store_entries(directory: Path | None) -> int:
    if directory is None or not directory.is_dir():
        return 0
    return sum(
        1 for path in sorted(directory.iterdir()) if path.is_file() and path.suffix == ".json"
    )


def observe_human_reference(artifacts: dict[str, Path | None]) -> tuple[bool, int, int]:
    """Structural probe over the fixed human stores; content validation is S02's job."""
    submissions = count_store_entries(artifacts.get("submissions"))
    adjudications = count_store_entries(artifacts.get("adjudications"))
    present = submissions >= HUMAN_SUBMISSION_COUNT and adjudications >= HUMAN_ADJUDICATION_COUNT
    return present, submissions, adjudications


def check_report_invariant(report: Path | None, human_present: bool, failures: Failures) -> bool:
    """The evaluation report exists iff a human reference exists; it is never read."""
    exists = report is not None and report.is_file()
    if exists and not human_present:
        _fail(
            failures,
            "REPORT_WITHOUT_HUMAN_DATA",
            f"{REPORT_REL} exists while no independent human reference does: a metric artifact "
            "may not precede its human input",
        )
    if human_present and not exists:
        _fail(
            failures,
            "REPORT_MISSING_WITH_HUMAN_DATA",
            f"a human reference exists but {REPORT_REL} does not: publish the metrics or the "
            "contour is inconsistent",
        )
    return exists


# --------------------------------------------------------------------------- #
# The derived battery.
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


def battery_contract(schemas: Any, failures: Failures) -> dict[str, Any] | None:
    if not isinstance(schemas, dict):
        _fail(
            failures, "MISSING_SCHEMA", "the frozen S03 schemas could not be read for the battery"
        )
        return None
    block = schemas.get("schemas")
    block = block.get("battery") if isinstance(block, dict) else None
    if not isinstance(block, dict):
        _fail(failures, "MISSING_SCHEMA", "the frozen battery schema is missing")
        return None
    closed = block.get("closed_keys")
    checks = block.get("check_closed_keys")
    pins = block.get("pins_closed_keys")
    if not isinstance(closed, list) or not isinstance(checks, list) or not isinstance(pins, list):
        _fail(failures, "MISSING_SCHEMA", "the frozen battery schema lacks its closed key sets")
        return None
    if block.get("schema_id") != BATTERY_SCHEMA_ID:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"the frozen battery schema_id={block.get('schema_id')!r} != {BATTERY_SCHEMA_ID!r}",
        )
    return {
        "closed": frozenset(str(item) for item in closed),
        "checks": frozenset(str(item) for item in checks),
        "pins": frozenset(str(item) for item in pins),
        "model_invoked": block.get("model_invoked"),
    }


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


def check_tracked_battery(
    path: Path | None, contract: dict[str, Any] | None, failures: Failures
) -> int:
    """Validate the tracked S03 battery when it exists (it never hashes itself)."""
    if path is None or not path.is_file() or contract is None:
        return 0
    try:
        doc = load_json(path, "S03 battery")
    except VerificationError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return 0
    if not isinstance(doc, dict):
        _fail(failures, "SCHEMA_KEY_DRIFT", "the S03 battery is not a JSON object")
        return 0
    if set(doc) != contract["closed"]:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"S03 battery keys {sorted(set(doc) ^ contract['closed'])} differ from the frozen "
            "closed set",
        )
    if doc.get("schema") != BATTERY_SCHEMA_ID:
        _fail(
            failures,
            "FROZEN_SOURCE_DRIFT",
            f"S03 battery schema={doc.get('schema')!r} != {BATTERY_SCHEMA_ID!r}",
        )
    if doc.get("schema_version") != SCHEMA_VERSION:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"S03 battery schema_version={doc.get('schema_version')!r} != {SCHEMA_VERSION}",
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
    pins = doc.get("pins")
    if isinstance(pins, list):
        pinned_paths = [str(entry.get("path")) for entry in pins if isinstance(entry, dict)]
        expected_paths = sorted(rel for rel, _pin in PINS.values())
        if sorted(pinned_paths) != expected_paths:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                "the battery pins are not exactly the frozen source roster",
            )
    return check_battery_rows(doc.get("checks"), "battery.checks", failures)


# --------------------------------------------------------------------------- #
# The S02 boundary as a real subprocess.
# --------------------------------------------------------------------------- #


def check_s02_regression(root: Path, chain: Path | None, failures: Failures) -> str:
    """Exit 0 (a human pilot happened) and exit 3 (honest absence) are both green."""
    if chain is None:
        return "absent"
    if not chain.is_file():
        _fail(failures, "S02_REGRESSION_FAILED", f"the S02 closeout chain is missing at {chain}")
        return "missing"
    try:
        completed = subprocess.run(
            ["bash", str(chain)],
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=S02_CHAIN_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _fail(
            failures,
            "S02_REGRESSION_FAILED",
            f"{chain} timed out after {S02_CHAIN_TIMEOUT}s",
        )
        return "timeout"
    except OSError as exc:
        _fail(failures, "S02_REGRESSION_FAILED", f"{chain} could not be spawned: {exc}")
        return "unspawnable"
    if completed.returncode not in (0, 3):
        _fail(
            failures,
            "S02_REGRESSION_FAILED",
            f"{chain} exited {completed.returncode}; only 0 (human pilot performed) and 3 "
            f"(HUMAN_PILOT_ABSENT) are green",
        )
        return f"exit{completed.returncode}"
    return f"exit{completed.returncode}"


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


def load_optional(path: Path | None, label: str, failures: Failures) -> Any:
    if path is None or not path.is_file():
        return None
    try:
        return load_json(path, label)
    except VerificationError as exc:
        _fail(failures, exc.diagnostic, exc.detail)
        return None


def run(root: Path, args: argparse.Namespace) -> tuple[Failures, str, dict[str, Any]]:
    artifacts, failures = resolve_all(root, args)
    try:
        chain: Path | None = chain_path(root, args.s02_chain)
    except VerificationError as exc:
        chain = None
        _fail(failures, exc.diagnostic, exc.detail)

    protocol_path = artifacts.get("s03_protocol")
    protocol_block: Any = None
    if protocol_path is not None and protocol_path.is_file():
        try:
            blocks = fenced_contracts(protocol_path, "S03 protocol")
        except VerificationError as exc:
            blocks = []
            _fail(failures, exc.diagnostic, exc.detail)
        if len(blocks) != 1:
            _fail(
                failures,
                "SCHEMA_KEY_DRIFT",
                f"the S03 protocol must carry exactly one machine-readable contract block, "
                f"found {len(blocks)}",
            )
        else:
            protocol_block = blocks[0]
        if len(blocks) == 1:
            required = (
                protocol_block.get("required_sections")
                if isinstance(protocol_block, dict)
                else None
            )
            if isinstance(required, list) and required:
                text = read_text(protocol_path, "S03 protocol")
                for heading in required:
                    if str(heading) not in text:
                        _fail(
                            failures,
                            REQUIRED_SECTIONS_DIAGNOSTIC,
                            f"the S03 protocol no longer carries the required section "
                            f"{str(heading)!r}",
                        )

    schemas = load_optional(artifacts.get("s03_schemas"), "S03 schemas", failures)
    manifest = load_optional(artifacts.get("s03_manifest"), "S03 eval manifest", failures)
    leakage = load_optional(artifacts.get("s03_leakage"), "S03 leakage report", failures)
    battery_doc = load_optional(artifacts.get("battery"), "S03 battery", failures)

    pinned = check_pins(artifacts, failures)
    diagnostics = check_diagnostic_table(schemas, failures)
    manifest_pins = check_manifest_pins(manifest, root, failures)
    counters = check_counters(manifest, schemas, failures)
    check_split_block(manifest, counters, failures)
    check_strata(manifest, schemas, failures)
    contract = battery_contract(schemas, failures)

    lifecycle_blocks = check_lifecycle(
        [
            ("protocol", protocol_block),
            ("schemas", schemas),
            ("manifest", manifest),
            ("leakage_report", leakage),
            ("battery", battery_doc),
        ],
        failures,
    )

    contracts = 0
    for label, doc in (
        ("protocol", protocol_block),
        ("schemas", schemas),
        ("manifest", manifest),
        ("leakage_report", leakage),
        ("battery", battery_doc),
    ):
        if not isinstance(doc, dict):
            continue
        hits = output_contract_hits(doc)
        if not hits:
            continue
        for _kind, pointer, value in hits:
            contracts += check_output_contract(f"{label}:{pointer}", value, failures)
        scan_claim_values(doc, label, failures)
    if contracts == 0:
        _fail(
            failures,
            "MISSING_SECTION",
            "no S03 artifact carries the frozen output_contract",
        )

    leakage_scanned = check_leakage(
        [
            ("protocol", protocol_block),
            ("schemas", schemas),
            ("manifest", manifest),
            ("leakage_report", leakage),
            ("battery", battery_doc),
        ],
        protocol_block,
        failures,
    )
    fragment_txt, fragment_drift = check_seed(artifacts, manifest, root, failures)
    isolation = check_prompt_isolation(root, failures)
    human_present, submissions, adjudications = observe_human_reference(artifacts)
    report_present = check_report_invariant(artifacts.get("report"), human_present, failures)
    battery_rows = check_tracked_battery(artifacts.get("battery"), contract, failures)
    s02_status = check_s02_regression(root, chain, failures)

    provider_line = ",".join(
        f"{provider}:{PROVIDER_CASE_COUNTS.get(provider, 0)}"
        for provider in ("consultant", "garant")
    )
    base = (
        f"pinned={pinned}/{len(PINS)} cases={counters['cases']} families={counters['families']} "
        f"work_family_cap={counters['work_family_cap']} "
        f"holdout_families={counters['holdout_families']} "
        f"holdout_cases={counters['holdout_cases']} dev_cases={counters['dev_cases']} "
        f"provider_strata={provider_line} fragments={fragment_txt} "
        f"fragment_drift={fragment_drift} isolation_files={isolation} "
        f"aspects={counters.get('aspects', 0)} battery_checks={len(CHAIN_CHECKS)} "
        f"battery_rows={battery_rows} lifecycle_blocks={lifecycle_blocks} "
        f"diagnostics={diagnostics} manifest_pins={manifest_pins} "
        f"leakage_scanned={leakage_scanned} s02_regression={s02_status} "
        f"report={'present' if report_present else 'absent'} "
        f"human_submissions={submissions} human_adjudications={adjudications} "
        f"human_pilot_performed={str(human_present).lower()}"
    )
    if human_present:
        summary = f"{HUMAN_DATA_MARKER} {base}"
    else:
        summary = f"{MARKER} {base} human={ABSENT_TOKEN}"
    details = {
        "pinned": pinned,
        "cases": counters["cases"],
        "families": counters["families"],
        "holdout_families": counters["holdout_families"],
        "holdout_cases": counters["holdout_cases"],
        "fragments": fragment_txt,
        "isolation_files": isolation,
        "aspects": counters.get("aspects", 0),
        "battery_checks": len(CHAIN_CHECKS),
        "battery_rows": battery_rows,
        "human_pilot_performed": human_present,
        "s02_regression": s02_status,
        "report_present": report_present,
        "chain": describe(chain, root),
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
                emit(f"FAIL {diagnostic}: {detail}", sys.stderr)
            except VerificationError as exc:
                emit(f"FAIL {exc.diagnostic}: {exc.detail}", sys.stderr)
        emit(f"FAIL M207_S03_PILOT_GATE: {len(seen)} finding(s)", sys.stderr)
        return FAIL_EXIT
    if not summary:
        return OK_EXIT
    try:
        emit(summary)
    except VerificationError as exc:
        emit(f"FAIL {exc.diagnostic}: {exc.detail}", sys.stderr)
        return FAIL_EXIT
    return OK_EXIT


def parse_results(text: str, failures: Failures) -> list[dict[str, Any]]:
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
        return rows
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
    return rows


def battery(
    results: Path,
    out: Path,
    artifacts: dict[str, Path | None],
    failures: Failures,
    *,
    write: bool,
) -> int:
    """Assemble the tracked slice battery; read-only unless explicitly authorized."""
    if not results.is_file():
        _fail(failures, "EMPTY_SUITE", f"result table {results} does not exist")
        return report(failures, "")
    text = read_text(results, "result table")
    rows = parse_results(text, failures)

    schemas = load_optional(artifacts.get("s03_schemas"), "S03 schemas", failures)
    contract = battery_contract(schemas, failures)
    if contract is None:
        return report(failures, "")
    non_claims = schemas.get("non_claims") if isinstance(schemas, dict) else None
    lifecycle = schemas.get("lifecycle") if isinstance(schemas, dict) else None
    if not isinstance(non_claims, list) or not non_claims:
        _fail(failures, "MISSING_NON_CLAIM", "the frozen non-claims could not be read")
    if not isinstance(lifecycle, dict) or not lifecycle:
        _fail(failures, "MISSING_LIFECYCLE_MARKER", "the frozen lifecycle could not be read")
    if failures:
        return report(failures, "")

    human_present, _submissions, _adjudications = observe_human_reference(artifacts)
    payload = {
        "schema": BATTERY_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "human_pilot_performed": human_present,
        "model_invoked": False,
        "lifecycle": dict(lifecycle),
        "non_claims": list(non_claims),
        "pins": [
            {"path": rel, "sha256": pin} for rel, pin in sorted(PINS.values(), key=lambda p: p[0])
        ],
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
    if set(payload) != contract["closed"]:
        _fail(
            failures,
            "SCHEMA_KEY_DRIFT",
            f"the assembled battery keys {sorted(set(payload) ^ contract['closed'])} differ "
            "from the frozen closed set",
        )
    if contract["model_invoked"] is not False or payload["model_invoked"] is not False:
        _fail(failures, "MODEL_INVOKED", "the frozen battery contract expects no model")
    if failures:
        return report(failures, "")

    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    rendered_bytes = rendered.encode("utf-8")
    timings = " ".join(f"{row['check_id']}={row['durationMs']}ms" for row in rows)
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        current = out.read_bytes() if out.is_file() else None
        outcome = "unchanged" if current == rendered_bytes else "written"
        if current != rendered_bytes:
            out.write_bytes(rendered_bytes)
    elif not out.is_file():
        _fail(failures, "MISSING_ARTIFACT", f"battery missing at {out}")
        return report(failures, "")
    elif out.read_bytes() != rendered_bytes:
        _fail(
            failures,
            "BATTERY_STALE",
            "assembled battery differs from the tracked battery; regenerate once with "
            "M207_S03_WRITE_BATTERY=1 --write before host verification",
        )
        return report(failures, "")
    else:
        outcome = "current"
    emit(f"{BATTERY_MARKER} checks={len(rows)} path={out.name} {outcome}")
    emit(f"{BATTERY_TIMINGS} {timings}")
    return OK_EXIT


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
        "--s02-chain",
        dest="s02_chain",
        default=S02_CHAIN_REL,
        help="the S02 closeout chain this verifier re-runs as a subprocess",
    )
    parser.add_argument("--results", default="", help="battery mode: tab-separated result table")
    parser.add_argument("--out", default=BATTERY_REL, help="battery mode: battery output path")
    parser.add_argument(
        "--write",
        action="store_true",
        help="battery mode: regenerate the tracked battery (needs M207_S03_WRITE_BATTERY=1)",
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
                root, args.out, "battery", suffix=".json", prefix=EVIDENCE_PREFIX
            )
        except VerificationError as exc:
            return report([(exc.diagnostic, exc.detail)], "")
        artifacts, resolve_failures = resolve_all(root, args)
        failures.extend(resolve_failures)
        if args.write and os.environ.get(BATTERY_WRITE_ENV) != "1":
            return report(
                [
                    (
                        "AUTHORITY_CLAIM",
                        f"--write was requested without {BATTERY_WRITE_ENV}=1: the tracked "
                        "battery is written only by the authorized closing chain",
                    )
                ],
                "",
            )
        write = args.write and os.environ.get(BATTERY_WRITE_ENV) == "1"
        return battery(Path(args.results), out, artifacts, failures, write=write)

    failures, summary, _details = run(root, args)
    return report(failures, summary)


if __name__ == "__main__":
    raise SystemExit(main())
