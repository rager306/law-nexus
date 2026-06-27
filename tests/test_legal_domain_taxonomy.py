from __future__ import annotations

from law_nexus.domain import (
    LEGAL_TAXONOMY_NON_CLAIMS,
    LEGAL_UNIT_HIERARCHY,
    SOURCE_LEVELS_BY_FORCE,
    LegalUnitType,
    SourceLevel,
    is_allowed_legal_unit_parent,
    is_higher_legal_force,
)


def test_legal_unit_hierarchy_is_ordered_from_broad_to_narrow() -> None:
    assert LEGAL_UNIT_HIERARCHY == (
        LegalUnitType.chapter,
        LegalUnitType.article,
        LegalUnitType.part,
        LegalUnitType.clause,
        LegalUnitType.subclause,
        LegalUnitType.paragraph,
    )


def test_allowed_parent_relationships_are_explicit() -> None:
    assert is_allowed_legal_unit_parent(parent=None, child=LegalUnitType.chapter)
    assert is_allowed_legal_unit_parent(parent=None, child=LegalUnitType.article)
    assert is_allowed_legal_unit_parent(parent=LegalUnitType.chapter, child=LegalUnitType.article)
    assert is_allowed_legal_unit_parent(parent=LegalUnitType.article, child=LegalUnitType.part)
    assert is_allowed_legal_unit_parent(parent=LegalUnitType.part, child=LegalUnitType.clause)
    assert is_allowed_legal_unit_parent(parent=LegalUnitType.clause, child=LegalUnitType.subclause)
    assert is_allowed_legal_unit_parent(parent=LegalUnitType.subclause, child=LegalUnitType.paragraph)

    assert not is_allowed_legal_unit_parent(parent=LegalUnitType.clause, child=LegalUnitType.article)
    assert not is_allowed_legal_unit_parent(parent=LegalUnitType.paragraph, child=LegalUnitType.chapter)


def test_source_levels_are_ordered_by_legal_force() -> None:
    assert SOURCE_LEVELS_BY_FORCE == (
        SourceLevel.constitution,
        SourceLevel.federal_constitutional_law,
        SourceLevel.federal_law_or_code,
        SourceLevel.presidential_act,
        SourceLevel.government_act,
        SourceLevel.departmental_act,
        SourceLevel.regional_legislation,
    )
    assert is_higher_legal_force(SourceLevel.constitution, SourceLevel.federal_law_or_code)
    assert is_higher_legal_force(SourceLevel.federal_law_or_code, SourceLevel.government_act)
    assert not is_higher_legal_force(SourceLevel.government_act, SourceLevel.federal_law_or_code)
    assert not is_higher_legal_force(SourceLevel.constitution, SourceLevel.constitution)


def test_taxonomy_non_claims_are_explicit() -> None:
    assert LEGAL_TAXONOMY_NON_CLAIMS == (
        "Legal taxonomy metadata does not validate legal correctness.",
        "Legal taxonomy metadata does not resolve conflicts or temporal applicability.",
        "Legal taxonomy metadata does not prove parser completeness or citation correctness.",
    )
