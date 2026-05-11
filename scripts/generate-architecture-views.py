#!/usr/bin/env python3
"""Generate derived, non-authoritative architecture health dashboard and views.

Reads the derived S03/S04 graph report (architecture_graph_report.json) and
produces compact human-readable views for health status, layer coverage, risk,
non-authoritative boundary documentation, and a claims safety ledger.
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


def render_health_dashboard(report: dict[str, Any]) -> str:
    """Render a compact health status dashboard from the graph report."""
    counts = report.get("counts", {})
    layer_coverage = report.get("layer_coverage", {})
    missing_layers = layer_coverage.get("missing_layers", [])
    invalid_layers = layer_coverage.get("invalid_layers", [])
    unresolved_gates = report.get("unresolved_proof_gates", [])
    orphan_findings = report.get("orphan_findings", [])
    high_risk_nodes = report.get("high_risk_nodes", [])
    contradiction_edges = report.get("contradiction_edges", [])
    non_claims_summary = report.get("non_claims_summary", {})

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
        "",
        "---",
        "",
        "## Layer Coverage",
        "",
    ]

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
    CAPABILITY_AREAS = sorted(LAYER_MAP.values())  # deterministic order

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
        return _nc_by_id.get(gate_id, [])

    def node_ncs(node_id: str) -> list[str]:
        return _nc_by_id.get(node_id, [])

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
        rows = [
            f"| `{nid}` | {title} "
            f"| {escape_md(gate.get('risk_level', ''))} "
            f"| {ver} "
            f"| {owner} |"
        ]
        for nc in gate_ncs(nid):
            rows.append(f"|  | {escape_md(nc)} | — | — | — |")
        return rows

    def render_node_rows(node: dict[str, Any]) -> list[str]:
        nid = node.get("id", "")
        # Enrich from items_lookup for title/owner/verification
        title = _full_title(nid)
        owner = _full_owner(nid)
        ver = _full_verification(nid)
        rows = [
            f"| `{nid}` | {title} "
            f"| {escape_md(node.get('risk_level', ''))} "
            f"| {ver} "
            f"| {owner} |"
        ]
        for nc in node_ncs(nid):
            rows.append(f"|  | {escape_md(nc)} | — | — | — |")
        return rows

    # ── Summary table ───────────────────────────────────────────────────────────
    lines: list[str] = [
        "# Product Readiness Blockers Report",
        "",
        "> **Scope:** This report maps active proof gates, blocked evidence, and non-claims "
        "to the six capability areas required for LegalGraph Nexus product readiness. "
        "It is a planning artifact only — it does **not** assert product readiness and "
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

    # ── Per-area sections ───────────────────────────────────────────────────────
    for area in CAPABILITY_AREAS:
        gate_list = gates_by_area[area]
        blocked_list = blocked_by_area[area]

        lines.extend(["", f"## {area}", ""])

        if gate_list or blocked_list:
            lines.extend([
                "### Proof Gates",
                "",
                "| ID | Title | Risk | Verification | Owner |",
                "| --- | --- | --- | --- | --- |",
            ])
            for gate in gate_list:
                lines.extend(render_gate_rows(gate))

            if blocked_list:
                lines.extend([
                    "",
                    "### Blocked / Bounded Evidence",
                    "",
                    "| ID | Title | Risk | Verification | Owner |",
                    "| --- | --- | --- | --- | --- |",
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
        "This is a planning artifact — it makes next proof work visible without asserting "
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
        "---",
        "",
        "## safe-to-say",
        "",
    ]

    if safe_items:
        lines.extend([
            "| ID | Title | Layer | Risk | Non-Claims |",
            "| --- | --- | --- | --- | --- |",
        ])
        for rid, record in safe_items:
            ncs = record.get("non_claims", [])
            nc_cell = "; ".join(f"❌ {escape_md(nc)}" for nc in ncs[:2]) if ncs else "—"
            lines.append(
                f"| `{rid}` | {escape_md(record.get('title', ''))} "
                f"| {escape_md(record.get('layer', ''))} "
                f"| {escape_md(record.get('risk_level', ''))} "
                f"| {nc_cell} |"
            )
    else:
        lines.append("No items classified as safe-to-say.")

    lines.extend(["", "---", "", "## bounded", ""])

    if bounded_items:
        lines.extend([
            "| ID | Title | Layer | Risk | Proof Level | Non-Claims |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for rid, record in bounded_items:
            ncs = record.get("non_claims", [])
            nc_cell = "; ".join(f"❌ {escape_md(nc)}" for nc in ncs[:2]) if ncs else "—"
            lines.append(
                f"| `{rid}` | {escape_md(record.get('title', ''))} "
                f"| {escape_md(record.get('layer', ''))} "
                f"| {escape_md(record.get('risk_level', ''))} "
                f"| {escape_md(record.get('proof_level', ''))} "
                f"| {nc_cell} |"
            )
    else:
        lines.append("No items classified as bounded.")

    lines.extend(["", "---", "", "## blocked/open", ""])

    if blocked_items:
        lines.extend([
            "| ID | Title | Layer | Risk | Proof Level | Verification | Non-Claims |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])
        for rid, record in blocked_items:
            ncs = record.get("non_claims", [])
            nc_cell = "; ".join(f"❌ {escape_md(nc)}" for nc in ncs[:2]) if ncs else "—"
            ver = escape_md(record.get("verification", "") or "")
            lines.append(
                f"| `{rid}` | {escape_md(record.get('title', ''))} "
                f"| {escape_md(record.get('layer', ''))} "
                f"| {escape_md(record.get('risk_level', ''))} "
                f"| {escape_md(record.get('proof_level', ''))} "
                f"| {ver[:60]}... |"
                if len(ver) > 60
                else f"| `{rid}` | {escape_md(record.get('title', ''))} "
                     f"| {escape_md(record.get('layer', ''))} "
                     f"| {escape_md(record.get('risk_level', ''))} "
                     f"| {escape_md(record.get('proof_level', ''))} "
                     f"| {ver} |"
                     f"| {nc_cell} |"
            )
    else:
        lines.append("No items classified as blocked/open.")

    lines.extend(["", "---", "", "## unsafe-to-assert", ""])

    if unsafe_items:
        lines.extend([
            "| ID | Title | Layer | Risk | Status | Non-Claims |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for rid, record in unsafe_items:
            ncs = record.get("non_claims", [])
            nc_cell = "; ".join(f"❌ {escape_md(nc)}" for nc in ncs[:2]) if ncs else "—"
            lines.append(
                f"| `{rid}` | {escape_md(record.get('title', ''))} "
                f"| {escape_md(record.get('layer', ''))} "
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

    expected_health = render_health_dashboard(report)
    items_lookup = _load_items_lookup(args.items_jsonl)
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
