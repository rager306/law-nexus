#!/usr/bin/env python3
"""Build deterministic non-authoritative Consultant WordML hierarchy records.

This command parses the canonical ConsultantPlus Word 2003 WordML fixture with a
streaming paragraph reader. It emits context-first hierarchy/source records only;
it does not claim legal correctness, parser completeness, or authoritative legal
interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from parser_records import dumps_jsonl_record, parse_parser_record

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = Path("law-source/consultant/44-FZ-2026.xml")
INVENTORY_PATH = Path("prd/parser/source_fixture_inventory.json")
JSONL_PATH = Path("prd/parser/consultant_hierarchy_records.jsonl")
JSON_PATH = Path("prd/parser/consultant_hierarchy_records.json")
REPORT_PATH = Path("prd/parser/consultant_hierarchy_records.md")
WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"
MAX_DIAGNOSTICS = 100
#: In-scope document types for M072 S05 hierarchy extraction. These are the
#: source-roles that have a normative-act structure (full-federal-law + code).
#: Other source-roles (court decisions, antimonopoly decisions, government
#: resolutions, lists, reviews, ODT) are out-of-scope and get a documented
#: 'no hierarchy' statement in the corpus report.
IN_SCOPE_DOCUMENT_TYPES: tuple[str, ...] = ("federal_law", "code")
NON_CLAIMS = [
    "Consultant hierarchy records are deterministic parser-source records only.",
    "Consultant hierarchy records do not claim legal correctness or authoritative legal interpretation.",
    "Consultant hierarchy records do not claim parser completeness.",
    "Consultant hierarchy records do not claim product ETL or FalkorDB load readiness.",
]

Level = Literal["document", "section", "chapter", "article", "part", "clause", "subclause", "paragraph", "unknown"]


@dataclass(frozen=True)
class Paragraph:
    """One bounded streamed WordML paragraph."""

    index: int
    text: str
    style: str | None


@dataclass(frozen=True)
class Marker:
    """Detected hierarchy marker for a paragraph."""

    level: Level
    raw: str
    normalized: str
    kind: str


@dataclass(frozen=True)
class BuildResult:
    """Generated artifacts and diagnostics."""

    records: list[dict[str, Any]]
    jsonl: str
    summary_json: str
    report_md: str
    diagnostics: dict[str, Any]


def stable_json(data: Any) -> str:
    """Return deterministic pretty JSON with a trailing newline."""

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(path: Path) -> str:
    """Return SHA-256 of a source file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    """Return SHA-256 of text encoded as UTF-8."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    """Decode XML/html entities and collapse WordML whitespace deterministically."""

    decoded = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", decoded).strip()


def truncate(text: str, limit: int) -> str:
    """Return a bounded string without splitting deterministic behavior across callers."""

    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def marker_title(text: str, marker: Marker | None) -> str:
    """Return a bounded title preserving the visible legal marker."""

    if marker is None:
        return truncate(text, 240)
    return truncate(text, 240)


def marker_for_text(text: str) -> Marker | None:
    """Classify one paragraph as a hierarchy marker using anchored context-first rules."""

    match = re.match(r"^(Глава\s+\d+(?:\.\d+)?\.)\s*(.+)$", text, flags=re.IGNORECASE)
    if match:
        return Marker("chapter", match.group(1), match.group(1).lower(), "chapter-number")

    match = re.match(r"^(§\s*\d+(?:\.\d+)?\.)\s*(.+)$", text, flags=re.IGNORECASE)
    if match:
        normalized = re.sub(r"\s+", "", match.group(1)).replace(".", "")
        return Marker("section", match.group(1), normalized, "section-symbol-number")

    match = re.match(r"^(Статья\s+\d+(?:\.\d+)?\.)\s*(.+)$", text, flags=re.IGNORECASE)
    if match:
        return Marker("article", match.group(1), match.group(1).lower(), "article-number")

    match = re.match(r"^(\d+(?:\.\d+)?\.)\s+\S", text)
    if match:
        return Marker("part", match.group(1), match.group(1).rstrip("."), "part-number")

    match = re.match(r"^(\d+(?:\.\d+)?\))\s+\S", text)
    if match:
        return Marker("clause", match.group(1), match.group(1).rstrip(")"), "clause-number")

    match = re.match(r"^([а-яё]\))\s+\S", text, flags=re.IGNORECASE)
    if match:
        return Marker("subclause", match.group(1), match.group(1).rstrip(")").lower(), "subclause-letter")

    return None


def paragraph_style(elem: ET.Element) -> str | None:
    """Return the WordML paragraph style value if present."""

    style_tag = f"{{{WORDML_NS}}}pStyle"
    style_attr = f"{{{WORDML_NS}}}val"
    for child in elem.iter():
        if child.tag == style_tag:
            return child.attrib.get(style_attr) or child.attrib.get("val")
    return None


def stream_wordml_paragraphs(path: Path) -> tuple[list[Paragraph], dict[str, Any]]:
    """Stream WordML paragraphs while collecting bounded source diagnostics."""

    paragraphs: list[Paragraph] = []
    namespace_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()
    skipped_empty = 0
    malformed_xml: str | None = None
    paragraph_count = 0

    try:
        context = ET.iterparse(path, events=("start", "end"))
        for event, elem in context:
            if event == "start" and elem.tag.startswith("{"):
                namespace_counts[elem.tag[1:].split("}", 1)[0]] += 1
            if event == "end" and elem.tag == f"{{{WORDML_NS}}}p":
                paragraph_count += 1
                style = paragraph_style(elem)
                style_counts[style or "<none>"] += 1
                text = normalize_text("".join(elem.itertext()))
                if text:
                    paragraphs.append(Paragraph(index=paragraph_count, text=text, style=style))
                else:
                    skipped_empty += 1
                elem.clear()
    except ET.ParseError as exc:
        malformed_xml = str(exc)

    diagnostics = {
        "malformed_xml": malformed_xml,
        "namespace_detected": WORDML_NS if namespace_counts.get(WORDML_NS, 0) else None,
        "namespace_observations": dict(sorted(namespace_counts.items())),
        "paragraph_count": paragraph_count,
        "style_observations": dict(sorted(style_counts.items())),
        "skipped_empty_paragraphs": skipped_empty,
    }
    return paragraphs, diagnostics


def compact_error(kind: str, message: str, **extra: Any) -> dict[str, Any]:
    """Return a bounded deterministic diagnostic error."""

    payload = {"kind": kind, "message": truncate(str(message), 240)}
    payload.update(extra)
    return payload


def _derive_scope_id(path: str) -> str:
    """Derive a deterministic ASCII-safe scope id from a fixture path.

    The scope id prefixes all hierarchy record ids emitted for that fixture
    (e.g. ``CONS-FL-44-FZ-2026``, ``CONS-CODE-BK-145-FZ``). It must be unique
    across the in-scope corpus so that concatenated JSONL output has no id
    collisions.
    """

    stem = Path(path).stem
    ascii_safe = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-")[:24]
    if not ascii_safe:
        ascii_safe = re.sub(r"[^A-Za-z0-9]+", "-", Path(path).name).strip("-")[:24]
    return f"CONS-{ascii_safe}" if ascii_safe else "CONS-UNKNOWN"


def _document_id(scope_id: str) -> str:
    """Stable document record id derived from the per-fixture scope id."""

    return f"DOC-{scope_id}"


def _document_hierarchy_id(scope_id: str) -> str:
    """Stable document-hierarchy (root) record id for a fixture."""

    return f"HIER-{scope_id}-DOCUMENT"


def load_inventory_fixture(target_path: str = str(SOURCE_PATH)) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Load the canonical inventory entry for the given target fixture path."""

    inventory_path = ROOT / INVENTORY_PATH
    if not inventory_path.exists():
        return None, [compact_error("missing_inventory", f"inventory file missing: {INVENTORY_PATH}", path=str(INVENTORY_PATH))]

    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [compact_error("malformed_inventory_json", exc, path=str(INVENTORY_PATH))]

    for fixture in payload.get("fixtures", []):
        if fixture.get("path") == target_path:
            return fixture, []
    return None, [
        compact_error(
            "missing_inventory_fixture",
            f"canonical inventory fixture missing: {target_path}",
            path=target_path,
        )
    ]


def next_record_id(scope_id: str, counters: Counter[str], level: Level) -> str:
    """Return a stable record id for a hierarchy level occurrence.

    IDs are prefixed with the per-fixture scope id (e.g. ``HIER-CONS-44-FZ-2026-CHAPTER-0001``)
    so concatenated records from multiple fixtures do not collide.
    """

    if level == "document":
        return _document_hierarchy_id(scope_id)
    counters[level] += 1
    return f"HIER-{scope_id}-{level.upper()}-{counters[level]:04d}"


def parent_for_level(level: Level, context: dict[str, str | None]) -> str | None:
    """Choose the current legal-context parent for a new hierarchy record."""

    if level == "document":
        return None
    if level == "chapter":
        return context["document"]
    if level == "section":
        return context["chapter"] or context["document"]
    if level == "article":
        return context["section"] or context["chapter"] or context["document"]
    if level == "part":
        return context["article"]
    if level == "clause":
        return context["part"] or context["article"]
    if level == "subclause":
        return context["clause"] or context["part"] or context["article"]
    return context["article"] or context["section"] or context["chapter"] or context["document"]


def update_context(level: Level, record_id: str, context: dict[str, str | None]) -> None:
    """Reset lower hierarchy boundaries after adding a record."""

    if level == "document":
        context.update({"document": record_id, "chapter": None, "section": None, "article": None, "part": None, "clause": None, "subclause": None})
    elif level == "chapter":
        context.update({"chapter": record_id, "section": None, "article": None, "part": None, "clause": None, "subclause": None})
    elif level == "section":
        context.update({"section": record_id, "article": None, "part": None, "clause": None, "subclause": None})
    elif level == "article":
        context.update({"article": record_id, "part": None, "clause": None, "subclause": None})
    elif level == "part":
        context.update({"part": record_id, "clause": None, "subclause": None})
    elif level == "clause":
        context.update({"clause": record_id, "subclause": None})
    elif level == "subclause":
        context.update({"subclause": record_id})


def build_record(
    *,
    record_id: str,
    level: Level,
    paragraph: Paragraph,
    marker: Marker | None,
    parent_id: str | None,
    source_sha256: str,
    scope_id: str,
    document_id: str,
    source_path: str,
) -> dict[str, Any]:
    """Build and validate one Consultant hierarchy parser record."""

    excerpt = truncate(paragraph.text, 500)
    payload: dict[str, Any] = {
        "record_kind": "consultant_hierarchy",
        "schema_version": "legalgraph-parser-record/v1",
        "id": record_id,
        "document_id": document_id,
        "source_kind": "consultant-wordml-xml",
        "source_path": source_path,
        "source_sha256": source_sha256,
        "source_member": None,
        "order_index": paragraph.index,
        "parent_id": parent_id,
        "level": level,
        "marker": None
        if marker is None
        else {"raw": marker.raw, "normalized": marker.normalized, "kind": marker.kind},
        "title": marker_title(paragraph.text, marker),
        "location": {
            "selector": f"/w:wordDocument/w:body/w:p[{paragraph.index}]",
            "label": f"WordML paragraph {paragraph.index}" + (f" style {paragraph.style}" if paragraph.style else ""),
        },
        "excerpt": excerpt,
        "excerpt_sha256": sha256_text(excerpt),
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
    }
    parse_parser_record(payload)
    return payload


def hierarchy_records(
    paragraphs: list[Paragraph],
    source_sha256: str,
    *,
    scope_id: str,
    document_id: str,
    source_path: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract hierarchy records using current-context boundaries, not global regex."""

    document_hierarchy_id = _document_hierarchy_id(scope_id)
    records: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    rejected_context_markers: list[dict[str, Any]] = []
    validation_errors: list[dict[str, Any]] = []
    context: dict[str, str | None] = {
        "document": document_hierarchy_id,
        "chapter": None,
        "section": None,
        "article": None,
        "part": None,
        "clause": None,
        "subclause": None,
    }

    first_title = next((p for p in paragraphs if p.style == "5" and not p.text.startswith("iVBOR")), paragraphs[0])
    document_paragraph = Paragraph(index=first_title.index, text=first_title.text, style=first_title.style)
    records.append(
        build_record(
            record_id=document_hierarchy_id,
            level="document",
            paragraph=document_paragraph,
            marker=None,
            parent_id=None,
            source_sha256=source_sha256,
            scope_id=scope_id,
            document_id=document_id,
            source_path=source_path,
        )
    )

    for paragraph in paragraphs:
        marker = marker_for_text(paragraph.text)
        if marker is None:
            continue
        if marker.level in {"part", "clause", "subclause"} and context["article"] is None:
            skipped[f"{marker.level}_outside_article"] += 1
            if len(rejected_context_markers) < MAX_DIAGNOSTICS:
                excerpt = truncate(paragraph.text, 240)
                rejected_context_markers.append(
                    {
                        "paragraph_index": paragraph.index,
                        "level": marker.level,
                        "marker": marker.raw,
                        "rule_id": "hierarchical_parsing_required",
                        "reason": f"{marker.level}_outside_article",
                        "source_excerpt": excerpt,
                        "source_excerpt_sha256": sha256_text(excerpt),
                    }
                )
            continue
        parent_id = parent_for_level(marker.level, context)
        if parent_id is None:
            skipped[f"{marker.level}_without_parent"] += 1
            if len(rejected_context_markers) < MAX_DIAGNOSTICS:
                excerpt = truncate(paragraph.text, 240)
                rejected_context_markers.append(
                    {
                        "paragraph_index": paragraph.index,
                        "level": marker.level,
                        "marker": marker.raw,
                        "rule_id": "hierarchical_parsing_required",
                        "reason": f"{marker.level}_without_parent",
                        "source_excerpt": excerpt,
                        "source_excerpt_sha256": sha256_text(excerpt),
                    }
                )
            continue
        record_id = next_record_id(scope_id, counters, marker.level)
        try:
            record = build_record(
                record_id=record_id,
                level=marker.level,
                paragraph=paragraph,
                marker=marker,
                parent_id=parent_id,
                source_sha256=source_sha256,
                scope_id=scope_id,
                document_id=document_id,
                source_path=source_path,
            )
        except Exception as exc:  # compact diagnostics; continue to bound failures deterministically
            if len(validation_errors) < MAX_DIAGNOSTICS:
                validation_errors.append(
                    {
                        "paragraph_index": paragraph.index,
                        "level": marker.level,
                        "marker": marker.raw,
                        "message": str(exc),
                    }
                )
            continue
        records.append(record)
        update_context(marker.level, record_id, context)

    emitted_counts = Counter(record["level"] for record in records)
    structural_errors: list[dict[str, Any]] = []
    if counters and emitted_counts.get("article", 0) == 0:
        structural_errors.append(
            compact_error(
                "missing_article_heading",
                "hierarchy markers were detected but no article heading was emitted; lower-level legal context is unsafe",
                emitted_counts_by_level=dict(sorted(emitted_counts.items())),
                skipped_marker_counts=dict(sorted(skipped.items())),
            )
        )
    if skipped:
        for kind, count in sorted(skipped.items()):
            structural_errors.append(compact_error("context_break", f"{kind}: {count}", count=count))

    diagnostics = {
        "emitted_counts_by_level": dict(sorted(emitted_counts.items())),
        "skipped_marker_counts": dict(sorted(skipped.items())),
        "rejected_context_marker_count": len(rejected_context_markers),
        "rejected_context_markers": rejected_context_markers,
        "structural_errors": structural_errors[:MAX_DIAGNOSTICS],
        "structural_error_count": len(structural_errors),
        "validation_errors": validation_errors,
        "validation_error_count": len(validation_errors),
    }
    return records, diagnostics


def build_for_fixture(source_path: Path, scope_id: str) -> BuildResult:
    """Build all Consultant hierarchy artifacts in memory for a single fixture.

    ``source_path`` is the repo-relative path to the Consultant WordML
    fixture; ``scope_id`` is the per-fixture id prefix (see :func:`_derive_scope_id`).
    The returned :class:`BuildResult` carries records, jsonl text, summary
    json, report markdown, and diagnostics for that fixture only.
    """

    source = ROOT / source_path
    fatal_errors: list[dict[str, Any]] = []
    inventory_fixture, inventory_errors = load_inventory_fixture(target_path=str(source_path))
    fatal_errors.extend(inventory_errors)

    if source.exists():
        source_sha256 = sha256_bytes(source)
        paragraphs, stream_diagnostics = stream_wordml_paragraphs(source)
    else:
        source_sha256 = None
        paragraphs = []
        stream_diagnostics = {
            "malformed_xml": None,
            "namespace_detected": None,
            "namespace_observations": {},
            "paragraph_count": 0,
            "style_observations": {},
            "skipped_empty_paragraphs": 0,
        }
        fatal_errors.append(compact_error("missing_source", f"source fixture missing: {source_path}", path=str(source_path)))

    inventory_sha256 = None if inventory_fixture is None else inventory_fixture.get("sha256")
    document_id = _document_id(scope_id)
    records, hierarchy_diagnostics = (
        hierarchy_records(
            paragraphs,
            source_sha256 or "0" * 64,
            scope_id=scope_id,
            document_id=document_id,
            source_path=str(source_path),
        )
        if not fatal_errors and stream_diagnostics["malformed_xml"] is None
        else ([], {
            "emitted_counts_by_level": {},
            "skipped_marker_counts": {},
            "rejected_context_marker_count": 0,
            "rejected_context_markers": [],
            "structural_errors": [],
            "structural_error_count": 0,
            "validation_errors": [],
            "validation_error_count": 0,
        })
    )

    inventory_hash_matches = source_sha256 == inventory_sha256 if source_sha256 is not None and inventory_sha256 is not None else False
    jsonl = "".join(dumps_jsonl_record(record) + "\n" for record in records)
    summary = {
        "scope_id": scope_id,
        "document_id": document_id,
        "artifact_paths": {
            "json": str(JSON_PATH),
            "jsonl": str(JSONL_PATH),
            "report": str(REPORT_PATH),
        },
        "artifact_freshness": None,
        "diagnostics_bounded": True,
        "fatal_errors": fatal_errors[:MAX_DIAGNOSTICS],
        "fatal_error_count": len(fatal_errors),
        "non_authoritative": True,
        "phase": "consultant_wordml_hierarchy_build",
        "source": {
            "inventory_hash_matches": inventory_hash_matches,
            "inventory_sha256": inventory_sha256,
            "path": str(source_path),
            "sha256": source_sha256,
        },
        **stream_diagnostics,
        **hierarchy_diagnostics,
    }
    summary_json = stable_json(summary)
    report_md = render_report(summary, records)
    return BuildResult(records=records, jsonl=jsonl, summary_json=summary_json, report_md=report_md, diagnostics=summary)


def build() -> BuildResult:
    """Build all Consultant hierarchy artifacts in memory for the canonical fixture.

    Convenience wrapper that delegates to :func:`build_for_fixture` with the
    legacy ``CONS`` scope id so existing tests, downstream consumers, and the
    documented default behaviour (44-FZ-2026 only) are preserved.
    """

    return build_for_fixture(SOURCE_PATH, "CONS")


def build_corpus() -> BuildResult:
    """Build Consultant hierarchy records for all in-scope fixtures in the corpus.

    In-scope is defined by :data:`IN_SCOPE_DOCUMENT_TYPES` (currently
    ``federal_law`` and ``code`` — the source-roles with normative-act
    structure). Other roles (court decisions, antimonopoly decisions,
    government resolutions, lists, reviews, ODT) are documented as
    out-of-scope in the corpus report. The returned :class:`BuildResult`
    carries concatenated records across all in-scope fixtures plus a
    per-fixture summary and a scope statement.
    """

    inventory_path = ROOT / INVENTORY_PATH
    if not inventory_path.exists():
        return _corpus_fatal(("missing_inventory", f"inventory file missing: {INVENTORY_PATH}", str(INVENTORY_PATH)))

    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _corpus_fatal(("malformed_inventory_json", exc, str(INVENTORY_PATH)))

    fixtures = payload.get("fixtures", [])
    if not isinstance(fixtures, list):
        return _corpus_fatal(("inventory_shape_invalid", "Inventory fixtures must be a list.", str(INVENTORY_PATH)))

    in_scope_fixtures: list[dict[str, Any]] = []
    out_of_scope_by_role: dict[str, list[dict[str, Any]]] = {}
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            continue
        doc_type = fixture.get("document_type")
        if doc_type in IN_SCOPE_DOCUMENT_TYPES:
            in_scope_fixtures.append(fixture)
        else:
            out_of_scope_by_role.setdefault(doc_type or "unknown", []).append(fixture)

    all_records: list[dict[str, Any]] = []
    per_fixture_summaries: list[dict[str, Any]] = []
    fatal_errors: list[dict[str, Any]] = []

    for fixture in in_scope_fixtures:
        path_str = str(fixture.get("path", ""))
        scope_id = _derive_scope_id(path_str)
        fixture_result = build_for_fixture(Path(path_str), scope_id)
        if fixture_result.diagnostics.get("fatal_error_count", 0) > 0:
            fatal_errors.extend(fixture_result.diagnostics["fatal_errors"])
            continue
        if fixture_result.diagnostics.get("malformed_xml") is not None:
            fatal_errors.append(
                compact_error(
                    "fixture_malformed",
                    f"fixture {path_str} produced malformed XML",
                    path=path_str,
                )
            )
            continue
        all_records.extend(fixture_result.records)
        per_fixture_summaries.append(
            {
                "scope_id": scope_id,
                "path": path_str,
                "document_type": fixture.get("document_type"),
                "record_count": len(fixture_result.records),
                "emitted_counts_by_level": fixture_result.diagnostics.get("emitted_counts_by_level", {}),
                "source_sha256": fixture_result.diagnostics.get("source", {}).get("sha256"),
                "structural_error_count": fixture_result.diagnostics.get("structural_error_count", 0),
            }
        )

    # Verify id uniqueness across the concatenated corpus.
    record_ids = [record["id"] for record in all_records]
    id_collisions: list[dict[str, Any]] = []
    if len(record_ids) != len(set(record_ids)):
        seen: set[str] = set()
        for record_id in record_ids:
            if record_id in seen and record_id not in {c["id"] for c in id_collisions}:
                id_collisions.append({"id": record_id})
            seen.add(record_id)

    out_of_scope_breakdown = [
        {
            "document_type": doc_type,
            "fixture_count": len(roles_fixtures),
            "reason": _scope_reason_for(doc_type),
        }
        for doc_type, roles_fixtures in sorted(out_of_scope_by_role.items())
    ]

    corpus_jsonl = "".join(dumps_jsonl_record(record) + "\n" for record in all_records)
    corpus_summary = {
        "schema_version": "consultant-hierarchy-corpus/v1",
        "phase": "consultant_wordml_hierarchy_corpus_build",
        "non_authoritative": True,
        "non_claims": [
            "Consultant hierarchy corpus records are deterministic parser-source records only.",
            "The corpus does not claim legal correctness or authoritative legal interpretation.",
            "The corpus does not claim parser completeness for non-in-scope document kinds.",
            "The corpus does not claim product ETL or FalkorDB load readiness.",
            "Out-of-scope fixtures are documented but not silently skipped — they remain on disk awaiting a later scope expansion.",
        ],
        "in_scope_document_types": list(IN_SCOPE_DOCUMENT_TYPES),
        "in_scope_fixtures": per_fixture_summaries,
        "out_of_scope": out_of_scope_breakdown,
        "totals": {
            "in_scope_fixture_count": len(per_fixture_summaries),
            "out_of_scope_fixture_count": sum(item["fixture_count"] for item in out_of_scope_breakdown),
            "record_count": len(all_records),
            "unique_record_id_count": len(set(record_ids)),
            "id_collision_count": len(id_collisions),
        },
        "id_collisions": id_collisions[:MAX_DIAGNOSTICS],
        "artifact_paths": {
            "json": str(JSON_PATH),
            "jsonl": str(JSONL_PATH),
            "report": str(REPORT_PATH),
        },
        "fatal_errors": fatal_errors[:MAX_DIAGNOSTICS],
        "fatal_error_count": len(fatal_errors),
    }
    corpus_json = stable_json(corpus_summary)
    corpus_md = render_corpus_report(corpus_summary, all_records, per_fixture_summaries)
    return BuildResult(
        records=all_records,
        jsonl=corpus_jsonl,
        summary_json=corpus_json,
        report_md=corpus_md,
        diagnostics=corpus_summary,
    )


def _scope_reason_for(document_type: str) -> str:
    """Return a one-line human-readable reason for a document_type being out of scope."""

    out_of_scope_reasons = {
        "code_amendment_overview": "Amendment overview; not a full normative-act source-shape.",
        "court_practice_review": "Court practice review; not a full normative-act source-shape.",
        "fas_review": "FAS / Treasury review; not a full normative-act source-shape.",
        "government_resolution": "Government resolution; structure is non-hierarchical for M072 S05 scope.",
        "constitutional_court_ruling": "Court ruling; treated as citation-evidence, not a full hierarchy.",
        "supreme_court_ruling": "Court ruling; treated as citation-evidence, not a full hierarchy.",
        "lower_court_ruling": "Lower court ruling; treated as citation-evidence, not a full hierarchy.",
        "antimonopoly_decision": "Antimonopoly decision; non-hierarchical structure for S05 scope.",
        "document_list": "Document list (relation candidate, not hierarchy).",
        "other_document": "Unclassified title; not a full normative-act source-shape.",
        "odt_document": "Garant ODT fixture; covered by separate ODT smoke path, not by Consultant parser.",
    }
    return out_of_scope_reasons.get(
        document_type,
        "Out of scope for hierarchy extraction; reserved for a later scope expansion.",
    )


def _corpus_fatal(error_payload: tuple) -> BuildResult:
    """Build a fatal-only :class:`BuildResult` for a corpus that cannot even start."""

    fatal_error_count = 1
    fatal_errors = [compact_error(*error_payload)]
    summary = {
        "schema_version": "consultant-hierarchy-corpus/v1",
        "phase": "consultant_wordml_hierarchy_corpus_build",
        "non_authoritative": True,
        "in_scope_document_types": list(IN_SCOPE_DOCUMENT_TYPES),
        "in_scope_fixtures": [],
        "out_of_scope": [],
        "totals": {
            "in_scope_fixture_count": 0,
            "out_of_scope_fixture_count": 0,
            "record_count": 0,
            "unique_record_id_count": 0,
            "id_collision_count": 0,
        },
        "id_collisions": [],
        "artifact_paths": {
            "json": str(JSON_PATH),
            "jsonl": str(JSONL_PATH),
            "report": str(REPORT_PATH),
        },
        "fatal_errors": fatal_errors,
        "fatal_error_count": fatal_error_count,
    }
    return BuildResult(
        records=[],
        jsonl="",
        summary_json=stable_json(summary),
        report_md="",
        diagnostics=summary,
    )


def render_corpus_report(
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    per_fixture_summaries: list[dict[str, Any]],
) -> str:
    """Render a compact deterministic Markdown report for the corpus build."""

    totals = summary.get("totals", {})
    lines = [
        "# Consultant WordML Hierarchy Corpus (M072 S05)",
        "",
        "This artifact is deterministic parser evidence only. It is non-authoritative and does not claim legal correctness, parser completeness, product ETL readiness, or FalkorDB load readiness. Out-of-scope fixtures are documented below; they remain on disk awaiting a later scope expansion (no silent skipping).",
        "",
        "## Scope",
        "",
        f"- In-scope document types: `{', '.join(summary.get('in_scope_document_types', []))}`",
        f"- In-scope fixtures: `{totals.get('in_scope_fixture_count', 0)}`",
        f"- Out-of-scope fixtures: `{totals.get('out_of_scope_fixture_count', 0)}`",
        f"- Total records emitted: `{totals.get('record_count', 0)}`",
        f"- Unique record ids: `{totals.get('unique_record_id_count', 0)}`",
        f"- ID collisions: `{totals.get('id_collision_count', 0)}`",
        f"- Fatal errors: `{summary.get('fatal_error_count', 0)}`",
        "",
        "## In-scope per-fixture breakdown",
        "",
        "| Scope id | Source path | Document type | Records | Levels | SHA-256 |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for entry in per_fixture_summaries:
        levels = entry.get("emitted_counts_by_level", {}) or {}
        levels_compact = ", ".join(f"{k}={v}" for k, v in sorted(levels.items()))
        lines.append(
            f"| `{entry.get('scope_id')}` | `{entry.get('path')}` | `{entry.get('document_type')}` | {entry.get('record_count', 0)} | {levels_compact} | `{entry.get('source_sha256')}` |"
        )
    lines.extend(
        [
            "",
            "## Out-of-scope fixtures (documented, not silently skipped)",
            "",
            "| Document type | Fixture count | Reason |",
            "| --- | ---: | --- |",
        ]
    )
    for entry in summary.get("out_of_scope", []):
        lines.append(
            f"| `{entry['document_type']}` | {entry['fixture_count']} | {entry['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Non-claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in summary.get("non_claims", []))
    lines.append("")
    return "\n".join(lines)


def freshness_map(expected: dict[Path, str]) -> dict[str, bool]:
    """Return whether generated artifact content matches files on disk."""

    result: dict[str, bool] = {}
    for relative_path, content in expected.items():
        path = ROOT / relative_path
        result[str(relative_path)] = path.exists() and path.read_text(encoding="utf-8") == content
    return result


def render_report(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    """Render a compact deterministic Markdown diagnostic report."""

    counts = summary.get("emitted_counts_by_level", {})
    lines = [
        "# Consultant WordML hierarchy records",
        "",
        "This artifact is deterministic parser evidence only. It is non-authoritative and does not claim legal correctness, parser completeness, product ETL readiness, or FalkorDB load readiness.",
        "",
        "## Source",
        "",
        f"- Path: `{summary['source']['path']}`",
        f"- SHA-256: `{summary['source']['sha256']}`",
        f"- Inventory hash matches: `{str(summary['source']['inventory_hash_matches']).lower()}`",
        f"- WordML namespace detected: `{summary.get('namespace_detected')}`",
        "",
        "## Counts",
        "",
        f"- Source paragraphs: `{summary.get('paragraph_count')}`",
        f"- Empty paragraphs skipped: `{summary.get('skipped_empty_paragraphs')}`",
        f"- Records emitted: `{len(records)}`",
    ]
    for level, count in counts.items():
        lines.append(f"- `{level}`: `{count}`")
    lines.extend(
        [
            "",
            "## Diagnostics",
            "",
            f"- Malformed XML: `{summary.get('malformed_xml')}`",
            f"- Validation errors: `{summary.get('validation_error_count', 0)}`",
            f"- Structural errors: `{summary.get('structural_error_count', 0)}`",
            f"- Rejected context markers: `{summary.get('rejected_context_marker_count', 0)}`",
            f"- Fatal errors: `{summary.get('fatal_error_count', 0)}`",
            f"- Skipped marker counts: `{json.dumps(summary.get('skipped_marker_counts', {}), ensure_ascii=False, sort_keys=True)}`",
            f"- Style observations: `{json.dumps(summary.get('style_observations', {}), ensure_ascii=False, sort_keys=True)}`",
            "",
            "## First records",
            "",
        ]
    )
    for record in records[:10]:
        lines.append(f"- `{record['id']}` `{record['level']}` parent=`{record['parent_id']}` title={json.dumps(record['title'], ensure_ascii=False)}")
    lines.append("")
    return "\n".join(lines)


def write_artifacts(result: BuildResult) -> None:
    """Write generated artifacts deterministically."""

    for relative_path, content in {
        JSONL_PATH: result.jsonl,
        JSON_PATH: result.summary_json,
        REPORT_PATH: result.report_md,
    }.items():
        path = ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_artifacts(result: BuildResult) -> bool:
    """Return True when all generated artifacts are fresh."""

    expected = {JSONL_PATH: result.jsonl, JSON_PATH: result.summary_json, REPORT_PATH: result.report_md}
    return all((ROOT / path).exists() and (ROOT / path).read_text(encoding="utf-8") == content for path, content in expected.items())


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated artifacts are fresh without writing")
    parser.add_argument(
        "--corpus",
        action="store_true",
        help="build hierarchy records for all in-scope fixtures in the corpus (federal_law + code); default is the canonical 44-FZ-2026 fixture only.",
    )
    args = parser.parse_args(argv)

    if args.corpus:
        result = build_corpus()
    else:
        result = build()
    if result.diagnostics.get("fatal_error_count", 0):
        print(result.summary_json, end="")
        return 1
    if not args.corpus:
        # Single-fixture path keeps the legacy fail-closed checks; corpus
        # path only fails on fatal errors.
        if result.diagnostics.get("malformed_xml") is not None:
            print(result.summary_json, end="")
            return 1
        if result.diagnostics["source"]["inventory_hash_matches"] is not True:
            print(result.summary_json, end="")
            return 1
        if result.diagnostics.get("structural_error_count", 0):
            print(result.summary_json, end="")
            return 1
        if result.diagnostics.get("validation_error_count", 0):
            print(result.summary_json, end="")
            return 1
    else:
        if result.diagnostics.get("totals", {}).get("id_collision_count", 0) > 0:
            print(result.summary_json, end="")
            return 1
        if result.diagnostics.get("totals", {}).get("in_scope_fixture_count", 0) == 0:
            print(result.summary_json, end="")
            return 1

    if args.check:
        fresh = check_artifacts(result)
        output = dict(result.diagnostics)
        output["artifact_freshness"] = freshness_map({JSONL_PATH: result.jsonl, JSON_PATH: result.summary_json, REPORT_PATH: result.report_md})
        output["status"] = "pass" if fresh else "fail"
        print(stable_json(output), end="")
        return 0 if fresh else 1

    write_artifacts(result)
    output = dict(result.diagnostics)
    output["artifact_freshness"] = freshness_map({JSONL_PATH: result.jsonl, JSON_PATH: result.summary_json, REPORT_PATH: result.report_md})
    output["status"] = "pass"
    print(stable_json(output), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
