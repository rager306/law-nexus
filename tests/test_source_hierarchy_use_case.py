from __future__ import annotations

from law_nexus.adapters.sources.consultant_hierarchy import (
    ConsultantHierarchyRecordBuilder,
    stream_wordml_paragraphs,
)
from law_nexus.application.source_hierarchy import SourceHierarchyUseCase
from law_nexus.ports.source_hierarchy import SourceHierarchyParagraph, SourceHierarchyRequest


def _request(paragraphs: list[SourceHierarchyParagraph], source_sha256: str = "a" * 64) -> SourceHierarchyRequest:
    return SourceHierarchyRequest(
        paragraphs=paragraphs,
        source_sha256=source_sha256,
        scope_id="CONS",
        document_id="DOC-TEST",
        source_path="test/fixture.xml",
    )


def _use_case() -> SourceHierarchyUseCase:
    return SourceHierarchyUseCase(builder=ConsultantHierarchyRecordBuilder())


def test_stream_wordml_paragraphs_decodes_text_and_reports_diagnostics(tmp_path) -> None:
    source = tmp_path / "fixture.xml"
    source.write_text(
        """
        <w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\">
          <w:body>
            <w:p><w:pPr><w:pStyle w:val=\"5\" /></w:pPr><w:r><w:t>Федеральный&#160;закон</w:t></w:r></w:p>
            <w:p><w:pPr><w:pStyle w:val=\"2\" /></w:pPr><w:r><w:t>&#167; 1. Планирование</w:t></w:r></w:p>
            <w:p><w:r><w:t>   </w:t></w:r></w:p>
          </w:body>
        </w:wordDocument>
        """,
        encoding="utf-8",
    )

    paragraphs, diagnostics = stream_wordml_paragraphs(source)

    assert [(p.index, p.text, p.style) for p in paragraphs] == [
        (1, "Федеральный закон", "5"),
        (2, "§ 1. Планирование", "2"),
    ]
    assert diagnostics["namespace_detected"] == "http://schemas.microsoft.com/office/word/2003/wordml"
    assert diagnostics["paragraph_count"] == 3
    assert diagnostics["skipped_empty_paragraphs"] == 1
    assert diagnostics["malformed_xml"] is None



def test_source_hierarchy_use_case_builds_contextual_records() -> None:
    result = _use_case().build_records(
        _request(
            [
                SourceHierarchyParagraph(index=1, text="Федеральный закон", style="5"),
                SourceHierarchyParagraph(index=2, text="Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ", style="2"),
                SourceHierarchyParagraph(index=3, text="§ 1. Планирование", style="2"),
                SourceHierarchyParagraph(index=4, text="Статья 1. Предмет", style="2"),
                SourceHierarchyParagraph(index=5, text="1. Часть первая", style="0"),
                SourceHierarchyParagraph(index=6, text="1) пункт", style="0"),
                SourceHierarchyParagraph(index=7, text="а) подпункт", style="0"),
                SourceHierarchyParagraph(index=8, text="Статья 2. Новая статья", style="2"),
                SourceHierarchyParagraph(index=9, text="1) пункт без новой части", style="0"),
            ]
        )
    )

    records = result.records
    assert [record["level"] for record in records] == [
        "document",
        "chapter",
        "section",
        "article",
        "part",
        "clause",
        "subclause",
        "article",
        "clause",
    ]
    by_id = {record["id"]: record for record in records}
    first_article = next(record for record in records if record["level"] == "article")
    second_article = [record for record in records if record["level"] == "article"][1]
    trailing_clause = records[-1]
    assert first_article["parent_id"] == "HIER-CONS-SECTION-0001"
    assert by_id["HIER-CONS-PART-0001"]["parent_id"] == first_article["id"]
    assert by_id["HIER-CONS-CLAUSE-0001"]["parent_id"] == "HIER-CONS-PART-0001"
    assert by_id["HIER-CONS-SUBCLAUSE-0001"]["parent_id"] == "HIER-CONS-CLAUSE-0001"
    assert trailing_clause["parent_id"] == second_article["id"]
    assert result.diagnostics["validation_error_count"] == 0


def test_source_hierarchy_use_case_rejects_markers_without_article_context() -> None:
    result = _use_case().build_records(
        _request(
            [
                SourceHierarchyParagraph(index=1, text="Федеральный закон", style="5"),
                SourceHierarchyParagraph(index=2, text="Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ", style="2"),
                SourceHierarchyParagraph(index=3, text="1. Часть без статьи", style="0"),
                SourceHierarchyParagraph(index=4, text="1) пункт без статьи", style="0"),
            ],
            source_sha256="c" * 64,
        )
    )

    assert [record["level"] for record in result.records] == ["document", "chapter"]
    assert result.diagnostics["skipped_marker_counts"] == {
        "clause_outside_article": 1,
        "part_outside_article": 1,
    }
    assert result.diagnostics["structural_error_count"] == 3
    assert result.diagnostics["structural_errors"][0]["kind"] == "missing_article_heading"
    assert {error["kind"] for error in result.diagnostics["structural_errors"]} == {
        "context_break",
        "missing_article_heading",
    }


def test_source_hierarchy_use_case_is_deterministic() -> None:
    request = _request(
        [
            SourceHierarchyParagraph(index=1, text="Федеральный закон", style="5"),
            SourceHierarchyParagraph(index=2, text="Статья 1. Предмет", style="2"),
            SourceHierarchyParagraph(index=3, text="1. Часть первая", style="0"),
        ]
    )

    first = _use_case().build_records(request)
    second = _use_case().build_records(request)

    assert first == second
    assert first.records[0]["record_kind"] == "consultant_hierarchy"
    assert first.records[0]["non_authoritative"] is True
    assert first.records[0]["non_claims"] == [
        "Consultant hierarchy records are deterministic parser-source records only.",
        "Consultant hierarchy records do not claim legal correctness or authoritative legal interpretation.",
        "Consultant hierarchy records do not claim parser completeness.",
        "Consultant hierarchy records do not claim product ETL or FalkorDB load readiness.",
    ]
