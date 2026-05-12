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
DOCUMENT_ID = "DOC-CONS-44-FZ"
DOCUMENT_HIERARCHY_ID = "HIER-CONS-DOCUMENT"
MAX_DIAGNOSTICS = 100
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


def load_inventory_fixture() -> dict[str, Any]:
    """Load the canonical inventory entry for the Consultant full-act fixture."""

    payload = json.loads((ROOT / INVENTORY_PATH).read_text(encoding="utf-8"))
    for fixture in payload.get("fixtures", []):
        if fixture.get("path") == str(SOURCE_PATH):
            return fixture
    raise ValueError(f"canonical inventory fixture missing: {SOURCE_PATH}")


def next_record_id(counters: Counter[str], level: Level) -> str:
    """Return a stable record id for a hierarchy level occurrence."""

    if level == "document":
        return DOCUMENT_HIERARCHY_ID
    counters[level] += 1
    return f"HIER-CONS-{level.upper()}-{counters[level]:04d}"


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
) -> dict[str, Any]:
    """Build and validate one Consultant hierarchy parser record."""

    excerpt = truncate(paragraph.text, 500)
    payload: dict[str, Any] = {
        "record_kind": "consultant_hierarchy",
        "schema_version": "legalgraph-parser-record/v1",
        "id": record_id,
        "document_id": DOCUMENT_ID,
        "source_kind": "consultant-wordml-xml",
        "source_path": str(SOURCE_PATH),
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


def hierarchy_records(paragraphs: list[Paragraph], source_sha256: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract hierarchy records using current-context boundaries, not global regex."""

    records: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    validation_errors: list[dict[str, Any]] = []
    context: dict[str, str | None] = {
        "document": DOCUMENT_HIERARCHY_ID,
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
            record_id=DOCUMENT_HIERARCHY_ID,
            level="document",
            paragraph=document_paragraph,
            marker=None,
            parent_id=None,
            source_sha256=source_sha256,
        )
    )

    for paragraph in paragraphs:
        marker = marker_for_text(paragraph.text)
        if marker is None:
            continue
        parent_id = parent_for_level(marker.level, context)
        if parent_id is None:
            skipped[f"{marker.level}_without_parent"] += 1
            continue
        if marker.level in {"part", "clause", "subclause"} and context["article"] is None:
            skipped[f"{marker.level}_outside_article"] += 1
            continue
        record_id = next_record_id(counters, marker.level)
        try:
            record = build_record(
                record_id=record_id,
                level=marker.level,
                paragraph=paragraph,
                marker=marker,
                parent_id=parent_id,
                source_sha256=source_sha256,
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

    diagnostics = {
        "emitted_counts_by_level": dict(sorted(Counter(record["level"] for record in records).items())),
        "skipped_marker_counts": dict(sorted(skipped.items())),
        "validation_errors": validation_errors,
        "validation_error_count": len(validation_errors),
    }
    return records, diagnostics


def build() -> BuildResult:
    """Build all Consultant hierarchy artifacts in memory."""

    source = ROOT / SOURCE_PATH
    inventory_fixture = load_inventory_fixture()
    source_sha256 = sha256_bytes(source)
    inventory_sha256 = inventory_fixture.get("sha256")
    paragraphs, stream_diagnostics = stream_wordml_paragraphs(source)
    records, hierarchy_diagnostics = hierarchy_records(paragraphs, source_sha256) if stream_diagnostics["malformed_xml"] is None else ([], {})

    inventory_hash_matches = source_sha256 == inventory_sha256
    jsonl = "".join(dumps_jsonl_record(record) + "\n" for record in records)
    summary = {
        "artifact_paths": {
            "json": str(JSON_PATH),
            "jsonl": str(JSONL_PATH),
            "report": str(REPORT_PATH),
        },
        "artifact_freshness": None,
        "diagnostics_bounded": True,
        "non_authoritative": True,
        "phase": "consultant_wordml_hierarchy_build",
        "source": {
            "inventory_hash_matches": inventory_hash_matches,
            "inventory_sha256": inventory_sha256,
            "path": str(SOURCE_PATH),
            "sha256": source_sha256,
        },
        **stream_diagnostics,
        **hierarchy_diagnostics,
    }
    summary_json = stable_json(summary)
    report_md = render_report(summary, records)
    return BuildResult(records=records, jsonl=jsonl, summary_json=summary_json, report_md=report_md, diagnostics=summary)


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
    args = parser.parse_args(argv)

    result = build()
    if result.diagnostics.get("malformed_xml") is not None:
        print(result.summary_json, end="")
        return 1
    if result.diagnostics["source"]["inventory_hash_matches"] is not True:
        print(result.summary_json, end="")
        return 1
    if result.diagnostics.get("validation_error_count", 0):
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
