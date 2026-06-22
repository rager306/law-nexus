from __future__ import annotations

import json
from pathlib import Path

from law_nexus.adapters.parsers.consultant_wordml import (
    ConsultantDocumentType,
    _classify_document_type,
    _extract_consultant_title_first_line,
)

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_JSON = ROOT / "prd/parser/source_fixture_inventory.json"


def _load_inventory() -> dict:
    return json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))


def _first_consultant_fixture_by_document_type(document_type: str) -> dict:
    """Return the first Consultant XML fixture whose inventory document_type matches."""
    inventory = _load_inventory()
    for fixture in inventory["fixtures"]:
        if (
            fixture.get("source_kind") == "consultant-wordml-xml"
            and fixture.get("document_type") == document_type
        ):
            return fixture
    msg = f"no Consultant XML fixture with document_type={document_type!r} in inventory"
    raise AssertionError(msg)


def test_enum_has_all_expected_variants() -> None:
    """Every variant we plan to support must be present on the enum."""
    expected = {
        "federal_law",
        "code",
        "code_amendment_overview",
        "court_practice_review",
        "fas_review",
        "government_resolution",
        "constitutional_court_ruling",
        "supreme_court_ruling",
        "lower_court_ruling",
        "antimonopoly_decision",
        "document_list",
        "other_document",
    }
    actual = {v.name for v in ConsultantDocumentType}
    assert expected <= actual, f"missing variants: {expected - actual}"


def test_per_variant_classification_real_fixtures() -> None:
    """For each non-other variant, the parser classifies the real fixture correctly.

    The test reads the actual fixture's first-line title via
    :func:`_extract_consultant_title_first_line` and asserts
    :func:`_classify_document_type` matches the inventory document_type.
    """

    inventory = _load_inventory()
    document_types_seen: set[str] = set()
    for fixture in inventory["fixtures"]:
        if fixture.get("source_kind") != "consultant-wordml-xml":
            continue
        inventory_doc_type = fixture.get("document_type")
        if inventory_doc_type in {"other_document", None}:
            # Other-document fixtures are intentionally not classified; the
            # probe surfaces them as classification gaps. We still verify the
            # parser falls through to ``other_document`` for them.
            if inventory_doc_type == "other_document":
                title = _extract_consultant_title_first_line(ROOT / fixture["path"])
                assert _classify_document_type(title or "") == ConsultantDocumentType.other_document, (
                    f"{fixture['path']}: title did not fall through to other_document"
                )
            continue
        title = _extract_consultant_title_first_line(ROOT / fixture["path"])
        expected = ConsultantDocumentType(inventory_doc_type)
        actual = _classify_document_type(title or "")
        assert actual == expected, (
            f"{fixture['path']}: title={title!r} inventory={inventory_doc_type} got={actual.value}"
        )
        document_types_seen.add(inventory_doc_type)

    # Sanity: every non-other variant must have at least one real fixture.
    assert document_types_seen >= {
        "federal_law",
        "code",
        "code_amendment_overview",
        "court_practice_review",
        "fas_review",
        "government_resolution",
        "constitutional_court_ruling",
        "supreme_court_ruling",
        "lower_court_ruling",
        "antimonopoly_decision",
        "document_list",
    }, f"no real fixture for variants: missing"


def test_federal_law_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("federal_law")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.federal_law


def test_code_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("code")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.code


def test_code_amendment_overview_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("code_amendment_overview")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.code_amendment_overview


def test_court_practice_review_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("court_practice_review")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.court_practice_review


def test_fas_review_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("fas_review")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.fas_review


def test_government_resolution_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("government_resolution")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.government_resolution


def test_constitutional_court_ruling_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("constitutional_court_ruling")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.constitutional_court_ruling


def test_supreme_court_ruling_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("supreme_court_ruling")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.supreme_court_ruling


def test_lower_court_ruling_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("lower_court_ruling")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.lower_court_ruling


def test_antimonopoly_decision_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("antimonopoly_decision")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.antimonopoly_decision


def test_document_list_real_fixture() -> None:
    fixture = _first_consultant_fixture_by_document_type("document_list")
    title = _extract_consultant_title_first_line(ROOT / fixture["path"])
    assert _classify_document_type(title or "") == ConsultantDocumentType.document_list


def test_empty_title_falls_through_to_other_document() -> None:
    assert _classify_document_type("") == ConsultantDocumentType.other_document


def test_unknown_title_falls_through_to_other_document() -> None:
    assert _classify_document_type("Какой-то совершенно неизвестный акт 2025 года") == ConsultantDocumentType.other_document


def test_priority_constitutional_beats_generic() -> None:
    """The Конституционного Суда pattern must win over the generic `Суда` fallback."""
    title = "Постановление Конституционного Суда РФ от 18.03.2021 N 7-П"
    assert _classify_document_type(title) == ConsultantDocumentType.constitutional_court_ruling


def test_priority_supreme_beats_generic() -> None:
    title = "Постановление Верховного Суда РФ от 09.10.2025 N 38-АД25-9-К"
    assert _classify_document_type(title) == ConsultantDocumentType.supreme_court_ruling


def test_code_amendment_overview_priority_over_court_practice_review() -> None:
    """`Обзор изменений ... Кодекс` must win over generic `Обзор` patterns."""
    title = "Обзор изменений Гражданского кодекса Российской Федерации"
    assert _classify_document_type(title) == ConsultantDocumentType.code_amendment_overview