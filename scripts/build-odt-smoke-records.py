#!/usr/bin/env python3
# ruff: noqa: E402,I001
"""Build deterministic smoke parser records from canonical Garant ODT fixtures.

This is a bounded contract generator, not a production parser. It reads raw
``content.xml`` order with Python stdlib only and emits S02-valid records for
fixture integration checks. The records are non-authoritative and do not prove
parser completeness, legal correctness, product ETL readiness, FalkorDB
readiness, legal answers, or citation-safe retrieval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.parser_records import MAX_EXCERPT_CHARS, dumps_jsonl_record, parse_parser_record  # noqa: E402

INVENTORY_PATH = Path("prd/parser/source_fixture_inventory.json")
DEFAULT_OUTPUT_DIR = Path("prd/parser")
DOCUMENT_JSONL = "odt_document_records.jsonl"
SOURCE_BLOCK_JSONL = "odt_source_block_records.jsonl"
REPORT_JSON = "odt_smoke_records.json"
REPORT_MD = "odt_smoke_records.md"
SCHEMA_VERSION = "legalgraph-odt-smoke-records/v1"
MAX_BLOCKS_PER_DOCUMENT = 24
CONTENT_MEMBER = "content.xml"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"

DOC_IDS_BY_PATH = {
    "law-source/garant/44-fz.odt": "DOC-44-FZ",
    "law-source/garant/PP_60_27-01-2022.odt": "DOC-PP-60",
}

NON_CLAIMS = [
    "This S03 smoke record does not claim parser completeness.",
    "This S03 smoke record does not claim legal correctness or authoritative legal interpretation.",
    "This S03 smoke record does not claim product ETL readiness.",
    "This S03 smoke record does not claim FalkorDB readiness or legal-answer support.",
]

ALLOWED_FIELDS_BY_KIND = {
    "document": {
        "schema_version",
        "id",
        "source_kind",
        "source_path",
        "source_sha256",
        "non_authoritative",
        "non_claims",
        "record_kind",
        "title",
    },
    "source_block": {
        "schema_version",
        "id",
        "source_kind",
        "source_path",
        "source_sha256",
        "non_authoritative",
        "non_claims",
        "record_kind",
        "document_id",
        "source_member",
        "order_index",
        "location",
        "excerpt",
        "excerpt_sha256",
    },
}


@dataclass(frozen=True)
class RawBlock:
    """One heading/paragraph observation in raw content.xml traversal order."""

    order_index: int
    kind: str
    text: str
    style_name: str | None
    outline_level: str | None


@dataclass
class FixtureResult:
    """Generated records and diagnostics for one canonical ODT fixture."""

    status: str
    source_path: str
    document_id: str
    document_record: dict[str, Any] | None = None
    source_block_records: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    raw_block_count: int = 0
    emitted_block_count: int = 0
    table_count: int = 0
    source_sha256: str | None = None
    truncated: bool = False


@dataclass
class BuildResult:
    """Complete generator output for all canonical ODT fixtures."""

    document_records: list[dict[str, Any]]
    source_block_records: list[dict[str, Any]]
    report: dict[str, Any]
    markdown: str
    diagnostics: list[dict[str, Any]]


def repo_path(path: Path, root: Path = ROOT) -> str:
    """Return a stable repository-relative POSIX path when possible."""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    """Hash a file without loading it all into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    """Return the SHA-256 hex digest for UTF-8 text."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def namespaced(name: str, namespace: str) -> str:
    """Build an ElementTree namespaced tag/attribute name."""

    return f"{{{namespace}}}{name}"


def flatten_text(element: ElementTree.Element) -> str:
    """Collapse all text descendants into one whitespace-normalized string."""

    return " ".join("".join(element.itertext()).split())


def bounded_text(value: str, limit: int) -> str:
    """Return a deterministic prefix bounded to a parser-record field limit."""

    return value[:limit]


def diagnostic(source_path: str, rule: str, message: str, **extra: Any) -> dict[str, Any]:
    """Create compact deterministic CLI/test diagnostics."""

    payload: dict[str, Any] = {
        "source_path": source_path,
        "rule": rule,
        "message": message,
    }
    payload.update(extra)
    return payload


def count_tables(root: ElementTree.Element) -> int:
    """Count raw ODT table elements for report diagnostics."""

    return sum(1 for _ in root.iter(namespaced("table", TABLE_NS)))


def iter_raw_blocks(root: ElementTree.Element) -> list[RawBlock]:
    """Traverse heading and paragraph elements in raw content.xml order."""

    style_attr = namespaced("style-name", TEXT_NS)
    outline_attr = namespaced("outline-level", TEXT_NS)
    blocks: list[RawBlock] = []
    raw_index = 0
    for element in root.iter():
        if element.tag == namespaced("h", TEXT_NS):
            kind = "heading"
        elif element.tag == namespaced("p", TEXT_NS):
            kind = "paragraph"
        else:
            continue
        blocks.append(
            RawBlock(
                order_index=raw_index,
                kind=kind,
                text=flatten_text(element),
                style_name=element.attrib.get(style_attr),
                outline_level=element.attrib.get(outline_attr),
            )
        )
        raw_index += 1
    return blocks


def read_content_xml(source: Path, source_path: str) -> tuple[bytes | None, list[dict[str, Any]]]:
    """Read content.xml bytes from an ODT ZIP or return one diagnostic."""

    try:
        with zipfile.ZipFile(source) as zf:
            if CONTENT_MEMBER not in zf.namelist():
                return None, [
                    diagnostic(
                        source_path,
                        "missing-content-xml",
                        "ODT package is missing content.xml.",
                        source_member=CONTENT_MEMBER,
                    )
                ]
            return zf.read(CONTENT_MEMBER), []
    except zipfile.BadZipFile as exc:
        return None, [diagnostic(source_path, "invalid-zip", "Source is not a valid ODT ZIP package.", error=str(exc))]
    except OSError as exc:
        return None, [diagnostic(source_path, "read-error", "Failed to read ODT package.", error=str(exc))]


def document_title(blocks: list[RawBlock], fallback: str) -> str:
    """Select a bounded deterministic title from the first non-empty raw block."""

    for block in blocks:
        if block.text:
            return bounded_text(block.text, 240)
    return bounded_text(fallback, 240)


def block_id(document_id: str, emitted_index: int) -> str:
    """Build a stable source-block ID for an emitted block."""

    return f"BLOCK-{document_id.removeprefix('DOC-')}-{emitted_index:03d}"


def make_document_record(document_id: str, source_path: str, source_sha256: str, title: str) -> dict[str, Any]:
    """Build and validate one S02 document record."""

    payload = {
        "record_kind": "document",
        "id": document_id,
        "source_kind": "garant-odt",
        "source_path": source_path,
        "source_sha256": source_sha256,
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
        "title": title,
    }
    parse_parser_record(payload)
    return payload


def make_block_record(
    *,
    document_id: str,
    source_path: str,
    source_sha256: str,
    raw_block: RawBlock,
    emitted_index: int,
) -> dict[str, Any]:
    """Build and validate one S02 source-block record from a raw block."""

    excerpt = bounded_text(raw_block.text, MAX_EXCERPT_CHARS)
    label_parts = [raw_block.kind]
    if raw_block.outline_level:
        label_parts.append(f"outline={raw_block.outline_level}")
    if raw_block.style_name:
        label_parts.append(f"style={raw_block.style_name}")
    payload = {
        "record_kind": "source_block",
        "id": block_id(document_id, emitted_index),
        "source_kind": "garant-odt",
        "source_path": source_path,
        "source_sha256": source_sha256,
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
        "document_id": document_id,
        "source_member": CONTENT_MEMBER,
        "order_index": raw_block.order_index,
        "location": {
            "selector": f"content.xml#block[{raw_block.order_index}]",
            "label": "; ".join(label_parts),
        },
        "excerpt": excerpt,
        "excerpt_sha256": sha256_text(excerpt),
    }
    parse_parser_record(payload)
    return payload


def load_fixture(document_id: str, source_path: str, expected_sha256: str, root: Path = ROOT) -> FixtureResult:
    """Load one canonical ODT fixture and emit bounded S02 records."""

    source = root / source_path
    result = FixtureResult(status="pass", source_path=source_path, document_id=document_id)
    if not source.exists():
        result.status = "missing-canonical-path"
        result.diagnostics.append(diagnostic(source_path, "missing-canonical-path", "Canonical fixture path does not exist."))
        return result

    actual_sha256 = sha256_file(source)
    result.source_sha256 = actual_sha256

    content_xml, diagnostics = read_content_xml(source, source_path)
    if diagnostics:
        result.status = str(diagnostics[0]["rule"])
        result.diagnostics.extend(diagnostics)
        return result
    assert content_xml is not None

    try:
        root_element = ElementTree.fromstring(content_xml)
    except ElementTree.ParseError as exc:
        result.status = "xml-parse-error"
        result.diagnostics.append(
            diagnostic(
                source_path,
                "xml-parse-error",
                "Failed to parse content.xml with ElementTree.",
                source_member=CONTENT_MEMBER,
                error=str(exc),
            )
        )
        return result

    if actual_sha256 != expected_sha256:
        result.status = "fixture-mismatch"
        result.diagnostics.append(
            diagnostic(
                source_path,
                "fixture-mismatch",
                "Canonical fixture hash does not match source_fixture_inventory.json.",
                expected_sha256=expected_sha256,
                actual_sha256=actual_sha256,
            )
        )
        return result

    raw_blocks = iter_raw_blocks(root_element)
    result.raw_block_count = len(raw_blocks)
    result.table_count = count_tables(root_element)
    non_empty_blocks = [block for block in raw_blocks if block.text]
    emitted_blocks = non_empty_blocks[:MAX_BLOCKS_PER_DOCUMENT]
    result.emitted_block_count = len(emitted_blocks)
    result.truncated = len(non_empty_blocks) > len(emitted_blocks)

    try:
        result.document_record = make_document_record(
            document_id,
            source_path,
            actual_sha256,
            document_title(raw_blocks, Path(source_path).stem),
        )
        result.source_block_records = [
            make_block_record(
                document_id=document_id,
                source_path=source_path,
                source_sha256=actual_sha256,
                raw_block=block,
                emitted_index=index,
            )
            for index, block in enumerate(emitted_blocks)
        ]
    except Exception as exc:  # noqa: BLE001 - preserve validation class/message in CLI diagnostics.
        result.status = "record-validation-error"
        result.diagnostics.append(
            diagnostic(source_path, "record-validation-error", "S02 parser-record validation failed.", error=str(exc))
        )
        result.document_record = None
        result.source_block_records = []
    return result


def load_inventory(root: Path = ROOT) -> tuple[list[tuple[str, str, str]], list[dict[str, Any]]]:
    """Load exact canonical garant-odt fixtures from the S01 inventory."""

    path = root / INVENTORY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], [diagnostic(str(INVENTORY_PATH), "missing-inventory", "S01 fixture inventory does not exist.")]
    except json.JSONDecodeError as exc:
        return [], [diagnostic(str(INVENTORY_PATH), "inventory-json-invalid", "S01 fixture inventory is not valid JSON.", error=exc.msg)]

    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list):
        return [], [diagnostic(str(INVENTORY_PATH), "inventory-shape-invalid", "Inventory fixtures must be a list.")]

    by_path: dict[str, dict[str, Any]] = {}
    for fixture in fixtures:
        if isinstance(fixture, dict) and fixture.get("source_kind") == "garant-odt" and fixture.get("canonical") is True:
            path_value = fixture.get("path")
            if isinstance(path_value, str):
                by_path[path_value] = fixture

    selected: list[tuple[str, str, str]] = []
    diagnostics: list[dict[str, Any]] = []
    for source_path, document_id in DOC_IDS_BY_PATH.items():
        fixture = by_path.get(source_path)
        if fixture is None:
            diagnostics.append(
                diagnostic(source_path, "missing-canonical-path", "Canonical garant-odt path is missing from inventory.")
            )
            continue
        sha256_value = fixture.get("sha256")
        if not isinstance(sha256_value, str):
            diagnostics.append(diagnostic(source_path, "inventory-shape-invalid", "Fixture sha256 must be a string."))
            continue
        selected.append((document_id, source_path, sha256_value))
    return selected, diagnostics


def fixture_report_row(fixture: FixtureResult) -> dict[str, Any]:
    """Return deterministic per-fixture report diagnostics."""

    first_hash = None
    last_hash = None
    if fixture.source_block_records:
        first_hash = fixture.source_block_records[0]["excerpt_sha256"]
        last_hash = fixture.source_block_records[-1]["excerpt_sha256"]
    return {
        "id": fixture.document_id,
        "source_path": fixture.source_path,
        "status": fixture.status,
        "source_sha256": fixture.source_sha256,
        "raw_block_count": fixture.raw_block_count,
        "emitted_block_count": fixture.emitted_block_count,
        "table_count": fixture.table_count,
        "truncated": fixture.truncated,
        "first_emitted_excerpt_sha256": first_hash,
        "last_emitted_excerpt_sha256": last_hash,
    }


def build_report(fixtures: list[FixtureResult], artifact_freshness: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a deterministic compact report for CLI and JSON artifact output."""

    diagnostics = [diag for fixture in fixtures for diag in fixture.diagnostics]
    status = "pass" if not diagnostics else "fail"
    freshness = artifact_freshness or {"status": "not-checked", "stale_paths": []}
    if freshness.get("status") == "stale":
        status = "fail"
        diagnostics.extend(freshness.get("diagnostics", []))
    documents = [fixture for fixture in fixtures if fixture.document_record is not None]
    block_count = sum(len(fixture.source_block_records) for fixture in fixtures)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "scripts/build-odt-smoke-records.py",
        "status": status,
        "document_count": len(documents),
        "source_block_count": block_count,
        "max_blocks_per_document": MAX_BLOCKS_PER_DOCUMENT,
        "artifact_freshness": freshness,
        "diagnostics": diagnostics,
        "documents": [fixture_report_row(fixture) for fixture in fixtures],
        "non_authoritative": True,
        "non_claims": NON_CLAIMS,
        "downstream_boundary": "S03 emits bounded smoke parser records only; S05 owns later NetworkX/FalkorDB compatibility proof.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a bounded human-readable report artifact."""

    lines = [
        "# ODT Smoke Parser Records",
        "",
        f"- Status: `{report['status']}`",
        f"- Schema: `{report['schema_version']}`",
        f"- Generated by: `{report['generated_by']}`",
        f"- Document records: {report['document_count']}",
        f"- Source block records: {report['source_block_count']}",
        f"- Max blocks per document: {report['max_blocks_per_document']}",
        "- Ordering oracle: raw `content.xml` heading/paragraph traversal order.",
        "- Non-authoritative: true.",
        "",
        "## Documents",
        "",
        "| ID | Source path | Status | Raw blocks | Emitted blocks | Tables | Truncated | First emitted hash | Last emitted hash |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for document in report["documents"]:
        lines.append(
            "| {id} | `{source_path}` | `{status}` | {raw_block_count} | {emitted_block_count} | {table_count} | {truncated} | `{first_emitted_excerpt_sha256}` | `{last_emitted_excerpt_sha256}` |".format(
                **document
            )
        )
    lines.extend(["", "## Non-claims", ""])
    lines.extend(f"- {claim}" for claim in report["non_claims"])
    lines.extend(
        [
            "",
            "These artifacts are deterministic fixture-integration evidence only. They do not prove parser completeness, legal correctness, product ETL readiness, FalkorDB readiness, legal answers, or citation-safe retrieval.",
            "",
            "S05 may consume these records as bounded staging/debug inputs, but S05 owns later NetworkX/FalkorDB compatibility proof and any claim narrowing.",
            "",
            "## Diagnostics",
            "",
        ]
    )
    if report["diagnostics"]:
        lines.extend(f"- `{diag['rule']}` `{diag.get('source_path') or diag.get('path')}`: {diag['message']}" for diag in report["diagnostics"])
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def build_smoke_records(root: Path = ROOT, artifact_freshness: dict[str, Any] | None = None) -> BuildResult:
    """Build all canonical ODT smoke records and report data."""

    selected, inventory_diagnostics = load_inventory(root)
    fixtures: list[FixtureResult] = []
    for document_id, source_path, expected_sha256 in selected:
        fixtures.append(load_fixture(document_id, source_path, expected_sha256, root))
    if inventory_diagnostics:
        fixtures.append(
            FixtureResult(
                status="inventory-error",
                source_path=str(INVENTORY_PATH),
                document_id="DOC-INVENTORY",
                diagnostics=inventory_diagnostics,
            )
        )
    document_records = [fixture.document_record for fixture in fixtures if fixture.document_record is not None]
    source_block_records = [record for fixture in fixtures for record in fixture.source_block_records]
    report = build_report(fixtures, artifact_freshness)
    return BuildResult(
        document_records=document_records,
        source_block_records=source_block_records,
        report=report,
        markdown=render_markdown(report),
        diagnostics=report["diagnostics"],
    )


def jsonl_content(records: list[dict[str, Any]]) -> str:
    """Return deterministic JSONL bytes as text."""

    return "".join(f"{dumps_jsonl_record(record)}\n" for record in records)


def output_contents(result: BuildResult) -> dict[str, str]:
    """Return all deterministic artifact contents keyed by filename."""

    return {
        DOCUMENT_JSONL: jsonl_content(result.document_records),
        SOURCE_BLOCK_JSONL: jsonl_content(result.source_block_records),
        REPORT_JSON: json.dumps(result.report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        REPORT_MD: result.markdown,
    }


def write_outputs(result: BuildResult, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    """Write deterministic smoke artifacts to an output directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in output_contents(result).items():
        (output_dir / name).write_text(content, encoding="utf-8")


def check_outputs(output_dir: Path = DEFAULT_OUTPUT_DIR, root: Path = ROOT) -> BuildResult:
    """Build expected outputs and byte-compare against existing artifacts."""

    initial = build_smoke_records(root)
    expected = output_contents(initial)
    diagnostics: list[dict[str, Any]] = []
    stale_paths: list[str] = []
    for name, content in expected.items():
        path = output_dir / name
        stable_path = repo_path(path, root)
        if not path.exists():
            stale_paths.append(stable_path)
            diagnostics.append(diagnostic("", "stale-artifact", "Expected artifact is missing or stale.", path=stable_path))
            continue
        current = path.read_text(encoding="utf-8")
        if current != content:
            stale_paths.append(stable_path)
            diagnostics.append(diagnostic("", "stale-artifact", "Expected artifact is missing or stale.", path=stable_path))
    freshness = {
        "status": "pass" if not diagnostics else "stale",
        "stale_paths": stale_paths,
        "diagnostics": diagnostics,
    }
    return build_smoke_records(root, artifact_freshness=freshness)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write deterministic ODT smoke artifacts.")
    mode.add_argument("--check", action="store_true", help="Check artifacts are fresh and print compact JSON report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Artifact directory, default prd/parser.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.write:
        result = build_smoke_records(ROOT)
        write_outputs(result, args.output_dir)
    else:
        result = check_outputs(args.output_dir, ROOT)
    print(json.dumps(result.report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result.report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
