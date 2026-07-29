from __future__ import annotations

from pathlib import Path
from typing import Any

from law_nexus.adapters.sources.filesystem_inventory import FilesystemParserFixtureInventory
from law_nexus.application.parser_inventory import ParserInventoryUseCase


class StubParserFixtureInventoryBuilder:
    def __init__(self) -> None:
        self.called_with: Path | None = None

    def build_parser_fixture_inventory(self, root: Path) -> dict[str, Any]:
        self.called_with = root
        return {"status": "pass", "root": str(root)}


def test_parser_inventory_use_case_delegates_to_builder(tmp_path: Path) -> None:
    builder = StubParserFixtureInventoryBuilder()
    use_case = ParserInventoryUseCase(builder=builder)

    manifest = use_case.build_parser_fixture_inventory(tmp_path)

    assert builder.called_with == tmp_path
    assert manifest == {"status": "pass", "root": str(tmp_path)}


def test_filesystem_parser_fixture_inventory_adapter_reports_empty_inventory(
    tmp_path: Path,
) -> None:
    use_case = ParserInventoryUseCase(builder=FilesystemParserFixtureInventory())

    manifest = use_case.build_parser_fixture_inventory(tmp_path)

    assert manifest["schema_version"] == "parser-source-fixture-inventory/v2"
    assert manifest["fixture_count"] == 0
    assert manifest["status"] == "pass"
    assert manifest["fixtures"] == []
