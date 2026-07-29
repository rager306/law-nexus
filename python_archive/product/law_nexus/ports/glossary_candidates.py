"""Glossary candidate port contracts.

[bounded] M076 S08 contract for deterministic glossary candidate extraction.
Candidates are source-linked signals, not validated legal definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from law_nexus.domain.jurisdiction import Jurisdiction
from law_nexus.domain.legal_unit import LegalUnitType
from law_nexus.domain.source_hierarchy import SourceLevel

GLOSSARY_CANDIDATE_NON_CLAIMS: tuple[str, ...] = (
    "Glossary candidates are not validated legal definitions.",
    "Glossary candidates do not decide legal applicability or interpretation.",
    "Glossary candidates do not prove parser extraction correctness.",
)


@dataclass(frozen=True)
class GlossaryCandidateParagraph:
    """Source paragraph eligible for deterministic glossary candidate scanning."""

    source_id: str
    paragraph_id: str
    text: str
    source_level: SourceLevel
    jurisdiction: Jurisdiction
    legal_unit_type: LegalUnitType | None = None


@dataclass(frozen=True)
class GlossaryCandidateRequest:
    """Batch request for glossary candidate extraction."""

    paragraphs: Sequence[GlossaryCandidateParagraph]


@dataclass(frozen=True)
class GlossaryCandidate:
    """A bounded glossary candidate linked back to one source paragraph."""

    term: str
    normalized_term: str
    definition: str
    source_id: str
    paragraph_id: str
    source_level: SourceLevel
    jurisdiction_id: str
    legal_unit_type: LegalUnitType | None
    pattern_id: str
    non_claims: tuple[str, ...] = GLOSSARY_CANDIDATE_NON_CLAIMS


@dataclass(frozen=True)
class GlossaryCandidateResult:
    """Candidate extraction result with non-fatal diagnostics."""

    candidates: tuple[GlossaryCandidate, ...]
    diagnostics: tuple[str, ...] = ()


class GlossaryCandidateExtractor(Protocol):
    """Extract bounded glossary candidates from source paragraphs."""

    def extract_candidates(
        self,
        paragraphs: Sequence[GlossaryCandidateParagraph],
    ) -> GlossaryCandidateResult:
        """Return deterministic candidates and diagnostics for ``paragraphs``."""
        ...
