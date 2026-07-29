"""SourceBlock domain model — a normalized unit of source text.

[proposed] D046 domain form — fields + basic validation only, no logic.
Materialises the R031 source-block contract as a Pydantic data shape.

A ``SourceBlock`` is produced by the parser from a ``SourceDocument`` and is
the substrate that ``EvidenceSpan`` records point into. Ordering and span
coordinates are carried as data; structural parsing logic lives in adapters.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceBlockType(str, Enum):
    """Coarse structural type of a source block.

    Mirrors the structural node labels in prd/02_architecture.md §2. Only the
    block-level types relevant to source segmentation are listed here; the
    full LegalUnit taxonomy lives in ``legal_unit.py``.
    """

    chapter = "chapter"
    article = "article"
    part = "part"
    clause = "clause"
    subclause = "subclause"
    paragraph = "paragraph"
    unstructured = "unstructured"


class SourceBlock(BaseModel):
    """A normalized text block extracted from a SourceDocument.

    ``source_document_id`` references the parent ``SourceDocument.source_id``.
    ``char_start``/``char_end`` locate the block in the cleaned source text;
    ``order`` gives linear source ordering (structural ``NEXT``/``PREVIOUS``
    navigation in the graph).
    """

    model_config = ConfigDict(extra="forbid")

    block_id: str
    source_document_id: str
    block_type: SourceBlockType
    order: int = Field(ge=0)
    text: str = ""
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)

    @field_validator("char_end")
    @classmethod
    def _char_end_after_start(cls, char_end: int, info) -> int:
        start = info.data.get("char_start")
        if start is not None and char_end < start:
            msg = f"char_end ({char_end}) must be >= char_start ({start})"
            raise ValueError(msg)
        return char_end
