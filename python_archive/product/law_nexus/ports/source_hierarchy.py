"""Source hierarchy builder port.

[bounded] M076 S04 port for deterministic source hierarchy extraction. The
port works with already-normalized paragraph data and returns parser-record
shaped dictionaries plus diagnostics. It does not claim legal semantic
correctness or production ``SourceBlock`` validation.

M088 S01 widens SourceHierarchyParagraph to RawBlock with 6 additive fields
(kind, outline_level, num_id, inline_refs, table_flag, source_span) per
proposal 26 Layer 1. SourceHierarchyParagraph remains as a backward-compatible
alias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, Sequence, runtime_checkable

BlockKind = Literal["heading", "paragraph", "table_row", "list_item"]


@dataclass(frozen=True)
class RawBlock:
    """One bounded paragraph available to hierarchy builders.

    Widen from the original SourceHierarchyParagraph with additive fields
    that populate from available format signals (WordML pStyle, ODT
    outline-level, etc.). Fields without corresponding source signal
    stay at their default value (None, empty list, False).
    """

    index: int
    text: str
    style: str | None
    kind: BlockKind = "paragraph"
    outline_level: int | None = None
    num_id: str | None = None
    inline_refs: list[str] = field(default_factory=list)
    table_flag: bool = False
    source_span: str | None = None


# Backward-compatible alias: all existing callers create
# SourceHierarchyParagraph(index=, text=, style=) which maps to
# RawBlock with additive fields defaulted.
SourceHierarchyParagraph = RawBlock


@dataclass(frozen=True)
class SourceHierarchyRequest:
    """Input for deterministic paragraph-to-hierarchy record generation."""

    paragraphs: Sequence[RawBlock]
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
