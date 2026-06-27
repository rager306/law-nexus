from __future__ import annotations

from law_nexus.adapters.sources.glossary_candidates import RegexGlossaryCandidateExtractor
from law_nexus.application.glossary_candidates import GlossaryCandidateUseCase
from law_nexus.domain import (
    RUSSIAN_FEDERATION_JURISDICTION,
    Jurisdiction,
    JurisdictionLevel,
    LegalUnitType,
    SourceLevel,
)
from law_nexus.ports.glossary_candidates import (
    GLOSSARY_CANDIDATE_NON_CLAIMS,
    GlossaryCandidateParagraph,
    GlossaryCandidateRequest,
)


def test_regex_glossary_candidate_use_case_extracts_bounded_candidates() -> None:
    paragraph = GlossaryCandidateParagraph(
        source_id="44-fz",
        paragraph_id="article-3-part-1",
        text='Для целей настоящего Федерального закона термин "контрактная система" означает совокупность участников контрактной системы.',
        source_level=SourceLevel.federal_law_or_code,
        jurisdiction=RUSSIAN_FEDERATION_JURISDICTION,
        legal_unit_type=LegalUnitType.part,
    )

    result = GlossaryCandidateUseCase(RegexGlossaryCandidateExtractor()).extract_candidates(
        GlossaryCandidateRequest(paragraphs=(paragraph,))
    )

    assert result.diagnostics == ()
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.term == "контрактная система"
    assert candidate.normalized_term == "контрактная система"
    assert candidate.definition == "совокупность участников контрактной системы."
    assert candidate.source_id == "44-fz"
    assert candidate.paragraph_id == "article-3-part-1"
    assert candidate.source_level is SourceLevel.federal_law_or_code
    assert candidate.jurisdiction_id == "RU"
    assert candidate.legal_unit_type is LegalUnitType.part
    assert candidate.pattern_id == "term_means"
    assert candidate.non_claims == GLOSSARY_CANDIDATE_NON_CLAIMS


def test_glossary_candidate_use_case_collapses_duplicate_normalized_terms() -> None:
    first = GlossaryCandidateParagraph(
        source_id="44-fz",
        paragraph_id="p1",
        text='термин "Контрактная система" означает первое определение.',
        source_level=SourceLevel.federal_law_or_code,
        jurisdiction=RUSSIAN_FEDERATION_JURISDICTION,
        legal_unit_type=LegalUnitType.part,
    )
    duplicate = GlossaryCandidateParagraph(
        source_id="44-fz",
        paragraph_id="p2",
        text='термин " контрактная   система " означает второе определение.',
        source_level=SourceLevel.federal_law_or_code,
        jurisdiction=RUSSIAN_FEDERATION_JURISDICTION,
        legal_unit_type=LegalUnitType.part,
    )

    result = GlossaryCandidateUseCase(RegexGlossaryCandidateExtractor()).extract_candidates(
        GlossaryCandidateRequest(paragraphs=(first, duplicate))
    )

    assert [candidate.paragraph_id for candidate in result.candidates] == ["p1"]
    assert result.diagnostics == ("duplicate-candidate:44-fz:контрактная система:p2",)


def test_glossary_candidates_carry_regional_jurisdiction_metadata() -> None:
    regional = Jurisdiction(
        jurisdiction_id="RU-MOW",
        level=JurisdictionLevel.regional,
        name="Moscow",
        parent_jurisdiction_id="RU",
        iso_code="RU-MOW",
    )
    paragraph = GlossaryCandidateParagraph(
        source_id="moscow-act",
        paragraph_id="article-1",
        text='понятие "городская программа" — комплекс мероприятий, утверждаемых правовым актом города Москвы.',
        source_level=SourceLevel.regional_legislation,
        jurisdiction=regional,
        legal_unit_type=LegalUnitType.article,
    )

    result = GlossaryCandidateUseCase(RegexGlossaryCandidateExtractor()).extract_candidates(
        GlossaryCandidateRequest(paragraphs=(paragraph,))
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.term == "городская программа"
    assert candidate.jurisdiction_id == "RU-MOW"
    assert candidate.source_level is SourceLevel.regional_legislation
    assert candidate.legal_unit_type is LegalUnitType.article
    assert candidate.pattern_id == "concept_dash"


def test_glossary_candidate_non_claims_are_explicit() -> None:
    assert GLOSSARY_CANDIDATE_NON_CLAIMS == (
        "Glossary candidates are not validated legal definitions.",
        "Glossary candidates do not decide legal applicability or interpretation.",
        "Glossary candidates do not prove parser extraction correctness.",
    )
