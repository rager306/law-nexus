from __future__ import annotations

from law_nexus.application.evidence_citations import EvidenceCitationLinkUseCase
from law_nexus.domain import Citation, EvidenceLifecycle, EvidenceSpan
from law_nexus.ports.evidence_citations import (
    EVIDENCE_CITATION_LINK_NON_CLAIMS,
    EvidenceCitationLinkRequest,
)


def _span(span_id: str = "span-1", lifecycle: EvidenceLifecycle = EvidenceLifecycle.current) -> EvidenceSpan:
    return EvidenceSpan(
        span_id=span_id,
        source_document_id="doc-44fz",
        source_block_id="block-article-3",
        source_sha256="sha256-source",
        legal_unit_id="article-3",
        act_edition_id="edition-2026",
        char_start=10,
        char_end=42,
        text="контрактная система",
        content_sha256="sha256-content",
        lifecycle_status=lifecycle,
    )


def test_evidence_citation_link_use_case_builds_valid_link() -> None:
    span = _span()
    citation = Citation(article="3", part="1")

    result = EvidenceCitationLinkUseCase().build_links(
        EvidenceCitationLinkRequest(
            evidence_spans=(span,),
            citations_by_span_id={"span-1": citation},
        )
    )

    assert result.diagnostics == ()
    assert len(result.links) == 1
    link = result.links[0]
    assert link.span_id == "span-1"
    assert link.source_document_id == "doc-44fz"
    assert link.source_block_id == "block-article-3"
    assert link.source_sha256 == "sha256-source"
    assert link.citation == citation
    assert link.lifecycle_status is EvidenceLifecycle.current
    assert link.non_claims == EVIDENCE_CITATION_LINK_NON_CLAIMS


def test_evidence_citation_link_use_case_reports_missing_and_orphan_citations() -> None:
    span = _span("span-without-citation")
    orphan_citation = Citation(article="5")

    result = EvidenceCitationLinkUseCase().build_links(
        EvidenceCitationLinkRequest(
            evidence_spans=(span,),
            citations_by_span_id={"missing-span": orphan_citation},
        )
    )

    assert result.links == ()
    assert result.diagnostics == (
        "missing-citation:span-without-citation",
        "orphan-citation:missing-span",
    )


def test_evidence_citation_link_use_case_preserves_non_current_lifecycle_with_diagnostic() -> None:
    span = _span("span-old", EvidenceLifecycle.superseded_by_new_sha)
    citation = Citation(article="3")

    result = EvidenceCitationLinkUseCase().build_links(
        EvidenceCitationLinkRequest(
            evidence_spans=(span,),
            citations_by_span_id={"span-old": citation},
        )
    )

    assert len(result.links) == 1
    assert result.links[0].lifecycle_status is EvidenceLifecycle.superseded_by_new_sha
    assert result.diagnostics == ("non-current-evidence-span:span-old:superseded_by_new_sha",)


def test_evidence_citation_link_non_claims_are_explicit() -> None:
    assert EVIDENCE_CITATION_LINK_NON_CLAIMS == (
        "Evidence-citation links are not proof of legal citation correctness.",
        "Evidence-citation links do not validate parser extraction correctness.",
        "Evidence-citation links do not decide legal applicability or interpretation.",
    )
