#!/usr/bin/env python3
"""Generate a derived, non-authoritative architecture remediation matrix.

The matrix is a planning artifact for M007/R04 closure. It classifies current
open proof gates and R04 recommendations without upgrading any product,
runtime, parser, retrieval, generated-Cypher, FalkorDB, or legal-answer claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_JSON_PATH = ROOT / "prd/architecture/architecture_graph_report.json"
DEFAULT_ITEMS_JSONL_PATH = ROOT / "prd/architecture/architecture_items.jsonl"
DEFAULT_R04_RECOMMENDATIONS_PATH = ROOT / "prd/architecture/review_findings/04/06_recommendations.json"
DEFAULT_MATRIX_JSON_PATH = ROOT / "prd/architecture/remediation_matrix.json"
DEFAULT_MATRIX_MD_PATH = ROOT / "prd/architecture/remediation_matrix.md"

ALLOWED_DISPOSITIONS = {"proof-now", "product-decision", "runtime-experiment", "defer"}

GATE_DECISIONS: dict[str, dict[str, Any]] = {
    "GATE-EMBEDDING-SUPPLY-CHAIN": {
        "disposition": "runtime-experiment",
        "r04_links": ["R04-REC-003"],
        "rationale": "Embedding candidates need local model provenance, integrity, resource, and leakage checks before promotion.",
        "next_proof_artifact": "Embedding supply-chain experiment report with model revision/checksum, local runtime envelope, vector dimensions, and no-secret/no-raw-vector leakage checks.",
        "owner_scope": "future-embedding-supply-chain-proof",
        "target_track": "M007/S03 retrieval-embedding track",
        "non_claims": [
            "Does not promote any embedding model to product default.",
            "Does not allow managed embedding API fallback.",
            "Does not prove retrieval quality.",
        ],
    },
    "GATE-G005": {
        "disposition": "product-decision",
        "r04_links": ["R04-REC-006"],
        "rationale": "Same-date temporal conflict behavior is a product semantics decision before runtime fixture proof can be meaningful.",
        "next_proof_artifact": "Temporal conflict policy plus fixture-backed same-date/new-edition/source-revision tests.",
        "owner_scope": "future-temporal-proof",
        "target_track": "M007/S03 temporal-model track",
        "non_claims": [
            "Does not specify temporal storage implementation.",
            "Does not validate temporal conflict resolution.",
            "Does not prove import runtime behavior.",
        ],
    },
    "GATE-G008": {
        "disposition": "proof-now",
        "r04_links": ["R04-REC-005"],
        "rationale": "Parser and retrieval proof already has bounded M006 artifacts; the next useful step is executable golden tests over real parser outputs and expected retrieval/evidence behavior.",
        "next_proof_artifact": "Parser/retrieval golden-test suite using tracked parser records and explicit no-answer/non-claim cases.",
        "owner_scope": "future-parser-retrieval-proof",
        "target_track": "M007/S03 parser-retrieval track",
        "non_claims": [
            "Does not prove parser completeness.",
            "Does not prove citation-safe retrieval.",
            "Does not prove legal-answer correctness.",
        ],
    },
    "GATE-G011": {
        "disposition": "runtime-experiment",
        "r04_links": ["R04-REC-004", "R04-REC-014"],
        "rationale": "Retrieval quality and migration strategy need measured runtime/evaluation evidence rather than registry-only assertions.",
        "next_proof_artifact": "Retrieval quality and migration experiment report with dataset skeleton, metrics, fallback boundaries, and explicit non-readiness result states.",
        "owner_scope": "future-retrieval-quality-proof",
        "target_track": "M007/S03 retrieval-embedding track",
        "non_claims": [
            "Does not prove product retrieval quality.",
            "Does not commit to a vector store topology.",
            "Does not validate FalkorDB production scale.",
        ],
    },
    "GATE-G015": {
        "disposition": "runtime-experiment",
        "r04_links": ["R04-REC-004"],
        "rationale": "Runtime migration/readiness claims require executable import/load/migration smoke evidence, not registry coverage alone.",
        "next_proof_artifact": "Runtime migration smoke proof with import package, graph load shape, rollback/failure diagnostics, and non-production boundary.",
        "owner_scope": "future-runtime-migration-proof",
        "target_track": "M007/S03 graph-runtime track",
        "non_claims": [
            "Does not prove FalkorDB production loading behavior.",
            "Does not prove production scale.",
            "Does not prove product ETL readiness.",
        ],
    },
    "GATE-GENERATED-CYPHER-SAFETY": {
        "disposition": "proof-now",
        "r04_links": ["R04-REC-003", "R017"],
        "rationale": "Generated-Cypher safety is the highest-risk explicit gate and should be retired by deterministic validator tests before any Legal KnowQL product-readiness claim.",
        "next_proof_artifact": "Generated-Cypher validator suite covering read-only enforcement, schema grounding, evidence-returning queries, injection rejection, and unsafe write rejection.",
        "owner_scope": "future-generated-cypher-safety-proof",
        "target_track": "M007/S03 generated-cypher track",
        "non_claims": [
            "Does not prove provider generation quality.",
            "Does not authorize executing raw generated Cypher.",
            "Does not validate product Legal KnowQL readiness.",
        ],
    },
    "GATE-LEGAL-NEXUS-ACCESS-CONTROL": {
        "disposition": "product-decision",
        "r04_links": ["R04-REC-003"],
        "rationale": "Access-control proof needs a product API/caller boundary decision before meaningful authz tests can be specified.",
        "next_proof_artifact": "Legal Nexus access-control decision and negative-test plan defining caller roles, authorization boundaries, audit logging, and denied-operation diagnostics.",
        "owner_scope": "future-api-security-proof",
        "target_track": "M007/S03 api-product/security track",
        "non_claims": [
            "Does not assert current product is insecure.",
            "Does not prove access-control enforcement.",
            "Does not define a production API surface.",
        ],
    },
}

R04_DISPOSITIONS: dict[str, dict[str, str]] = {
    "R04-REC-001": {"status": "implemented-s01", "next": "Keep as coverage baseline; do not treat one record per layer as completeness."},
    "R04-REC-002": {"status": "implemented-s01", "next": "Keep connectivity visible in graph report; reassess if new orphan findings appear."},
    "R04-REC-003": {"status": "implemented-s01-open-gates", "next": "Use proof-gate rows to split concrete product/runtime proof work."},
    "R04-REC-004": {"status": "downstream-s03", "next": "Project FR/NFR coverage only after S02 matrix classifies current gates and deferrals."},
    "R04-REC-005": {"status": "implemented-s01", "next": "Use parser bridge records as inputs for parser/retrieval golden-test proof."},
    "R04-REC-006": {"status": "implemented-s01", "next": "Use temporal records as inputs for temporal conflict policy and fixture tests."},
    "R04-REC-007": {"status": "defer-s04", "next": "Handle anchor line ranges/quote hashes as a minor hardening pass."},
    "R04-REC-008": {"status": "defer-s04", "next": "Document schema evolution policy after blocker/major proof tracks are split."},
    "R04-REC-009": {"status": "implemented-s01", "next": "Claims ledger now includes claim-domain separation."},
    "R04-REC-010": {"status": "defer-s04", "next": "Decide report/dashboard roles in minor recommendation disposition."},
    "R04-REC-011": {"status": "defer-s04", "next": "Document edge confidence semantics or schedule schema v2 work."},
    "R04-REC-012": {"status": "defer-s04", "next": "Document CI/regenerate hook recipe after matrix/check workflow stabilizes."},
    "R04-REC-013": {"status": "defer-s04", "next": "Decide schema-level versus extractor-level ID prefix enforcement."},
    "R04-REC-014": {"status": "downstream-s03", "next": "Use coverage metrics only with explicit non-readiness caveat."},
    "R04-REC-015": {"status": "partially-implemented-s01", "next": "S04 should decide whether additional risks edges are necessary or whether current coverage is sufficient."},
    "R04-REC-016": {"status": "defer-s04", "next": "Fixture-test contradiction/supersession branches without adding fake production edges."},
    "R04-REC-017": {"status": "partially-implemented-s01", "next": "Verifier summary has a non-authoritative boundary; S04 can decide whether to add a longer CLI prose card."},
    "R04-REC-018": {"status": "defer-s04", "next": "Document .gsd path stability assumption or path-mapping response procedure."},
}


def escape_md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc


def load_items(path: Path) -> dict[str, dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing input: {path}") from exc
    items: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid JSONL in {path}:{line_number}: {exc}") from exc
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise RuntimeError(f"missing id in {path}:{line_number}")
        items[record_id] = record
    return items


def validate_required_gate_decisions(report: dict[str, Any]) -> list[str]:
    gate_ids = [gate.get("id") for gate in report.get("unresolved_proof_gates", [])]
    if any(not isinstance(gate_id, str) for gate_id in gate_ids):
        raise RuntimeError("all unresolved_proof_gates entries must have string id")
    current = set(gate_ids)
    expected = set(GATE_DECISIONS)
    missing = sorted(current - expected)
    stale = sorted(expected - current)
    errors: list[str] = []
    if missing:
        errors.append(f"missing gate decision rows: {', '.join(missing)}")
    if stale:
        errors.append(f"stale gate decision rows not present in report: {', '.join(stale)}")
    return errors


def validate_r04_dispositions(recommendations: dict[str, Any]) -> list[str]:
    rec_ids = {item.get("id") for item in recommendations.get("items", [])}
    if any(not isinstance(rec_id, str) for rec_id in rec_ids):
        return ["all R04 recommendation items must have string id"]
    expected = set(R04_DISPOSITIONS)
    missing = sorted(rec_ids - expected)
    stale = sorted(expected - rec_ids)
    errors: list[str] = []
    if missing:
        errors.append(f"missing R04 disposition rows: {', '.join(missing)}")
    if stale:
        errors.append(f"stale R04 disposition rows not present in recommendations: {', '.join(stale)}")
    return errors


def build_matrix(report: dict[str, Any], items: dict[str, dict[str, Any]], recommendations: dict[str, Any]) -> dict[str, Any]:
    errors = validate_required_gate_decisions(report)
    errors.extend(validate_r04_dispositions(recommendations))
    if errors:
        raise RuntimeError("; ".join(errors))

    gate_rows: list[dict[str, Any]] = []
    for gate in sorted(report.get("unresolved_proof_gates", []), key=lambda item: item["id"]):
        gate_id = gate["id"]
        item = items.get(gate_id)
        if item is None:
            raise RuntimeError(f"unresolved gate {gate_id} is missing from item registry")
        decision = GATE_DECISIONS[gate_id]
        disposition = decision["disposition"]
        if disposition not in ALLOWED_DISPOSITIONS:
            raise RuntimeError(f"invalid disposition for {gate_id}: {disposition}")
        non_claims = decision.get("non_claims", [])
        if not non_claims:
            raise RuntimeError(f"gate {gate_id} must have explicit non_claims")
        gate_rows.append(
            {
                "gate_id": gate_id,
                "title": item.get("title", ""),
                "layer": item.get("layer", ""),
                "risk_level": item.get("risk_level", ""),
                "disposition": disposition,
                "r04_links": decision["r04_links"],
                "rationale": decision["rationale"],
                "next_proof_artifact": decision["next_proof_artifact"],
                "owner_scope": decision["owner_scope"],
                "target_track": decision["target_track"],
                "source_anchors": item.get("source_anchors", []),
                "non_claims": non_claims,
            }
        )

    recommendation_rows: list[dict[str, Any]] = []
    for rec in sorted(recommendations.get("items", []), key=lambda item: item["id"]):
        disposition = R04_DISPOSITIONS[rec["id"]]
        recommendation_rows.append(
            {
                "id": rec["id"],
                "title": rec.get("title", ""),
                "priority": rec.get("priority", ""),
                "status": disposition["status"],
                "next": disposition["next"],
                "resolves": rec.get("resolves", []),
                "non_claims": rec.get("non_claims", []),
            }
        )

    counts_by_disposition = {key: 0 for key in sorted(ALLOWED_DISPOSITIONS)}
    for row in gate_rows:
        counts_by_disposition[row["disposition"]] += 1

    return {
        "schema_version": "legalgraph-architecture-remediation-matrix/v1",
        "record_kind": "derived-remediation-matrix",
        "review_id": "R04",
        "non_authoritative": True,
        "source_inputs": [
            "prd/architecture/architecture_graph_report.json",
            "prd/architecture/architecture_items.jsonl",
            "prd/architecture/review_findings/04/06_recommendations.json",
        ],
        "allowed_dispositions": sorted(ALLOWED_DISPOSITIONS),
        "summary": {
            "unresolved_gate_count": len(gate_rows),
            "r04_recommendation_count": len(recommendation_rows),
            "gate_counts_by_disposition": counts_by_disposition,
        },
        "gate_rows": gate_rows,
        "recommendation_rows": recommendation_rows,
        "non_claims": [
            "This matrix is a planning artifact, not product readiness evidence.",
            "Disposition classes prioritize proof work; they do not validate runtime behavior.",
            "Open proof gates remain unresolved until their next_proof_artifact is produced and verified.",
            "Resolving all R04 recommendations does not prove legal-answer correctness, parser completeness, retrieval quality, generated-Cypher safety, FalkorDB production behavior, or LLM legal authority.",
        ],
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Architecture Remediation Matrix",
        "",
        "> **Scope:** Derived, non-authoritative R04/M007 planning artifact. It classifies open proof gates and R04 recommendations so downstream work can be split safely. It does not prove product readiness.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Unresolved proof gates | {matrix['summary']['unresolved_gate_count']} |",
        f"| R04 recommendations | {matrix['summary']['r04_recommendation_count']} |",
        "",
        "| Disposition | Gate Count |",
        "| --- | ---: |",
    ]
    for disposition, count in matrix["summary"]["gate_counts_by_disposition"].items():
        lines.append(f"| {escape_md(disposition)} | {count} |")

    lines.extend([
        "",
        "## Gate Remediation Rows",
        "",
        "| Gate | Layer | Risk | Disposition | R04 Links | Next Proof Artifact | Target Track |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in matrix["gate_rows"]:
        lines.append(
            f"| `{escape_md(row['gate_id'])}` | {escape_md(row['layer'])} | {escape_md(row['risk_level'])} | "
            f"{escape_md(row['disposition'])} | {escape_md(', '.join(row['r04_links']))} | "
            f"{escape_md(row['next_proof_artifact'])} | {escape_md(row['target_track'])} |"
        )

    lines.extend([
        "",
        "## Gate Non-Claims",
        "",
        "| Gate | Non-Claims |",
        "| --- | --- |",
    ])
    for row in matrix["gate_rows"]:
        lines.append(
            f"| `{escape_md(row['gate_id'])}` | "
            f"{escape_md('; '.join(row['non_claims']))} |"
        )

    lines.extend([
        "",
        "## R04 Recommendation Disposition",
        "",
        "| Recommendation | Priority | Status | Next |",
        "| --- | --- | --- | --- |",
    ])
    for row in matrix["recommendation_rows"]:
        lines.append(
            f"| `{escape_md(row['id'])}` — {escape_md(row['title'])} | "
            f"{escape_md(row['priority'])} | {escape_md(row['status'])} | {escape_md(row['next'])} |"
        )

    lines.extend([
        "",
        "## Non-Claims",
        "",
    ])
    for claim in matrix["non_claims"]:
        lines.append(f"- {escape_md(claim)}")

    lines.extend([
        "",
        "---",
        "",
        "*Generated from `architecture_graph_report.json`, `architecture_items.jsonl`, and R04 recommendations. Source evidence remains authoritative.*",
    ])
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def check_output(path: Path, expected: str, label: str) -> bool:
    if not path.exists():
        print(f"missing {label}: {path}; regenerate with `uv run python scripts/generate-architecture-remediation-matrix.py`", file=sys.stderr)
        return False
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        print(f"stale {label}: {path}; regenerate with `uv run python scripts/generate-architecture-remediation-matrix.py`", file=sys.stderr)
        return False
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate/check the derived architecture remediation matrix.")
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--items-jsonl", type=Path, default=DEFAULT_ITEMS_JSONL_PATH)
    parser.add_argument("--r04-recommendations", type=Path, default=DEFAULT_R04_RECOMMENDATIONS_PATH)
    parser.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX_JSON_PATH)
    parser.add_argument("--matrix-md", type=Path, default=DEFAULT_MATRIX_MD_PATH)
    parser.add_argument("--check", action="store_true", help="Compare expected matrix outputs without rewriting.")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = load_json(args.report_json)
        items = load_items(args.items_jsonl)
        recommendations = load_json(args.r04_recommendations)
        matrix = build_matrix(report, items, recommendations)
    except RuntimeError as exc:
        print(f"remediation matrix error: {exc}", file=sys.stderr)
        return 1

    expected_json = json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(matrix)

    if args.check:
        if not check_output(args.matrix_json, expected_json, "matrix JSON"):
            return 1
        if not check_output(args.matrix_md, expected_md, "matrix Markdown"):
            return 1
    else:
        write_atomic(args.matrix_json, expected_json)
        write_atomic(args.matrix_md, expected_md)

    summary = {
        "status": "ok",
        "mode": "check" if args.check else "write",
        "matrix_json": str(args.matrix_json),
        "matrix_md": str(args.matrix_md),
        "unresolved_gate_count": matrix["summary"]["unresolved_gate_count"],
        "r04_recommendation_count": matrix["summary"]["r04_recommendation_count"],
        "non_authoritative": True,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
