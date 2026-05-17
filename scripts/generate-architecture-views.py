#!/usr/bin/env python3
"""Generate derived, non-authoritative architecture health dashboard and views.

Reads the derived S03/S04 graph report (architecture_graph_report.json) and
produces compact human-readable views for health status, layer coverage, risk,
non-authoritative boundary documentation, and a claims safety ledger. The GSD
validation contract stays intentionally small: priority buckets, promotion
blockers, typed drift classes, and R035 gate status only; no dashboard or
interactive graph UI is implied by these generated views.
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
DEFAULT_HEALTH_MD_PATH = ROOT / "prd/architecture/architecture_health.md"
DEFAULT_BLOCKERS_MD_PATH = ROOT / "prd/architecture/product_readiness_blockers.md"
DEFAULT_CLAIMS_MD_PATH = ROOT / "prd/architecture/claims_ledger.md"


def escape_md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def drift_counts_from_report(report: dict[str, Any]) -> dict[str, int]:
    """Extract optional verifier drift counts from a report-like payload.

    The canonical S03 graph report does not contain verifier failures when the
    registry is healthy. Tests and future diagnostic integrations can pass either
    a top-level ``drift_counts`` map, a nested ``verifier.drift_counts`` map, or
    a ``diagnostics`` list with ``drift_kind`` values. This helper keeps the view
    diagnostics-only: it counts categories but never implies repair or proof.
    """
    raw_counts = report.get("drift_counts")
    if not isinstance(raw_counts, dict):
        verifier = report.get("verifier")
        raw_counts = verifier.get("drift_counts") if isinstance(verifier, dict) else None

    counts: dict[str, int] = {}
    if isinstance(raw_counts, dict):
        for drift_kind, count in raw_counts.items():
            if isinstance(drift_kind, str) and isinstance(count, int) and count > 0:
                counts[drift_kind] = count

    diagnostics = report.get("diagnostics", [])
    if isinstance(diagnostics, list):
        for diagnostic in diagnostics:
            if not isinstance(diagnostic, dict):
                continue
            drift_kind = diagnostic.get("drift_kind")
            if isinstance(drift_kind, str) and drift_kind:
                counts[drift_kind] = counts.get(drift_kind, 0) + 1

    return dict(sorted(counts.items()))


PRIORITY_BUCKETS: dict[str, tuple[str, str]] = {
    "critical": ("P0", "critical-gate"),
    "high": ("P1", "high-priority-blocker"),
    "medium": ("P2", "medium-diagnostic"),
    "low": ("P3", "backlog-only-signal"),
}

R035_RULES: tuple[dict[str, Any], ...] = (
    {
        "terms": ("Akoma Ntoso", "LegalDocML", "FRBR"),
        "safe_bucket": "compatibility/reference projection only",
        "gate": "GATE-AKOMA-FRBR-NORMALIZATION",
        "minimum_proof_level": "static-check",
    },
    {
        "terms": ("LKIF", "deontic mapping"),
        "safe_bucket": "proof-gated candidate",
        "gate": "GATE-LKIF-DEONTIC-BENCHMARK",
        "minimum_proof_level": "unit-test",
    },
    {
        "terms": ("RusLegalCore",),
        "safe_bucket": "proof-gated domain-scope candidate",
        "gate": "GATE-RUSLEGALCORE-SCOPE",
        "minimum_proof_level": "static-check",
    },
    {
        "terms": ("BFO", "GOST", "GOST R 59798-2021", "OWL", "OWL 2", "Common Logic"),
        "safe_bucket": "deferred formal-alignment review",
        "gate": "GATE-BFO-GOST-ALIGNMENT",
        "minimum_proof_level": "static-check",
    },
    {
        "terms": ("legal source hierarchy", "source hierarchy", "legal collision policy", "collision policy", "lex superior", "lex specialis", "lex posterior", "supersession"),
        "safe_bucket": "proof-gated legal-priority candidate",
        "gate": "GATE-LEGAL-COLLISION-POLICY",
        "minimum_proof_level": "static-check",
    },
    {
        "terms": ("Ontology GraphRAG", "ontology-aware GraphRAG", "ontology-driven GraphRAG"),
        "safe_bucket": "proof-gated integration candidate",
        "gate": "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
        "minimum_proof_level": "integration-test",
    },
    {
        "terms": ("GraphRAG",),
        "safe_bucket": "proof-gated integration candidate",
        "gate": "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
        "minimum_proof_level": "integration-test",
    },
    {
        "terms": ("graph-vector", "HNSW", "hybrid retrieval"),
        "safe_bucket": "deferred runtime behavior claim",
        "gate": "GATE-G015 or GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
        "minimum_proof_level": "runtime-smoke",
    },
    {
        "terms": ("pilot-scale", "1000-document", "1,000-document"),
        "safe_bucket": "deferred readiness proof",
        "gate": "GATE-PILOT-SCALE-READINESS",
        "minimum_proof_level": "integration-test",
    },
)

PROOF_LEVEL_ORDER = {
    "none": 0,
    "source-anchor": 1,
    "static-check": 2,
    "unit-test": 3,
    "integration-test": 4,
    "runtime-smoke": 5,
    "real-document-proof": 6,
    "production-observation": 7,
}


def priority_bucket_for_record(record: dict[str, Any]) -> tuple[str, str]:
    """Return the compact GSD priority bucket for an architecture record."""
    priority = str(record.get("priority") or record.get("risk_level") or "").lower()
    return PRIORITY_BUCKETS.get(priority, ("P3", "backlog-only-signal"))


def priority_summary(items_lookup: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group records into P0-P3 buckets for compact validation views."""
    grouped: dict[str, list[dict[str, Any]]] = {"P0": [], "P1": [], "P2": [], "P3": []}
    for record in items_lookup.values():
        bucket, _ = priority_bucket_for_record(record)
        grouped[bucket].append(record)
    for records in grouped.values():
        records.sort(key=lambda item: str(item.get("id", "")))
    return grouped


def is_promotion_blocker(record: dict[str, Any]) -> bool:
    """Return True when a record blocks safe promotion rather than proving readiness."""
    status = str(record.get("status", ""))
    proof_level = str(record.get("proof_level", ""))
    record_type = str(record.get("type", ""))
    bucket, _ = priority_bucket_for_record(record)
    return (
        record_type == "proof_gate"
        or status == "blocked"
        or (bucket in {"P0", "P1"} and proof_level == "none")
    )


def deferred_candidates(items_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return low-urgency records that should remain backlog/candidate material."""
    candidates = [
        record
        for record in items_lookup.values()
        if str(record.get("status", "")) in {"deferred", "proposed"}
        or str(record.get("lifecycle", "")) in {"deferred", "proposed", "researching"}
        and priority_bucket_for_record(record)[0] == "P3"
    ]
    return sorted(candidates, key=lambda item: str(item.get("id", "")))


def r035_gate_rows(items_lookup: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Return compact R035 ontology/external-standard guardrail rows."""
    rows: list[dict[str, str]] = []
    ids = set(items_lookup)
    for record_id, record in sorted(items_lookup.items()):
        haystack = " ".join(str(record.get(field, "")) for field in ("id", "title", "summary"))
        for rule in R035_RULES:
            matched_terms = [term for term in rule["terms"] if term.lower() in haystack.lower()]
            if not matched_terms:
                continue
            gate_expr = str(rule["gate"])
            required_gates = [part.strip() for part in gate_expr.split(" or ")]
            missing: list[str] = []
            if not any(gate in ids for gate in required_gates):
                missing.append(f"missing gate {gate_expr}")
            proof_level = str(record.get("proof_level", "none"))
            minimum = str(rule["minimum_proof_level"])
            if PROOF_LEVEL_ORDER.get(proof_level, -1) < PROOF_LEVEL_ORDER.get(minimum, 999):
                missing.append(f"proof_level<{minimum}")
            if not record.get("owner"):
                missing.append("missing owner")
            if not record.get("status"):
                missing.append("missing status")
            rows.append({
                "id": str(record_id),
                "trigger": ", ".join(matched_terms),
                "safe_bucket": str(rule["safe_bucket"]),
                "required_gate": gate_expr,
                "minimum_proof_level": minimum,
                "current_status": str(record.get("status", "")),
                "missing": "; ".join(missing) if missing else "none",
                "remediation_class": "add-proof-gate" if missing else "none",
            })
            break
    return rows


def render_health_dashboard(
    report: dict[str, Any],
    items_lookup: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Render a compact health status dashboard from the graph report."""
    items_lookup = items_lookup or {}
    counts = report.get("counts", {})
    layer_coverage = report.get("layer_coverage", {})
    missing_layers = layer_coverage.get("missing_layers", [])
    invalid_layers = layer_coverage.get("invalid_layers", [])
    unresolved_gates = report.get("unresolved_proof_gates", [])
    orphan_findings = report.get("orphan_findings", [])
    high_risk_nodes = report.get("high_risk_nodes", [])
    contradiction_edges = report.get("contradiction_edges", [])
    non_claims_summary = report.get("non_claims_summary", {})
    drift_counts = drift_counts_from_report(report)
    total_drift_findings = sum(drift_counts.values())

    # Determine overall health status
    health_issues = []
    if missing_layers:
        health_issues.append(f"{len(missing_layers)} missing layer(s)")
    if unresolved_gates:
        health_issues.append(f"{len(unresolved_gates)} unresolved proof gate(s)")
    if orphan_findings:
        health_issues.append(f"{len(orphan_findings)} orphan finding(s)")
    if invalid_layers:
        health_issues.append(f"{len(invalid_layers)} invalid layer record(s)")

    critical_count = sum(1 for n in high_risk_nodes if n.get("risk_level") == "critical")
    high_count = sum(1 for n in high_risk_nodes if n.get("risk_level") == "high")

    health_status = "⚠️  Needs Attention" if health_issues else "✅  Healthy"

    lines = [
        "# Architecture Health Dashboard",
        "",
        f"**Status:** {health_status}",
        f"**Non-Authoritative:** This dashboard is derived from graph artifacts and does not validate product/runtime/legal claims. "
        "PRD, GSD, ADR, source anchors, and runtime evidence remain the authoritative source of truth.",
        "",
        "---",
        "",
        "## Quick Stats",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Total Nodes | {counts.get('nodes', 0)} |",
        f"| Total Edges | {counts.get('edges', 0)} |",
        f"| Schema Layers | {len(layer_coverage.get('counts', {}))} |",
        f"| Missing Layers | {len(missing_layers)} |",
        f"| Invalid Layer Records | {len(invalid_layers)} |",
        f"| Unresolved Proof Gates | {len(unresolved_gates)} |",
        f"| Orphan Findings | {len(orphan_findings)} |",
        f"| Contradiction Edges | {len(contradiction_edges)} |",
        f"| High/Critical Risk Nodes | {len(high_risk_nodes)} ({critical_count} critical, {high_count} high) |",
        f"| Nodes with Non-Claims | {non_claims_summary.get('nodes_with_non_claims', 0)} |",
        f"| Total Non-Claims | {non_claims_summary.get('total_non_claims', 0)} |",
    ]

    if drift_counts:
        lines.append(f"| Drift Diagnostics | {total_drift_findings} |")

    lines.extend([
        "",
        "---",
        "",
    ])

    if items_lookup:
        buckets = priority_summary(items_lookup)
        blockers = [record for record in items_lookup.values() if is_promotion_blocker(record)]
        critical_blockers = sorted(
            [record for record in blockers if priority_bucket_for_record(record)[0] == "P0"],
            key=lambda item: str(item.get("id", "")),
        )
        high_priority_failures = sorted(
            [record for record in blockers if priority_bucket_for_record(record)[0] == "P1"],
            key=lambda item: str(item.get("id", "")),
        )
        deferred = deferred_candidates(items_lookup)
        lines.extend([
            "## GSD Validation Snapshot",
            "",
            "Priority and gate rows below are compact triage metadata only. They do not promote claims, prove product readiness, or replace source anchors.",
            "",
            "| Bucket | Diagnostic Class | Count |",
            "| --- | --- | ---: |",
        ])
        for priority, label in (("P0", "critical-gate"), ("P1", "high-priority-blocker"), ("P2", "medium-diagnostic"), ("P3", "backlog-only-signal")):
            lines.append(f"| {priority} | {label} | {len(buckets[priority])} |")
        lines.extend(["", "### Critical Blockers", ""])
        if critical_blockers:
            lines.extend(["| ID | Status | Proof Level | Remediation Class |", "| --- | --- | --- | --- |"])
            for record in critical_blockers[:10]:
                remediation = "add-proof-gate" if str(record.get("proof_level", "")) == "none" else "downgrade-claim"
                lines.append(f"| `{escape_md(record.get('id', ''))}` | {escape_md(record.get('status', ''))} | {escape_md(record.get('proof_level', ''))} | {remediation} |")
        else:
            lines.append("No P0 promotion blockers in the generated registry view.")
        lines.extend(["", "### High-Priority Validator Failures", ""])
        if high_priority_failures:
            lines.extend(["| ID | Status | Proof Level | Remediation Class |", "| --- | --- | --- | --- |"])
            for record in high_priority_failures[:10]:
                remediation = "add-proof-gate" if str(record.get("proof_level", "")) == "none" else "add-evidence-class"
                lines.append(f"| `{escape_md(record.get('id', ''))}` | {escape_md(record.get('status', ''))} | {escape_md(record.get('proof_level', ''))} | {remediation} |")
        else:
            lines.append("No P1 promotion blockers in the generated registry view.")
        lines.extend(["", "### Deferred Candidates", ""])
        if deferred:
            lines.extend(["| ID | Priority | Status | Safe Handling |", "| --- | --- | --- | --- |"])
            for record in deferred[:10]:
                bucket, label = priority_bucket_for_record(record)
                lines.append(f"| `{escape_md(record.get('id', ''))}` | {bucket} / {label} | {escape_md(record.get('status', ''))} | defer-to-backlog |")
        else:
            lines.append("No deferred or proposed backlog candidates in the generated registry view.")
        lines.extend([
            "",
            "### Non-Authoritative Warnings",
            "",
            f"- Non-claim statements visible in registry: {non_claims_summary.get('total_non_claims', 0)}.",
            "- Reports must not include raw legal text, secrets, provider payloads, vectors, prompts, or local-only execution artifact paths.",
            "- A passing generated view check is not product/runtime/legal validation.",
            "",
            "---",
            "",
        ])

    if drift_counts:
        lines.extend([
            "## Drift Diagnostics",
            "",
            "These verifier findings are non-authoritative diagnostics only. They do not prove product readiness, repair authoritative sources, or imply that derived projection regeneration is safe unless the verifier explicitly marks that drift class as safe to regenerate.",
            "",
            "| Drift Kind | Count |",
            "| --- | ---: |",
        ])
        for drift_kind, count in drift_counts.items():
            lines.append(f"| {escape_md(drift_kind)} | {count} |")
        lines.extend([
            "",
            "---",
            "",
        ])

    lines.extend([
        "## Layer Coverage",
        "",
    ])

    layer_counts = layer_coverage.get("counts", {})
    if layer_counts:
        lines.extend([
            "| Layer | Node Count |",
            "| --- | ---: |",
        ])
        for layer, count in sorted(layer_counts.items()):
            marker = "⚠️" if layer in missing_layers else ""
            lines.append(f"| {escape_md(layer)} {marker} | {count} |")

    if missing_layers:
        lines.extend([
            "",
            "### ⚠️  Missing Layers",
            "",
            "The following schema layers have no architecture records:",
            "",
        ])
        for layer in sorted(missing_layers):
            lines.append(f"- {escape_md(layer)}")
    else:
        lines.extend([
            "",
            "### ✅  All Schema Layers Covered",
            "",
            "Every defined schema layer has at least one architecture record.",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## Open Proof Gates",
        "",
    ])

    if unresolved_gates:
        lines.extend([
            "| ID | Layer | Owner | Risk | Verification |",
            "| --- | --- | --- | --- | --- |",
        ])
        for gate in unresolved_gates:
            lines.append(
                f"| {escape_md(gate.get('id', ''))} | {escape_md(gate.get('layer', ''))} "
                f"| {escape_md(gate.get('owner', ''))} | {escape_md(gate.get('risk_level', ''))} "
                f"| {escape_md(gate.get('verification', ''))[:60]}... |"
                if len(gate.get('verification', '')) > 60
                else f"| {escape_md(gate.get('id', ''))} | {escape_md(gate.get('layer', ''))} "
                     f"| {escape_md(gate.get('owner', ''))} | {escape_md(gate.get('risk_level', ''))} "
                     f"| {escape_md(gate.get('verification', ''))} |"
            )
    else:
        lines.extend([
            "No unresolved proof gates.",
            "",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## High-Risk Nodes",
        "",
    ])

    if high_risk_nodes:
        lines.extend([
            "| ID | Risk | Type | Layer | Status | Proof Level |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for node in high_risk_nodes:
            lines.append(
                f"| {escape_md(node.get('id', ''))} | "
                f"{escape_md(node.get('risk_level', ''))} | "
                f"{escape_md(node.get('type', ''))} | "
                f"{escape_md(node.get('layer', ''))} | "
                f"{escape_md(node.get('status', ''))} | "
                f"{escape_md(node.get('proof_level', ''))} |"
            )
    else:
        lines.extend([
            "No high or critical risk nodes.",
            "",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## Non-Authoritative Boundary",
        "",
        "This architecture graph and derived reports **do not** establish or validate:",
        "",
    ])

    non_claims_by_node = non_claims_summary.get("by_node", [])
    if non_claims_by_node:
        # Collect unique non-claim statements
        all_non_claims: set[str] = set()
        for node_entry in non_claims_by_node:
            for claim in node_entry.get("non_claims", []):
                all_non_claims.add(str(claim))

        lines.append("| Non-Claim |")
        lines.append("| --- |")
        for claim in sorted(all_non_claims):
            lines.append(f"| {escape_md(claim)} |")
    else:
        lines.append("No non-claims documented.")

    lines.extend([
        "",
        "---",
        "",
        "## Orphan Findings",
        "",
    ])

    if orphan_findings:
        lines.extend([
            "| ID | Rule |",
            "| --- | --- |",
        ])
        for finding in orphan_findings:
            lines.append(f"| {escape_md(finding.get('id', ''))} | {escape_md(finding.get('rule', ''))} |")
    else:
        lines.extend([
            "No orphan findings.",
            "",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## Weakly Connected Components",
        "",
    ])

    weak_components = report.get("weak_components", [])
    if weak_components:
        lines.extend([
            "| Size | Node Count |",
            "| --- | ---: |",
        ])
        for comp in sorted(weak_components, key=lambda c: -c["size"])[:10]:  # Top 10 largest
            lines.append(f"| {len(comp.get('nodes', []))} | {comp.get('size', 0)} |")
        if len(weak_components) > 10:
            lines.append(f"| _(other {len(weak_components) - 10} components)_ | |")
    else:
        lines.append("No weakly connected components.")

    lines.extend([
        "",
        "---",
        "",
        "*Dashboard generated from `prd/architecture/architecture_graph_report.json`. "
        "This is a derived, non-authoritative view. Source-of-truth remains with PRD, GSD, ADR, "
        "and source anchor evidence.*",
    ])

    return "\n".join(lines) + "\n"


def _load_items_lookup(items_path: Path) -> dict[str, dict[str, Any]]:
    """Load architecture items JSONL and build an id→record lookup for enrichment."""
    if not items_path.exists():
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for line in items_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            lookup[record.get("id", "")] = record
        except json.JSONDecodeError:
            continue
    return lookup


def render_blockers_report(
    report: dict[str, Any],
    items_lookup: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Render a product-readiness blockers report mapping gates/non-claims to proof work.

    This is a planning artifact for future milestone work. It does NOT assert
    product readiness; it makes next proof obligations visible.

    Args:
        report: The architecture graph report dict.
        items_lookup: Optional id→record lookup for enriching rows with title/owner/verification.
    """
    items_lookup = items_lookup or {}
    # ── Layer → capability-area mapping ─────────────────────────────────────────
    LAYER_MAP: dict[str, str] = {
        "parser-ingestion": "ETL / Parser",
        "temporal-model": "Temporal Model",
        "retrieval-embedding": "Retrieval / Embedding",
        "generated-cypher": "Legal KnowQL / Generated Cypher",
        "graph-runtime": "Graph Runtime",
        "security-safety": "Legal Answering",
    }

    def area_of(layer: str) -> str:
        return LAYER_MAP.get(layer, layer)

    # ── Collect unresolved gates ─────────────────────────────────────────────────
    unresolved_gates = report.get("unresolved_proof_gates", [])
    gate_ids: set[str] = {g["id"] for g in unresolved_gates}

    # ── Collect high-risk blocked/bounded evidence ───────────────────────────────
    high_risk_nodes = report.get("high_risk_nodes", [])
    blocked_nodes: list[dict[str, Any]] = [
        n for n in high_risk_nodes
        if n.get("id", "") not in gate_ids
        and n.get("status", "") in ("blocked", "bounded-evidence")
    ]

    # ── Build per-area gate/blocker lists (sorted for deterministic output) ─────
    # Include report-provided layers in addition to the curated display buckets so
    # new registry layers fail verifier policy, not markdown rendering.
    report_areas = {
        area_of(record.get("layer", ""))
        for record in [*unresolved_gates, *blocked_nodes]
        if record.get("layer", "")
    }
    CAPABILITY_AREAS = sorted(set(LAYER_MAP.values()) | report_areas)  # deterministic order

    gates_by_area: dict[str, list[dict[str, Any]]] = {a: [] for a in CAPABILITY_AREAS}
    for gate in unresolved_gates:
        gates_by_area[area_of(gate.get("layer", ""))].append(gate)

    blocked_by_area: dict[str, list[dict[str, Any]]] = {a: [] for a in CAPABILITY_AREAS}
    for node in blocked_nodes:
        blocked_by_area[area_of(node.get("layer", ""))].append(node)

    # ── Helpers ─────────────────────────────────────────────────────────────────
    non_claims_summary = report.get("non_claims_summary", {})
    _nc_by_id: dict[str, list[str]] = {}
    for entry in non_claims_summary.get("by_node", []):
        _nc_by_id[entry["id"]] = entry.get("non_claims", [])

    def gate_ncs(gate_id: str) -> list[str]:
        return _nc_by_id.get(gate_id) or list(items_lookup.get(gate_id, {}).get("non_claims", []))

    def node_ncs(node_id: str) -> list[str]:
        return _nc_by_id.get(node_id) or list(items_lookup.get(node_id, {}).get("non_claims", []))

    def _full_title(record_id: str) -> str:
        return escape_md(items_lookup.get(record_id, {}).get("title", "") or "")

    def _full_owner(record_id: str) -> str:
        return escape_md(items_lookup.get(record_id, {}).get("owner", "") or "")

    def _full_verification(record_id: str) -> str:
        return escape_md(items_lookup.get(record_id, {}).get("verification", "") or "")

    def render_gate_rows(gate: dict[str, Any]) -> list[str]:
        nid = gate.get("id", "")
        # Prefer graph-report field; fall back to items_lookup for title
        title = gate.get("title") or _full_title(nid)
        owner = gate.get("owner") or _full_owner(nid)
        ver = gate.get("verification") or _full_verification(nid)
        source_record = items_lookup.get(nid, gate)
        bucket, diagnostic_class = priority_bucket_for_record(source_record)
        status = escape_md(source_record.get("status", gate.get("status", "")))
        rows = [
            f"| `{nid}` | {title} "
            f"| {bucket} / {diagnostic_class} "
            f"| {status} "
            f"| {escape_md(gate.get('risk_level', ''))} "
            f"| {ver} "
            f"| {owner} |"
        ]
        for nc in gate_ncs(nid):
            rows.append(f"|  | {escape_md(nc)} | — | — | — | — | — |")
        return rows

    def render_node_rows(node: dict[str, Any]) -> list[str]:
        nid = node.get("id", "")
        # Enrich from items_lookup for title/owner/verification
        source_record = items_lookup.get(nid, node)
        title = _full_title(nid)
        owner = _full_owner(nid)
        ver = _full_verification(nid)
        bucket, diagnostic_class = priority_bucket_for_record(source_record)
        status = escape_md(source_record.get("status", node.get("status", "")))
        rows = [
            f"| `{nid}` | {title} "
            f"| {bucket} / {diagnostic_class} "
            f"| {status} "
            f"| {escape_md(node.get('risk_level', ''))} "
            f"| {escape_md(node.get('proof_level', ''))} "
            f"| {ver} "
            f"| {owner} |"
        ]
        for nc in node_ncs(nid):
            rows.append(f"|  | {escape_md(nc)} | — | — | — | — | — | — |")
        return rows

    # ── Summary table ───────────────────────────────────────────────────────────
    lines: list[str] = [
        "# Product Readiness Blockers Report",
        "",
        "> **Scope:** This report maps active proof gates, blocked evidence, and non-claims "
        "to the six capability areas required for LegalGraph Nexus product readiness. "
        "It is a derived, non-authoritative planning artifact only — it does **not** assert product readiness and "
        "does not validate runtime behavior, retrieval quality, parser completeness, "
        "generated-Cypher safety, FalkorDB production scale, or legal-answer correctness.",
        "",
        "---",
        "",
        "## Summary Table",
        "",
        "| Capability Area | Gate Count | Blocked / Bounded Count |",
        "| --- | ---: | ---: |",
    ]
    for area in CAPABILITY_AREAS:
        lines.append(
            f"| {area} | {len(gates_by_area[area])} | {len(blocked_by_area[area])} |"
        )

    all_blockers = [*unresolved_gates, *blocked_nodes]
    if all_blockers:
        lines.extend([
            "",
            "## Priority Snapshot",
            "",
            "This snapshot is a triage view only; priority does not prove readiness or promote claims.",
            "",
            "| Priority | Count | Representative Blockers |",
            "| --- | ---: | --- |",
        ])
        by_bucket: dict[str, list[str]] = {"P0": [], "P1": [], "P2": [], "P3": []}
        for blocker in all_blockers:
            record_id = str(blocker.get("id", ""))
            source_record = items_lookup.get(record_id, blocker)
            bucket, _ = priority_bucket_for_record(source_record)
            by_bucket[bucket].append(record_id)
        for bucket in ("P0", "P1", "P2", "P3"):
            ids = sorted(by_bucket[bucket])
            representatives = ", ".join(f"`{escape_md(record_id)}`" for record_id in ids[:5]) if ids else "—"
            lines.append(f"| {bucket} | {len(ids)} | {representatives} |")

    # ── Per-area sections ───────────────────────────────────────────────────────
    for area in CAPABILITY_AREAS:
        gate_list = gates_by_area[area]
        blocked_list = blocked_by_area[area]

        lines.extend(["", f"## {area}", ""])

        if gate_list or blocked_list:
            lines.extend([
                "### Proof Gates",
                "",
                "| ID | Title | Priority | Status | Risk | Verification | Owner |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ])
            for gate in gate_list:
                lines.extend(render_gate_rows(gate))

            if blocked_list:
                lines.extend([
                    "",
                    "### Blocked / Bounded Evidence",
                    "",
                    "| ID | Title | Priority | Status | Risk | Proof Level | Verification | Owner |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- |",
                ])
                for node in blocked_list:
                    lines.extend(render_node_rows(node))

            # What this area does NOT prove
            seen_nc: set[str] = set()
            lines.extend([
                "",
                "### What This Area Does Not Prove",
                "",
                "_Below non-claims are drawn directly from architecture registry records. "
                "They are not exhaustive._",
                "",
                "| Non-Claim |",
                "| --- |",
            ])
            for nid in [g["id"] for g in gate_list] + [n["id"] for n in blocked_list]:
                for nc in _nc_by_id.get(nid, []):
                    if nc not in seen_nc:
                        seen_nc.add(nc)
                        lines.append(f"| {escape_md(nc)} |")

            lines.extend([
                "",
                "### Next Proof Work",
                "",
                "Proof work for this area should:",
                "",
            ])
            for gate in gate_list:
                lines.append(
                    f"- Address [`{gate.get('id', '')}`](#proof-gates): "
                    f"{gate.get('verification') or _full_verification(gate.get('id', ''))}"
                )
            for node in blocked_list:
                nid = node.get("id", "")
                lines.append(
                    f"- Resolve [`{nid}`](#blocked--bounded-evidence): "
                    f"{_full_verification(nid)}"
                )
        else:
            lines.extend([
                "No active proof gates or blocked evidence for this area in the current architecture registry.",
                "",
            ])

    # ── Global non-claims summary ───────────────────────────────────────────────
    lines.extend([
        "",
        "---",
        "",
        "## Global Non-Claims Summary",
        "",
        "_The following statements appear across one or more architecture records and "
        "collectively define what this architecture does NOT validate:_",
        "",
        "| Non-Claim | Appears In |",
        "| --- | --- |",
    ])

    seen_nc_global: set[str] = set()
    for entry in non_claims_summary.get("by_node", []):
        nid = entry.get("id", "")
        for nc in entry.get("non_claims", []):
            if nc not in seen_nc_global:
                seen_nc_global.add(nc)
                lines.append(f"| {escape_md(nc)} | `{nid}` |")

    lines.extend([
        "",
        "---",
        "",
        "*Blockers report generated from `prd/architecture/architecture_graph_report.json`. "
        "This is a derived, non-authoritative planning artifact — it makes next proof work visible without asserting "
        "product readiness. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*",
    ])

    return "\n".join(lines) + "\n"


# ── Claims ledger ───────────────────────────────────────────────────────────────

ClaimClassification = str  # Literal["safe-to-say", "bounded", "blocked/open", "unsafe-to-assert", "non-claim"]


def _classify_record(record: dict[str, Any]) -> ClaimClassification:
    """Classify a single architecture item into a claims safety class.

    Classification rules (applied in order):
    1. blocked  → blocked/open
    2. proof_level == "none" and status == "active" → blocked/open
    3. out-of-scope  → unsafe-to-assert  (guardrail items are themselves safe to assert as non-claims,
       but the items they reference are unsafe-to-assert)
    4. status == "bounded-evidence" → bounded
    5. proof_level in ("source-anchor", "static-check") and status == "active" → safe-to-say
    6. proof_level in ("runtime-smoke", "real-document-proof") and status == "active" → bounded
    7. otherwise → unsafe-to-assert
    """
    status = record.get("status", "")
    proof_level = record.get("proof_level", "")
    non_claims: list[str] = record.get("non_claims", [])

    if status == "blocked":
        return "blocked/open"
    if proof_level == "none" and status == "active":
        return "blocked/open"
    if status == "out-of-scope":
        # Guardrail items: the item itself says "no X" — treat as non-claim framing
        return "unsafe-to-assert"
    if status == "bounded-evidence":
        return "bounded"
    if proof_level in ("source-anchor", "static-check") and status == "active":
        return "safe-to-say"
    if proof_level in ("runtime-smoke", "real-document-proof") and status == "active":
        return "bounded"
    return "unsafe-to-assert"


def _claim_domain(record: dict[str, Any]) -> str:
    """Return the claim domain that future readers must not over-broaden."""
    layer = str(record.get("layer", ""))
    record_type = str(record.get("type", ""))
    if layer in {"architecture-governance", "workflow-governance"}:
        return "registry/process"
    if layer in {"legal-evidence", "temporal-model", "api-product", "generated-cypher"}:
        return "product/legal-runtime"
    if layer in {"parser-ingestion", "retrieval-embedding", "graph-runtime"}:
        return "bounded-technical-proof"
    if record_type == "proof_gate":
        return "open-proof-gate"
    return "architecture-planning"


def render_claims_ledger(
    items_lookup: dict[str, dict[str, Any]],
    report: dict[str, Any],
) -> str:
    """Render a concise claims ledger classifying every architecture item.

    Classifications:
    - safe-to-say      : source-anchor / static-check proof, active status
    - bounded          : bounded-evidence status OR runtime-smoke / real-document-proof
    - blocked/open     : proof_level==none + active OR explicit blocked status
    - unsafe-to-assert : out-of-scope guardrails and items without sufficient proof

    The ledger makes overclaim risk visible for architecture reviews and planning.
    """
    # Build sorted list of (id, record, classification)
    rows: list[tuple[str, dict[str, Any], ClaimClassification]] = []
    for record_id, record in sorted(items_lookup.items()):
        classification = _classify_record(record)
        rows.append((record_id, record, classification))

    # Group by classification
    safe_items = [(rid, r) for rid, r, c in rows if c == "safe-to-say"]
    bounded_items = [(rid, r) for rid, r, c in rows if c == "bounded"]
    blocked_items = [(rid, r) for rid, r, c in rows if c == "blocked/open"]
    unsafe_items = [(rid, r) for rid, r, c in rows if c == "unsafe-to-assert"]

    lines: list[str] = [
        "# Claims Ledger",
        "",
        "> **Scope:** This ledger classifies each architecture registry item by the safety "
        "of asserting its claims in future planning, PRDs, or agent handoffs. "
        "It is a derived, non-authoritative planning artifact — do not use it as proof. "
        "Always cite source anchors, runtime artifacts, and real-document evidence.",
        "",
        "## Classification Guide",
        "",
        "| Class | Meaning | When to use |",
        "| --- | --- | --- |",
        "| **safe-to-say** | Source-anchor or static-check proof; active status. | Use freely with source anchor citation. |",
        "| **bounded** | Bounded-evidence, runtime-smoke, or real-document-proof; product-scale unproven. | Cite scope; do not extrapolate. |",
        "| **blocked/open** | Unresolved proof gate (proof_level=none) or blocked status. | Do not assert; resolve proof gate first. |",
        "| **unsafe-to-assert** | Out-of-scope guardrail, or item without sufficient proof. | Do not assert without independent evidence. |",
        "",
    ]

    ontology_rows = r035_gate_rows(items_lookup)
    lines.extend([
        "## R035 Gate Status",
        "",
        "Ontology, external-standard, GraphRAG, graph-vector, and pilot-scale rows are guardrails only. They do not validate the referenced standard or product behavior.",
        "",
    ])
    if ontology_rows:
        lines.extend([
            "| ID | Trigger | Current Safe Bucket | Required Gate | Minimum Proof | Status | Missing Requirements | Remediation Class |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for row in ontology_rows:
            lines.append(
                f"| `{escape_md(row['id'])}` | {escape_md(row['trigger'])} "
                f"| {escape_md(row['safe_bucket'])} "
                f"| {escape_md(row['required_gate'])} "
                f"| {escape_md(row['minimum_proof_level'])} "
                f"| {escape_md(row['current_status'])} "
                f"| {escape_md(row['missing'])} "
                f"| {escape_md(row['remediation_class'])} |"
            )
    else:
        lines.append("No R035-triggered ontology or external-standard rows in the generated registry view.")

    lines.extend([
        "",
        "---",
        "",
        "## safe-to-say",
        "",
    ])

    if safe_items:
        lines.extend([
            "| ID | Title | Layer | Claim Domain | Risk | Non-Claims |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for rid, record in safe_items:
            ncs = record.get("non_claims", [])
            nc_cell = "; ".join(f"❌ {escape_md(nc)}" for nc in ncs[:2]) if ncs else "—"
            lines.append(
                f"| `{rid}` | {escape_md(record.get('title', ''))} "
                f"| {escape_md(record.get('layer', ''))} "
                f"| {escape_md(_claim_domain(record))} "
                f"| {escape_md(record.get('risk_level', ''))} "
                f"| {nc_cell} |"
            )
    else:
        lines.append("No items classified as safe-to-say.")

    lines.extend(["", "---", "", "## bounded", ""])

    if bounded_items:
        lines.extend([
            "| ID | Title | Layer | Claim Domain | Risk | Proof Level | Non-Claims |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])
        for rid, record in bounded_items:
            ncs = record.get("non_claims", [])
            nc_cell = "; ".join(f"❌ {escape_md(nc)}" for nc in ncs) if ncs else "—"
            lines.append(
                f"| `{rid}` | {escape_md(record.get('title', ''))} "
                f"| {escape_md(record.get('layer', ''))} "
                f"| {escape_md(_claim_domain(record))} "
                f"| {escape_md(record.get('risk_level', ''))} "
                f"| {escape_md(record.get('proof_level', ''))} "
                f"| {nc_cell} |"
            )
    else:
        lines.append("No items classified as bounded.")

    lines.extend(["", "---", "", "## blocked/open", ""])

    if blocked_items:
        lines.extend([
            "| ID | Title | Layer | Claim Domain | Risk | Status | Proof Level | Verification | Non-Claims |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for rid, record in blocked_items:
            ncs = record.get("non_claims", [])
            nc_cell = "; ".join(f"❌ {escape_md(nc)}" for nc in ncs[:2]) if ncs else "—"
            ver = escape_md(record.get("verification", "") or "")
            lines.append(
                f"| `{rid}` | {escape_md(record.get('title', ''))} "
                f"| {escape_md(record.get('layer', ''))} "
                f"| {escape_md(_claim_domain(record))} "
                f"| {escape_md(record.get('risk_level', ''))} "
                f"| {escape_md(record.get('status', ''))} "
                f"| {escape_md(record.get('proof_level', ''))} "
                f"| {ver[:60]}... "
                f"| {nc_cell} |"
                if len(ver) > 60
                else f"| `{rid}` | {escape_md(record.get('title', ''))} "
                     f"| {escape_md(record.get('layer', ''))} "
                     f"| {escape_md(_claim_domain(record))} "
                     f"| {escape_md(record.get('risk_level', ''))} "
                     f"| {escape_md(record.get('status', ''))} "
                     f"| {escape_md(record.get('proof_level', ''))} "
                     f"| {ver} |"
                     f"| {nc_cell} |"
            )
    else:
        lines.append("No items classified as blocked/open.")

    lines.extend(["", "---", "", "## unsafe-to-assert", ""])

    if unsafe_items:
        lines.extend([
            "| ID | Title | Layer | Claim Domain | Risk | Status | Non-Claims |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])
        for rid, record in unsafe_items:
            ncs = record.get("non_claims", [])
            nc_cell = "; ".join(f"❌ {escape_md(nc)}" for nc in ncs[:2]) if ncs else "—"
            lines.append(
                f"| `{rid}` | {escape_md(record.get('title', ''))} "
                f"| {escape_md(record.get('layer', ''))} "
                f"| {escape_md(_claim_domain(record))} "
                f"| {escape_md(record.get('risk_level', ''))} "
                f"| {escape_md(record.get('status', ''))} "
                f"| {nc_cell} |"
            )
    else:
        lines.append("No items classified as unsafe-to-assert.")

    # Non-authoritative footer
    lines.extend([
        "",
        "---",
        "",
        "*Claims ledger generated from `prd/architecture/architecture_items.jsonl` and "
        "`prd/architecture/architecture_graph_report.json`. This is a derived, "
        "non-authoritative planning artifact. Source-of-truth remains with PRD, GSD, ADR, "
        "and source anchor evidence.*",
    ])

    return "\n".join(lines) + "\n"


def check_claims_ledger_output(path: Path, expected: str) -> bool:
    """Return True if the claims ledger is up to date."""
    if not path.exists():
        print(
            f"missing claims ledger: {path}; regenerate with `uv run python scripts/generate-architecture-views.py`",
            file=sys.stderr,
        )
        return False
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        print(
            f"stale claims ledger: {path}; regenerate with `uv run python scripts/generate-architecture-views.py` and review the diff",
            file=sys.stderr,
        )
        return False
    return True


def write_claims_ledger(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def check_health_output(path: Path, expected: str) -> bool:
    """Return True if the health dashboard is up to date."""
    if not path.exists():
        print(
            f"missing health dashboard: {path}; regenerate with `uv run python scripts/generate-architecture-views.py`",
            file=sys.stderr,
        )
        return False
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        print(
            f"stale health dashboard: {path}; regenerate with `uv run python scripts/generate-architecture-views.py` and review the diff",
            file=sys.stderr,
        )
        return False
    return True


def write_health(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def check_blockers_output(path: Path, expected: str) -> bool:
    """Return True if the blockers report is up to date."""
    if not path.exists():
        print(
            f"missing blockers report: {path}; regenerate with `uv run python scripts/generate-architecture-views.py`",
            file=sys.stderr,
        )
        return False
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        print(
            f"stale blockers report: {path}; regenerate with `uv run python scripts/generate-architecture-views.py` and review the diff",
            file=sys.stderr,
        )
        return False
    return True


def write_blockers(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate derived, non-authoritative architecture health dashboard, blockers report, and claims ledger from graph report."
    )
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--items-jsonl", type=Path, default=DEFAULT_ITEMS_JSONL_PATH)
    parser.add_argument("--health-md", type=Path, default=DEFAULT_HEALTH_MD_PATH)
    parser.add_argument("--blockers-md", type=Path, default=DEFAULT_BLOCKERS_MD_PATH)
    parser.add_argument("--claims-ledger-md", type=Path, default=DEFAULT_CLAIMS_MD_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare expected outputs to existing files without rewriting.",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report_json = args.report_json.read_text(encoding="utf-8")
        report = json.loads(report_json)
    except FileNotFoundError as exc:
        print(
            f"missing input: {exc}; run `uv run python scripts/build-architecture-graph.py` first",
            file=sys.stderr,
        )
        return 1
    except json.JSONDecodeError as exc:
        print(f"invalid JSON in {args.report_json}: {exc}", file=sys.stderr)
        return 1

    items_lookup = _load_items_lookup(args.items_jsonl)
    expected_health = render_health_dashboard(report, items_lookup=items_lookup)
    expected_blockers = render_blockers_report(report, items_lookup=items_lookup)
    expected_claims = render_claims_ledger(items_lookup, report)

    if args.check:
        if not check_health_output(args.health_md, expected_health):
            return 1
        if not check_blockers_output(args.blockers_md, expected_blockers):
            return 1
        if not check_claims_ledger_output(args.claims_ledger_md, expected_claims):
            return 1
    else:
        write_health(args.health_md, expected_health)
        write_blockers(args.blockers_md, expected_blockers)
        write_claims_ledger(args.claims_ledger_md, expected_claims)

    summary = {
        "status": "ok",
        "mode": "check" if args.check else "write",
        "health_md": str(args.health_md),
        "blockers_md": str(args.blockers_md),
        "claims_ledger_md": str(args.claims_ledger_md),
        "non_authoritative": True,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
