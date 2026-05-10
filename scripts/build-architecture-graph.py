#!/usr/bin/env python3
"""Build a derived, non-authoritative NetworkX architecture graph from S02 JSONL."""

from __future__ import annotations

import argparse
import json
import sys
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
