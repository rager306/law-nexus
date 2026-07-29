"""Deterministic-first ingest use case.

[bounded] D046 application-layer lifecycle tag. ``Ingest`` is a thin,
deterministic use case: it takes a :class:`law_nexus.ports.parser.Parser`
port and delegates ``parse(path)`` to it, returning a
:class:`law_nexus.domain.SourceDocument`. No side effects, no LLM calls, no
graph writes — the deterministic seam that later steps (normalisation,
extraction) build on.

Why a class holding a port instead of a free function:
    The port is injected once at the composition root; the same ingest instance
    can be reused across calls, and swapping the parser (consultant, garant,
    a test stub) is a wiring concern, not a use-case concern. This keeps the
    application layer free of concrete adapter imports.
"""

from __future__ import annotations

# ``Parser`` is imported for type-checking only: it is a ``typing.Protocol``,
# so structural conformance is checked statically by basedpyright at the
# composition root, and no ports module is needed at runtime to run the use
# case (only to type-check it).
from pathlib import Path
from typing import TYPE_CHECKING

from law_nexus.domain import SourceDocument

if TYPE_CHECKING:
    from law_nexus.ports.parser import Parser


class Ingest:
    """Ingest a legal source document via an injected :class:`Parser` port.

    The use case is deterministic: identical ``path`` + identical parser
    implementation yield an identical :class:`SourceDocument` (the
    ``imported_at`` timestamp is intentionally left ``None`` so the parsed
    document is reproducible — timestamping is an infrastructure concern, set
    by the persistence/graph-write layer, not by the ingest use case).

    This use case returns the :class:`SourceDocument` (the document-level
    root). The parser also produces a ``SourceBlock`` sequence; that sequence
    is the substrate for downstream structural/normalisation use cases and is
    not surfaced here.
    """

    def __init__(self, parser: "Parser") -> None:
        self._parser = parser

    def parse(self, path: str | Path) -> SourceDocument:
        """Parse ``path`` and return the ingested :class:`SourceDocument`.

        Delegates to the injected parser and returns the document root.
        Structural ``SourceBlock`` extraction is handled by downstream use
        cases; this method surfaces the document-level metadata.

        Args:
            path: Path to a source document accepted by the injected parser.

        Raises:
            Whatever the parser raises on unreadable/invalid input (e.g.
            :class:`law_nexus.adapters.parsers.ConsultantParseError` for the
            Consultant adapter). The use case does not swallow adapter errors.
        """

        document, _blocks = self._parser.parse(str(path))
        return document
