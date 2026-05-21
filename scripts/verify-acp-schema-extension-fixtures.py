#!/usr/bin/env python3
"""Validate ACP schema-extension custom fixtures.

This checker validates the isolated candidate fixtures under
``prd/architecture/acp/fixtures/schema-extension``. It does not validate or
mutate the canonical architecture registry schema or JSONL outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_DIR = ROOT / "prd/architecture/acp/fixtures/schema-extension"
DEFAULT_ITEMS = DEFAULT_FIXTURE_DIR / "custom-items.jsonl"
DEFAULT_EDGES = DEFAULT_FIXTURE_DIR / "custom-edges.jsonl"
CANONICAL_REGISTRY_FILES = {
    "prd/architecture/architecture.schema.json",
    "prd/architecture/architecture_items.jsonl",
    "prd/architecture/architecture_edges.jsonl",
}
REQUIRED_ITEM_TYPES = {"prompt_record", "proposal", "decision_candidate", "proof_gate", "health_finding"}
REQUIRED_RELATIONS = {
    "produced_proposal",
    "origin_prompt_record",
    "suggested_decision",
    "origin_proposal",
    "requires_proof",
    "blocks",
    "affects",
}
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


def is_repo_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\x00" in value:
        return False
    parts = Path(value).parts
    if ".." in parts:
        return False
    if value.startswith(".gsd/exec"):
        return False
    return True


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records, [Diagnostic("missing-file", "fixture file is missing", path)]

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            diagnostics.append(Diagnostic("jsonl-parse", f"invalid JSON on line {line_number}: {exc.msg}", path))
            continue
        if not isinstance(value, dict):
            diagnostics.append(Diagnostic("jsonl-record", "JSONL record must be an object", path, field=str(line_number)))
            continue
        records.append(value)
    return records, diagnostics


def text_diagnostics(path: Path) -> list[Diagnostic]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    diagnostics: list[Diagnostic] = []
    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            diagnostics.append(Diagnostic("forbidden-marker", f"forbidden marker found: {marker}", path))
    return diagnostics


def require_string(record: dict[str, Any], field: str, path: Path) -> list[Diagnostic]:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        return [Diagnostic("required-string", "field must be a non-empty string", path, str(record.get("id", "<missing-id>")), field)]
    return []


def require_list(record: dict[str, Any], field: str, path: Path) -> list[Diagnostic]:
    value = record.get(field)
    if not isinstance(value, list) or not value:
        return [Diagnostic("required-list", "field must be a non-empty list", path, str(record.get("id", "<missing-id>")), field)]
    return []


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
        if not isinstance(ref_path, str) or not is_repo_relative_path(ref_path):
            diagnostics.append(Diagnostic("source-anchor-path", "source anchor path must be repo-relative", path, record_id, f"source_anchors[{index}].path"))
        elif ref_path in CANONICAL_REGISTRY_FILES:
            diagnostics.append(Diagnostic("canonical-anchor", "custom fixture must not use canonical registry file as source anchor", path, record_id, f"source_anchors[{index}].path"))
        elif not (ROOT / ref_path).exists():
            diagnostics.append(Diagnostic("source-anchor-exists", "source anchor path does not exist", path, record_id, f"source_anchors[{index}].path"))
        if not isinstance(anchor.get("role"), str) or not anchor["role"]:
            diagnostics.append(Diagnostic("source-anchor-role", "source anchor role is required", path, record_id, f"source_anchors[{index}].role"))
    return diagnostics


def validate_item(record: dict[str, Any], path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    record_id = str(record.get("id", "<missing-id>"))
    for field in (
        "schema_version",
        "record_kind",
        "id",
        "type",
        "title",
        "summary",
        "layer",
        "status",
        "proof_level",
        "risk_level",
        "owner",
        "acp_record_kind",
        "acp_source_record_id",
    ):
        diagnostics.extend(require_string(record, field, path))
    if record.get("schema_version") != "candidate-acp-registry-extension-v0":
        diagnostics.append(Diagnostic("schema-version", "unexpected candidate schema version", path, record_id, "schema_version"))
    if record.get("record_kind") != "architecture_item_candidate":
        diagnostics.append(Diagnostic("record-kind", "unexpected item record kind", path, record_id, "record_kind"))
    if record.get("type") not in REQUIRED_ITEM_TYPES:
        diagnostics.append(Diagnostic("item-type", "unexpected candidate item type", path, record_id, "type"))
    if record.get("layer") != "architecture-governance":
        diagnostics.append(Diagnostic("layer", "candidate item must stay in architecture-governance layer", path, record_id, "layer"))
    if record.get("type") == "prompt_record":
        for field in ("capture_mode", "redaction_status"):
            diagnostics.extend(require_string(record, field, path))
    if record.get("type") == "decision_candidate" and record.get("authority_required") is not True:
        diagnostics.append(Diagnostic("authority-required", "decision candidate must require authority", path, record_id, "authority_required"))
    if record.get("type") in {"proof_gate", "health_finding"}:
        diagnostics.extend(require_list(record, "blocked_actions", path))
    if record.get("type") == "health_finding":
        diagnostics.extend(require_list(record, "allowed_next_actions", path))
    diagnostics.extend(require_list(record, "non_claims", path))
    diagnostics.extend(validate_source_anchors(record, path))
    return diagnostics


def validate_edge(record: dict[str, Any], path: Path, item_ids: set[str]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    record_id = str(record.get("id", "<missing-id>"))
    for field in ("schema_version", "record_kind", "id", "source", "target", "relation", "acp_relationship", "summary"):
        diagnostics.extend(require_string(record, field, path))
    if record.get("schema_version") != "candidate-acp-registry-extension-v0":
        diagnostics.append(Diagnostic("schema-version", "unexpected candidate schema version", path, record_id, "schema_version"))
    if record.get("record_kind") != "architecture_edge_candidate":
        diagnostics.append(Diagnostic("record-kind", "unexpected edge record kind", path, record_id, "record_kind"))
    if record.get("relation") not in REQUIRED_RELATIONS:
        diagnostics.append(Diagnostic("edge-relation", "unexpected candidate edge relation", path, record_id, "relation"))
    for field in ("source", "target"):
        value = record.get(field)
        if isinstance(value, str) and value not in item_ids:
            diagnostics.append(Diagnostic("edge-endpoint", "edge endpoint does not reference a candidate item", path, record_id, field))
    diagnostics.extend(require_list(record, "non_claims", path))
    return diagnostics


def validate(items_path: Path, edges_path: Path, notes_path: Path) -> dict[str, Any]:
    items, diagnostics = load_jsonl(items_path)
    edges, edge_diagnostics = load_jsonl(edges_path)
    diagnostics.extend(edge_diagnostics)
    diagnostics.extend(text_diagnostics(items_path))
    diagnostics.extend(text_diagnostics(edges_path))
    diagnostics.extend(text_diagnostics(notes_path))

    item_ids = {str(item.get("id")) for item in items if isinstance(item.get("id"), str)}
    item_types = {str(item.get("type")) for item in items if isinstance(item.get("type"), str)}
    relations = {str(edge.get("relation")) for edge in edges if isinstance(edge.get("relation"), str)}

    for required_type in sorted(REQUIRED_ITEM_TYPES):
        if required_type not in item_types:
            diagnostics.append(Diagnostic("required-item-type", f"missing required candidate item type {required_type}", items_path, field="type"))
    for required_relation in sorted(REQUIRED_RELATIONS):
        if required_relation not in relations:
            diagnostics.append(Diagnostic("required-edge-relation", f"missing required candidate edge relation {required_relation}", edges_path, field="relation"))

    seen_items: set[str] = set()
    for item in items:
        item_id = str(item.get("id", "<missing-id>"))
        if item_id in seen_items:
            diagnostics.append(Diagnostic("duplicate-id", "duplicate candidate item id", items_path, item_id, "id"))
        seen_items.add(item_id)
        diagnostics.extend(validate_item(item, items_path))

    seen_edges: set[str] = set()
    for edge in edges:
        edge_id = str(edge.get("id", "<missing-id>"))
        if edge_id in seen_edges:
            diagnostics.append(Diagnostic("duplicate-id", "duplicate candidate edge id", edges_path, edge_id, "id"))
        seen_edges.add(edge_id)
        diagnostics.extend(validate_edge(edge, edges_path, item_ids))

    return {
        "status": "ok" if not diagnostics else "failed",
        "item_count": len(items),
        "edge_count": len(edges),
        "item_types": sorted(item_types),
        "relations": sorted(relations),
        "diagnostic_count": len(diagnostics),
        "diagnostics": [diagnostic.to_json() for diagnostic in diagnostics],
        "boundary": "Custom-path fixture proof only; canonical architecture registry files are unchanged.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=DEFAULT_ITEMS, help="Path to candidate custom items JSONL.")
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES, help="Path to candidate custom edges JSONL.")
    parser.add_argument(
        "--notes",
        type=Path,
        default=DEFAULT_FIXTURE_DIR / "schema-extension-notes.md",
        help="Path to schema extension notes for forbidden marker scanning.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = validate(args.items, args.edges, args.notes)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
