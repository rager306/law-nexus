"""Source inventory port contracts.

[proposed] port contract for repository source inventory builders. The port is
pure ``typing.Protocol`` and depends only on stdlib typing/path shapes.
Concrete filesystem discovery belongs in adapters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class ParserFixtureInventoryBuilder(Protocol):
    """Build a parser fixture inventory for a repository root."""

    def build_parser_fixture_inventory(self, root: Path) -> dict[str, Any]:
        """Return a deterministic parser fixture inventory manifest."""
        ...
