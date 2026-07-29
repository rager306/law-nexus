"""Russian legal-force source hierarchy.

[proposed] D046 domain form — data only, no conflict-resolution logic.
Materialises the R035 source-hierarchy contract as a Pydantic data shape.

Canonical hierarchy (highest legal force → lowest):

    Конституция          (Constitution)
      → ФКЗ             (federal constitutional laws)
        → ФЗ / кодексы  (federal laws and codes)
          → указы       (presidential acts)
            → постановления (government acts)
              → ведомственные (departmental normative acts)
                → региональные (regional legislation)

Rank is encoded as the ``SourceLevel`` enum value: lower rank = higher legal
force. This is data, not logic — lex superior comparison (05-03-06) is deferred
to the temporal/collision layer.
"""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel, ConfigDict


class SourceLevel(IntEnum):
    """Legal-force tier of a Russian legal source.

    Enum value is the force rank: 0 is the Constitution (highest force),
    increasing values are weaker force. Ranks are contiguous so future
    deterministic ``lex superior`` logic can compare them directly.
    """

    constitution = 0
    federal_constitutional_law = 1
    federal_law_or_code = 2
    presidential_act = 3
    government_act = 4
    departmental_act = 5
    regional_legislation = 6


#: Canonical hierarchy ordered highest legal force → lowest.
SOURCE_HIERARCHY: tuple[SourceLevel, ...] = (
    SourceLevel.constitution,
    SourceLevel.federal_constitutional_law,
    SourceLevel.federal_law_or_code,
    SourceLevel.presidential_act,
    SourceLevel.government_act,
    SourceLevel.departmental_act,
    SourceLevel.regional_legislation,
)


class SourceTier(BaseModel):
    """Where a source document sits in the legal-force hierarchy.

    The rank mirrors ``level`` so it is carried as data; it is NOT recomputed
    here (no logic) — callers read ``SourceLevel`` value for comparison.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    level: SourceLevel
    rank: int
