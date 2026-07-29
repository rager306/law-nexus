"""law_nexus.adapters.sources — source discovery and inventory adapters."""

from __future__ import annotations

from law_nexus.adapters.sources.consultant_hierarchy import ConsultantHierarchyRecordBuilder
from law_nexus.adapters.sources.filesystem_inventory import (
    FilesystemParserFixtureInventory,
    InventoryError,
    build_parser_fixture_inventory,
)
from law_nexus.adapters.sources.glossary_candidates import (
    RegexGlossaryCandidateExtractor,
    normalize_glossary_term,
)

__all__ = [
    "ConsultantHierarchyRecordBuilder",
    "FilesystemParserFixtureInventory",
    "InventoryError",
    "RegexGlossaryCandidateExtractor",
    "build_parser_fixture_inventory",
    "normalize_glossary_term",
]
