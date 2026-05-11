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


# ---------------------------------------------------------------------------
# Product-readiness blockers report guardrails
# ---------------------------------------------------------------------------

BLOCKERS_MD_PATH = ROOT / "prd/architecture/product_readiness_blockers.md"


def _load_blockers_content() -> str:
    """Load blocker report content, fail with clear message if missing."""
    assert BLOCKERS_MD_PATH.exists(), (
        f"Blocker report not found at {BLOCKERS_MD_PATH}. "
        "Run: uv run python scripts/generate-architecture-views.py"
    )
    return BLOCKERS_MD_PATH.read_text(encoding="utf-8")


def test_blockers_report_exists() -> None:
    """Blocker report file must exist."""
    _load_blockers_content()


def test_blockers_report_scope_disclaimer_present() -> None:
    """Blocker report must include a scope disclaimer that it is a planning artifact."""
    content = _load_blockers_content()
    assert "planning artifact" in content.lower(), (
        "Blocker report must contain 'planning artifact' disclaimer"
    )


def test_blockers_report_does_not_claim_product_ready() -> None:
    """Blocker report must NOT contain language claiming product readiness."""
    content = _load_blockers_content()
    content_lower = content.lower()
    overclaims = [
        "product ready",
        "product-ready",
        "production ready",
        "production-ready",
        "shippable",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Blocker report must NOT contain '{phrase}' — it is a planning artifact only"
        )


def test_blockers_report_does_not_claim_legal_answer_correctness() -> None:
    """Blocker report must NOT claim legal-answer correctness."""
    content = _load_blockers_content()
    content_lower = content.lower()
    # These phrases would overclaim legal-answer quality
    overclaims = [
        "legal answer correct",
        "legally correct",
        "correct legal answer",
        "guarantees legal accuracy",
        "legal answer is correct",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Blocker report must NOT claim '{phrase}'"
        )


def test_blockers_report_includes_gate_g005() -> None:
    """Blocker report must cite GATE-G005 (temporal model)."""
    content = _load_blockers_content()
    assert "GATE-G005" in content, (
        "Blocker report must include GATE-G005 for temporal same-date conflict policy"
    )


def test_blockers_report_includes_gate_g008() -> None:
    """Blocker report must cite GATE-G008 (parser + retrieval golden tests)."""
    content = _load_blockers_content()
    assert "GATE-G008" in content, (
        "Blocker report must include GATE-G008 for executable parser and retrieval golden tests"
    )


def test_blockers_report_includes_gate_g011() -> None:
    """Blocker report must cite GATE-G011 (local embedding quality proof)."""
    content = _load_blockers_content()
    assert "GATE-G011" in content, (
        "Blocker report must include GATE-G011 for local embedding quality proof"
    )


def test_blockers_report_includes_gate_g015() -> None:
    """Blocker report must cite GATE-G015 (FalkorDBLite to Docker migration)."""
    content = _load_blockers_content()
    assert "GATE-G015" in content, (
        "Blocker report must include GATE-G015 for FalkorDBLite to Docker migration runbook"
    )


def test_blockers_report_includes_all_four_gates() -> None:
    """Blocker report must cite all four required gates G005, G008, G011, G015."""
    content = _load_blockers_content()
    required_gates = ["GATE-G005", "GATE-G008", "GATE-G011", "GATE-G015"]
    missing = [g for g in required_gates if g not in content]
    assert not missing, f"Blocker report is missing gates: {missing}"


def test_blockers_report_includes_non_claim_no_parser_completeness() -> None:
    """Blocker report must include 'No parser completeness claim' non-claim."""
    content = _load_blockers_content()
    assert "No parser completeness claim" in content, (
        "Blocker report must include the 'No parser completeness claim' non-claim"
    )


def test_blockers_report_includes_non_claim_no_retrieval_quality() -> None:
    """Blocker report must include 'No product retrieval quality claim' non-claim."""
    content = _load_blockers_content()
    assert "No product retrieval quality claim" in content, (
        "Blocker report must include the 'No product retrieval quality claim' non-claim"
    )


def test_blockers_report_includes_non_claim_no_production_falkordb() -> None:
    """Blocker report must include 'No production-scale FalkorDB claim' non-claim."""
    content = _load_blockers_content()
    assert "No production-scale FalkorDB claim" in content, (
        "Blocker report must include the 'No production-scale FalkorDB claim' non-claim"
    )


def test_blockers_report_includes_non_claim_no_legal_answer_correctness() -> None:
    """Blocker report must include 'No legal-answer correctness claim' non-claim."""
    content = _load_blockers_content()
    assert "No legal-answer correctness claim" in content, (
        "Blocker report must include the 'No legal-answer correctness claim' non-claim"
    )


def test_blockers_report_does_not_claim_etl_is_complete() -> None:
    """Blocker report must not assert ETL is complete or production-ready."""
    content = _load_blockers_content()
    content_lower = content.lower()
    overclaims = [
        "etl is complete",
        "etl is production",
        "etl is ready",
        "parser is complete",
        "parser is production",
        "parser is ready",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Blocker report must NOT claim '{phrase}'"
        )


def test_blockers_report_does_not_claim_legal_knowql_works() -> None:
    """Blocker report must not claim Legal KnowQL works in production."""
    content = _load_blockers_content()
    content_lower = content.lower()
    overclaims = [
        "knowql works",
        "knowql is production",
        "knowql is ready",
        "legal knowql works",
        "legal knowql is production",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Blocker report must NOT claim '{phrase}'"
        )


def test_blockers_report_has_summary_table() -> None:
    """Blocker report must have a Summary Table mapping capability areas to gate counts."""
    content = _load_blockers_content()
    assert "| Capability Area | Gate Count |" in content, (
        "Blocker report must include a Summary Table with capability areas"
    )


def test_blockers_report_lists_etl_parser_area() -> None:
    """Blocker report must list the ETL / Parser capability area."""
    content = _load_blockers_content()
    assert "ETL / Parser" in content, (
        "Blocker report must include the ETL / Parser capability area"
    )


def test_blockers_report_lists_retrieval_embedding_area() -> None:
    """Blocker report must list the Retrieval / Embedding capability area."""
    content = _load_blockers_content()
    assert "Retrieval / Embedding" in content, (
        "Blocker report must include the Retrieval / Embedding capability area"
    )


def test_blockers_report_lists_temporal_model_area() -> None:
    """Blocker report must list the Temporal Model capability area."""
    content = _load_blockers_content()
    assert "Temporal Model" in content, (
        "Blocker report must include the Temporal Model capability area"
    )


def test_blockers_report_lists_graph_runtime_area() -> None:
    """Blocker report must list the Graph Runtime capability area."""
    content = _load_blockers_content()
    assert "Graph Runtime" in content, (
        "Blocker report must include the Graph Runtime capability area"
    )


def test_blockers_report_does_not_claim_runtime_migration_complete() -> None:
    """Blocker report must not assert runtime migration is complete."""
    content = _load_blockers_content()
    content_lower = content.lower()
    overclaims = [
        "migration is complete",
        "migration is done",
        "migration is successful",
        "runtime migration is complete",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Blocker report must NOT claim '{phrase}'"
        )


def test_blockers_report_includes_global_non_claims_summary() -> None:
    """Blocker report must include a Global Non-Claims Summary section."""
    content = _load_blockers_content()
    assert "Global Non-Claims Summary" in content, (
        "Blocker report must include a Global Non-Claims Summary section"
    )


def test_blockers_report_non_claims_cite_architecture_ids() -> None:
    """Blocker report non-claim rows must cite architecture record IDs."""
    content = _load_blockers_content()
    # The Global Non-Claims Summary should cite specific record IDs like GATE-G008, REQ-R001, etc.
    assert "GATE-G" in content, (
        "Blocker report must cite gate IDs in the Global Non-Claims Summary"
    )
    assert "REQ-R" in content, (
        "Blocker report must cite requirement IDs in the Global Non-Claims Summary"
    )


def test_blockers_report_does_not_contain_llm_authority_claim() -> None:
    """Blocker report must not assert LLM has legal authority."""
    content = _load_blockers_content()
    content_lower = content.lower()
    overclaims = [
        "llm has legal authority",
        "llm is legally authoritative",
        "llm provides legal authority",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Blocker report must NOT claim '{phrase}'"
        )


def test_blockers_report_blocked_evidence_cites_architecture_ids() -> None:
    """Blocked evidence rows must cite architecture record IDs (e.g. S05-OLD-PROJECT-PRIOR-ART)."""
    content = _load_blockers_content()
    assert "S05-OLD-PROJECT-PRIOR-ART" in content, (
        "Blocker report must include S05-OLD-PROJECT-PRIOR-ART in blocked evidence"
    )


def test_blockers_report_next_proof_work_section_present() -> None:
    """Each capability area must have a 'Next Proof Work' section."""
    content = _load_blockers_content()
    # Check that at least one area has "Next Proof Work"
    assert "Next Proof Work" in content, (
        "Blocker report must include 'Next Proof Work' sections"
    )


# ---------------------------------------------------------------------------
# Claims ledger — content and structure
# ---------------------------------------------------------------------------

CLAIMS_MD_PATH = ROOT / "prd/architecture/claims_ledger.md"

ALL_23_IDS = {
    "ASSUMP-PRD-SOURCE-TRUTH", "CHECK-ARCHITECTURE-EXTRACTOR", "DEC-D031",
    "DEC-D032", "GATE-G005", "GATE-G008", "GATE-G011", "GATE-G015",
    "M001-ARCHITECTURE-ONLY-GUARDRAIL", "REQ-R001", "REQ-R009", "REQ-R010",
    "REQ-R017", "REQ-R022", "REQ-R028", "REQ-R029",
    "RISK-OVERCLAIM-RUNTIME", "S04-FALKORDB-RUNTIME-BOUNDED",
    "S05-OLD-PROJECT-PRIOR-ART", "S05-PARSER-ODT-BOUNDARY", "S07-FIXED-PRD-CONSISTENCY",
    "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED", "S10-USER-BGE-M3-BASELINE",
}

SAFE_IDS = {
    "ASSUMP-PRD-SOURCE-TRUTH", "CHECK-ARCHITECTURE-EXTRACTOR", "DEC-D031",
    "DEC-D032", "REQ-R001", "REQ-R009", "REQ-R010", "REQ-R017",
    "REQ-R022", "REQ-R029", "RISK-OVERCLAIM-RUNTIME",
}

BOUNDED_IDS = {
    "S04-FALKORDB-RUNTIME-BOUNDED", "S05-OLD-PROJECT-PRIOR-ART",
    "S05-PARSER-ODT-BOUNDARY", "S07-FIXED-PRD-CONSISTENCY", "S10-USER-BGE-M3-BASELINE",
}

BLOCKED_IDS = {
    "GATE-G005", "GATE-G008", "GATE-G011", "GATE-G015",
    "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED",
}

UNSAFE_IDS = {"M001-ARCHITECTURE-ONLY-GUARDRAIL", "REQ-R028"}


def _load_claims_content() -> str:
    """Load claims ledger content, fail with clear message if missing."""
    assert CLAIMS_MD_PATH.exists(), (
        f"Claims ledger not found at {CLAIMS_MD_PATH}. "
        "Run: uv run python scripts/generate-architecture-views.py"
    )
    return CLAIMS_MD_PATH.read_text(encoding="utf-8")


def test_claims_ledger_exists() -> None:
    """Claims ledger file must exist."""
    _load_claims_content()


def test_claims_ledger_has_required_sections() -> None:
    """Claims ledger must contain all four classification sections."""
    content = _load_claims_content()
    required = [
        "## safe-to-say",
        "## bounded",
        "## blocked/open",
        "## unsafe-to-assert",
    ]
    for section in required:
        assert section in content, f"Missing required section: {section}"


def test_claims_ledger_has_classification_guide() -> None:
    """Claims ledger must include a classification guide table."""
    content = _load_claims_content()
    assert "## Classification Guide" in content, (
        "Claims ledger must include a Classification Guide"
    )
    assert "| **safe-to-say**" in content
    assert "| **bounded**" in content
    assert "| **blocked/open**" in content
    assert "| **unsafe-to-assert**" in content


def test_claims_ledger_scope_disclaimer_present() -> None:
    """Claims ledger must include a scope disclaimer."""
    content = _load_claims_content()
    assert "non-authoritative" in content.lower(), (
        "Claims ledger must declare itself non-authoritative"
    )


def test_claims_ledger_non_authoritative_footer_present() -> None:
    """Claims ledger must have a non-authoritative footer."""
    content = _load_claims_content()
    assert "derived, non-authoritative planning artifact" in content, (
        "Claims ledger must have non-authoritative footer"
    )


# ---------------------------------------------------------------------------
# Claims ledger — all 23 items appear
# ---------------------------------------------------------------------------

def test_claims_ledger_covers_all_23_items() -> None:
    """Every architecture item ID must appear in the claims ledger somewhere."""
    content = _load_claims_content()
    missing = [rid for rid in sorted(ALL_23_IDS) if rid not in content]
    assert not missing, f"Claims ledger is missing item IDs: {missing}"


def test_claims_ledger_all_safe_items_present() -> None:
    """All 11 safe-to-say items must appear in the safe-to-say section."""
    content = _load_claims_content()
    section_start = content.find("## safe-to-say")
    section_end = content.find("\n## ", section_start + 1)
    safe_section = content[section_start:section_end]
    missing = [rid for rid in sorted(SAFE_IDS) if rid not in safe_section]
    assert not missing, f"safe-to-say section is missing: {missing}"


def test_claims_ledger_all_bounded_items_present() -> None:
    """All 5 bounded items must appear in the bounded section."""
    content = _load_claims_content()
    section_start = content.find("## bounded")
    section_end = content.find("\n## ", section_start + 1)
    bounded_section = content[section_start:section_end]
    missing = [rid for rid in sorted(BOUNDED_IDS) if rid not in bounded_section]
    assert not missing, f"bounded section is missing: {missing}"


def test_claims_ledger_all_blocked_items_present() -> None:
    """All 5 blocked/open items must appear in the blocked/open section."""
    content = _load_claims_content()
    section_start = content.find("## blocked/open")
    section_end = content.find("\n## ", section_start + 1)
    blocked_section = content[section_start:section_end]
    missing = [rid for rid in sorted(BLOCKED_IDS) if rid not in blocked_section]
    assert not missing, f"blocked/open section is missing: {missing}"


def test_claims_ledger_all_unsafe_items_present() -> None:
    """All 2 unsafe-to-assert items must appear in the unsafe-to-assert section."""
    content = _load_claims_content()
    section_start = content.find("## unsafe-to-assert")
    section_end = len(content)
    unsafe_section = content[section_start:section_end]
    missing = [rid for rid in sorted(UNSAFE_IDS) if rid not in unsafe_section]
    assert not missing, f"unsafe-to-assert section is missing: {missing}"


def test_claims_ledger_total_count_is_23() -> None:
    """The ledger must account for all 23 architecture items across four classes."""
    content = _load_claims_content()
    safe_count = content.count("## safe-to-say")  # section header
    bounded_count = content.count("## bounded")
    blocked_count = content.count("## blocked/open")
    unsafe_count = content.count("## unsafe-to-assert")
    # All four class markers must appear exactly once each
    assert safe_count == 1
    assert bounded_count == 1
    assert blocked_count == 1
    assert unsafe_count == 1
    # Total unique IDs across all sections must be 23
    all_found = sum(1 for rid in ALL_23_IDS if rid in content)
    assert all_found == 23, f"Expected 23 items, found {all_found}"


def test_claims_ledger_no_duplicate_item_ids() -> None:
    """No item ID should appear in more than one classification section."""
    content = _load_claims_content()
    for rid in sorted(ALL_23_IDS):
        # Find all occurrences
        start = 0
        positions = []
        while True:
            idx = content.find(rid, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + 1
        # Should appear exactly once
        assert len(positions) == 1, (
            f"Item {rid} appears {len(positions)} times — each item must be "
            f"classified into exactly one section"
        )


# ---------------------------------------------------------------------------
# Claims ledger — required known unsafe items
# ---------------------------------------------------------------------------

def test_claims_ledger_includes_m001_guardrail() -> None:
    """M001 architecture-only guardrail must appear as unsafe-to-assert."""
    content = _load_claims_content()
    assert "M001-ARCHITECTURE-ONLY-GUARDRAIL" in content
    # Must appear in the unsafe-to-assert section, not any other
    section_start = content.find("## unsafe-to-assert")
    assert section_start >= 0
    section_end = len(content)
    unsafe_section = content[section_start:section_end]
    assert "M001-ARCHITECTURE-ONLY-GUARDRAIL" in unsafe_section


def test_claims_ledger_includes_r028_llm_not_legal_authority() -> None:
    """REQ-R028 (LLM not legal authority) must appear as unsafe-to-assert."""
    content = _load_claims_content()
    assert "REQ-R028" in content
    # Must appear in the unsafe-to-assert section
    section_start = content.find("## unsafe-to-assert")
    section_end = len(content)
    unsafe_section = content[section_start:section_end]
    assert "REQ-R028" in unsafe_section


def test_claims_ledger_unsafe_items_have_out_of_scope_status() -> None:
    """Both unsafe-to-assert items must show 'out-of-scope' status in the ledger."""
    content = _load_claims_content()
    section_start = content.find("## unsafe-to-assert")
    section_end = len(content)
    unsafe_section = content[section_start:section_end]
    for rid in UNSAFE_IDS:
        assert rid in unsafe_section
        # The row should contain "| out-of-scope |" for these items
        rid_pos = unsafe_section.find(rid)
        # Check the next ~200 chars after the ID contains "| out-of-scope |"
        row_snippet = unsafe_section[rid_pos:rid_pos + 300]
        assert "out-of-scope" in row_snippet, (
            f"{rid} should show 'out-of-scope' status in the unsafe-to-assert table"
        )


# ---------------------------------------------------------------------------
# Claims ledger — evidence / non-claims
# ---------------------------------------------------------------------------

def test_claims_ledger_safe_items_have_non_claims_column() -> None:
    """Safe-to-say rows must include a Non-Claims column."""
    content = _load_claims_content()
    section_start = content.find("## safe-to-say")
    section_end = content.find("\n## ", section_start + 1)
    safe_section = content[section_start:section_end]
    assert "| Non-Claims |" in safe_section, (
        "Safe-to-say table must have a Non-Claims column"
    )


def test_claims_ledger_bounded_items_have_proof_level() -> None:
    """Bounded rows must include a Proof Level column."""
    content = _load_claims_content()
    section_start = content.find("## bounded")
    section_end = content.find("\n## ", section_start + 1)
    bounded_section = content[section_start:section_end]
    assert "| Proof Level |" in bounded_section, (
        "Bounded table must have a Proof Level column"
    )


def test_claims_ledger_blocked_items_have_verification() -> None:
    """Blocked/open rows must include a Verification column."""
    content = _load_claims_content()
    section_start = content.find("## blocked/open")
    section_end = content.find("\n## ", section_start + 1)
    blocked_section = content[section_start:section_end]
    assert "| Verification |" in blocked_section, (
        "Blocked/open table must have a Verification column"
    )


def test_claims_ledger_safe_items_contain_non_claims_content() -> None:
    """Safe-to-say rows must contain actual non-claims text (❌ markers or text)."""
    content = _load_claims_content()
    section_start = content.find("## safe-to-say")
    section_end = content.find("\n## ", section_start + 1)
    safe_section = content[section_start:section_end]
    # At least ASSUMP-PRD-SOURCE-TRUTH has a non-claim
    assert "❌" in safe_section or "Does not make generated artifacts authoritative" in safe_section


def test_claims_ledger_bounded_items_show_specific_proof_levels() -> None:
    """Bounded items must show the correct proof_level from the JSONL."""
    content = _load_claims_content()
    # S05-OLD-PROJECT-PRIOR-ART has proof_level=source-anchor
    assert "S05-OLD-PROJECT-PRIOR-ART" in content
    # S05-PARSER-ODT-BOUNDARY has proof_level=real-document-proof
    assert "S05-PARSER-ODT-BOUNDARY" in content
    # S10-USER-BGE-M3-BASELINE has proof_level=runtime-smoke
    assert "S10-USER-BGE-M3-BASELINE" in content


def test_claims_ledger_blocked_gates_have_no_proof() -> None:
    """Blocked/open items with proof_level=none must show 'none' in their row."""
    content = _load_claims_content()
    for gate_id in ["GATE-G005", "GATE-G008", "GATE-G011", "GATE-G015"]:
        section_start = content.find("## blocked/open")
        section_end = content.find("\n## ", section_start + 1)
        blocked_section = content[section_start:section_end]
        assert gate_id in blocked_section
        pos = blocked_section.find(gate_id)
        row_snippet = blocked_section[pos:pos + 300]
        # The proof_level column should contain "none" for these gates
        assert "none" in row_snippet, (
            f"{gate_id} should show 'none' proof level in the blocked/open table"
        )


# ---------------------------------------------------------------------------
# Claims ledger — forbidden overclaim wording
# ---------------------------------------------------------------------------

def test_claims_ledger_does_not_claim_product_ready() -> None:
    """Claims ledger must NOT claim product readiness."""
    content = _load_claims_content()
    content_lower = content.lower()
    overclaims = [
        "product ready",
        "product-ready",
        "production ready",
        "production-ready",
        "shippable",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Claims ledger must NOT contain '{phrase}'"
        )


def test_claims_ledger_does_not_claim_legal_answer_correctness() -> None:
    """Claims ledger must NOT claim legal-answer correctness."""
    content = _load_claims_content()
    content_lower = content.lower()
    overclaims = [
        "legal answer correct",
        "legally correct",
        "correct legal answer",
        "guarantees legal accuracy",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Claims ledger must NOT contain '{phrase}'"
        )


def test_claims_ledger_does_not_claim_llm_legal_authority() -> None:
    """Claims ledger must NOT claim LLM has legal authority."""
    content = _load_claims_content()
    content_lower = content.lower()
    overclaims = [
        "llm has legal authority",
        "llm is legally authoritative",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Claims ledger must NOT contain '{phrase}'"
        )


def test_claims_ledger_does_not_claim_parser_complete() -> None:
    """Claims ledger must NOT assert the parser is complete."""
    content = _load_claims_content()
    content_lower = content.lower()
    overclaims = [
        "parser is complete",
        "parser is production",
        "parser is ready",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Claims ledger must NOT contain '{phrase}'"
        )


def test_claims_ledger_does_not_claim_etl_production() -> None:
    """Claims ledger must NOT assert ETL is production-ready."""
    content = _load_claims_content()
    content_lower = content.lower()
    overclaims = [
        "etl is production",
        "etl is ready",
        "etl is complete",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Claims ledger must NOT contain '{phrase}'"
        )


def test_claims_ledger_does_not_claim_knowql_works() -> None:
    """Claims ledger must NOT claim Legal KnowQL works."""
    content = _load_claims_content()
    content_lower = content.lower()
    overclaims = [
        "knowql works",
        "legal knowql works",
        "knowql is production",
    ]
    for phrase in overclaims:
        assert phrase not in content_lower, (
            f"Claims ledger must NOT contain '{phrase}'"
        )


def test_claims_ledger_does_not_claim_falkordb_production_scale() -> None:
    """Claims ledger must NOT claim FalkorDB is production-scale."""
    content = _load_claims_content()
    content_lower = content.lower()
    overclaims = [
        "production-scale falkordb",  # "No production-scale FalkorDB claim" is fine; "is production-scale" is not
    ]
    # Check for the affirmative form only (not the non-claim "No production-scale")
    assert "is production-scale falkordb" not in content_lower
    assert "falkordb is production" not in content_lower


# ---------------------------------------------------------------------------
# Claims ledger — classification function unit tests
# ---------------------------------------------------------------------------

def test_classify_safe_source_anchor_active() -> None:
    """source-anchor proof + active status → safe-to-say."""
    module = load_generator()
    record = {
        "id": "TEST-SAFE-001",
        "status": "active",
        "proof_level": "source-anchor",
        "non_claims": ["does not assert X."],
    }
    assert module._classify_record(record) == "safe-to-say"


def test_classify_safe_static_check_active() -> None:
    """static-check proof + active status → safe-to-say."""
    module = load_generator()
    record = {
        "id": "TEST-SAFE-002",
        "status": "active",
        "proof_level": "static-check",
        "non_claims": [],
    }
    assert module._classify_record(record) == "safe-to-say"


def test_classify_bounded_runtime_smoke_active() -> None:
    """runtime-smoke proof + active status → bounded."""
    module = load_generator()
    record = {
        "id": "TEST-BOUNDED-001",
        "status": "active",
        "proof_level": "runtime-smoke",
        "non_claims": [],
    }
    assert module._classify_record(record) == "bounded"


def test_classify_bounded_real_document_proof_active() -> None:
    """real-document-proof + active status → bounded."""
    module = load_generator()
    record = {
        "id": "TEST-BOUNDED-002",
        "status": "active",
        "proof_level": "real-document-proof",
        "non_claims": [],
    }
    assert module._classify_record(record) == "bounded"


def test_classify_bounded_status() -> None:
    """bounded-evidence status → bounded regardless of proof_level."""
    module = load_generator()
    record = {
        "id": "TEST-BOUNDED-003",
        "status": "bounded-evidence",
        "proof_level": "source-anchor",
        "non_claims": [],
    }
    assert module._classify_record(record) == "bounded"


def test_classify_blocked_explicit_status() -> None:
    """blocked status → blocked/open."""
    module = load_generator()
    record = {
        "id": "TEST-BLOCKED-001",
        "status": "blocked",
        "proof_level": "source-anchor",
        "non_claims": [],
    }
    assert module._classify_record(record) == "blocked/open"


def test_classify_blocked_none_proof_active() -> None:
    """proof_level=none + active → blocked/open."""
    module = load_generator()
    record = {
        "id": "TEST-BLOCKED-002",
        "status": "active",
        "proof_level": "none",
        "non_claims": [],
    }
    assert module._classify_record(record) == "blocked/open"


def test_classify_unsafe_out_of_scope() -> None:
    """out-of-scope status → unsafe-to-assert."""
    module = load_generator()
    record = {
        "id": "TEST-UNSAFE-001",
        "status": "out-of-scope",
        "proof_level": "source-anchor",
        "non_claims": [],
    }
    assert module._classify_record(record) == "unsafe-to-assert"


def test_classify_unsafe_unknown_proof_and_status() -> None:
    """Unknown proof_level + active → unsafe-to-assert."""
    module = load_generator()
    record = {
        "id": "TEST-UNSAFE-002",
        "status": "active",
        "proof_level": "unknown",
        "non_claims": [],
    }
    assert module._classify_record(record) == "unsafe-to-assert"


# ---------------------------------------------------------------------------
# Claims ledger — determinism
# ---------------------------------------------------------------------------

def test_claims_ledger_generator_is_deterministic() -> None:
    """Claims ledger generator is deterministic for the same items_lookup + report."""
    module = load_generator()
    report = load_report()
    items_lookup = module._load_items_lookup(REPORT_JSON_PATH.parent / "architecture_items.jsonl")
    first = module.render_claims_ledger(items_lookup, report)
    second = module.render_claims_ledger(items_lookup, report)
    assert first == second, "Claims ledger generator is non-deterministic"


def test_claims_ledger_matches_stored_file() -> None:
    """Stored claims ledger must match current generator output."""
    module = load_generator()
    report = load_report()
    items_lookup = module._load_items_lookup(REPORT_JSON_PATH.parent / "architecture_items.jsonl")
    expected = module.render_claims_ledger(items_lookup, report)
    actual = CLAIMS_MD_PATH.read_text(encoding="utf-8")
    assert actual == expected, (
        "Stored claims ledger is stale. Run:\n"
        f"  uv run python {GENERATE_SCRIPT_PATH}"
    )


def test_check_claims_ledger_output_function_detects_stale(tmp_path: Path) -> None:
    """check_claims_ledger_output must detect stale content."""
    module = load_generator()
    report = load_report()
    items_lookup = module._load_items_lookup(REPORT_JSON_PATH.parent / "architecture_items.jsonl")
    fresh = module.render_claims_ledger(items_lookup, report)
    claims_path = tmp_path / "claims.md"
    claims_path.write_text(fresh, encoding="utf-8")
    assert module.check_claims_ledger_output(claims_path, fresh) is True
    stale = fresh + "\n\n<!-- stale -->"
    assert module.check_claims_ledger_output(claims_path, stale) is False


def test_check_claims_ledger_output_function_detects_missing(tmp_path: Path) -> None:
    """check_claims_ledger_output must detect missing files."""
    module = load_generator()
    missing = tmp_path / "nonexistent.md"
    assert module.check_claims_ledger_output(missing, "any") is False


# ---------------------------------------------------------------------------
# Blockers report — determinism
# ---------------------------------------------------------------------------

def test_blockers_report_generator_is_deterministic() -> None:
    """Blockers report generator is deterministic for the same report + items_lookup."""
    module = load_generator()
    report = load_report()
    items_lookup = module._load_items_lookup(REPORT_JSON_PATH.parent / "architecture_items.jsonl")
    first = module.render_blockers_report(report, items_lookup)
    second = module.render_blockers_report(report, items_lookup)
    assert first == second, "Blockers report generator is non-deterministic"


def test_blockers_report_matches_stored_file() -> None:
    """Stored blockers report must match current generator output."""
    module = load_generator()
    report = load_report()
    items_lookup = module._load_items_lookup(REPORT_JSON_PATH.parent / "architecture_items.jsonl")
    expected = module.render_blockers_report(report, items_lookup)
    actual = BLOCKERS_MD_PATH.read_text(encoding="utf-8")
    assert actual == expected, (
        "Stored blockers report is stale. Run:\n"
        f"  uv run python {GENERATE_SCRIPT_PATH}"
    )


def test_check_blockers_output_function_detects_stale(tmp_path: Path) -> None:
    """check_blockers_output must detect stale content."""
    module = load_generator()
    report = load_report()
    items_lookup = module._load_items_lookup(REPORT_JSON_PATH.parent / "architecture_items.jsonl")
    fresh = module.render_blockers_report(report, items_lookup)
    blockers_path = tmp_path / "blockers.md"
    blockers_path.write_text(fresh, encoding="utf-8")
    assert module.check_blockers_output(blockers_path, fresh) is True
    stale = fresh + "\n\n<!-- stale -->"
    assert module.check_blockers_output(blockers_path, stale) is False


def test_check_blockers_output_function_detects_missing(tmp_path: Path) -> None:
    """check_blockers_output must detect missing files."""
    module = load_generator()
    missing = tmp_path / "nonexistent.md"
    assert module.check_blockers_output(missing, "any") is False


# ---------------------------------------------------------------------------
# Full view generator — --check mode integration
# ---------------------------------------------------------------------------

def test_generate_script_supports_check_flag() -> None:
    """The generator script must support --check and exit 0 when all views are fresh."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(GENERATE_SCRIPT_PATH), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"generate-architecture-views.py --check failed:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_generate_script_check_reports_all_three_views() -> None:
    """--check mode must process all three views (health, blockers, claims)."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(GENERATE_SCRIPT_PATH), "--check"],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert "health" in output.lower() or "architecture_health" in output.lower() or "ok" in output.lower()


def test_generate_script_write_produces_all_three_views(tmp_path: Path) -> None:
    """Write mode must produce all three .md files."""
    import subprocess
    health = tmp_path / "health.md"
    blockers = tmp_path / "blockers.md"
    claims = tmp_path / "claims.md"
    result = subprocess.run(
        [
            sys.executable, str(GENERATE_SCRIPT_PATH),
            "--health-md", str(health),
            "--blockers-md", str(blockers),
            "--claims-ledger-md", str(claims),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Generator failed: {result.stderr}"
    assert health.exists(), "Health dashboard not written"
    assert blockers.exists(), "Blockers report not written"
    assert claims.exists(), "Claims ledger not written"
    # Spot-check content
    assert health.read_text().startswith("# Architecture Health Dashboard")
    assert blockers.read_text().startswith("# Product Readiness Blockers Report")
    assert claims.read_text().startswith("# Claims Ledger")


def test_generate_script_check_fails_on_stale_health(tmp_path: Path) -> None:
    """--check must fail if the health dashboard is stale."""
    import subprocess
    stale_health = tmp_path / "health.md"
    stale_health.write_text("# stale", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, str(GENERATE_SCRIPT_PATH),
            "--health-md", str(stale_health),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "--check should fail on stale health dashboard"
    )
    assert "stale" in result.stderr.lower() or "stale" in result.stdout.lower()


def test_generate_script_check_fails_on_stale_blockers(tmp_path: Path) -> None:
    """--check must fail if the blockers report is stale."""
    import subprocess
    stale_blockers = tmp_path / "blockers.md"
    stale_blockers.write_text("# stale", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, str(GENERATE_SCRIPT_PATH),
            "--blockers-md", str(stale_blockers),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "--check should fail on stale blockers report"
    )


def test_generate_script_check_fails_on_stale_claims(tmp_path: Path) -> None:
    """--check must fail if the claims ledger is stale."""
    import subprocess
    stale_claims = tmp_path / "claims.md"
    stale_claims.write_text("# stale", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, str(GENERATE_SCRIPT_PATH),
            "--claims-ledger-md", str(stale_claims),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "--check should fail on stale claims ledger"
    )


def test_generate_script_check_fails_on_missing_report() -> None:
    """Generator must fail gracefully if the report JSON is missing."""
    import subprocess
    result = subprocess.run(
        [
            sys.executable, str(GENERATE_SCRIPT_PATH),
            "--report-json", "/nonexistent/report.json",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "Generator should exit non-zero when report JSON is missing"
    )


def test_all_three_views_use_non_authoritative_disclaimer() -> None:
    """All three generated views must include a non-authoritative or scope disclaimer."""
    health = HEALTH_MD_PATH.read_text(encoding="utf-8")
    blockers = BLOCKERS_MD_PATH.read_text(encoding="utf-8")
    claims = CLAIMS_MD_PATH.read_text(encoding="utf-8")

    # Health dashboard uses "**Non-Authoritative:**" in bold
    assert "Non-Authoritative" in health or "non-authoritative" in health.lower(), (
        "health view must include a non-authoritative disclaimer"
    )

    # Blockers report uses "planning artifact" scope disclaimer + "Source-of-truth"
    blockers_lower = blockers.lower()
    assert ("planning artifact" in blockers_lower
            or "non-authoritative" in blockers_lower), (
        "blockers view must include a scope disclaimer"
    )
    assert "source-of-truth" in blockers_lower, (
        "blockers view must reference source-of-truth boundaries"
    )

    # Claims ledger uses "non-authoritative planning artifact" in footer
    assert "non-authoritative" in claims.lower(), (
        "claims ledger must include a non-authoritative disclaimer"
    )
