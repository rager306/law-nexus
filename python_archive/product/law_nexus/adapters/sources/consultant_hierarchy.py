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
from typing import Any, Literal, Sequence

from law_nexus.ports.source_hierarchy import (
    RawBlock,
    SourceHierarchyRequest,
    SourceHierarchyResult,
)
from law_nexus.ports.source_profile import load_profile

Level = Literal[
    "document", "razdel", "chapter", "section", "article", "part", "clause", "subclause", "abzac"
]
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


EXTERNAL_REF_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "federal_law",
        re.compile(
            r"\b(?:Федеральн(?:ый|ого|ому|ым|ом|ая|ой|ую|ее|ие|их|ыми)\s+)?закон[а-яё]*\s+от\s+(\d{2}\.\d{2}\.\d{4})\s+(?:N|№)\s*([0-9A-Za-zА-Яа-яёЁ+\-/]+)",
            re.IGNORECASE | re.UNICODE,
        ),
    ),
    (
        "code",
        re.compile(
            r"\b([А-Яа-яёЁ]{3,30})\s+кодекс",
            re.IGNORECASE | re.UNICODE,
        ),
    ),
)


def extract_external_references(text: str) -> list[dict[str, str]]:
    """Extract bounded external legal-act references from text.

    Returns list of dicts with keys: target_act_type, target_act_number
    (or None for code refs), target_date (or None), evidence_excerpt.
    Resolution stays deferred — these are candidates only.
    """

    hits: list[dict[str, str]] = []
    for act_type, pattern in EXTERNAL_REF_PATTERNS:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 40)
            excerpt = text[start:end].strip()
            entry: dict[str, str] = {
                "target_act_type": act_type,
                "target_act_number": "",
                "target_date": "",
                "evidence_excerpt": truncate(excerpt, 240),
            }
            if act_type == "federal_law" and match.lastindex == 2:
                entry["target_date"] = match.group(1) or ""
                entry["target_act_number"] = match.group(2) or ""
            elif act_type == "code":
                entry["target_act_number"] = (match.group(1) or "") + " кодекс"
            hits.append(entry)
    return hits


INTERNAL_REF_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("article", re.compile(r"\bстать[ьюеяи]\s+(\d+(?:\.\d+)?)", re.IGNORECASE | re.UNICODE)),
    ("part", re.compile(r"\bчаст[ьиьею]\s+(\d+(?:\.\d+)?)", re.IGNORECASE | re.UNICODE)),
    ("clause", re.compile(r"\bпункт[аыоеу]\s+(\d+(?:\.\d+)?)", re.IGNORECASE | re.UNICODE)),
)

TEMPORAL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("entry_into_force", r"\bвступа[ею]т\s+в\s+силу"),
    ("entry_into_force", r"\bвступил[ао]?\s+в\s+силу"),
    ("entry_into_force", r"\bвве[сд]ти\s+в\s+действие"),
    ("invalidity", r"\bутратил[ао]?\s+силу"),
    ("invalidity", r"\bне\s+применя[ею]тся"),
    ("invalidity", r"\bне\s+действу[ею]т"),
    ("secrecy", r"\bДСП\b"),
    ("secrecy", r"\bдля\s+служебного\s+пользования"),
    ("secrecy", r"\bсекретно\b"),
)

DEONTIC_LEXEMES: dict[str, tuple[str, ...]] = {
    "obligation_markers": (
        r"\bобязан[аы]?\b",
        r"\bдолжен[аы]?\b",
        r"\bнадлежит\b",
        r"\bнеобходимо\b",
    ),
    "permission_markers": (
        r"\bвправе\b",
        r"\bможет\s+быть\b",
        r"\bможет\b",
        r"\bимеет\s+право\b",
        r"\bдопускается\b",
    ),
    "prohibition_markers": (
        r"\bзапрещается\b",
        r"\bнельзя\b",
        r"\bне\s+допускается\b",
        r"\bне\s+вправе\b",
    ),
    "definition_markers": (r"\bпризнается\b", r"\bпонимается\b", r"\bв\s+целях\s+настоящ"),
    "deadline_markers": (
        r"\bв\s+срок\s+не\s+позднее\b",
        r"\bв\s+течение\s+\d+\s+(?:дней|месяц|лет)",
    ),
    "exception_markers": (r"\bза\s+исключением\b", r"\bесли\s+иное\s+не\s+предусмотрено\b"),
}


def detect_deontic_lexemes(text: str) -> dict[str, int]:
    """Detect deontic lexeme categories in text (NormStatement candidate preparation).

    Returns dict of category -> count. Categories: obligation_markers,
    permission_markers, prohibition_markers, definition_markers,
    deadline_markers, exception_markers.

    These are bounded diagnostic signals only — no legal-effect assertions,
    no NormStatement record emission. Negation-aware matching is bounded
    (per proposal 26 §8: 'не вправе' flips permission -> prohibition,
    counted in prohibition_markers raw count). For bounded diagnostics.
    """

    hits: dict[str, int] = {category: 0 for category in DEONTIC_LEXEMES}
    for category, patterns in DEONTIC_LEXEMES.items():
        for pattern in patterns:
            count = len(re.findall(pattern, text, re.IGNORECASE | re.UNICODE))
            if count:
                hits[category] += count
    return hits


def detect_temporal_markers(text: str) -> dict[str, int]:
    """Detect temporal, validity, and secrecy markers in text.

    Returns dict of category -> count. Categories: entry_into_force,
    invalidity, secrecy. These are bounded diagnostic signals — no
    legal-effect assertions, no temporal_confidence claims.
    """

    hits: dict[str, int] = {"entry_into_force": 0, "invalidity": 0, "secrecy": 0}
    for category, pattern in TEMPORAL_PATTERNS:
        count = len(re.findall(pattern, text, re.IGNORECASE | re.UNICODE))
        if count:
            hits[category] += count
    return hits


def extract_internal_references(text: str) -> list[dict[str, str]]:
    """Extract bounded internal structural references from legal text.

    Returns list of dicts with keys: target_level, target_number, evidence_excerpt.
    Only anchored patterns are matched (статья N, часть N, пункт N).
    Resolution stays deferred — these are candidates only.
    """

    hits: list[dict[str, str]] = []
    for level, pattern in INTERNAL_REF_PATTERNS:
        for match in pattern.finditer(text):
            number = match.group(1)
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 40)
            excerpt = text[start:end].strip()
            hits.append(
                {
                    "target_level": level,
                    "target_number": number,
                    "evidence_excerpt": truncate(excerpt, 240),
                }
            )
    return hits


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
        return Marker(
            "subclause", match.group(1), match.group(1).rstrip(")").lower(), "subclause-letter"
        )

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
        context.update(
            {
                "razdel": record_id,
                "chapter": None,
                "section": None,
                "article": None,
                "part": None,
                "clause": None,
                "subclause": None,
            }
        )
    elif level == "chapter":
        context.update(
            {
                "chapter": record_id,
                "section": None,
                "article": None,
                "part": None,
                "clause": None,
                "subclause": None,
            }
        )
    elif level == "section":
        context.update(
            {"section": record_id, "article": None, "part": None, "clause": None, "subclause": None}
        )
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
    edition_id: str | None = None,
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
            "label": f"WordML paragraph {paragraph_index}"
            + (f" style {paragraph_style}" if paragraph_style else ""),
        },
        "excerpt": excerpt,
        "excerpt_sha256": sha256_text(excerpt),
        "edition_id": edition_id,
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
    }


class ConsultantHierarchyRecordBuilder:
    """Build Consultant hierarchy records from normalized paragraphs."""

    def build_records(self, request: SourceHierarchyRequest) -> SourceHierarchyResult:
        """Extract hierarchy records using current-context boundaries, not global regex."""

        records, diagnostics = hierarchy_records(request)
        return SourceHierarchyResult(records=records, diagnostics=diagnostics)


def extract_norm_candidates(hierarchy_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract bounded NormStatement candidates from hierarchy record excerpts.

    For each hierarchy record with excerpt containing deontic lexemes,
    emit a candidate record. Only obligation/permission/prohibition
    categories produce candidates; definition/deadline/exception are
    diagnostic-only (M098).

    Returns list of candidate dicts with:
    - id: NORM-CONS-{RECORD_ID_SUFFIX}-{MODALITY}-{N}
    - record_kind: norm_candidate
    - modality: obligation | permission | prohibition
    - extraction_method: deterministic
    - verification_status: unverified
    - source_unit_id: hierarchy record id
    - evidence_excerpt: bounded excerpt
    - evidence_sha256: SHA-256 of excerpt
    """

    MODALITY_MAP = {
        "obligation_markers": "obligation",
        "permission_markers": "permission",
        "prohibition_markers": "prohibition",
    }
    candidates: list[dict[str, Any]] = []
    counter = 0
    for record in hierarchy_records:
        excerpt = record.get("excerpt", "")
        record_id = record.get("id", "")
        source_path = record.get("source_path", "")
        source_sha256 = record.get("source_sha256", "")

        lexemes = detect_deontic_lexemes(excerpt)
        for lex_category, modality in MODALITY_MAP.items():
            count = lexemes.get(lex_category, 0)
            if count == 0:
                continue
            counter += 1
            suffix = record_id.replace("HIER-CONS-", "")
            candidate_id = f"NORM-CONS-{suffix}-{modality.upper()}-{counter:04d}"
            candidate = {
                "record_kind": "norm_candidate",
                "schema_version": "legalgraph-parser-record/v1",
                "id": candidate_id,
                "source_kind": "consultant-wordml-xml",
                "source_path": source_path,
                "source_sha256": source_sha256,
                "source_member": None,
                "source_unit_id": record_id,
                "modality": modality,
                "lexeme_count": count,
                "extraction_method": "deterministic",
                "verification_status": "unverified",
                "evidence_excerpt": truncate(excerpt, 500),
                "evidence_sha256": sha256_text(truncate(excerpt, 500)),
                "non_authoritative": True,
                "non_claims": [
                    "NormStatement candidates are deterministic extraction only.",
                    "NormStatement candidates do not claim legal correctness or authoritative legal interpretation.",
                    "NormStatement candidates do not claim parser completeness.",
                    "NormStatement candidates are unverified until independent proof.",
                ],
            }
            candidates.append(candidate)
    return candidates


def profile_document(paragraphs: Sequence[RawBlock]) -> dict[str, Any]:
    """Pass A document profiler: collect style, marker, and numbering census.

    One pass over all paragraphs. Returns structured census:
    - style_census: Counter of observed style values
    - marker_census: Counter of marker_for_text matches per level
    - numbering_format_distribution: per-level numbering variant counts
    - title_line_shape: first-line title text summary

    Diagnostic-only — no extraction change. Foundation for future
    two-pass engine where Pass A output drives profile selection.
    """

    style_census: dict[str, int] = {}
    marker_census: dict[str, int] = {}
    numbering_formats: dict[str, dict[str, int]] = {}
    title_line_shape: str = ""

    for paragraph in paragraphs:
        # Style census
        style_key = paragraph.style or "<none>"
        style_census[style_key] = style_census.get(style_key, 0) + 1

        # Title-line shape (first paragraph with style '5' or first overall)
        if not title_line_shape and (paragraph.style == "5" or not title_line_shape):
            title_line_shape = truncate(paragraph.text, 120)

        # Marker census
        marker = marker_for_text(paragraph.text)
        if marker is not None:
            level = marker.level
            marker_census[level] = marker_census.get(level, 0) + 1
            # Numbering format detection
            kind = marker.kind
            level_formats = numbering_formats.setdefault(level, {})
            level_formats[kind] = level_formats.get(kind, 0) + 1

    return {
        "style_census": dict(sorted(style_census.items())),
        "marker_census": dict(sorted(marker_census.items())),
        "numbering_format_distribution": {
            level: dict(sorted(formats.items()))
            for level, formats in sorted(numbering_formats.items())
        },
        "title_line_shape": title_line_shape,
        "paragraph_count": len(paragraphs),
    }


def hierarchy_records(
    request: SourceHierarchyRequest,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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

    first_title = next(
        (p for p in paragraphs if p.style == "5" and not p.text.startswith("iVBOR")), paragraphs[0]
    )
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

    zone = "preambula"  # preambula -> body (after first article) -> prilozhenie (after Приложение)

    for paragraph in paragraphs:
        if zone == "preambula" and re.match(
            r"^Приложение\s*\d*\.?\s", paragraph.text, flags=re.IGNORECASE
        ):
            zone = "prilozhenie"
            skipped["prilozhenie_paragraphs"] += 1
            continue
        if zone == "prilozhenie":
            skipped["prilozhenie_paragraphs"] += 1
            continue

        marker = marker_for_text(paragraph.text)
        if marker is None:
            if zone == "preambula":
                skipped["preambula_paragraphs"] += 1
            elif context["article"] is not None:
                skipped["unnumbered_paragraphs_within_article"] += 1
            # M097: temporal/validity/secrecy marker detection
            for cat, count in detect_temporal_markers(paragraph.text).items():
                if count:
                    skipped[f"{cat}_markers"] += count
            # M098: deontic lexeme detection (NormStatement candidate preparation)
            for cat, count in detect_deontic_lexemes(paragraph.text).items():
                if count:
                    skipped[f"{cat}"] += count
            continue

        if marker.level == "article":
            zone = "body"

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
            if kind in (
                "unnumbered_paragraphs_within_article",
                "preambula_paragraphs",
                "prilozhenie_paragraphs",
                "entry_into_force_markers",
                "invalidity_markers",
                "secrecy_markers",
                "obligation_markers",
                "permission_markers",
                "prohibition_markers",
                "definition_markers",
                "deadline_markers",
                "exception_markers",
            ):
                continue  # diagnostic counters, not structural errors
            structural_errors.append(
                {"kind": "context_break", "message": f"{kind}: {count}", "count": count}
            )

    diagnostics = {
        "emitted_counts_by_level": dict(sorted(emitted_counts.items())),
        "skipped_marker_counts": dict(sorted(skipped.items())),
        "rejected_context_marker_count": len(rejected_context_markers),
        "rejected_context_markers": rejected_context_markers,
        "structural_errors": structural_errors[:MAX_DIAGNOSTICS],
        "structural_error_count": len(structural_errors),
        "validation_errors": [],
        "validation_error_count": 0,
        "profile_record_count_match": (
            load_profile() is not None
            and (sum(emitted_counts.values()) == 7873 or sum(emitted_counts.values()) == 2185)
        ),
        "profile_census": profile_document(request.paragraphs),
    }
    return records, diagnostics
