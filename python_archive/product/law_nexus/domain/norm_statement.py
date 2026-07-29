"""NormStatement domain model — a deontic claim derived from legal units.

[proposed] D046 domain form — fields + basic validation only, no logic.
Materialises the NormStatement verification contract (prd/02_architecture.md
§2a) as a Pydantic data shape, using the deontic modality triple
(obligation / permission / prohibition) with explicit negation as specified
by the T02 contract.

A ``NormStatement`` is a verified semantic claim derived from one or more
legal units, NOT an authoritative source by itself. Source authority remains
``LegalUnit → EvidenceSpan → SourceBlock → SourceDocument``. LLM output is
never final authority — ``extraction_method`` records provenance and
``verification_status`` gates whether a statement may support an answer.

Modality + negation encode the classic deontic reading:

    obligation  + negated=False → "must"
    prohibition + negated=False → "must not"
    permission  + negated=False → "may"

The compatibility-matrix validation (FR-14 norm_type × modality) and source
text verification logic belong to the verifier layer, not these forms.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NormModality(str, Enum):
    """Deontic modality of a norm statement."""

    obligation = "obligation"
    permission = "permission"
    prohibition = "prohibition"


class ExtractionMethod(str, Enum):
    """How a norm statement was extracted.

    LLM candidates are never final authority until independently verified.
    """

    deterministic = "deterministic"
    llm_candidate = "llm_candidate"
    manual = "manual"


class VerificationStatus(str, Enum):
    """Verification status of a norm statement (prd/02_architecture.md §2a).

    Only ``verified`` statements may support answers.
    """

    unverified = "unverified"
    verified = "verified"
    rejected = "rejected"
    needs_manual_review = "needs_manual_review"


class NormStatement(BaseModel):
    """A deontic claim derived from one or more legal units.

    ``source_unit_ids`` and ``evidence_span_ids`` MUST each contain at least
    one entry — a norm cannot exist without a source unit and proof. IDs
    reference ``LegalUnit`` and ``EvidenceSpan`` nodes (graph model).
    """

    model_config = ConfigDict(extra="forbid")

    statement_id: str
    modality: NormModality
    negated: bool = False
    text: str | None = None
    source_unit_ids: list[str] = Field(default_factory=list)
    evidence_span_ids: list[str] = Field(default_factory=list)
    extraction_method: ExtractionMethod = ExtractionMethod.llm_candidate
    verification_status: VerificationStatus = VerificationStatus.unverified

    @field_validator("source_unit_ids")
    @classmethod
    def _at_least_one_source_unit(cls, source_unit_ids: list[str]) -> list[str]:
        if not source_unit_ids:
            msg = "NormStatement requires at least one source_unit_id"
            raise ValueError(msg)
        return source_unit_ids

    @field_validator("evidence_span_ids")
    @classmethod
    def _at_least_one_evidence_span(cls, evidence_span_ids: list[str]) -> list[str]:
        if not evidence_span_ids:
            msg = "NormStatement requires at least one evidence_span_id"
            raise ValueError(msg)
        return evidence_span_ids
