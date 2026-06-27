"""Pure jurisdiction domain model.

[bounded] M076 S07 domain jurisdiction metadata. This module provides stable
jurisdiction identifiers and hierarchy helpers for later parser/source
enrichment. It does not decide legal applicability, conflict resolution, or
parser correctness.
"""

from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class JurisdictionLevel(str, Enum):
    """Coarse jurisdiction level for Russian legal sources."""

    federal = "federal"
    regional = "regional"
    municipal = "municipal"


JURISDICTION_LEVELS: tuple[JurisdictionLevel, ...] = (
    JurisdictionLevel.federal,
    JurisdictionLevel.regional,
    JurisdictionLevel.municipal,
)

JURISDICTION_NON_CLAIMS: tuple[str, ...] = (
    "Jurisdiction metadata does not decide legal applicability.",
    "Jurisdiction metadata does not resolve conflicts between federal and regional acts.",
    "Jurisdiction metadata does not validate parser extraction correctness.",
)


class Jurisdiction(BaseModel):
    """A bounded jurisdiction value object.

    ``jurisdiction_id`` is the stable project-local identifier. ``iso_code`` is
    optional because municipal or reconstructed scopes may not have a stable ISO
    code in the source artifact. Non-federal jurisdictions must reference a
    parent jurisdiction so downstream enrichment does not imply orphan scope.
    """

    model_config = ConfigDict(extra="forbid")

    jurisdiction_id: str
    level: JurisdictionLevel
    name: str
    parent_jurisdiction_id: str | None = None
    iso_code: str | None = None

    @model_validator(mode="after")
    def _non_federal_requires_parent(self) -> Self:
        if self.level is not JurisdictionLevel.federal and self.parent_jurisdiction_id is None:
            msg = "non-federal jurisdictions require parent_jurisdiction_id"
            raise ValueError(msg)
        if self.level is JurisdictionLevel.federal and self.parent_jurisdiction_id is not None:
            msg = "federal jurisdiction must not have parent_jurisdiction_id"
            raise ValueError(msg)
        return self


RUSSIAN_FEDERATION_JURISDICTION = Jurisdiction(
    jurisdiction_id="RU",
    level=JurisdictionLevel.federal,
    name="Russian Federation",
    parent_jurisdiction_id=None,
    iso_code="RU",
)


def is_subordinate_jurisdiction_level(child: JurisdictionLevel, parent: JurisdictionLevel) -> bool:
    """Return whether ``child`` is lower in scope than ``parent``."""

    return JURISDICTION_LEVELS.index(child) > JURISDICTION_LEVELS.index(parent)
