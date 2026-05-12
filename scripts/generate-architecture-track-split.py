#!/usr/bin/env python3
"""Generate a derived, non-authoritative major proof-track split.

The track split consumes the S02 remediation matrix and groups open proof gates
into implementation-sized future proof tracks. It is planning evidence only;
it does not retire gates or validate product/runtime/legal behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX_JSON_PATH = ROOT / "prd/architecture/remediation_matrix.json"
DEFAULT_TRACK_JSON_PATH = ROOT / "prd/architecture/major_track_split.json"
DEFAULT_TRACK_MD_PATH = ROOT / "prd/architecture/major_track_split.md"

TRACK_DEFINITIONS: list[dict[str, Any]] = [
    {
        "track_id": "TRACK-GENERATED-CYPHER-SAFETY",
        "title": "Generated-Cypher validator safety proof",
        "gate_ids": ["GATE-GENERATED-CYPHER-SAFETY"],
        "track_status": "planned-proof",
        "scope_boundary": "Design and verify deterministic generated-Cypher validator behavior before any product Legal KnowQL readiness claim.",
        "required_inputs": [
            "prd/06_m002_cypher_safety_contract.md",
            "R017 active requirement context",
            "Current architecture generated-Cypher proof gate",
        ],
        "proof_artifact": "Validator suite report covering read-only enforcement, schema grounding, evidence-returning queries, injection rejection, and unsafe write rejection.",
        "acceptance_criteria": [
            "Unsafe write/mutation Cypher candidates are rejected deterministically.",
            "Queries must be schema-grounded and evidence-returning before execution is allowed.",
            "Negative tests cover prompt-injection and non-evidence answer paths.",
        ],
        "recommended_next_unit": "Future generated-Cypher safety proof slice before R017 validation.",
        "non_claims": [
            "Does not prove provider generation quality.",
            "Does not authorize executing raw generated Cypher.",
            "Does not validate product Legal KnowQL readiness.",
        ],
    },
    {
        "track_id": "TRACK-PARSER-RETRIEVAL-GOLDEN",
        "title": "Parser/retrieval golden-test proof",
        "gate_ids": ["GATE-G008"],
        "track_status": "planned-proof",
        "scope_boundary": "Turn bounded M006 parser artifacts into executable golden tests without claiming parser completeness or retrieval quality.",
        "required_inputs": [
            "prd/parser/parser_record_contract.md",
            "prd/parser/odt_smoke_records.md",
            "prd/parser/consultant_relation_candidates.md",
            "prd/parser/parser_staging_graph.md",
        ],
        "proof_artifact": "Golden-test suite over tracked parser records with expected no-answer and non-claim cases.",
        "acceptance_criteria": [
            "Golden tests consume tracked parser artifacts rather than rescanning undocumented sources.",
            "Expected evidence/citation rows are asserted for bounded fixtures.",
            "No-answer and candidate-only relation behavior is explicitly tested.",
        ],
        "recommended_next_unit": "Future parser/retrieval proof slice using M006 artifacts.",
        "non_claims": [
            "Does not prove parser completeness.",
            "Does not prove citation-safe retrieval.",
            "Does not prove legal-answer correctness.",
        ],
    },
    {
        "track_id": "TRACK-TEMPORAL-SEMANTICS",
        "title": "Temporal conflict semantics decision and tests",
        "gate_ids": ["GATE-G005"],
        "track_status": "needs-product-decision",
        "scope_boundary": "Resolve same-date/source-revision/new-edition semantics before runtime import behavior is treated as valid.",
        "required_inputs": [
            "prd/03_PRD.md temporal/idempotent import policy",
            "DATA-TEMPORAL-PROPERTY-BUNDLE",
            "REQ-TEMPORAL-STATUS-SEMANTICS",
        ],
        "proof_artifact": "Temporal policy decision plus fixture tests for idempotent replay, source revision, new edition, and metadata conflict cases.",
        "acceptance_criteria": [
            "Policy distinguishes same hash replay, changed hash same edition, new edition date, and metadata conflict.",
            "Tests preserve prior source/edition records rather than mutating historical evidence.",
            "Diagnostics expose temporal conflict state without LLM interpretation.",
        ],
        "recommended_next_unit": "Future temporal semantics decision/proof slice.",
        "non_claims": [
            "Does not specify temporal storage implementation.",
            "Does not validate temporal conflict resolution yet.",
            "Does not prove import runtime behavior.",
        ],
    },
    {
        "track_id": "TRACK-LEGAL-NEXUS-ACCESS-CONTROL",
        "title": "Legal Nexus access-control boundary",
        "gate_ids": ["GATE-LEGAL-NEXUS-ACCESS-CONTROL"],
        "track_status": "needs-product-decision",
        "scope_boundary": "Define caller roles, API boundary, authorization policy, and denial diagnostics before non-local Legal Nexus/API promotion.",
        "required_inputs": [
            "prd/03_PRD.md Legal Nexus Module",
            "COMP-LEGAL-NEXUS-ORCHESTRATOR",
            "GATE-LEGAL-NEXUS-ACCESS-CONTROL",
        ],
        "proof_artifact": "Access-control decision record and negative-test plan for import operators, query users, reviewers, and administrators.",
        "acceptance_criteria": [
            "Role/capability matrix is explicit before API implementation claims.",
            "Denied operations have deterministic diagnostics and audit expectations.",
            "Logs and metrics boundaries exclude secrets and unauthorized raw legal text exposure.",
        ],
        "recommended_next_unit": "Future Legal Nexus API/access-control design slice.",
        "non_claims": [
            "Does not assert current product is insecure.",
            "Does not prove access-control enforcement.",
            "Does not define a production API surface.",
        ],
    },
    {
        "track_id": "TRACK-RETRIEVAL-EMBEDDING-EXPERIMENT",
        "title": "Retrieval quality and local embedding experiment",
        "gate_ids": ["GATE-EMBEDDING-SUPPLY-CHAIN", "GATE-G011"],
        "track_status": "needs-runtime-experiment",
        "scope_boundary": "Evaluate local/open-weight embedding and retrieval quality candidates without managed embedding fallback or product retrieval claims.",
        "required_inputs": [
            "prd/03_PRD.md FR-28b embedding pipeline",
            "GATE-EMBEDDING-SUPPLY-CHAIN",
            "GATE-G011",
            "Human decision excluding managed GigaChat/GigaChat API embedding paths",
        ],
        "proof_artifact": "Local embedding/retrieval experiment report with model provenance, revision/checksum, resource envelope, dataset skeleton, metrics, and leakage checks.",
        "acceptance_criteria": [
            "Only local/open-weight embedding candidates are considered.",
            "Model provenance and vector dimensions are recorded.",
            "Retrieval metrics are reported as experiment results, not product readiness.",
        ],
        "recommended_next_unit": "Future retrieval/embedding experiment slice.",
        "non_claims": [
            "Does not promote any embedding model to product default.",
            "Does not allow managed embedding API fallback.",
            "Does not prove product retrieval quality or FalkorDB vector scale.",
        ],
    },
    {
        "track_id": "TRACK-RUNTIME-MIGRATION-SMOKE",
        "title": "Runtime migration/import smoke proof",
        "gate_ids": ["GATE-G015"],
        "track_status": "needs-runtime-experiment",
        "scope_boundary": "Prove a bounded import/load/migration smoke path with diagnostics before runtime migration readiness is claimed.",
        "required_inputs": [
            "Current parser staging graph artifacts",
            "Future FalkorDB load-shape recommendation",
            "GATE-G015",
        ],
        "proof_artifact": "Runtime migration smoke report with import package, graph load shape, rollback/failure diagnostics, and explicit non-production boundary.",
        "acceptance_criteria": [
            "Smoke proof uses bounded fixture data and reports exact graph load shape.",
            "Failure diagnostics include phase, last error, and rollback/remediation guidance.",
            "The result remains non-production unless scale and operational checks are separately proven.",
        ],
        "recommended_next_unit": "Future runtime migration smoke slice.",
        "non_claims": [
            "Does not prove FalkorDB production loading behavior.",
            "Does not prove production scale.",
            "Does not prove product ETL readiness.",
        ],
    },
]


def escape_md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def load_matrix(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc


def validate_track_definitions(matrix: dict[str, Any]) -> None:
    matrix_gate_ids = {row["gate_id"] for row in matrix.get("gate_rows", []) if row.get("disposition") != "defer"}
    assigned: list[str] = []
    for track in TRACK_DEFINITIONS:
        gate_ids = track.get("gate_ids", [])
        if not gate_ids:
            raise RuntimeError(f"track {track.get('track_id')} must assign at least one gate")
        assigned.extend(gate_ids)
        for field in [
            "track_id",
            "title",
            "track_status",
            "scope_boundary",
            "required_inputs",
            "proof_artifact",
            "acceptance_criteria",
            "recommended_next_unit",
            "non_claims",
        ]:
            if not track.get(field):
                raise RuntimeError(f"track {track.get('track_id')} missing required field {field}")
    duplicate_assignments = sorted({gate_id for gate_id in assigned if assigned.count(gate_id) > 1})
    if duplicate_assignments:
        raise RuntimeError(f"duplicate gate assignments: {', '.join(duplicate_assignments)}")
    assigned_set = set(assigned)
    missing = sorted(matrix_gate_ids - assigned_set)
    stale = sorted(assigned_set - matrix_gate_ids)
    errors: list[str] = []
    if missing:
        errors.append(f"unassigned matrix gates: {', '.join(missing)}")
    if stale:
        errors.append(f"track gates not present in matrix: {', '.join(stale)}")
    if errors:
        raise RuntimeError("; ".join(errors))


def build_track_split(matrix: dict[str, Any]) -> dict[str, Any]:
    validate_track_definitions(matrix)
    gate_lookup = {row["gate_id"]: row for row in matrix.get("gate_rows", [])}
    tracks: list[dict[str, Any]] = []
    for definition in TRACK_DEFINITIONS:
        gate_rows = [gate_lookup[gate_id] for gate_id in definition["gate_ids"]]
        tracks.append(
            {
                **definition,
                "gate_dispositions": sorted({row["disposition"] for row in gate_rows}),
                "risk_levels": sorted({row["risk_level"] for row in gate_rows}),
                "r04_links": sorted({link for row in gate_rows for link in row.get("r04_links", [])}),
                "source_gates": gate_rows,
            }
        )
    return {
        "schema_version": "legalgraph-architecture-major-track-split/v1",
        "record_kind": "derived-major-track-split",
        "source_matrix": "prd/architecture/remediation_matrix.json",
        "non_authoritative": True,
        "summary": {
            "track_count": len(tracks),
            "assigned_gate_count": sum(len(track["gate_ids"]) for track in tracks),
            "source_gate_count": len([row for row in matrix.get("gate_rows", []) if row.get("disposition") != "defer"]),
        },
        "tracks": tracks,
        "non_claims": [
            "This track split is planning evidence only.",
            "Track assignment does not retire proof gates.",
            "Track assignment does not prove product readiness, legal correctness, parser completeness, retrieval quality, generated-Cypher safety, FalkorDB production behavior, or LLM authority.",
        ],
    }


def render_markdown(track_split: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Major Architecture Proof Track Split",
        "",
        "> **Scope:** Derived, non-authoritative M007/S03 planning artifact. It groups open proof gates into future proof tracks and does not retire any gate.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Tracks | {track_split['summary']['track_count']} |",
        f"| Assigned gates | {track_split['summary']['assigned_gate_count']} |",
        f"| Source gates | {track_split['summary']['source_gate_count']} |",
        "",
        "## Tracks",
        "",
        "| Track | Status | Gates | R04 Links | Proof Artifact | Next Unit |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for track in track_split["tracks"]:
        lines.append(
            f"| `{escape_md(track['track_id'])}` — {escape_md(track['title'])} | "
            f"{escape_md(track['track_status'])} | {escape_md(', '.join(track['gate_ids']))} | "
            f"{escape_md(', '.join(track['r04_links']))} | {escape_md(track['proof_artifact'])} | "
            f"{escape_md(track['recommended_next_unit'])} |"
        )
    lines.extend([
        "",
        "## Track Boundaries and Acceptance Criteria",
        "",
    ])
    for track in track_split["tracks"]:
        lines.extend([
            f"### {escape_md(track['track_id'])}: {escape_md(track['title'])}",
            "",
            f"- Status: `{escape_md(track['track_status'])}`",
            f"- Scope boundary: {escape_md(track['scope_boundary'])}",
            "- Required inputs:",
        ])
        for item in track["required_inputs"]:
            lines.append(f"  - {escape_md(item)}")
        lines.append("- Acceptance criteria:")
        for item in track["acceptance_criteria"]:
            lines.append(f"  - {escape_md(item)}")
        lines.append("- Non-claims:")
        for item in track["non_claims"]:
            lines.append(f"  - {escape_md(item)}")
        lines.append("")
    lines.extend([
        "## Global Non-Claims",
        "",
    ])
    for claim in track_split["non_claims"]:
        lines.append(f"- {escape_md(claim)}")
    lines.extend([
        "",
        "---",
        "",
        "*Generated from `prd/architecture/remediation_matrix.json`. Source evidence remains authoritative.*",
    ])
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def check_output(path: Path, expected: str, label: str) -> bool:
    if not path.exists():
        print(f"missing {label}: {path}; regenerate with `uv run python scripts/generate-architecture-track-split.py`", file=sys.stderr)
        return False
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        print(f"stale {label}: {path}; regenerate with `uv run python scripts/generate-architecture-track-split.py`", file=sys.stderr)
        return False
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate/check the derived major architecture proof-track split.")
    parser.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX_JSON_PATH)
    parser.add_argument("--track-json", type=Path, default=DEFAULT_TRACK_JSON_PATH)
    parser.add_argument("--track-md", type=Path, default=DEFAULT_TRACK_MD_PATH)
    parser.add_argument("--check", action="store_true", help="Compare expected outputs without rewriting.")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        matrix = load_matrix(args.matrix_json)
        track_split = build_track_split(matrix)
    except RuntimeError as exc:
        print(f"track split error: {exc}", file=sys.stderr)
        return 1

    expected_json = json.dumps(track_split, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(track_split)

    if args.check:
        if not check_output(args.track_json, expected_json, "track split JSON"):
            return 1
        if not check_output(args.track_md, expected_md, "track split Markdown"):
            return 1
    else:
        write_atomic(args.track_json, expected_json)
        write_atomic(args.track_md, expected_md)

    summary = {
        "status": "ok",
        "mode": "check" if args.check else "write",
        "track_json": str(args.track_json),
        "track_md": str(args.track_md),
        "track_count": track_split["summary"]["track_count"],
        "assigned_gate_count": track_split["summary"]["assigned_gate_count"],
        "non_authoritative": True,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
