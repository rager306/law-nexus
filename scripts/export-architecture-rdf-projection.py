#!/usr/bin/env python3
"""Export a derived architecture registry RDF/SHACL/SPARQL projection.

This projection is custom-only and non-authoritative. It reads the generated
architecture JSONL registry, writes derived ACP proof artifacts, and refuses to
write canonical registry paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
DEFAULT_EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"
DEFAULT_TTL_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.ttl"
DEFAULT_SHACL_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.shacl.ttl"
DEFAULT_SPARQL_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.sparql"
DEFAULT_REPORT_OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection-rdf-report.json"
CANONICAL_REGISTRY_PATHS = {DEFAULT_ITEMS.resolve(), DEFAULT_EDGES.resolve()}
REQUIRED_ACP_NON_CLAIMS = (
    "Does not validate R035.",
    "Does not validate R037.",
    "Does not validate R038.",
)
NON_CLAIMS = (
    "This RDF/SHACL/SPARQL projection is derived and non-authoritative.",
    "This projection does not validate R035.",
    "This projection does not validate R037.",
    "This projection does not validate R038.",
    "This projection does not prove parser completeness, legal correctness, FalkorDB ingestion, retrieval quality, production readiness, independent external review, ontology correctness, RDF completeness, SHACL completeness, SPARQL engine correctness, or product Legal KnowQL behavior.",
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
    "RDF is authoritative",
    "SHACL proves ontology correctness",
    "SPARQL proves product runtime behavior",
    "/root/",
    ".gsd/exec",
)
DIAGNOSTIC_METADATA = {
    "missing-file": ("error", "input", "Regenerate or provide the expected generated registry input."),
    "jsonl-parse": ("error", "input", "Fix the generating source or regenerated JSONL line."),
    "jsonl-record": ("error", "input", "Ensure every JSONL line is an object record."),
    "duplicate-id": ("error", "shape", "Fix source mapping or generator ID derivation."),
    "record-kind": ("error", "shape", "Fix source mapping or generator output partitioning."),
    "shape-smoke": ("error", "shape", "Add the missing generated registry field from source evidence."),
    "source-anchor": ("error", "safety", "Add safe tracked source anchors."),
    "unsafe-source-anchor": ("error", "safety", "Replace with a safe repository-relative tracked anchor."),
    "missing-non-claim": ("error", "authority", "Add explicit R035/R037/R038 non-claims in source-owned ACP records."),
    "authority-required": ("error", "authority", "Set authority_required to true for decision candidates."),
    "missing-endpoint": ("error", "shape", "Fix the edge endpoint or add the missing item through source generation."),
    "forbidden-marker": ("error", "output", "Remove the secret, local path, or overclaim from generated inputs or templates."),
    "stale-output": ("error", "freshness", "Run the exporter in write mode after reviewing expected changes."),
}
VOCABULARY = {
    "boundary": "Custom projection vocabulary only; not ontology completeness, SHACL engine proof, SPARQL execution proof, or architecture authority.",
    "namespaces": {
        "lgarch": "urn:law-nexus:vocab:architecture:",
        "acp": "urn:law-nexus:vocab:acp:",
    },
    "classes": [
        "lgarch:ArchitectureItem",
        "lgarch:ArchitectureEdge",
        "lgarch:SourceAnchor",
        "lgarch:DecisionCandidate",
        "lgarch:ProofGate",
    ],
    "predicates": [
        "lgarch:recordId",
        "lgarch:recordKind",
        "lgarch:itemType",
        "lgarch:edgeType",
        "lgarch:status",
        "lgarch:layer",
        "lgarch:proofLevel",
        "lgarch:riskLevel",
        "lgarch:nonClaim",
        "lgarch:sourceAnchor",
        "lgarch:from",
        "lgarch:to",
        "acp:recordKind",
        "acp:sourceRecordId",
        "acp:captureMode",
        "acp:redactionStatus",
        "acp:authorityRequired",
        "acp:allowedNextAction",
        "acp:blockedAction",
    ],
}
SAFETY_BOUNDARY = (
    "Derived, custom-only ACP projection. Do not use as source truth, legal truth, product runtime proof, "
    "requirement validation, RDF completeness proof, SHACL engine proof, SPARQL execution proof, "
    "FalkorDB ingestion proof, or git-lex compatibility proof."
)


@dataclass(frozen=True)
class Diagnostic:
    rule: str
    message: str
    path: Path
    record_id: str = "<none>"
    field: str = "<none>"

    def to_json(self) -> dict[str, str]:
        severity, category, remediation = DIAGNOSTIC_METADATA.get(
            self.rule,
            ("error", "output", "Inspect the diagnostic rule and repair the generated source or projection output."),
        )
        return {
            "rule": self.rule,
            "severity": severity,
            "category": category,
            "message": self.message,
            "path": display_path(self.path),
            "record_id": self.record_id,
            "field": self.field,
            "remediation": remediation,
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


def turtle_string(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": "\\\\",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return f'"{text}"'


def rdf_bool(value: object) -> str:
    return "true" if value is True else "false"


def record_iri(record_id: str) -> str:
    return f"<urn:law-nexus:architecture:{record_id}>"


def source_anchor_iri(anchor: dict[str, Any]) -> str:
    stable = {
        "path": anchor.get("path", ""),
        "kind": anchor.get("kind", ""),
        "selector": anchor.get("selector", ""),
        "section": anchor.get("section", ""),
        "line_start": anchor.get("line_start", ""),
        "line_end": anchor.get("line_end", ""),
    }
    digest = hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"<urn:law-nexus:architecture-source:{digest}>"


def pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)


def edge_predicate(value: str) -> str:
    parts = [part for part in value.replace("-", "_").split("_") if part]
    if not parts:
        return "relatedTo"
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def add_literal(lines: list[str], predicate: str, value: object) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        lines.append(f"  {predicate} {rdf_bool(value)} ;")
    elif isinstance(value, (int, float)):
        lines.append(f"  {predicate} {value} ;")
    else:
        lines.append(f"  {predicate} {turtle_string(value)} ;")


def add_repeated_literals(lines: list[str], predicate: str, values: object) -> None:
    if not isinstance(values, list):
        return
    for value in sorted(str(item) for item in values if item is not None):
        lines.append(f"  {predicate} {turtle_string(value)} ;")


def ttl_prefixes() -> str:
    return "\n".join(
        [
            "@prefix lgarch: <urn:law-nexus:vocab:architecture:> .",
            "@prefix acp: <urn:law-nexus:vocab:acp:> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "",
        ]
    )


def finish_block(lines: list[str]) -> None:
    if not lines:
        return
    if lines[-1].endswith(" ;"):
        lines[-1] = lines[-1][:-2] + " ."
    elif not lines[-1].endswith("."):
        lines[-1] += " ."


def item_ttl(item: dict[str, Any]) -> list[str]:
    item_id = str(item.get("id", ""))
    item_type = str(item.get("type", ""))
    classes = ["lgarch:ArchitectureItem"]
    if item_type:
        classes.append(f"lgarch:{pascal_case(item_type)}")
    lines = [f"{record_iri(item_id)} a {', '.join(classes)} ;"]
    add_literal(lines, "lgarch:recordId", item_id)
    add_literal(lines, "lgarch:recordKind", item.get("record_kind"))
    add_literal(lines, "lgarch:itemType", item_type)
    add_literal(lines, "lgarch:status", item.get("status"))
    add_literal(lines, "lgarch:layer", item.get("layer"))
    add_literal(lines, "lgarch:proofLevel", item.get("proof_level"))
    add_literal(lines, "lgarch:riskLevel", item.get("risk_level"))
    add_literal(lines, "lgarch:generatedDraft", item.get("generated_draft"))
    add_literal(lines, "rdfs:label", item.get("title"))
    add_literal(lines, "lgarch:summary", item.get("summary"))
    add_literal(lines, "lgarch:owner", item.get("owner"))
    add_literal(lines, "lgarch:verification", item.get("verification"))
    add_repeated_literals(lines, "lgarch:nonClaim", item.get("non_claims"))
    add_literal(lines, "acp:recordKind", item.get("acp_record_kind"))
    add_literal(lines, "acp:sourceRecordId", item.get("acp_source_record_id"))
    add_literal(lines, "acp:captureMode", item.get("capture_mode"))
    add_literal(lines, "acp:redactionStatus", item.get("redaction_status"))
    add_literal(lines, "acp:authorityRequired", item.get("authority_required"))
    add_literal(lines, "acp:nonMappable", item.get("acp_non_mappable"))
    add_repeated_literals(lines, "acp:allowedNextAction", item.get("allowed_next_actions"))
    add_repeated_literals(lines, "acp:blockedAction", item.get("blocked_actions"))
    for anchor in item.get("source_anchors", []):
        if isinstance(anchor, dict):
            lines.append(f"  lgarch:sourceAnchor {source_anchor_iri(anchor)} ;")
    finish_block(lines)
    return lines


def edge_ttl(edge: dict[str, Any]) -> list[str]:
    edge_id = str(edge.get("id", ""))
    edge_type = str(edge.get("type", ""))
    from_id = str(edge.get("from", ""))
    to_id = str(edge.get("to", ""))
    lines = [f"{record_iri(edge_id)} a lgarch:ArchitectureEdge ;"]
    add_literal(lines, "lgarch:recordId", edge_id)
    add_literal(lines, "lgarch:recordKind", edge.get("record_kind"))
    add_literal(lines, "lgarch:edgeType", edge_type)
    add_literal(lines, "lgarch:status", edge.get("status"))
    add_literal(lines, "lgarch:confidence", edge.get("confidence"))
    add_literal(lines, "lgarch:generatedDraft", edge.get("generated_draft"))
    add_literal(lines, "lgarch:owner", edge.get("owner"))
    add_literal(lines, "lgarch:rationale", edge.get("rationale"))
    add_literal(lines, "lgarch:verification", edge.get("verification"))
    lines.append(f"  lgarch:from {record_iri(from_id)} ;")
    lines.append(f"  lgarch:to {record_iri(to_id)} ;")
    for anchor in edge.get("source_anchors", []):
        if isinstance(anchor, dict):
            lines.append(f"  lgarch:sourceAnchor {source_anchor_iri(anchor)} ;")
    finish_block(lines)
    direct = [f"{record_iri(from_id)} lgarch:{edge_predicate(edge_type)} {record_iri(to_id)} ."] if from_id and to_id and edge_type else []
    return [*lines, *direct]


def source_anchor_ttl(records: list[dict[str, Any]]) -> list[str]:
    anchors: dict[str, dict[str, Any]] = {}
    for record in records:
        for anchor in record.get("source_anchors", []):
            if isinstance(anchor, dict):
                anchors[source_anchor_iri(anchor)] = anchor
    blocks: list[str] = []
    for iri in sorted(anchors):
        anchor = anchors[iri]
        lines = [f"{iri} a lgarch:SourceAnchor ;"]
        add_literal(lines, "lgarch:path", anchor.get("path"))
        add_literal(lines, "lgarch:kind", anchor.get("kind"))
        add_literal(lines, "lgarch:selector", anchor.get("selector"))
        add_literal(lines, "lgarch:section", anchor.get("section"))
        add_literal(lines, "lgarch:lineStart", anchor.get("line_start"))
        add_literal(lines, "lgarch:lineEnd", anchor.get("line_end"))
        finish_block(lines)
        blocks.extend(lines)
        blocks.append("")
    return blocks


def build_ttl(items: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    lines = [ttl_prefixes().rstrip(), ""]
    for item in sorted(items, key=lambda record: str(record.get("id", ""))):
        lines.extend(item_ttl(item))
        lines.append("")
    for edge in sorted(edges, key=lambda record: str(record.get("id", ""))):
        lines.extend(edge_ttl(edge))
        lines.append("")
    lines.extend(source_anchor_ttl([*items, *edges]))
    return "\n".join(lines).rstrip() + "\n"


def build_shacl() -> str:
    return """@prefix lgarch: <urn:law-nexus:vocab:architecture:> .
@prefix acp: <urn:law-nexus:vocab:acp:> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

lgarch:ArchitectureItemShape a sh:NodeShape ;
  sh:targetClass lgarch:ArchitectureItem ;
  sh:property [ sh:path lgarch:recordId ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:itemType ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:status ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:layer ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:proofLevel ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:sourceAnchor ; sh:minCount 1 ] .

lgarch:ArchitectureEdgeShape a sh:NodeShape ;
  sh:targetClass lgarch:ArchitectureEdge ;
  sh:property [ sh:path lgarch:recordId ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:edgeType ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:from ; sh:minCount 1 ] ;
  sh:property [ sh:path lgarch:to ; sh:minCount 1 ] .

acp:DecisionCandidateShape a sh:NodeShape ;
  sh:targetClass lgarch:DecisionCandidate ;
  sh:property [ sh:path acp:authorityRequired ; sh:hasValue true ] .
"""


def build_sparql() -> str:
    return """PREFIX lgarch: <urn:law-nexus:vocab:architecture:>
PREFIX acp: <urn:law-nexus:vocab:acp:>

# Count architecture registry items.
SELECT (COUNT(?item) AS ?itemCount)
WHERE { ?item a lgarch:ArchitectureItem . }

# Count architecture registry edges.
SELECT (COUNT(?edge) AS ?edgeCount)
WHERE { ?edge a lgarch:ArchitectureEdge . }

# List ACP governance rows.
SELECT ?item ?type ?status
WHERE {
  ?item a lgarch:ArchitectureItem ;
        lgarch:itemType ?type ;
        lgarch:status ?status .
  FILTER(STRSTARTS(STR(?item), "urn:law-nexus:architecture:ACP-"))
}

# List explicit R035/R037/R038 non-claims.
SELECT ?item ?claim
WHERE {
  ?item lgarch:nonClaim ?claim .
  FILTER(?claim IN ("Does not validate R035.", "Does not validate R037.", "Does not validate R038."))
}

# List proof gates and their status.
SELECT ?gate ?status
WHERE {
  ?gate a lgarch:ArchitectureItem ;
        lgarch:itemType "proof_gate" ;
        lgarch:status ?status .
}

# List high and critical risk records.
SELECT ?item ?risk
WHERE {
  ?item a lgarch:ArchitectureItem ;
        lgarch:riskLevel ?risk .
  FILTER(?risk IN ("high", "critical"))
}
"""


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
        anchor_path = anchor.get("path")
        if not isinstance(anchor_path, str) or not safe_repo_relative_path(anchor_path):
            diagnostics.append(Diagnostic("unsafe-source-anchor", "source anchor path must be safe and repo-relative", path, record_id, f"source_anchors[{index}].path"))
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
        for field in ("type", "status", "layer", "proof_level"):
            if not item.get(field):
                diagnostics.append(Diagnostic("shape-smoke", f"item missing {field}", items_path, item_id, field))
        diagnostics.extend(validate_source_anchors(item, items_path))
        if item_id.startswith("ACP-"):
            non_claims = item.get("non_claims")
            if not isinstance(non_claims, list):
                diagnostics.append(Diagnostic("missing-non-claim", "ACP item non_claims must be a list", items_path, item_id, "non_claims"))
            else:
                for claim in REQUIRED_ACP_NON_CLAIMS:
                    if claim not in non_claims:
                        diagnostics.append(Diagnostic("missing-non-claim", f"missing required non-claim: {claim}", items_path, item_id, "non_claims"))
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
                diagnostics.append(Diagnostic("missing-endpoint", "edge endpoint does not reference an item", edges_path, edge_id, field))
        diagnostics.extend(validate_source_anchors(edge, edges_path))
    return diagnostics


def validate_generated_text(path: Path, text: str) -> list[Diagnostic]:
    return [Diagnostic("forbidden-marker", f"forbidden marker found: {marker}", path) for marker in FORBIDDEN_MARKERS if marker in text]


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def output_state(path: Path, expected: str) -> dict[str, Any]:
    expected_hash = sha256_text(expected)
    state: dict[str, Any] = {
        "path": display_path(path),
        "state": "missing",
        "expected_bytes": len(expected.encode("utf-8")),
        "expected_sha256": expected_hash,
    }
    if not path.exists():
        return state
    current = path.read_text(encoding="utf-8")
    current_hash = sha256_text(current)
    state.update(
        {
            "state": "current" if current == expected else "stale",
            "current_bytes": len(current.encode("utf-8")),
            "current_sha256": current_hash,
        }
    )
    return state


def diagnostic_summary(diagnostics: list[Diagnostic]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {"by_rule": {}, "by_category": {}, "by_severity": {}}
    for diagnostic in diagnostics:
        severity, category, _remediation = DIAGNOSTIC_METADATA.get(diagnostic.rule, ("error", "output", ""))
        summary["by_rule"][diagnostic.rule] = summary["by_rule"].get(diagnostic.rule, 0) + 1
        summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
    return {key: dict(sorted(value.items())) for key, value in summary.items()}


def apply_diagnostics(report: dict[str, Any], diagnostics: list[Diagnostic]) -> None:
    report["status"] = "ok" if not diagnostics else "failed"
    report["shape_smoke"]["status"] = "ok" if not diagnostics else "failed"
    report["diagnostic_count"] = len(diagnostics)
    report["diagnostics"] = [diagnostic.to_json() for diagnostic in diagnostics]
    report["diagnostic_summary"] = diagnostic_summary(diagnostics)


def build_diff(output_pairs: list[tuple[Path, str]]) -> dict[str, Any]:
    outputs = {label: output_state(path, expected) for label, (path, expected) in zip(("ttl", "shacl", "sparql", "report"), output_pairs, strict=True)}
    states = sorted({value["state"] for value in outputs.values()})
    return {
        "mode": "diff",
        "non_writing": True,
        "status": "current" if states == ["current"] else "changed",
        "states": states,
        "outputs": outputs,
    }


def count_statements(ttl_text: str) -> int:
    return sum(1 for line in ttl_text.splitlines() if line.strip().endswith("."))


def build_outputs(args: argparse.Namespace) -> tuple[dict[str, str], dict[str, Any], list[Diagnostic]]:
    items, diagnostics = load_jsonl(args.items)
    edges, edge_diagnostics = load_jsonl(args.edges)
    diagnostics.extend(edge_diagnostics)
    item_ids, item_diagnostics = validate_items(items, args.items)
    diagnostics.extend(item_diagnostics)
    diagnostics.extend(validate_edges(edges, item_ids, args.edges))

    ttl_text = build_ttl(items, edges)
    shacl_text = build_shacl()
    sparql_text = build_sparql()
    for path, text in ((args.ttl_output, ttl_text), (args.shacl_output, shacl_text), (args.sparql_output, sparql_text)):
        diagnostics.extend(validate_generated_text(path, text))

    acp_items = sum(1 for item in items if str(item.get("id", "")).startswith("ACP-"))
    acp_edges = sum(1 for edge in edges if str(edge.get("id", "")).startswith("ACP-EDGE-"))
    report = {
        "status": "ok" if not diagnostics else "failed",
        "non_authoritative": True,
        "mode": "custom",
        "inputs": {
            "items": display_path(args.items),
            "edges": display_path(args.edges),
        },
        "outputs": {
            "ttl": display_path(args.ttl_output),
            "shacl": display_path(args.shacl_output),
            "sparql": display_path(args.sparql_output),
            "report": display_path(args.report_output),
        },
        "counts": {
            "items": len(items),
            "edges": len(edges),
            "acp_items": acp_items,
            "acp_edges": acp_edges,
            "rdf_resources": len(items) + len(edges),
            "statements": count_statements(ttl_text),
        },
        "shape_smoke": {
            "status": "ok" if not diagnostics else "failed",
            "engine": "deterministic-structural-check",
            "checked_rules": [
                "item-required-fields",
                "edge-endpoints",
                "source-anchor-safety",
                "acp-non-claims",
                "decision-candidate-authority-required",
            ],
        },
        "sparql_smoke": {
            "status": "ok",
            "engine": "not-executed",
            "handoff_queries": [
                "count-items",
                "count-edges",
                "list-acp-governance-rows",
                "list-r035-r037-r038-non-claims",
                "list-proof-gates",
                "list-high-critical-records",
            ],
        },
        "diagnostic_count": len(diagnostics),
        "diagnostics": [diagnostic.to_json() for diagnostic in diagnostics],
        "diagnostic_summary": diagnostic_summary(diagnostics),
        "vocabulary": VOCABULARY,
        "safety_boundary": SAFETY_BOUNDARY,
        "non_claims": list(NON_CLAIMS),
    }
    report_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    diagnostics.extend(validate_generated_text(args.report_output, report_text))
    if diagnostics:
        apply_diagnostics(report, diagnostics)
        report_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return {"ttl": ttl_text, "shacl": shacl_text, "sparql": sparql_text, "report": report_text}, report, diagnostics


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.ttl_output, args.shacl_output, args.sparql_output, args.report_output):
        if is_canonical_registry_path(path):
            return {
                "status": "failed",
                "message": "refusing to write canonical architecture registry file",
                "path": display_path(path),
                "non_authoritative": True,
            }

    outputs, report, diagnostics = build_outputs(args)
    output_pairs = [
        (args.ttl_output, outputs["ttl"]),
        (args.shacl_output, outputs["shacl"]),
        (args.sparql_output, outputs["sparql"]),
        (args.report_output, outputs["report"]),
    ]

    if args.diff:
        if diagnostics:
            apply_diagnostics(report, diagnostics)
            return report
        report["diff"] = build_diff(output_pairs)
        return report

    if args.check:
        for path, expected in output_pairs:
            ok, message = check_output(path, expected)
            if not ok:
                diagnostics.append(Diagnostic("stale-output", message, path))
        if diagnostics:
            apply_diagnostics(report, diagnostics)
    elif not diagnostics:
        for path, text in output_pairs:
            write_output(path, text)

    if diagnostics and not args.check:
        apply_diagnostics(report, diagnostics)

    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=DEFAULT_ITEMS)
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    parser.add_argument("--ttl-output", type=Path, default=DEFAULT_TTL_OUTPUT)
    parser.add_argument("--shacl-output", type=Path, default=DEFAULT_SHACL_OUTPUT)
    parser.add_argument("--sparql-output", type=Path, default=DEFAULT_SPARQL_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--diff", action="store_true", help="Report output freshness without writing files.")
    args = parser.parse_args(argv)
    if args.check and args.diff:
        parser.error("--check and --diff are mutually exclusive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
