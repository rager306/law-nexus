"""LegalUnit domain model — a structural node of a legal act.

[proposed] D046 domain form — fields + basic validation only, no logic.
Materialises the structural LegalUnit taxonomy (prd/02_architecture.md §2) as
a Pydantic data shape.

A ``LegalUnit`` is one node in the structural hierarchy of an act
(Chapter → Article → Part → Clause → SubClause → Paragraph). It carries a
``Citation`` and references its parent unit and edition by ID. Temporal
applicability is resolved through its ``ActEdition`` (the temporal window
itself lives on ``ActEdition`` per the T02 contract).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from law_nexus.domain.citation import Citation


class LegalUnitType(str, Enum):
    """Structural type of a legal unit (prd/02_architecture.md §2 labels)."""

    chapter = "chapter"
    article = "article"
    part = "part"
    clause = "clause"
    subclause = "subclause"
    paragraph = "paragraph"


class LegalUnit(BaseModel):
    """A structural node of a legal act.

    ``legal_document_id`` references the parent ``LegalDocument`` (act),
    ``parent_unit_id`` references the enclosing ``LegalUnit`` (structural
    ``CONTAINS``), and ``edition_id`` references the ``ActEdition`` whose
    temporal window governs applicability. ``citation`` locates the unit by
    ст/ч/п/подп/абз coordinates.
    """

    model_config = ConfigDict(extra="forbid")

    unit_id: str
    legal_document_id: str
    unit_type: LegalUnitType
    citation: Citation | None = None
    text: str | None = None
    parent_unit_id: str | None = None
    edition_id: str | None = None
