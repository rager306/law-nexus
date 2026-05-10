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
