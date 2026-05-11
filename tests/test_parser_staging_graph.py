from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build-parser-staging-graph.py"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("build_parser_staging_graph", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_multigraph_preserves_real_artifact_counts_and_non_authoritative_state():
    builder = load_builder_module()

    result = builder.build_default_staging_graph()

    assert result.diagnostics == []
    assert isinstance(result.graph, nx.MultiDiGraph)
    assert result.graph.is_multigraph()
    assert result.summary.node_counts == {
        "document": 2,
        "source_block": 48,
        "unresolved_reference": 2,
    }
    assert result.summary.edge_counts == {
        "contains_source_block": 48,
        "relation_candidate": 1,
    }
    assert result.summary.non_authoritative is True
    assert result.summary.relation_candidate_edge_keys == ["REL-CONS-0001"]


def test_keyed_consultant_relation_uses_unresolved_reference_nodes_without_doc_rewrite():
    builder = load_builder_module()

    result = builder.build_default_staging_graph()
    relation = result.graph.get_edge_data(
        "consultant-list:law-source/consultant/Список документов (5).xml",
        "consultant:LAW:179581@11.05.2026",
        key="REL-CONS-0001",
    )

    assert relation is not None
    assert relation["edge_kind"] == "relation_candidate"
    assert relation["record"].id == "REL-CONS-0001"
    assert result.graph.nodes["consultant-list:law-source/consultant/Список документов (5).xml"]["node_kind"] == "unresolved_reference"
    assert result.graph.nodes["consultant:LAW:179581@11.05.2026"]["node_kind"] == "unresolved_reference"
    assert not result.graph.has_edge("DOC-PP-60", "DOC-44-FZ", key="REL-CONS-0001")
    assert not result.graph.has_edge("DOC-44-FZ", "DOC-PP-60", key="REL-CONS-0001")


def test_source_block_records_keep_full_attributes_and_document_order_links():
    builder = load_builder_module()

    result = builder.build_default_staging_graph()
    document_blocks = [
        edge_data["record"].id
        for _, target, key, edge_data in result.graph.out_edges("DOC-44-FZ", keys=True, data=True)
        if edge_data["edge_kind"] == "contains_source_block"
        for node_data in [result.graph.nodes[target]]
        if node_data["record"].document_id == "DOC-44-FZ"
    ]
    ordered_records = [result.graph.nodes[node_id]["record"] for node_id in document_blocks]

    assert document_blocks == sorted(document_blocks, key=lambda block_id: result.graph.nodes[block_id]["record"].order_index)
    assert ordered_records[0].record_kind == "source_block"
    assert ordered_records[0].document_id == "DOC-44-FZ"
    assert ordered_records[0].excerpt
    assert result.graph.nodes["DOC-44-FZ"]["record"].title
    assert result.graph.has_edge("DOC-44-FZ", ordered_records[0].id, key=f"contains:{ordered_records[0].id}")


def test_malformed_jsonl_becomes_path_line_rule_diagnostic(tmp_path: Path):
    builder = load_builder_module()
    malformed = tmp_path / "bad.jsonl"
    missing = tmp_path / "missing.jsonl"
    malformed.write_text('{"record_kind":"document"\n', encoding="utf-8")

    result = builder.build_staging_graph(
        document_records_path=malformed,
        source_block_records_path=missing,
        relation_candidate_records_path=missing,
    )

    assert result.graph.number_of_nodes() == 0
    assert result.diagnostics
    assert {diagnostic.rule for diagnostic in result.diagnostics} >= {"json_invalid", "missing_file"}
    assert any(diagnostic.path == malformed and diagnostic.line == 1 for diagnostic in result.diagnostics)
    assert all(diagnostic.message for diagnostic in result.diagnostics)
