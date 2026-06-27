"""Parser fixture inventory use case.

[bounded] application-layer seam for M076 S02. The use case depends on a
``ParserFixtureInventoryBuilder`` port and does not know whether the inventory
comes from the filesystem, a test fixture, or a future source repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from law_nexus.ports.source_inventory import ParserFixtureInventoryBuilder


@dataclass(frozen=True)
class ParserInventoryUseCase:
    """Build parser fixture inventory manifests through an injected port."""

    builder: ParserFixtureInventoryBuilder

    def build_parser_fixture_inventory(self, root: Path) -> dict[str, Any]:
        """Build a deterministic parser fixture inventory manifest for ``root``."""
        return self.builder.build_parser_fixture_inventory(root)
