#!/usr/bin/env python3
"""Fail-closed battery for the M224/S07 FRBR-bridge mapping artifact (T05).

Independent, read-only verification of the tracked counts-only artifact
published by T03:

* ``prd/migration/rust-evidence/m224-s07-frbr-bridge.json`` — the
  ``m224-s07-frbr-bridge/v1`` bound of one Work and 118 Expressions of 44-ФЗ
  (``npa/law_2013-04-05_44-fz/edition-*``), joined from four tracked inputs:

  - the **S02 identity envelope** (``m224-s02-identity-envelope.jsonl``) —
    the per-edition ``source.sha256`` and the byte-exact ``consultant_uri``
    anchor;
  - the **m223-S07 consumer receipts** (``m223-s07-corpus-receipts.jsonl``) —
    ``counts.identity.{source_revision, source_sha256}``;
  - the **S06 edition timeline** (``m224-s06-edition-timeline.json``) —
    ``per_edition[].{edition_number, effect_day}``;
  - the read-only **catalog edition map** (pinned for shape only, never read:
    ``consru_export/`` is gitignored).

The battery never regenerates the artifact, never runs the producer/consumer,
never mutates git, never touches dependencies and never reads a gitignored path
(``consru_export/`` and ``target/`` are deliberately out of scope: their pins
are checked for shape only, with an explicit non-claim; the five *tracked*
inputs — envelope, receipts, timeline, ontology, hierarchy registry — are
re-hashed from their committed bytes).

Two axes are deliberately kept apart:

* the **ELI/join axis** — ``work_eli_urn`` must be the byte-exact
  ``urn:lex:ru:federal:zakon:2013-04-05;44-fz``, every
  ``expression_eli_urn`` must be ``<work_eli_urn>@<effect_iso>``, and every
  ``effect_day``/``effect_iso`` must be a single date derived independently
  from the ordinal epoch ``1800-01-01``;
* the **divergence axis** — the registry rev-only expression id (the
  ``rev-<date>`` filename segment, ``rev-initial`` falling back to the act
  enactment date) is compared against the timeline effect day and the
  divergence is **counted, not smoothed** (46 rows), matching the published
  field.

Integrity is not semantic completeness: ``r1000_status == "active/unclosed"``
plus bounded non-claims are asserted (``not_r1000_closure``,
``not_r035_promotion_bounded_mapping_evidence_only``,
``eli_urn_is_a_compatibility_projection_not_project_local_canon``).  Redaction
discipline mirrors ``scripts/test_m224_s06_edition_timeline.py`` (closed
ASCII-safe string shape + forbidden key set): decoded corpus text leaking into
a persisted payload is a hard failure.

Finally the battery re-runs the two repository-wide quality gates the plan
requires (governor and ADR conformance) as subprocesses and parses their JSON.
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
ARTIFACT_PATH = EVIDENCE / "m224-s07-frbr-bridge.json"
ENVELOPE_PATH = EVIDENCE / "m224-s02-identity-envelope.jsonl"
RECEIPTS_PATH = EVIDENCE / "m223-s07-corpus-receipts.jsonl"
TIMELINE_PATH = EVIDENCE / "m224-s06-edition-timeline.json"
ONTOLOGY_PATH = ROOT / "prd/architecture/kb-ontology.yaml"
REGISTRY_PATH = ROOT / "prd/architecture/kb-hierarchy-registry.yaml"

ENVELOPE_RELPATH = "prd/migration/rust-evidence/m224-s02-identity-envelope.jsonl"
RECEIPTS_RELPATH = "prd/migration/rust-evidence/m223-s07-corpus-receipts.jsonl"
TIMELINE_RELPATH = "prd/migration/rust-evidence/m224-s06-edition-timeline.json"
ONTOLOGY_RELPATH = "prd/architecture/kb-ontology.yaml"
REGISTRY_RELPATH = "prd/architecture/kb-hierarchy-registry.yaml"

SCHEMA = "m224-s07-frbr-bridge/v1"
VERSION = 1
KIND = "frbr_bridge_corpus"
ENVELOPE_SCHEMA = "m224-s02-identity-envelope/v1"
RECEIPTS_SCHEMA = "m223-s07-consumer-receipt/v1"
TIMELINE_SCHEMA = "m224-s06-edition-timeline/v1"
TIMELINE_KIND = "edition_timeline_corpus"
R1000_STATUS = "active/unclosed"

EDITION_PREFIX = "npa/law_2013-04-05_44-fz/edition-"
EXPECTED_ACT = {"number": "44-fz", "authority": "federal", "enactment_date": "2013-04-05"}
EXPECTED_WORK_ID = "work:ru:federal:zakon:2013-04-05:44-fz"
EXPECTED_WORK_ELI_URN = "urn:lex:ru:federal:zakon:2013-04-05;44-fz"
EXPECTED_EXPRESSION_PREFIX = "expr:ru:federal:zakon:2013-04-05:44-fz:"

EXPECTED_WORKS = 1
EXPECTED_EXPRESSIONS = 118
EXPECTED_DISTINCT_EFFECT_DAYS = 118
EXPECTED_DISTINCT_ANCHORS = 1
EXPECTED_DIVERGENCE = 46
EXPECTED_FIRST_EDITION = 1
EXPECTED_LAST_EDITION = 118
EXPECTED_FIRST_ISO = "2013-04-05"
EXPECTED_LAST_ISO = "2026-07-01"

#: Civil-day ordinal epoch: ``effect_day`` 0 == 1800-01-01.  Independent of the
#: Rust ``ln_temporal`` conversion — this battery re-derives every date itself.
ORDINAL_EPOCH = datetime.date(1800, 1, 1)

#: Registry rev-only date carried by the edition filename segment
#: (``rev-initial`` rows fall back to the act enactment date).
REV_SEGMENT = re.compile(r"_rev-(\d{4}-\d{2}-\d{2})_")

ARTIFACT_KEYS = frozenset(
    {
        "schema",
        "version",
        "kind",
        "act",
        "work",
        "edition_prefix",
        "works",
        "expressions",
        "distinct_effect_days",
        "distinct_anchors",
        "join_coverage",
        "registry_expression_id_divergence",
        "pins",
        "totals",
        "r1000_status",
        "non_claims",
        "per_expression",
    }
)
ACT_KEYS = frozenset({"number", "authority", "enactment_date"})
WORK_KEYS = frozenset({"id", "eli_urn"})
PIN_KEYS = frozenset(
    {"envelope", "receipts", "timeline", "ontology", "registry", "catalog", "consumer_binary"}
)
PIN_ENTRY_KEYS = frozenset({"path", "sha256"})
TOTAL_KEYS = frozenset({"join_mismatches", "catalog_misses", "anchor_mismatches"})
PER_EXPRESSION_KEYS = frozenset(
    {
        "relative_path",
        "edition_number",
        "effect_day",
        "effect_iso",
        "expression_id",
        "expression_eli_urn",
        "source_sha256",
        "source_revision",
        "document_version_ref",
        "decoder_profile",
        "uri_anchor",
        "catalog",
    }
)
CATALOG_KEYS = frozenset({"edition_id", "document_id", "edition_number"})

#: Tracked pins re-hashed from committed bytes (path key -> relpath).
TRACKED_PINS = {
    "envelope": ENVELOPE_RELPATH,
    "receipts": RECEIPTS_RELPATH,
    "timeline": TIMELINE_RELPATH,
    "ontology": ONTOLOGY_RELPATH,
    "registry": REGISTRY_RELPATH,
}
#: Gitignored / build-artifact pins verified for shape only (never read).
SHAPE_ONLY_PINS = {
    "catalog": "consru_export/consru_export/catalog.sqlite",
    "consumer_binary": "target/release/frbr-bridge",
}

REQUIRED_NON_CLAIMS = frozenset(
    {
        "eli_urn_is_a_compatibility_projection_not_project_local_canon",
        "cc_component_concept_canon_is_not_replaced_or_rekeyed",
        "uri_anchor_is_never_decoded_normalized_or_re_derived",
        "expression_day_is_the_timeline_effect_day_not_the_registry_rev_date",
        "not_r1000_closure",
        "not_r035_promotion_bounded_mapping_evidence_only",
        "counts_and_keys_only_no_decoded_text",
        "bounded_single_corpus_act_44fz_not_tsg_s6_not_applicable",
        "one_work_per_act_dated_editions_are_expressions",
    }
)
MIN_NON_CLAIMS = 9

_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
#: Mirrors the driver's redaction guard: closed ASCII path/hash/token/anchor
#: shapes.  The charset is the exact union used by the artifact (letters,
#: digits, ``_``, ``.``, ``/``, ``:``, ``;``, ``=``, ``@``, ``-``); a leaked
#: ASCII prose sentence (spaces/commas) is rejected, and non-ASCII decoded
#: corpus text is rejected separately.
SAFE_STRING = re.compile(r"^[A-Za-z0-9_./:=;@-]{1,1024}$")
FORBIDDEN_KEYS = frozenset({"text", "literal", "decoded", "content", "detail"})
_MAX_PERSISTED_STRING = 4096

GOVERNOR_SCHEMA = "law-nexus-governor-report/v1"
GOVERNOR_CMD = (sys.executable, "-m", "law_nexus_harness", "governor")
ADR_CMD = (sys.executable, "scripts/verify-adr-conformance.py")
SUBPROCESS_TIMEOUT_S = 600.0


class BatteryError(AssertionError):
    """A fail-closed invariant violation detected by this battery."""


class RedactionError(BatteryError):
    """Decoded corpus text or an oversized payload string leaked into an artifact."""


# --------------------------------------------------------------- redaction #


def assert_no_raw_text(value: object, *, where: str = "$") -> None:
    """Fail-closed redaction invariant over a persisted JSON value.

    Every persisted string must be a path, hash, count, closed token, identifier
    or URI anchor.  Decoded legal text (Cyrillic / prose) can never pass.
    """
    if isinstance(value, str):
        if not SAFE_STRING.match(value):
            raise RedactionError(f"unsafe persisted string at {where}: {value[:60]!r}")
        if len(value) > _MAX_PERSISTED_STRING:
            raise RedactionError(f"oversized string persisted at {where}")
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise RedactionError(f"non-string key at {where}")
            if key in FORBIDDEN_KEYS:
                raise RedactionError(f"forbidden artifact key {key!r} at {where}")
            if not SAFE_STRING.match(key):
                raise RedactionError(f"unsafe artifact key {key!r} at {where}")
            assert_no_raw_text(item, where=f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_no_raw_text(item, where=f"{where}[{index}]")
    elif isinstance(value, bool):
        return
    elif isinstance(value, (int, float)):
        return
    elif value is None:
        return
    else:
        raise RedactionError(f"unexpected value type at {where}")


# ---------------------------------------------------------------- ordinal #


def ordinal_to_iso(ordinal: int) -> str:
    """Independently re-derive ``YYYY-MM-DD`` from a civil-day ordinal.

    Epoch is ``1800-01-01`` at ordinal ``0`` (``ln_temporal`` epoch), matching
    the S06 timeline's ``effect_day``.
    """
    return (ORDINAL_EPOCH + datetime.timedelta(days=ordinal)).isoformat()


def _registry_rev_date(path: str, enactment_date: str) -> str:
    """Rev-only registry date: ``rev-<date>`` segment, else the act enactment date."""
    match = REV_SEGMENT.search(path)
    return match.group(1) if match is not None else enactment_date


# ------------------------------------------------------------------ loaders #

_ARTIFACT_CACHE: dict | None = None
_ENVELOPE_CACHE: dict[str, dict] | None = None
_RECEIPTS_CACHE: dict[str, dict] | None = None
_TIMELINE_CACHE: tuple[dict, dict[int, int]] | None = None


def load_artifact() -> dict:
    """Parse the artifact from committed ASCII bytes (cached)."""
    global _ARTIFACT_CACHE
    if _ARTIFACT_CACHE is None:
        _ARTIFACT_CACHE = json.loads(ARTIFACT_PATH.read_text(encoding="ascii"))
    return _ARTIFACT_CACHE


def load_envelope_edition_rows() -> dict[str, dict]:
    """Return ``relative_path -> envelope record`` for the bounded edition set.

    Streamed from committed bytes; only the 44-ФЗ edition rows are retained.
    """
    global _ENVELOPE_CACHE
    if _ENVELOPE_CACHE is None:
        prefix = EDITION_PREFIX.encode("ascii")
        rows: dict[str, dict] = {}
        with ENVELOPE_PATH.open("rb") as handle:
            for raw in handle:
                if prefix not in raw:
                    continue
                record = json.loads(raw)
                path = record.get("relative_path", "")
                if path.startswith(EDITION_PREFIX):
                    rows[path] = record
        _ENVELOPE_CACHE = rows
    return _ENVELOPE_CACHE


def load_receipt_edition_rows() -> dict[str, dict]:
    """Return ``relative_path -> {schema, source_revision, source_sha256}``.

    Streamed from the 77 MB committed receipts file; only the 44-ФЗ edition
    rows are parsed.
    """
    global _RECEIPTS_CACHE
    if _RECEIPTS_CACHE is None:
        prefix = EDITION_PREFIX.encode("ascii")
        rows: dict[str, dict] = {}
        with RECEIPTS_PATH.open("rb") as handle:
            for raw in handle:
                if prefix not in raw:
                    continue
                record = json.loads(raw)
                path = record.get("relative_path", "")
                if not path.startswith(EDITION_PREFIX):
                    continue
                identity = record.get("counts", {}).get("identity")
                if not isinstance(identity, dict):
                    raise BatteryError(f"receipt {path} carries no counts.identity object")
                rows[path] = {
                    "schema": record.get("schema"),
                    "source_revision": identity.get("source_revision"),
                    "source_sha256": identity.get("source_sha256"),
                }
        _RECEIPTS_CACHE = rows
    return _RECEIPTS_CACHE


def load_timeline() -> tuple[dict, dict[int, int]]:
    """Return (timeline document, ``edition_number -> effect_day``) (cached)."""
    global _TIMELINE_CACHE
    if _TIMELINE_CACHE is None:
        doc = json.loads(TIMELINE_PATH.read_text(encoding="ascii"))
        days = {
            point["edition_number"]: point["effect_day"] for point in doc.get("per_edition", [])
        }
        _TIMELINE_CACHE = (doc, days)
    return _TIMELINE_CACHE


def _sha256_bytes(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


# --------------------------------------------------------------- validators #


def _require_int(value: object, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise BatteryError(f"{where} is not an int")
    return value


def _require_exact_keys(record: object, keys: frozenset[str], label: str) -> dict:
    if not isinstance(record, dict):
        raise BatteryError(f"{label} is not an object")
    if set(record) != keys:
        missing = sorted(keys - set(record))
        extra = sorted(set(record) - keys)
        raise BatteryError(f"{label} keys drift (missing={missing}, extra={extra})")
    return record


def validate_identity(doc: object) -> None:
    """Closed schema/version/kind, lifecycle and required non-claims."""
    if not isinstance(doc, dict):
        raise BatteryError("artifact is not an object")
    if set(doc) != ARTIFACT_KEYS:
        missing = sorted(ARTIFACT_KEYS - set(doc))
        extra = sorted(set(doc) - ARTIFACT_KEYS)
        raise BatteryError(f"artifact keys drift (missing={missing}, extra={extra})")
    if doc.get("schema") != SCHEMA:
        raise BatteryError(f"artifact schema mismatch: {doc.get('schema')!r}")
    if doc.get("version") != VERSION:
        raise BatteryError(f"artifact version mismatch: {doc.get('version')!r}")
    if doc.get("kind") != KIND:
        raise BatteryError(f"artifact kind mismatch: {doc.get('kind')!r}")
    if doc.get("r1000_status") != R1000_STATUS:
        raise BatteryError(f"unexpected r1000_status: {doc.get('r1000_status')!r}")
    non_claims = doc.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims:
        raise BatteryError("non_claims must be a non-empty list")
    if not all(isinstance(claim, str) and claim for claim in non_claims):
        raise BatteryError("non_claims must contain non-empty strings")
    if len(set(non_claims)) != len(non_claims):
        raise BatteryError("non_claims contains duplicates")
    if len(non_claims) < MIN_NON_CLAIMS:
        raise BatteryError(
            f"non_claims carries {len(non_claims)} entries, expected >= {MIN_NON_CLAIMS}"
        )
    missing = REQUIRED_NON_CLAIMS - set(non_claims)
    if missing:
        raise BatteryError(f"artifact is missing required non_claims: {sorted(missing)}")


def validate_act_and_work(doc: dict) -> None:
    """The bounded act and the single registry Work are byte-exact."""
    act = _require_exact_keys(doc.get("act"), ACT_KEYS, "act")
    if act != EXPECTED_ACT:
        raise BatteryError(f"act != {EXPECTED_ACT}: {act!r}")
    work = _require_exact_keys(doc.get("work"), WORK_KEYS, "work")
    if work.get("id") != EXPECTED_WORK_ID:
        raise BatteryError(f"work.id != {EXPECTED_WORK_ID}: {work.get('id')!r}")
    if work.get("eli_urn") != EXPECTED_WORK_ELI_URN:
        raise BatteryError(f"work.eli_urn != {EXPECTED_WORK_ELI_URN}: {work.get('eli_urn')!r}")
    if doc.get("edition_prefix") != EDITION_PREFIX:
        raise BatteryError(f"edition_prefix != {EDITION_PREFIX}: {doc.get('edition_prefix')!r}")
    if doc.get("works") != EXPECTED_WORKS:
        raise BatteryError(f"works != {EXPECTED_WORKS}: {doc.get('works')!r}")
    if doc.get("expressions") != EXPECTED_EXPRESSIONS:
        raise BatteryError(f"expressions != {EXPECTED_EXPRESSIONS}: {doc.get('expressions')!r}")
    if doc.get("distinct_anchors") != EXPECTED_DISTINCT_ANCHORS:
        raise BatteryError(f"distinct_anchors != {EXPECTED_DISTINCT_ANCHORS}")
    expected_coverage = f"{EXPECTED_EXPRESSIONS}/{EXPECTED_EXPRESSIONS}"
    if doc.get("join_coverage") != expected_coverage:
        raise BatteryError(f"join_coverage != {expected_coverage}: {doc.get('join_coverage')!r}")


def validate_per_expression(doc: dict) -> list[dict]:
    """The per_expression axis: closed keys, contiguous editions, ordinal dates."""
    records = doc.get("per_expression")
    if not isinstance(records, list) or len(records) != EXPECTED_EXPRESSIONS:
        count = len(records) if isinstance(records, list) else records
        raise BatteryError(f"per_expression length != {EXPECTED_EXPRESSIONS}: {count!r}")
    work_eli_urn = doc["work"]["eli_urn"]
    numbers: list[int] = []
    paths: list[str] = []
    for record in records:
        rec = _require_exact_keys(record, PER_EXPRESSION_KEYS, "per_expression record")
        path = rec["relative_path"]
        if not isinstance(path, str) or not path.startswith(EDITION_PREFIX):
            raise BatteryError(f"per_expression relative_path outside the bounded prefix: {path!r}")
        if path.startswith("/") or ".." in path.split("/") or "\\" in path:
            raise BatteryError(f"unsafe relative_path: {path!r}")
        number = _require_int(rec["edition_number"], "per_expression.edition_number")
        numbers.append(number)
        paths.append(path)

        day = _require_int(rec["effect_day"], "per_expression.effect_day")
        if day < 0:
            raise BatteryError("per_expression.effect_day is negative")
        expected_iso = ordinal_to_iso(day)
        if rec["effect_iso"] != expected_iso:
            raise BatteryError(
                f"effect_iso {rec['effect_iso']!r} != independently derived {expected_iso!r}"
            )
        if rec["expression_eli_urn"] != f"{work_eli_urn}@{expected_iso}":
            raise BatteryError(
                f"expression_eli_urn is not <work_eli_urn>@{expected_iso}: "
                f"{rec['expression_eli_urn']!r}"
            )
        if rec["expression_id"] != f"{EXPECTED_EXPRESSION_PREFIX}{expected_iso}":
            raise BatteryError(
                f"expression_id is not grounded on the effect day: {rec['expression_id']!r}"
            )
        if not _SHA256_RE.fullmatch(str(rec["source_sha256"])):
            raise BatteryError("per_expression.source_sha256 is not a sha256 token")
        if not re.fullmatch(r"[0-9a-f]{64}", str(rec["source_revision"])):
            raise BatteryError("per_expression.source_revision is not raw hex")
        _require_exact_keys(rec["catalog"], CATALOG_KEYS, "per_expression.catalog")
        if rec["catalog"]["edition_number"] != number:
            raise BatteryError(
                "per_expression.catalog.edition_number disagrees with edition_number"
            )

    if numbers != list(range(EXPECTED_FIRST_EDITION, EXPECTED_LAST_EDITION + 1)):
        raise BatteryError("per_expression edition_number is not contiguous ascending 1..118")
    if len(set(paths)) != len(paths):
        raise BatteryError("per_expression relative_path values are not unique")
    if records[0]["effect_iso"] != EXPECTED_FIRST_ISO:
        raise BatteryError(f"edition 1 effect_iso != {EXPECTED_FIRST_ISO}")
    if records[-1]["effect_iso"] != EXPECTED_LAST_ISO:
        raise BatteryError(f"edition 118 effect_iso != {EXPECTED_LAST_ISO}")

    distinct_days = len({rec["effect_day"] for rec in records})
    if doc.get("distinct_effect_days") != EXPECTED_DISTINCT_EFFECT_DAYS:
        raise BatteryError(
            f"distinct_effect_days != {EXPECTED_DISTINCT_EFFECT_DAYS}: "
            f"{doc.get('distinct_effect_days')!r}"
        )
    if distinct_days != EXPECTED_DISTINCT_EFFECT_DAYS:
        raise BatteryError(f"derived distinct effect days {distinct_days} != 118")
    if len({rec["effect_iso"] for rec in records}) != EXPECTED_DISTINCT_EFFECT_DAYS:
        raise BatteryError("derived distinct effect_iso count != 118")
    distinct_anchors = len({rec["uri_anchor"] for rec in records})
    if distinct_anchors != EXPECTED_DISTINCT_ANCHORS:
        raise BatteryError(f"derived distinct anchors {distinct_anchors} != 1")
    return records


def validate_join(
    doc: dict,
    envelope_rows: dict[str, dict],
    receipt_rows: dict[str, dict],
    timeline_days: dict[int, int],
) -> None:
    """Independent byte-exact join over the three tracked inputs (ADR-0030 D1)."""
    records = doc["per_expression"]
    artifact_paths = {rec["relative_path"] for rec in records}
    if set(envelope_rows) != artifact_paths:
        raise BatteryError("S02 envelope edition paths != artifact per_expression paths")
    if set(receipt_rows) != artifact_paths:
        raise BatteryError("m223-S07 receipts edition paths != artifact per_expression paths")
    artifact_numbers = {rec["edition_number"] for rec in records}
    if set(timeline_days) != artifact_numbers:
        raise BatteryError("S06 timeline edition numbers != artifact edition numbers")

    for rec in records:
        path = rec["relative_path"]
        envelope = envelope_rows[path]
        receipt = receipt_rows[path]

        if envelope.get("schema") != ENVELOPE_SCHEMA:
            raise BatteryError(f"envelope record {path} schema drift: {envelope.get('schema')!r}")
        if receipt.get("schema") != RECEIPTS_SCHEMA:
            raise BatteryError(f"receipt {path} schema drift: {receipt.get('schema')!r}")

        anchor = envelope.get("consultant_uri")
        if not isinstance(anchor, str) or not anchor:
            raise BatteryError(f"envelope record {path} carries no consultant_uri anchor")
        if rec["uri_anchor"] != anchor:
            raise BatteryError(f"uri_anchor for {path} is not byte-exact against the envelope")
        if rec["source_sha256"] != envelope.get("source", {}).get("sha256"):
            raise BatteryError(f"source_sha256 for {path} differs from the envelope source.sha256")
        if rec["source_revision"] != receipt.get("source_revision"):
            raise BatteryError(f"source_revision for {path} differs from the receipt identity")
        if rec["source_sha256"] != f"sha256:{receipt.get('source_sha256')}":
            raise BatteryError(f"source_sha256 for {path} differs from the receipt identity sha")

        day = timeline_days.get(rec["edition_number"])
        if day is None:
            raise BatteryError(f"no S06 timeline point for edition {rec['edition_number']}")
        if day != rec["effect_day"]:
            raise BatteryError(
                f"effect_day for {path} differs from the S06 timeline "
                f"({rec['effect_day']} != {day})"
            )


def validate_divergence(doc: dict) -> int:
    """Independently recount the registry-rev vs timeline divergence (46 rows)."""
    enactment_date = doc["act"]["enactment_date"]
    derived = 0
    for rec in doc["per_expression"]:
        registry_date = _registry_rev_date(rec["relative_path"], enactment_date)
        if registry_date != rec["effect_iso"]:
            derived += 1
    published = doc.get("registry_expression_id_divergence")
    _require_int(published, "registry_expression_id_divergence")
    if published != EXPECTED_DIVERGENCE:
        raise BatteryError(
            f"registry_expression_id_divergence != {EXPECTED_DIVERGENCE}: {published!r}"
        )
    if derived != EXPECTED_DIVERGENCE:
        raise BatteryError(f"independently derived divergence {derived} != {EXPECTED_DIVERGENCE}")
    if derived != published:
        raise BatteryError(f"derived divergence {derived} != published {published}")
    return derived


def validate_totals(doc: dict) -> None:
    """Every reconciliation total is zero: publishing zeros is the proof."""
    totals = _require_exact_keys(doc.get("totals"), TOTAL_KEYS, "totals")
    for key in TOTAL_KEYS:
        value = _require_int(totals[key], f"totals.{key}")
        if value != 0:
            raise BatteryError(f"totals.{key} is non-zero: {value}")


def validate_pins(doc: dict) -> None:
    """Tracked pins re-hash to committed bytes; gitignored pins are shape-only."""
    pins = _require_exact_keys(doc.get("pins"), PIN_KEYS, "pins")
    for name, relpath in TRACKED_PINS.items():
        entry = _require_exact_keys(pins.get(name), PIN_ENTRY_KEYS, f"pins.{name}")
        if entry["path"] != relpath:
            raise BatteryError(f"pins.{name}.path != {relpath}: {entry['path']!r}")
        if not _SHA256_RE.fullmatch(str(entry["sha256"])):
            raise BatteryError(f"pins.{name}.sha256 is not a sha256 token")
        actual = _sha256_bytes((ROOT / relpath).read_bytes())
        if entry["sha256"] != actual:
            raise BatteryError(f"pins.{name}.sha256 does not match the tracked bytes")
    for name, relpath in SHAPE_ONLY_PINS.items():
        entry = _require_exact_keys(pins.get(name), PIN_ENTRY_KEYS, f"pins.{name}")
        if entry["path"] != relpath:
            raise BatteryError(f"pins.{name}.path != {relpath}: {entry['path']!r}")
        if not _SHA256_RE.fullmatch(str(entry["sha256"])):
            raise BatteryError(f"pins.{name}.sha256 is not a sha256 token")


def validate_redaction(doc: object) -> None:
    """Every persisted string is a path/hash/count/closed token (ASCII-bounded)."""
    assert_no_raw_text(doc)


# --------------------------------------------------- subprocess quality gates #


def parse_governor_report(stdout: str) -> dict:
    """Parse the governor JSON report from stdout (fail closed on garbage)."""
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise BatteryError(f"governor stdout is not JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise BatteryError("governor report is not an object")
    return report


def assert_governor_ok(report: dict) -> None:
    """The governor must be ok with zero tool errors (advisory warns allowed)."""
    if report.get("schema_version") != GOVERNOR_SCHEMA:
        raise BatteryError(f"governor schema mismatch: {report.get('schema_version')!r}")
    if report.get("status") != "ok":
        raise BatteryError(f"governor status != ok: {report.get('status')!r}")
    if report.get("tool_error_count") != 0:
        raise BatteryError(f"governor tool_error_count != 0: {report.get('tool_error_count')!r}")
    if report.get("error_count") != 0:
        raise BatteryError(f"governor error_count != 0: {report.get('error_count')!r}")
    _require_int(report.get("pass_count"), "governor pass_count")


def parse_adr_summary(stdout: str) -> dict:
    """Parse the ADR-conformance JSON summary from stdout (fail closed)."""
    try:
        summary = json.loads(stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise BatteryError(f"ADR conformance stdout is not JSON: {exc}") from exc
    if not isinstance(summary, dict):
        raise BatteryError("ADR conformance summary is not an object")
    return summary


def assert_adr_clean(summary: dict) -> None:
    """The ADR conformance gate must report zero findings."""
    if summary.get("status") != "ok":
        raise BatteryError(f"ADR conformance status != ok: {summary.get('status')!r}")
    if summary.get("finding_count") != 0:
        raise BatteryError(f"ADR conformance finding_count != 0: {summary.get('finding_count')!r}")


def _run(command: tuple[str, ...]) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(command),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_S,
        check=False,
    )


# -------------------------------------------------------------------- tests #


def test_artifacts_exist() -> None:
    for path in (ARTIFACT_PATH, ENVELOPE_PATH, RECEIPTS_PATH, TIMELINE_PATH):
        assert path.is_file(), path
    for path in (ONTOLOGY_PATH, REGISTRY_PATH):
        assert path.is_file(), path


def test_schema_and_identity() -> None:
    doc = load_artifact()
    validate_identity(doc)
    assert doc["schema"] == SCHEMA
    assert doc["kind"] == KIND
    assert doc["r1000_status"] == R1000_STATUS
    assert REQUIRED_NON_CLAIMS <= set(doc["non_claims"])
    assert len(doc["non_claims"]) >= MIN_NON_CLAIMS


def test_act_and_work_are_byte_exact() -> None:
    doc = load_artifact()
    validate_act_and_work(doc)
    assert doc["work"]["eli_urn"] == EXPECTED_WORK_ELI_URN
    assert doc["work"]["id"] == EXPECTED_WORK_ID


def test_eli_forms_and_ordinal_dates() -> None:
    doc = load_artifact()
    records = validate_per_expression(doc)
    assert len(records) == EXPECTED_EXPRESSIONS
    assert records[0]["effect_iso"] == EXPECTED_FIRST_ISO
    assert records[-1]["effect_iso"] == EXPECTED_LAST_ISO
    # Non-vacuity: the independent epoch conversion reproduces the endpoints.
    assert ordinal_to_iso(records[0]["effect_day"]) == EXPECTED_FIRST_ISO
    assert ordinal_to_iso(records[-1]["effect_day"]) == EXPECTED_LAST_ISO


def test_join_matches_tracked_inputs() -> None:
    doc = load_artifact()
    validate_join(
        doc,
        load_envelope_edition_rows(),
        load_receipt_edition_rows(),
        load_timeline()[1],
    )
    assert len(load_envelope_edition_rows()) == EXPECTED_EXPRESSIONS
    assert len(load_receipt_edition_rows()) == EXPECTED_EXPRESSIONS


def test_timeline_input_cross_check() -> None:
    timeline, days = load_timeline()
    assert timeline.get("schema") == TIMELINE_SCHEMA
    assert timeline.get("kind") == TIMELINE_KIND
    assert len(days) == EXPECTED_EXPRESSIONS
    assert timeline.get("edition_prefix") == EDITION_PREFIX


def test_divergence_recount_is_46() -> None:
    doc = load_artifact()
    assert validate_divergence(doc) == EXPECTED_DIVERGENCE
    assert doc["registry_expression_id_divergence"] == EXPECTED_DIVERGENCE


def test_totals_are_zero() -> None:
    doc = load_artifact()
    validate_totals(doc)
    assert doc["totals"] == {"join_mismatches": 0, "catalog_misses": 0, "anchor_mismatches": 0}


def test_pins_rehash_or_shape() -> None:
    doc = load_artifact()
    validate_pins(doc)
    # The five tracked inputs really re-hash to their pinned tokens.
    for name, relpath in TRACKED_PINS.items():
        assert doc["pins"][name]["sha256"] == _sha256_bytes((ROOT / relpath).read_bytes())
    # Gitignored inputs are shape-only and never read by this battery.
    for name in SHAPE_ONLY_PINS:
        assert _SHA256_RE.fullmatch(doc["pins"][name]["sha256"])


def test_artifact_is_ascii_bytes() -> None:
    raw = ARTIFACT_PATH.read_bytes()
    assert raw, "artifact is empty"
    assert max(raw) < 0x80, "artifact carries non-ASCII bytes"
    raw.decode("ascii")


def test_redaction_no_raw_text_in_payload() -> None:
    validate_redaction(load_artifact())
    # Sanity: the redaction guard rejects decoded text and ASCII prose alike.
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "a leaked English sentence with spaces"})
    with pytest.raises(RedactionError):
        assert_no_raw_text({"text": "decoded"})


def test_full_document_validation() -> None:
    doc = load_artifact()
    validate_identity(doc)
    validate_act_and_work(doc)
    validate_per_expression(doc)
    validate_join(
        doc,
        load_envelope_edition_rows(),
        load_receipt_edition_rows(),
        load_timeline()[1],
    )
    validate_divergence(doc)
    validate_totals(doc)
    validate_pins(doc)
    validate_redaction(doc)


def test_governor_gate_is_ok() -> None:
    result = _run(GOVERNOR_CMD)
    assert result.returncode == 0, result.stderr[-2000:]
    assert_governor_ok(parse_governor_report(result.stdout))


def test_adr_conformance_gate_is_clean() -> None:
    result = _run(ADR_CMD)
    assert result.returncode == 0, result.stderr[-2000:]
    assert_adr_clean(parse_adr_summary(result.stdout))


# ------------------------------------------- negative self-checks (battery) #


def test_battery_rejects_wrong_schema() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["schema"] = "m224-s07-frbr-bridge/v2"
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_closed_r1000_status() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["r1000_status"] = "closed"
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_removed_required_non_claim() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["non_claims"] = [
        claim
        for claim in bad["non_claims"]
        if claim != "not_r035_promotion_bounded_mapping_evidence_only"
    ]
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_too_few_non_claims() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["non_claims"] = bad["non_claims"][: MIN_NON_CLAIMS - 1]
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_extra_or_missing_artifact_key() -> None:
    extra = copy.deepcopy(load_artifact())
    extra["unexpected"] = 1
    with pytest.raises(BatteryError):
        validate_identity(extra)
    missing = copy.deepcopy(load_artifact())
    del missing["totals"]
    with pytest.raises(BatteryError):
        validate_identity(missing)


def test_battery_rejects_join_mismatch() -> None:
    doc = load_artifact()
    envelope = load_envelope_edition_rows()
    receipts = load_receipt_edition_rows()
    _, days = load_timeline()
    validate_join(doc, envelope, receipts, days)  # positive path first

    bad_anchor = copy.deepcopy(doc)
    bad_anchor["per_expression"][0]["uri_anchor"] = "consultantplus://offline/ref=" + "0" * 10
    with pytest.raises(BatteryError):
        validate_join(bad_anchor, envelope, receipts, days)

    bad_sha = copy.deepcopy(doc)
    bad_sha["per_expression"][1]["source_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(BatteryError):
        validate_join(bad_sha, envelope, receipts, days)

    bad_rev = copy.deepcopy(doc)
    bad_rev["per_expression"][2]["source_revision"] = "0" * 64
    with pytest.raises(BatteryError):
        validate_join(bad_rev, envelope, receipts, days)

    bad_day = copy.deepcopy(doc)
    bad_day["per_expression"][3]["effect_day"] += 1
    with pytest.raises(BatteryError):
        validate_join(bad_day, envelope, receipts, days)

    # A set drift (an extra artifact path) is also caught.
    bad_set = copy.deepcopy(doc)
    bad_set["per_expression"][4]["relative_path"] = EDITION_PREFIX + "edition-9999_rev-x.xml"
    bad_set["per_expression"][4]["catalog"] = {}
    with pytest.raises(BatteryError):
        validate_join(bad_set, envelope, receipts, days)


def test_battery_rejects_eli_form_drift() -> None:
    doc = load_artifact()
    validate_per_expression(doc)  # positive path first
    bad = copy.deepcopy(doc)
    bad["per_expression"][0]["expression_eli_urn"] = (
        "urn:lex:ru:federal:zakon:1999-01-01;99-fz@1999-01-01"
    )
    with pytest.raises(BatteryError):
        validate_per_expression(bad)
    bad_work = copy.deepcopy(doc)
    bad_work["work"]["eli_urn"] = "urn:lex:ru:other:1999-01-01;99-fz"
    with pytest.raises(BatteryError):
        validate_act_and_work(bad_work)


def test_battery_rejects_effect_iso_drift() -> None:
    doc = load_artifact()
    bad = copy.deepcopy(doc)
    bad["per_expression"][5]["effect_iso"] = "2000-01-01"
    with pytest.raises(BatteryError):
        validate_per_expression(bad)
    bad_work = copy.deepcopy(doc)
    bad_work["per_expression"][6]["expression_id"] = "expr:wrong"
    with pytest.raises(BatteryError):
        validate_per_expression(bad_work)


def test_battery_rejects_divergence_drift() -> None:
    doc = load_artifact()
    validate_divergence(doc)  # positive path first
    bad = copy.deepcopy(doc)
    bad["registry_expression_id_divergence"] = 45
    with pytest.raises(BatteryError):
        validate_divergence(bad)


def test_battery_rejects_pin_drift() -> None:
    doc = load_artifact()
    validate_pins(doc)  # positive path first
    for name, _ in TRACKED_PINS.items():
        bad = copy.deepcopy(doc)
        bad["pins"][name]["sha256"] = "sha256:" + "0" * 64
        with pytest.raises(BatteryError):
            validate_pins(bad)
    bad_shape = copy.deepcopy(doc)
    bad_shape["pins"]["catalog"]["sha256"] = "not-a-hash"
    with pytest.raises(BatteryError):
        validate_pins(bad_shape)
    bad_path = copy.deepcopy(doc)
    bad_path["pins"]["envelope"]["path"] = "elsewhere.jsonl"
    with pytest.raises(BatteryError):
        validate_pins(bad_path)


def test_battery_rejects_nonzero_totals() -> None:
    doc = load_artifact()
    validate_totals(doc)  # positive path first
    for key in TOTAL_KEYS:
        bad = copy.deepcopy(doc)
        bad["totals"][key] = 1
        with pytest.raises(BatteryError):
            validate_totals(bad)


def test_battery_rejects_decoded_text_in_payload() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})
    bad = copy.deepcopy(load_artifact())
    bad["act"]["number"] = "\u0444\u0430\u0441"
    with pytest.raises(RedactionError):
        validate_redaction(bad)


def test_battery_rejects_oversized_string() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "a" * (_MAX_PERSISTED_STRING + 1)})


def test_battery_rejects_failing_governor_and_adr_reports() -> None:
    with pytest.raises(BatteryError):
        assert_governor_ok({"schema_version": GOVERNOR_SCHEMA, "status": "failure"})
    with pytest.raises(BatteryError):
        assert_governor_ok(
            {
                "schema_version": GOVERNOR_SCHEMA,
                "status": "ok",
                "tool_error_count": 1,
                "error_count": 0,
                "pass_count": 1,
            }
        )
    with pytest.raises(BatteryError):
        assert_adr_clean({"status": "fail", "finding_count": 1})


def test_battery_derivation_is_non_vacuous() -> None:
    doc = load_artifact()
    envelope = load_envelope_edition_rows()
    receipts = load_receipt_edition_rows()
    _, days = load_timeline()
    # The positive path is accepted by the *same* validators the negatives hit.
    validate_identity(doc)
    validate_act_and_work(doc)
    validate_per_expression(doc)
    validate_join(doc, envelope, receipts, days)
    validate_divergence(doc)
    validate_totals(doc)
    validate_pins(doc)
    validate_redaction(doc)
    # The independent derivation really visited all 118 edition rows.
    assert len(doc["per_expression"]) == EXPECTED_EXPRESSIONS
    assert len(envelope) == EXPECTED_EXPRESSIONS
    assert len(receipts) == EXPECTED_EXPRESSIONS
    assert len(days) == EXPECTED_EXPRESSIONS
    # A one-count perturbation anywhere on the join axis is caught.
    bad = copy.deepcopy(doc)
    bad["per_expression"][-1]["effect_iso"] = "2000-01-01"
    with pytest.raises(BatteryError):
        validate_per_expression(bad)
