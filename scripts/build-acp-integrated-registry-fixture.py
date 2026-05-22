#!/usr/bin/env python3
"""Build and validate a custom ACP integrated architecture registry fixture.

This script combines the current generated architecture registry JSONL records
with ACP canonical-shaped custom projection records under ACP derived paths. It
never writes the tracked canonical registry files.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
CANONICAL_EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"
ACP_ITEMS = ROOT / "prd/architecture/acp/derived/canonical-projection.items.jsonl"
ACP_EDGES = ROOT / "prd/architecture/acp/derived/canonical-projection.edges.jsonl"
DEFAULT_ITEMS_OUTPUT = ROOT / "prd/architecture/acp/derived/integrated-registry.items.jsonl"
DEFAULT_EDGES_OUTPUT = ROOT / "prd/architecture/acp/derived/integrated-registry.edges.jsonl"
CANONICAL_REGISTRY_PATHS = {CANONICAL_ITEMS.resolve(), CANONICAL_EDGES.resolve()}
FORBIDDEN_MARKERS = (
    "GIGACHAT" + "_AUTH_DATA",
    "MINIMAX" + "_API_KEY=",
    "OPENAI" + "_API_KEY=",
    "sk-",
    "R035 is validated",
    "R037 is validated",
    "R038 is validated",
    "validates parser completeness",
    "validates FalkorDB ingestion",
    "proves legal correctness",
    "graph-context staging is FalkorDB ingestion",
    "MiniMax is authoritative",
    "external AI dialogue is authority",
    "visualization validates architecture",
    "/root/",
    ".gsd/exec",
)
REQUIRED_NON_CLAIMS = (
    "Does not validate R035.",
    "Does not validate R037.",
    "Does not validate R038.",
)


@dataclass(frozen=True)
class Diagnostic:
    rule: str
    message: str
    path: Path
    record_id: str = "<none>"
    field: str = "<none>"

    def to_json(self) -> dict[str, str]:
        return {
            "rule": self.rule,
            "message": self.message,
            "path": display_path(self.path),
            "record_id": self.record_id,
            "field": self.field,
        }


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def normalized_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def is_canonical_registry_path(path: Path) -> bool:
    return normalized_path(path).resolve() in CANONICAL_REGISTRY_PATHS


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    records: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    if not path.exists():
        return records, [Diagnostic("missing-file", "input file is missing", path)]
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            diagnostics.append(Diagnostic("jsonl-parse", f"invalid JSON on line {line_number}: {exc.msg}", path))
            continue
        if not isinstance(record, dict):
            diagnostics.append(Diagnostic("jsonl-record", "JSONL record must be an object", path, field=str(line_number)))
            continue
        records.append(record)
    return records, diagnostics


def expected_jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if is_canonical_registry_path(path):
        raise ValueError("refusing to write canonical architecture registry file")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected_jsonl_text(records), encoding="utf-8")


def check_jsonl(path: Path, records: list[dict[str, Any]]) -> tuple[bool, str]:
    if not path.exists():
        return False, "output file does not exist"
    if path.read_text(encoding="utf-8") != expected_jsonl_text(records):
        return False, "output file is stale"
    return True, "output file is current"


def safe_repo_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\x00" in value:
        return False
    parts = Path(value).parts
    return ".." not in parts and not value.startswith(".gsd/exec")


def validate_source_anchors(record: dict[str, Any], path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    record_id = str(record.get("id", "<missing-id>"))
    anchors = record.get("source_anchors")
    if not isinstance(anchors, list) or not anchors:
        return [Diagnostic("source-anchor", "source_anchors must be a non-empty list", path, record_id, "source_anchors")]
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, dict):
            diagnostics.append(Diagnostic("source-anchor", "source anchor must be an object", path, record_id, f"source_anchors[{index}]"))
            continue
        ref_path = anchor.get("path")
        if not isinstance(ref_path, str) or not safe_repo_relative_path(ref_path):
            diagnostics.append(Diagnostic("source-anchor-path", "source anchor path must be safe and repo-relative", path, record_id, f"source_anchors[{index}].path"))
        elif not (ROOT / ref_path).exists():
            diagnostics.append(Diagnostic("source-anchor-exists", "source anchor path does not exist", path, record_id, f"source_anchors[{index}].path"))
    return diagnostics


def validate_forbidden_text(path: Path) -> list[Diagnostic]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [Diagnostic("forbidden-marker", f"forbidden marker found: {marker}", path) for marker in FORBIDDEN_MARKERS if marker in text]


def validate_integrated_fixture(items: list[dict[str, Any]], edges: list[dict[str, Any]], items_path: Path, edges_path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    item_ids: set[str] = set()
    edge_ids: set[str] = set()

    for item in items:
        item_id = str(item.get("id", "<missing-id>"))
        if item_id in item_ids:
            diagnostics.append(Diagnostic("duplicate-id", "duplicate item id", items_path, item_id, "id"))
        item_ids.add(item_id)
        if item.get("record_kind") != "item":
            diagnostics.append(Diagnostic("record-kind", "item file contains non-item record", items_path, item_id, "record_kind"))
        diagnostics.extend(validate_source_anchors(item, items_path))
        if item_id.startswith("ACP-"):
            non_claims = item.get("non_claims")
            if not isinstance(non_claims, list):
                diagnostics.append(Diagnostic("acp-non-claims", "ACP item non_claims must be a list", items_path, item_id, "non_claims"))
            else:
                for claim in REQUIRED_NON_CLAIMS:
                    if claim not in non_claims:
                        diagnostics.append(Diagnostic("acp-non-claims", f"missing required non-claim: {claim}", items_path, item_id, "non_claims"))
            if item.get("type") == "decision_candidate" and item.get("authority_required") is not True:
                diagnostics.append(Diagnostic("authority-required", "decision_candidate must require authority", items_path, item_id, "authority_required"))

    for edge in edges:
        edge_id = str(edge.get("id", "<missing-id>"))
        if edge_id in edge_ids:
            diagnostics.append(Diagnostic("duplicate-id", "duplicate edge id", edges_path, edge_id, "id"))
        edge_ids.add(edge_id)
        if edge.get("record_kind") != "edge":
            diagnostics.append(Diagnostic("record-kind", "edge file contains non-edge record", edges_path, edge_id, "record_kind"))
        for field in ("from", "to"):
            endpoint = edge.get(field)
            if not isinstance(endpoint, str) or endpoint not in item_ids:
                diagnostics.append(Diagnostic("edge-endpoint", "edge endpoint does not reference an item", edges_path, edge_id, field))
        diagnostics.extend(validate_source_anchors(edge, edges_path))

    diagnostics.extend(validate_forbidden_text(items_path))
    diagnostics.extend(validate_forbidden_text(edges_path))
    return diagnostics


def build_integrated_fixture(
    canonical_items_path: Path,
    canonical_edges_path: Path,
    acp_items_path: Path,
    acp_edges_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Diagnostic]]:
    canonical_items, diagnostics = load_jsonl(canonical_items_path)
    canonical_edges, edge_diagnostics = load_jsonl(canonical_edges_path)
    acp_items, acp_item_diagnostics = load_jsonl(acp_items_path)
    acp_edges, acp_edge_diagnostics = load_jsonl(acp_edges_path)
    diagnostics.extend(edge_diagnostics)
    diagnostics.extend(acp_item_diagnostics)
    diagnostics.extend(acp_edge_diagnostics)
    items = sorted([*canonical_items, *acp_items], key=lambda record: str(record.get("id", "")))
    edges = sorted([*canonical_edges, *acp_edges], key=lambda record: str(record.get("id", "")))
    return items, edges, diagnostics


def run(args: argparse.Namespace) -> dict[str, Any]:
    items, edges, diagnostics = build_integrated_fixture(
        args.canonical_items,
        args.canonical_edges,
        args.acp_items,
        args.acp_edges,
    )
    diagnostics.extend(validate_integrated_fixture(items, edges, args.items_output, args.edges_output))
    status = "ok" if not diagnostics else "failed"

    if not args.check and status == "ok":
        write_jsonl(args.items_output, items)
        write_jsonl(args.edges_output, edges)

    if args.check:
        items_ok, items_message = check_jsonl(args.items_output, items)
        edges_ok, edges_message = check_jsonl(args.edges_output, edges)
        if not items_ok:
            diagnostics.append(Diagnostic("stale-output", items_message, args.items_output))
        if not edges_ok:
            diagnostics.append(Diagnostic("stale-output", edges_message, args.edges_output))
        status = "ok" if not diagnostics else "failed"
    else:
        items_message = "output file written" if status == "ok" else "output file not written"
        edges_message = items_message

    return {
        "status": status,
        "item_count": len(items),
        "edge_count": len(edges),
        "acp_item_count": sum(1 for item in items if str(item.get("id", "")).startswith("ACP-")),
        "acp_edge_count": sum(1 for edge in edges if str(edge.get("id", "")).startswith("ACP-EDGE-")),
        "items_output": display_path(args.items_output),
        "edges_output": display_path(args.edges_output),
        "items_message": items_message,
        "edges_message": edges_message,
        "diagnostic_count": len(diagnostics),
        "diagnostics": [diagnostic.to_json() for diagnostic in diagnostics],
        "boundary": "Custom integrated fixture only; tracked canonical architecture registry files are unchanged.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-items", type=Path, default=CANONICAL_ITEMS)
    parser.add_argument("--canonical-edges", type=Path, default=CANONICAL_EDGES)
    parser.add_argument("--acp-items", type=Path, default=ACP_ITEMS)
    parser.add_argument("--acp-edges", type=Path, default=ACP_EDGES)
    parser.add_argument("--items-output", type=Path, default=DEFAULT_ITEMS_OUTPUT)
    parser.add_argument("--edges-output", type=Path, default=DEFAULT_EDGES_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"status": "failed", "message": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
