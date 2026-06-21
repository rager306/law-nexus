"""SourceDocument domain model — the ingested source artifact.

[proposed] D046 domain form — fields + basic validation only, no logic.
Materialises the R031/R034 source-record contract as a Pydantic data shape.

A ``SourceDocument`` is the root of the evidence chain:

    EvidenceSpan → SourceBlock → SourceDocument

Identity is keyed by ``sha256``; import lifecycle and provenance rules
(official vs commercial vs reconstructed vs legacy vs generated) are described
in prd/02_architecture.md §3c. Provenance class is carried as data here;
enforcement belongs to the ingestion/adapter layer.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SourceProvenanceClass(str, Enum):
    """Provenance class of a source document (prd/02_architecture.md §3c).

    Distinguishes legal authority from reconstruction and generated context.
    Only ``official_publication`` and ``commercial_consolidated`` may back
    authoritative evidence; the rest are explanatory or prior-art only.
    """

    official_publication = "official_publication"
    commercial_consolidated = "commercial_consolidated"
    open_reconstructed = "open_reconstructed"
    legacy_prior_art = "legacy_prior_art"
    generated_summary = "generated_summary"


class SourceDocument(BaseModel):
    """An ingested legal source artifact (e.g. a Гарант ODT, Consultant XML).

    ``sha256`` is the load-bearing identity: re-importing the same SHA is an
    idempotent no-op for graph facts; a changed SHA creates a new revision.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str
    sha256: str = Field(min_length=1)
    source_system: str
    source_provenance_class: SourceProvenanceClass
    mime_type: str | None = None
    filename: str | None = None
    act_number: str | None = None
    edition_date: date | None = None
    imported_at: datetime | None = None
