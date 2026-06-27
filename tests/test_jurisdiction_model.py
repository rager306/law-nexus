from __future__ import annotations

import pytest
from pydantic import ValidationError

from law_nexus.domain import (
    JURISDICTION_LEVELS,
    JURISDICTION_NON_CLAIMS,
    RUSSIAN_FEDERATION_JURISDICTION,
    Jurisdiction,
    JurisdictionLevel,
    is_subordinate_jurisdiction_level,
)


def test_russian_federation_jurisdiction_is_stable_default() -> None:
    assert RUSSIAN_FEDERATION_JURISDICTION == Jurisdiction(
        jurisdiction_id="RU",
        level=JurisdictionLevel.federal,
        name="Russian Federation",
        parent_jurisdiction_id=None,
        iso_code="RU",
    )


def test_jurisdiction_levels_are_ordered_broad_to_local() -> None:
    assert JURISDICTION_LEVELS == (
        JurisdictionLevel.federal,
        JurisdictionLevel.regional,
        JurisdictionLevel.municipal,
    )
    assert is_subordinate_jurisdiction_level(JurisdictionLevel.regional, JurisdictionLevel.federal)
    assert is_subordinate_jurisdiction_level(JurisdictionLevel.municipal, JurisdictionLevel.regional)
    assert is_subordinate_jurisdiction_level(JurisdictionLevel.municipal, JurisdictionLevel.federal)
    assert not is_subordinate_jurisdiction_level(JurisdictionLevel.federal, JurisdictionLevel.regional)
    assert not is_subordinate_jurisdiction_level(JurisdictionLevel.federal, JurisdictionLevel.federal)


def test_regional_and_municipal_jurisdictions_carry_parent_ids() -> None:
    region = Jurisdiction(
        jurisdiction_id="RU-MOW",
        level=JurisdictionLevel.regional,
        name="Moscow",
        parent_jurisdiction_id="RU",
        iso_code="RU-MOW",
    )
    municipality = Jurisdiction(
        jurisdiction_id="RU-MOW-MUNICIPAL-001",
        level=JurisdictionLevel.municipal,
        name="Example municipal district",
        parent_jurisdiction_id="RU-MOW",
        iso_code=None,
    )

    assert region.parent_jurisdiction_id == "RU"
    assert municipality.parent_jurisdiction_id == "RU-MOW"


def test_non_federal_jurisdictions_require_parent() -> None:
    with pytest.raises(ValidationError):
        Jurisdiction(
            jurisdiction_id="RU-MOW",
            level=JurisdictionLevel.regional,
            name="Moscow",
            parent_jurisdiction_id=None,
            iso_code="RU-MOW",
        )


def test_jurisdiction_non_claims_are_explicit() -> None:
    assert JURISDICTION_NON_CLAIMS == (
        "Jurisdiction metadata does not decide legal applicability.",
        "Jurisdiction metadata does not resolve conflicts between federal and regional acts.",
        "Jurisdiction metadata does not validate parser extraction correctness.",
    )
