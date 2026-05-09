#!/usr/bin/env python3
"""Smoke-only raw ODT baseline probe for M001/S05.

This harness intentionally keeps raw source observations on Python stdlib so they do
not silently depend on odfpy, odfdo, lxml, PyYAML, network access, or product ETL
code. Optional parser probes are lazy, comparison-only observations: they diagnose
real parser behavior against the same ODT without making either parser a hidden
product dependency or authoritative legal evidence source.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
import tempfile
import textwrap
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
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
    gsd_root = ROOT / ".gsd"
    if gsd_root.exists():
        try:
            return f".gsd/{resolved.relative_to(gsd_root.resolve()).as_posix()}"
        except ValueError:
            pass
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


def exception_payload(exc: BaseException) -> dict[str, str]:
    return {
        "exception_class": exc.__class__.__name__,
        "exception_message": str(exc),
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
        error.update(exception_payload(exception))
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
            "Raw stdlib baseline only; optional parser direction is comparison evidence, not product ETL proof."
        ],
        "error": None,
    }


def optional_probe_base(parser: str, source: Path, status: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "owner": OWNER,
        "timestamp": utc_now(),
        "source": {"path": normalized_path(source)},
        "parser": parser,
        "status": status,
        "evidence_class": "parser-comparison-evidence",
        "issue_ids": [f"S05-optional-{parser}-{status}"],
        "parser_direction_claims_authoritative": False,
        "comparison_scope": "optional-parser-smoke-only",
    }


def remove_xml_doctype(payload: bytes) -> tuple[bytes, bool]:
    cleaned, count = re.subn(rb"<!DOCTYPE\s+[^>]*>\s*", b"", payload, count=1, flags=re.IGNORECASE | re.DOTALL)
    return cleaned, count > 0


def write_manifest_doctype_clean_copy(source: Path, target: Path) -> dict[str, Any]:
    """Copy an ODT while removing only META-INF/manifest.xml's DOCTYPE declaration."""
    removed_manifest_doctype = False
    manifest_seen = False
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(target, "w") as dst:
        for info in src.infolist():
            payload = src.read(info.filename)
            if info.filename == "META-INF/manifest.xml":
                manifest_seen = True
                payload, removed_manifest_doctype = remove_xml_doctype(payload)
            dst.writestr(info, payload)
    return {
        "source_path": normalized_path(source),
        "clean_copy_path": normalized_path(target),
        "manifest_seen": manifest_seen,
        "removed_manifest_doctype": removed_manifest_doctype,
        "controlled_mitigation": True,
        "source_mutated": False,
    }


def odfpy_probe(source: Path) -> dict[str, Any]:
    probe = optional_probe_base("odfpy", source, "pending")
    try:
        odf_open_document = importlib.import_module("odf.opendocument")
    except ModuleNotFoundError as exc:
        return probe | {"status": "not-installed", "issue_ids": ["S05-optional-odfpy-not-installed"], "error": exception_payload(exc)}

    load = getattr(odf_open_document, "load", None)
    if not callable(load):
        return probe | {
            "status": "api-incomplete",
            "issue_ids": ["S05-optional-odfpy-api-incomplete"],
            "observed_capabilities": {"has_load": False},
        }

    phases: dict[str, Any] = {}
    try:
        load(source)
    except Exception as exc:  # noqa: BLE001 - smoke probe must serialize parser exception class/message.
        phases["unmodified"] = {
            "status": "failed-unmodified-load",
            "phase": "unmodified",
            "error": exception_payload(exc),
        }
    else:
        phases["unmodified"] = {"status": "loaded-unmodified", "phase": "unmodified"}

    with tempfile.TemporaryDirectory(prefix="s05-odfpy-") as temp_dir:
        clean_path = Path(temp_dir) / source.name
        clean_info = write_manifest_doctype_clean_copy(source, clean_path)
        try:
            load(clean_path)
        except Exception as exc:  # noqa: BLE001 - smoke probe must serialize parser exception class/message.
            phases["temp-clean-manifest"] = clean_info | {
                "status": "failed-temp-clean-load",
                "phase": "temp-clean-manifest",
                "error": exception_payload(exc),
            }
        else:
            phases["temp-clean-manifest"] = clean_info | {
                "status": "loaded-temp-clean-manifest",
                "phase": "temp-clean-manifest",
            }

    if phases["unmodified"]["status"] == "loaded-unmodified":
        status = "loaded-unmodified"
    elif phases["temp-clean-manifest"]["status"] == "loaded-temp-clean-manifest":
        status = "loaded-temp-clean-manifest"
    else:
        status = "failed-temp-clean-load"
    return probe | {
        "status": status,
        "issue_ids": [f"S05-optional-odfpy-{status}"],
        "phases": phases,
        "comparison_summary": {
            "ordering_oracle": "raw-content-xml",
            "controlled_manifest_mitigation_only": True,
            "classified_as_final_etl_proof": False,
        },
    }


def first_callable(*candidates: Any) -> Callable[..., Any] | None:
    for candidate in candidates:
        if callable(candidate):
            return candidate
    return None


def call_optional(method: Callable[..., Any] | None) -> tuple[bool, Any]:
    if method is None:
        return False, None
    try:
        return True, method()
    except TypeError:
        return False, None
    except Exception as exc:  # noqa: BLE001 - capability probing must preserve parser behavior.
        return True, {"error": exception_payload(exc)}


def summarize_odfdo_document(document: Any, raw_result: dict[str, Any]) -> dict[str, Any]:
    body = getattr(document, "body", None)
    if body is None and callable(getattr(document, "get_body", None)):
        try:
            body = document.get_body()
        except Exception as exc:  # noqa: BLE001 - capability probing must preserve parser behavior.
            body = {"error": exception_payload(exc)}

    text_available, formatted_text = call_optional(
        first_callable(getattr(body, "get_formatted_text", None), getattr(document, "get_formatted_text", None))
    )
    tables_available, tables = call_optional(
        first_callable(getattr(body, "get_tables", None), getattr(document, "get_tables", None))
    )
    styles_attr = getattr(document, "styles", None)
    get_styles = getattr(document, "get_styles", None)
    styles_available = styles_attr is not None or callable(get_styles)

    table_count: int | None = None
    if isinstance(tables, (list, tuple)):
        table_count = len(tables)
    elif tables_available and tables is not None and not isinstance(tables, dict):
        try:
            table_count = len(tables)
        except TypeError:
            table_count = None

    text_char_count: int | None = None
    if isinstance(formatted_text, str):
        text_char_count = len(formatted_text)

    raw_observations = raw_result.get("raw_odt_observations", {})
    return {
        "ordering_oracle": "raw-content-xml",
        "forbidden_ordering_oracle": "odfpy-getElementsByType(P/H)",
        "ordered_text_available": isinstance(formatted_text, str),
        "ordered_text_char_count": text_char_count,
        "table_count_available": table_count is not None,
        "table_count": table_count,
        "style_metadata_available": styles_available,
        "table_metadata_available": tables_available,
        "raw_ordered_block_count": raw_observations.get("ordered_block_count"),
        "raw_table_count": raw_observations.get("table_count"),
    }


def odfdo_probe(source: Path, raw_result: dict[str, Any]) -> dict[str, Any]:
    probe = optional_probe_base("odfdo", source, "pending")
    try:
        odfdo_module = importlib.import_module("odfdo")
    except ModuleNotFoundError as exc:
        return probe | {"status": "not-installed", "issue_ids": ["S05-optional-odfdo-not-installed"], "error": exception_payload(exc)}

    document_class = getattr(odfdo_module, "Document", None)
    observed_capabilities = {
        "has_Document": callable(document_class),
        "module_attrs_sample": sorted(name for name in dir(odfdo_module) if not name.startswith("_"))[:20],
    }
    if not callable(document_class):
        return probe | {
            "status": "api-incomplete",
            "issue_ids": ["S05-optional-odfdo-api-incomplete"],
            "observed_capabilities": observed_capabilities,
        }

    try:
        document = document_class(source)
    except Exception as exc:  # noqa: BLE001 - smoke probe must serialize parser exception class/message.
        return probe | {
            "status": "failed-unmodified-load",
            "issue_ids": ["S05-optional-odfdo-failed-unmodified-load"],
            "phase": "unmodified",
            "observed_capabilities": observed_capabilities,
            "error": exception_payload(exc),
        }

    comparison_summary = summarize_odfdo_document(document, raw_result)
    status = (
        "loaded-unmodified"
        if comparison_summary["ordered_text_available"] or comparison_summary["table_count_available"]
        else "api-incomplete"
    )
    return probe | {
        "status": status,
        "issue_ids": [f"S05-optional-odfdo-{status}"],
        "phase": "unmodified",
        "observed_capabilities": observed_capabilities,
        "comparison_summary": comparison_summary,
    }


def probe_optional_parsers(source: Path, raw_result: dict[str, Any]) -> list[dict[str, Any]]:
    source = Path(source)
    return [odfpy_probe(source), odfdo_probe(source, raw_result)]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_cli_payload(result: dict[str, Any], optional_probes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    probes = [result, *(optional_probes or [])]
    statuses = {"raw-baseline": result["status"]}
    statuses.update({probe["parser"]: probe["status"] for probe in optional_probes or []})
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "probe_log_path": None,
        "probe_count": len(probes),
        "probes": probes,
        "statuses": statuses,
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
    parser.add_argument(
        "--include-optional-parsers",
        action="store_true",
        help="Run lazy odfpy/odfdo comparison probes; raw baseline remains stdlib-only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = probe_raw_odt(args.source, allow_fixture_source=args.allow_fixture_source)
    optional_probes = probe_optional_parsers(args.source, result) if args.include_optional_parsers else []
    payload = build_cli_payload(result, optional_probes)
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
