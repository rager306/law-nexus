from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

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


def test_optional_parsers_are_not_run_unless_requested(tmp_path: Path) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    out = tmp_path / "probe.json"
    harness.write_test_odt_fixture(source, content_body="<office:text><text:p>test</text:p></office:text>")

    exit_code = harness.main(
        ["--source", str(source), "--allow-fixture-source", "--out", str(out)]
    )

    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["statuses"] == {"raw-baseline": "verified-source-evidence"}
    assert len(payload["probes"]) == 1


def test_optional_parser_absence_is_comparison_evidence_not_raw_failure(
    tmp_path: Path, monkeypatch
) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    harness.write_test_odt_fixture(source, content_body="<office:text><text:p>test</text:p></office:text>")

    def missing_import(name: str):
        if name in {"odf.opendocument", "odfdo"}:
            raise ModuleNotFoundError(name)
        return importlib.import_module(name)

    monkeypatch.setattr(harness.importlib, "import_module", missing_import)

    raw = harness.probe_raw_odt(source, allow_fixture_source=True)
    optional = harness.probe_optional_parsers(source, raw)

    assert raw["status"] == "verified-source-evidence"
    assert {probe["parser"]: probe["status"] for probe in optional} == {
        "odfpy": "not-installed",
        "odfdo": "not-installed",
    }
    assert all(probe["evidence_class"] == "parser-comparison-evidence" for probe in optional)
    assert all(probe["parser_direction_claims_authoritative"] is False for probe in optional)


def test_odfpy_unmodified_failure_and_temp_clean_success_are_recorded(
    tmp_path: Path, monkeypatch
) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    harness.write_test_odt_fixture(
        source,
        content_body="<office:text><text:p>test</text:p></office:text>",
        manifest_doctype=True,
    )
    original_bytes = source.read_bytes()
    calls: list[Path] = []

    def fake_load(path: str | Path):
        call_path = Path(path)
        calls.append(call_path)
        with zipfile.ZipFile(call_path) as zf:
            manifest = zf.read("META-INF/manifest.xml")
        if b"<!DOCTYPE" in manifest.upper():
            raise RuntimeError("external manifest reference rejected")
        return object()

    original_import_module = harness.importlib.import_module
    monkeypatch.setattr(
        harness.importlib,
        "import_module",
        lambda name: Mock(load=fake_load)
        if name == "odf.opendocument"
        else original_import_module(name),
    )

    raw = harness.probe_raw_odt(source, allow_fixture_source=True)
    [probe] = [probe for probe in harness.probe_optional_parsers(source, raw) if probe["parser"] == "odfpy"]

    assert probe["status"] == "loaded-temp-clean-manifest"
    assert probe["phases"]["unmodified"]["status"] == "failed-unmodified-load"
    assert probe["phases"]["unmodified"]["error"]["exception_class"] == "RuntimeError"
    assert probe["phases"]["temp-clean-manifest"]["controlled_mitigation"] is True
    assert probe["phases"]["temp-clean-manifest"]["removed_manifest_doctype"] is True
    assert source.read_bytes() == original_bytes
    assert calls[0] == source
    assert calls[1] != source


def test_manifest_clean_copy_removes_only_doctype(tmp_path: Path) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    harness.write_test_odt_fixture(
        source,
        content_body="<office:text><text:p>test</text:p></office:text>",
        manifest_doctype=True,
    )

    clean = tmp_path / "clean.odt"
    result = harness.write_manifest_doctype_clean_copy(source, clean)

    assert result["removed_manifest_doctype"] is True
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(clean) as cleaned:
        assert b"<!DOCTYPE" in original.read("META-INF/manifest.xml").upper()
        cleaned_manifest = cleaned.read("META-INF/manifest.xml")
        assert b"<!DOCTYPE" not in cleaned_manifest.upper()
        assert cleaned.read("content.xml") == original.read("content.xml")


def test_manifest_clean_copy_without_doctype_reports_no_removal(tmp_path: Path) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    harness.write_test_odt_fixture(
        source,
        content_body="<office:text><text:p>test</text:p></office:text>",
        manifest_doctype=False,
    )

    clean = tmp_path / "clean.odt"
    result = harness.write_manifest_doctype_clean_copy(source, clean)

    assert result["removed_manifest_doctype"] is False
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(clean) as cleaned:
        assert cleaned.read("META-INF/manifest.xml") == original.read("META-INF/manifest.xml")


def test_odfdo_api_incomplete_records_observed_capabilities(tmp_path: Path, monkeypatch) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    harness.write_test_odt_fixture(source, content_body="<office:text><text:p>test</text:p></office:text>")

    original_import_module = harness.importlib.import_module
    monkeypatch.setattr(
        harness.importlib,
        "import_module",
        lambda name: SimpleNamespace() if name == "odfdo" else original_import_module(name),
    )

    raw = harness.probe_raw_odt(source, allow_fixture_source=True)
    [probe] = [probe for probe in harness.probe_optional_parsers(source, raw) if probe["parser"] == "odfdo"]

    assert probe["status"] == "api-incomplete"
    assert probe["observed_capabilities"]["has_Document"] is False
    assert probe["evidence_class"] == "parser-comparison-evidence"


def test_odfdo_loaded_summary_keeps_raw_ordering_as_oracle(tmp_path: Path, monkeypatch) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    harness.write_test_odt_fixture(source, content_body="<office:text><text:p>test</text:p></office:text>")

    class FakeBody:
        def get_formatted_text(self) -> str:
            return "test"

        def get_tables(self) -> list[str]:
            return ["table"]

    class FakeDocument:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.body = FakeBody()
            self.styles = {"P1": object()}

    original_import_module = harness.importlib.import_module
    monkeypatch.setattr(
        harness.importlib,
        "import_module",
        lambda name: Mock(Document=FakeDocument) if name == "odfdo" else original_import_module(name),
    )

    raw = harness.probe_raw_odt(source, allow_fixture_source=True)
    [probe] = [probe for probe in harness.probe_optional_parsers(source, raw) if probe["parser"] == "odfdo"]

    assert probe["status"] == "loaded-unmodified"
    assert probe["comparison_summary"]["ordering_oracle"] == "raw-content-xml"
    assert probe["comparison_summary"]["ordered_text_available"] is True
    assert probe["comparison_summary"]["table_count"] == 1
    assert probe["comparison_summary"]["style_metadata_available"] is True


def test_cli_include_optional_parsers_adds_statuses_to_payload(tmp_path: Path, monkeypatch) -> None:
    harness = load_harness()
    source = tmp_path / "fixture.odt"
    out = tmp_path / "probe.json"
    harness.write_test_odt_fixture(source, content_body="<office:text><text:p>test</text:p></office:text>")

    monkeypatch.setattr(
        harness,
        "probe_optional_parsers",
        lambda source_path, raw_result: [
            {
                "parser": "odfpy",
                "status": "not-installed",
                "issue_ids": ["S05-optional-odfpy-not-installed"],
                "evidence_class": "parser-comparison-evidence",
            },
            {
                "parser": "odfdo",
                "status": "not-installed",
                "issue_ids": ["S05-optional-odfdo-not-installed"],
                "evidence_class": "parser-comparison-evidence",
            },
        ],
    )

    exit_code = harness.main(
        [
            "--source",
            str(source),
            "--allow-fixture-source",
            "--include-optional-parsers",
            "--out",
            str(out),
        ]
    )

    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["statuses"] == {
        "raw-baseline": "verified-source-evidence",
        "odfpy": "not-installed",
        "odfdo": "not-installed",
    }
    assert payload["probe_count"] == 3
