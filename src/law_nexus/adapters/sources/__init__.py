"""law_nexus.adapters.sources — source discovery and inventory adapters."""

from __future__ import annotations

from law_nexus.adapters.sources.consultant_hierarchy import ConsultantHierarchyRecordBuilder
from law_nexus.adapters.sources.filesystem_inventory import (
    FilesystemParserFixtureInventory,
    InventoryError,
    build_parser_fixture_inventory,
)

__all__ = [
    "ConsultantHierarchyRecordBuilder",
    "FilesystemParserFixtureInventory",
    "InventoryError",
    "build_parser_fixture_inventory",
]
