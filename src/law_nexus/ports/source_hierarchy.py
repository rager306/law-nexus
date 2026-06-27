"""Source hierarchy builder port.

[bounded] M076 S04 port for deterministic source hierarchy extraction. The
port works with already-normalized paragraph data and returns parser-record
shaped dictionaries plus diagnostics. It does not claim legal semantic
correctness or production ``SourceBlock`` validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class SourceHierarchyParagraph:
    """One bounded paragraph available to hierarchy builders."""

    index: int
    text: str
    style: str | None


@dataclass(frozen=True)
class SourceHierarchyRequest:
    """Input for deterministic paragraph-to-hierarchy record generation."""

    paragraphs: Sequence[SourceHierarchyParagraph]
    source_sha256: str
    scope_id: str
    document_id: str
    source_path: str


@dataclass(frozen=True)
class SourceHierarchyResult:
    """Hierarchy parser records and bounded diagnostics."""

    records: list[dict[str, Any]]
    diagnostics: dict[str, Any]


@runtime_checkable
class SourceHierarchyBuilder(Protocol):
    """Build hierarchy parser records from normalized source paragraphs."""

    def build_records(self, request: SourceHierarchyRequest) -> SourceHierarchyResult:
        """Return deterministic hierarchy records and diagnostics for ``request``."""
        ...
