from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-falkordb-bulk-loader-proof.py"

FORBIDDEN_SNIPPETS = {
    "Федеральный закон",
    "Статья",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
}


def load_module(name: str = "bulk_loader_proof") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Args:
    container = "auto"
    container_image = "falkordb/falkordb:edge"


def test_fixture_counts_match_load_csv_baseline() -> None:
    module = load_module("bulk_counts")

    assert module.expected_counts() == {
        "expected_source_node_rows": 4,
        "expected_source_relationship_rows": 3,
        "expected_node_count": 4,
        "expected_relationship_count": 3,
        "expected_current_nodes": 3,
        "expected_inactive_nodes": 1,
    }


def test_bulk_csv_generation_uses_schema_headers(tmp_path: Path) -> None:
    module = load_module("bulk_schema")

    nodes_path, rels_path = module.write_bulk_csvs(tmp_path)

    nodes_header = nodes_path.read_text().splitlines()[0]
    rels_header = rels_path.read_text().splitlines()[0]
    assert ":ID(LegalUnit)" in nodes_header
    assert "kind:STRING" in nodes_header
    assert ":START_ID(LegalUnit)" in rels_header
    assert ":END_ID(LegalUnit)" in rels_header
    assert len(nodes_path.read_text().splitlines()) == 5
    assert len(rels_path.read_text().splitlines()) == 4


def test_base_report_is_safe_and_non_authoritative() -> None:
    module = load_module("bulk_safe_report")

    report = module.base_report(Args(), "bulk_loader_passed", [])
    report["graph_counts"] = {
        "node_count": 4,
        "relationship_count": 3,
        "current_nodes": 3,
        "inactive_nodes": 1,
    }

    module.assert_safe_payload(report)
    serialized = json.dumps(report, ensure_ascii=False)
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in serialized
    assert report["schema_version"] == "falkordb-bulk-loader-proof/v1"
    assert report["loader"]["command"] == "falkordb-bulk-insert"
    assert report["loader"]["uses_graph_bulk"] is True
    assert report["loader"]["create_new_graph_semantics"] is True
    assert report["loader"]["idempotent_update_claimed"] is False
    assert any("Does not validate R035" in claim for claim in report["non_claims"])


def test_compare_counts_reports_bulk_mismatch() -> None:
    module = load_module("bulk_mismatch")

    report: dict[str, Any] = module.base_report(Args(), "bulk_loader_passed", [])
    report["graph_counts"] = {
        "node_count": 4,
        "relationship_count": 2,
        "current_nodes": 3,
        "inactive_nodes": 1,
    }

    assert module.compare_counts(report) == ["BULK_LOADER_COUNTS_MISMATCH"]
