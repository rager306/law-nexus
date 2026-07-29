"""Pure legal taxonomy metadata.

[bounded] M076 S06 domain taxonomy helpers. These constants and predicates
centralize structural order and legal-force order for downstream deterministic
use cases. They do not parse sources, resolve conflicts, decide legal
applicability, or validate citation correctness.
"""

from __future__ import annotations

from law_nexus.domain.legal_unit import LegalUnitType
from law_nexus.domain.source_hierarchy import SourceLevel

LEGAL_UNIT_HIERARCHY: tuple[LegalUnitType, ...] = (
    LegalUnitType.chapter,
    LegalUnitType.article,
    LegalUnitType.part,
    LegalUnitType.clause,
    LegalUnitType.subclause,
    LegalUnitType.paragraph,
)

LEGAL_UNIT_ALLOWED_PARENTS: dict[LegalUnitType, frozenset[LegalUnitType | None]] = {
    LegalUnitType.chapter: frozenset({None}),
    LegalUnitType.article: frozenset({None, LegalUnitType.chapter}),
    LegalUnitType.part: frozenset({LegalUnitType.article}),
    LegalUnitType.clause: frozenset({LegalUnitType.article, LegalUnitType.part}),
    LegalUnitType.subclause: frozenset({LegalUnitType.clause}),
    LegalUnitType.paragraph: frozenset(
        {LegalUnitType.subclause, LegalUnitType.clause, LegalUnitType.part}
    ),
}

SOURCE_LEVELS_BY_FORCE: tuple[SourceLevel, ...] = (
    SourceLevel.constitution,
    SourceLevel.federal_constitutional_law,
    SourceLevel.federal_law_or_code,
    SourceLevel.presidential_act,
    SourceLevel.government_act,
    SourceLevel.departmental_act,
    SourceLevel.regional_legislation,
)

LEGAL_TAXONOMY_NON_CLAIMS: tuple[str, ...] = (
    "Legal taxonomy metadata does not validate legal correctness.",
    "Legal taxonomy metadata does not resolve conflicts or temporal applicability.",
    "Legal taxonomy metadata does not prove parser completeness or citation correctness.",
)


def is_allowed_legal_unit_parent(parent: LegalUnitType | None, child: LegalUnitType) -> bool:
    """Return whether ``parent`` is a structurally allowed parent for ``child``."""

    return parent in LEGAL_UNIT_ALLOWED_PARENTS[child]


def is_higher_legal_force(left: SourceLevel, right: SourceLevel) -> bool:
    """Return whether ``left`` has higher legal force than ``right``.

    Lower ``SourceLevel`` integer values represent higher legal force.
    Equal levels are not higher than each other.
    """

    return int(left) < int(right)
