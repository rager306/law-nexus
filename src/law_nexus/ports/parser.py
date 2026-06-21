"""Parser port — source file → SourceDocument + SourceBlock sequence.

[proposed] port contract per D046. The port is a pure ``typing.Protocol``: it
declares the *shape* adapters must satisfy, with zero implementation. Real
adapters (e.g. Consultant WordML) are wired in the adapter layer.

The contract mirrors the import-package seam (prd/02_architecture.md §11): a
Parser turns an opaque source path into the document root and the ordered
``SourceBlock`` sequence that ``EvidenceSpan`` records point into. Structural
``LegalUnit`` / ``ActEdition`` derivation belongs to downstream parsers, not
this port.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from law_nexus.domain.source_block import SourceBlock
from law_nexus.domain.source_document import SourceDocument


@runtime_checkable
class Parser(Protocol):
    """Parse a source file into its document root and ordered source blocks.

    Contract:
    - ``path`` is a filesystem path readable by the adapter (a trusted root
      for MVP — see the S01 threat model). The port does not validate it;
      that is the adapter's boundary.
    - Returns the :class:`SourceDocument` (SHA-keyed identity) and the ordered
      :class:`SourceBlock` sequence produced from it.
    - Deterministic: the same ``path`` (same bytes → same SHA) MUST yield the
      same structural result. Re-parsing is idempotent for graph facts.

    This is the only product-layer trust boundary in S01; adapters own all
    I/O, XXE/path-traversal hardening, and parser-confidence reporting.
    """

    def parse(self, path: str) -> tuple[SourceDocument, list[SourceBlock]]:
        """Parse ``path`` into a SourceDocument and its ordered SourceBlocks."""
        ...
