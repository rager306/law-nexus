#!/usr/bin/env python3
"""Fail-closed battery for the M224/S05 hierarchy-lift census artifacts (T06).

Independent, read-only verification of the two artifacts published by T04/T05:

* ``prd/migration/rust-evidence/m224-s05-hierarchy-lift-census.json`` — the
  ``m224-s05-hierarchy-lift-census/v1`` counts-only census of the bounded
  stratified corpus lift (one producer ``cleaned-project export`` pass per
  sampled document, then the JSONL-only ``hierarchy-lift-census`` consumer);
* ``prd/migration/rust-evidence/m224-s05-lift-census-patches.json`` — the
  ``m224-s05-lift-census-patches/v1`` census-driven patch-loop record that
  classifies every unmapped marker token as ``patched`` or ``residual``.

The battery never regenerates an artifact, never runs the producer or consumer,
never mutates git, never touches dependencies and never reads a gitignored path
(``target/`` is deliberately out of scope: the binary pins are checked for shape
only, while the two *tracked* pins — the S02 manifest and the ontology — are
re-hashed from their committed bytes).  It re-derives every accounting /
non-normative / XML-reparse / redaction / pin / patch-coverage invariant from the
committed bytes and fails closed on any divergence.  Negative self-checks feed
deliberately broken fixtures through the *same* validators, proving the
validators actually reject the conditions they claim to guard (a battery that
cannot fail is not a battery).

Two axes are deliberately kept apart:

* the **accounting** axis — ``lift`` / ``by_group`` / ``by_catalog_token`` /
  ``by_role`` / ``unmapped_tokens``: ``markers == bound + unknown +
  non_normative``; the per-role tally closes over ``bound``; the unmapped-token
  tally closes over ``unknown`` and is non-empty whenever ``unknown > 0``
  (an unmapped marker is fail-closed, never a guessed default);
* the **non-normative barrier** axis — derived from the ``text_only: true``
  groups in the tracked YAML catalog and the ``courts/`` / ``fas/`` path
  prefixes of the deterministic S02-manifest sample.  ``non_normative_documents``
  and ``non_normative_prefix_documents`` are re-derived independently and the
  ``by_group`` markers grouped under the text-only groups must equal
  ``lift.non_normative`` (dropping the barrier would move those markers into the
  normative ``by_role``/``bound`` side and fail closed here).

The XML-reparse guard is two-fold: the artifact must carry
``xml_reparse_in_lift == false`` **and** the lift-path Rust sources
(``wire_blocks.rs`` / ``hierarchy_lift.rs`` / ``hierarchy_lift_census.rs`` and
the ``hierarchy-lift-census`` bin) must not contain any XML-decode surface
(``from_xml`` / ``ConsultantWordMlBlockDecoder`` / ``decode_blocks`` /
``read_odt_content_xml``).

Integrity is not semantic completeness: both artifacts carry
``r1000_status == "active/unclosed"`` plus bounded non-claims, and the battery
asserts them.  Redaction discipline is adapted from
``scripts/test_m224_s04_document_group_coverage.py`` (non-ASCII reject + bounded
persisted string length): decoded corpus text leaking into a persisted payload
is a hard failure.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
CENSUS_PATH = EVIDENCE / "m224-s05-hierarchy-lift-census.json"
PATCHES_PATH = EVIDENCE / "m224-s05-lift-census-patches.json"
MANIFEST_PATH = EVIDENCE / "m223-s02-corpus-manifest.jsonl"
ONTOLOGY_PATH = ROOT / "prd/architecture/kb-ontology.yaml"

MANIFEST_RELPATH = "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
ONTOLOGY_RELPATH = "prd/architecture/kb-ontology.yaml"
CORPUS_ROOT = "consru_export/consru_export/exports"

#: Lift-path Rust sources that must carry no XML-decode surface.  The bin is
#: included: the whole consumer path is JSONL-only by contract (ADR-0017/S03).
LIFT_SOURCES = (
    "crates/ln-decode/src/wire_blocks.rs",
    "crates/ln-decode/src/hierarchy_lift.rs",
    "crates/ln-consultant-parser/src/hierarchy_lift_census.rs",
    "crates/ln-consultant-parser/src/bin/hierarchy-lift-census.rs",
)

#: Any occurrence of these in a lift-path source is an XML re-parse surface.
XML_REPARSE_TOKENS = re.compile(
    r"from_xml|ConsultantWordMlBlockDecoder|decode_blocks|read_odt_content_xml"
)

CENSUS_SCHEMA = "m224-s05-hierarchy-lift-census/v1"
CENSUS_KIND = "hierarchy_lift_census"
CENSUS_VERSION = 1
DOC_SCHEMA = "m224-s05-hierarchy-lift-doc/v1"
PATCHES_SCHEMA = "m224-s05-lift-census-patches/v1"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
R1000_STATUS = "active/unclosed"

EXPECTED_MANIFEST_ENTRIES = 43785
#: Deterministic bounded sample (driver pins): seed + per-decile + tail.
SAMPLE_SEED = 22405
SAMPLE_PER_DECILE = 2
SAMPLE_TAIL_N = 8
SAMPLE_SIZE = 28
EXPECTED_NON_NORMATIVE_PREFIX_DOCUMENTS = 17

#: Closed catalog-token vocabulary of the authoritative extractor
#: (``ln_decode::hierarchy::catalog_token``); the census fails closed on any
#: token outside this set instead of inventing a bucket.
CATALOG_TOKENS = frozenset({"razdel", "glava", "paragraph", "statya", "chast", "punkt", "podpunkt"})
#: Closed ladder-role vocabulary declared by the ``document_groups`` ladders.
ROLES = frozenset({"container", "unit", "subunit", "subunit-text"})
#: Closed ``document_groups`` id vocabulary (embedded catalog, 7 groups).
GROUPS = frozenset(
    {
        "federal_law@v1",
        "code",
        "government_resolution",
        "presidential_decree",
        "departmental_order",
        "court_practice",
        "non_normative",
    }
)
GROUP_KEYS = GROUPS | {"Unknown"}
#: Corpus path prefixes the text-only barrier classifies as non-normative.
NON_NORMATIVE_PREFIXES = ("courts/", "fas/")

LIFT_KEYS = frozenset({"markers", "bound", "unknown", "non_normative"})
PATCH_DISPOSITIONS = frozenset({"patched", "residual"})

REQUIRED_NON_CLAIMS = frozenset(
    {
        "not_r1000_closure",
        "integrity_is_not_semantic_completeness",
        "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml",
        "no_xml_reparse_in_lift",
        "an_unmapped_marker_is_fail_closed_never_a_guessed_default",
        "non_normative_is_a_structural_barrier_not_a_legal_claim",
        "census_counts_only_no_decoded_text",
    }
)
#: The two textual structural groups declared ``text_only: true`` in the YAML
#: catalog (derived, never the only source of truth).
EXPECTED_NON_NORMATIVE_CLASSES = ("court_practice", "non_normative")

_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
_NON_ASCII = re.compile(r"[^\x20-\x7e]")
_MAX_PERSISTED_STRING = 4096

DOCUMENT_GROUPS_HEADING = "document_groups:"


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
            if not isinstance(key, str):
                raise RedactionError(f"non-string key at {where}")
            if _NON_ASCII.search(key):
                raise RedactionError(f"non-ASCII key at {where}")
            assert_no_raw_text(item, where=f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_no_raw_text(item, where=f"{where}[{index}]")
    elif value is not None and not isinstance(value, (int, float, bool)):
        raise RedactionError(f"unexpected value type at {where}")


# ----------------------------------------------------- XML-reparse guard #


def assert_no_xml_reparse(sources: dict[str, str]) -> None:
    """Fail closed if a lift-path source carries any XML-decode surface."""
    if not sources:
        raise BatteryError("no lift-path sources supplied to the XML-reparse guard")
    for path, text in sources.items():
        if not isinstance(text, str) or not text.strip():
            raise BatteryError(f"lift-path source {path} is missing or empty")
        match = XML_REPARSE_TOKENS.search(text)
        if match is not None:
            raise BatteryError(
                f"XML re-parse surface {match.group(0)!r} found in lift-path source {path}"
            )


# -------------------------------------------------- YAML catalog helpers #


def _strip_comment(line: str) -> str:
    """Mirror of ln-kb-ontology ``strip_comment``: cut at first ``#`` then rstrip."""
    marker = line.find("#")
    if marker < 0:
        return line.rstrip()
    return line[:marker].rstrip()


def _section_lines(text: str, heading: str) -> list[str] | None:
    """Raw lines of the top-level YAML section ``heading`` (original indent).

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


def text_only_groups(text: str) -> list[str]:
    """Derive the ``text_only: true`` structural group ids from the YAML section."""
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


# ------------------------------------------------------------------ loaders #

_CENSUS_CACHE: dict | None = None
_PATCHES_CACHE: dict | None = None
_MANIFEST_CACHE: tuple[dict, list[dict]] | None = None
_ONTOLOGY_CACHE: str | None = None
_SOURCE_CACHE: dict[str, str] | None = None


def load_census() -> dict:
    """Parse the census artifact from committed ASCII bytes (cached)."""
    global _CENSUS_CACHE
    if _CENSUS_CACHE is None:
        _CENSUS_CACHE = json.loads(CENSUS_PATH.read_text(encoding="ascii"))
    return _CENSUS_CACHE


def load_patches() -> dict:
    """Parse the patch-loop artifact from committed ASCII bytes (cached)."""
    global _PATCHES_CACHE
    if _PATCHES_CACHE is None:
        _PATCHES_CACHE = json.loads(PATCHES_PATH.read_text(encoding="ascii"))
    return _PATCHES_CACHE


def load_manifest() -> tuple[dict, list[dict]]:
    """Return (header, records) from the S02 corpus manifest (cached)."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        lines = MANIFEST_PATH.read_text(encoding="ascii").splitlines()
        if not lines:
            raise BatteryError("corpus manifest is empty")
        header = json.loads(lines[0])
        records = [json.loads(line) for line in lines[1:] if line.strip()]
        _MANIFEST_CACHE = (header, records)
    return _MANIFEST_CACHE


def load_ontology_text() -> str:
    """Read the tracked YAML ontology catalog (cached)."""
    global _ONTOLOGY_CACHE
    if _ONTOLOGY_CACHE is None:
        _ONTOLOGY_CACHE = ONTOLOGY_PATH.read_text(encoding="utf-8")
    return _ONTOLOGY_CACHE


def load_lift_sources() -> dict[str, str]:
    """Read the lift-path Rust sources (cached)."""
    global _SOURCE_CACHE
    if _SOURCE_CACHE is None:
        _SOURCE_CACHE = {
            relpath: (ROOT / relpath).read_text(encoding="utf-8") for relpath in LIFT_SOURCES
        }
    return _SOURCE_CACHE


def _sha256_bytes(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


# ------------------------------------------------------- sample derivation #


def build_sample(records: list[dict], *, seed: int, per_decile: int, tail_n: int) -> list[str]:
    """Independently re-derive the deterministic bounded sample paths.

    Mirrors the census driver's contract (manifest-order deciles + largest
    tail) but is re-implemented here so a silent algorithm change in the driver
    is caught: the manifest is sha256-pinned, so identical inputs must yield the
    identical sample.  Only the sample *paths* are needed (no re-generation).
    """
    total = len(records)
    if total == 0:
        raise BatteryError("cannot derive a sample from an empty manifest")
    deciles: list[list[dict]] = [[] for _ in range(10)]
    for index, record in enumerate(records):
        deciles[min(9, index * 10 // total)].append(record)

    rng = random.Random(seed)
    chosen: dict[str, None] = {}
    for bucket in deciles:
        for record in rng.sample(bucket, min(per_decile, len(bucket))):
            chosen.setdefault(record["relative_path"], None)

    by_size = sorted(records, key=lambda record: (record["bytes"], record["relative_path"]))
    for record in by_size[-tail_n:] if tail_n > 0 else []:
        chosen.setdefault(record["relative_path"], None)
    return sorted(chosen)


def derive_non_normative_prefix_count(sample_paths: list[str]) -> int:
    """Count sampled paths under the non-normative bank prefixes."""
    return sum(1 for path in sample_paths if path.startswith(NON_NORMATIVE_PREFIXES))


# --------------------------------------------------------------- validators #


def _require_int(value: object, where: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise BatteryError(f"{where} is not an int")


def _require_non_negative_int_map(value: object, vocabulary: frozenset[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise BatteryError(f"{where} is not an object")
    for key, count in value.items():
        if key not in vocabulary:
            raise BatteryError(f"{where} carries a non-vocabulary key: {key!r}")
        _require_int(count, f"{where}.{key}")
        if count < 0:
            raise BatteryError(f"{where}.{key} is negative")
    return value


def validate_identity(doc: object) -> None:
    """Closed schema/version/kind, lifecycle and required non-claims."""
    if not isinstance(doc, dict):
        raise BatteryError("census document is not an object")
    if doc.get("schema") != CENSUS_SCHEMA:
        raise BatteryError(f"census schema mismatch: {doc.get('schema')!r}")
    if doc.get("version") != CENSUS_VERSION:
        raise BatteryError(f"census version mismatch: {doc.get('version')!r}")
    if doc.get("kind") != CENSUS_KIND:
        raise BatteryError(f"census kind mismatch: {doc.get('kind')!r}")
    if doc.get("r1000_status") != R1000_STATUS:
        raise BatteryError(f"unexpected r1000_status: {doc.get('r1000_status')!r}")
    non_claims = doc.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims:
        raise BatteryError("non_claims must be a non-empty list")
    if not all(isinstance(claim, str) and claim for claim in non_claims):
        raise BatteryError("non_claims must contain non-empty strings")
    missing = REQUIRED_NON_CLAIMS - set(non_claims)
    if missing:
        raise BatteryError(f"census is missing required non_claims: {sorted(missing)}")


def validate_lift_accounting(doc: dict) -> None:
    """The accounting axis closes exactly (markers/bound/unknown/tokens)."""
    lift = doc.get("lift")
    if not isinstance(lift, dict) or frozenset(lift) != LIFT_KEYS:
        raise BatteryError("lift is missing or does not carry the closed lift keys")
    for key in LIFT_KEYS:
        _require_int(lift[key], f"lift.{key}")
        if lift[key] < 0:
            raise BatteryError(f"lift.{key} is negative")
    if lift["markers"] != lift["bound"] + lift["unknown"] + lift["non_normative"]:
        raise BatteryError("lift.markers != bound + unknown + non_normative")

    by_group = _require_non_negative_int_map(doc.get("by_group"), GROUP_KEYS, "by_group")
    by_token = _require_non_negative_int_map(
        doc.get("by_catalog_token"), CATALOG_TOKENS, "by_catalog_token"
    )
    by_role = _require_non_negative_int_map(doc.get("by_role"), ROLES, "by_role")
    unmapped = _require_non_negative_int_map(
        doc.get("unmapped_tokens"), CATALOG_TOKENS, "unmapped_tokens"
    )

    if sum(by_group.values()) != lift["markers"]:
        raise BatteryError("sum(by_group) != lift.markers")
    if sum(by_token.values()) != lift["markers"]:
        raise BatteryError("sum(by_catalog_token) != lift.markers")
    if sum(by_role.values()) != lift["bound"]:
        raise BatteryError("sum(by_role) != lift.bound")
    if sum(unmapped.values()) != lift["unknown"]:
        raise BatteryError("sum(unmapped_tokens) != lift.unknown")
    if lift["bound"] > 0 and not by_role:
        raise BatteryError("lift.bound > 0 but by_role is empty (bound markers unaccounted)")
    if lift["bound"] == 0 and by_role:
        raise BatteryError("lift.bound == 0 but by_role is non-empty")
    if lift["unknown"] > 0 and not unmapped:
        raise BatteryError("lift.unknown > 0 but unmapped_tokens is empty (fail-closed lost)")
    if lift["unknown"] == 0 and unmapped:
        raise BatteryError("lift.unknown == 0 but unmapped_tokens is non-empty")


def validate_non_normative(
    doc: dict, *, derived_prefix_documents: int, text_only: list[str]
) -> None:
    """The non-normative barrier axis is structural and independently re-derived."""
    observed = doc.get("non_normative_documents")
    prefix = doc.get("non_normative_prefix_documents")
    _require_int(observed, "non_normative_documents")
    _require_int(prefix, "non_normative_prefix_documents")
    if observed < 0 or prefix < 0:
        raise BatteryError("non_normative document counters are negative")
    if observed != prefix:
        raise BatteryError(
            "structural non_normative_documents disagrees with the path-prefix expectation "
            f"({observed} != {prefix})"
        )
    if observed != derived_prefix_documents:
        raise BatteryError(
            "non_normative_documents disagrees with the independent manifest re-derivation "
            f"({observed} != {derived_prefix_documents})"
        )
    if not text_only:
        raise BatteryError("no text_only document_groups declared in the catalog")
    by_group = doc.get("by_group")
    if not isinstance(by_group, dict):
        raise BatteryError("by_group missing for the non-normative barrier check")
    barrier_markers = sum(by_group.get(group, 0) for group in text_only)
    lift = doc.get("lift")
    if not isinstance(lift, dict):
        raise BatteryError("lift missing for the non-normative barrier check")
    if barrier_markers != lift.get("non_normative"):
        raise BatteryError(
            "text-only group markers != lift.non_normative (non-normative barrier dropped) "
            f"({barrier_markers} != {lift.get('non_normative')})"
        )
    if observed == 0 and lift.get("non_normative", 0) > 0:
        raise BatteryError("lift.non_normative > 0 but no document was classified non-normative")


def validate_pins(doc: dict, header: dict) -> None:
    """Tracked-file pins match the committed bytes; binary pins are well-shaped."""
    if doc.get("manifest_path") != MANIFEST_RELPATH:
        raise BatteryError(f"manifest_path != {MANIFEST_RELPATH}: {doc.get('manifest_path')!r}")
    if not _SHA256_RE.fullmatch(str(doc.get("manifest_sha256", ""))):
        raise BatteryError("manifest_sha256 is not a sha256 token")
    if doc["manifest_sha256"] != _sha256_bytes(MANIFEST_PATH.read_bytes()):
        raise BatteryError("manifest_sha256 does not match the tracked manifest bytes")
    _require_int(doc.get("manifest_entries"), "manifest_entries")
    if doc["manifest_entries"] != EXPECTED_MANIFEST_ENTRIES:
        raise BatteryError(
            f"manifest_entries != {EXPECTED_MANIFEST_ENTRIES}: {doc['manifest_entries']}"
        )
    if not isinstance(header, dict) or doc["manifest_entries"] != header.get("counts", {}).get(
        "entries"
    ):
        raise BatteryError("manifest_entries != manifest header counts.entries")
    if not isinstance(header, dict) or doc.get("inventory_digest") != header.get(
        "inventory_digest"
    ):
        raise BatteryError("inventory_digest != manifest header inventory_digest")
    if not isinstance(header, dict) or doc.get("corpus_root") != header.get("root"):
        raise BatteryError("corpus_root != manifest header root")
    if doc.get("corpus_root") != CORPUS_ROOT:
        raise BatteryError(f"corpus_root != {CORPUS_ROOT}: {doc.get('corpus_root')!r}")

    if doc.get("ontology_path") != ONTOLOGY_RELPATH:
        raise BatteryError(f"ontology_path != {ONTOLOGY_RELPATH}: {doc.get('ontology_path')!r}")
    if not _SHA256_RE.fullmatch(str(doc.get("ontology_sha256", ""))):
        raise BatteryError("ontology_sha256 is not a sha256 token")
    if doc["ontology_sha256"] != _sha256_bytes(ONTOLOGY_PATH.read_bytes()):
        raise BatteryError("ontology_sha256 does not match the tracked ontology bytes")

    for path_key, hash_key in (
        ("producer_binary_path", "producer_binary_sha256"),
        ("consumer_binary_path", "consumer_binary_sha256"),
    ):
        if not isinstance(doc.get(path_key), str) or not doc[path_key]:
            raise BatteryError(f"{path_key} is empty")
        # target/ is gitignored: check the pin's shape only, never read it.
        if not _SHA256_RE.fullmatch(str(doc.get(hash_key, ""))):
            raise BatteryError(f"{hash_key} is not a sha256 token")

    if not isinstance(doc.get("sample_strata"), dict) or not doc["sample_strata"]:
        raise BatteryError("sample_strata is missing or empty")


def validate_xml_reparse_absent(doc: dict, sources: dict[str, str]) -> None:
    """Artifact flag false plus a clean source grep self-check."""
    if doc.get("xml_reparse_in_lift") is not False:
        raise BatteryError(
            f"xml_reparse_in_lift must be false, got {doc.get('xml_reparse_in_lift')!r}"
        )
    assert_no_xml_reparse(sources)


def validate_redaction(doc: object) -> None:
    """Every persisted string is a path/hash/count/closed token (ASCII-bounded)."""
    assert_no_raw_text(doc)


# ---------------------------------------------------------- patches axis #


def validate_patches(patches: object, census: dict) -> None:
    """Every unmapped token is classified ``patched`` or ``residual`` exactly once."""
    if not isinstance(patches, dict):
        raise BatteryError("patches document is not an object")
    if patches.get("schema") != PATCHES_SCHEMA:
        raise BatteryError(f"patches schema mismatch: {patches.get('schema')!r}")
    if patches.get("version") != 1:
        raise BatteryError(f"patches version mismatch: {patches.get('version')!r}")
    if patches.get("r1000_status") != R1000_STATUS:
        raise BatteryError(f"unexpected patches r1000_status: {patches.get('r1000_status')!r}")

    source = patches.get("source_census")
    if not isinstance(source, dict):
        raise BatteryError("patches source_census pin missing")
    if source.get("path") != "prd/migration/rust-evidence/m224-s05-hierarchy-lift-census.json":
        raise BatteryError(f"patches source_census.path unexpected: {source.get('path')!r}")
    if not _SHA256_RE.fullmatch(str(source.get("after_sha256", ""))):
        raise BatteryError("patches source_census.after_sha256 is not a sha256 token")
    if source["after_sha256"] != _sha256_bytes(CENSUS_PATH.read_bytes()):
        raise BatteryError("patches source_census.after_sha256 does not match the census bytes")

    unmapped = census.get("unmapped_tokens")
    if not isinstance(unmapped, dict):
        raise BatteryError("census unmapped_tokens missing for the patches check")

    entries = patches.get("entries")
    if not isinstance(entries, list) or not entries:
        raise BatteryError("patches entries must be a non-empty list")
    seen: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise BatteryError("patches entry is not an object")
        token = entry.get("token")
        disposition = entry.get("disposition")
        if not isinstance(token, str) or not token:
            raise BatteryError("patches entry carries an empty token")
        if token not in CATALOG_TOKENS:
            raise BatteryError(f"patches entry token is not a catalog token: {token!r}")
        if disposition not in PATCH_DISPOSITIONS:
            raise BatteryError(
                f"patches entry {token!r} disposition must be patched|residual, got {disposition!r}"
            )
        if token in seen:
            raise BatteryError(f"duplicate patches entry for token {token!r}")
        seen[token] = disposition
        _require_int(entry.get("count"), f"patches.{token}.count")
        if entry["token"] in unmapped and entry["count"] != unmapped[token]:
            raise BatteryError(
                f"patches.{token}.count != census unmapped_tokens ({entry['count']} "
                f"!= {unmapped[token]})"
            )
        groups = entry.get("groups")
        if not isinstance(groups, list) or not groups:
            raise BatteryError(f"patches.{token}.groups must be a non-empty list")
        if not all(isinstance(group, str) and group in GROUP_KEYS for group in groups):
            raise BatteryError(f"patches.{token}.groups carries a non-vocabulary group")

    missing = set(unmapped) - set(seen)
    if missing:
        raise BatteryError(f"unmapped tokens without a patches disposition: {sorted(missing)}")
    extra = set(seen) - set(unmapped)
    if extra:
        raise BatteryError(f"patches entries without a census unmapped token: {sorted(extra)}")


# -------------------------------------------------------- orchestration #


def validate_census_document(
    doc: object,
    *,
    header: dict,
    records: list[dict],
    ontology_text: str,
    sources: dict[str, str],
) -> None:
    """Full fail-closed validation of the census artifact against its sources."""
    validate_identity(doc)
    assert isinstance(doc, dict)
    validate_lift_accounting(doc)
    sample_paths = build_sample(
        records, seed=SAMPLE_SEED, per_decile=SAMPLE_PER_DECILE, tail_n=SAMPLE_TAIL_N
    )
    if len(sample_paths) != SAMPLE_SIZE:
        raise BatteryError(f"re-derived sample size {len(sample_paths)} != pinned {SAMPLE_SIZE}")
    if doc.get("sample_size") != SAMPLE_SIZE:
        raise BatteryError(f"census sample_size != {SAMPLE_SIZE}: {doc.get('sample_size')!r}")
    derived_prefix = derive_non_normative_prefix_count(sample_paths)
    validate_non_normative(
        doc, derived_prefix_documents=derived_prefix, text_only=text_only_groups(ontology_text)
    )
    validate_pins(doc, header)
    validate_xml_reparse_absent(doc, sources)
    validate_redaction(doc)


def _real_context() -> dict:
    header, records = load_manifest()
    return {
        "header": header,
        "records": records,
        "ontology_text": load_ontology_text(),
        "sources": load_lift_sources(),
    }


# -------------------------------------------------------------------- tests #


def test_artifacts_exist() -> None:
    assert CENSUS_PATH.is_file(), CENSUS_PATH
    assert PATCHES_PATH.is_file(), PATCHES_PATH
    assert MANIFEST_PATH.is_file(), MANIFEST_PATH
    assert ONTOLOGY_PATH.is_file(), ONTOLOGY_PATH
    for relpath in LIFT_SOURCES:
        assert (ROOT / relpath).is_file(), relpath


def test_schema_and_identity() -> None:
    doc = load_census()
    assert doc["schema"] == CENSUS_SCHEMA
    assert doc["kind"] == CENSUS_KIND
    validate_identity(doc)
    assert doc["r1000_status"] == R1000_STATUS
    assert REQUIRED_NON_CLAIMS <= set(doc["non_claims"])


def test_lift_accounting() -> None:
    doc = load_census()
    validate_lift_accounting(doc)
    lift = doc["lift"]
    assert lift["markers"] == sum(doc["by_group"].values())
    assert lift["markers"] == sum(doc["by_catalog_token"].values())
    assert lift["bound"] == sum(doc["by_role"].values())
    assert lift["unknown"] == sum(doc["unmapped_tokens"].values())
    assert lift["unknown"] > 0 and doc["unmapped_tokens"]


def test_xml_reparse_absent_in_flag_and_sources() -> None:
    doc = load_census()
    sources = load_lift_sources()
    validate_xml_reparse_absent(doc, sources)
    assert doc["xml_reparse_in_lift"] is False
    # Non-vacuous pattern: the guard must match a synthetic XML surface.
    assert XML_REPARSE_TOKENS.search("fn x() { from_xml(path) }") is not None
    assert XML_REPARSE_TOKENS.search("let _ = decode_blocks(stream);") is not None
    for text in sources.values():
        assert not XML_REPARSE_TOKENS.search(text)


def test_non_normative_derived_from_manifest() -> None:
    header, records = load_manifest()
    doc = load_census()
    sample_paths = build_sample(
        records, seed=SAMPLE_SEED, per_decile=SAMPLE_PER_DECILE, tail_n=SAMPLE_TAIL_N
    )
    assert len(sample_paths) == SAMPLE_SIZE
    derived = derive_non_normative_prefix_count(sample_paths)
    assert derived == EXPECTED_NON_NORMATIVE_PREFIX_DOCUMENTS
    validate_non_normative(
        doc,
        derived_prefix_documents=derived,
        text_only=text_only_groups(load_ontology_text()),
    )
    assert doc["non_normative_documents"] == derived
    assert doc["non_normative_prefix_documents"] == derived
    assert header["root"] == CORPUS_ROOT


def test_text_only_groups_match_catalog() -> None:
    derived = text_only_groups(load_ontology_text())
    assert derived == sorted(EXPECTED_NON_NORMATIVE_CLASSES)
    doc = load_census()
    barrier = sum(doc["by_group"].get(group, 0) for group in derived)
    assert barrier == doc["lift"]["non_normative"] > 0


def test_pins_match_tracked_bytes() -> None:
    header, _ = load_manifest()
    doc = load_census()
    validate_pins(doc, header)
    assert doc["manifest_sha256"] == _sha256_bytes(MANIFEST_PATH.read_bytes())
    assert doc["ontology_sha256"] == _sha256_bytes(ONTOLOGY_PATH.read_bytes())
    assert doc["manifest_entries"] == EXPECTED_MANIFEST_ENTRIES


def test_patches_cover_every_unmapped_token() -> None:
    census = load_census()
    patches = load_patches()
    validate_patches(patches, census)
    dispositions = {entry["token"]: entry["disposition"] for entry in patches["entries"]}
    assert set(dispositions) == set(census["unmapped_tokens"])
    assert set(dispositions.values()) <= PATCH_DISPOSITIONS


def test_artifacts_are_ascii_bytes() -> None:
    for path in (CENSUS_PATH, PATCHES_PATH, MANIFEST_PATH):
        raw = path.read_bytes()
        assert raw, f"{path} is empty"
        assert max(raw) < 0x80, f"{path} carries non-ASCII bytes"
        raw.decode("ascii")


def test_redaction_no_raw_text_in_payloads() -> None:
    validate_redaction(load_census())
    validate_redaction(load_patches())
    # Sanity: the redaction guard rejects non-ASCII even outside the artifact.
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})


def test_full_document_validation() -> None:
    validate_census_document(load_census(), **_real_context())


def test_full_patches_validation() -> None:
    validate_patches(load_patches(), load_census())


# ------------------------------------------- negative self-checks (battery) #


def _synthetic_census() -> dict:
    """A minimal internally-consistent census fixture for the negative checks."""
    return {
        "lift": {"markers": 3, "bound": 1, "unknown": 1, "non_normative": 1},
        "by_group": {"federal_law@v1": 1, "Unknown": 1, "non_normative": 1},
        "by_catalog_token": {"statya": 1, "punkt": 1, "chast": 1},
        "by_role": {"unit": 1},
        "unmapped_tokens": {"punkt": 1},
    }


def test_battery_rejects_wrong_schema() -> None:
    bad = copy.deepcopy(load_census())
    bad["schema"] = "m224-s05-hierarchy-lift-census/v2"
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_closed_r1000_status() -> None:
    bad = copy.deepcopy(load_census())
    bad["r1000_status"] = "closed"
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_removed_required_non_claim() -> None:
    bad = copy.deepcopy(load_census())
    bad["non_claims"] = [c for c in bad["non_claims"] if c != "no_xml_reparse_in_lift"]
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_folded_bound_into_unknown() -> None:
    # A synthetic valid doc first proves the fixture itself is accepted.
    good = _synthetic_census()
    validate_lift_accounting(good)
    folded = copy.deepcopy(good)
    folded["lift"]["bound"] = 0
    folded["lift"]["unknown"] = 2
    folded["by_role"] = {}
    # unmapped_tokens still sums to 1 != unknown (2): the fold is caught.
    with pytest.raises(BatteryError):
        validate_lift_accounting(folded)


def test_battery_rejects_bound_without_role_tally() -> None:
    bad = copy.deepcopy(_synthetic_census())
    bad["by_role"] = {}
    with pytest.raises(BatteryError):
        validate_lift_accounting(bad)


def test_battery_rejects_by_group_sum_drift() -> None:
    bad = copy.deepcopy(load_census())
    bad["by_group"]["Unknown"] += 1
    with pytest.raises(BatteryError):
        validate_lift_accounting(bad)


def test_battery_rejects_unmapped_empty_with_unknown() -> None:
    bad = copy.deepcopy(_synthetic_census())
    bad["unmapped_tokens"] = {}
    with pytest.raises(BatteryError):
        validate_lift_accounting(bad)


def test_battery_rejects_non_vocabulary_token() -> None:
    bad = copy.deepcopy(load_census())
    bad["by_catalog_token"]["chapter"] = 1
    with pytest.raises(BatteryError):
        validate_lift_accounting(bad)


def test_battery_rejects_xml_reparse_flag_true() -> None:
    bad = copy.deepcopy(load_census())
    bad["xml_reparse_in_lift"] = True
    with pytest.raises(BatteryError):
        validate_xml_reparse_absent(bad, load_lift_sources())


def test_battery_rejects_xml_call_in_lift_source() -> None:
    sources = dict(load_lift_sources())
    # The clean sources pass first (non-vacuous guard).
    assert_no_xml_reparse(sources)
    sources["crates/ln-decode/src/hierarchy_lift.rs"] += "\nfn sneaky(){ decode_blocks(); }\n"
    with pytest.raises(BatteryError):
        assert_no_xml_reparse(sources)


def test_battery_rejects_stale_manifest_pin() -> None:
    bad = copy.deepcopy(load_census())
    bad["manifest_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(BatteryError):
        validate_pins(bad, load_manifest()[0])


def test_battery_rejects_stale_ontology_pin() -> None:
    bad = copy.deepcopy(load_census())
    bad["ontology_sha256"] = "sha256:" + "1" * 64
    with pytest.raises(BatteryError):
        validate_pins(bad, load_manifest()[0])


def test_battery_rejects_non_normative_barrier_removed() -> None:
    _, records = load_manifest()
    doc = load_census()
    sample_paths = build_sample(
        records, seed=SAMPLE_SEED, per_decile=SAMPLE_PER_DECILE, tail_n=SAMPLE_TAIL_N
    )
    derived = derive_non_normative_prefix_count(sample_paths)
    text_only = text_only_groups(load_ontology_text())
    validate_non_normative(doc, derived_prefix_documents=derived, text_only=text_only)
    # Drop the barrier: no document is classified non-normative.
    blind = copy.deepcopy(doc)
    blind["non_normative_documents"] = 0
    with pytest.raises(BatteryError):
        validate_non_normative(blind, derived_prefix_documents=derived, text_only=text_only)
    # Or fold the text-only markers into the normative side.
    folded = copy.deepcopy(doc)
    folded["lift"]["non_normative"] = 0
    with pytest.raises(BatteryError):
        validate_non_normative(folded, derived_prefix_documents=derived, text_only=text_only)


def test_battery_rejects_wrong_non_normative_prefix_count() -> None:
    bad = copy.deepcopy(load_census())
    bad["non_normative_prefix_documents"] = 0
    with pytest.raises(BatteryError):
        validate_non_normative(
            bad,
            derived_prefix_documents=EXPECTED_NON_NORMATIVE_PREFIX_DOCUMENTS,
            text_only=text_only_groups(load_ontology_text()),
        )


def test_battery_rejects_patches_unknown_disposition() -> None:
    bad = copy.deepcopy(load_patches())
    bad["entries"][0]["disposition"] = "maybe"
    with pytest.raises(BatteryError):
        validate_patches(bad, load_census())


def test_battery_rejects_patches_missing_unmapped_token() -> None:
    bad = copy.deepcopy(load_patches())
    bad["entries"] = bad["entries"][:-1]
    with pytest.raises(BatteryError):
        validate_patches(bad, load_census())


def test_battery_rejects_patches_stale_census_pin() -> None:
    bad = copy.deepcopy(load_patches())
    bad["source_census"]["after_sha256"] = "sha256:" + "2" * 64
    with pytest.raises(BatteryError):
        validate_patches(bad, load_census())


def test_battery_rejects_decoded_text_in_payload() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})
    bad = copy.deepcopy(load_census())
    bad["r1000_status"] = "\u0444\u0430\u0441"
    with pytest.raises(RedactionError):
        validate_redaction(bad)


def test_battery_rejects_oversized_string() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "a" * (_MAX_PERSISTED_STRING + 1)})


def test_battery_derivation_is_non_vacuous() -> None:
    header, records = load_manifest()
    assert len(records) == EXPECTED_MANIFEST_ENTRIES
    sample_a = build_sample(
        records, seed=SAMPLE_SEED, per_decile=SAMPLE_PER_DECILE, tail_n=SAMPLE_TAIL_N
    )
    sample_b = build_sample(
        records, seed=SAMPLE_SEED, per_decile=SAMPLE_PER_DECILE, tail_n=SAMPLE_TAIL_N
    )
    assert sample_a == sample_b and len(sample_a) == SAMPLE_SIZE
    assert derive_non_normative_prefix_count(sample_a) == EXPECTED_NON_NORMATIVE_PREFIX_DOCUMENTS
    # A changed seed perturbs the sample: the derivation is seed-sensitive.
    sample_c = build_sample(
        records, seed=SAMPLE_SEED + 1, per_decile=SAMPLE_PER_DECILE, tail_n=SAMPLE_TAIL_N
    )
    assert sample_c != sample_a
    # Guard is non-vacuous against a drifted artifact.
    bad = copy.deepcopy(load_census())
    bad["by_group"]["Unknown"] -= 1
    with pytest.raises(BatteryError):
        validate_lift_accounting(bad)
