"""Evidence-citation link port contracts.

[bounded] M076 S09 contracts for linking evidence spans to citation objects.
Links are audit structures only and do not prove citation correctness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from law_nexus.domain.citation import Citation
from law_nexus.domain.evidence_span import EvidenceLifecycle, EvidenceSpan

EVIDENCE_CITATION_LINK_NON_CLAIMS: tuple[str, ...] = (
    "Evidence-citation links are not proof of legal citation correctness.",
    "Evidence-citation links do not validate parser extraction correctness.",
    "Evidence-citation links do not decide legal applicability or interpretation.",
)


@dataclass(frozen=True)
class EvidenceCitationLinkRequest:
    """Input evidence spans and citations keyed by evidence span ID."""

    evidence_spans: Sequence[EvidenceSpan]
    citations_by_span_id: Mapping[str, Citation]


@dataclass(frozen=True)
class EvidenceCitationLink:
    """A bounded link between one evidence span and one citation object."""

    span_id: str
    source_document_id: str
    source_block_id: str
    source_sha256: str
    citation: Citation
    lifecycle_status: EvidenceLifecycle
    non_claims: tuple[str, ...] = EVIDENCE_CITATION_LINK_NON_CLAIMS


@dataclass(frozen=True)
class EvidenceCitationLinkResult:
    """Evidence-citation link result with deterministic diagnostics."""

    links: tuple[EvidenceCitationLink, ...]
    diagnostics: tuple[str, ...] = ()
