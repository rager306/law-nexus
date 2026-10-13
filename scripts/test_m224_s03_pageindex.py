#!/usr/bin/env python3
"""Fail-closed battery for the M224/S03 corpus pageindex artifacts (T04).

Independent, read-only verification of the two committed artifacts published by
T03:

* ``prd/migration/rust-evidence/m224-s03-pageindex.json`` — the
  ``m224-s03-pageindex/v1`` coverage contract (``pageindex_coverage``);
* ``prd/migration/rust-evidence/m224-s03-pageindex.jsonl`` — the
  ``m224-s03-pageindex-entries/v1`` keyed index (one ``pageindex_header`` line
  plus one line per ``(bank, document_key)`` keyed entry).

It cross-checks the derived tokens against the S02 identity envelope
(``m224-s02-identity-envelope.jsonl``) without decoding, normalising or
re-deriving anything.

The battery never regenerates the artifacts, never mutates git and never reads
a gitignored path.  It re-derives every accounting/class/key/redaction
invariant from the committed bytes and fails closed on any divergence.  In
addition it carries negative self-checks that feed deliberately broken fixtures
through the same validators, proving the validators actually reject the
conditions they claim to guard (a battery that cannot fail is not a battery).

Redaction discipline is adapted from
``scripts/test_m224_s02_anchor_coverage.py`` (non-ASCII reject + bounded
persisted string length): any decoded corpus text leaking into a persisted
payload is a hard failure.  The only deliberate non-ASCII payload is the
closed, declared ``negative_probe.numbers`` set, which the coverage JSON stores
JSON-escaped as ``\\uXXXX`` and which this battery re-verifies as such.
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
COVERAGE_PATH = EVIDENCE / "m224-s03-pageindex.json"
INDEX_PATH = EVIDENCE / "m224-s03-pageindex.jsonl"
ENVELOPE_PATH = EVIDENCE / "m224-s02-identity-envelope.jsonl"

COVERAGE_SCHEMA = "m224-s03-pageindex/v1"
INDEX_SCHEMA = "m224-s03-pageindex-entries/v1"
COVERAGE_KIND = "pageindex_coverage"
HEADER_KIND = "pageindex_header"
ENVELOPE_SCHEMA = "m224-s02-identity-envelope/v1"
WHOLE_DOCUMENT_PARA = 4294967295
URI_PREFIX = "consultantplus://offline/ref="

ENVELOPE_RELPATH = "prd/migration/rust-evidence/m224-s02-identity-envelope.jsonl"
CATALOG_SUFFIX = "catalog.sqlite"
MANIFEST_SUFFIX = "m223-s02-corpus-manifest.jsonl"

EXPECTED_ENTRIES = 43785
EXPECTED_ANCHORED = 36989
EXPECTED_UNRESOLVED = 6796
EXPECTED_KEYED = 5776
EXPECTED_KEY_UNRESOLVED = 31213
EXPECTED_KEY_COLLISION = 2
EXPECTED_TOKEN_MULTI_KEYED = 0

REQUIRED_NON_CLAIMS = {
    "no_file_path_is_a_resolution_key",
    "no_offline_token_is_decoded_normalized_or_re_derived",
}

_RECORD_FIELDS = frozenset({"bank", "document_key", "relative_path", "offline_token"})
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
#: catches an ASCII leak that the byte check would miss.
_NON_ASCII = re.compile(r"[^\x20-\x7e]")
_MAX_PERSISTED_STRING = 4096


def assert_no_raw_text(value: object, *, where: str = "$") -> None:
    """Fail-closed redaction invariant over a persisted JSON value."""
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
_INDEX_CACHE: tuple[dict, list[dict]] | None = None
_ENVELOPE_CACHE: tuple[set[str], set[str]] | None = None


def load_coverage() -> dict:
    """Parse the coverage artifact from committed ASCII bytes (cached)."""
    global _COVERAGE_CACHE
    if _COVERAGE_CACHE is None:
        _COVERAGE_CACHE = json.loads(COVERAGE_PATH.read_text(encoding="ascii"))
    return _COVERAGE_CACHE


def load_index() -> tuple[dict, list[dict]]:
    """Return (header, records) from the keyed index artifact (cached)."""
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        lines = INDEX_PATH.read_text(encoding="ascii").splitlines()
        if not lines:
            raise BatteryError("pageindex index is empty")
        header = json.loads(lines[0])
        records = [json.loads(line) for line in lines[1:]]
        _INDEX_CACHE = (header, records)
    return _INDEX_CACHE


def load_envelope_anchored() -> tuple[set[str], set[str]]:
    """Return (anchored consultant_uri tokens, anchored relative_paths)."""
    global _ENVELOPE_CACHE
    if _ENVELOPE_CACHE is None:
        lines = ENVELOPE_PATH.read_text(encoding="ascii").splitlines()
        if not lines:
            raise BatteryError("identity envelope is empty")
        assert json.loads(lines[0]).get("schema") == ENVELOPE_SCHEMA
        tokens: set[str] = set()
        paths: set[str] = set()
        for line in lines[1:]:
            record = json.loads(line)
            if "consultant_uri" in record:
                tokens.add(record["consultant_uri"])
                paths.add(record["relative_path"])
        _ENVELOPE_CACHE = (tokens, paths)
    return _ENVELOPE_CACHE


# ----------------------------------------------------------------- coverage #


def _require_int(value: object, where: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise BatteryError(f"{where} is not an int")


def _validate_meta(meta: object) -> None:
    if not isinstance(meta, dict):
        raise BatteryError("pageindex meta section missing")
    for section, suffix in (
        ("envelope", ENVELOPE_RELPATH),
        ("catalog", CATALOG_SUFFIX),
        ("manifest", MANIFEST_SUFFIX),
    ):
        entry = meta.get(section)
        if not isinstance(entry, dict):
            raise BatteryError(f"meta.{section} pin missing")
        path = entry.get("path")
        if not isinstance(path, str) or not path.endswith(suffix):
            raise BatteryError(f"meta.{section}.path does not point at {suffix}: {path!r}")
        if not _SHA256_RE.fullmatch(str(entry.get("sha256", ""))):
            raise BatteryError(f"meta.{section}.sha256 is not a sha256 token")
    if meta["envelope"]["path"] != ENVELOPE_RELPATH:
        raise BatteryError(f"meta.envelope.path != {ENVELOPE_RELPATH}")


def validate_coverage(doc: object) -> None:
    """Fail-closed validation of a coverage document (pure; accepts fixtures)."""
    if not isinstance(doc, dict):
        raise BatteryError("coverage document is not an object")
    if doc.get("schema") != COVERAGE_SCHEMA:
        raise BatteryError(f"coverage schema mismatch: {doc.get('schema')!r}")
    if doc.get("kind") != COVERAGE_KIND:
        raise BatteryError(f"coverage kind mismatch: {doc.get('kind')!r}")
    if doc.get("whole_document_para") != WHOLE_DOCUMENT_PARA:
        raise BatteryError(
            f"coverage whole_document_para != {WHOLE_DOCUMENT_PARA}: "
            f"{doc.get('whole_document_para')!r}"
        )

    counts = doc.get("counts")
    if not isinstance(counts, dict):
        raise BatteryError("coverage counts missing")
    for key in (
        "entries",
        "anchored",
        "unresolved",
        "token_index",
        "keyed",
        "key_unresolved",
        "key_collision",
        "token_multi_keyed",
    ):
        _require_int(counts.get(key), f"coverage.counts.{key}")
    if counts["entries"] != EXPECTED_ENTRIES:
        raise BatteryError(f"entries != {EXPECTED_ENTRIES}: {counts['entries']}")
    if counts["anchored"] != EXPECTED_ANCHORED:
        raise BatteryError(f"anchored != {EXPECTED_ANCHORED}: {counts['anchored']}")
    if counts["unresolved"] != EXPECTED_UNRESOLVED:
        raise BatteryError(f"unresolved != {EXPECTED_UNRESOLVED}: {counts['unresolved']}")
    if counts["anchored"] + counts["unresolved"] != counts["entries"]:
        raise BatteryError("anchored + unresolved != entries")
    if counts["token_index"] != counts["anchored"]:
        raise BatteryError("token_index != anchored")
    if counts["keyed"] + counts["key_unresolved"] != counts["anchored"]:
        raise BatteryError("keyed + key_unresolved != anchored")
    if counts["keyed"] <= 0:
        raise BatteryError("keyed is not positive (vacuous pageindex)")
    if counts["key_collision"] < 0 or counts["token_multi_keyed"] < 0:
        raise BatteryError("negative closed-class counters are impossible")

    keyed_by_bank = doc.get("keyed_by_bank")
    key_unresolved_by_bank = doc.get("key_unresolved_by_bank")
    if not isinstance(keyed_by_bank, dict) or not keyed_by_bank:
        raise BatteryError("keyed_by_bank missing or empty")
    if not isinstance(key_unresolved_by_bank, dict) or not key_unresolved_by_bank:
        raise BatteryError("key_unresolved_by_bank missing or empty")
    for bank, value in keyed_by_bank.items():
        if not isinstance(bank, str) or not bank:
            raise BatteryError("keyed_by_bank carries an empty bank")
        if "/" in bank or "\\" in bank:
            raise BatteryError(f"path-like bank in keyed_by_bank: {bank!r}")
        _require_int(value, f"keyed_by_bank.{bank}")
        if value <= 0:
            raise BatteryError(f"keyed_by_bank.{bank} is not positive")
    for bank, value in key_unresolved_by_bank.items():
        if not isinstance(bank, str) or not bank:
            raise BatteryError("key_unresolved_by_bank carries an empty label")
        if "/" in bank or "\\" in bank:
            raise BatteryError(f"path-like label in key_unresolved_by_bank: {bank!r}")
        _require_int(value, f"key_unresolved_by_bank.{bank}")
    if sum(keyed_by_bank.values()) != counts["keyed"]:
        raise BatteryError("keyed_by_bank does not sum to keyed")
    if sum(key_unresolved_by_bank.values()) != counts["key_unresolved"]:
        raise BatteryError("key_unresolved_by_bank does not sum to key_unresolved")

    probe = doc.get("negative_probe")
    if not isinstance(probe, dict):
        raise BatteryError("negative_probe missing")
    numbers = probe.get("numbers")
    if not isinstance(numbers, list) or not 0 < len(numbers) <= _MAX_NEGATIVE_PROBE_NUMBERS:
        raise BatteryError("negative_probe.numbers is not a bounded closed set")
    for number in numbers:
        if not isinstance(number, str) or not number:
            raise BatteryError("negative_probe number is not a string")
        if len(number) > _MAX_NEGATIVE_PROBE_NUMBER_LEN:
            raise BatteryError("negative_probe number exceeds the bounded length")
    if probe.get("key_matches") != 0:
        raise BatteryError(f"negative_probe.key_matches != 0: {probe.get('key_matches')!r}")
    if probe.get("token_matches") != 0:
        raise BatteryError(f"negative_probe.token_matches != 0: {probe.get('token_matches')!r}")
    per_number = probe.get("per_number")
    if not isinstance(per_number, list) or len(per_number) != len(numbers):
        raise BatteryError("negative_probe.per_number does not cover every number")
    for item in per_number:
        if not isinstance(item, dict):
            raise BatteryError("negative_probe.per_number item is not an object")
        if item.get("number") not in numbers:
            raise BatteryError("negative_probe per-number entry has an undeclared number")
        if item.get("key_matches") != 0 or item.get("token_matches") != 0:
            raise BatteryError("negative_probe per-number match is non-zero")

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

    _validate_meta(doc.get("meta"))


def validate_coverage_redaction(doc: dict) -> None:
    """Apply the redaction discipline to a coverage payload.

    ``negative_probe.numbers`` is a closed, declared set of *legal* numbers
    (e.g. Russian law abbreviations); it is the only non-ASCII payload and is
    deliberately exempt.  Every other persisted string — path, sha256, bank
    label, status, non-claim — must be ASCII.
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


# -------------------------------------------------------------------- index #


def validate_index_header(header: object, coverage: dict) -> None:
    """Fail-closed validation of the keyed-index header line."""
    if not isinstance(header, dict):
        raise BatteryError("index header is not an object")
    if header.get("schema") != INDEX_SCHEMA:
        raise BatteryError(f"index header schema mismatch: {header.get('schema')!r}")
    if header.get("kind") != HEADER_KIND:
        raise BatteryError(f"unexpected index header kind: {header.get('kind')!r}")
    if header.get("whole_document_para") != WHOLE_DOCUMENT_PARA:
        raise BatteryError("index header whole_document_para mismatch")
    if header.get("counts") != coverage.get("counts"):
        raise BatteryError("index header counts != coverage counts")
    if header.get("r1000_status") != "active/unclosed":
        raise BatteryError(f"unexpected index r1000_status: {header.get('r1000_status')!r}")
    meta = header.get("meta")
    if not isinstance(meta, dict):
        raise BatteryError("index header meta missing")
    coverage_meta = coverage.get("meta")
    if not isinstance(coverage_meta, dict):
        raise BatteryError("coverage meta missing")
    for section in ("envelope", "catalog", "manifest"):
        if meta.get(section) != coverage_meta.get(section):
            raise BatteryError(f"index header meta.{section} != coverage meta.{section}")


def validate_index_record(record: object) -> None:
    """Fail-closed validation of one keyed-index entry."""
    if not isinstance(record, dict):
        raise BatteryError("index record is not an object")
    if frozenset(record) != _RECORD_FIELDS:
        raise BatteryError(f"index record fields drifted: {sorted(record)}")

    for field in ("bank", "document_key"):
        value = record[field]
        if not isinstance(value, str) or not value:
            raise BatteryError(f"index record {field} is empty")
        if "/" in value or "\\" in value:
            raise BatteryError(f"path-like {field} used as a resolution key: {value!r}")
        if value == record.get("relative_path"):
            raise BatteryError(f"{field} equals relative_path (file path used as key)")

    path = record.get("relative_path")
    if not isinstance(path, str) or not path:
        raise BatteryError("index record relative_path missing")
    if path.startswith("/") or ".." in path.split("/") or "\\" in path:
        raise BatteryError(f"unsafe relative_path: {path!r}")

    token = record.get("offline_token")
    if not isinstance(token, str) or not token.startswith(URI_PREFIX):
        raise BatteryError(f"offline_token lacks the offline ref prefix: {token!r}")


def validate_index(
    header: object,
    records: list,
    coverage: dict,
    envelope_tokens: set[str],
) -> None:
    """Fail-closed cross-artifact validation of the whole keyed index."""
    validate_index_header(header, coverage)
    if len(records) != coverage["counts"]["keyed"]:
        raise BatteryError(
            f"index rows {len(records)} != coverage keyed {coverage['counts']['keyed']}"
        )
    if len(records) != EXPECTED_KEYED:
        raise BatteryError(f"index rows {len(records)} != {EXPECTED_KEYED}")
    for record in records:
        validate_index_record(record)

    keys = [(record["bank"], record["document_key"]) for record in records]
    if len(set(keys)) != len(keys):
        raise BatteryError("(bank, document_key) keys are not unique")

    order = [
        (record["bank"], record["document_key"], record["relative_path"]) for record in records
    ]
    if order != sorted(order):
        raise BatteryError("index rows are not sorted by (bank, document_key, relative_path)")

    paths = {record["relative_path"] for record in records}
    for record in records:
        if record["bank"] in paths or record["document_key"] in paths:
            raise BatteryError("a file path (relative_path) is used as a resolution key")

    tokens = {record["offline_token"] for record in records}
    if not tokens <= envelope_tokens:
        extra = tokens - envelope_tokens
        raise BatteryError(f"{len(extra)} index tokens are absent from the identity envelope")


def validate_index_redaction(records: list) -> None:
    """Apply the redaction discipline to every keyed-index record payload."""
    for record in records:
        assert_no_raw_text(record)


# -------------------------------------------------------------------- tests #


def test_artifacts_exist() -> None:
    assert COVERAGE_PATH.is_file(), COVERAGE_PATH
    assert INDEX_PATH.is_file(), INDEX_PATH
    assert ENVELOPE_PATH.is_file(), ENVELOPE_PATH


def test_coverage_schema_and_accounting() -> None:
    doc = load_coverage()
    assert doc["schema"] == COVERAGE_SCHEMA
    validate_coverage(doc)


def test_coverage_bank_tallies() -> None:
    doc = load_coverage()
    assert sum(doc["keyed_by_bank"].values()) == doc["counts"]["keyed"]
    assert sum(doc["key_unresolved_by_bank"].values()) == doc["counts"]["key_unresolved"]
    assert doc["counts"]["keyed"] > 0


def test_coverage_closed_class_counters() -> None:
    doc = load_coverage()
    assert doc["counts"]["key_collision"] == EXPECTED_KEY_COLLISION
    assert doc["counts"]["token_multi_keyed"] == EXPECTED_TOKEN_MULTI_KEYED


def test_coverage_whole_document_para() -> None:
    doc = load_coverage()
    assert doc["whole_document_para"] == WHOLE_DOCUMENT_PARA


def test_coverage_negative_probe_zero() -> None:
    probe = load_coverage()["negative_probe"]
    assert probe["key_matches"] == 0
    assert probe["token_matches"] == 0
    assert all(item["key_matches"] == 0 for item in probe["per_number"])
    assert all(item["token_matches"] == 0 for item in probe["per_number"])


def test_negative_probe_numbers_are_json_escaped() -> None:
    raw = COVERAGE_PATH.read_bytes()
    assert raw.decode("ascii").isascii()
    numbers = load_coverage()["negative_probe"]["numbers"]
    assert numbers, "closed probe set must not be empty"
    for number in numbers:
        escaped = json.dumps(number, ensure_ascii=True)[1:-1].encode("ascii")
        assert escaped in raw, f"probe number not JSON-escaped: {number!r}"
        assert number.encode("utf-8") not in raw, "raw non-ASCII probe number persisted"


def test_coverage_lifecycle_and_non_claims() -> None:
    doc = load_coverage()
    assert doc["r1000_status"] == "active/unclosed"
    assert doc["non_claims"], "non_claims must be non-empty"
    assert REQUIRED_NON_CLAIMS <= set(doc["non_claims"])


def test_coverage_meta_pins() -> None:
    meta = load_coverage()["meta"]
    assert meta["envelope"]["path"] == ENVELOPE_RELPATH
    assert meta["catalog"]["path"].endswith(CATALOG_SUFFIX)
    for section in ("envelope", "catalog", "manifest"):
        assert _SHA256_RE.fullmatch(meta[section]["sha256"]), section


def test_meta_envelope_sha256_matches_actual_bytes() -> None:
    doc = load_coverage()
    digest = hashlib.sha256(ENVELOPE_PATH.read_bytes()).hexdigest()
    assert doc["meta"]["envelope"]["sha256"] == f"sha256:{digest}"


def test_index_header_matches_coverage() -> None:
    header, _ = load_index()
    validate_index_header(header, load_coverage())


def test_index_line_count() -> None:
    raw = INDEX_PATH.read_bytes()
    assert raw.count(b"\n") == 1 + EXPECTED_KEYED
    header, records = load_index()
    assert len(records) == EXPECTED_KEYED
    validate_index_header(header, load_coverage())


def test_index_records_valid() -> None:
    _, records = load_index()
    for record in records:
        validate_index_record(record)


def test_index_keys_unique_sorted_and_not_paths() -> None:
    _, records = load_index()
    keys = [(record["bank"], record["document_key"]) for record in records]
    assert len(set(keys)) == len(keys)
    order = [(r["bank"], r["document_key"], r["relative_path"]) for r in records]
    assert order == sorted(order)


def test_index_tokens_byte_exact_subset_of_envelope() -> None:
    _, records = load_index()
    envelope_tokens, _ = load_envelope_anchored()
    tokens = {record["offline_token"] for record in records}
    assert tokens <= envelope_tokens


def test_index_relative_paths_subset_of_anchored_envelope() -> None:
    _, records = load_index()
    _, anchored_paths = load_envelope_anchored()
    assert {record["relative_path"] for record in records} <= anchored_paths


def test_index_full_cross_artifact_validation() -> None:
    header, records = load_index()
    envelope_tokens, _ = load_envelope_anchored()
    validate_index(header, records, load_coverage(), envelope_tokens)


def test_artifacts_are_ascii_bytes() -> None:
    for path in (COVERAGE_PATH, INDEX_PATH, ENVELOPE_PATH):
        raw = path.read_bytes()
        assert raw, f"{path.name} is empty"
        assert max(raw) < 0x80, f"{path.name} carries non-ASCII bytes"
        raw.decode("ascii")


def test_redaction_no_raw_text_in_coverage_payload() -> None:
    validate_coverage_redaction(load_coverage())


def test_redaction_no_raw_text_in_index_records() -> None:
    _, records = load_index()
    validate_index_redaction(records)


# ------------------------------------------- negative self-checks (battery) #


def test_battery_rejects_wrong_coverage_schema() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["schema"] = "m224-s03-pageindex/v2"
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_broken_accounting() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["counts"]["keyed"] += 1  # keyed + key_unresolved != anchored
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_token_index_drift() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["counts"]["token_index"] = 0
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_vacuous_keyed() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["counts"]["keyed"] = 0
    bad["counts"]["key_unresolved"] = bad["counts"]["anchored"]
    bad["keyed_by_bank"] = {}
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_keyed_by_bank_sum_mismatch() -> None:
    bad = copy.deepcopy(load_coverage())
    bank = next(iter(bad["keyed_by_bank"]))
    bad["keyed_by_bank"][bank] += 1
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_positive_key_match() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["negative_probe"]["key_matches"] = 1
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_per_number_token_match() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["negative_probe"]["per_number"][0]["token_matches"] = 1
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_wrong_whole_document_para() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["whole_document_para"] = 0
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_wrong_r1000_status() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["r1000_status"] = "closed"
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_missing_required_non_claim() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["non_claims"] = [
        claim for claim in bad["non_claims"] if claim != "no_file_path_is_a_resolution_key"
    ]
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_bad_meta_sha256() -> None:
    bad = copy.deepcopy(load_coverage())
    bad["meta"]["envelope"]["sha256"] = "sha256:zzzz"
    with pytest.raises(BatteryError):
        validate_coverage(bad)


def test_battery_rejects_header_schema_drift() -> None:
    header, _ = load_index()
    bad = copy.deepcopy(header)
    bad["schema"] = "m224-s03-pageindex-entries/v2"
    with pytest.raises(BatteryError):
        validate_index_header(bad, load_coverage())


def test_battery_rejects_header_counts_drift() -> None:
    header, _ = load_index()
    bad = copy.deepcopy(header)
    bad["counts"]["keyed"] += 1
    with pytest.raises(BatteryError):
        validate_index_header(bad, load_coverage())


def test_battery_rejects_path_like_bank() -> None:
    _, records = load_index()
    bad = copy.deepcopy(records[0])
    bad["bank"] = "courts/acn"
    with pytest.raises(BatteryError):
        validate_index_record(bad)


def test_battery_rejects_path_like_document_key() -> None:
    _, records = load_index()
    bad = copy.deepcopy(records[0])
    bad["document_key"] = "acn\\000166280"
    with pytest.raises(BatteryError):
        validate_index_record(bad)


def test_battery_rejects_key_equals_relative_path() -> None:
    _, records = load_index()
    bad = copy.deepcopy(records[0])
    bad["document_key"] = bad["relative_path"]
    with pytest.raises(BatteryError):
        validate_index_record(bad)


def test_battery_rejects_bad_offline_token_prefix() -> None:
    _, records = load_index()
    bad = copy.deepcopy(records[0])
    bad["offline_token"] = "https://example.invalid/token"
    with pytest.raises(BatteryError):
        validate_index_record(bad)


def test_battery_rejects_extra_record_field() -> None:
    _, records = load_index()
    bad = copy.deepcopy(records[0])
    bad["fld"] = "int-1-1"
    with pytest.raises(BatteryError):
        validate_index_record(bad)


def test_battery_rejects_unsorted_index() -> None:
    header, records = load_index()
    bad = copy.deepcopy(records)
    bad[0], bad[1] = bad[1], bad[0]
    envelope_tokens, _ = load_envelope_anchored()
    with pytest.raises(BatteryError):
        validate_index(header, bad, load_coverage(), envelope_tokens)


def test_battery_rejects_duplicate_index_keys() -> None:
    header, records = load_index()
    bad = copy.deepcopy(records)
    bad.append(copy.deepcopy(bad[0]))
    envelope_tokens, _ = load_envelope_anchored()
    with pytest.raises(BatteryError):
        validate_index(header, bad, load_coverage(), envelope_tokens)


def test_battery_rejects_index_token_outside_envelope() -> None:
    header, records = load_index()
    bad = copy.deepcopy(records)
    bad[0]["offline_token"] = URI_PREFIX + "DEADBEEF"
    envelope_tokens, _ = load_envelope_anchored()
    with pytest.raises(BatteryError):
        validate_index(header, bad, load_coverage(), envelope_tokens)


def test_battery_rejects_index_row_count_drift() -> None:
    header, records = load_index()
    bad = copy.deepcopy(records[:-1])
    envelope_tokens, _ = load_envelope_anchored()
    with pytest.raises(BatteryError):
        validate_index(header, bad, load_coverage(), envelope_tokens)


def test_battery_redaction_rejects_decoded_text() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})


def test_battery_redaction_rejects_oversized_string() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "a" * (_MAX_PERSISTED_STRING + 1)})


def test_battery_redaction_rejects_non_ascii_record() -> None:
    _, records = load_index()
    bad = copy.deepcopy(records[0])
    bad["bank"] = "\u0444\u0430\u0441"
    with pytest.raises(RedactionError):
        validate_index_redaction([bad])
