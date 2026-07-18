"""Consultant WordML source hierarchy record builder.

[bounded] M076 S04 adapter seam extracted from
``scripts/build-consultant-hierarchy-records.py``. This module converts already
normalized Consultant WordML paragraphs into deterministic, non-authoritative
parser-record dictionaries. It intentionally does not perform file I/O, corpus
selection, freshness checks, report rendering, graph writes, or legal semantic
validation.
"""

from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from law_nexus.ports.source_hierarchy import (
    RawBlock,
    SourceHierarchyParagraph,
    SourceHierarchyRequest,
    SourceHierarchyResult,
)

Level = Literal["document", "razdel", "chapter", "section", "article", "part", "clause", "subclause", "abzac"]
WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"
MAX_DIAGNOSTICS = 100
NON_CLAIMS = [
    "Consultant hierarchy records are deterministic parser-source records only.",
    "Consultant hierarchy records do not claim legal correctness or authoritative legal interpretation.",
    "Consultant hierarchy records do not claim parser completeness.",
    "Consultant hierarchy records do not claim product ETL or FalkorDB load readiness.",
]


@dataclass(frozen=True)
class Marker:
    """Detected hierarchy marker for a paragraph."""

    level: Level
    raw: str
    normalized: str
    kind: str


def sha256_text(text: str) -> str:
    """Return SHA-256 of text encoded as UTF-8."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    """Decode XML/html entities and collapse WordML whitespace deterministically."""

    decoded = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", decoded).strip()


def paragraph_style(elem: ET.Element) -> str | None:
    """Return the WordML paragraph style value if present."""

    style_tag = f"{{{WORDML_NS}}}pStyle"
    style_attr = f"{{{WORDML_NS}}}val"
    for child in elem.iter():
        if child.tag == style_tag:
            return child.attrib.get(style_attr) or child.attrib.get("val")
    return None


def stream_wordml_paragraphs(path: Path) -> tuple[list[RawBlock], dict[str, Any]]:
    """Stream WordML paragraphs while collecting bounded source diagnostics."""

    paragraphs: list[RawBlock] = []
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
                    paragraphs.append(
                        RawBlock(
                            index=paragraph_count,
                            text=text,
                            style=style,
                            source_span=f"/w:wordDocument/w:body/w:p[{paragraph_count}]",
                        )
                    )
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

    match = re.match(r"^(Раздел\s+[IVX]+\.?)\s*(.+)$", text, flags=re.IGNORECASE)
    if match:
        normalized = re.sub(r"\s+", "", match.group(1)).rstrip(".").lower()
        return Marker("razdel", match.group(1), normalized, "razdel-roman-number")

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


def _document_hierarchy_id(scope_id: str) -> str:
    return f"HIER-{scope_id}-DOCUMENT"


def next_record_id(scope_id: str, counters: Counter[str], level: Level) -> str:
    """Return a stable record id for a hierarchy level occurrence."""

    if level == "document":
        return _document_hierarchy_id(scope_id)
    counters[level] += 1
    return f"HIER-{scope_id}-{level.upper()}-{counters[level]:04d}"


def parent_for_level(level: Level, context: dict[str, str | None]) -> str | None:
    """Choose the current legal-context parent for a new hierarchy record."""

    if level == "document":
        return None
    if level == "razdel":
        return context["document"]
    if level == "chapter":
        return context["razdel"] or context["document"]
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
        context.update(
            {
                "document": record_id,
                "razdel": None,
                "chapter": None,
                "section": None,
                "article": None,
                "part": None,
                "clause": None,
                "subclause": None,
            }
        )
    elif level == "razdel":
        context.update({"razdel": record_id, "chapter": None, "section": None, "article": None, "part": None, "clause": None, "subclause": None})
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
    paragraph_index: int,
    paragraph_text: str,
    paragraph_style: str | None,
    marker: Marker | None,
    parent_id: str | None,
    source_sha256: str,
    scope_id: str,
    document_id: str,
    source_path: str,
) -> dict[str, Any]:
    """Build one Consultant hierarchy parser record."""

    excerpt = truncate(paragraph_text, 500)
    return {
        "record_kind": "consultant_hierarchy",
        "schema_version": "legalgraph-parser-record/v1",
        "id": record_id,
        "document_id": document_id,
        "source_kind": "consultant-wordml-xml",
        "source_path": source_path,
        "source_sha256": source_sha256,
        "source_member": None,
        "order_index": paragraph_index,
        "parent_id": parent_id,
        "level": level,
        "marker": None
        if marker is None
        else {"raw": marker.raw, "normalized": marker.normalized, "kind": marker.kind},
        "title": marker_title(paragraph_text, marker),
        "location": {
            "selector": f"/w:wordDocument/w:body/w:p[{paragraph_index}]",
            "label": f"WordML paragraph {paragraph_index}" + (f" style {paragraph_style}" if paragraph_style else ""),
        },
        "excerpt": excerpt,
        "excerpt_sha256": sha256_text(excerpt),
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
    }


class ConsultantHierarchyRecordBuilder:
    """Build Consultant hierarchy records from normalized paragraphs."""

    def build_records(self, request: SourceHierarchyRequest) -> SourceHierarchyResult:
        """Extract hierarchy records using current-context boundaries, not global regex."""

        records, diagnostics = hierarchy_records(request)
        return SourceHierarchyResult(records=records, diagnostics=diagnostics)


def hierarchy_records(request: SourceHierarchyRequest) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract Consultant hierarchy records and diagnostics for ``request``."""

    paragraphs = list(request.paragraphs)
    document_hierarchy_id = _document_hierarchy_id(request.scope_id)
    records: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    rejected_context_markers: list[dict[str, Any]] = []
    context: dict[str, str | None] = {
        "document": document_hierarchy_id,
        "razdel": None,
        "chapter": None,
        "section": None,
        "article": None,
        "part": None,
        "clause": None,
        "subclause": None,
    }

    first_title = next((p for p in paragraphs if p.style == "5" and not p.text.startswith("iVBOR")), paragraphs[0])
    records.append(
        build_record(
            record_id=document_hierarchy_id,
            level="document",
            paragraph_index=first_title.index,
            paragraph_text=first_title.text,
            paragraph_style=first_title.style,
            marker=None,
            parent_id=None,
            source_sha256=request.source_sha256,
            scope_id=request.scope_id,
            document_id=request.document_id,
            source_path=request.source_path,
        )
    )

    for paragraph in paragraphs:
        marker = marker_for_text(paragraph.text)
        if marker is None:
            if context["article"] is not None:
                skipped["unnumbered_paragraphs_within_article"] += 1
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
                        "rule_id": "hierarchy_parent_required",
                        "reason": f"{marker.level}_without_parent",
                        "source_excerpt": excerpt,
                        "source_excerpt_sha256": sha256_text(excerpt),
                    }
                )
            continue
        record_id = next_record_id(request.scope_id, counters, marker.level)
        record = build_record(
            record_id=record_id,
            level=marker.level,
            paragraph_index=paragraph.index,
            paragraph_text=paragraph.text,
            paragraph_style=paragraph.style,
            marker=marker,
            parent_id=parent_id,
            source_sha256=request.source_sha256,
            scope_id=request.scope_id,
            document_id=request.document_id,
            source_path=request.source_path,
        )
        records.append(record)
        update_context(marker.level, record_id, context)

    emitted_counts = Counter(record["level"] for record in records)
    structural_errors: list[dict[str, Any]] = []
    if counters and emitted_counts.get("article", 0) == 0:
        structural_errors.append(
            {
                "kind": "missing_article_heading",
                "message": "hierarchy markers were detected but no article heading was emitted; lower-level legal context is unsafe",
                "emitted_counts_by_level": dict(sorted(emitted_counts.items())),
                "skipped_marker_counts": dict(sorted(skipped.items())),
            }
        )
    if skipped:
        for kind, count in sorted(skipped.items()):
            if kind == "unnumbered_paragraphs_within_article":
                continue  # diagnostic counter, not a structural error
            structural_errors.append({"kind": "context_break", "message": f"{kind}: {count}", "count": count})

    diagnostics = {
        "emitted_counts_by_level": dict(sorted(emitted_counts.items())),
        "skipped_marker_counts": dict(sorted(skipped.items())),
        "rejected_context_marker_count": len(rejected_context_markers),
        "rejected_context_markers": rejected_context_markers,
        "structural_errors": structural_errors[:MAX_DIAGNOSTICS],
        "structural_error_count": len(structural_errors),
        "validation_errors": [],
        "validation_error_count": 0,
    }
    return records, diagnostics
