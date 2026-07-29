"""ActEdition domain model — a temporal edition of a legal act.

[proposed] D046 domain form — fields + basic validation only, no logic.
Materialises the temporal-layer contract (prd/02_architecture.md §3) as a
Pydantic data shape.

Per the T02 contract the temporal window (valid_from / valid_to / effective /
status / temporal_confidence) is carried on ``ActEdition``. ``status`` is
recorded as data only — deterministic ``legal.active_at`` derivation logic
(§3) belongs to the temporal/collision layer, not the domain forms.

Glossary (prd/02_architecture.md §3a):
- ``edition_date``      — date of the edition fixed by the source system.
- ``valid_from/to``     — period of formal legal force.
- ``effective_from/to`` — period of practical application when it differs
  from formal validity; remains ``null`` unless independently extracted.
- ``temporal_confidence`` — confidence in the extracted temporal window.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class ActStatus(str, Enum):
    """Applicability status of an edition/unit at a point in time (§3)."""

    active = "active"
    expired = "expired"
    future = "future"
    partially_active = "partially_active"
    unknown = "unknown"


class TemporalConfidence(str, Enum):
    """Confidence in an extracted temporal window."""

    verified = "verified"
    inferred = "inferred"
    unknown = "unknown"


class ActEdition(BaseModel):
    """A specific edition of a legal act, derived from a SourceDocument.

    ``legal_document_id`` references the parent ``LegalDocument`` (act) and
    ``source_document_id`` references the ``SourceDocument`` this edition was
    derived from. Temporal fields are data only here.
    """

    model_config = ConfigDict(extra="forbid")

    edition_id: str
    legal_document_id: str
    source_document_id: str
    edition_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    status: ActStatus = ActStatus.unknown
    temporal_confidence: TemporalConfidence = TemporalConfidence.unknown

    @model_validator(mode="after")
    def _windows_are_ordered(self) -> Self:
        if self.valid_from is not None and self.valid_to is not None:
            if self.valid_to < self.valid_from:
                msg = f"valid_to ({self.valid_to}) must be >= valid_from ({self.valid_from})"
                raise ValueError(msg)
        if self.effective_from is not None and self.effective_to is not None:
            if self.effective_to < self.effective_from:
                msg = (
                    f"effective_to ({self.effective_to}) must be >= "
                    f"effective_from ({self.effective_from})"
                )
                raise ValueError(msg)
        return self
