"""Glossary candidate use case.

[bounded] M076 S08 application seam. It delegates deterministic extraction to
an injected port and collapses duplicate normalized terms per source. The use
case does not validate legal meaning, parser correctness, or applicability.
"""

from __future__ import annotations

from dataclasses import dataclass

from law_nexus.ports.glossary_candidates import (
    GlossaryCandidate,
    GlossaryCandidateExtractor,
    GlossaryCandidateRequest,
    GlossaryCandidateResult,
)


@dataclass(frozen=True)
class GlossaryCandidateUseCase:
    """Extract bounded glossary candidates through an injected extractor."""

    extractor: GlossaryCandidateExtractor

    def extract_candidates(self, request: GlossaryCandidateRequest) -> GlossaryCandidateResult:
        """Return de-duplicated glossary candidates and diagnostics."""

        extracted = self.extractor.extract_candidates(request.paragraphs)
        candidates: list[GlossaryCandidate] = []
        diagnostics = list(extracted.diagnostics)
        seen: set[tuple[str, str]] = set()
        for candidate in extracted.candidates:
            key = (candidate.source_id, candidate.normalized_term)
            if key in seen:
                diagnostics.append(
                    f"duplicate-candidate:{candidate.source_id}:{candidate.normalized_term}:{candidate.paragraph_id}"
                )
                continue
            seen.add(key)
            candidates.append(candidate)
        return GlossaryCandidateResult(candidates=tuple(candidates), diagnostics=tuple(diagnostics))
