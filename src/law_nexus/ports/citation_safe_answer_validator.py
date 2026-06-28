"""Citation-safe answer validator port contracts.

[bounded] M076 S13 contracts for deterministic retrieval output validation.
Validation results are proof diagnostics, not legal advice or retrieval-quality
claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

CITATION_SAFE_ANSWER_VALIDATOR_NON_CLAIMS: tuple[str, ...] = (
    "Does not prove product retrieval quality.",
    "Does not prove legal-answer correctness.",
    "Does not provide legal interpretation authority.",
    "Does not prove parser completeness.",
    "Does not prove production FalkorDB runtime behavior.",
    "Does not make LLM output legal authority.",
)


@dataclass(frozen=True)
class CitationSafeAnswerValidationRequest:
    """Loaded input for citation-safe answer validation."""

    output: Any
    fixture_data: Mapping[str, Any]
    fixture_artifact: str
    case_id: str = "<ad-hoc>"
