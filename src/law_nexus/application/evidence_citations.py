"""Evidence-citation link use case.

[bounded] M076 S09 application seam. The use case performs deterministic
shape/link validation only. It does not validate legal citation correctness,
parser extraction correctness, or legal applicability.
"""

from __future__ import annotations

from dataclasses import dataclass

from law_nexus.domain.evidence_span import EvidenceLifecycle
from law_nexus.ports.evidence_citations import (
    EvidenceCitationLink,
    EvidenceCitationLinkRequest,
    EvidenceCitationLinkResult,
)


@dataclass(frozen=True)
class EvidenceCitationLinkUseCase:
    """Build bounded evidence-citation links with deterministic diagnostics."""

    def build_links(self, request: EvidenceCitationLinkRequest) -> EvidenceCitationLinkResult:
        """Build links for spans that have citations keyed by ``span_id``."""

        links: list[EvidenceCitationLink] = []
        diagnostics: list[str] = []
        seen_span_ids: set[str] = set()

        for span in request.evidence_spans:
            seen_span_ids.add(span.span_id)
            citation = request.citations_by_span_id.get(span.span_id)
            if citation is None:
                diagnostics.append(f"missing-citation:{span.span_id}")
                continue
            if span.lifecycle_status is not EvidenceLifecycle.current:
                diagnostics.append(f"non-current-evidence-span:{span.span_id}:{span.lifecycle_status.value}")
            links.append(
                EvidenceCitationLink(
                    span_id=span.span_id,
                    source_document_id=span.source_document_id,
                    source_block_id=span.source_block_id,
                    source_sha256=span.source_sha256,
                    citation=citation,
                    lifecycle_status=span.lifecycle_status,
                )
            )

        for span_id in request.citations_by_span_id:
            if span_id not in seen_span_ids:
                diagnostics.append(f"orphan-citation:{span_id}")

        return EvidenceCitationLinkResult(links=tuple(links), diagnostics=tuple(diagnostics))
