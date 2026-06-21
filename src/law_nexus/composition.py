"""Composition root — factory functions wiring adapters into use cases.

[bounded] D046 composition-layer lifecycle tag. This is **not** a
dependency-injection framework: it is a small set of explicit factory
functions that construct application use cases with concrete adapters. Each
factory is a single, readable wiring statement.

Conformance note:
    ``ConsultantWordMLParser`` is asserted to structurally satisfy the
    :class:`law_nexus.ports.parser.Parser` protocol by assigning it to a
    ``Parser``-typed alias; basedpyright enforces this statically. At runtime
    the protocol is structural (duck-typed), so no ``isinstance`` check is
    required for the happy path.
"""

from __future__ import annotations

from pathlib import Path

from law_nexus.adapters.parsers import ConsultantWordMLParser
from law_nexus.application.ingest import Ingest
from law_nexus.ports.parser import Parser


def make_consultant_parser(source_root: str | Path = "law-source") -> ConsultantWordMLParser:
    """Build a :class:`ConsultantWordMLParser` rooted at ``source_root``."""

    return ConsultantWordMLParser(source_root=str(source_root))


def make_default_ingest(source_root: str | Path = "law-source") -> Ingest:
    """Build the default :class:`Ingest` wired with the Consultant parser.

    The default parser is the real Consultant WordML adapter
    (:class:`ConsultantWordMLParser`), which satisfies the :class:`Parser`
    protocol. Use this for the canonical end-to-end ingest path over the
    ``law-source/consultant`` fixtures.
    """

    parser: Parser = make_consultant_parser(source_root=source_root)
    return Ingest(parser)
