#!/usr/bin/env python3
"""Generate derived, non-authoritative architecture health dashboard and views.

Reads the derived S03/S04 graph report (architecture_graph_report.json) and
produces compact human-readable views for health status, layer coverage, risk,
and non-authoritative boundary documentation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_JSON_PATH = ROOT / "prd/architecture/architecture_graph_report.json"
DEFAULT_HEALTH_MD_PATH = ROOT / "prd/architecture/architecture_health.md"


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate derived, non-authoritative architecture health dashboard from graph report."
    )
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--health-md", type=Path, default=DEFAULT_HEALTH_MD_PATH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare expected health dashboard to existing output without rewriting.",
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

    if args.check:
        if not check_health_output(args.health_md, expected_health):
            return 1
    else:
        write_health(args.health_md, expected_health)

    summary = {
        "status": "ok",
        "mode": "check" if args.check else "write",
        "health_md": str(args.health_md),
        "non_authoritative": True,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
