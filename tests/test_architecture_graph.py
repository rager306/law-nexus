from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/build-architecture-graph.py"
ITEMS_PATH = ROOT / "prd/architecture/architecture_items.jsonl"
EDGES_PATH = ROOT / "prd/architecture/architecture_edges.jsonl"
SCHEMA_PATH = ROOT / "prd/architecture/architecture.schema.json"


def load_graph_module() -> Any:
    spec = importlib.util.spec_from_file_location("architecture_graph", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records))


def test_builds_current_registry_as_keyed_multidigraph() -> None:
    graph_module = load_graph_module()

    items = graph_module.load_records(ITEMS_PATH, expected_kind="item")
    edges = graph_module.load_records(EDGES_PATH, expected_kind="edge")
    graph = graph_module.build_graph(items, edges)

    assert graph.number_of_nodes() == 23
    assert graph.number_of_edges() == 17
    assert graph.is_multigraph()

    edge = edges[0]
    assert graph.has_edge(edge["from"], edge["to"], key=edge["id"])
    assert graph.edges[edge["from"], edge["to"], edge["id"]]["record"] == edge
    assert graph.nodes[items[0]["id"]]["record"] == items[0]


def test_networkx_imports_under_uv_run() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "-c", "import networkx; print(networkx.__version__)"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_rejects_duplicate_ids_with_file_record_and_rule_context(tmp_path: Path) -> None:
    graph_module = load_graph_module()
    items_path = tmp_path / "items.jsonl"
    write_jsonl(
        items_path,
        [
            {"record_kind": "item", "id": "DUPLICATE", "title": "first"},
            {"record_kind": "item", "id": "DUPLICATE", "title": "second"},
        ],
    )

    with pytest.raises(graph_module.ArchitectureGraphError) as exc_info:
        graph_module.load_records(items_path, expected_kind="item")

    diagnostic = str(exc_info.value)
    assert "items.jsonl:2" in diagnostic
    assert "id=DUPLICATE" in diagnostic
    assert "rule=duplicate-id" in diagnostic


def test_rejects_wrong_record_kind_with_file_record_and_rule_context(tmp_path: Path) -> None:
    graph_module = load_graph_module()
    items_path = tmp_path / "items.jsonl"
    write_jsonl(items_path, [{"record_kind": "edge", "id": "EDGE-WRONG"}])

    with pytest.raises(graph_module.ArchitectureGraphError) as exc_info:
        graph_module.load_records(items_path, expected_kind="item")

    diagnostic = str(exc_info.value)
    assert "items.jsonl:1" in diagnostic
    assert "id=EDGE-WRONG" in diagnostic
    assert "record_kind=edge" in diagnostic
    assert "rule=record-kind" in diagnostic


def test_rejects_missing_edge_endpoints_with_edge_and_node_context() -> None:
    graph_module = load_graph_module()
    items = [{"record_kind": "item", "id": "NODE-A"}]
    edges = [
        {
            "record_kind": "edge",
            "id": "EDGE-MISSING-ENDPOINT",
            "from": "NODE-A",
            "to": "NODE-MISSING",
        }
    ]

    with pytest.raises(graph_module.ArchitectureGraphError) as exc_info:
        graph_module.build_graph(items, edges)

    diagnostic = str(exc_info.value)
    assert "id=EDGE-MISSING-ENDPOINT" in diagnostic
    assert "missing_node=NODE-MISSING" in diagnostic
    assert "rule=missing-endpoint" in diagnostic


def test_rejects_malformed_jsonl_with_file_and_line_context(tmp_path: Path) -> None:
    graph_module = load_graph_module()
    items_path = tmp_path / "items.jsonl"
    items_path.write_text('{"record_kind": "item", "id": "OK"}\n{"record_kind":')

    with pytest.raises(graph_module.ArchitectureGraphError) as exc_info:
        graph_module.load_records(items_path, expected_kind="item")

    diagnostic = str(exc_info.value)
    assert "items.jsonl:2" in diagnostic
    assert "rule=malformed-jsonl" in diagnostic






def test_rejects_malformed_jsonl_at_cli_with_nonzero_diagnostic(tmp_path: Path) -> None:
    items_path = tmp_path / "items.jsonl"
    edges_path = tmp_path / "edges.jsonl"
    items_path.write_text('{"record_kind": "item", "id": "OK"}\n{"record_kind":')
    edges_path.write_text("")

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(SCRIPT_PATH),
            "--items",
            str(items_path),
            "--edges",
            str(edges_path),
            "--check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "architecture graph error:" in result.stderr
    assert "items.jsonl:2" in result.stderr
    assert "rule=malformed-jsonl" in result.stderr


def test_report_current_registry_exposes_baseline_graph_health() -> None:
    graph_module = load_graph_module()

    items = graph_module.load_records(ITEMS_PATH, expected_kind="item")
    edges = graph_module.load_records(EDGES_PATH, expected_kind="edge")
    graph = graph_module.build_graph(items, edges)
    report = graph_module.compute_graph_report(graph, schema_path=SCHEMA_PATH)

    assert report["counts"] == {"nodes": 23, "edges": 17}
    assert report["layer_coverage"]["missing_layers"] == [
        "api-product",
        "legal-evidence",
        "observability-operability",
    ]
    assert report["layer_coverage"]["counts"]["architecture-governance"] == 7
    assert [gate["id"] for gate in report["unresolved_proof_gates"]] == [
        "GATE-G005",
        "GATE-G008",
        "GATE-G011",
        "GATE-G015",
    ]
    assert report["contradiction_edges"] == []
    assert report["contradiction_pairs"] == []
    assert report["invalid_records"] == []
    assert [node["id"] for node in report["high_risk_nodes"]][:3] == [
        "ASSUMP-PRD-SOURCE-TRUTH",
        "CHECK-ARCHITECTURE-EXTRACTOR",
        "DEC-D031",
    ]
    assert len(report["high_risk_nodes"]) == 15
    assert report["non_claims_summary"]["nodes_with_non_claims"] == 23
    assert report["non_claims_summary"]["total_non_claims"] > 23


def test_report_handles_empty_graph_with_schema_layer_contract() -> None:
    graph_module = load_graph_module()

    report = graph_module.compute_graph_report(graph_module.nx.MultiDiGraph(), schema_path=SCHEMA_PATH)

    assert report["counts"] == {"nodes": 0, "edges": 0}
    assert report["layer_coverage"]["missing_layers"] == [
        "api-product",
        "architecture-governance",
        "generated-cypher",
        "graph-runtime",
        "legal-evidence",
        "observability-operability",
        "parser-ingestion",
        "retrieval-embedding",
        "security-safety",
        "temporal-model",
        "workflow-governance",
    ]
    assert report["weak_components"] == []
    assert report["isolates"] == []


def test_report_flags_contradiction_edges_and_pairs_without_inference() -> None:
    graph_module = load_graph_module()
    graph = graph_module.build_graph(
        [
            {
                "record_kind": "item",
                "id": "NODE-A",
                "type": "requirement",
                "layer": "api-product",
                "status": "active",
                "proof_level": "source-anchor",
                "risk_level": "medium",
                "owner": "owner-a",
                "non_claims": [],
                "title": "A",
            },
            {
                "record_kind": "item",
                "id": "NODE-B",
                "type": "requirement",
                "layer": "api-product",
                "status": "active",
                "proof_level": "source-anchor",
                "risk_level": "medium",
                "owner": "owner-b",
                "non_claims": [],
                "title": "B",
            },
        ],
        [
            {
                "record_kind": "edge",
                "id": "EDGE-CONTRADICTS",
                "from": "NODE-A",
                "to": "NODE-B",
                "type": "contradicts",
                "status": "active",
                "rationale": "A conflicts with B in source-bound architecture review.",
            }
        ],
    )

    report = graph_module.compute_graph_report(graph, schema_path=SCHEMA_PATH)

    assert report["contradiction_edges"] == [
        {
            "id": "EDGE-CONTRADICTS",
            "from": "NODE-A",
            "to": "NODE-B",
            "status": "active",
            "rationale": "A conflicts with B in source-bound architecture review.",
        }
    ]
    assert report["contradiction_pairs"] == [
        {"from": "NODE-A", "to": "NODE-B", "edge_ids": ["EDGE-CONTRADICTS"]}
    ]


def test_report_flags_orphan_like_missing_endpoint_records_and_invalid_layers() -> None:
    graph_module = load_graph_module()
    graph = graph_module.nx.MultiDiGraph()
    graph.add_node(
        "NODE-A",
        record={
            "record_kind": "item",
            "id": "NODE-A",
            "type": "component",
            "layer": "not-a-schema-layer",
            "status": "active",
            "proof_level": "source-anchor",
            "risk_level": "medium",
            "owner": "owner-a",
            "non_claims": [],
            "title": "A",
        },
    )
    graph.add_edge(
        "NODE-A",
        "NODE-MISSING-RECORD",
        key="EDGE-MISSING-RECORD",
        record={
            "record_kind": "edge",
            "id": "EDGE-MISSING-RECORD",
            "from": "NODE-A",
            "to": "NODE-MISSING-RECORD",
            "type": "depends_on",
            "status": "active",
        },
    )

    report = graph_module.compute_graph_report(graph, schema_path=SCHEMA_PATH)

    assert report["layer_coverage"]["invalid_layers"] == [
        {"id": "NODE-A", "layer": "not-a-schema-layer"}
    ]
    assert report["orphan_findings"] == [
        {"id": "NODE-MISSING-RECORD", "rule": "node-without-record"}
    ]
    assert {finding["rule"] for finding in report["invalid_records"]} == {
        "invalid-layer",
        "missing-node-record",
    }


def test_report_rejects_schema_without_layer_enum(tmp_path: Path) -> None:
    graph_module = load_graph_module()
    schema_path = tmp_path / "architecture.schema.json"
    schema_path.write_text(json.dumps({"$defs": {"layer": {"type": "string"}}}))

    with pytest.raises(graph_module.ArchitectureGraphError) as exc_info:
        graph_module.compute_graph_report(graph_module.nx.MultiDiGraph(), schema_path=schema_path)

    diagnostic = str(exc_info.value)
    assert "prd/architecture/architecture.schema.json" in diagnostic
    assert "rule=schema-layer-enum" in diagnostic


def test_report_records_unresolved_gate_owner_status_and_invalid_missing_fields() -> None:
    graph_module = load_graph_module()
    graph = graph_module.nx.MultiDiGraph()
    graph.add_node(
        "GATE-MISSING-OWNER",
        record={
            "record_kind": "item",
            "id": "GATE-MISSING-OWNER",
            "type": "proof_gate",
            "layer": "graph-runtime",
            "status": "active",
            "proof_level": "none",
            "risk_level": "high",
            "non_claims": ["Not product runtime proof."],
            "title": "Missing owner gate",
            "verification": "future proof",
        },
    )
    graph.add_node(
        "GATE-MISSING-STATUS",
        record={
            "record_kind": "item",
            "id": "GATE-MISSING-STATUS",
            "type": "proof_gate",
            "layer": "graph-runtime",
            "proof_level": "none",
            "risk_level": "high",
            "owner": "owner-b",
            "non_claims": [],
            "title": "Missing status gate",
            "verification": "future proof",
        },
    )

    report = graph_module.compute_graph_report(graph, schema_path=SCHEMA_PATH)

    assert report["unresolved_proof_gates"] == [
        {
            "id": "GATE-MISSING-OWNER",
            "owner": "<missing-owner>",
            "status": "active",
            "proof_level": "none",
            "layer": "graph-runtime",
            "risk_level": "high",
            "verification": "future proof",
        }
    ]
    assert {finding["rule"] for finding in report["invalid_records"]} == {"missing-status"}
