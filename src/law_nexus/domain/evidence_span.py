"""EvidenceSpan domain model — immutable grounding anchor keyed by SHA.

[proposed] D044/Evidence-layer domain form — fields + basic validation only.
Materialises the R034 fail-closed evidence contract as a Pydantic data shape.

An ``EvidenceSpan`` is the immutable link between a semantic claim
(``NormStatement`` / ``TextChunk`` / ``Answer``) and the source bytes. It is
immutable for a given ``SourceDocument.sha256`` + ``SourceBlock`` + span +
``LegalUnit`` + ``ActEdition``. When the source SHA changes, import MUST
create new span IDs; old spans are retained for audit and marked with a
lifecycle status rather than overwritten (prd/02_architecture.md §4).

Immutability is enforced structurally via a frozen model. ``source_sha256``
is part of the span's identity; ``content_sha256`` (the span-text hash) is
[proposed] and populated by the adapter layer — no hashing logic here.
"""

from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceLifecycle(str, Enum):
    """Lifecycle status of an evidence span (prd/02_architecture.md §4)."""

    current = "current"
    superseded_by_new_sha = "superseded_by_new_sha"
    orphaned_by_parser_change = "orphaned_by_parser_change"
    rejected_by_validation = "rejected_by_validation"
    archived = "archived"


class EvidenceSpan(BaseModel):
    """An immutable evidence anchor pointing into a SourceBlock.

    References are by ID (graph model): ``source_document_id``, ``source_block_id``,
    ``legal_unit_id``, ``act_edition_id``. ``source_sha256`` pins the span to a
    specific source revision; mutating it would require a new span ID.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    span_id: str
    source_document_id: str
    source_block_id: str
    source_sha256: str = Field(min_length=1)
    legal_unit_id: str | None = None
    act_edition_id: str | None = None
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    text: str | None = None
    content_sha256: str | None = None
    lifecycle_status: EvidenceLifecycle = EvidenceLifecycle.current

    @model_validator(mode="after")
    def _span_is_ordered(self) -> Self:
        if self.char_end < self.char_start:
            msg = f"char_end ({self.char_end}) must be >= char_start ({self.char_start})"
            raise ValueError(msg)
        return self
