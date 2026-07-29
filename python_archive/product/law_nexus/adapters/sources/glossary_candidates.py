"""Deterministic glossary candidate source adapter.

[bounded] M076 S08 adapter. Regex matches are intentionally conservative and
produce candidates only. They do not validate legal definitions.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from law_nexus.ports.glossary_candidates import (
    GlossaryCandidate,
    GlossaryCandidateParagraph,
    GlossaryCandidateResult,
)

_WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)
_TERM_MEANS_RE = re.compile(
    r"(?:термин|термины)\s+[\"«](?P<term>[^\"»]+)[\"»]\s+означа(?:ет|ют)\s+(?P<definition>.+)",
    re.IGNORECASE | re.UNICODE,
)
_CONCEPT_DASH_RE = re.compile(
    r"(?:понятие|понятия)\s+[\"«](?P<term>[^\"»]+)[\"»]\s+[—-]\s+(?P<definition>.+)",
    re.IGNORECASE | re.UNICODE,
)


def normalize_glossary_term(term: str) -> str:
    """Normalize glossary candidate term text for duplicate detection."""

    return _WHITESPACE_RE.sub(" ", term.casefold().strip())


class RegexGlossaryCandidateExtractor:
    """Extract glossary candidates from Russian definition marker patterns."""

    _patterns = (
        ("term_means", _TERM_MEANS_RE),
        ("concept_dash", _CONCEPT_DASH_RE),
    )

    def extract_candidates(
        self,
        paragraphs: Sequence[GlossaryCandidateParagraph],
    ) -> GlossaryCandidateResult:
        """Extract deterministic candidates from ``paragraphs``."""

        candidates: list[GlossaryCandidate] = []
        for paragraph in paragraphs:
            for pattern_id, pattern in self._patterns:
                match = pattern.search(paragraph.text)
                if match is None:
                    continue
                term = _WHITESPACE_RE.sub(" ", match.group("term").strip())
                definition = match.group("definition").strip()
                candidates.append(
                    GlossaryCandidate(
                        term=term,
                        normalized_term=normalize_glossary_term(term),
                        definition=definition,
                        source_id=paragraph.source_id,
                        paragraph_id=paragraph.paragraph_id,
                        source_level=paragraph.source_level,
                        jurisdiction_id=paragraph.jurisdiction.jurisdiction_id,
                        legal_unit_type=paragraph.legal_unit_type,
                        pattern_id=pattern_id,
                    )
                )
                break
        return GlossaryCandidateResult(candidates=tuple(candidates))
