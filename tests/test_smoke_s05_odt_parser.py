from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/smoke-s05-odt-parser.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_s05_odt_parser", HARNESS_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_raw_fixture_preserves_ordered_blocks_and_counts_markers(tmp_path: Path) -> None:
    harness = load_harness()

    source = tmp_path / "fixture.odt"
    harness.write_test_odt_fixture(
        source,
        content_body="""
        <office:text>
          <text:h text:style-name="Heading_20_1">Статья 1</text:h>
          <text:p text:style-name="P1">Федеральный закон регулирует закупки.</text:p>
          <text:h text:style-name="Heading_20_2">Часть 1</text:h>
          <text:p text:style-name="P2"><text:span>Пункт 2</text:span> контракта.</text:p>
          <table:table table:name="T1"><table:table-row><table:table-cell><text:p>cell</text:p></table:table-cell></table:table-row></table:table>
          <text:p text:style-name="P2">Статья 2. Закон.</text:p>
        </office:text>
        """,
        manifest_doctype=True,
    )

    result = harness.probe_raw_odt(source, allow_fixture_source=True)

    assert result["status"] == "verified-source-evidence"
    assert result["manifest"]["has_doctype"] is True
    assert [block["kind"] for block in result["raw_odt_observations"]["ordered_blocks"][:4]] == [
        "heading",
        "paragraph",
        "heading",
        "paragraph",
    ]
    assert result["raw_odt_observations"]["style_counts"] == {
        "Heading_20_1": 1,
        "P1": 1,
        "Heading_20_2": 1,
        "P2": 2,
    }
    assert result["raw_odt_observations"]["table_count"] == 1
    assert result["raw_odt_observations"]["legal_markers"]["counts"]["статья"] == 2
    assert result["evidence_class"] == "verified-source-evidence"


def test_raw_missing_source_returns_structured_missing_source(tmp_path: Path) -> None:
    harness = load_harness()

    result = harness.probe_raw_odt(tmp_path / "missing.odt", allow_fixture_source=True)

    assert result["status"] == "missing-source"
    assert result["parser_direction_claims_authoritative"] is False
    assert result["error"]["message"] == "Source ODT file does not exist."


def test_raw_invalid_zip_returns_invalid_zip_status(tmp_path: Path) -> None:
    harness = load_harness()
    source = tmp_path / "invalid.odt"
    source.write_text("not a zip", encoding="utf-8")

    result = harness.probe_raw_odt(source, allow_fixture_source=True)

    assert result["status"] == "invalid-zip"
    assert result["source"]["sha256"]
    assert result["error"]["exception_class"] == "BadZipFile"


def test_raw_missing_content_xml_returns_malformed_odt(tmp_path: Path) -> None:
    harness = load_harness()
    source = tmp_path / "missing-content.odt"
    with zipfile.ZipFile(source, "w") as zf:
        zf.writestr("META-INF/manifest.xml", "<manifest:manifest xmlns:manifest='urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'/>")

    result = harness.probe_raw_odt(source, allow_fixture_source=True)

    assert result["status"] == "malformed-odt"
    assert result["package"]["has_content_xml"] is False
    assert result["error"]["xml_entry"] == "content.xml"


def test_raw_xml_parse_failure_preserves_package_metadata(tmp_path: Path) -> None:
    harness = load_harness()
    source = tmp_path / "bad-content.odt"
    with zipfile.ZipFile(source, "w") as zf:
        zf.writestr("META-INF/manifest.xml", "<manifest:manifest xmlns:manifest='urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'/>")
        zf.writestr("content.xml", "<office:document-content>")

    result = harness.probe_raw_odt(source, allow_fixture_source=True)

    assert result["status"] == "raw-xml-failed"
    assert result["package"]["has_content_xml"] is True
    assert result["package"]["content_xml_size_bytes"] > 0
    assert result["error"]["exception_class"] == "ParseError"


def test_raw_empty_document_body_is_a_bounded_success(tmp_path: Path) -> None:
    harness = load_harness()
    source = tmp_path / "empty.odt"
    harness.write_test_odt_fixture(source, content_body="<office:text/>")

    result = harness.probe_raw_odt(source, allow_fixture_source=True)

    assert result["status"] == "verified-source-evidence"
    assert result["raw_odt_observations"]["empty_document_body"] is True
    assert result["raw_odt_observations"]["ordered_block_count"] == 0


def test_raw_required_real_source_policy_rejects_fixture_without_bypass(tmp_path: Path) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    harness.write_test_odt_fixture(source, content_body="<office:text><text:p>test</text:p></office:text>")
    out = tmp_path / "probe.json"

    exit_code = harness.main(["--source", str(source), "--out", str(out)])

    assert exit_code == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["statuses"]["raw-baseline"] == "wrong-source"
    assert payload["probes"][0]["required_real_source"] == "law-source/garant/44-fz.odt"


def test_real_file_metadata_smoke(tmp_path: Path) -> None:
    harness = load_harness()
    source = ROOT / "law-source/garant/44-fz.odt"
    out = tmp_path / "real-probe.json"

    exit_code = harness.main(["--source", str(source), "--out", str(out)])

    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    result = payload["probes"][0]
    assert result["status"] == "verified-source-evidence"
    assert result["source"]["path"] == "law-source/garant/44-fz.odt"
    assert result["source"]["size_bytes"] > 0
    assert len(result["source"]["sha256"]) == 64
    assert result["package"]["content_xml_size_bytes"] > 0
    assert result["raw_odt_observations"]["ordered_block_examples"]
