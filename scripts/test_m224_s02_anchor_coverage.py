#!/usr/bin/env python3
"""Fail-closed battery for the M224/S02 corpus URI-anchor artifacts (T05).

Independent, read-only verification of the two committed artifacts published by
T04:

* ``prd/migration/rust-evidence/m224-s02-uri-anchor-coverage.json`` — the
  ``m224-s02-uri-anchor-coverage/v1`` coverage contract;
* ``prd/migration/rust-evidence/m224-s02-identity-envelope.jsonl`` — the
  ``m224-s02-identity-envelope/v1`` identity envelope (one header line plus one
  line per manifest entry).

The battery never regenerates the artifacts, never mutates git and never reads
a gitignored path.  It re-derives every accounting/class/path/redaction
invariant from the committed bytes and fails closed on any divergence.  In
addition it carries negative self-checks that feed deliberately broken fixtures
through the same validators, proving the validators actually reject the
conditions they claim to guard (a battery that cannot fail is not a battery).

Redaction discipline is adapted from
``scripts/m223_s07_corpus_run.py::assert_no_raw_text`` (non-ASCII reject +
bounded persisted string length): any decoded corpus text leaking into a
persisted payload is a hard failure.
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
COVERAGE_PATH = EVIDENCE / "m224-s02-uri-anchor-coverage.json"
ENVELOPE_PATH = EVIDENCE / "m224-s02-identity-envelope.jsonl"
MANIFEST_PATH = EVIDENCE / "m223-s02-corpus-manifest.jsonl"

COVERAGE_SCHEMA = "m224-s02-uri-anchor-coverage/v1"
ENVELOPE_SCHEMA = "m224-s02-identity-envelope/v1"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
URI_PREFIX = "consultantplus://offline/ref="
UNRESOLVED_STATUS = "anchor_unresolved"

EXPECTED_ENTRIES = 43785
EXPECTED_ANCHORED = 36989
EXPECTED_UNRESOLVED = 6796
EXPECTED_UNRESOLVED_BY_BANK = {"courts": 1, "xml": 6795}

_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
_MAX_NEGATIVE_PROBE_NUMBERS = 8
_MAX_NEGATIVE_PROBE_NUMBER_LEN = 32


class BatteryError(AssertionError):
    """A fail-closed invariant violation detected by this battery."""


class RedactionError(BatteryError):
    """Decoded corpus text or an oversized payload string leaked into an artifact."""


# --------------------------------------------------------------- redaction #

#: The decoded corpus is Russian legal text, so any non-ASCII character in a
#: persisted payload string is a decoded-text leak.  A generous length cap
#: catches an ASCII leak that the byte check would miss.  Mirrors
#: ``scripts/m223_s07_corpus_run.py`` so both batteries share one discipline.
_NON_ASCII = re.compile(r"[^\x20-\x7e]")
_MAX_PERSISTED_STRING = 4096


def assert_no_raw_text(value: object, *, where: str = "$") -> None:
    """Fail-closed redaction invariant over a persisted JSON value.

    Every persisted string must be a path, a hash, a count, a closed token or a
    bounded English diagnostic.  Decoded legal text (Cyrillic) can never pass.
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


# ------------------------------------------------------------------ loaders #

_COVERAGE_CACHE: dict | None = None
_ENVELOPE_CACHE: tuple[dict, list[dict]] | None = None
_MANIFEST_CACHE: tuple[dict, list[dict]] | None = None


def load_coverage() -> dict:
    """Parse the coverage artifact from committed ASCII bytes (cached)."""
    global _COVERAGE_CACHE
    if _COVERAGE_CACHE is None:
        _COVERAGE_CACHE = json.loads(COVERAGE_PATH.read_text(encoding="ascii"))
    return _COVERAGE_CACHE


def load_envelope() -> tuple[dict, list[dict]]:
    """Return (header, records) from the identity envelope (cached)."""
    global _ENVELOPE_CACHE
    if _ENVELOPE_CACHE is None:
        lines = ENVELOPE_PATH.read_text(encoding="ascii").splitlines()
        if not lines:
            raise BatteryError("identity envelope is empty")
        header = json.loads(lines[0])
        records = [json.loads(line) for line in lines[1:]]
        _ENVELOPE_CACHE = (header, records)
    return _ENVELOPE_CACHE


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


# --------------------------------------------------------------- coverage #


def validate_coverage(doc: object) -> None:
    """Fail-closed validation of a coverage document (pure; accepts fixtures)."""
    if not isinstance(doc, dict):
        raise BatteryError("coverage document is not an object")
    if doc.get("schema") != COVERAGE_SCHEMA:
        raise BatteryError(f"coverage schema mismatch: {doc.get('schema')!r}")

    counts = doc.get("counts")
    if not isinstance(counts, dict):
        raise BatteryError("coverage counts missing")
    for key in ("entries", "anchored", "unresolved"):
        if not isinstance(counts.get(key), int) or isinstance(counts.get(key), bool):
            raise BatteryError(f"coverage counts.{key} is not an int")
    if counts["entries"] != EXPECTED_ENTRIES:
        raise BatteryError(f"entries != {EXPECTED_ENTRIES}: {counts['entries']}")
    if counts["anchored"] != EXPECTED_ANCHORED:
        raise BatteryError(f"anchored != {EXPECTED_ANCHORED}: {counts['anchored']}")
    if counts["unresolved"] != EXPECTED_UNRESOLVED:
        raise BatteryError(f"unresolved != {EXPECTED_UNRESOLVED}: {counts['unresolved']}")
    if counts["anchored"] + counts["unresolved"] != counts["entries"]:
        raise BatteryError("anchored + unresolved != entries")

    anchored_by_bank = doc.get("anchored_by_bank")
    unresolved_by_bank = doc.get("unresolved_by_bank")
    if not isinstance(anchored_by_bank, dict) or not isinstance(unresolved_by_bank, dict):
        raise BatteryError("coverage bank tallies missing")
    if sum(anchored_by_bank.values()) != counts["anchored"]:
        raise BatteryError("anchored_by_bank does not sum to anchored")
    if sum(unresolved_by_bank.values()) != counts["unresolved"]:
        raise BatteryError("unresolved_by_bank does not sum to unresolved")
    if unresolved_by_bank != EXPECTED_UNRESOLVED_BY_BANK:
        raise BatteryError(f"unresolved_by_bank != {EXPECTED_UNRESOLVED_BY_BANK}")

    probe = doc.get("negative_probe")
    if not isinstance(probe, dict):
        raise BatteryError("negative_probe missing")
    numbers = probe.get("numbers")
    if not isinstance(numbers, list) or not numbers:
        raise BatteryError("negative_probe.numbers must be a non-empty list")
    if probe.get("exact_matches") != 0:
        raise BatteryError(f"negative_probe.exact_matches != 0: {probe.get('exact_matches')!r}")
    if probe.get("like_matches") != 0:
        raise BatteryError(f"negative_probe.like_matches != 0: {probe.get('like_matches')!r}")
    per_number = probe.get("per_number")
    if not isinstance(per_number, list) or not per_number:
        raise BatteryError("negative_probe.per_number missing")
    for item in per_number:
        if not isinstance(item, dict):
            raise BatteryError("negative_probe.per_number item is not an object")
        if item.get("exact_matches") != 0 or item.get("like_matches") != 0:
            raise BatteryError("negative_probe per-number match is non-zero")

    if doc.get("r1000_status") != "active/unclosed":
        raise BatteryError(f"unexpected r1000_status: {doc.get('r1000_status')!r}")
    non_claims = doc.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims:
        raise BatteryError("non_claims must be a non-empty list")
    if not all(isinstance(claim, str) and claim for claim in non_claims):
        raise BatteryError("non_claims must contain non-empty strings")

    for section in ("manifest", "catalog"):
        entry = doc.get(section)
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise BatteryError(f"coverage.{section}.path missing")
        if not _SHA256_RE.fullmatch(str(entry.get("sha256", ""))):
            raise BatteryError(f"coverage.{section}.sha256 is not a sha256 token")


def validate_coverage_redaction(doc: dict) -> None:
    """Apply the redaction discipline to a coverage payload.

    ``negative_probe.numbers`` is a closed, declared set of *legal* numbers
    (e.g. the Russian law abbreviations); it is the only non-ASCII payload and
    is deliberately exempt.  Every other persisted string — path, sha256, bank
    name, status, non-claim — must be ASCII.
    """
    probe = doc.get("negative_probe")
    if not isinstance(probe, dict):
        raise BatteryError("negative_probe missing")
    numbers = probe.get("numbers")
    if not isinstance(numbers, list) or not 0 < len(numbers) <= _MAX_NEGATIVE_PROBE_NUMBERS:
        raise BatteryError("negative_probe.numbers is not a bounded closed set")
    for number in numbers:
        if (
            not isinstance(number, str)
            or not number
            or len(number) > _MAX_NEGATIVE_PROBE_NUMBER_LEN
        ):
            raise BatteryError("negative_probe number is not a bounded token")

    scrubbed = {key: value for key, value in doc.items() if key != "negative_probe"}
    assert_no_raw_text(scrubbed)


# --------------------------------------------------------------- envelope #


def validate_envelope_header(header: object) -> None:
    """Fail-closed validation of the envelope header line."""
    if not isinstance(header, dict):
        raise BatteryError("envelope header is not an object")
    if header.get("schema") != ENVELOPE_SCHEMA:
        raise BatteryError(f"envelope header schema mismatch: {header.get('schema')!r}")
    if header.get("kind") != "identity_envelope_header":
        raise BatteryError(f"unexpected envelope kind: {header.get('kind')!r}")
    counts = header.get("counts")
    expected = {
        "entries": EXPECTED_ENTRIES,
        "anchored": EXPECTED_ANCHORED,
        "unresolved": EXPECTED_UNRESOLVED,
    }
    if counts != expected:
        raise BatteryError(f"envelope header counts != {expected}: {counts!r}")


def validate_envelope_record(record: object) -> None:
    """Fail-closed validation of one identity-envelope data line."""
    if not isinstance(record, dict):
        raise BatteryError("envelope record is not an object")
    if record.get("schema") != ENVELOPE_SCHEMA:
        raise BatteryError(f"envelope record schema mismatch: {record.get('schema')!r}")

    path = record.get("relative_path")
    if not isinstance(path, str) or not path:
        raise BatteryError("envelope record relative_path missing")
    if path.startswith("/") or ".." in path.split("/") or "\\" in path:
        raise BatteryError(f"unsafe relative_path: {path!r}")

    source = record.get("source")
    if not isinstance(source, dict):
        raise BatteryError("envelope record source missing")
    if not _SHA256_RE.fullmatch(str(source.get("sha256", ""))):
        raise BatteryError("envelope record source.sha256 is not a sha256 token")
    if not isinstance(source.get("bytes"), int) or isinstance(source.get("bytes"), bool):
        raise BatteryError("envelope record source.bytes is not an int")
    if source["bytes"] <= 0:
        raise BatteryError("envelope record source.bytes is not positive")

    has_uri = "consultant_uri" in record
    has_status = "anchor_status" in record
    if has_uri == has_status:
        raise BatteryError("envelope record must carry exactly one of consultant_uri/anchor_status")

    if has_uri:
        uri = record["consultant_uri"]
        if not isinstance(uri, str) or not uri.startswith(URI_PREFIX):
            raise BatteryError(f"consultant_uri lacks the offline ref prefix: {uri!r}")
    else:
        if record["anchor_status"] != UNRESOLVED_STATUS:
            raise BatteryError(f"unexpected anchor_status: {record['anchor_status']!r}")


def validate_envelope(header: object, records: list, manifest_records: list) -> None:
    """Fail-closed cross-artifact validation of the whole envelope."""
    validate_envelope_header(header)
    if len(records) != EXPECTED_ENTRIES:
        raise BatteryError(f"envelope coverage {len(records)} != {EXPECTED_ENTRIES}")
    for record in records:
        validate_envelope_record(record)

    envelope_paths = [record["relative_path"] for record in records]
    if len(envelope_paths) != len(set(envelope_paths)):
        raise BatteryError("envelope relative_path values are not unique")
    manifest_paths = [record["relative_path"] for record in manifest_records]
    if set(envelope_paths) != set(manifest_paths):
        raise BatteryError("envelope path set != manifest path set")
    if envelope_paths != manifest_paths:
        raise BatteryError("envelope path order != manifest path order")


def validate_envelope_redaction(records: list) -> None:
    """Apply the redaction discipline to every envelope record payload."""
    for record in records:
        assert_no_raw_text(record)


# ------------------------------------------------------------------ tests #


def test_artifacts_exist() -> None:
    assert COVERAGE_PATH.is_file(), COVERAGE_PATH
    assert ENVELOPE_PATH.is_file(), ENVELOPE_PATH
    assert MANIFEST_PATH.is_file(), MANIFEST_PATH


def test_coverage_schema_and_accounting() -> None:
    doc = load_coverage()
    assert doc["schema"] == COVERAGE_SCHEMA
    validate_coverage(doc)


def test_coverage_bank_tallies() -> None:
    doc = load_coverage()
    assert sum(doc["anchored_by_bank"].values()) == doc["counts"]["anchored"]
    assert sum(doc["unresolved_by_bank"].values()) == doc["counts"]["unresolved"]
    assert doc["unresolved_by_bank"] == EXPECTED_UNRESOLVED_BY_BANK


def test_coverage_lifecycle_and_non_claims() -> None:
    doc = load_coverage()
    assert doc["r1000_status"] == "active/unclosed"
    assert doc["non_claims"], "non_claims must be non-empty"


def test_manifest_binding() -> None:
    doc = load_coverage()
    manifest_header, manifest_records = load_manifest()
    assert manifest_header["schema"] == MANIFEST_SCHEMA
    assert manifest_header["counts"]["entries"] == EXPECTED_ENTRIES
    assert len(manifest_records) == EXPECTED_ENTRIES
    digest = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    assert doc["manifest"]["sha256"] == f"sha256:{digest}"
    assert doc["manifest"]["inventory_digest"] == manifest_header["inventory_digest"]
    assert doc["manifest"]["path"] == MANIFEST_PATH.relative_to(ROOT).as_posix()


def test_envelope_header() -> None:
    header, _ = load_envelope()
    assert header["schema"] == ENVELOPE_SCHEMA
    validate_envelope_header(header)


def test_envelope_line_count() -> None:
    raw = ENVELOPE_PATH.read_bytes()
    assert raw.count(b"\n") == 1 + EXPECTED_ENTRIES
    header, records = load_envelope()
    assert len(records) == EXPECTED_ENTRIES
    validate_envelope_header(header)


def test_envelope_records_and_classes() -> None:
    _, records = load_envelope()
    for record in records:
        validate_envelope_record(record)
    anchored = [r for r in records if "consultant_uri" in r]
    unresolved = [r for r in records if "anchor_status" in r]
    assert len(anchored) == EXPECTED_ANCHORED
    assert len(unresolved) == EXPECTED_UNRESOLVED
    assert all(r["consultant_uri"].startswith(URI_PREFIX) for r in anchored)
    assert all(r["anchor_status"] == UNRESOLVED_STATUS for r in unresolved)


def test_envelope_paths_unique_and_match_manifest() -> None:
    header, records = load_envelope()
    _, manifest_records = load_manifest()
    validate_envelope(header, records, manifest_records)


def test_envelope_tokens_carry_no_extracted_number() -> None:
    doc = load_coverage()
    numbers = doc["negative_probe"]["numbers"]
    _, records = load_envelope()
    for record in records:
        uri = record.get("consultant_uri")
        if uri is None:
            continue
        for number in numbers:
            assert number not in uri, "extracted law number leaked into a resolved token"


def test_artifacts_are_ascii_bytes() -> None:
    for path in (COVERAGE_PATH, ENVELOPE_PATH, MANIFEST_PATH):
        raw = path.read_bytes()
        assert raw, f"{path.name} is empty"
        assert max(raw) < 0x80, f"{path.name} carries non-ASCII bytes"


def test_redaction_no_raw_text_in_envelope() -> None:
    _, records = load_envelope()
    validate_envelope_redaction(records)


def test_redaction_no_raw_text_in_coverage_payload() -> None:
    validate_coverage_redaction(load_coverage())


# ------------------------------------------- negative self-checks (battery) #


def test_battery_rejects_broken_accounting() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["counts"]["unresolved"] += 1  # anchored + unresolved != entries
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_positive_exact_match() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["negative_probe"]["exact_matches"] = 1
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_per_number_match() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["negative_probe"]["per_number"][0]["like_matches"] = 1
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_wrong_unresolved_bank_split() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["unresolved_by_bank"] = {"courts": 2, "xml": 6794}
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_both_anchor_fields() -> None:
    _, records = load_envelope()
    bad = copy.deepcopy(records[0])
    bad["anchor_status"] = UNRESOLVED_STATUS
    with pytest.raises(BatteryError):
        validate_envelope_record(bad)


def test_battery_rejects_neither_anchor_field() -> None:
    _, records = load_envelope()
    bad = copy.deepcopy(records[0])
    bad.pop("consultant_uri", None)
    bad.pop("anchor_status", None)
    with pytest.raises(BatteryError):
        validate_envelope_record(bad)


def test_battery_rejects_bad_uri_prefix() -> None:
    _, records = load_envelope()
    bad = copy.deepcopy(records[0])
    bad["consultant_uri"] = "https://example.invalid/token"
    with pytest.raises(BatteryError):
        validate_envelope_record(bad)


def test_battery_redaction_rejects_decoded_text() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})


def test_battery_redaction_rejects_oversized_string() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "a" * (_MAX_PERSISTED_STRING + 1)})
