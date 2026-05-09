#!/usr/bin/env python3
"""Smoke-only raw ODT baseline probe for M001/S05.

This harness intentionally uses only Python stdlib so raw source observations do not
silently depend on odfpy, odfdo, lxml, PyYAML, network access, or product ETL code.
It inspects an ODT as a ZIP package, parses only content.xml with ElementTree, and
emits structured evidence/error payloads for future parser comparison tasks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import textwrap
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "law-source/garant/44-fz.odt"
SCHEMA_VERSION = "s05-raw-odt-baseline/v1"
OWNER = "S05"
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_CONTENT_XML_BYTES = 20 * 1024 * 1024
BLOCK_EXAMPLE_LIMIT = 12
MARKER_EXAMPLE_LIMIT = 5

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
MANIFEST_NS = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"

NAMESPACES = {
    "text": TEXT_NS,
    "office": OFFICE_NS,
    "table": TABLE_NS,
    "manifest": MANIFEST_NS,
}

LEGAL_MARKERS = (
    "статья",
    "часть",
    "пункт",
    "закон",
    "контракт",
    "закупк",
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": normalized_path(path),
        "resolved_path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "sha256": sha256_file(path),
        "is_default_real_source": path.resolve() == DEFAULT_SOURCE.resolve(),
    }


def namespaced(name: str, namespace: str) -> str:
    return f"{{{namespace}}}{name}"


def flatten_text(element: ElementTree.Element) -> str:
    text = "".join(element.itertext())
    return " ".join(text.split())


def detect_doctype(payload: bytes) -> dict[str, Any]:
    prefix = payload[:1024].decode("utf-8", errors="ignore")
    return {
        "has_doctype": "<!DOCTYPE" in prefix.upper(),
        "prefix_sample": prefix[:160],
    }


def package_entries(zf: zipfile.ZipFile) -> list[dict[str, Any]]:
    return [
        {
            "name": info.filename,
            "compressed_size": info.compress_size,
            "uncompressed_size": info.file_size,
            "is_dir": info.is_dir(),
        }
        for info in zf.infolist()
    ]


def count_tables(root: ElementTree.Element) -> int:
    return sum(1 for _ in root.iter(namespaced("table", TABLE_NS)))


def iter_heading_paragraph_blocks(root: ElementTree.Element) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    style_attr = namespaced("style-name", TEXT_NS)
    outline_attr = namespaced("outline-level", TEXT_NS)
    for element in root.iter():
        if element.tag == namespaced("h", TEXT_NS):
            kind = "heading"
        elif element.tag == namespaced("p", TEXT_NS):
            kind = "paragraph"
        else:
            continue
        text = flatten_text(element)
        blocks.append(
            {
                "index": len(blocks),
                "kind": kind,
                "style_name": element.attrib.get(style_attr),
                "outline_level": element.attrib.get(outline_attr),
                "text": text,
                "char_count": len(text),
            }
        )
    return blocks


def count_styles(blocks: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for block in blocks:
        style_name = block.get("style_name")
        if isinstance(style_name, str) and style_name:
            counts[style_name] += 1
    return dict(sorted(counts.items()))


def legal_marker_observations(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = {marker: [] for marker in LEGAL_MARKERS}
    for block in blocks:
        text = str(block.get("text", ""))
        lower_text = text.lower()
        for marker in LEGAL_MARKERS:
            count = lower_text.count(marker)
            if count == 0:
                continue
            counts[marker] += count
            if len(examples[marker]) < MARKER_EXAMPLE_LIMIT:
                examples[marker].append(
                    {
                        "block_index": block["index"],
                        "kind": block["kind"],
                        "text": text[:240],
                    }
                )
    return {
        "counts": dict(sorted(counts.items())),
        "examples": {marker: value for marker, value in examples.items() if value},
    }


def failure_result(
    status: str,
    source: Path,
    message: str,
    *,
    source_meta: dict[str, Any] | None = None,
    package_meta: dict[str, Any] | None = None,
    xml_entry: str | None = None,
    exception: BaseException | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "message": message,
        "xml_entry": xml_entry,
    }
    if exception is not None:
        error.update(
            {
                "exception_class": exception.__class__.__name__,
                "exception_message": str(exception),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "owner": OWNER,
        "timestamp": utc_now(),
        "source": source_meta or {"path": normalized_path(source)},
        "status": status,
        "evidence_class": "parser-error" if status != "wrong-source" else "policy-error",
        "issue_ids": [f"S05-{status}"],
        "required_real_source": normalized_path(DEFAULT_SOURCE),
        "package": package_meta or {},
        "raw_odt_observations": {},
        "parser_direction_claims_authoritative": False,
        "error": error,
    }


def probe_raw_odt(source: Path, *, allow_fixture_source: bool = False) -> dict[str, Any]:
    source = Path(source)
    if not allow_fixture_source and source.resolve() != DEFAULT_SOURCE.resolve():
        return failure_result(
            "wrong-source",
            source,
            "Required real-source runs must use law-source/garant/44-fz.odt; pass "
            "--allow-fixture-source only for tests/fixtures.",
        )
    if not source.exists():
        return failure_result("missing-source", source, "Source ODT file does not exist.")
    source_meta = source_metadata(source)
    if int(source_meta["size_bytes"]) > MAX_SOURCE_BYTES:
        return failure_result(
            "source-too-large",
            source,
            f"Source exceeds bounded smoke limit of {MAX_SOURCE_BYTES} bytes.",
            source_meta=source_meta,
        )

    try:
        with zipfile.ZipFile(source) as zf:
            entries = package_entries(zf)
            package_meta: dict[str, Any] = {
                "entry_count": len(entries),
                "entries": entries,
                "has_content_xml": "content.xml" in zf.namelist(),
                "has_manifest_xml": "META-INF/manifest.xml" in zf.namelist(),
            }
            if "content.xml" not in zf.namelist():
                return failure_result(
                    "malformed-odt",
                    source,
                    "ODT package is missing content.xml.",
                    source_meta=source_meta,
                    package_meta=package_meta,
                    xml_entry="content.xml",
                )
            if package_meta["has_manifest_xml"]:
                manifest_payload = zf.read("META-INF/manifest.xml")
                manifest = {
                    **detect_doctype(manifest_payload),
                    "size_bytes": len(manifest_payload),
                }
            else:
                manifest = {
                    "has_doctype": False,
                    "prefix_sample": "",
                    "size_bytes": 0,
                    "missing": True,
                }
            content_payload = zf.read("content.xml")
            package_meta["content_xml_size_bytes"] = len(content_payload)
            if len(content_payload) > MAX_CONTENT_XML_BYTES:
                return failure_result(
                    "content-xml-too-large",
                    source,
                    f"content.xml exceeds bounded smoke limit of {MAX_CONTENT_XML_BYTES} bytes.",
                    source_meta=source_meta,
                    package_meta=package_meta,
                    xml_entry="content.xml",
                )
    except zipfile.BadZipFile as exc:
        return failure_result(
            "invalid-zip",
            source,
            "Source is not a valid zip/ODT package.",
            source_meta=source_meta,
            exception=exc,
        )
    except OSError as exc:
        return failure_result(
            "source-read-failed",
            source,
            "Failed to read source package.",
            source_meta=source_meta,
            exception=exc,
        )

    try:
        root = ElementTree.fromstring(content_payload)
    except ElementTree.ParseError as exc:
        return failure_result(
            "raw-xml-failed",
            source,
            "Failed to parse content.xml with Python stdlib ElementTree.",
            source_meta=source_meta,
            package_meta=package_meta,
            xml_entry="content.xml",
            exception=exc,
        )

    blocks = iter_heading_paragraph_blocks(root)
    observations = {
        "content_xml_size_bytes": package_meta["content_xml_size_bytes"],
        "ordered_block_count": len(blocks),
        "ordered_blocks": blocks,
        "ordered_block_examples": blocks[:BLOCK_EXAMPLE_LIMIT],
        "style_counts": count_styles(blocks),
        "table_count": count_tables(root),
        "legal_markers": legal_marker_observations(blocks),
        "empty_document_body": len(blocks) == 0,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "owner": OWNER,
        "timestamp": utc_now(),
        "source": source_meta,
        "status": "verified-source-evidence",
        "evidence_class": "verified-source-evidence",
        "issue_ids": ["S05-raw-odt-baseline"],
        "required_real_source": normalized_path(DEFAULT_SOURCE),
        "package": package_meta,
        "manifest": manifest,
        "raw_odt_observations": observations,
        "parser_direction_claims_authoritative": False,
        "future_direction_notes": [
            "Raw stdlib baseline only; optional parser direction is intentionally deferred to later S05 probes."
        ],
        "error": None,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_cli_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "probe_log_path": None,
        "probes": [result],
        "statuses": {"raw-baseline": result["status"]},
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="ODT source path.")
    parser.add_argument("--out", type=Path, required=True, help="JSON output path for probe log.")
    parser.add_argument("--format", choices=("json",), default="json", help="Output format.")
    parser.add_argument(
        "--allow-fixture-source",
        action="store_true",
        help="Permit non-law-source/garant/44-fz.odt sources for tests/fixtures only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = probe_raw_odt(args.source, allow_fixture_source=args.allow_fixture_source)
    payload = build_cli_payload(result)
    out_path = args.out
    write_json(out_path, payload | {"probe_log_path": normalized_path(out_path)})
    if result["status"] == "verified-source-evidence":
        return 0
    print(f"S05 raw ODT probe failed: {result['status']}: {result['error']['message']}", file=sys.stderr)
    return 1


def write_test_odt_fixture(source: Path, *, content_body: str, manifest_doctype: bool = False) -> None:
    """Create a minimal ODT package for pytest fixtures.

    This helper is intentionally in the harness so tests exercise the same namespace
    constants as the parser while still using inline synthetic content.
    """
    source.parent.mkdir(parents=True, exist_ok=True)
    manifest_doctype_text = (
        '<!DOCTYPE manifest:manifest PUBLIC "-//OpenOffice.org//DTD Manifest 1.0//EN" "Manifest.dtd">\n'
        if manifest_doctype
        else ""
    )
    manifest = f"""<?xml version="1.0" encoding="UTF-8"?>
{manifest_doctype_text}<manifest:manifest xmlns:manifest="{MANIFEST_NS}">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="{OFFICE_NS}"
  xmlns:text="{TEXT_NS}"
  xmlns:table="{TABLE_NS}">
  <office:body>
    {textwrap.dedent(content_body).strip()}
  </office:body>
</office:document-content>
"""
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/manifest.xml", manifest)
        zf.writestr("content.xml", content)


if __name__ == "__main__":
    raise SystemExit(main())
