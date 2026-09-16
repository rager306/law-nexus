#!/usr/bin/env python3
"""M207 S03 T02 -- frozen evaluation manifest, Work-family holdout, provider strata.

This gate freezes the *selection* half of the S03 evaluation contour on the 40
frozen S01 pilot cases (24 Work families, family cap 4) and publishes the two
tracked artifacts of T02:

* ``prd/migration/rust-evidence/m207-s03-eval-manifest.json``
  (``m207-s03-eval-manifest/v1``) -- seed, family table, family-granular
  holdout/dev split, per-case provider/stratum/scope/metadata, provider strata
  with ``quota <= availability`` justifications, the sealed C3 exclusion set,
  the 180 frozen fragment pins, the frozen-source pins and the lifecycle
  markers;
* ``prd/migration/rust-evidence/m207-s03-leakage-report.json``
  (``m207-s03-leakage-report/v1``) -- every leakage check with
  ``required``/``observed``/``status``.

Modes::

    check      read-only: verify pins, byte-compare the regeneration
               (MANIFEST_STALE) and print M207_S03_EVAL_MANIFEST_OK <counters>
    run        regenerate and write both artifacts
    selftest   prove the named refusal paths on temporary copies

The tool measures **nothing**.  It declares no rate, no denominator, no gold,
no threshold and no promotion: the per-aspect rates belong to T03 and become
publishable only against the independent human reference of S02.  Metadata is
published **as-is**: the frozen ``metadata_source/year/document_type = unknown``
of all 40 cases stays ``unknown`` and is never re-derived from a path.

Decisions frozen here (the protocol fixes the vocabulary, this manifest fixes
the concrete instances):

* **Declared provider roots.**  ``consru_export/consru_export/exports`` and
  ``law-source/consultant`` are consultant roots, ``law-source/garant`` is a
  garant root; anything else -- including ``law-source/consultant/**`` when the
  third root is not declared -- stays ``unknown`` and is never guessed from
  digits in a file name or a substring of the full path.  The pilot contains
  three ``law-source/consultant/**`` cases, so declaring that root is what makes
  ``provider_strata=consultant:40,garant:0`` an honest counter rather than a
  filename heuristic (``PROVIDER_MISATTRIBUTED``/``METADATA_REDERIVED``).  Both
  the declared root and the case path are canonicalized before any
  relativization, because ``.gsd`` is a symlink and an uncanolicalized
  ``path.relative`` yields ``../``-poisoned paths.
* **Family-granular holdout.**  Every Work family is ranked by
  ``splitmix64``-style mixing of ``sha256(work_family)`` seeded with the frozen
  S01 ``draw_seed`` -- the same construction as Rust
  ``corpus_sample::mixed_rank`` -- and the lowest-ranked ``HOLDOUT_FAMILY_COUNT``
  families form the holdout.  The split is a pure function of the seed and the
  frozen family set, so it is frozen before any measurement and reproduces
  byte-for-byte.  A family is never split across scopes.
* **Marker printing rule.**  The marker prints every *declared* provider stratum
  even at zero units (``garant:0`` must stay visible; dropping it is
  ``PROVIDER_STRATUM_DROPPED``) and prints the residual ``unknown`` stratum only
  when it has units.
* **C5 ladder cross-check (read-only, F02 remainder).**  The three frozen
  ``m204-s02-c5-gold-manifest-{100,400,800}.json`` manifests are re-read and
  must carry validated-or-unknown metadata (``METADATA_REDERIVED``), provider
  strata with non-empty ``quota``/``availability_cap``
  (``PROVIDER_QUOTA_UNJUSTIFIED``/``PROVIDER_STRATUM_DROPPED``), a seed-driven
  draw (``C5_MEASUREMENT_CLAIM``), path-safe entry paths (``UNSAFE_PATH``) and
  no measurement, no ``double_coded_accepted`` and no promoted claim
  (``C5_MEASUREMENT_CLAIM``).  The C5 artifacts are never mutated.

Fail-closed diagnostics spoken by this tool (all names exist in the frozen
``$.diagnostics`` table; a name outside it is ``DIAGNOSTIC_TABLE_DRIFT``):
``MISSING_ARTIFACT``, ``MISSING_SCHEMA``, ``MISSING_LIFECYCLE_MARKER``,
``MISSING_NON_CLAIM``, ``SCHEMA_KEY_DRIFT``, ``SCHEMA_PARSE_ERROR``,
``DUPLICATE_JSON_KEY``, ``VOCABULARY_DRIFT``, ``UNSAFE_PATH``,
``FROZEN_SOURCE_DRIFT``, ``FRAGMENT_PIN_DRIFT``, ``HOLDOUT_LEAKAGE``,
``C3_ISOLATION_VIOLATION``, ``WORK_FAMILY_DOMINANCE``, ``SEED_ENLARGED``,
``PROVIDER_STRATUM_DROPPED``, ``PROVIDER_QUOTA_UNJUSTIFIED``,
``PROVIDER_MISATTRIBUTED``, ``METADATA_REDERIVED``, ``C5_MEASUREMENT_CLAIM``,
``MANIFEST_STALE``, ``CASE_COUNT_OUT_OF_RANGE``, ``STRATUM_TABLE_DRIFT``,
``MEASUREMENT_STATUS_DRIFT``, ``PROXY_INPUT_REFUSED``, ``UNKNOWN_CASE_ID``,
``DIAGNOSTIC_TABLE_DRIFT``.

Every refusal is fail-closed: the contour is built and validated **before** a
single byte is written, so a hostile input produces a named diagnostic and no
artifact (a probe in ``selftest`` asserts that the tracked artifacts are byte
identical before and after the refusal).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

MARKER = "M207_S03_EVAL_MANIFEST_OK"
SELFTEST_MARKER = "M207_S03_EVAL_MANIFEST_SELFTEST_OK"
WRITTEN_LINE = "m207_s03_eval_manifest=written"
C5_LINE_PREFIX = "m207_s03_c5_cross_check="

FAIL_EXIT = 1
OK_EXIT = 0

SCHEMA_VERSION = 1
MANIFEST_SCHEMA = "m207-s03-eval-manifest/v1"
LEAKAGE_SCHEMA = "m207-s03-leakage-report/v1"
CASES_SCHEMA = "m207-s01-pilot-cases/v1"
CORPUS_MANIFEST_SCHEMA = "law-nexus-npa-corpus-manifest/v1"

# -- frozen inputs --------------------------------------------------------- #
CASES_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
PROMPT_PACKETS_REL = "prd/migration/rust-evidence/m207-s01-prompt-packets.jsonl"
C3_REL = "prd/migration/rust-evidence/m203-s08-c3-holdout-manifest.json"
C5_RELS = (
    "prd/migration/rust-evidence/m204-s02-c5-gold-manifest-100.json",
    "prd/migration/rust-evidence/m204-s02-c5-gold-manifest-400.json",
    "prd/migration/rust-evidence/m204-s02-c5-gold-manifest-800.json",
)
SCHEMAS_REL = "prd/annotation/m207-s03-schemas.json"
PROTOCOL_REL = "prd/annotation/m207-s03-eval-protocol.md"
CODEBOOK_REL = "prd/annotation/m207-s01-codebook.md"
METAPROMPT_REL = "prd/annotation/m207-s01-metaprompt.md"
S01_SCHEMAS_REL = "prd/annotation/m207-s01-schemas.json"
S02_PROTOCOL_REL = "prd/annotation/m207-s02-coder-protocol.md"
S02_SCHEMAS_REL = "prd/annotation/m207-s02-schemas.json"
M199_PROTOCOL_REL = "prd/migration/rust-evidence/m199-s01-annotation-protocol.md"
KIT_PASS1_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json"
KIT_PASS2_REL = "prd/migration/rust-evidence/m207-s02-coder-kit-pass2.json"
FIXTURE_DIR_REL = "crates/ln-decode/tests/fixtures/npa-lawref"
SEED_SIDECAR_NAME = "lawref_seed.json"

MANIFEST_REL = "prd/migration/rust-evidence/m207-s03-eval-manifest.json"
LEAKAGE_REL = "prd/migration/rust-evidence/m207-s03-leakage-report.json"

# The prompt packets inline *decoded source text* (``fragment_text``).  That is not a
# development surface, so it is scanned separately and reported as
# ``inlined_source_text_hits`` instead of being counted as a holdout leak.
INLINED_TEXT_KEYS = frozenset({"fragment_text"})

# -- frozen constants ------------------------------------------------------ #
CASE_COUNT = 40
FAMILY_COUNT = 24
WORK_FAMILY_CAP = 4
FRAGMENT_COUNT = 180
HOLDOUT_FAMILY_COUNT = 8
MIN_CALENDAR_YEAR = 1991
MAX_CALENDAR_YEAR = 2027

# The declared provider roots.  Only these attribute a provider; every other
# path stays `unknown`.  Order is part of the freeze.
DECLARED_PROVIDER_ROOTS: tuple[tuple[str, str], ...] = (
    ("consru_export/consru_export/exports", "consultant"),
    ("law-source/consultant", "consultant"),
    ("law-source/garant", "garant"),
)
UNKNOWN_PROVIDER = "unknown"
PROVIDER_ORDER = ("consultant", "garant", UNKNOWN_PROVIDER)
RESIDUAL_PROVIDERS = frozenset({UNKNOWN_PROVIDER})

ALLOWED_METADATA_SOURCES = frozenset({"unknown", "validated-manifest"})
UNKNOWN_METADATA_VALUE = "unknown"

MEASUREMENT_STATUS_VALUES = ("not-measured", "proxy-measured", "independent-measured")
STRATUM_MEASUREMENT_STATUS = "not-measured"

LEAKAGE_DIAGNOSTICS = frozenset(
    {"HOLDOUT_LEAKAGE", "C3_ISOLATION_VIOLATION", "WORK_FAMILY_DOMINANCE", "SEED_ENLARGED"}
)

# Claim tokens refused inside a C5 ladder manifest: a producer manifest may not
# publish a measurement or a promoted acceptance.
C5_FORBIDDEN_KEYS = frozenset(
    {
        "double_coded_accepted",
        "measurement",
        "measurement_status",
        "measured",
        "denominator",
        "precision",
        "recall",
        "accuracy",
        "kappa",
        "alpha",
        "rate",
        "f1",
        "is_gold",
        "gold",
        "human_acceptance",
        "promotion",
        "threshold",
        "classification",
        "label",
        "expected",
        "answer",
        "prediction",
        "capture",
    }
)

# Every diagnostic this module may speak, checked against the frozen table.
TOOL_DIAGNOSTICS = (
    "MISSING_ARTIFACT",
    "MISSING_SCHEMA",
    "MISSING_LIFECYCLE_MARKER",
    "MISSING_NON_CLAIM",
    "SCHEMA_KEY_DRIFT",
    "SCHEMA_PARSE_ERROR",
    "DUPLICATE_JSON_KEY",
    "VOCABULARY_DRIFT",
    "UNSAFE_PATH",
    "FROZEN_SOURCE_DRIFT",
    "FRAGMENT_PIN_DRIFT",
    "HOLDOUT_LEAKAGE",
    "C3_ISOLATION_VIOLATION",
    "WORK_FAMILY_DOMINANCE",
    "SEED_ENLARGED",
    "PROVIDER_STRATUM_DROPPED",
    "PROVIDER_QUOTA_UNJUSTIFIED",
    "PROVIDER_MISATTRIBUTED",
    "METADATA_REDERIVED",
    "C5_MEASUREMENT_CLAIM",
    "MANIFEST_STALE",
    "CASE_COUNT_OUT_OF_RANGE",
    "STRATUM_TABLE_DRIFT",
    "MEASUREMENT_STATUS_DRIFT",
    "PROXY_INPUT_REFUSED",
    "UNKNOWN_CASE_ID",
    "DIAGNOSTIC_TABLE_DRIFT",
)


class GateError(Exception):
    """Named, machine-distinguishable refusal."""

    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


# --------------------------------------------------------------------------- #
# Hashing, path safety and closed JSON (the S01/S02 contract, copied verbatim
# in behaviour: S03 must re-use it, not reinvent it).
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def resolve_artifact(root: Path, raw: str, label: str, *, suffix: str | None = None) -> Path:
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
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    if not candidate.is_relative_to(root_resolved):
        raise GateError("UNSAFE_PATH", f"{label}={raw!r} resolves outside {root_resolved}")
    return candidate


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GateError("DUPLICATE_JSON_KEY", f"duplicate JSON key {key!r}")
        seen[key] = value
    return seen


def load_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except GateError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError("SCHEMA_PARSE_ERROR", f"{label}: {exc}") from exc


def read_bytes(root: Path, raw: str, label: str, *, suffix: str | None = None) -> bytes:
    path = resolve_artifact(root, raw, label, suffix=suffix)
    if not path.is_file():
        raise GateError("MISSING_ARTIFACT", f"{label}={raw!r} is not a file under {root}")
    return path.read_bytes()


def read_json(root: Path, raw: str, label: str) -> Any:
    return load_json_bytes(read_bytes(root, raw, label), raw)


# --------------------------------------------------------------------------- #
# Deterministic ranking (mirrors Rust `corpus_sample::mixed_rank`).
# --------------------------------------------------------------------------- #

_MASK64 = (1 << 64) - 1


def _rotate_left(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (64 - shift))) & _MASK64


def mixed_rank(seed: int, digest_hex: str) -> int:
    """Stable splitmix-style rank over a 64-digit hexadecimal digest.

    Byte-for-byte the construction of ``crates/ln-consultant-parser/src/corpus_sample.rs``
    (``mixed_rank``): seed xor const, then rotate/multiply over the digest byte
    pairs, then SplitMix integer mixing.  No path order, process state,
    ``DefaultHasher`` or random generator is involved.
    """
    if len(digest_hex) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest_hex):
        raise GateError("SCHEMA_PARSE_ERROR", f"digest {digest_hex!r} is not 64 hex digits")
    value = (seed ^ 0x9E3779B97F4A7C15) & _MASK64
    lowered = digest_hex.lower()
    for index in range(0, 64, 2):
        byte = int(lowered[index : index + 2], 16)
        value = _rotate_left(value, 7) ^ byte
        value = (value * 0x100000001B3) & _MASK64
    z = value
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK64
    return z ^ (z >> 31)


def family_rank(seed: int, work_family: str) -> int:
    return mixed_rank(seed, sha256_bytes(work_family.encode("utf-8")))


# --------------------------------------------------------------------------- #
# Provider attribution (declared roots only, canonicalized before relativizing).
# --------------------------------------------------------------------------- #


def posix_relative(base: Path, child: Path) -> str:
    """Canonical relative path: never applied to an uncanonicalized input.

    Both sides are already ``resolve()``-canonicalized by the caller, so the
    ``../``-poisoning the repository hit with ``path.relative`` on the ``.gsd``
    symlink cannot occur here.
    """
    if not child.is_relative_to(base):
        raise GateError("UNSAFE_PATH", f"{child} is not inside {base}")
    return PurePosixPath(*child.relative_to(base).parts).as_posix()


def attribute_provider(root: Path, source_path: str, label: str) -> tuple[str, str | None]:
    """Attribute a case to a declared provider root, or to ``unknown``.

    The root and the case path are canonicalized *before* any relativization.
    No file-name digit heuristic and no substring of the full checkout path is
    used: an undeclared root is honestly ``unknown``.
    """
    root_real = root.resolve()
    target = resolve_artifact(root, source_path, label).resolve(strict=False)
    for declared_root, provider in DECLARED_PROVIDER_ROOTS:
        base = (root_real / declared_root).resolve(strict=False)
        if target.is_relative_to(base):
            posix_relative(base, target)  # prove canonicalization precedes relativization
            return provider, declared_root
    return UNKNOWN_PROVIDER, None


# --------------------------------------------------------------------------- #
# Frozen inputs.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Paths:
    cases: str = CASES_REL
    prompt_packets: str = PROMPT_PACKETS_REL
    c3: str = C3_REL
    c5: tuple[str, str, str] = C5_RELS
    schemas: str = SCHEMAS_REL
    protocol: str = PROTOCOL_REL
    codebook: str = CODEBOOK_REL
    metaprompt: str = METAPROMPT_REL
    s01_schemas: str = S01_SCHEMAS_REL
    s02_protocol: str = S02_PROTOCOL_REL
    s02_schemas: str = S02_SCHEMAS_REL
    m199_protocol: str = M199_PROTOCOL_REL
    kit_pass1: str = KIT_PASS1_REL
    kit_pass2: str = KIT_PASS2_REL
    fixture_dir: str = FIXTURE_DIR_REL
    manifest: str = MANIFEST_REL
    leakage: str = LEAKAGE_REL

    def surfaces(self) -> tuple[tuple[str, str], ...]:
        return (
            ("codebook", self.codebook),
            ("metaprompt", self.metaprompt),
            ("prompt_packets", self.prompt_packets),
            ("coder_kit_pass1", self.kit_pass1),
            ("coder_kit_pass2", self.kit_pass2),
        )

    def pin_sources(self) -> dict[str, str]:
        return {
            "m207_s01_codebook": self.codebook,
            "m207_s01_metaprompt": self.metaprompt,
            "m207_s01_schemas": self.s01_schemas,
            "m207_s01_cases": self.cases,
            "m207_s01_prompt_packets": self.prompt_packets,
            "m207_s02_protocol": self.s02_protocol,
            "m207_s02_schemas": self.s02_schemas,
            "m207_s02_coder_kit_pass1": self.kit_pass1,
            "m207_s02_coder_kit_pass2": self.kit_pass2,
            "m199_protocol": self.m199_protocol,
            "m207_s03_protocol": self.protocol,
            "m207_s03_schemas": self.schemas,
            "m203_s08_c3_holdout": self.c3,
            "m204_s02_c5_gold_100": self.c5[0],
            "m204_s02_c5_gold_400": self.c5[1],
            "m204_s02_c5_gold_800": self.c5[2],
        }


def load_schemas(root: Path, paths: Paths) -> dict[str, Any]:
    doc = read_json(root, paths.schemas, "m207-s03 schemas")
    if not isinstance(doc, dict) or doc.get("schema") != "m207-s03-eval-schemas/v1":
        raise GateError("MISSING_SCHEMA", f"{paths.schemas} is not m207-s03-eval-schemas/v1")
    return doc


def load_frozen_cases(root: Path, paths: Paths) -> tuple[int, int, list[dict[str, Any]]]:
    doc = read_json(root, paths.cases, "m207-s01 pilot cases")
    if doc.get("schema") != CASES_SCHEMA:
        raise GateError(
            "FROZEN_SOURCE_DRIFT",
            f"{paths.cases} schema={doc.get('schema')!r} is not {CASES_SCHEMA!r}",
        )
    cases = doc.get("cases")
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        raise GateError(
            "CASE_COUNT_OUT_OF_RANGE",
            f"{paths.cases} carries {len(cases) if isinstance(cases, list) else 'no'} cases, "
            f"expected {CASE_COUNT}",
        )
    if doc.get("case_count") != len(cases):
        raise GateError(
            "CASE_COUNT_OUT_OF_RANGE", f"{paths.cases} case_count disagrees with cases[]"
        )
    cap = doc.get("work_family_cap")
    if cap != WORK_FAMILY_CAP:
        raise GateError(
            "WORK_FAMILY_DOMINANCE", f"work_family_cap={cap!r} != frozen {WORK_FAMILY_CAP}"
        )
    seed = doc.get("draw_seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise GateError("SCHEMA_PARSE_ERROR", f"{paths.cases} draw_seed={seed!r} is not an integer")
    return seed, cap, cases


def collect_fragments(root: Path, paths: Paths) -> list[dict[str, str]]:
    """The 180 frozen ``*.txt`` fragments, pinned by name and content."""
    directory = resolve_artifact(root, paths.fixture_dir, "fixture dir")
    if not directory.is_dir():
        raise GateError("MISSING_ARTIFACT", f"fixture dir {paths.fixture_dir!r} is not a directory")
    txts = sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == ".txt")
    if len(txts) != FRAGMENT_COUNT:
        raise GateError(
            "SEED_ENLARGED",
            f"the seed holds {len(txts)} .txt fragments, the frozen seed is {FRAGMENT_COUNT}",
        )
    pins = [
        {
            "path": f"{paths.fixture_dir}/{p.name}",
            "sha256": sha256_file(p),
        }
        for p in txts
    ]
    # The rule-seed sidecar sits in the same directory; it is a producer surface
    # and must never be consumed as an evaluation input.
    if any(not pin["path"].endswith(".txt") for pin in pins):
        raise GateError("PROXY_INPUT_REFUSED", "a non-.txt seed file entered the fragment pins")
    sidecar = directory / SEED_SIDECAR_NAME
    if sidecar.exists() and any(pin["path"].endswith(SEED_SIDECAR_NAME) for pin in pins):
        raise GateError("PROXY_INPUT_REFUSED", f"{SEED_SIDECAR_NAME} must not be consumed")
    return pins


def fragment_rollup(pins: list[dict[str, str]]) -> str:
    lines = [
        f"{Path(pin['path']).name} {pin['sha256']}" for pin in sorted(pins, key=lambda p: p["path"])
    ]
    return sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def load_c3_hashes(root: Path, paths: Paths) -> list[str]:
    doc = read_json(root, paths.c3, "sealed C3 holdout manifest")
    if doc.get("schema_version") != CORPUS_MANIFEST_SCHEMA:
        raise GateError(
            "C3_ISOLATION_VIOLATION",
            f"{paths.c3} schema_version={doc.get('schema_version')!r} is not the corpus manifest",
        )
    if doc.get("sealed") is not True:
        raise GateError("C3_ISOLATION_VIOLATION", f"{paths.c3} is not sealed=true")
    entries = doc.get("entries")
    if not isinstance(entries, list):
        raise GateError("C3_ISOLATION_VIOLATION", f"{paths.c3} carries no entries[]")
    hashes: set[str] = set()
    for index, entry in enumerate(entries):
        value = entry.get("content_hash") if isinstance(entry, dict) else None
        if not isinstance(value, str) or not value.startswith("sha256:"):
            raise GateError(
                "C3_ISOLATION_VIOLATION",
                f"{paths.c3} entries[{index}].content_hash={value!r} is not a sha256: digest",
            )
        hashes.add(value)
    return sorted(hashes)


def _iter_strings(
    payload: Any, *, skip_keys: frozenset[str] = frozenset()
) -> tuple[list[str], list[str]]:
    """Return (development-surface strings, inlined decoded-source strings)."""
    surface: list[str] = []
    inlined: list[str] = []

    def walk(node: Any, *, skipped: bool) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, skipped=skipped or key in skip_keys)
        elif isinstance(node, list):
            for value in node:
                walk(value, skipped=skipped)
        elif isinstance(node, str):
            (inlined if skipped else surface).append(node)

    walk(payload, skipped=False)
    return surface, inlined


def scan_development_surfaces(
    root: Path, paths: Paths, identifiers: list[str]
) -> tuple[list[str], int]:
    """Return (real leaks, inlined-text hits) for the holdout family identity."""
    hits: list[str] = []
    inlined_hits = 0
    for surface_name, rel in paths.surfaces():
        raw = read_bytes(root, rel, f"development surface {surface_name}")
        if rel.endswith(".jsonl"):
            payload: Any = [
                json.loads(line, object_pairs_hook=_reject_duplicate_keys)
                for line in raw.decode("utf-8").splitlines()
                if line.strip()
            ]
        elif rel.endswith(".json"):
            payload = load_json_bytes(raw, rel)
        else:
            payload = raw.decode("utf-8")
        if isinstance(payload, str):
            surface_strings, inlined_strings = [payload], []
        else:
            surface_strings, inlined_strings = _iter_strings(payload, skip_keys=INLINED_TEXT_KEYS)
        haystack = "\n".join(surface_strings)
        inlined_text = "\n".join(inlined_strings)
        for identifier in identifiers:
            if identifier in haystack:
                hits.append(f"{surface_name}:{identifier}")
            elif identifier in inlined_text:
                inlined_hits += 1
    return hits, inlined_hits


# --------------------------------------------------------------------------- #
# Derivation.
# --------------------------------------------------------------------------- #


@dataclass
class Contour:
    seed: int
    cap: int
    families: list[dict[str, Any]]
    holdout: list[str]
    dev: list[str]
    scope_of: dict[str, str]
    cases: list[dict[str, Any]]
    strata: list[dict[str, Any]]
    c3_hashes: list[str]
    fragments: list[dict[str, str]]
    holdout_cases: int
    dev_cases: int


def derive_split(
    cases: list[dict[str, Any]], seed: int, holdout_count: int
) -> tuple[Counter[str], list[tuple[int, str]], list[str], list[str]]:
    counts: Counter[str] = Counter(case.get("work_family") for case in cases)
    if any(not isinstance(family, str) or not family for family in counts):
        raise GateError("SCHEMA_KEY_DRIFT", "a frozen case carries no work_family")
    over = sorted(f for f, n in counts.items() if n > WORK_FAMILY_CAP)
    if over:
        raise GateError(
            "WORK_FAMILY_DOMINANCE",
            f"Work families above the frozen cap of {WORK_FAMILY_CAP}: "
            f"{[(f, counts[f]) for f in over]}",
        )
    if len(counts) != FAMILY_COUNT:
        raise GateError(
            "CASE_COUNT_OUT_OF_RANGE",
            f"{len(counts)} Work families, the frozen pilot declares {FAMILY_COUNT}",
        )
    ranked = sorted(((family_rank(seed, family), family) for family in counts), key=lambda p: p)
    if holdout_count <= 0 or holdout_count >= len(ranked):
        raise GateError(
            "SCHEMA_PARSE_ERROR",
            f"holdout family count {holdout_count} is not inside 1..{len(ranked) - 1}",
        )
    holdout = [family for _, family in ranked[:holdout_count]]
    dev = [family for _, family in ranked[holdout_count:]]
    return counts, ranked, holdout, dev


def build_cases(
    root: Path, paths: Paths, frozen_cases: list[dict[str, Any]], scope_of: dict[str, str]
) -> list[dict[str, Any]]:
    built: list[dict[str, Any]] = []
    for case in sorted(frozen_cases, key=lambda c: str(c.get("case_id"))):
        case_id = case.get("case_id")
        source_path = case.get("source_path")
        source_sha256 = case.get("source_sha256")
        work_family = case.get("work_family")
        if not isinstance(case_id, str) or not isinstance(source_path, str):
            raise GateError("SCHEMA_KEY_DRIFT", f"frozen case {case_id!r} lacks id/source_path")
        if not isinstance(source_sha256, str) or len(source_sha256) != 64:
            raise GateError(
                "SCHEMA_KEY_DRIFT", f"case {case_id} source_sha256 is not 64 hex digits"
            )
        if work_family not in scope_of:
            raise GateError("SCHEMA_KEY_DRIFT", f"case {case_id} family {work_family!r} is unknown")
        provider, provider_root = attribute_provider(
            root, source_path, f"case {case_id} source_path"
        )
        fragment_rel = f"{paths.fixture_dir}/{case.get('fragment_id')}.txt"
        fragment_bytes = read_bytes(root, fragment_rel, f"case {case_id} fragment", suffix=".txt")
        if len(fragment_bytes) != case.get("byte_len"):
            raise GateError(
                "FRAGMENT_PIN_DRIFT",
                f"case {case_id} byte_len={case.get('byte_len')!r} != fragment bytes "
                f"{len(fragment_bytes)}",
            )
        metadata_source = case.get("metadata_source")
        year = case.get("year")
        document_type = case.get("document_type")
        if metadata_source not in ALLOWED_METADATA_SOURCES:
            raise GateError(
                "METADATA_REDERIVED",
                f"case {case_id} metadata_source={metadata_source!r} is not in "
                f"{sorted(ALLOWED_METADATA_SOURCES)}",
            )
        if metadata_source == UNKNOWN_METADATA_VALUE and (
            year != UNKNOWN_METADATA_VALUE or document_type != UNKNOWN_METADATA_VALUE
        ):
            raise GateError(
                "METADATA_REDERIVED",
                f"case {case_id} declares metadata_source=unknown but publishes "
                f"year={year!r} document_type={document_type!r}",
            )
        built.append(
            {
                "case_id": case_id,
                "work_family": work_family,
                "family_scope": scope_of[work_family],
                "draw_stratum": case.get("draw_stratum"),
                "provider": provider,
                "provider_root": provider_root,
                "source_path": source_path,
                "source_sha256": source_sha256,
                "fragment_sha256": sha256_bytes(fragment_bytes),
                "byte_len": case.get("byte_len"),
                "year": year,
                "document_type": document_type,
                "metadata_source": metadata_source,
            }
        )
    return built


def build_provider_strata(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    availability = Counter(case["provider"] for case in cases)
    rows: list[dict[str, Any]] = []
    for provider in PROVIDER_ORDER:
        available = availability.get(provider, 0)
        quota = available
        if provider == UNKNOWN_PROVIDER:
            prefix = (
                f"undeclared paths attribute {available} of the {CASE_COUNT} frozen pilot cases "
                "(no frozen case falls outside the declared provider roots)"
            )
        else:
            declared = ", ".join(f"`{r}`" for r, p in DECLARED_PROVIDER_ROOTS if p == provider)
            prefix = (
                f"declared root {declared} attributes {available} of the {CASE_COUNT} "
                "frozen pilot cases"
            )
        justification = f"{prefix}; quota {quota} <= availability {available}; " + (
            "the stratum is retained as not-measured -- a zero stratum is honest, "
            "dropping it is PROVIDER_STRATUM_DROPPED"
            if available == 0
            else "the stratum stays not-measured until the independent S02 human reference exists"
        )
        rows.append(
            {
                "provider": provider,
                "availability": available,
                "quota": quota,
                "justification": justification,
                "measurement_status": STRATUM_MEASUREMENT_STATUS,
            }
        )
    return rows


def build_pins(root: Path, paths: Paths, contour: Contour) -> dict[str, Any]:
    """The single place pins are declared: split contract, source pins, seed rollup."""
    return {
        "split": build_split_declaration(contour),
        "sources": {
            key: {"path": rel, "sha256": sha256_file(resolve_artifact(root, rel, f"pin {key}"))}
            for key, rel in paths.pin_sources().items()
        },
        "fragment_rollup": {
            "path": paths.fixture_dir,
            "count": FRAGMENT_COUNT,
            "sha256": f"sha256:{fragment_rollup(contour.fragments)}",
        },
    }


def build_contour(
    root: Path, paths: Paths, *, holdout_family_count: int = HOLDOUT_FAMILY_COUNT
) -> Contour:
    load_schemas(root, paths)
    c5_cross_check(root, paths)
    seed, cap, frozen_cases = load_frozen_cases(root, paths)
    counts, ranked, holdout, dev = derive_split(frozen_cases, seed, holdout_family_count)
    scope_of = {family: "holdout" for family in holdout} | {family: "dev" for family in dev}
    families = [
        {
            "work_family": family,
            "rank": rank,
            "case_count": counts[family],
            "family_scope": scope_of[family],
        }
        for rank, family in ranked
    ]
    cases = build_cases(root, paths, frozen_cases, scope_of)
    strata = build_provider_strata(cases)
    c3_hashes = load_c3_hashes(root, paths)
    fragments = collect_fragments(root, paths)
    holdout_cases = sum(counts[family] for family in holdout)
    return Contour(
        seed=seed,
        cap=cap,
        families=families,
        holdout=holdout,
        dev=dev,
        scope_of=scope_of,
        cases=cases,
        strata=strata,
        c3_hashes=c3_hashes,
        fragments=fragments,
        holdout_cases=holdout_cases,
        dev_cases=CASE_COUNT - holdout_cases,
    )


def build_split_declaration(contour: Contour) -> dict[str, Any]:
    return {
        "granularity": "work_family",
        "seed": contour.seed,
        "seed_source": "frozen m207-s01-pilot-cases/v1 draw_seed",
        "rank_algorithm": (
            "splitmix64 mixing of sha256(work_family) seeded with seed ^ 0x9e3779b97f4a7c15 "
            "(rotate_left(7)/0x100000001b3 over the digest byte pairs), mirroring Rust "
            "corpus_sample::mixed_rank"
        ),
        "family_count": len(contour.families),
        "holdout_family_count": len(contour.holdout),
        "dev_family_count": len(contour.dev),
        "holdout_cases": contour.holdout_cases,
        "dev_cases": contour.dev_cases,
        "holdout_families_sha256": (
            f"sha256:{sha256_bytes(('\n'.join(contour.holdout) + '\n').encode('utf-8'))}"
        ),
        "rank_order": [[row["work_family"], row["rank"]] for row in contour.families],
    }


def build_manifest(
    root: Path, paths: Paths, contour: Contour, schemas: dict[str, Any]
) -> dict[str, Any]:
    fragments = contour.fragments
    return {
        "schema": MANIFEST_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "seed": contour.seed,
        "families": contour.families,
        "holdout_families": contour.holdout,
        "dev_families": contour.dev,
        "cases": contour.cases,
        "provider_strata": contour.strata,
        "c3_hashes_excluded": [
            f"sha256:{value.removeprefix('sha256:')}" for value in contour.c3_hashes
        ],
        "fragments": fragments,
        "pins": build_pins(root, paths, contour),
        "lifecycle": schemas["lifecycle"],
        "non_claims": schemas["non_claims"],
    }


# --------------------------------------------------------------------------- #
# Leakage checks.
# --------------------------------------------------------------------------- #


def make_check(
    check_id: str, required: str, observed: str, ok: bool, diagnostic: str
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "required": required,
        "observed": observed,
        "status": "pass" if ok else "fail",
        "diagnostic": diagnostic,
    }


def compute_leakage_checks(root: Path, paths: Paths, contour: Contour) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    intersection = sorted(set(contour.holdout) & set(contour.dev))
    checks.append(
        make_check(
            "holdout_dev_disjoint",
            "holdout_families and dev_families are disjoint (|intersection| == 0)",
            f"|intersection|={len(intersection)}",
            not intersection,
            "HOLDOUT_LEAKAGE",
        )
    )

    per_family_scope: dict[str, set[str]] = {}
    for case in contour.cases:
        per_family_scope.setdefault(case["work_family"], set()).add(case["family_scope"])
    split_families = sorted(f for f, scopes in per_family_scope.items() if len(scopes) > 1)
    checks.append(
        make_check(
            "holdout_family_granularity",
            "every Work family is wholly in holdout or wholly in dev (no family is split across scopes)",
            f"families_split_across_scopes={len(split_families)}",
            not split_families,
            "HOLDOUT_LEAKAGE",
        )
    )

    hits, inlined_hits = scan_development_surfaces(root, paths, contour.holdout)
    checks.append(
        make_check(
            "holdout_family_absent_from_development_surface",
            "no holdout Work-family identifier appears in the frozen codebook, metaprompt, "
            "prompt packets or coder kits",
            f"matches={len(hits)} inlined_source_text_hits={inlined_hits}"
            + (f" first={hits[0]}" if hits else ""),
            not hits,
            "HOLDOUT_LEAKAGE",
        )
    )

    holdout_hashes = {
        f"sha256:{case['source_sha256']}"
        for case in contour.cases
        if case["family_scope"] == "holdout"
    }
    all_hashes = {f"sha256:{case['source_sha256']}" for case in contour.cases}
    c3 = set(contour.c3_hashes)
    holdout_overlap = sorted(holdout_hashes & c3)
    all_overlap = sorted(all_hashes & c3)
    checks.append(
        make_check(
            "holdout_hashes_absent_from_sealed_c3",
            "no holdout case content hash appears in the sealed C3 holdout manifest",
            f"holdout_overlap={len(holdout_overlap)} (holdout_hashes={len(holdout_hashes)}) "
            f"all_pilot_overlap={len(all_overlap)} (pilot_hashes={len(all_hashes)})",
            not holdout_overlap,
            "C3_ISOLATION_VIOLATION",
        )
    )

    family_counts = Counter(case["work_family"] for case in contour.cases)
    biggest = max(family_counts.values()) if family_counts else 0
    checks.append(
        make_check(
            "work_family_cap_respected",
            f"no Work family exceeds the frozen cap of {WORK_FAMILY_CAP} cases",
            f"max_family_cases={biggest} cap={WORK_FAMILY_CAP}",
            biggest <= WORK_FAMILY_CAP,
            "WORK_FAMILY_DOMINANCE",
        )
    )

    checks.append(
        make_check(
            "seed_fragment_count_frozen",
            f"the seed still holds exactly {FRAGMENT_COUNT} frozen .txt fragments",
            f"fragments={len(contour.fragments)}",
            len(contour.fragments) == FRAGMENT_COUNT,
            "SEED_ENLARGED",
        )
    )
    return checks


def build_leakage_report(
    root: Path, paths: Paths, contour: Contour, schemas: dict[str, Any]
) -> dict[str, Any]:
    checks = compute_leakage_checks(root, paths, contour)
    failed = [check for check in checks if check["status"] != "pass"]
    if failed:
        first = failed[0]
        raise GateError(
            first["diagnostic"],
            f"leakage check {first['check_id']} failed: {first['observed']}",
        )
    return {
        "schema": LEAKAGE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "check_count": len(checks),
        "leakage_count": 0,
        "lifecycle": schemas["lifecycle"],
        "non_claims": schemas["non_claims"],
    }


# --------------------------------------------------------------------------- #
# C5 ladder cross-check (read-only; the artifacts are never mutated).
# --------------------------------------------------------------------------- #


def _validated_or_unknown_metadata(label: str, year: Any, document_type: Any) -> None:
    if year != UNKNOWN_METADATA_VALUE:
        if not isinstance(year, str) or len(year) != 4 or not year.isdigit():
            raise GateError(
                "METADATA_REDERIVED",
                f"{label} year={year!r} is neither 'unknown' nor a 4-digit year",
            )
        if not MIN_CALENDAR_YEAR <= int(year) <= MAX_CALENDAR_YEAR:
            raise GateError(
                "METADATA_REDERIVED",
                f"{label} year={year!r} is outside the frozen calendar window "
                f"{MIN_CALENDAR_YEAR}..{MAX_CALENDAR_YEAR}",
            )
    if not isinstance(document_type, str) or not document_type:
        raise GateError("METADATA_REDERIVED", f"{label} document_type={document_type!r} is empty")
    if document_type != UNKNOWN_METADATA_VALUE and not all(
        part.islower() and part.replace("-", "").isalnum() for part in [document_type]
    ):
        raise GateError(
            "METADATA_REDERIVED",
            f"{label} document_type={document_type!r} is not a validated label or 'unknown'",
        )


def _collect_keys(payload: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.add(key)
            keys |= _collect_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            keys |= _collect_keys(value)
    return keys


def c5_cross_check(root: Path, paths: Paths) -> str:
    """Re-read the three frozen C5 manifests; return a one-line summary."""
    summaries: list[str] = []
    for rel in paths.c5:
        doc = read_json(root, rel, "C5 ladder manifest")
        label = Path(rel).name
        if doc.get("schema_version") != CORPUS_MANIFEST_SCHEMA:
            raise GateError(
                "C5_MEASUREMENT_CLAIM",
                f"{label} schema_version={doc.get('schema_version')!r} is not {CORPUS_MANIFEST_SCHEMA!r}",
            )
        claims = sorted(_collect_keys(doc) & C5_FORBIDDEN_KEYS)
        if claims:
            raise GateError(
                "C5_MEASUREMENT_CLAIM",
                f"{label} publishes forbidden claim keys {claims}",
            )
        strata = doc.get("provider_strata")
        if not isinstance(strata, list) or not strata:
            raise GateError("PROVIDER_STRATUM_DROPPED", f"{label} carries no provider_strata[]")
        for index, row in enumerate(strata):
            if not isinstance(row, dict):
                raise GateError(
                    "STRATUM_TABLE_DRIFT", f"{label} provider_strata[{index}] is not an object"
                )
            provider = row.get("provider")
            if not isinstance(provider, str) or not provider:
                raise GateError(
                    "PROVIDER_STRATUM_DROPPED", f"{label} provider_strata[{index}] has no provider"
                )
            quota = row.get("quota")
            cap = row.get("availability_cap")
            if not isinstance(quota, int) or isinstance(quota, bool) or quota < 0:
                raise GateError(
                    "PROVIDER_QUOTA_UNJUSTIFIED",
                    f"{label} provider {provider!r} quota={quota!r} is not a non-negative integer",
                )
            if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
                raise GateError(
                    "PROVIDER_QUOTA_UNJUSTIFIED",
                    f"{label} provider {provider!r} availability_cap={cap!r} is not a non-negative "
                    "integer",
                )
            if quota > cap:
                raise GateError(
                    "PROVIDER_QUOTA_UNJUSTIFIED",
                    f"{label} provider {provider!r} quota={quota} exceeds availability_cap={cap}",
                )
        environment = doc.get("environment")
        command = environment.get("command") if isinstance(environment, dict) else None
        draw_seed = doc.get("draw_seed")
        if (
            not isinstance(command, str)
            or not isinstance(draw_seed, int)
            or isinstance(draw_seed, bool)
        ):
            raise GateError(
                "C5_MEASUREMENT_CLAIM",
                f"{label} environment.command={command!r} draw_seed={draw_seed!r} do not "
                "establish a seed-driven draw",
            )
        if str(draw_seed) not in command:
            raise GateError(
                "C5_MEASUREMENT_CLAIM",
                f"{label} environment.command={command!r} does not carry draw_seed={draw_seed}",
            )
        entries = doc.get("entries")
        if not isinstance(entries, list):
            raise GateError("MISSING_ARTIFACT", f"{label} carries no entries[]")
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise GateError("SCHEMA_KEY_DRIFT", f"{label} entries[{index}] is not an object")
            entry_label = f"{label} entries[{index}]"
            document_path = entry.get("document_relative_path")
            if not isinstance(document_path, str):
                raise GateError("SCHEMA_KEY_DRIFT", f"{entry_label} has no document_relative_path")
            resolve_artifact(root, document_path, f"{entry_label} document_relative_path")
            _validated_or_unknown_metadata(
                entry_label, entry.get("year"), entry.get("document_type")
            )
        summaries.append(
            f"{label}:entries={len(entries)}:strata={len(strata)}:seed={draw_seed}:claims=0"
        )
    return f"{C5_LINE_PREFIX}ok manifests={len(paths.c5)} " + " ".join(summaries)


# --------------------------------------------------------------------------- #
# Serialization and structural validation.
# --------------------------------------------------------------------------- #


def serialize(doc: Any) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _require_keys(
    label: str, payload: Any, required: tuple[str, ...], closed: tuple[str, ...]
) -> None:
    if not isinstance(payload, dict):
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} is not an object")
    keys = set(payload)
    missing = [key for key in required if key not in keys]
    if missing:
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} is missing required keys {missing}")
    extra = sorted(keys - set(closed))
    if extra:
        raise GateError("SCHEMA_KEY_DRIFT", f"{label} carries keys outside the closed set {extra}")


def _schema_block(schemas: dict[str, Any], name: str) -> dict[str, Any]:
    block = schemas.get("schemas", {}).get(name)
    if not isinstance(block, dict):
        raise GateError("MISSING_SCHEMA", f"the S03 schemas declare no $.schemas.{name}")
    return block


def guard_diagnostic_table(schemas: dict[str, Any]) -> None:
    declared = schemas.get("diagnostics")
    if not isinstance(declared, list):
        raise GateError("DIAGNOSTIC_TABLE_DRIFT", "the S03 schemas declare no $.diagnostics")
    unknown = sorted(set(TOOL_DIAGNOSTICS) - set(declared))
    if unknown:
        raise GateError(
            "DIAGNOSTIC_TABLE_DRIFT", f"diagnostics outside the frozen table: {unknown}"
        )


def verify_pins_root(doc: dict[str, Any], root: Path, paths: Paths) -> None:
    pins = doc.get("pins")
    if not isinstance(pins, dict):
        raise GateError("FROZEN_SOURCE_DRIFT", "the manifest declares no pins object")
    sources = pins.get("sources")
    if not isinstance(sources, dict):
        raise GateError("FROZEN_SOURCE_DRIFT", "the manifest declares no pins.sources")
    expected = paths.pin_sources()
    missing = sorted(set(expected) - set(sources))
    if missing:
        raise GateError("FROZEN_SOURCE_DRIFT", f"the manifest pins miss {missing}")
    extra = sorted(set(sources) - set(expected))
    if extra:
        raise GateError("FROZEN_SOURCE_DRIFT", f"the manifest pins unknown sources {extra}")
    drift: list[str] = []
    for key, rel in expected.items():
        record = sources[key]
        if not isinstance(record, dict) or record.get("path") != rel:
            raise GateError("FROZEN_SOURCE_DRIFT", f"pin {key!r} does not declare path {rel!r}")
        current = sha256_file(resolve_artifact(root, rel, f"pin {key}"))
        if record.get("sha256") != current:
            drift.append(f"{key} ({rel}): pinned={record.get('sha256')} current={current}")
    if drift:
        raise GateError(
            "FROZEN_SOURCE_DRIFT",
            "pinned frozen sources changed after the freeze: " + "; ".join(drift),
        )
    rollup = pins.get("fragment_rollup")
    if not isinstance(rollup, dict):
        raise GateError("FROZEN_SOURCE_DRIFT", "the manifest declares no pins.fragment_rollup")
    current_rollup = f"sha256:{fragment_rollup(collect_fragments(root, paths))}"
    if rollup.get("sha256") != current_rollup or rollup.get("count") != FRAGMENT_COUNT:
        raise GateError(
            "FRAGMENT_PIN_DRIFT",
            f"the seed rollup moved: pinned={rollup.get('sha256')} current={current_rollup}",
        )


def validate_manifest_document(root: Path, paths: Paths, doc: Any, schemas: dict[str, Any]) -> None:
    """Recompute the contour and reject every divergence, fail-closed."""
    block = _schema_block(schemas, "eval_manifest")
    _require_keys(
        "$.eval_manifest",
        doc,
        tuple(block["required_keys"]),
        tuple(block["closed_keys"]),
    )
    if doc.get("schema") != block["schema_id"] or doc.get("schema_version") != SCHEMA_VERSION:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"eval manifest schema={doc.get('schema')!r} version={doc.get('schema_version')!r}",
        )
    if doc.get("lifecycle") != schemas["lifecycle"]:
        raise GateError("MISSING_LIFECYCLE_MARKER", "eval manifest lifecycle markers drifted")
    if doc.get("non_claims") != schemas["non_claims"]:
        raise GateError("MISSING_NON_CLAIM", "eval manifest non-claims drifted")

    expected = build_contour(root, paths)

    if doc.get("seed") != expected.seed:
        raise GateError("SCHEMA_KEY_DRIFT", f"seed={doc.get('seed')!r} != frozen {expected.seed}")
    if doc.get("holdout_families") != expected.holdout:
        raise GateError(
            "HOLDOUT_LEAKAGE",
            "the published holdout families are not the seed-derived family-granular split",
        )
    if doc.get("dev_families") != expected.dev:
        raise GateError(
            "HOLDOUT_LEAKAGE", "the published dev families are not the seed-derived split"
        )
    if doc.get("families") != expected.families:
        raise GateError(
            "SCHEMA_KEY_DRIFT", "the published family table disagrees with the frozen cases"
        )

    published_families = doc.get("families")
    published_ids = [row.get("work_family") for row in published_families]
    if sorted(published_ids) != sorted(expected.holdout + expected.dev):
        raise GateError(
            "HOLDOUT_LEAKAGE",
            "the family table does not cover every frozen Work family exactly once",
        )

    case_block = block["case_closed_keys"]
    cases = doc.get("cases")
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        raise GateError(
            "CASE_COUNT_OUT_OF_RANGE",
            f"the manifest carries {len(cases) if isinstance(cases, list) else 'no'} cases, "
            f"expected {CASE_COUNT}",
        )
    expected_by_id = {case["case_id"]: case for case in expected.cases}
    seen: set[str] = set()
    for index, case in enumerate(cases):
        label = f"$.cases[{index}]"
        _require_keys(label, case, tuple(block["case_required_keys"]), tuple(case_block))
        case_id = case.get("case_id")
        if case_id not in expected_by_id:
            raise GateError(
                "UNKNOWN_CASE_ID", f"{label} case_id={case_id!r} is not a frozen S01 case"
            )
        if case_id in seen:
            raise GateError("SCHEMA_KEY_DRIFT", f"{label} duplicates case_id={case_id!r}")
        seen.add(case_id)
        frozen = expected_by_id[case_id]
        for key in ("source_path", "source_sha256", "byte_len", "work_family", "draw_stratum"):
            if case.get(key) != frozen[key]:
                raise GateError(
                    "FROZEN_SOURCE_DRIFT",
                    f"{label}.{key}={case.get(key)!r} disagrees with the frozen S01 case "
                    f"({frozen[key]!r})",
                )
        for key in ("year", "document_type", "metadata_source"):
            if case.get(key) != frozen[key]:
                raise GateError(
                    "METADATA_REDERIVED",
                    f"{label}.{key}={case.get(key)!r} disagrees with the frozen S01 metadata "
                    f"({frozen[key]!r}); metadata is published as-is",
                )
        if case.get("provider") != frozen["provider"]:
            raise GateError(
                "PROVIDER_MISATTRIBUTED",
                f"{label}.provider={case.get('provider')!r} but source_path {frozen['source_path']!r} "
                f"attributes {frozen['provider']!r} by the declared roots",
            )
        if case.get("provider_root") != frozen["provider_root"]:
            raise GateError(
                "PROVIDER_MISATTRIBUTED",
                f"{label}.provider_root={case.get('provider_root')!r} != derived "
                f"{frozen['provider_root']!r}",
            )
        if case.get("family_scope") != frozen["family_scope"]:
            raise GateError(
                "HOLDOUT_LEAKAGE",
                f"{label}.family_scope={case.get('family_scope')!r} splits family "
                f"{frozen['work_family']!r} from its derived scope {frozen['family_scope']!r}",
            )
        if case.get("fragment_sha256") != frozen["fragment_sha256"]:
            raise GateError(
                "FRAGMENT_PIN_DRIFT",
                f"{label}.fragment_sha256 does not pin the frozen fragment",
            )
    if seen != set(expected_by_id):
        raise GateError("CASE_COUNT_OUT_OF_RANGE", "the manifest case ids are not the frozen 40")

    stratum_block = block["provider_stratum_closed_keys"]
    strata = doc.get("provider_strata")
    if not isinstance(strata, list) or not strata:
        raise GateError("PROVIDER_STRATUM_DROPPED", "the manifest carries no provider_strata[]")
    published_strata = {row.get("provider"): row for row in strata}
    for provider in PROVIDER_ORDER:
        if provider not in published_strata:
            raise GateError(
                "PROVIDER_STRATUM_DROPPED",
                f"provider stratum {provider!r} is absent; every stratum must be published",
            )
    for index, row in enumerate(strata):
        label = f"$.provider_strata[{index}]"
        _require_keys(
            label, row, tuple(block["provider_stratum_required_keys"]), tuple(stratum_block)
        )
    if len(strata) != len(PROVIDER_ORDER) or set(published_strata) != set(PROVIDER_ORDER):
        raise GateError("STRATUM_TABLE_DRIFT", "the provider strata are not the closed vocabulary")
    for expected_row in expected.strata:
        row = published_strata[expected_row["provider"]]
        quota, availability = row.get("quota"), row.get("availability")
        if (
            not isinstance(quota, int)
            or isinstance(quota, bool)
            or not isinstance(availability, int)
        ):
            raise GateError(
                "PROVIDER_QUOTA_UNJUSTIFIED",
                f"provider {row.get('provider')!r} quota={quota!r} availability={availability!r} "
                "must be integers",
            )
        if quota > availability:
            raise GateError(
                "PROVIDER_QUOTA_UNJUSTIFIED",
                f"provider {row.get('provider')!r} quota={quota} > availability={availability}",
            )
        if row.get("availability") != expected_row["availability"]:
            raise GateError(
                "STRATUM_TABLE_DRIFT",
                f"provider {row.get('provider')!r} availability={row.get('availability')!r} but the "
                f"declared roots attribute {expected_row['availability']} frozen cases",
            )
        if row.get("quota") != expected_row["quota"]:
            raise GateError(
                "STRATUM_TABLE_DRIFT",
                f"provider {row.get('provider')!r} quota={row.get('quota')!r} != {expected_row['quota']}",
            )
        if row.get("measurement_status") not in MEASUREMENT_STATUS_VALUES:
            raise GateError(
                "MEASUREMENT_STATUS_DRIFT",
                f"provider {row.get('provider')!r} measurement_status="
                f"{row.get('measurement_status')!r}",
            )
        if row.get("measurement_status") != STRATUM_MEASUREMENT_STATUS:
            raise GateError(
                "MEASUREMENT_STATUS_DRIFT",
                "the manifest declares no human reference, so every stratum is not-measured",
            )
        justification = row.get("justification")
        if not isinstance(justification, str) or not justification.strip():
            raise GateError(
                "PROVIDER_QUOTA_UNJUSTIFIED",
                f"provider {row.get('provider')!r} carries no quota justification",
            )

    fragments = doc.get("fragments")
    if not isinstance(fragments, list) or len(fragments) != FRAGMENT_COUNT:
        raise GateError(
            "SEED_ENLARGED",
            f"the manifest pins {len(fragments) if isinstance(fragments, list) else 'no'} fragments, "
            f"the frozen seed is {FRAGMENT_COUNT}",
        )
    fragment_block = block["fragment_pin_closed_keys"]
    for index, pin in enumerate(fragments):
        _require_keys(f"$.fragments[{index}]", pin, tuple(fragment_block), tuple(fragment_block))
    if fragments != expected.fragments:
        raise GateError("FRAGMENT_PIN_DRIFT", "the fragment pins disagree with the frozen seed")
    if doc.get("c3_hashes_excluded") != [
        f"sha256:{value.removeprefix('sha256:')}" for value in expected.c3_hashes
    ]:
        raise GateError(
            "C3_ISOLATION_VIOLATION",
            "c3_hashes_excluded does not pin the sealed C3 holdout hash set",
        )

    pins = doc.get("pins")
    if not isinstance(pins, dict) or pins.get("split") != build_split_declaration(expected):
        raise GateError("HOLDOUT_LEAKAGE", "the declared holdout split contract drifted")
    verify_pins_root(doc, root, paths)


def validate_leakage_document(root: Path, paths: Paths, doc: Any, schemas: dict[str, Any]) -> None:
    block = _schema_block(schemas, "leakage_report")
    _require_keys(
        "$.leakage_report",
        doc,
        tuple(block["required_keys"]),
        tuple(block["closed_keys"]),
    )
    if doc.get("schema") != block["schema_id"] or doc.get("schema_version") != SCHEMA_VERSION:
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"leakage report schema={doc.get('schema')!r} version={doc.get('schema_version')!r}",
        )
    if doc.get("lifecycle") != schemas["lifecycle"]:
        raise GateError("MISSING_LIFECYCLE_MARKER", "leakage report lifecycle markers drifted")
    if doc.get("non_claims") != schemas["non_claims"]:
        raise GateError("MISSING_NON_CLAIM", "leakage report non-claims drifted")
    contour = build_contour(root, paths)
    expected_checks = compute_leakage_checks(root, paths, contour)
    published = doc.get("checks")
    if not isinstance(published, list):
        raise GateError("SCHEMA_KEY_DRIFT", "$.leakage_report.checks is not a list")
    if doc.get("check_count") != len(published):
        raise GateError(
            "SCHEMA_KEY_DRIFT",
            f"check_count={doc.get('check_count')!r} != len(checks)={len(published)}",
        )
    failures = [check for check in published if check.get("status") != "pass"]
    if doc.get("leakage_count") != len(failures):
        raise GateError(
            "HOLDOUT_LEAKAGE",
            f"leakage_count={doc.get('leakage_count')!r} != failing checks {len(failures)}",
        )
    if failures:
        first = failures[0]
        raise GateError(
            first.get("diagnostic") or "HOLDOUT_LEAKAGE",
            f"published leakage check {first.get('check_id')!r} failed: {first.get('observed')!r}",
        )
    check_block = block["check_closed_keys"]
    if [check.get("check_id") for check in published] != [
        check["check_id"] for check in expected_checks
    ]:
        raise GateError(
            "HOLDOUT_LEAKAGE",
            "the published leakage checks are not the six structural checks of the frozen contour",
        )
    for index, check in enumerate(published):
        _require_keys(
            f"$.checks[{index}]", check, tuple(block["check_required_keys"]), tuple(check_block)
        )
        diagnostic = check.get("diagnostic")
        if diagnostic is not None and diagnostic not in LEAKAGE_DIAGNOSTICS:
            raise GateError(
                "VOCABULARY_DRIFT",
                f"$.checks[{index}].diagnostic={diagnostic!r} is outside {sorted(LEAKAGE_DIAGNOSTICS)}",
            )
        if check.get("status") not in block["status_values"]:
            raise GateError("VOCABULARY_DRIFT", f"$.checks[{index}].status={check.get('status')!r}")
        expected_check = expected_checks[index]
        for key in ("required", "observed", "status"):
            if check.get(key) != expected_check[key]:
                raise GateError(
                    expected_check["diagnostic"],
                    f"$.checks[{index}].{key}={check.get(key)!r} disagrees with the recomputed "
                    f"{expected_check[key]!r}",
                )


# --------------------------------------------------------------------------- #
# Entry points.
# --------------------------------------------------------------------------- #


def build_all(
    root: Path, paths: Paths
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Contour]:
    """Build the whole contour in memory; a refusal here writes no artifact."""
    schemas = load_schemas(root, paths)
    guard_diagnostic_table(schemas)
    contour = build_contour(root, paths)
    manifest = build_manifest(root, paths, contour, schemas)
    leakage = build_leakage_report(root, paths, contour, schemas)
    return schemas, manifest, leakage, contour


def marker_line(contour: Contour, leakage_count: int) -> str:
    printed: list[str] = []
    for row in contour.strata:
        provider = row["provider"]
        if provider in RESIDUAL_PROVIDERS and row["availability"] == 0:
            continue
        printed.append(f"{provider}:{row['availability']}")
    return (
        f"{MARKER} cases={len(contour.cases)} families={len(contour.families)} "
        f"holdout_families={len(contour.holdout)} holdout_cases={contour.holdout_cases} "
        f"provider_strata={','.join(printed)} leakage={leakage_count} "
        f"fragments={len(contour.fragments)}"
    )


def check_pipeline(root: Path, paths: Paths) -> tuple[Contour, dict[str, Any]]:
    """Read-only check: pins, byte-compare of the regeneration, structural validation."""
    schemas = load_schemas(root, paths)
    guard_diagnostic_table(schemas)
    tracked_manifest = read_bytes(root, paths.manifest, "eval manifest")
    tracked_leakage = read_bytes(root, paths.leakage, "leakage report")
    manifest_doc = load_json_bytes(tracked_manifest, paths.manifest)
    leakage_doc = load_json_bytes(tracked_leakage, paths.leakage)
    verify_pins_root(manifest_doc, root, paths)
    _, manifest_regen, leakage_regen, contour = build_all(root, paths)
    regenerated_manifest = serialize(manifest_regen)
    regenerated_leakage = serialize(leakage_regen)
    if regenerated_manifest != tracked_manifest:
        raise GateError(
            "MANIFEST_STALE",
            f"{paths.manifest}: tracked sha256={sha256_bytes(tracked_manifest)} "
            f"regenerated sha256={sha256_bytes(regenerated_manifest)}",
        )
    if regenerated_leakage != tracked_leakage:
        raise GateError(
            "MANIFEST_STALE",
            f"{paths.leakage}: tracked sha256={sha256_bytes(tracked_leakage)} "
            f"regenerated sha256={sha256_bytes(regenerated_leakage)}",
        )
    validate_manifest_document(root, paths, manifest_doc, schemas)
    validate_leakage_document(root, paths, leakage_doc, schemas)
    return contour, schemas


def run_check(root: Path, paths: Paths) -> int:
    try:
        contour, _ = check_pipeline(root, paths)
        print(c5_cross_check(root, paths))
        print(marker_line(contour, 0))
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return FAIL_EXIT
    return OK_EXIT


def run_write(root: Path, paths: Paths, *, refreeze: bool) -> int:
    try:
        schemas = load_schemas(root, paths)
        guard_diagnostic_table(schemas)
        manifest_path = resolve_artifact(root, paths.manifest, "eval manifest")
        leakage_path = resolve_artifact(root, paths.leakage, "leakage report")
        if manifest_path.is_file() and not refreeze:
            existing = load_json_bytes(manifest_path.read_bytes(), paths.manifest)
            verify_pins_root(existing, root, paths)
        contour = build_contour(root, paths)
        manifest = build_manifest(root, paths, contour, schemas)
        leakage = build_leakage_report(root, paths, contour, schemas)
        manifest_bytes = serialize(manifest)
        leakage_bytes = serialize(leakage)
        manifest_path.write_bytes(manifest_bytes)
        leakage_path.write_bytes(leakage_bytes)
        print(c5_cross_check(root, paths))
        print(
            f"{WRITTEN_LINE} manifest_sha256={sha256_bytes(manifest_bytes)} "
            f"leakage_sha256={sha256_bytes(leakage_bytes)} refreeze={str(refreeze).lower()}"
        )
        print(marker_line(contour, 0))
    except GateError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return FAIL_EXIT
    return OK_EXIT


# --------------------------------------------------------------------------- #
# Selftest: prove the named refusal paths on temporary copies.
# --------------------------------------------------------------------------- #


SELFTEST_INPUT_FILES = (
    CASES_REL,
    PROMPT_PACKETS_REL,
    C3_REL,
    C5_RELS[0],
    C5_RELS[1],
    C5_RELS[2],
    SCHEMAS_REL,
    PROTOCOL_REL,
    CODEBOOK_REL,
    METAPROMPT_REL,
    S01_SCHEMAS_REL,
    S02_PROTOCOL_REL,
    S02_SCHEMAS_REL,
    M199_PROTOCOL_REL,
    KIT_PASS1_REL,
    KIT_PASS2_REL,
    MANIFEST_REL,
    LEAKAGE_REL,
)


def _copy_tree(source: Path, target: Path, paths: Paths) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for rel in SELFTEST_INPUT_FILES:
        src = resolve_artifact(source, rel, f"selftest copy {rel}")
        if src.is_file():
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    fixture_src = source / paths.fixture_dir
    fixture_dest = target / paths.fixture_dir
    if fixture_src.is_dir():
        shutil.copytree(fixture_src, fixture_dest, dirs_exist_ok=True)


def _rewrite_json(path: Path, mutate: Any) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    mutate(doc)
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _artifact_digest(root: Path, paths: Paths) -> dict[str, str]:
    digests: dict[str, str] = {}
    for rel in (paths.manifest, paths.leakage):
        path = resolve_artifact(root, rel, "artifact")
        digests[rel] = sha256_file(path) if path.is_file() else "<absent>"
    return digests


def _expect_refusal(entry: str, root: Path, paths: Paths, diagnostic: str) -> tuple[bool, str]:
    before = _artifact_digest(root, paths)
    try:
        if entry == "build":
            build_all(root, paths)
        elif entry == "validate":
            schemas = load_schemas(root, paths)
            doc = load_json_bytes(
                resolve_artifact(root, paths.manifest, "manifest").read_bytes(), paths.manifest
            )
            validate_manifest_document(root, paths, doc, schemas)
        elif entry == "check":
            check_pipeline(root, paths)
        else:  # pragma: no cover - defensive
            return False, f"unknown entry {entry!r}"
    except GateError as exc:
        if exc.diagnostic != diagnostic:
            return False, f"{entry} refused with {exc.diagnostic}, expected {diagnostic}"
        if _artifact_digest(root, paths) != before:
            return False, f"{entry} mutated the tracked artifacts while refusing"
        return True, f"{entry} refused with {exc.diagnostic}: {exc.detail}"[:200]
    return False, f"{entry} accepted the hostile input (expected {diagnostic})"


def _probe_holdout_dev_surface_leak(root: Path, paths: Paths) -> None:
    contour = build_contour(root, paths)
    codebook = resolve_artifact(root, paths.codebook, "codebook")
    codebook.write_text(
        codebook.read_text(encoding="utf-8")
        + f"\n<!-- leaked holdout family: {contour.holdout[0]} -->\n",
        encoding="utf-8",
    )


def _probe_metaprompt_leak(root: Path, paths: Paths) -> None:
    contour = build_contour(root, paths)
    metaprompt = resolve_artifact(root, paths.metaprompt, "metaprompt")
    metaprompt.write_text(
        metaprompt.read_text(encoding="utf-8") + f"\nleak: {contour.holdout[1]}\n",
        encoding="utf-8",
    )


def _probe_work_family_dominance(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        cases = doc["cases"]
        counts = Counter(case["work_family"] for case in cases)
        dominant = max(counts, key=lambda family: (counts[family], family))
        for case in cases:
            if case["work_family"] != dominant:
                case["work_family"] = dominant
                return

    _rewrite_json(resolve_artifact(root, paths.cases, "cases"), mutate)


def _probe_metadata_rederived(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["cases"][0]["year"] = "2020"

    _rewrite_json(resolve_artifact(root, paths.cases, "cases"), mutate)


def _probe_unsafe_path(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["cases"][0]["source_path"] = "../escape.xml"

    _rewrite_json(resolve_artifact(root, paths.cases, "cases"), mutate)


def _probe_seed_enlarged(root: Path, paths: Paths) -> None:
    extra = resolve_artifact(root, paths.fixture_dir, "fixture dir") / "npa-frag-999.txt"
    extra.write_bytes(b"enlarged seed\n")


def _probe_c3_overlap(root: Path, paths: Paths) -> None:
    contour = build_contour(root, paths)
    holdout_hash = next(
        case["source_sha256"] for case in contour.cases if case["family_scope"] == "holdout"
    )

    def mutate(doc: dict[str, Any]) -> None:
        doc["entries"][0]["content_hash"] = f"sha256:{holdout_hash}"

    _rewrite_json(resolve_artifact(root, paths.c3, "c3"), mutate)


def _probe_c3_unsealed(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["sealed"] = False

    _rewrite_json(resolve_artifact(root, paths.c3, "c3"), mutate)


def _probe_c5_claim(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["double_coded_accepted"] = True

    _rewrite_json(resolve_artifact(root, paths.c5[0], "c5"), mutate)


def _probe_c5_metadata(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["entries"][0]["year"] = "not-a-year"

    _rewrite_json(resolve_artifact(root, paths.c5[0], "c5"), mutate)


def _probe_split_drift(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["dev_families"].append(doc["holdout_families"].pop())

    _rewrite_json(resolve_artifact(root, paths.manifest, "manifest"), mutate)


def _probe_case_scope_split(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        for case in doc["cases"]:
            if case["family_scope"] == "holdout":
                case["family_scope"] = "dev"
                break

    _rewrite_json(resolve_artifact(root, paths.manifest, "manifest"), mutate)


def _probe_stratum_dropped(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["provider_strata"] = [
            row for row in doc["provider_strata"] if row["provider"] != "garant"
        ]

    _rewrite_json(resolve_artifact(root, paths.manifest, "manifest"), mutate)


def _probe_quota_unjustified(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        for row in doc["provider_strata"]:
            if row["provider"] == "consultant":
                row["quota"] = row["availability"] + 1

    _rewrite_json(resolve_artifact(root, paths.manifest, "manifest"), mutate)


def _probe_provider_misattributed(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        for case in doc["cases"]:
            if case["provider"] == "consultant":
                case["provider"] = "garant"
                break

    _rewrite_json(resolve_artifact(root, paths.manifest, "manifest"), mutate)


def _probe_manifest_stale(root: Path, paths: Paths) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        doc["seed"] = doc["seed"] + 1

    _rewrite_json(resolve_artifact(root, paths.manifest, "manifest"), mutate)


def _probe_frozen_source_drift(root: Path, paths: Paths) -> None:
    codebook = resolve_artifact(root, paths.codebook, "codebook")
    codebook.write_text(
        codebook.read_text(encoding="utf-8") + "\n<!-- drift -->\n", encoding="utf-8"
    )


SELFTEST_PROBES: tuple[tuple[str, str, str, Any], ...] = (
    ("holdout_dev_surface_leak", "build", "HOLDOUT_LEAKAGE", _probe_holdout_dev_surface_leak),
    ("metaprompt_dev_surface_leak", "build", "HOLDOUT_LEAKAGE", _probe_metaprompt_leak),
    ("work_family_dominance", "build", "WORK_FAMILY_DOMINANCE", _probe_work_family_dominance),
    ("c3_isolation_overlap", "build", "C3_ISOLATION_VIOLATION", _probe_c3_overlap),
    ("c3_unsealed", "build", "C3_ISOLATION_VIOLATION", _probe_c3_unsealed),
    ("provider_misattributed_unsafe_path", "build", "UNSAFE_PATH", _probe_unsafe_path),
    ("metadata_rederived", "build", "METADATA_REDERIVED", _probe_metadata_rederived),
    ("seed_enlarged", "build", "SEED_ENLARGED", _probe_seed_enlarged),
    ("c5_measurement_claim", "build", "C5_MEASUREMENT_CLAIM", _probe_c5_claim),
    ("c5_metadata_rederived", "build", "METADATA_REDERIVED", _probe_c5_metadata),
    ("holdout_split_drift", "validate", "HOLDOUT_LEAKAGE", _probe_split_drift),
    ("case_scope_split", "validate", "HOLDOUT_LEAKAGE", _probe_case_scope_split),
    ("provider_stratum_dropped", "validate", "PROVIDER_STRATUM_DROPPED", _probe_stratum_dropped),
    (
        "provider_quota_unjustified",
        "validate",
        "PROVIDER_QUOTA_UNJUSTIFIED",
        _probe_quota_unjustified,
    ),
    ("provider_misattributed", "validate", "PROVIDER_MISATTRIBUTED", _probe_provider_misattributed),
    ("manifest_stale", "check", "MANIFEST_STALE", _probe_manifest_stale),
    ("frozen_source_drift", "check", "FROZEN_SOURCE_DRIFT", _probe_frozen_source_drift),
)


def run_selftest(root: Path, paths: Paths) -> int:
    workspace = Path(tempfile.mkdtemp(prefix="m207-s03-eval-manifest-"))
    failures: list[str] = []
    try:
        base = workspace / "base"
        _copy_tree(root, base, paths)
        if run_write(base, paths, refreeze=True) != OK_EXIT:
            print("FAIL MISSING_ARTIFACT: selftest base generation failed", file=sys.stderr)
            return FAIL_EXIT
        manifest_bytes = (base / paths.manifest).read_bytes()
        leakage_bytes = (base / paths.leakage).read_bytes()
        _, regen_manifest, regen_leakage, _ = build_all(base, paths)
        positives = (
            ("holdout_split_reproducible", serialize(regen_manifest) == manifest_bytes),
            ("leakage_report_reproducible", serialize(regen_leakage) == leakage_bytes),
        )
        print(
            "selftest_positive " + " ".join(f"{name}={str(ok).lower()}" for name, ok in positives)
        )
        for name, ok in positives:
            if not ok:
                failures.append(f"positive probe {name} failed")

        for probe_id, entry, diagnostic, mutate in SELFTEST_PROBES:
            scenario = workspace / probe_id
            _copy_tree(base, scenario, paths)
            mutate(scenario, paths)
            ok, detail = _expect_refusal(entry, scenario, paths, diagnostic)
            print(
                f"selftest_probe={probe_id} entry={entry} expected={diagnostic} "
                f"ok={str(ok).lower()} detail={detail}"
            )
            if not ok:
                failures.append(f"{probe_id}: {detail}")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    if failures:
        for failure in failures:
            print(f"FAIL SELFTEST: {failure}", file=sys.stderr)
        return FAIL_EXIT
    print(f"{SELFTEST_MARKER} probes={len(SELFTEST_PROBES)}")
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
        help="'check' verifies the tracked artifacts read-only, 'run' regenerates them, "
        "'selftest' proves the refusal paths on temporary copies",
    )
    parser.add_argument(
        "--root", default=str(ROOT), help="repository root the paths resolve against"
    )
    parser.add_argument("--manifest", default=MANIFEST_REL, help="frozen evaluation manifest")
    parser.add_argument("--leakage", default=LEAKAGE_REL, help="frozen leakage report")
    parser.add_argument("--cases", default=CASES_REL, help="frozen S01 pilot case manifest")
    parser.add_argument("--c3", default=C3_REL, help="sealed C3 holdout manifest")
    parser.add_argument("--c5-100", default=C5_RELS[0], help="frozen C5 ladder manifest (100)")
    parser.add_argument("--c5-400", default=C5_RELS[1], help="frozen C5 ladder manifest (400)")
    parser.add_argument("--c5-800", default=C5_RELS[2], help="frozen C5 ladder manifest (800)")
    parser.add_argument("--schemas", default=SCHEMAS_REL, help="frozen S03 closed schemas")
    parser.add_argument("--protocol", default=PROTOCOL_REL, help="frozen S03 evaluation protocol")
    parser.add_argument("--codebook", default=CODEBOOK_REL, help="frozen S01 codebook")
    parser.add_argument("--metaprompt", default=METAPROMPT_REL, help="frozen S01 metaprompt")
    parser.add_argument("--s01-schemas", default=S01_SCHEMAS_REL, help="frozen S01 closed schemas")
    parser.add_argument(
        "--s02-protocol", default=S02_PROTOCOL_REL, help="frozen S02 coder protocol"
    )
    parser.add_argument("--s02-schemas", default=S02_SCHEMAS_REL, help="frozen S02 closed schemas")
    parser.add_argument("--m199-protocol", default=M199_PROTOCOL_REL, help="frozen M199 protocol")
    parser.add_argument("--kit-pass1", default=KIT_PASS1_REL, help="frozen pass-1 coder kit")
    parser.add_argument("--kit-pass2", default=KIT_PASS2_REL, help="frozen pass-2 coder kit")
    parser.add_argument("--prompt-packets", default=PROMPT_PACKETS_REL, help="frozen S01 packets")
    parser.add_argument("--fixture-dir", default=FIXTURE_DIR_REL, help="frozen fragment seed dir")
    parser.add_argument(
        "--refreeze",
        action="store_true",
        help="run: accept moved frozen inputs and record fresh pins (auditable re-freeze)",
    )
    return parser


def paths_from(args: argparse.Namespace) -> Paths:
    return Paths(
        cases=args.cases,
        prompt_packets=args.prompt_packets,
        c3=args.c3,
        c5=(args.c5_100, args.c5_400, args.c5_800),
        schemas=args.schemas,
        protocol=args.protocol,
        codebook=args.codebook,
        metaprompt=args.metaprompt,
        s01_schemas=args.s01_schemas,
        s02_protocol=args.s02_protocol,
        s02_schemas=args.s02_schemas,
        m199_protocol=args.m199_protocol,
        kit_pass1=args.kit_pass1,
        kit_pass2=args.kit_pass2,
        fixture_dir=args.fixture_dir,
        manifest=args.manifest,
        leakage=args.leakage,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"FAIL MISSING_ARTIFACT: root {root} is not a directory", file=sys.stderr)
        return FAIL_EXIT
    paths = paths_from(args)
    if args.mode == "run":
        return run_write(root, paths, refreeze=args.refreeze)
    if args.mode == "selftest":
        return run_selftest(root, paths)
    if args.refreeze:
        print("FAIL SCHEMA_KEY_DRIFT: --refreeze is only meaningful for run", file=sys.stderr)
        return FAIL_EXIT
    return run_check(root, paths)


if __name__ == "__main__":
    raise SystemExit(main())
