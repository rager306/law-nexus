#!/usr/bin/env python3
"""Fail-closed battery for the M224/S04 corpus document_groups coverage artifact (T05).

Independent, read-only verification of the single artifact published by T03:

* ``prd/migration/rust-evidence/m224-s04-document-group-coverage.json`` — the
  ``m224-s04-document-group-coverage/v1`` coverage contract
  (``document_group_coverage``), derived over all 43785 rows of the S02 corpus
  manifest.

The battery never regenerates the artifact, never mutates git, never touches
dependencies and never reads a gitignored path.  It re-derives every
accounting / bank-class / structural-group / redaction invariant from the
committed bytes and fails closed on any divergence.  In addition it carries
negative self-checks that feed deliberately broken fixtures through the same
validators, proving the validators actually reject the conditions they claim to
guard (a battery that cannot fail is not a battery).

Two axes are deliberately kept apart (D667):

* the **principal** (bank) axis — ``counts`` / ``by_class`` / ``by_bank``:
  ``courts``/``fas`` are non-normative practice, ``npa``/``xml`` are normative
  law, anything else is a fail-visible ``unknown``;
* the **structural** axis — ``by_group``: which ``document_groups`` profile the
  path alone binds to.  A structural ``Unknown`` is *not* a legal
  non-normativity claim (after the M224/S05 P01 needle patch there are 6936
  structurally-unknown rows -- down from 7288 -- while the bank axis has zero
  unknowns); the battery distinguishes the two counters explicitly.

Integrity is not semantic completeness: the artifact carries
``r1000_status == "active/unclosed"`` plus bounded non-claims, and the battery
asserts them.

Redaction discipline is adapted from ``scripts/test_m224_s03_pageindex.py``
(non-ASCII reject + bounded persisted string length): any decoded corpus text
leaking into a persisted payload is a hard failure.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
COVERAGE_PATH = EVIDENCE / "m224-s04-document-group-coverage.json"
MANIFEST_PATH = EVIDENCE / "m223-s02-corpus-manifest.jsonl"
ONTOLOGY_PATH = ROOT / "prd/architecture/kb-ontology.yaml"

MANIFEST_RELPATH = "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"

COVERAGE_SCHEMA = "m224-s04-document-group-coverage/v1"
COVERAGE_KIND = "document_group_coverage"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"

EXPECTED_ENTRIES = 43785
EXPECTED_NORMATIVE = 7719
EXPECTED_NON_NORMATIVE = 36066
EXPECTED_UNKNOWN = 0

CLASS_NORMATIVE = "normative"
CLASS_NON_NORMATIVE = "non-normative"
CLASS_UNKNOWN = "unknown"
CLOSED_CLASSES = (CLASS_NORMATIVE, CLASS_NON_NORMATIVE, CLASS_UNKNOWN)

#: Closed bank -> class vocabulary (ADR-0030 D2).  Anything else is ``unknown``
#: and must surface as such, never be folded into a neighbouring class.
NORMATIVE_BANKS = ("npa", "xml")
NON_NORMATIVE_BANKS = ("courts", "fas")

BANK_KEYS = frozenset({"total", "normative", "non_normative", "unknown"})
GROUP_UNKNOWN_KEY = "Unknown"
GROUP_CONFLICT_KEY = "Conflict"

DOCUMENT_GROUPS_HEADING = "document_groups:"
#: The two textual structural groups declared `text_only: true` in the YAML
#: catalog (derived, never hardcoded as the only source of truth).
EXPECTED_NON_NORMATIVE_CLASSES = ("court_practice", "non_normative")

REQUIRED_NON_CLAIMS = frozenset(
    {
        "integrity_is_not_semantic_completeness",
        "structural_group_unknown_is_not_legal_non_normativity",
        "bank_is_export_bucket_not_catalog_legal_bank",
        "non_normative_class_is_structural_coverage_heuristic_not_legal_claim",
    }
)

_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
_DOCUMENT_GROUPS_VERSION_RE = re.compile(r"fnv1a64-[0-9a-f]{16}")

_FNV_OFFSET_BASIS = 0xCBF29CE484222325
_FNV_PRIME = 0x100000001B3
_FNV_MASK = (1 << 64) - 1

_NON_ASCII = re.compile(r"[^\x20-\x7e]")
_MAX_PERSISTED_STRING = 4096


class BatteryError(AssertionError):
    """A fail-closed invariant violation detected by this battery."""


class RedactionError(BatteryError):
    """Decoded corpus text or an oversized payload string leaked into an artifact."""


# --------------------------------------------------------------- redaction #


def assert_no_raw_text(value: object, *, where: str = "$") -> None:
    """Fail-closed redaction invariant over a persisted JSON value.

    Every persisted string must be a path, hash, count, closed token or bounded
    English diagnostic.  Decoded legal text (Cyrillic) can never pass this.
    """
    if isinstance(value, str):
        if _NON_ASCII.search(value):
            raise RedactionError(f"raw decoded text leaked into {where}")
        if len(value) > _MAX_PERSISTED_STRING:
            raise RedactionError(f"oversized string persisted at {where}")
    elif isinstance(value, dict):
        for key, item in value.items():
            assert_no_raw_text(item, where=f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_no_raw_text(item, where=f"{where}[{index}]")
    elif value is not None and not isinstance(value, (int, float, bool)):
        raise RedactionError(f"unexpected value type at {where}")


# ----------------------------------------------------- YAML section helpers #


def _strip_comment(line: str) -> str:
    """Mirror of ln-kb-ontology `strip_comment`: cut at first `#`, then rstrip."""
    marker = line.find("#")
    if marker < 0:
        return line.rstrip()
    return line[:marker].rstrip()


def _section_lines(text: str, heading: str) -> list[str] | None:
    """Raw lines of the top-level section `heading` (original indentation).

    Blank and comment-only lines are skipped; the heading line itself is
    excluded; the section ends at the next line at or below the heading indent.
    ``None`` when the heading is absent (fail-closed).
    """
    found = False
    heading_indent = 0
    out: list[str] = []
    for raw in text.split("\n"):
        if raw.endswith("\r"):
            raw = raw[:-1]
        trimmed = _strip_comment(raw)
        if not trimmed.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        if not found:
            if trimmed.strip() == heading:
                found = True
                heading_indent = indent
            continue
        if indent <= heading_indent:
            break
        out.append(raw)
    return out if found else None


def document_groups_section_hash(text: str) -> str:
    """Independent FNV-1a 64 re-derivation of the `document_groups` section.

    Mirrors ``ln_kb_ontology::catalog::document_groups_section_hash`` /
    ``governor.document_groups_section_hash`` byte for byte: each raw section
    line's UTF-8 bytes feed the FNV-1a 64 state, then a trailing ``\\n`` byte
    per line.  Absent section yields an empty string (fail-closed).
    """
    lines = _section_lines(text, DOCUMENT_GROUPS_HEADING)
    if lines is None:
        return ""
    hash_value = _FNV_OFFSET_BASIS
    for raw in lines:
        for byte in raw.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * _FNV_PRIME) & _FNV_MASK
        hash_value ^= 0x0A
        hash_value = (hash_value * _FNV_PRIME) & _FNV_MASK
    return f"fnv1a64-{hash_value:016x}"


def text_only_groups(text: str) -> list[str]:
    """Derive the `text_only: true` structural group ids from the YAML section.

    The only source of truth for ``non_normative_classes`` is the catalog: this
    scans the `document_groups` section for `- id: <name>` entries and records
    which of them declare `text_only: true` before the next group header.
    """
    groups: list[list[object]] = []
    current: str | None = None
    for raw in _section_lines(text, DOCUMENT_GROUPS_HEADING) or []:
        trimmed = raw.strip()
        if trimmed.startswith("- id:"):
            current = trimmed[len("- id:") :].strip()
            groups.append([current, False])
        elif current is not None and trimmed == "text_only: true":
            groups[-1][1] = True
    return [str(name) for name, declared in groups if declared]


# ------------------------------------------------------ bank axis helpers #


def bank_of(relative_path: str) -> str:
    """First path component (the export bank), mirroring the Rust `bank_of`."""
    return relative_path.split("/", 1)[0]


def bank_normativity(bank: str) -> str:
    """Closed bank -> class mapping; anything else is fail-visible `unknown`."""
    normalized = bank.strip().lower()
    if normalized in NON_NORMATIVE_BANKS:
        return CLASS_NON_NORMATIVE
    if normalized in NORMATIVE_BANKS:
        return CLASS_NORMATIVE
    return CLASS_UNKNOWN


def _bank_field_for_class(class_name: str) -> str:
    return class_name.replace("-", "_")


def derive_axis(records: list[dict]) -> tuple[dict, dict]:
    """Independently re-derive (by_bank, by_class) from manifest records."""
    by_bank: dict[str, dict[str, int]] = {}
    by_class = {class_name: 0 for class_name in CLOSED_CLASSES}
    for record in records:
        bank = bank_of(record["relative_path"])
        class_name = bank_normativity(bank)
        entry = by_bank.setdefault(
            bank,
            {"total": 0, "normative": 0, "non_normative": 0, "unknown": 0},
        )
        entry["total"] += 1
        entry[_bank_field_for_class(class_name)] += 1
        by_class[class_name] += 1
    return by_bank, by_class


# ------------------------------------------------------------------ loaders #


_COVERAGE_CACHE: dict | None = None
_MANIFEST_CACHE: tuple[dict, list[dict]] | None = None
_ONTOLOGY_CACHE: str | None = None


def load_coverage() -> dict:
    """Parse the coverage artifact from committed ASCII bytes (cached)."""
    global _COVERAGE_CACHE
    if _COVERAGE_CACHE is None:
        _COVERAGE_CACHE = json.loads(COVERAGE_PATH.read_text(encoding="ascii"))
    return _COVERAGE_CACHE


def load_manifest() -> tuple[dict, list[dict]]:
    """Return (header, records) from the S02 corpus manifest (cached)."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        lines = MANIFEST_PATH.read_text(encoding="ascii").splitlines()
        if not lines:
            raise BatteryError("corpus manifest is empty")
        header = json.loads(lines[0])
        records = [json.loads(line) for line in lines[1:]]
        _MANIFEST_CACHE = (header, records)
    return _MANIFEST_CACHE


def load_ontology_text() -> str:
    """Read the tracked YAML ontology catalog (cached)."""
    global _ONTOLOGY_CACHE
    if _ONTOLOGY_CACHE is None:
        _ONTOLOGY_CACHE = ONTOLOGY_PATH.read_text(encoding="utf-8")
    return _ONTOLOGY_CACHE


# --------------------------------------------------------------- validators #


def _require_int(value: object, where: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise BatteryError(f"{where} is not an int")


def validate_identity(doc: object) -> None:
    """Closed schema/kind plus the exact corpus class totals."""
    if not isinstance(doc, dict):
        raise BatteryError("coverage document is not an object")
    if doc.get("schema") != COVERAGE_SCHEMA:
        raise BatteryError(f"coverage schema mismatch: {doc.get('schema')!r}")
    if doc.get("kind") != COVERAGE_KIND:
        raise BatteryError(f"coverage kind mismatch: {doc.get('kind')!r}")
    counts = doc.get("counts")
    if not isinstance(counts, dict):
        raise BatteryError("coverage counts missing")
    for key in ("entries", "normative", "non_normative", "unknown"):
        _require_int(counts.get(key), f"coverage.counts.{key}")
    if counts["entries"] != EXPECTED_ENTRIES:
        raise BatteryError(f"entries != {EXPECTED_ENTRIES}: {counts['entries']}")
    if counts["normative"] != EXPECTED_NORMATIVE:
        raise BatteryError(f"normative != {EXPECTED_NORMATIVE}: {counts['normative']}")
    if counts["non_normative"] != EXPECTED_NON_NORMATIVE:
        raise BatteryError(f"non_normative != {EXPECTED_NON_NORMATIVE}: {counts['non_normative']}")
    if counts["unknown"] != EXPECTED_UNKNOWN:
        raise BatteryError(f"unknown != {EXPECTED_UNKNOWN}: {counts['unknown']}")
    if counts["normative"] + counts["non_normative"] + counts["unknown"] != counts["entries"]:
        raise BatteryError("normative + non_normative + unknown != entries")


def validate_class_axis(doc: dict) -> None:
    """`by_class` is a closed-vocabulary, complete class tally."""
    counts = doc.get("counts")
    if not isinstance(counts, dict):
        raise BatteryError("coverage counts missing")
    by_class = doc.get("by_class")
    if not isinstance(by_class, dict) or not by_class:
        raise BatteryError("coverage by_class missing or empty")
    for key, value in by_class.items():
        if key not in CLOSED_CLASSES:
            raise BatteryError(f"by_class carries a non-vocabulary key: {key!r}")
        _require_int(value, f"by_class.{key}")
        if value < 0:
            raise BatteryError(f"by_class.{key} is negative")
    if sum(by_class.values()) != counts["entries"]:
        raise BatteryError("sum(by_class) != entries")
    for class_name in CLOSED_CLASSES:
        field = _bank_field_for_class(class_name)
        if by_class.get(class_name, 0) != counts[field]:
            raise BatteryError(f"by_class[{class_name!r}] != counts.{field}")


def validate_axis(
    doc: dict,
    derived_by_bank: dict,
    derived_by_class: dict,
    entries: int,
) -> None:
    """Per-bank split identities plus the independent manifest re-derivation.

    Also enforces that a fail-visible `unknown` bank stays a separate class: a
    bank row whose class split was folded into a neighbouring class (e.g.
    `unknown` counted as `non_normative`) cannot equal the independently
    derived split and fails closed.
    """
    by_bank = doc.get("by_bank")
    if not isinstance(by_bank, dict) or not by_bank:
        raise BatteryError("coverage by_bank missing or empty")
    for bank, entry in by_bank.items():
        if not isinstance(bank, str) or not bank:
            raise BatteryError("by_bank carries an empty bank label")
        if "/" in bank or "\\" in bank:
            raise BatteryError(f"path-like bank label in by_bank: {bank!r}")
        if not isinstance(entry, dict) or frozenset(entry) != BANK_KEYS:
            raise BatteryError(f"by_bank.{bank} does not carry the closed bank keys")
        for field, value in entry.items():
            _require_int(value, f"by_bank.{bank}.{field}")
            if value < 0:
                raise BatteryError(f"by_bank.{bank}.{field} is negative")
        if entry["total"] <= 0:
            raise BatteryError(f"by_bank.{bank}.total is not positive")
        parts = entry["normative"] + entry["non_normative"] + entry["unknown"]
        if entry["total"] != parts:
            raise BatteryError(f"by_bank.{bank}.total != class-field sum")
    totals = sum(entry["total"] for entry in by_bank.values())
    if totals != entries:
        raise BatteryError(f"sum(by_bank totals)={totals} != entries={entries}")

    unknown_total = sum(entry["unknown"] for entry in by_bank.values())
    if doc["by_class"].get(CLASS_UNKNOWN, 0) != unknown_total:
        raise BatteryError("by_class unknown != sum of by_bank unknown")
    if doc["counts"]["unknown"] != unknown_total:
        raise BatteryError("counts.unknown != sum of by_bank unknown")

    if by_bank != derived_by_bank:
        raise BatteryError("by_bank disagrees with the independent manifest derivation")
    normalized = {class_name: doc["by_class"].get(class_name, 0) for class_name in CLOSED_CLASSES}
    if normalized != derived_by_class:
        raise BatteryError("by_class disagrees with the independent manifest derivation")


def validate_ctv_and_bank_class_identities(doc: dict) -> None:
    """`ctv_blocked` and the class identities tie back to the bank vocabulary."""
    counts = doc.get("counts")
    by_bank = doc.get("by_bank")
    if not isinstance(counts, dict) or not isinstance(by_bank, dict):
        raise BatteryError("coverage counts/by_bank missing")
    ctv_blocked = doc.get("ctv_blocked")
    _require_int(ctv_blocked, "coverage.ctv_blocked")
    if ctv_blocked != counts["non_normative"]:
        raise BatteryError("ctv_blocked != counts.non_normative")
    if ctv_blocked != doc["by_class"].get(CLASS_NON_NORMATIVE, 0):
        raise BatteryError("ctv_blocked != by_class non-normative")
    for bank in NON_NORMATIVE_BANKS:
        if by_bank.get(bank, {}).get("normative", 0) != 0:
            raise BatteryError(f"non-normative bank {bank} carries normative entries")
        if by_bank.get(bank, {}).get("unknown", 0) != 0:
            raise BatteryError(f"non-normative bank {bank} carries unknown entries")
    for bank in NORMATIVE_BANKS:
        if by_bank.get(bank, {}).get("non_normative", 0) != 0:
            raise BatteryError(f"normative bank {bank} carries non-normative entries")
        if by_bank.get(bank, {}).get("unknown", 0) != 0:
            raise BatteryError(f"normative bank {bank} carries unknown entries")
    normative = sum(by_bank.get(bank, {}).get("total", 0) for bank in NORMATIVE_BANKS)
    non_normative = sum(by_bank.get(bank, {}).get("total", 0) for bank in NON_NORMATIVE_BANKS)
    if counts["normative"] != normative:
        raise BatteryError("counts.normative != npa + xml totals")
    if counts["non_normative"] != non_normative:
        raise BatteryError("counts.non_normative != courts + fas totals")


def validate_group_axis(doc: dict, entries: int) -> None:
    """Structural axis is separate from the bank axis (D667).

    The structural `Unknown` key must be explicit and non-zero while the bank
    axis reports zero unknown.  The two counters are different axes and must
    never be conflated.
    """
    by_group = doc.get("by_group")
    if not isinstance(by_group, dict) or not by_group:
        raise BatteryError("coverage by_group missing or empty")
    for key, value in by_group.items():
        if not isinstance(key, str) or not key:
            raise BatteryError("by_group carries an empty key")
        _require_int(value, f"by_group.{key}")
        if value <= 0:
            raise BatteryError(f"by_group.{key} is not positive")
    if sum(by_group.values()) != entries:
        raise BatteryError("sum(by_group) != entries")
    structural_unknown = by_group.get(GROUP_UNKNOWN_KEY, 0)
    bank_unknown = doc["by_class"].get(CLASS_UNKNOWN, 0)
    if structural_unknown <= 0:
        raise BatteryError("structural by_group.Unknown must be explicit and non-zero")
    if bank_unknown != 0:
        raise BatteryError("bank by_class.unknown must be zero on this corpus")
    if structural_unknown == bank_unknown:
        raise BatteryError("structural Unknown and bank unknown are different axes (D667)")


def validate_non_normative_classes(doc: dict, ontology_text: str) -> None:
    """`non_normative_classes` is derived from the YAML catalog, not hardcoded."""
    value = doc.get("non_normative_classes")
    if not isinstance(value, list) or not value:
        raise BatteryError("non_normative_classes missing or empty")
    for item in value:
        if not isinstance(item, str) or not item:
            raise BatteryError("non_normative_classes carries an empty entry")
    if value != sorted(value):
        raise BatteryError("non_normative_classes is not deterministically sorted")
    derived = text_only_groups(ontology_text)
    if value != derived:
        raise BatteryError(
            f"non_normative_classes != YAML text_only groups: {value!r} != {derived!r}"
        )
    if set(derived) != set(EXPECTED_NON_NORMATIVE_CLASSES):
        raise BatteryError(f"unexpected text_only group set: {sorted(derived)!r}")


def validate_lifecycle_and_non_claims(doc: dict) -> None:
    """R1000 stays active/unclosed and every required non-claim is present."""
    if doc.get("r1000_status") != "active/unclosed":
        raise BatteryError(f"unexpected r1000_status: {doc.get('r1000_status')!r}")
    non_claims = doc.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims:
        raise BatteryError("non_claims must be a non-empty list")
    if not all(isinstance(claim, str) and claim for claim in non_claims):
        raise BatteryError("non_claims must contain non-empty strings")
    missing = REQUIRED_NON_CLAIMS - set(non_claims)
    if missing:
        raise BatteryError(f"coverage is missing required non_claims: {sorted(missing)}")


def validate_manifest_pins(doc: dict, header: dict) -> None:
    """Manifest path/sha256/inventory_digest pins match the tracked bytes."""
    manifest = doc.get("manifest")
    if not isinstance(manifest, dict):
        raise BatteryError("coverage manifest pin missing")
    if manifest.get("path") != MANIFEST_RELPATH:
        raise BatteryError(f"manifest.path != {MANIFEST_RELPATH}: {manifest.get('path')!r}")
    if not _SHA256_RE.fullmatch(str(manifest.get("sha256", ""))):
        raise BatteryError("manifest.sha256 is not a sha256 token")
    if not _SHA256_RE.fullmatch(str(manifest.get("inventory_digest", ""))):
        raise BatteryError("manifest.inventory_digest is not a sha256 token")
    digest = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    if manifest["sha256"] != f"sha256:{digest}":
        raise BatteryError("manifest.sha256 does not match the tracked manifest bytes")
    if not isinstance(header, dict) or manifest["inventory_digest"] != header.get(
        "inventory_digest"
    ):
        raise BatteryError("manifest.inventory_digest != manifest header inventory_digest")


def validate_catalog_version(doc: dict, ontology_text: str) -> None:
    """The catalog version is a fnv1a64 pin of the live YAML section."""
    catalog = doc.get("catalog")
    if not isinstance(catalog, dict):
        raise BatteryError("coverage catalog pin missing")
    version = catalog.get("document_groups_version")
    if not isinstance(version, str) or not _DOCUMENT_GROUPS_VERSION_RE.fullmatch(version):
        raise BatteryError(f"catalog.document_groups_version is not fnv1a64-<16 hex>: {version!r}")
    if version != document_groups_section_hash(ontology_text):
        raise BatteryError("catalog.document_groups_version disagrees with the YAML re-derivation")


def validate_redaction(doc: dict) -> None:
    """Every persisted string is a path/hash/count/closed token (ASCII)."""
    assert_no_raw_text(doc)


def validate_document(
    doc: object,
    *,
    header: dict,
    records: list[dict],
    ontology_text: str,
) -> None:
    """Full fail-closed validation of a coverage document against its sources."""
    validate_identity(doc)
    assert isinstance(doc, dict)
    validate_class_axis(doc)
    derived_by_bank, derived_by_class = derive_axis(records)
    validate_axis(doc, derived_by_bank, derived_by_class, len(records))
    validate_ctv_and_bank_class_identities(doc)
    validate_group_axis(doc, len(records))
    validate_non_normative_classes(doc, ontology_text)
    validate_lifecycle_and_non_claims(doc)
    validate_manifest_pins(doc, header)
    validate_catalog_version(doc, ontology_text)
    validate_redaction(doc)


def _real_context() -> dict:
    header, records = load_manifest()
    return {"header": header, "records": records, "ontology_text": load_ontology_text()}


# -------------------------------------------------------------------- tests #


def test_artifacts_exist() -> None:
    assert COVERAGE_PATH.is_file(), COVERAGE_PATH
    assert MANIFEST_PATH.is_file(), MANIFEST_PATH
    assert ONTOLOGY_PATH.is_file(), ONTOLOGY_PATH


def test_schema_and_accounting() -> None:
    doc = load_coverage()
    assert doc["schema"] == COVERAGE_SCHEMA
    assert doc["kind"] == COVERAGE_KIND
    validate_identity(doc)
    validate_class_axis(doc)


def test_bank_tallies_and_ctv() -> None:
    doc = load_coverage()
    validate_ctv_and_bank_class_identities(doc)
    assert doc["by_bank"]["courts"]["total"] == 5667
    assert doc["by_bank"]["fas"]["total"] == 30399
    assert doc["by_bank"]["npa"]["total"] == 916
    assert doc["by_bank"]["xml"]["total"] == 6803
    assert doc["ctv_blocked"] == EXPECTED_NON_NORMATIVE


def test_manifest_derived_axis_matches_artifact() -> None:
    header, records = load_manifest()
    doc = load_coverage()
    assert len(records) == EXPECTED_ENTRIES
    derived_by_bank, derived_by_class = derive_axis(records)
    validate_axis(doc, derived_by_bank, derived_by_class, len(records))
    assert derived_by_class[CLASS_NON_NORMATIVE] == EXPECTED_NON_NORMATIVE
    assert derived_by_class[CLASS_NORMATIVE] == EXPECTED_NORMATIVE
    assert derived_by_class[CLASS_UNKNOWN] == EXPECTED_UNKNOWN
    assert header["schema"] == MANIFEST_SCHEMA


def test_manifest_header_subdir_pins_match_by_bank() -> None:
    header, _ = load_manifest()
    doc = load_coverage()
    subdirs = header.get("subdirs")
    assert isinstance(subdirs, dict) and subdirs
    for bank, entry in subdirs.items():
        assert entry["entries"] == doc["by_bank"][bank]["total"], bank
    assert sum(entry["entries"] for entry in subdirs.values()) == EXPECTED_ENTRIES


def test_manifest_pins() -> None:
    header, _ = load_manifest()
    validate_manifest_pins(load_coverage(), header)


def test_manifest_sha256_matches_tracked_bytes() -> None:
    doc = load_coverage()
    digest = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    assert doc["manifest"]["sha256"] == f"sha256:{digest}"
    assert doc["manifest"]["path"] == MANIFEST_RELPATH


def test_document_groups_version_matches_yaml_fnv1a64() -> None:
    doc = load_coverage()
    validate_catalog_version(doc, load_ontology_text())
    assert doc["catalog"]["document_groups_version"] != ""


def test_non_normative_classes_derived_from_yaml() -> None:
    doc = load_coverage()
    validate_non_normative_classes(doc, load_ontology_text())
    derived = text_only_groups(load_ontology_text())
    assert derived == ["court_practice", "non_normative"]
    assert doc["non_normative_classes"] == derived


def test_structural_group_axis_is_distinct_from_bank_axis() -> None:
    doc = load_coverage()
    validate_group_axis(doc, EXPECTED_ENTRIES)
    assert doc["by_group"][GROUP_UNKNOWN_KEY] > 0
    assert doc["by_class"].get(CLASS_UNKNOWN, 0) == 0
    assert doc["by_group"][GROUP_UNKNOWN_KEY] != doc["by_class"].get(CLASS_UNKNOWN, 0)


def test_lifecycle_and_non_claims() -> None:
    doc = load_coverage()
    validate_lifecycle_and_non_claims(doc)
    assert REQUIRED_NON_CLAIMS <= set(doc["non_claims"])


def test_artifacts_are_ascii_bytes() -> None:
    raw = COVERAGE_PATH.read_bytes()
    assert raw, "coverage artifact is empty"
    assert max(raw) < 0x80, "coverage artifact carries non-ASCII bytes"
    raw.decode("ascii")
    assert max(MANIFEST_PATH.read_bytes()) < 0x80


def test_redaction_no_raw_text_in_coverage_payload() -> None:
    validate_redaction(load_coverage())


def test_full_document_validation() -> None:
    validate_document(load_coverage(), **_real_context())


# ------------------------------------------- negative self-checks (battery) #


def test_battery_rejects_wrong_schema() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["schema"] = "m224-s04-document-group-coverage/v2"
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_counts_entry_drift() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["counts"]["entries"] += 1
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_broken_class_sum() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["by_class"][CLASS_NON_NORMATIVE] += 1  # sum(by_class) != entries
    with pytest.raises(BatteryError):
        validate_class_axis(bad)


def test_battery_rejects_non_vocabulary_class_key() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["by_class"]["practice"] = 1
    with pytest.raises(BatteryError):
        validate_class_axis(bad)


def test_battery_rejects_bank_total_sum_mismatch() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["by_bank"]["courts"]["total"] += 1
    with pytest.raises(BatteryError):
        validate_axis(bad, *derive_axis(load_manifest()[1]), EXPECTED_ENTRIES)


def test_battery_rejects_per_bank_split_drift() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["by_bank"]["npa"]["non_normative"] = 1  # total != class-field sum
    with pytest.raises(BatteryError):
        validate_axis(bad, *derive_axis(load_manifest()[1]), EXPECTED_ENTRIES)


def test_battery_rejects_class_substitution() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["by_bank"]["courts"]["non_normative"] -= 1
    bad["by_bank"]["courts"]["unknown"] += 1  # re-derivation now disagrees
    with pytest.raises(BatteryError):
        validate_axis(bad, *derive_axis(load_manifest()[1]), EXPECTED_ENTRIES)


def test_battery_rejects_folded_unknown_bank() -> None:
    records = [
        {"relative_path": "courts/acn/a.xml"},
        {"relative_path": "npa/decree_b.xml"},
        {"relative_path": "mystery/c.xml"},
    ]
    derived_by_bank, derived_by_class = derive_axis(records)
    correct = {
        "counts": {"entries": 3, "normative": 1, "non_normative": 1, "unknown": 1},
        "by_class": {"non-normative": 1, "normative": 1, "unknown": 1},
        "by_bank": {
            "courts": {"total": 1, "normative": 0, "non_normative": 1, "unknown": 0},
            "npa": {"total": 1, "normative": 1, "non_normative": 0, "unknown": 0},
            "mystery": {"total": 1, "normative": 0, "non_normative": 0, "unknown": 1},
        },
    }
    validate_axis(correct, derived_by_bank, derived_by_class, 3)

    folded = copy.deepcopy(correct)
    folded["by_bank"]["mystery"] = {
        "total": 1,
        "normative": 0,
        "non_normative": 1,  # unknown folded into non_normative
        "unknown": 0,
    }
    folded["by_class"] = {"non-normative": 2, "normative": 1, "unknown": 0}
    folded["counts"] = {"entries": 3, "normative": 1, "non_normative": 2, "unknown": 0}
    with pytest.raises(BatteryError):
        validate_axis(folded, derived_by_bank, derived_by_class, 3)


def test_battery_rejects_axis_conflation() -> None:
    bad = copy.deepcopy(load_coverage())
    # Fold the structural Unknown into the bank class axis: axes must not mix.
    bad["by_class"][CLASS_UNKNOWN] = bad["by_group"][GROUP_UNKNOWN_KEY]
    with pytest.raises(BatteryError):
        validate_class_axis(bad)


def test_battery_rejects_structural_unknown_removed() -> None:
    bad = copy.deepcopy(load_coverage())
    removed = bad["by_group"].pop(GROUP_UNKNOWN_KEY)
    bad["by_group"]["court_practice"] += removed
    with pytest.raises(BatteryError):
        validate_group_axis(bad, EXPECTED_ENTRIES)


def test_battery_rejects_by_group_sum_drift() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["by_group"]["court_practice"] += 1
    with pytest.raises(BatteryError):
        validate_group_axis(bad, EXPECTED_ENTRIES)


def test_battery_rejects_ctv_blocked_drift() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["ctv_blocked"] += 1
    with pytest.raises(BatteryError):
        validate_ctv_and_bank_class_identities(bad)


def test_battery_rejects_hardcoded_non_normative_classes() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["non_normative_classes"] = ["court_practice"]  # dropped non_normative
    with pytest.raises(BatteryError):
        validate_non_normative_classes(bad, load_ontology_text())


def test_battery_rejects_unsorted_non_normative_classes() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["non_normative_classes"] = ["non_normative", "court_practice"]
    with pytest.raises(BatteryError):
        validate_non_normative_classes(bad, load_ontology_text())


def test_battery_rejects_removed_required_non_claim() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["non_claims"] = [
        claim
        for claim in bad["non_claims"]
        if claim != "bank_is_export_bucket_not_catalog_legal_bank"
    ]
    with pytest.raises(BatteryError):
        validate_lifecycle_and_non_claims(bad)


def test_battery_rejects_closed_r1000_status() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["r1000_status"] = "closed"
    with pytest.raises(BatteryError):
        validate_lifecycle_and_non_claims(bad)


def test_battery_rejects_manifest_sha_drift() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["manifest"]["sha256"] = "sha256:" + "0" * 64
    with pytest.raises(BatteryError):
        validate_manifest_pins(bad, load_manifest()[0])


def test_battery_rejects_wrong_document_groups_version() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["catalog"]["document_groups_version"] = "fnv1a64-0000000000000000"
    with pytest.raises(BatteryError):
        validate_catalog_version(bad, load_ontology_text())


def test_battery_rejects_bad_document_groups_version_token() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["catalog"]["document_groups_version"] = "sha256:" + "0" * 64
    with pytest.raises(BatteryError):
        validate_catalog_version(bad, load_ontology_text())


def test_battery_rejects_bad_manifest_inventory_digest() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["manifest"]["inventory_digest"] = "not-a-sha256"
    with pytest.raises(BatteryError):
        validate_manifest_pins(bad, load_manifest()[0])


def test_battery_rejects_decoded_text_in_payload() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})
    bad = copy.deepcopy(load_coverage())
    bad["r1000_status"] = "\u0444\u0430\u0441"
    with pytest.raises(RedactionError):
        validate_redaction(bad)


def test_battery_rejects_oversized_string() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "a" * (_MAX_PERSISTED_STRING + 1)})


def test_battery_derivation_is_non_vacuous() -> None:
    derived_by_bank, derived_by_class = derive_axis(load_manifest()[1])
    assert derived_by_bank != {}
    assert sum(derived_by_class.values()) == EXPECTED_ENTRIES
    bad = copy.deepcopy(load_coverage())
    bad["by_bank"]["courts"]["total"] -= 1
    with pytest.raises(BatteryError):
        validate_axis(bad, derived_by_bank, derived_by_class, EXPECTED_ENTRIES)
