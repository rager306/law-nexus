#!/usr/bin/env python3
"""Build a derived, non-authoritative NetworkX architecture graph from S02 JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Literal

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ITEMS_PATH = ROOT / "prd/architecture/architecture_items.jsonl"
DEFAULT_EDGES_PATH = ROOT / "prd/architecture/architecture_edges.jsonl"
DEFAULT_REPORT_JSON_PATH = ROOT / "prd/architecture/architecture_graph_report.json"
DEFAULT_REPORT_MD_PATH = ROOT / "prd/architecture/architecture_report.md"
DEFAULT_SCHEMA_PATH = ROOT / "prd/architecture/architecture.schema.json"
RecordKind = Literal["item", "edge"]


class ArchitectureGraphError(Exception):
    """Raised for deterministic, user-actionable graph loading/build failures."""


@dataclass(frozen=True)
class LocatedRecord:
    path: Path
    line_number: int
    record: dict[str, Any]

    @property
    def record_id(self) -> str:
        value = self.record.get("id")
        return value if isinstance(value, str) and value else "<missing-id>"

    @property
    def record_kind(self) -> str:
        value = self.record.get("record_kind")
        return value if isinstance(value, str) and value else "<missing-record-kind>"

    def diagnostic(self, rule: str, message: str, **context: str) -> str:
        context_text = " ".join(f"{key}={value}" for key, value in sorted(context.items()))
        suffix = f" {context_text}" if context_text else ""
        return (
            f"{display_path(self.path)}:{self.line_number} "
            f"id={self.record_id} record_kind={self.record_kind} "
            f"rule={rule} message={message}{suffix}"
        )


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[LocatedRecord]:
    located: list[LocatedRecord] = []
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        raise ArchitectureGraphError(
            f"{display_path(path)}:0 id=<none> record_kind=<none> "
            f"rule=read-jsonl message={exc}"
        ) from exc

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except JSONDecodeError as exc:
            raise ArchitectureGraphError(
                f"{display_path(path)}:{line_number} id=<unknown> record_kind=<unknown> "
                f"rule=malformed-jsonl message={exc.msg}"
            ) from exc
        if not isinstance(record, dict):
            raise ArchitectureGraphError(
                f"{display_path(path)}:{line_number} id=<unknown> record_kind=<unknown> "
                "rule=jsonl-object message=expected each JSONL record to be an object"
            )
        located.append(LocatedRecord(path=path, line_number=line_number, record=record))
    return located


def load_records(path: Path, *, expected_kind: RecordKind) -> list[dict[str, Any]]:
    located_records = load_jsonl(path)
    seen_ids: dict[str, LocatedRecord] = {}

    for located in located_records:
        record_id = located.record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ArchitectureGraphError(
                located.diagnostic("record-id", "expected non-empty string record id")
            )
        if located.record_kind != expected_kind:
            raise ArchitectureGraphError(
                located.diagnostic(
                    "record-kind",
                    f"expected record_kind={expected_kind}",
                    expected_record_kind=expected_kind,
                )
            )
        if record_id in seen_ids:
            first = seen_ids[record_id]
            raise ArchitectureGraphError(
                located.diagnostic(
                    "duplicate-id",
                    "record id already appeared in this file",
                    first_line=str(first.line_number),
                )
            )
        seen_ids[record_id] = located

    return [located.record for located in sorted(located_records, key=record_sort_key)]


def record_sort_key(located: LocatedRecord) -> tuple[str, int]:
    return (located.record_id, located.line_number)


def build_graph(items: list[dict[str, Any]], edges: list[dict[str, Any]]) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    item_ids: set[str] = set()

    for item in sorted(items, key=record_id_sort_key):
        item_id = require_record_string(item, "id", "item")
        record_kind = item.get("record_kind")
        if record_kind != "item":
            raise ArchitectureGraphError(
                f"id={item_id} record_kind={record_kind} rule=record-kind "
                "message=build_graph expected item records"
            )
        if item_id in item_ids:
            raise ArchitectureGraphError(
                f"id={item_id} record_kind=item rule=duplicate-id "
                "message=duplicate item id passed to build_graph"
            )
        item_ids.add(item_id)
        graph.add_node(item_id, record=item)

    for edge in sorted(edges, key=record_id_sort_key):
        edge_id = require_record_string(edge, "id", "edge")
        record_kind = edge.get("record_kind")
        if record_kind != "edge":
            raise ArchitectureGraphError(
                f"id={edge_id} record_kind={record_kind} rule=record-kind "
                "message=build_graph expected edge records"
            )
        from_id = require_record_string(edge, "from", edge_id)
        to_id = require_record_string(edge, "to", edge_id)
        missing = sorted(endpoint for endpoint in (from_id, to_id) if endpoint not in item_ids)
        if missing:
            missing_text = ",".join(missing)
            raise ArchitectureGraphError(
                f"id={edge_id} record_kind=edge rule=missing-endpoint "
                f"message=edge references absent endpoint missing_node={missing_text}"
            )
        graph.add_edge(from_id, to_id, key=edge_id, record=edge)

    return graph



def compute_graph_report(
    graph: nx.MultiDiGraph, *, schema_path: Path = DEFAULT_SCHEMA_PATH
) -> dict[str, Any]:
    """Compute deterministic, non-authoritative graph-health findings."""
    layer_enum = load_schema_enum(schema_path, "layer")
    status_enum = set(load_schema_enum(schema_path, "item_status"))
    proof_level_enum = set(load_schema_enum(schema_path, "proof_level"))

    node_records = sorted_node_records(graph)
    edge_records = sorted_edge_records(graph)
    invalid_records: list[dict[str, Any]] = []
    layer_counts: Counter[str] = Counter()
    invalid_layers: list[dict[str, str]] = []
    unresolved_proof_gates: list[dict[str, str]] = []
    high_risk_nodes: list[dict[str, str]] = []
    non_claim_nodes: list[dict[str, Any]] = []
    orphan_findings: list[dict[str, str]] = []

    for node_id in sorted(graph.nodes, key=str):
        record = graph.nodes[node_id].get("record")
        if not isinstance(record, dict):
            orphan_findings.append({"id": str(node_id), "rule": "node-without-record"})
            invalid_records.append({"id": str(node_id), "rule": "missing-node-record"})

    for node_id, record in node_records:
        layer = record.get("layer")
        if isinstance(layer, str) and layer in layer_enum:
            layer_counts[layer] += 1
        else:
            layer_text = layer if isinstance(layer, str) else "<missing-layer>"
            invalid_layers.append({"id": node_id, "layer": layer_text})
            invalid_records.append({"id": node_id, "rule": "invalid-layer", "value": layer_text})

        status = record.get("status")
        if not isinstance(status, str):
            invalid_records.append({"id": node_id, "rule": "missing-status"})
        elif status not in status_enum:
            invalid_records.append({"id": node_id, "rule": "invalid-status", "value": status})

        proof_level = record.get("proof_level")
        if not isinstance(proof_level, str):
            invalid_records.append({"id": node_id, "rule": "missing-proof-level"})
        elif proof_level not in proof_level_enum:
            invalid_records.append({"id": node_id, "rule": "invalid-proof-level", "value": proof_level})

        if record.get("type") == "proof_gate" and status == "active" and proof_level == "none":
            unresolved_proof_gates.append(
                {
                    "id": node_id,
                    "owner": string_or_placeholder(record.get("owner"), "<missing-owner>"),
                    "status": "active",
                    "proof_level": "none",
                    "layer": string_or_placeholder(layer, "<missing-layer>"),
                    "risk_level": string_or_placeholder(record.get("risk_level"), "<missing-risk-level>"),
                    "verification": string_or_placeholder(
                        record.get("verification"), "<missing-verification>"
                    ),
                }
            )

        if record.get("risk_level") in {"high", "critical"}:
            high_risk_nodes.append(
                {
                    "id": node_id,
                    "risk_level": string_or_placeholder(
                        record.get("risk_level"), "<missing-risk-level>"
                    ),
                    "type": string_or_placeholder(record.get("type"), "<missing-type>"),
                    "layer": string_or_placeholder(layer, "<missing-layer>"),
                    "status": string_or_placeholder(status, "<missing-status>"),
                    "proof_level": string_or_placeholder(proof_level, "<missing-proof-level>"),
                }
            )

        non_claims = record.get("non_claims")
        if isinstance(non_claims, list) and non_claims:
            non_claim_nodes.append(
                {
                    "id": node_id,
                    "count": len(non_claims),
                    "non_claims": sorted(str(value) for value in non_claims),
                }
            )

    isolates = sorted(str(node) for node in nx.isolates(graph))
    for node_id in isolates:
        orphan_findings.append({"id": node_id, "rule": "isolated-node"})

    contradiction_edges = collect_contradiction_edges(edge_records)
    contradiction_pairs = collect_contradiction_pairs(contradiction_edges)

    return {
        "non_authoritative": True,
        "counts": {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()},
        "layer_coverage": {
            "counts": {layer: layer_counts.get(layer, 0) for layer in layer_enum},
            "missing_layers": [layer for layer in layer_enum if layer_counts.get(layer, 0) == 0],
            "invalid_layers": sorted(invalid_layers, key=lambda item: item["id"]),
        },
        "unresolved_proof_gates": sorted(unresolved_proof_gates, key=lambda item: item["id"]),
        "isolates": isolates,
        "weak_components": collect_weak_components(graph),
        "contradiction_edges": contradiction_edges,
        "contradiction_pairs": contradiction_pairs,
        "high_risk_nodes": sorted(high_risk_nodes, key=lambda item: item["id"]),
        "orphan_findings": sorted(orphan_findings, key=lambda item: (item["id"], item["rule"])),
        "invalid_records": sorted(invalid_records, key=lambda item: (item["id"], item["rule"])),
        "non_claims_summary": {
            "nodes_with_non_claims": len(non_claim_nodes),
            "total_non_claims": sum(item["count"] for item in non_claim_nodes),
            "by_node": sorted(non_claim_nodes, key=lambda item: item["id"]),
        },
    }


def load_schema_enum(schema_path: Path, def_name: str) -> list[str]:
    try:
        schema = json.loads(schema_path.read_text())
    except (OSError, JSONDecodeError) as exc:
        raise ArchitectureGraphError(
            f"{display_path(DEFAULT_SCHEMA_PATH)}:0 rule=schema-read "
            f"actual_schema={display_path(schema_path)} message={exc}"
        ) from exc
    enum = schema.get("$defs", {}).get(def_name, {}).get("enum")
    if not isinstance(enum, list) or not all(isinstance(value, str) for value in enum):
        raise ArchitectureGraphError(
            f"{display_path(DEFAULT_SCHEMA_PATH)}:0 rule=schema-{def_name.replace('_', '-')}-enum "
            f"actual_schema={display_path(schema_path)} message=expected $defs.{def_name}.enum"
        )
    return sorted(enum)


def sorted_node_records(graph: nx.MultiDiGraph) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    for node_id, data in graph.nodes(data=True):
        record = data.get("record")
        if isinstance(record, dict):
            records.append((str(node_id), record))
    return sorted(records, key=lambda item: item[0])


def sorted_edge_records(graph: nx.MultiDiGraph) -> list[tuple[str, str, str, dict[str, Any]]]:
    records: list[tuple[str, str, str, dict[str, Any]]] = []
    for from_id, to_id, key, data in graph.edges(keys=True, data=True):
        record = data.get("record")
        if isinstance(record, dict):
            edge_id = record.get("id") if isinstance(record.get("id"), str) else str(key)
            records.append((edge_id, str(from_id), str(to_id), record))
    return sorted(records, key=lambda item: item[0])


def string_or_placeholder(value: Any, placeholder: str) -> str:
    return value if isinstance(value, str) and value else placeholder


def collect_weak_components(graph: nx.MultiDiGraph) -> list[dict[str, Any]]:
    components = []
    for nodes in nx.weakly_connected_components(graph):
        sorted_nodes = sorted(str(node) for node in nodes)
        components.append({"size": len(sorted_nodes), "nodes": sorted_nodes})
    return sorted(components, key=lambda item: (item["nodes"][0] if item["nodes"] else "", item["size"]))


def collect_contradiction_edges(
    edge_records: list[tuple[str, str, str, dict[str, Any]]],
) -> list[dict[str, str]]:
    contradiction_edges = []
    for edge_id, from_id, to_id, record in edge_records:
        if record.get("type") != "contradicts":
            continue
        contradiction_edges.append(
            {
                "id": edge_id,
                "from": from_id,
                "to": to_id,
                "status": string_or_placeholder(record.get("status"), "<missing-status>"),
                "rationale": string_or_placeholder(record.get("rationale"), "<missing-rationale>"),
            }
        )
    return contradiction_edges


def collect_contradiction_pairs(
    contradiction_edges: list[dict[str, str]],
) -> list[dict[str, Any]]:
    pair_edges: dict[tuple[str, str], list[str]] = defaultdict(list)
    for edge in contradiction_edges:
        left, right = sorted([edge["from"], edge["to"]])
        pair_edges[(left, right)].append(edge["id"])
    return [
        {"from": left, "to": right, "edge_ids": sorted(edge_ids)}
        for (left, right), edge_ids in sorted(pair_edges.items())
    ]


def record_id_sort_key(record: dict[str, Any]) -> str:
    value = record.get("id")
    return value if isinstance(value, str) else ""


def require_record_string(record: dict[str, Any], field: str, record_label: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        record_id = record.get("id", record_label)
        record_kind = record.get("record_kind", "<missing-record-kind>")
        raise ArchitectureGraphError(
            f"id={record_id} record_kind={record_kind} rule=required-field "
            f"field={field} message=expected non-empty string"
        )
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a derived, non-authoritative NetworkX architecture graph from S02 JSONL. "
            "Report rendering and stale-output checks are completed in later S03 tasks."
        )
    )
    parser.add_argument("--items", type=Path, default=DEFAULT_ITEMS_PATH)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES_PATH)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate inputs and graph shape without writing outputs; stale report checks are a T03 seam.",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        items = load_records(args.items, expected_kind="item")
        edges = load_records(args.edges, expected_kind="edge")
        graph = build_graph(items, edges)
    except ArchitectureGraphError as exc:
        print(f"architecture graph error: {exc}", file=sys.stderr)
        return 1

    summary = {
        "status": "ok",
        "mode": "check" if args.check else "build-skeleton",
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "report_json": str(args.report_json),
        "report_md": str(args.report_md),
        "non_authoritative": True,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
