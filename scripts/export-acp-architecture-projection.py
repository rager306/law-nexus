#!/usr/bin/env python3
"""Export a preview architecture projection from ACP recovery records.

This exporter is deliberately preview-only. It never writes canonical
``architecture_items.jsonl`` or ``architecture_edges.jsonl`` registry files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECOVERY_VIEW = ROOT / "prd/architecture/acp/derived/recovery-view.json"
DEFAULT_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.preview.json"
CANONICAL_REGISTRY_PATHS = (
    ROOT / "prd/architecture/architecture_items.jsonl",
    ROOT / "prd/architecture/architecture_edges.jsonl",
)
NON_CLAIMS = [
    "Does not validate R035.",
    "Does not validate R037.",
    "Does not validate R038.",
    "Does not prove parser completeness.",
    "Does not prove legal correctness.",
    "Does not prove FalkorDB ingestion or runtime loading.",
    "Does not prove graph-vector retrieval quality.",
    "Does not prove production readiness.",
    "Does not prove independent external review.",
]
BLOCKED_CANONICAL_MUTATIONS = [
    "write prd/architecture/architecture_items.jsonl",
    "write prd/architecture/architecture_edges.jsonl",
    "change prd/architecture/architecture.schema.json",
    "change scripts/extract-prd-architecture-items.py",
    "change scripts/build-architecture-graph.py",
    "promote DC-0001 to accepted decision",
    "project ACP preview items as validated product architecture",
]
KIND_MAPPING = {
    "architecture_prompt_record": {
        "suggested_type": "evidence",
        "suggested_layer": "architecture-governance",
        "suggested_status": "bounded-evidence",
        "suggested_proof_level": "source-anchor",
        "mapping_notes": "Provenance only; not decision or implementation proof.",
    },
    "architecture_proposal": {
        "suggested_type": "viewpoint",
        "suggested_layer": "architecture-governance",
        "suggested_status": "bounded-evidence",
        "suggested_proof_level": "source-anchor",
        "mapping_notes": "Proposal quality artifact; not accepted doctrine.",
    },
    "decision_candidate": {
        "suggested_type": "decision",
        "suggested_layer": "architecture-governance",
        "suggested_status": "hypothesis",
        "suggested_proof_level": "source-anchor",
        "mapping_notes": "Candidate only; requires authority and proof gates before acceptance.",
    },
    "proof_gate": {
        "suggested_type": "proof_gate",
        "suggested_layer": "architecture-governance",
        "suggested_status": "blocked",
        "suggested_proof_level": "static-check",
        "mapping_notes": "Defines evidence requirement; static-check applies only to ACP mechanics.",
    },
    "architecture_health_finding": {
        "suggested_type": "risk",
        "suggested_layer": "architecture-governance",
        "suggested_status": "blocked",
        "suggested_proof_level": "source-anchor",
        "mapping_notes": "Health/blocker signal; not architecture proof.",
    },
}
RELATIONSHIP_MAPPING = {
    "producedProposal": ("informs", "bounded-evidence"),
    "originPromptRecord": ("informs", "bounded-evidence"),
    "suggestedDecision": ("informs", "hypothesis"),
    "originProposal": ("informs", "hypothesis"),
    "requiresProof": ("checked_by", "active"),
    "affects": ("blocks", "active"),
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def source_anchor_kind(path: str, role: str) -> str:
    role_lower = role.lower()
    if path.startswith("scripts/"):
        return "source-code"
    if path.startswith("tests/"):
        return "test-artifact"
    if path.startswith("prd/"):
        return "prd"
    if any(token in role_lower for token in ("contract", "profile", "plan", "assessment")):
        return "prd"
    return "manual-note"


def convert_source_refs(source_refs: list[dict[str, Any]]) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    for ref in source_refs:
        path = str(ref.get("path", ""))
        role = str(ref.get("role", "manual-note"))
        note = str(ref.get("note", role))
        anchors.append(
            {
                "path": path,
                "kind": source_anchor_kind(path, role),
                "selector": f"acp-role:{role}; {note}",
            }
        )
    return anchors


def summary_for_record(record: dict[str, Any]) -> str:
    return (
        f"ACP {record['record_kind']} {record['id']} projected as preview only. "
        "Canonical architecture registry files are unchanged."
    )


def preview_item(record: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    mapping = KIND_MAPPING.get(str(record.get("record_kind")))
    if mapping is None:
        return None, {
            "record_id": record.get("id"),
            "reason": f"Unsupported ACP record kind {record.get('record_kind')}",
        }
    item = {
        "preview_id": f"ACP-PREVIEW-{record['id']}",
        "source_record_id": record["id"],
        "source_record_kind": record["record_kind"],
        "suggested_type": mapping["suggested_type"],
        "suggested_layer": mapping["suggested_layer"],
        "suggested_status": mapping["suggested_status"],
        "suggested_proof_level": mapping["suggested_proof_level"],
        "title": record["title"],
        "summary": summary_for_record(record),
        "source_anchors": convert_source_refs(record.get("source_refs", [])),
        "non_claims": NON_CLAIMS,
        "mapping_notes": [mapping["mapping_notes"]],
    }
    if record.get("record_kind") == "architecture_prompt_record":
        item["mapping_notes"].append("capture_mode and redaction_status remain ACP-only in M037 preview.")
    if record.get("record_kind") == "architecture_health_finding":
        item["mapping_notes"].append("blocked actions remain ACP recovery data until registry schema is extended.")
    return item, None


def preview_edge(edge: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    relationship = str(edge.get("relationship", ""))
    mapping = RELATIONSHIP_MAPPING.get(relationship)
    if mapping is None:
        return None, {
            "edge": edge,
            "reason": f"Unsupported ACP relationship {relationship}",
        }
    suggested_edge_type, suggested_status = mapping
    source = str(edge.get("source"))
    target = str(edge.get("target"))
    return {
        "preview_id": f"ACP-PREVIEW-EDGE-{source}-{relationship}-{target}",
        "source_preview_id": f"ACP-PREVIEW-{source}",
        "target_preview_id": f"ACP-PREVIEW-{target}",
        "relationship": relationship,
        "suggested_edge_type": suggested_edge_type,
        "suggested_status": suggested_status,
        "mapping_notes": ["Preview edge only; not written to canonical architecture_edges.jsonl."],
    }, None


def build_projection(recovery_view_path: Path) -> dict[str, Any]:
    recovery = load_json(recovery_view_path)
    items: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    non_mappable: list[dict[str, Any]] = []

    for record in recovery.get("records", []):
        item, issue = preview_item(record)
        if item is not None:
            items.append(item)
        if issue is not None:
            non_mappable.append(issue)

    for edge in recovery.get("edges", []):
        projected, issue = preview_edge(edge)
        if projected is not None:
            edges.append(projected)
        if issue is not None:
            non_mappable.append(issue)

    return {
        "kind": "acp_architecture_projection_preview",
        "version": "0.1.0",
        "boundary": "Preview only; canonical architecture registry files are unchanged.",
        "source": display_path(recovery_view_path),
        "items": sorted(items, key=lambda item: item["preview_id"]),
        "edges": sorted(edges, key=lambda edge: edge["preview_id"]),
        "non_mappable": non_mappable,
        "blocked_canonical_mutations": BLOCKED_CANONICAL_MUTATIONS,
        "canonical_registry_files": [display_path(path) for path in CANONICAL_REGISTRY_PATHS],
    }


def write_output(output_path: Path, payload: dict[str, Any]) -> None:
    if output_path in CANONICAL_REGISTRY_PATHS:
        raise ValueError("refusing to write canonical architecture registry file")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def expected_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def check_output(output_path: Path, payload: dict[str, Any]) -> tuple[bool, str]:
    if not output_path.exists():
        return False, "output file does not exist"
    if output_path.read_text(encoding="utf-8") != expected_text(payload):
        return False, "output file is stale"
    return True, "output file is current"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery-view", type=Path, default=DEFAULT_RECOVERY_VIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        payload = build_projection(args.recovery_view)
        if args.check:
            ok, message = check_output(args.output, payload)
            result = {"status": "ok" if ok else "failed", "message": message, "output": display_path(args.output)}
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if ok else 1
        write_output(args.output, payload)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "output": display_path(args.output),
                    "item_count": len(payload["items"]),
                    "edge_count": len(payload["edges"]),
                    "boundary": payload["boundary"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
