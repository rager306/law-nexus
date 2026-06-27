from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from law_nexus.adapters.parsers.consultant_wordml import (
    ConsultantParseError,
    ConsultantWordMLParser,
)
from law_nexus.domain.source_document import SourceProvenanceClass

_WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"
_OFFICE_NS = "urn:schemas-microsoft-com:office:office"


def _write_wordml(
    path: Path,
    *,
    title: str | None = "Федеральный закон от 05.04.2013 N 44-ФЗ (ред. от 26.12.2024)",
    root_tag: str = "w:wordDocument",
    include_properties: bool = True,
    include_title: bool = True,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    properties = ""
    if include_properties:
        title_xml = f"<o:Title>{title}</o:Title>" if include_title and title is not None else ""
        properties = (
            "<o:DocumentProperties>"
            f"{title_xml}"
            "<o:Company>Версия 4025.00.30</o:Company>"
            "</o:DocumentProperties>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<{root_tag} xmlns:w="{_WORDML_NS}" xmlns:o="{_OFFICE_NS}">'
        f"{properties}"
        "<w:body><w:p>bounded document-level fixture</w:p></w:body>"
        f"</{root_tag}>"
    )
    path.write_text(xml, encoding="utf-8")


def test_parse_returns_document_metadata_and_empty_blocks(tmp_path: Path) -> None:
    source = tmp_path / "consultant.xml"
    _write_wordml(source)

    document, blocks = ConsultantWordMLParser(source_root=str(tmp_path)).parse(source)

    assert document.source_id.startswith("consultant:44-ФЗ-")
    assert len(document.sha256) == 64
    assert document.source_system == "consultant"
    assert document.source_provenance_class is SourceProvenanceClass.commercial_consolidated
    assert document.mime_type == "application/xml"
    assert document.filename == "consultant.xml"
    assert document.act_number == "44-ФЗ"
    assert document.edition_date == date(2024, 12, 26)
    assert document.imported_at is None
    assert blocks == []


def test_parse_refuses_path_outside_source_root(tmp_path: Path) -> None:
    trusted_root = tmp_path / "trusted"
    outside = tmp_path / "outside.xml"
    trusted_root.mkdir()
    _write_wordml(outside)

    parser = ConsultantWordMLParser(source_root=str(trusted_root))

    with pytest.raises(ConsultantParseError, match="outside trusted source root"):
        parser.parse(outside)


def test_parse_rejects_missing_file_with_typed_error(tmp_path: Path) -> None:
    parser = ConsultantWordMLParser(source_root=str(tmp_path))

    with pytest.raises(ConsultantParseError, match="source not found or not a file"):
        parser.parse(tmp_path / "missing.xml")


def test_parse_rejects_malformed_xml_with_typed_error(tmp_path: Path) -> None:
    source = tmp_path / "malformed.xml"
    source.write_text("<w:wordDocument>", encoding="utf-8")

    parser = ConsultantWordMLParser(source_root=str(tmp_path))

    with pytest.raises(ConsultantParseError, match="malformed WordML XML"):
        parser.parse(source)


def test_parse_rejects_non_wordml_root(tmp_path: Path) -> None:
    source = tmp_path / "plain.xml"
    source.write_text("<root />", encoding="utf-8")

    parser = ConsultantWordMLParser(source_root=str(tmp_path))

    with pytest.raises(ConsultantParseError, match="expected WordML root"):
        parser.parse(source)


def test_parse_requires_document_properties(tmp_path: Path) -> None:
    source = tmp_path / "missing-properties.xml"
    _write_wordml(source, include_properties=False)

    parser = ConsultantWordMLParser(source_root=str(tmp_path))

    with pytest.raises(ConsultantParseError, match="missing <o:DocumentProperties>"):
        parser.parse(source)


def test_parse_requires_title_in_document_properties(tmp_path: Path) -> None:
    source = tmp_path / "missing-title.xml"
    _write_wordml(source, include_title=False)

    parser = ConsultantWordMLParser(source_root=str(tmp_path))

    with pytest.raises(ConsultantParseError, match="missing <o:Title>"):
        parser.parse(source)


def test_parse_leaves_optional_act_number_and_edition_date_empty(tmp_path: Path) -> None:
    source = tmp_path / "review.xml"
    _write_wordml(source, title="Обзор судебной практики Верховного Суда Российской Федерации")

    document, blocks = ConsultantWordMLParser(source_root=str(tmp_path)).parse(source)

    assert document.source_id.startswith("consultant:review-")
    assert document.act_number is None
    assert document.edition_date is None
    assert document.source_provenance_class is SourceProvenanceClass.commercial_consolidated
    assert blocks == []
