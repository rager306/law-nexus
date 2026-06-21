"""law_nexus.adapters.parsers — source-format parsers.

Each parser adapter reads a specific source format and produces a
:class:`law_nexus.domain.SourceDocument`, structurally satisfying the
:class:`law_nexus.ports.parser.Parser` protocol.
"""

from __future__ import annotations

from law_nexus.adapters.parsers.consultant_wordml import (
    ConsultantDocumentType,
    ConsultantParseError,
    ConsultantWordMLParser,
)

__all__ = [
    "ConsultantDocumentType",
    "ConsultantParseError",
    "ConsultantWordMLParser",
]
