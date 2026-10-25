#!/usr/bin/env python3
"""Fail-closed battery for the M224/S06 corpus edition-timeline artifact (T07).

Independent, read-only verification of the tracked counts-only artifact
published by T05:

* ``prd/migration/rust-evidence/m224-s06-edition-timeline.json`` — the
  ``m224-s06-edition-timeline/v1`` corpus timeline of all 118 editions of
  44-ФЗ (``npa/law_2013-04-05_44-fz/edition-*``), joined from the T03
  ``edition-timeline/v1`` and T04 ``edition-ast-ctv/v1`` consumer payloads.

The battery never regenerates an artifact, never runs the producer or consumer,
never mutates git, never touches dependencies and never reads a gitignored path
(``target/`` is deliberately out of scope: the binary pins are checked for shape
only, while the four *tracked* pins — the S02 manifest, the ontology, the
hierarchy registry and (transitively) the manifest header — are re-hashed from
their committed bytes).  It re-derives every accounting / non-monotonic /
XML-reparse / redaction / pin invariant from the committed bytes and fails
closed on any divergence.

Two axes are deliberately kept apart:

* the **edition accounting** axis — ``editions`` / ``per_edition`` / ``totals``:
  ``editions == len(per_edition) == 118`` with contiguous ascending
  ``edition_number`` ``1..118``; per edition ``drift == missing + phantom`` and
  every per-edition ``drift == 0``; the point sums close exactly over
  ``totals`` (``markers`` / ``drafts`` / ``drift`` / ``missing`` / ``phantom`` /
  ``visible`` / ``hidden`` / ``ctv_resolved`` / ``ctv_unknown`` /
  ``ctv_conflict``), ``totals.max_nodes == max(per_edition.nodes)``,
  ``totals.admitted == totals.visible + totals.hidden``,
  ``totals.applied + totals.quarantined == totals.drafts`` and
  ``totals.applied == applied_attach + applied_detach``;
* the **non-monotonic residual** axis — the 118-edition fold is documented to
  contain exactly one non-monotonic transition ``0036 -> 0037`` (D767 residual:
  ``from_day`` precedes ``rev_day``); the battery re-derives that it is
  singular, that the endpoints/sides match, and that the applied day clamps up.

The XML-reparse guard is two-fold: the artifact must carry
``xml_reparse == false`` **and** the timeline-path Rust sources
(``edition_timeline.rs`` / ``bin/edition-timeline.rs``) must not contain any
XML-decode surface (``from_xml`` / ``ConsultantWordMlBlockDecoder`` /
``decode_blocks`` / ``read_odt_content_xml``) while remaining non-vacuous (the
JSONL-only surface ``read_cleaned_wire`` / ``blocks_from_cleaned_projection``
is present).

Integrity is not semantic completeness: ``r1000_status == "active/unclosed"``
(``r070_stays_active_only_a_structural_timeline_is_claimed``) plus bounded
non-claims are asserted.  Redaction discipline mirrors
``scripts/m224_s06_edition_timeline.py`` (closed ASCII-safe string shape +
forbidden key set): decoded corpus text leaking into a persisted payload is a
hard failure.

Finally the battery re-runs the two repository-wide quality gates the plan
requires (governor and ADR conformance) as subprocesses and parses their JSON.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "prd/migration/rust-evidence"
ARTIFACT_PATH = EVIDENCE / "m224-s06-edition-timeline.json"
MANIFEST_PATH = EVIDENCE / "m223-s02-corpus-manifest.jsonl"
ONTOLOGY_PATH = ROOT / "prd/architecture/kb-ontology.yaml"
REGISTRY_PATH = ROOT / "prd/architecture/kb-hierarchy-registry.yaml"

MANIFEST_RELPATH = "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
ONTOLOGY_RELPATH = "prd/architecture/kb-ontology.yaml"
REGISTRY_RELPATH = "prd/architecture/kb-hierarchy-registry.yaml"
CORPUS_ROOT = "consru_export/consru_export/exports"
EDITION_PREFIX = "npa/law_2013-04-05_44-fz/edition-"

#: Timeline-path Rust sources that must carry no XML-decode surface.  The bin is
#: included: the whole consumer path is JSONL-only by contract (ADR-0017/S03).
TIMELINE_SOURCES = (
    "crates/ln-consultant-parser/src/edition_timeline.rs",
    "crates/ln-consultant-parser/src/bin/edition-timeline.rs",
)

#: Any occurrence of these in a timeline-path source is an XML re-parse surface.
XML_REPARSE_TOKENS = re.compile(
    r"from_xml|ConsultantWordMlBlockDecoder|decode_blocks|read_odt_content_xml"
)

#: Tokens that *must* be present: the materialized-JSONL read surface.  Their
#: absence would make the XML-reparse grep vacuously clean.
JSONL_SURFACE_TOKENS = ("read_cleaned_wire", "blocks_from_cleaned_projection")

SCHEMA = "m224-s06-edition-timeline/v1"
VERSION = 1
KIND = "edition_timeline_corpus"
MANIFEST_SCHEMA = "m223-s02-corpus-inventory/v1"
R1000_STATUS = "active/unclosed"

EXPECTED_EDITIONS = 118
EXPECTED_SLUG = "44-fz"
EXPECTED_REGISTRY_BINDINGS = 102
EXPECTED_HISTORICAL_REBINDS = 142
EXPECTED_MANIFEST_ENTRIES = 43785
EXPECTED_INVENTORY_DIGEST = (
    "sha256:aa7e14e31059c906f291423a2e8151f8bf0f857e9fd7370545d7e3b5800766dd"
)
#: The single documented non-monotonic transition (D767 residual).
EXPECTED_TRANSITION = {
    "from_edition": 36,
    "from_day": 79475,
    "to_edition": 37,
    "to_day": 79467,
    "applied_day": 79475,
}

ARTIFACT_KEYS = frozenset(
    {
        "schema",
        "version",
        "kind",
        "non_claims",
        "manifest_path",
        "manifest_sha256",
        "manifest_entries",
        "inventory_digest",
        "corpus_root",
        "edition_prefix",
        "producer_binary_path",
        "producer_binary_sha256",
        "consumer_binary_path",
        "consumer_binary_sha256",
        "ontology_path",
        "ontology_sha256",
        "registry_path",
        "registry_sha256",
        "editions",
        "slug",
        "registry_bindings",
        "historical_rebinds",
        "distinct_effect_days",
        "drift_nonzero_count",
        "totals",
        "per_edition",
        "non_monotonic_transitions",
        "xml_reparse",
        "r1000_status",
    }
)
PER_EDITION_KEYS = frozenset(
    {
        "edition_number",
        "effect_day",
        "markers",
        "drafts",
        "drift",
        "missing",
        "phantom",
        "roots",
        "nodes",
        "ctv_resolved",
        "ctv_unknown",
        "ctv_conflict",
        "visible",
        "hidden",
    }
)
TOTAL_KEYS = frozenset(
    {
        "markers",
        "drafts",
        "applied",
        "applied_attach",
        "applied_detach",
        "quarantined",
        "drift",
        "missing",
        "phantom",
        "max_nodes",
        "admitted",
        "visible",
        "hidden",
        "ctv_resolved",
        "ctv_unknown",
        "ctv_conflict",
    }
)
TRANSITION_KEYS = frozenset({"from_edition", "from_day", "to_edition", "to_day", "applied_day"})

#: Sum-closing totals keys: ``sum(per_edition[key]) == totals[key]``.
SUM_TOTAL_KEYS = (
    "markers",
    "drafts",
    "drift",
    "missing",
    "phantom",
    "visible",
    "hidden",
    "ctv_resolved",
    "ctv_unknown",
    "ctv_conflict",
)

REQUIRED_NON_CLAIMS = frozenset(
    {
        "not_r1000_closure",
        "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml",
        "no_xml_reparse_in_the_timeline_or_ctv_layer",
        "bounded_single_corpus_act_44fz_not_tsg_s6_not_applicable",
        "counts_only_no_decoded_text",
        "r070_stays_active_only_a_structural_timeline_is_claimed",
    }
)

_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
#: Mirrors the driver's redaction guard: only ASCII-safe path/hash/token shapes.
SAFE_STRING = re.compile(r"^[A-Za-z0-9_.\-/:@]{1,240}$")
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

    Every persisted string must be a path, hash, count, closed token or bounded
    English diagnostic.  Decoded legal text (Cyrillic) can never pass this.
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


# ----------------------------------------------------- XML-reparse guard #


def assert_no_xml_reparse(sources: dict[str, str]) -> None:
    """Fail closed if a timeline-path source carries any XML-decode surface."""
    if not sources:
        raise BatteryError("no timeline-path sources supplied to the XML-reparse guard")
    for path, text in sources.items():
        if not isinstance(text, str) or not text.strip():
            raise BatteryError(f"timeline-path source {path} is missing or empty")
        match = XML_REPARSE_TOKENS.search(text)
        if match is not None:
            raise BatteryError(
                f"XML re-parse surface {match.group(0)!r} found in timeline-path source {path}"
            )


def assert_jsonl_surface_present(sources: dict[str, str]) -> None:
    """The XML-reparse guard is only meaningful if the JSONL surface is present."""
    for token in JSONL_SURFACE_TOKENS:
        if not any(token in text for text in sources.values()):
            raise BatteryError(
                f"JSONL read surface {token!r} absent from every timeline-path source "
                "(XML-reparse guard would be vacuous)"
            )


# ------------------------------------------------------------------ loaders #

_ARTIFACT_CACHE: dict | None = None
_MANIFEST_CACHE: tuple[dict, list[dict]] | None = None
_SOURCE_CACHE: dict[str, str] | None = None


def load_artifact() -> dict:
    """Parse the artifact from committed ASCII bytes (cached)."""
    global _ARTIFACT_CACHE
    if _ARTIFACT_CACHE is None:
        _ARTIFACT_CACHE = json.loads(ARTIFACT_PATH.read_text(encoding="ascii"))
    return _ARTIFACT_CACHE


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


def load_timeline_sources() -> dict[str, str]:
    """Read the timeline-path Rust sources (cached)."""
    global _SOURCE_CACHE
    if _SOURCE_CACHE is None:
        _SOURCE_CACHE = {
            relpath: (ROOT / relpath).read_text(encoding="utf-8") for relpath in TIMELINE_SOURCES
        }
    return _SOURCE_CACHE


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
    if doc.get("xml_reparse") is not False:
        raise BatteryError(f"xml_reparse must be false, got {doc.get('xml_reparse')!r}")
    non_claims = doc.get("non_claims")
    if not isinstance(non_claims, list) or not non_claims:
        raise BatteryError("non_claims must be a non-empty list")
    if not all(isinstance(claim, str) and claim for claim in non_claims):
        raise BatteryError("non_claims must contain non-empty strings")
    missing = REQUIRED_NON_CLAIMS - set(non_claims)
    if missing:
        raise BatteryError(f"artifact is missing required non_claims: {sorted(missing)}")


def validate_edition_accounting(doc: dict) -> None:
    """The per-edition axis closes exactly over the totals."""
    if doc.get("editions") != EXPECTED_EDITIONS:
        raise BatteryError(f"editions != {EXPECTED_EDITIONS}: {doc.get('editions')!r}")
    if doc.get("slug") != EXPECTED_SLUG:
        raise BatteryError(f"slug != {EXPECTED_SLUG}: {doc.get('slug')!r}")
    if doc.get("registry_bindings") != EXPECTED_REGISTRY_BINDINGS:
        raise BatteryError(
            f"registry_bindings != {EXPECTED_REGISTRY_BINDINGS}: {doc.get('registry_bindings')!r}"
        )
    if doc.get("historical_rebinds") != EXPECTED_HISTORICAL_REBINDS:
        raise BatteryError(
            f"historical_rebinds != {EXPECTED_HISTORICAL_REBINDS}: "
            f"{doc.get('historical_rebinds')!r}"
        )
    if doc.get("edition_prefix") != EDITION_PREFIX:
        raise BatteryError(f"edition_prefix != {EDITION_PREFIX}: {doc.get('edition_prefix')!r}")

    points = doc.get("per_edition")
    if not isinstance(points, list) or len(points) != EXPECTED_EDITIONS:
        raise BatteryError(
            f"per_edition length != {EXPECTED_EDITIONS}: "
            f"{len(points) if isinstance(points, list) else points!r}"
        )
    numbers: list[int] = []
    for point in points:
        record = _require_exact_keys(point, PER_EDITION_KEYS, "per_edition point")
        numbers.append(_require_int(record["edition_number"], "per_edition.edition_number"))
    if numbers != list(range(1, EXPECTED_EDITIONS + 1)):
        raise BatteryError("per_edition edition_number is not contiguous ascending 1..118")

    totals = _require_exact_keys(doc.get("totals"), TOTAL_KEYS, "totals")
    for key in TOTAL_KEYS:
        _require_int(totals[key], f"totals.{key}")

    seen: dict[str, int] = {key: 0 for key in SUM_TOTAL_KEYS}
    max_nodes = 0
    for point in points:
        record = _require_exact_keys(point, PER_EDITION_KEYS, "per_edition point")
        for key in PER_EDITION_KEYS:
            value = _require_int(record[key], f"per_edition.{key}")
            if value < 0:
                raise BatteryError(f"per_edition.{key} is negative")
        if record["drift"] != record["missing"] + record["phantom"]:
            raise BatteryError("per_edition drift != missing + phantom")
        if record["drift"] != 0:
            raise BatteryError(f"per_edition drift is non-zero: {record['drift']}")
        if record["visible"] + record["hidden"] != record["nodes"]:
            raise BatteryError("per_edition visible + hidden != nodes")
        for key in SUM_TOTAL_KEYS:
            seen[key] += record[key]
        max_nodes = max(max_nodes, record["nodes"])

    for key in SUM_TOTAL_KEYS:
        if seen[key] != totals[key]:
            raise BatteryError(
                f"totals.{key} does not sum over per_edition ({seen[key]} != {totals[key]})"
            )
    if totals["max_nodes"] != max_nodes:
        raise BatteryError(
            f"totals.max_nodes != max(per_edition.nodes) ({totals['max_nodes']} != {max_nodes})"
        )
    if totals["admitted"] != totals["visible"] + totals["hidden"]:
        raise BatteryError("totals.admitted != totals.visible + totals.hidden")
    if seen["visible"] + seen["hidden"] != totals["admitted"]:
        raise BatteryError("sum(visible) + sum(hidden) != totals.admitted")
    if totals["applied"] != totals["applied_attach"] + totals["applied_detach"]:
        raise BatteryError("totals.applied != applied_attach + applied_detach")
    if totals["applied"] + totals["quarantined"] != totals["drafts"]:
        raise BatteryError("totals.applied + totals.quarantined != totals.drafts")
    if totals["drift"] != totals["missing"] + totals["phantom"]:
        raise BatteryError("totals.drift != totals.missing + totals.phantom")
    if totals["drift"] != 0:
        raise BatteryError(f"totals.drift is non-zero: {totals['drift']}")

    if doc.get("drift_nonzero_count") != 0:
        raise BatteryError(f"drift_nonzero_count != 0: {doc.get('drift_nonzero_count')!r}")
    if doc.get("distinct_effect_days") != EXPECTED_EDITIONS:
        raise BatteryError(
            f"distinct_effect_days != {EXPECTED_EDITIONS}: {doc.get('distinct_effect_days')!r}"
        )
    derived_days = len({point["effect_day"] for point in points})
    if derived_days != EXPECTED_EDITIONS:
        raise BatteryError(f"distinct effect_day count {derived_days} != {EXPECTED_EDITIONS}")
    # Nodes/roots are structural, never zero for a law with a glava/statya body.
    if max_nodes <= 0:
        raise BatteryError("every edition carries zero nodes (accounting lost its subject)")
    if sum(point["roots"] for point in points) <= 0:
        raise BatteryError("every edition carries zero roots (accounting lost its subject)")


def validate_non_monotonic(doc: dict) -> None:
    """Exactly the single documented 0036 -> 0037 residual, clamped up."""
    transitions = doc.get("non_monotonic_transitions")
    if not isinstance(transitions, list) or len(transitions) != 1:
        raise BatteryError(
            f"non_monotonic_transitions must hold exactly one transition, got {transitions!r}"
        )
    transition = _require_exact_keys(transitions[0], TRANSITION_KEYS, "non_monotonic transition")
    for key in TRANSITION_KEYS:
        _require_int(transition[key], f"non_monotonic.{key}")
    if transition != EXPECTED_TRANSITION:
        raise BatteryError(
            f"non_monotonic transition != documented 0036->0037 residual: {transition!r}"
        )
    if transition["from_day"] <= transition["to_day"]:
        raise BatteryError("transition is not actually non-monotonic (from_day <= to_day)")
    if transition["applied_day"] != max(transition["from_day"], transition["to_day"]):
        raise BatteryError("applied_day is not the clamped max(from_day, to_day)")
    if transition["to_edition"] != transition["from_edition"] + 1:
        raise BatteryError("transition endpoints are not adjacent editions")


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
    if header.get("schema") != MANIFEST_SCHEMA:
        raise BatteryError(f"manifest header schema mismatch: {header.get('schema')!r}")
    if doc.get("inventory_digest") != header.get("inventory_digest"):
        raise BatteryError("inventory_digest != manifest header inventory_digest")
    if doc.get("inventory_digest") != EXPECTED_INVENTORY_DIGEST:
        raise BatteryError("inventory_digest != the pinned corpus digest")
    if doc.get("corpus_root") != header.get("root"):
        raise BatteryError("corpus_root != manifest header root")
    if doc.get("corpus_root") != CORPUS_ROOT:
        raise BatteryError(f"corpus_root != {CORPUS_ROOT}: {doc.get('corpus_root')!r}")
    # The manifest really indexes the 44-FZ edition rows the artifact claims.
    _, records = load_manifest()
    edition_rows = [
        record
        for record in records
        if str(record.get("relative_path", "")).startswith(EDITION_PREFIX)
    ]
    if len(edition_rows) != EXPECTED_EDITIONS:
        raise BatteryError(
            f"manifest carries {len(edition_rows)} 44-FZ edition rows, expected {EXPECTED_EDITIONS}"
        )

    if doc.get("ontology_path") != ONTOLOGY_RELPATH:
        raise BatteryError(f"ontology_path != {ONTOLOGY_RELPATH}: {doc.get('ontology_path')!r}")
    if not _SHA256_RE.fullmatch(str(doc.get("ontology_sha256", ""))):
        raise BatteryError("ontology_sha256 is not a sha256 token")
    if doc["ontology_sha256"] != _sha256_bytes(ONTOLOGY_PATH.read_bytes()):
        raise BatteryError("ontology_sha256 does not match the tracked ontology bytes")

    if doc.get("registry_path") != REGISTRY_RELPATH:
        raise BatteryError(f"registry_path != {REGISTRY_RELPATH}: {doc.get('registry_path')!r}")
    if not _SHA256_RE.fullmatch(str(doc.get("registry_sha256", ""))):
        raise BatteryError("registry_sha256 is not a sha256 token")
    if doc["registry_sha256"] != _sha256_bytes(REGISTRY_PATH.read_bytes()):
        raise BatteryError("registry_sha256 does not match the tracked registry bytes")

    for path_key, hash_key in (
        ("producer_binary_path", "producer_binary_sha256"),
        ("consumer_binary_path", "consumer_binary_sha256"),
    ):
        if not isinstance(doc.get(path_key), str) or not doc[path_key]:
            raise BatteryError(f"{path_key} is empty")
        # target/ is gitignored: check the pin's shape only, never read it.
        if not _SHA256_RE.fullmatch(str(doc.get(hash_key, ""))):
            raise BatteryError(f"{hash_key} is not a sha256 token")


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
    assert ARTIFACT_PATH.is_file(), ARTIFACT_PATH
    assert MANIFEST_PATH.is_file(), MANIFEST_PATH
    assert ONTOLOGY_PATH.is_file(), ONTOLOGY_PATH
    assert REGISTRY_PATH.is_file(), REGISTRY_PATH
    for relpath in TIMELINE_SOURCES:
        assert (ROOT / relpath).is_file(), relpath


def test_schema_and_identity() -> None:
    doc = load_artifact()
    validate_identity(doc)
    assert doc["schema"] == SCHEMA
    assert doc["kind"] == KIND
    assert doc["r1000_status"] == R1000_STATUS
    assert doc["xml_reparse"] is False
    assert REQUIRED_NON_CLAIMS <= set(doc["non_claims"])


def test_edition_accounting_closes() -> None:
    doc = load_artifact()
    validate_edition_accounting(doc)
    assert doc["editions"] == EXPECTED_EDITIONS
    assert len(doc["per_edition"]) == EXPECTED_EDITIONS
    assert all(point["drift"] == 0 for point in doc["per_edition"])
    assert doc["totals"]["drift"] == 0
    assert doc["drift_nonzero_count"] == 0


def test_non_monotonic_residual_is_singular_and_documented() -> None:
    doc = load_artifact()
    validate_non_monotonic(doc)
    transition = doc["non_monotonic_transitions"][0]
    assert (transition["from_edition"], transition["to_edition"]) == (36, 37)
    assert transition["from_day"] > transition["to_day"]


def test_pins_match_tracked_bytes() -> None:
    header, _ = load_manifest()
    doc = load_artifact()
    validate_pins(doc, header)
    assert doc["manifest_sha256"] == _sha256_bytes(MANIFEST_PATH.read_bytes())
    assert doc["ontology_sha256"] == _sha256_bytes(ONTOLOGY_PATH.read_bytes())
    assert doc["registry_sha256"] == _sha256_bytes(REGISTRY_PATH.read_bytes())
    assert doc["manifest_entries"] == EXPECTED_MANIFEST_ENTRIES


def test_xml_reparse_absent_in_flag_and_sources() -> None:
    doc = load_artifact()
    sources = load_timeline_sources()
    assert doc["xml_reparse"] is False
    assert_no_xml_reparse(sources)
    assert_jsonl_surface_present(sources)
    # Non-vacuous pattern: the guard must match synthetic XML surfaces.
    assert XML_REPARSE_TOKENS.search("fn x() { from_xml(path) }") is not None
    assert XML_REPARSE_TOKENS.search("let _ = decode_blocks(stream);") is not None
    assert XML_REPARSE_TOKENS.search("ConsultantWordMlBlockDecoder::new()") is not None
    assert XML_REPARSE_TOKENS.search("read_odt_content_xml(&path)") is not None


def test_artifacts_are_ascii_bytes() -> None:
    # The counts-only artifact and the pinned manifest are ASCII; the YAML
    # catalogs are tracked UTF-8 and are deliberately out of this axis.
    for path in (ARTIFACT_PATH, MANIFEST_PATH):
        raw = path.read_bytes()
        assert raw, f"{path} is empty"
        assert max(raw) < 0x80, f"{path} carries non-ASCII bytes"
        raw.decode("ascii")


def test_redaction_no_raw_text_in_payload() -> None:
    validate_redaction(load_artifact())
    # Sanity: the redaction guard rejects non-ASCII even outside the artifact.
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})
    with pytest.raises(RedactionError):
        assert_no_raw_text({"text": "decoded"})


def test_redaction_text_layer_stays_within_counts() -> None:
    """The counts-only artifact carries no decoded corpus text layer."""
    doc = load_artifact()
    # Every persisted string is a closed ASCII path/hash/token (never prose or
    # decoded legal text), and the CTV layer is pure counts.
    assert_no_raw_text(doc)
    for point in doc["per_edition"]:
        for key in ("ctv_resolved", "ctv_unknown", "ctv_conflict", "visible", "hidden"):
            assert isinstance(point[key], int) and not isinstance(point[key], bool)
    for key in ("ctv_resolved", "ctv_unknown", "ctv_conflict", "visible", "hidden"):
        assert isinstance(doc["totals"][key], int)
    # A decoded-text leak is rejected by the same guard.
    with pytest.raises(RedactionError):
        assert_no_raw_text({"decoded": "\u0424\u0417"})


def test_full_document_validation() -> None:
    header, _ = load_manifest()
    doc = load_artifact()
    validate_identity(doc)
    validate_edition_accounting(doc)
    validate_non_monotonic(doc)
    validate_pins(doc, header)
    validate_redaction(doc)
    assert_no_xml_reparse(load_timeline_sources())
    assert_jsonl_surface_present(load_timeline_sources())


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
    bad["schema"] = "m224-s06-edition-timeline/v2"
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_closed_r1000_status() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["r1000_status"] = "closed"
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_removed_required_non_claim() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["non_claims"] = [claim for claim in bad["non_claims"] if claim != "not_r1000_closure"]
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_xml_reparse_flag_true() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["xml_reparse"] = True
    with pytest.raises(BatteryError):
        validate_identity(bad)


def test_battery_rejects_extra_or_missing_artifact_key() -> None:
    extra = copy.deepcopy(load_artifact())
    extra["pins"] = {}
    with pytest.raises(BatteryError):
        validate_identity(extra)
    missing = copy.deepcopy(load_artifact())
    del missing["registry_sha256"]
    with pytest.raises(BatteryError):
        validate_identity(missing)


def test_battery_rejects_corrupt_drift_value() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["per_edition"][0]["drift"] = 7
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad)
    # A drift/missing/phantom identity break is also caught without drift>0.
    bad2 = copy.deepcopy(load_artifact())
    bad2["per_edition"][5]["missing"] = 1
    bad2["per_edition"][5]["drift"] = 1
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad2)


def test_battery_rejects_totals_sum_drift() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["totals"]["markers"] += 1
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad)
    bad2 = copy.deepcopy(load_artifact())
    bad2["totals"]["max_nodes"] += 1
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad2)
    bad3 = copy.deepcopy(load_artifact())
    bad3["totals"]["admitted"] += 1
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad3)
    bad4 = copy.deepcopy(load_artifact())
    bad4["totals"]["quarantined"] = 0
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad4)


def test_battery_rejects_wrong_edition_count_and_numbers() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["editions"] = 117
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad)
    bad2 = copy.deepcopy(load_artifact())
    bad2["per_edition"][10]["edition_number"] = 999
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad2)
    bad3 = copy.deepcopy(load_artifact())
    bad3["per_edition"] = bad3["per_edition"][:-1]
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad3)


def test_battery_rejects_drift_nonzero_count() -> None:
    bad = copy.deepcopy(load_artifact())
    bad["drift_nonzero_count"] = 1
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad)


def test_battery_rejects_wrong_non_monotonic() -> None:
    extra = copy.deepcopy(load_artifact())
    extra["non_monotonic_transitions"] = extra["non_monotonic_transitions"] * 2
    with pytest.raises(BatteryError):
        validate_non_monotonic(extra)
    moved = copy.deepcopy(load_artifact())
    moved["non_monotonic_transitions"][0]["to_edition"] = 38
    with pytest.raises(BatteryError):
        validate_non_monotonic(moved)
    monotonic = copy.deepcopy(load_artifact())
    monotonic["non_monotonic_transitions"][0]["to_day"] = 79480
    with pytest.raises(BatteryError):
        validate_non_monotonic(monotonic)
    unclamped = copy.deepcopy(load_artifact())
    unclamped["non_monotonic_transitions"][0]["applied_day"] = 79467
    with pytest.raises(BatteryError):
        validate_non_monotonic(unclamped)


def test_battery_rejects_stale_pins() -> None:
    header, _ = load_manifest()
    for key in ("manifest_sha256", "ontology_sha256", "registry_sha256"):
        bad = copy.deepcopy(load_artifact())
        bad[key] = "sha256:" + "0" * 64
        with pytest.raises(BatteryError):
            validate_pins(bad, header)
    bad_entries = copy.deepcopy(load_artifact())
    bad_entries["manifest_entries"] = EXPECTED_MANIFEST_ENTRIES - 1
    with pytest.raises(BatteryError):
        validate_pins(bad_entries, header)
    bad_digest = copy.deepcopy(load_artifact())
    bad_digest["inventory_digest"] = "sha256:" + "1" * 64
    with pytest.raises(BatteryError):
        validate_pins(bad_digest, header)
    bad_binary = copy.deepcopy(load_artifact())
    bad_binary["consumer_binary_sha256"] = "not-a-hash"
    with pytest.raises(BatteryError):
        validate_pins(bad_binary, header)


def test_battery_rejects_xml_call_in_timeline_source() -> None:
    sources = dict(load_timeline_sources())
    # The clean sources pass first (non-vacuous guard).
    assert_no_xml_reparse(sources)
    sources["crates/ln-consultant-parser/src/edition_timeline.rs"] += (
        "\nfn sneaky(){ decode_blocks(); }\n"
    )
    with pytest.raises(BatteryError):
        assert_no_xml_reparse(sources)


def test_battery_rejects_missing_jsonl_surface() -> None:
    with pytest.raises(BatteryError):
        assert_jsonl_surface_present({"a.rs": "fn main(){}"})
    with pytest.raises(BatteryError):
        assert_no_xml_reparse({})


def test_battery_rejects_decoded_text_in_payload() -> None:
    with pytest.raises(RedactionError):
        assert_no_raw_text({"leak": "\u0424\u0417"})
    bad = copy.deepcopy(load_artifact())
    bad["slug"] = "\u0444\u0430\u0441"
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
    # The positive path is accepted by the *same* validators the negatives hit.
    validate_identity(doc)
    validate_edition_accounting(doc)
    validate_non_monotonic(doc)
    header, _ = load_manifest()
    validate_pins(doc, header)
    validate_redaction(doc)
    sources = load_timeline_sources()
    assert_no_xml_reparse(sources)
    assert_jsonl_surface_present(sources)
    # A one-count perturbation anywhere on the accounting axis is caught.
    bad = copy.deepcopy(doc)
    bad["per_edition"][-1]["nodes"] += 1
    with pytest.raises(BatteryError):
        validate_edition_accounting(bad)
