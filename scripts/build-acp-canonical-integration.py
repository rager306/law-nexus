#!/usr/bin/env python3
"""Build opt-in ACP canonical integration proof outputs.

This command is intentionally opt-in. It does not modify the default canonical
architecture extractor, and it refuses tracked canonical registry output paths.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
CANONICAL_EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"
ACP_ITEMS = ROOT / "prd/architecture/acp/derived/canonical-projection.items.jsonl"
ACP_EDGES = ROOT / "prd/architecture/acp/derived/canonical-projection.edges.jsonl"
DEFAULT_ITEMS_OUTPUT = ROOT / "prd/architecture/acp/derived/canonical-integration.items.jsonl"
DEFAULT_EDGES_OUTPUT = ROOT / "prd/architecture/acp/derived/canonical-integration.edges.jsonl"
DEFAULT_REPORT_OUTPUT = ROOT / "prd/architecture/acp/derived/canonical-integration-report.json"
DEFAULT_GRAPH_REPORT_JSON = ROOT / "prd/architecture/acp/derived/canonical-integration-graph-report.json"
DEFAULT_GRAPH_REPORT_MD = ROOT / "prd/architecture/acp/derived/canonical-integration-graph-report.md"
CANONICAL_REGISTRY_PATHS = {CANONICAL_ITEMS.resolve(), CANONICAL_EDGES.resolve()}
REQUIRED_NON_CLAIMS = (
    "Does not validate R035.",
    "Does not validate R037.",
    "Does not validate R038.",
)
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


def safe_repo_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\x00" in value:
        return False
    parts = Path(value).parts
    return ".." not in parts and not value.startswith(".gsd/exec")


def is_tracked_repo_path(repo_relative_path: str) -> bool:
    if not safe_repo_relative_path(repo_relative_path):
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", repo_relative_path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


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


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)


def stable_json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_output(path: Path, text: str) -> None:
    if is_canonical_registry_path(path):
        raise ValueError("refusing to write canonical architecture registry file")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def check_output(path: Path, expected: str) -> tuple[bool, str]:
    if not path.exists():
        return False, "output file does not exist"
    if path.read_text(encoding="utf-8") != expected:
        return False, "output file is stale"
    return True, "output file is current"


def validate_forbidden_text(path: Path) -> list[Diagnostic]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [Diagnostic("forbidden-marker", f"forbidden marker found: {marker}", path) for marker in FORBIDDEN_MARKERS if marker in text]


def validate_source_anchors(record: dict[str, Any], path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    record_id = str(record.get("id", "<missing-id>"))
    anchors = record.get("source_anchors")
    if not isinstance(anchors, list) or not anchors:
        return [Diagnostic("source-anchor", "source_anchors must be a non-empty list", path, record_id, "source_anchors")]
    require_tracked = record_id.startswith("ACP-") or record_id.startswith("ACP-EDGE-")
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, dict):
            diagnostics.append(Diagnostic("source-anchor", "source anchor must be an object", path, record_id, f"source_anchors[{index}]"))
            continue
        anchor_path = anchor.get("path")
        if not isinstance(anchor_path, str) or not safe_repo_relative_path(anchor_path):
            diagnostics.append(Diagnostic("source-anchor-path", "source anchor path must be safe and repo-relative", path, record_id, f"source_anchors[{index}].path"))
        elif require_tracked and not is_tracked_repo_path(anchor_path):
            diagnostics.append(Diagnostic("source-anchor-tracked", "ACP source anchor path must be tracked", path, record_id, f"source_anchors[{index}].path"))
    return diagnostics


def validate_items(items: list[dict[str, Any]], items_path: Path) -> tuple[set[str], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    item_ids: set[str] = set()
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
    return item_ids, diagnostics


def validate_edges(edges: list[dict[str, Any]], item_ids: set[str], edges_path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    edge_ids: set[str] = set()
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
    return diagnostics


def build_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int], list[Diagnostic]]:
    canonical_items, diagnostics = load_jsonl(args.canonical_items)
    canonical_edges, edge_diagnostics = load_jsonl(args.canonical_edges)
    diagnostics.extend(edge_diagnostics)
    acp_items: list[dict[str, Any]] = []
    acp_edges: list[dict[str, Any]] = []
    if args.include_acp:
        acp_items, acp_item_diagnostics = load_jsonl(args.acp_items)
        acp_edges, acp_edge_diagnostics = load_jsonl(args.acp_edges)
        diagnostics.extend(acp_item_diagnostics)
        diagnostics.extend(acp_edge_diagnostics)
    items = sorted([*canonical_items, *acp_items], key=lambda record: str(record.get("id", "")))
    edges = sorted([*canonical_edges, *acp_edges], key=lambda record: str(record.get("id", "")))
    counts = {
        "canonical_item_count": len(canonical_items),
        "canonical_edge_count": len(canonical_edges),
        "acp_item_count": len(acp_items),
        "acp_edge_count": len(acp_edges),
        "integration_item_count": len(items),
        "integration_edge_count": len(edges),
    }
    return items, edges, counts, diagnostics


def normalize_graph_summary(summary: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(summary)
    normalized["mode"] = "custom"
    if "report_json" in normalized:
        normalized["report_json"] = display_path(Path(str(normalized["report_json"])))
    if "report_md" in normalized:
        normalized["report_md"] = display_path(Path(str(normalized["report_md"])))
    return normalized


def run_graph_build(args: argparse.Namespace) -> tuple[dict[str, Any] | None, Diagnostic | None]:
    command = [
        sys.executable,
        "scripts/build-architecture-graph.py",
        "--items",
        str(args.items_output),
        "--edges",
        str(args.edges_output),
        "--report-json",
        str(args.graph_report_json),
        "--report-md",
        str(args.graph_report_md),
    ]
    if args.check:
        command.append("--check")
    result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip().splitlines()
        return None, Diagnostic("graph-build", message[0] if message else "graph builder failed", args.graph_report_json)
    try:
        return normalize_graph_summary(json.loads(result.stdout)), None
    except json.JSONDecodeError:
        return None, Diagnostic("graph-build-output", "graph builder did not emit JSON summary", args.graph_report_json)


def build_report(
    args: argparse.Namespace,
    counts: dict[str, int],
    diagnostics: list[Diagnostic],
    graph_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    mode = "enabled" if args.include_acp else "disabled"
    return {
        "boundary": "ACP canonical integration is opt-in and non-authoritative; default tracked architecture registry currentness remains verifier-owned.",
        "diagnostic_count": len(diagnostics),
        "diagnostics": [diagnostic.to_json() for diagnostic in diagnostics],
        "graph_summary": graph_summary,
        "inputs": {
            "acp_edges": display_path(args.acp_edges) if args.include_acp else None,
            "acp_items": display_path(args.acp_items) if args.include_acp else None,
            "canonical_edges": display_path(args.canonical_edges),
            "canonical_items": display_path(args.canonical_items),
        },
        "mode": mode,
        "outputs": {
            "edges": display_path(args.edges_output),
            "graph_report_json": display_path(args.graph_report_json),
            "graph_report_md": display_path(args.graph_report_md),
            "items": display_path(args.items_output),
            "report": display_path(args.report_output),
        },
        "owner": "opt-in architecture-build composition",
        "record_counts": counts,
        "status": "ok" if not diagnostics else "failed",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if is_canonical_registry_path(args.items_output) or is_canonical_registry_path(args.edges_output):
        raise ValueError("refusing to write canonical architecture registry file")
    items, edges, counts, diagnostics = build_records(args)
    item_ids, item_diagnostics = validate_items(items, args.items_output)
    diagnostics.extend(item_diagnostics)
    diagnostics.extend(validate_edges(edges, item_ids, args.edges_output))
    diagnostics.extend(validate_forbidden_text(args.items_output))
    diagnostics.extend(validate_forbidden_text(args.edges_output))
    item_text = jsonl_text(items)
    edge_text = jsonl_text(edges)
    graph_summary: dict[str, Any] | None = None

    if not diagnostics and not args.check:
        write_output(args.items_output, item_text)
        write_output(args.edges_output, edge_text)

    if args.check:
        for path, expected in ((args.items_output, item_text), (args.edges_output, edge_text)):
            ok, message = check_output(path, expected)
            if not ok:
                diagnostics.append(Diagnostic("stale-output", message, path))

    if not diagnostics:
        graph_summary, graph_diagnostic = run_graph_build(args)
        if graph_diagnostic is not None:
            diagnostics.append(graph_diagnostic)

    report = build_report(args, counts, diagnostics, graph_summary)
    expected_report = stable_json_text(report)
    if args.check:
        ok, message = check_output(args.report_output, expected_report)
        if not ok:
            diagnostics.append(Diagnostic("stale-output", message, args.report_output))
            report = build_report(args, counts, diagnostics, graph_summary)
    elif not diagnostics:
        write_output(args.report_output, expected_report)

    report["status"] = "ok" if not diagnostics else "failed"
    report["diagnostic_count"] = len(diagnostics)
    report["diagnostics"] = [diagnostic.to_json() for diagnostic in diagnostics]
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-acp", action="store_true", help="Enable opt-in ACP composition rows.")
    parser.add_argument("--canonical-items", type=Path, default=CANONICAL_ITEMS)
    parser.add_argument("--canonical-edges", type=Path, default=CANONICAL_EDGES)
    parser.add_argument("--acp-items", type=Path, default=ACP_ITEMS)
    parser.add_argument("--acp-edges", type=Path, default=ACP_EDGES)
    parser.add_argument("--items-output", type=Path, default=DEFAULT_ITEMS_OUTPUT)
    parser.add_argument("--edges-output", type=Path, default=DEFAULT_EDGES_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--graph-report-json", type=Path, default=DEFAULT_GRAPH_REPORT_JSON)
    parser.add_argument("--graph-report-md", type=Path, default=DEFAULT_GRAPH_REPORT_MD)
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
