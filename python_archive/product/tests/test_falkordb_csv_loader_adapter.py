from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from law_nexus.adapters.graph.falkordb_csv_loader import (
    FALKORDB_CSV_INGEST_NON_CLAIMS,
    FalkorCsvIngestRequest,
    build_base_report,
    build_load_csv_query_plan,
    compare_graph_counts,
    expected_counts_from_rows,
    read_csv_rows,
    validate_safe_report,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest"
UNITS_CSV = FIXTURE_DIR / "legal_units.csv"
EDGES_CSV = FIXTURE_DIR / "legal_unit_edges.csv"


def test_expected_counts_from_csv_rows_match_existing_contract() -> None:
    units = read_csv_rows(UNITS_CSV)
    edges = read_csv_rows(EDGES_CSV)

    assert expected_counts_from_rows(units, edges) == {
        "expected_source_node_rows": 4,
        "expected_source_relationship_rows": 3,
        "expected_node_count": 4,
        "expected_relationship_count": 3,
        "expected_current_nodes": 3,
        "expected_inactive_nodes": 1,
    }


def test_load_csv_query_plan_is_bounded_and_uses_fixture_import_paths() -> None:
    plan = build_load_csv_query_plan(
        node_csv_uri="file:///legal_units.csv", edge_csv_uri="file:///legal_unit_edges.csv"
    )

    assert [step.name for step in plan.steps] == [
        "cleanup_before_load",
        "load_nodes_first",
        "load_relationships_first",
        "load_nodes_second",
        "load_relationships_second",
    ]
    assert all(
        "LOAD CSV WITH HEADERS" in step.cypher or step.name == "cleanup_before_load"
        for step in plan.steps
    )
    assert all("/root/" not in step.cypher and "/tmp/" not in step.cypher for step in plan.steps)
    assert plan.raw_query_text_persisted is False


def test_base_report_keeps_non_claims_and_safe_counts() -> None:
    request = FalkorCsvIngestRequest(
        source_units_path="prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest/legal_units.csv",
        source_edges_path="prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest/legal_unit_edges.csv",
        container_mode="never",
        container_image="falkordb/falkordb:edge",
    )
    units = read_csv_rows(UNITS_CSV)
    edges = read_csv_rows(EDGES_CSV)

    report = build_base_report(
        request,
        expected_counts=expected_counts_from_rows(units, edges),
        disposition="blocked",
        diagnostic_codes=("CSV_FILE_ACCESS_BLOCKED",),
    )

    assert report["schema_version"] == "falkordb-csv-ingest-proof/v1"
    assert report["loader"]["mechanism"] == "LOAD CSV"
    assert report["loader"]["raw_query_text_persisted"] is False
    assert report["source_counts"] == {"node_rows": 4, "relationship_rows": 3}
    assert report["non_claims"] == list(FALKORDB_CSV_INGEST_NON_CLAIMS)
    validate_safe_report(report)


def test_compare_graph_counts_reports_mismatch_once() -> None:
    expected = {
        "expected_node_count": 4,
        "expected_relationship_count": 3,
        "expected_current_nodes": 3,
        "expected_inactive_nodes": 1,
    }

    assert (
        compare_graph_counts(
            expected,
            {"node_count": 4, "relationship_count": 3, "current_nodes": 3, "inactive_nodes": 1},
        )
        == []
    )
    assert compare_graph_counts(
        expected,
        {"node_count": 1, "relationship_count": 3, "current_nodes": 3, "inactive_nodes": 1},
    ) == ["LOAD_CSV_COUNTS_MISMATCH"]


def test_validate_safe_report_rejects_raw_or_absolute_payloads() -> None:
    with pytest.raises(ValueError):
        validate_safe_report({"unsafe": "raw_legal_text"})
    with pytest.raises(ValueError):
        validate_safe_report({"unsafe": "/tmp/leak"})


def test_request_from_args_preserves_container_boundary() -> None:
    args = SimpleNamespace(container="never", container_image="falkordb/falkordb:edge")
    request = FalkorCsvIngestRequest.from_args(
        args, source_units_path="units.csv", source_edges_path="edges.csv"
    )

    assert request.container_mode == "never"
    assert request.container_image == "falkordb/falkordb:edge"
    assert request.source_units_path == "units.csv"
    assert request.source_edges_path == "edges.csv"
