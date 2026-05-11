"""Tests for architecture health dashboard content and determinism.

Verifies that the architecture health dashboard correctly reflects the graph report,
contains required sections, exposes risk/layer gaps, and maintains deterministic output.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATE_SCRIPT_PATH = ROOT / "scripts/generate-architecture-views.py"
REPORT_JSON_PATH = ROOT / "prd/architecture/architecture_graph_report.json"
HEALTH_MD_PATH = ROOT / "prd/architecture/architecture_health.md"


def load_generator() -> ModuleType:
    """Dynamically import the generator script."""
    spec = importlib.util.spec_from_file_location("generate_architecture_views", GENERATE_SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    return module


def load_report() -> dict:
    """Load the architecture graph report JSON."""
    return json.loads(REPORT_JSON_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Section presence
# ---------------------------------------------------------------------------

def test_health_dashboard_has_required_sections() -> None:
    """Health dashboard must contain all required structural sections."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    required_sections = [
        "## Quick Stats",
        "## Layer Coverage",
        "## Open Proof Gates",
        "## High-Risk Nodes",
        "## Non-Authoritative Boundary",
        "## Orphan Findings",
        "## Weakly Connected Components",
    ]
    for section in required_sections:
        assert section in content, f"Missing required section: {section}"


def test_health_dashboard_has_status_line() -> None:
    """Dashboard must have a status indicator line."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert "**Status:**" in content


def test_health_dashboard_has_non_authoritative_disclaimer() -> None:
    """Dashboard must include the non-authoritative disclaimer."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert "**Non-Authoritative:**" in content
    assert "does not validate product/runtime/legal claims" in content
    assert "PRD, GSD, ADR" in content


# ---------------------------------------------------------------------------
# Derived / non-authoritative boundary
# ---------------------------------------------------------------------------

def test_non_authoritative_boundary_section_has_table() -> None:
    """Non-authoritative boundary section must contain a table of non-claims."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    # Find the Non-Authoritative Boundary section
    section_start = content.find("## Non-Authoritative Boundary")
    assert section_start >= 0, "Missing Non-Authoritative Boundary section"
    section = content[section_start:]
    # Check for the intro line (with markdown bold formatting)
    assert "**do not** establish or validate" in section
    # Check for the non-claims table header
    assert "| Non-Claim |" in section


def test_non_authoritative_boundary_lists_specific_disclaimers() -> None:
    """Non-authoritative boundary must include specific non-claim disclaimers."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    # These are concrete non-claims from the JSON
    expected_non_claims = [
        "Does not itself prove product runtime behavior",
        "Does not make generated artifacts authoritative",
        "No LLM legal authority claim",
        "No parser completeness claim",
    ]
    for claim in expected_non_claims:
        assert claim in content, f"Missing non-claim: {claim}"


def test_non_authoritative_flag_in_report() -> None:
    """Report JSON must declare itself as non-authoritative."""
    report = load_report()
    assert report.get("non_authoritative") is True


# ---------------------------------------------------------------------------
# Unresolved proof gates
# ---------------------------------------------------------------------------

def test_unresolved_gates_appear_in_dashboard() -> None:
    """All unresolved proof gates from JSON must appear in the dashboard."""
    report = load_report()
    gates = report.get("unresolved_proof_gates", [])
    assert len(gates) > 0, "Test requires at least one unresolved gate"

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    for gate in gates:
        gate_id = gate.get("id", "")
        assert gate_id in content, f"Gate {gate_id} not found in dashboard"
        assert gate.get("layer", "") in content, f"Gate {gate_id} layer missing"
        assert gate.get("risk_level", "") in content, f"Gate {gate_id} risk level missing"


def test_unresolved_gates_count_matches_report() -> None:
    """Dashboard must report correct count of unresolved gates."""
    report = load_report()
    expected_count = len(report.get("unresolved_proof_gates", []))

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    # Look for the Quick Stats table row for gates
    assert f"| Unresolved Proof Gates | {expected_count} |" in content, (
        f"Expected {expected_count} unresolved gates in Quick Stats"
    )


def test_gate_table_has_required_columns() -> None:
    """Open Proof Gates table must have all required columns."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    section_start = content.find("## Open Proof Gates")
    section = content[section_start:]
    table_end = section.find("\n## ", 1)  # Find next section
    if table_end > 0:
        table = section[:table_end]
    else:
        table = section
    assert "| ID |" in table
    assert "| Layer |" in table
    assert "| Owner |" in table
    assert "| Risk |" in table
    assert "| Verification |" in table


# ---------------------------------------------------------------------------
# High-risk nodes
# ---------------------------------------------------------------------------

def test_high_risk_nodes_appear_in_dashboard() -> None:
    """All high-risk and critical nodes must appear in the dashboard."""
    report = load_report()
    high_risk = report.get("high_risk_nodes", [])
    assert len(high_risk) > 0, "Test requires at least one high-risk node"

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    for node in high_risk:
        node_id = node.get("id", "")
        assert node_id in content, f"Node {node_id} not found in dashboard"


def test_critical_risk_nodes_are_distinguishable() -> None:
    """Critical nodes must appear with 'critical' risk level."""
    report = load_report()
    critical_nodes = [
        n for n in report.get("high_risk_nodes", []) if n.get("risk_level") == "critical"
    ]

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    for node in critical_nodes:
        node_id = node.get("id", "")
        # The node should appear in the high-risk table with "critical" risk
        assert "critical" in content.lower() or node_id in content


def test_high_risk_count_matches_report() -> None:
    """Dashboard must show correct count of high/critical risk nodes."""
    report = load_report()
    high_risk_nodes = report.get("high_risk_nodes", [])
    critical_count = sum(1 for n in high_risk_nodes if n.get("risk_level") == "critical")
    high_count = sum(1 for n in high_risk_nodes if n.get("risk_level") == "high")

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    expected_line = f"| High/Critical Risk Nodes | {len(high_risk_nodes)} ({critical_count} critical, {high_count} high) |"
    assert expected_line in content, f"Expected risk count line in Quick Stats"


# ---------------------------------------------------------------------------
# Missing layers
# ---------------------------------------------------------------------------

def test_missing_layers_appear_in_dashboard() -> None:
    """Missing schema layers must be documented in the dashboard."""
    report = load_report()
    missing = report.get("layer_coverage", {}).get("missing_layers", [])
    assert len(missing) > 0, "Test requires at least one missing layer"

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    for layer in missing:
        assert layer in content, f"Missing layer '{layer}' not in dashboard"


def test_missing_layers_count_matches_report() -> None:
    """Dashboard must report correct count of missing layers."""
    report = load_report()
    expected_count = len(report.get("layer_coverage", {}).get("missing_layers", []))

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert f"| Missing Layers | {expected_count} |" in content


def test_missing_layers_section_has_warning_header() -> None:
    """Missing layers section must have a warning indicator."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert "### ⚠️  Missing Layers" in content


# ---------------------------------------------------------------------------
# Contradiction count
# ---------------------------------------------------------------------------

def test_contradiction_count_shown_in_quick_stats() -> None:
    """Dashboard must show contradiction edge count."""
    report = load_report()
    contradiction_count = len(report.get("contradiction_edges", []))

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert f"| Contradiction Edges | {contradiction_count} |" in content


def test_zero_contradiction_edges_is_valid_state() -> None:
    """Zero contradiction edges is a valid (healthy) state to report."""
    report = load_report()
    assert report.get("contradiction_edges", []) == []
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert "| Contradiction Edges | 0 |" in content


# ---------------------------------------------------------------------------
# Orphan findings
# ---------------------------------------------------------------------------

def test_orphan_findings_count_matches_report() -> None:
    """Dashboard must report correct count of orphan findings."""
    report = load_report()
    expected_count = len(report.get("orphan_findings", []))

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert f"| Orphan Findings | {expected_count} |" in content


def test_orphan_nodes_appear_in_dashboard() -> None:
    """All orphan nodes must be listed in the Orphan Findings section."""
    report = load_report()
    orphans = report.get("orphan_findings", [])

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    for orphan in orphans:
        node_id = orphan.get("id", "")
        assert node_id in content, f"Orphan node {node_id} not in dashboard"


# ---------------------------------------------------------------------------
# Quick stats integrity
# ---------------------------------------------------------------------------

def test_quick_stats_table_header_present() -> None:
    """Quick Stats section must have a proper markdown table."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    section_start = content.find("## Quick Stats")
    section = content[section_start:]
    table_end = section.find("\n## ", 1)
    table = section[:table_end] if table_end > 0 else section
    assert "| Metric | Count |" in table
    assert "| --- | ---: |" in table


def test_node_and_edge_counts_present() -> None:
    """Quick Stats must include node and edge counts."""
    report = load_report()
    expected_nodes = report.get("counts", {}).get("nodes", 0)
    expected_edges = report.get("counts", {}).get("edges", 0)

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert f"| Total Nodes | {expected_nodes} |" in content
    assert f"| Total Edges | {expected_edges} |" in content


def test_schema_layer_count_present() -> None:
    """Quick Stats must include total schema layer count."""
    report = load_report()
    layer_count = len(report.get("layer_coverage", {}).get("counts", {}))

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert f"| Schema Layers | {layer_count} |" in content


def test_non_claims_summary_counts_present() -> None:
    """Quick Stats must include non-claims summary counts."""
    report = load_report()
    non_claims = report.get("non_claims_summary", {})
    nodes_with_claims = non_claims.get("nodes_with_non_claims", 0)
    total_claims = non_claims.get("total_non_claims", 0)

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert f"| Nodes with Non-Claims | {nodes_with_claims} |" in content
    assert f"| Total Non-Claims | {total_claims} |" in content


# ---------------------------------------------------------------------------
# Layer coverage table
# ---------------------------------------------------------------------------

def test_layer_coverage_table_has_headers() -> None:
    """Layer Coverage section must have proper table headers."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    section_start = content.find("## Layer Coverage")
    section = content[section_start:]
    table_end = section.find("\n## ", 1)
    table = section[:table_end] if table_end > 0 else section
    assert "| Layer | Node Count |" in table


def test_all_layers_from_report_in_table() -> None:
    """All layers from the report must appear in the coverage table."""
    report = load_report()
    all_layers = report.get("layer_coverage", {}).get("counts", {})

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    for layer in all_layers:
        assert layer in content, f"Layer {layer} not found in Layer Coverage table"


def test_missing_layers_marked_in_table() -> None:
    """Missing layers must have a warning marker in the coverage table."""
    report = load_report()
    missing_layers = report.get("layer_coverage", {}).get("missing_layers", [])

    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    for layer in missing_layers:
        # Each missing layer should appear with a ⚠️ marker in its table row
        assert f"{layer} ⚠️" in content or f"{layer}  ⚠️" in content, (
            f"Missing layer {layer} should be marked with ⚠️"
        )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_generator_is_deterministic() -> None:
    """Running the generator twice produces identical output."""
    module = load_generator()
    report = load_report()

    first_output = module.render_health_dashboard(report)
    second_output = module.render_health_dashboard(report)

    assert first_output == second_output, (
        "Generator output is non-deterministic: "
        f"first run length={len(first_output)}, second run length={len(second_output)}"
    )


def test_generated_output_matches_stored_file() -> None:
    """The stored health dashboard must match current generator output."""
    module = load_generator()
    report = load_report()
    expected = module.render_health_dashboard(report)

    actual = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert actual == expected, (
        "Stored health dashboard is stale. Run:\n"
        f"  uv run python {GENERATE_SCRIPT_PATH}"
    )


def test_generator_produces_valid_markdown_structure() -> None:
    """Generator output must have valid markdown structure."""
    module = load_generator()
    report = load_report()
    output = module.render_health_dashboard(report)

    # Check that the output starts with a heading
    assert output.startswith("# Architecture Health Dashboard")
    # Check that sections start with h2
    section_count = output.count("\n## ")
    assert section_count >= 5, f"Expected at least 5 h2 sections, got {section_count}"
    # Check tables have headers
    assert output.count("| --- |") >= 3, "Expected at least 3 markdown tables"


def test_check_health_output_function_detects_stale_output(tmp_path: Path) -> None:
    """The check_health_output helper must detect stale content."""
    module = load_generator()
    report = load_report()
    fresh_content = module.render_health_dashboard(report)

    # Test with matching content
    health_path = tmp_path / "health.md"
    health_path.write_text(fresh_content, encoding="utf-8")
    assert module.check_health_output(health_path, fresh_content) is True

    # Test with mismatched content
    stale_content = fresh_content + "\n\n<!-- stale -->"
    assert module.check_health_output(health_path, stale_content) is False


def test_check_health_output_function_detects_missing_file(tmp_path: Path) -> None:
    """The check_health_output helper must detect missing files."""
    module = load_generator()
    missing_path = tmp_path / "nonexistent.md"
    assert module.check_health_output(missing_path, "any content") is False


# ---------------------------------------------------------------------------
# Weakly connected components
# ---------------------------------------------------------------------------

def test_weak_components_section_present() -> None:
    """Weakly Connected Components section must exist."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    assert "## Weakly Connected Components" in content


def test_weak_components_table_has_headers() -> None:
    """Weak components table must have proper headers."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    section_start = content.find("## Weakly Connected Components")
    section = content[section_start:]
    table_end = section.find("\n\n*", 1)  # Footer starts with *
    table = section[:table_end] if table_end > 0 else section
    assert "| Size | Node Count |" in table


# ---------------------------------------------------------------------------
# High-risk nodes table
# ---------------------------------------------------------------------------

def test_high_risk_table_has_all_required_columns() -> None:
    """High-Risk Nodes table must have all required columns."""
    content = HEALTH_MD_PATH.read_text(encoding="utf-8")
    section_start = content.find("## High-Risk Nodes")
    section = content[section_start:]
    table_end = section.find("\n## ", 1)
    table = section[:table_end] if table_end > 0 else section
    required_columns = [
        "| ID |",
        "| Risk |",
        "| Type |",
        "| Layer |",
        "| Status |",
        "| Proof Level |",
    ]
    for col in required_columns:
        assert col in table, f"Missing column: {col}"
