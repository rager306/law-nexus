from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_SCRIPT_PATH = ROOT / "scripts/generate-architecture-views.py"


def load_view_generator_module() -> Any:
    spec = importlib.util.spec_from_file_location("architecture_view_generator", GENERATOR_SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def item(
    record_id: str,
    *,
    title: str = "Fixture item",
    summary: str = "Fixture summary.",
    record_type: str = "requirement",
    status: str = "active",
    proof_level: str = "source-anchor",
    risk_level: str = "medium",
    priority: str = "medium",
    layer: str = "architecture-governance",
    owner: str = "fixture-owner",
    verification: str = "Fixture verification.",
    non_claims: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "title": title,
        "summary": summary,
        "type": record_type,
        "status": status,
        "proof_level": proof_level,
        "risk_level": risk_level,
        "priority": priority,
        "layer": layer,
        "owner": owner,
        "verification": verification,
        "non_claims": non_claims or ["Does not validate product readiness."],
    }


def minimal_report() -> dict[str, Any]:
    return {
        "counts": {"nodes": 4, "edges": 0},
        "layer_coverage": {"counts": {"architecture-governance": 4}, "missing_layers": [], "invalid_layers": []},
        "unresolved_proof_gates": [
            {
                "id": "GATE-CRITICAL",
                "layer": "generated-cypher",
                "owner": "fixture-owner",
                "risk_level": "critical",
                "verification": "Future proof work only.",
            }
        ],
        "orphan_findings": [],
        "high_risk_nodes": [
            {
                "id": "GATE-CRITICAL",
                "risk_level": "critical",
                "type": "proof_gate",
                "layer": "generated-cypher",
                "status": "active",
                "proof_level": "none",
            }
        ],
        "contradiction_edges": [],
        "non_claims_summary": {"nodes_with_non_claims": 1, "total_non_claims": 1, "by_node": []},
    }


def test_health_view_surfaces_priority_buckets_and_non_authoritative_warnings() -> None:
    generator = load_view_generator_module()
    items = {
        "GATE-CRITICAL": item(
            "GATE-CRITICAL",
            record_type="proof_gate",
            status="active",
            proof_level="none",
            risk_level="critical",
            priority="critical",
        ),
        "GATE-HIGH": item(
            "GATE-HIGH",
            record_type="proof_gate",
            status="active",
            proof_level="none",
            risk_level="high",
            priority="high",
        ),
        "BACKLOG-CANDIDATE": item(
            "BACKLOG-CANDIDATE",
            status="proposed",
            proof_level="none",
            risk_level="low",
            priority="low",
        ),
    }

    content = generator.render_health_dashboard(minimal_report(), items_lookup=items)

    assert "## GSD Validation Snapshot" in content
    assert "| P0 | critical-gate | 1 |" in content
    assert "| P1 | high-priority-blocker | 1 |" in content
    assert "### Critical Blockers" in content
    assert "`GATE-CRITICAL`" in content
    assert "### High-Priority Validator Failures" in content
    assert "`GATE-HIGH`" in content
    assert "### Deferred Candidates" in content
    assert "`BACKLOG-CANDIDATE`" in content
    assert "A passing generated view check is not product/runtime/legal validation" in content


def test_blockers_report_adds_priority_snapshot_without_raw_payloads() -> None:
    generator = load_view_generator_module()
    report = minimal_report()
    report["unresolved_proof_gates"][0]["title"] = "Generated-Cypher safety gate"
    items = {
        "GATE-CRITICAL": item(
            "GATE-CRITICAL",
            title="Generated-Cypher safety gate",
            record_type="proof_gate",
            status="active",
            proof_level="none",
            risk_level="critical",
            priority="critical",
            layer="generated-cypher",
            non_claims=["Does not authorize generated Cypher execution."],
        )
    }

    content = generator.render_blockers_report(report, items_lookup=items)

    assert "## Priority Snapshot" in content
    assert "| P0 | 1 | `GATE-CRITICAL` |" in content
    assert "| ID | Title | Priority | Status | Risk | Verification | Owner |" in content
    assert "P0 / critical-gate" in content
    assert "Does not authorize generated Cypher execution." in content
    assert "SECRET" not in content
    assert ".gsd/exec" not in content


def test_blockers_report_includes_report_layers_outside_curated_area_map() -> None:
    generator = load_view_generator_module()
    report = minimal_report()
    report["high_risk_nodes"].append(
        {
            "id": "REQ-GOVERNANCE-BLOCKED",
            "risk_level": "high",
            "type": "requirement",
            "layer": "architecture-governance",
            "status": "bounded-evidence",
            "proof_level": "source-anchor",
        }
    )
    items = {
        "REQ-GOVERNANCE-BLOCKED": item(
            "REQ-GOVERNANCE-BLOCKED",
            title="Architecture governance blocker",
            status="bounded-evidence",
            risk_level="high",
            priority="high",
            layer="architecture-governance",
            verification="Verify through architecture registry generation.",
            non_claims=["Does not prove architecture governance drift is resolved."],
        )
    }

    content = generator.render_blockers_report(report, items_lookup=items)

    assert "| architecture-governance | 0 | 1 |" in content
    assert "## architecture-governance" in content
    assert "`REQ-GOVERNANCE-BLOCKED`" in content
    assert "Does not prove architecture governance drift is resolved." in content


def test_claims_ledger_surfaces_r035_gate_status_as_guardrail_only() -> None:
    generator = load_view_generator_module()
    items = {
        "EVID-GRAPHRAG-CANDIDATE": item(
            "EVID-GRAPHRAG-CANDIDATE",
            title="GraphRAG candidate",
            summary="GraphRAG remains a proof-gated integration candidate only.",
            record_type="evidence",
            status="bounded-evidence",
            proof_level="source-anchor",
            risk_level="high",
            priority="high",
            layer="retrieval-embedding",
            non_claims=["Does not prove GraphRAG production behavior."],
        )
    }

    content = generator.render_claims_ledger(items, minimal_report())

    assert "## R035 Gate Status" in content
    assert "Ontology, external-standard, GraphRAG, graph-vector, and pilot-scale rows are registry/view synchronization-only guardrails" in content
    assert "not standard, runtime, product behavior, retrieval quality, FalkorDB runtime, or R035 validation" in content
    assert "`EVID-GRAPHRAG-CANDIDATE`" in content
    assert "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION" in content
    assert "S07/S08 runtime remediation reference" in content
    assert "ontology_graphrag_runtime_integration_proof.json" in content
    assert "13-r035-runtime-integration-remediation.md" in content
    assert "bounded runtime remediation or blocked prerequisite diagnostics only" in content
    assert "R035 remains Active" in content
    assert "formal standard conformance" in content
    assert "proof_level<integration-test" in content
    assert "add-proof-gate" in content
    assert "do not validate the referenced standard or product behavior" not in content
    assert "not standard, runtime, product behavior, retrieval quality, FalkorDB runtime, or R035 validation" in content
    assert "production ready" not in content.lower()


def test_claims_ledger_r035_gate_status_lists_legal_hierarchy_and_collision_policy() -> None:
    generator = load_view_generator_module()
    items = {
        "DATA-LEGAL-SOURCE-HIERARCHY": item(
            "DATA-LEGAL-SOURCE-HIERARCHY",
            title="Legal source hierarchy candidate",
            summary="Candidate hierarchy model for legal force, federal competence, supersession, and lex maxim inputs.",
            record_type="data_entity",
            status="hypothesis",
            proof_level="source-anchor",
            risk_level="high",
            priority="high",
            layer="legal-evidence",
            non_claims=["Does not decide legal priority."],
        ),
        "GATE-LEGAL-COLLISION-POLICY": item(
            "GATE-LEGAL-COLLISION-POLICY",
            title="Legal collision policy proof gate",
            summary="Proof gate for lex superior, lex specialis, lex posterior, supersession, and explainable norm-priority behavior.",
            record_type="proof_gate",
            status="proposed",
            proof_level="source-anchor",
            risk_level="high",
            priority="high",
            layer="legal-evidence",
            non_claims=["Does not prove automated legal collision resolution."],
        ),
    }

    content = generator.render_claims_ledger(items, minimal_report())

    assert "`DATA-LEGAL-SOURCE-HIERARCHY`" in content
    assert "`GATE-LEGAL-COLLISION-POLICY`" in content
    assert "GATE-LEGAL-COLLISION-POLICY" in content
    assert "registry/view synchronization-only guardrails" in content
    assert "not standard, runtime, product behavior, retrieval quality, FalkorDB runtime, or R035 validation" in content


REPORT_PATHS = (
    ROOT / "prd/architecture/architecture_health.md",
    ROOT / "prd/architecture/product_readiness_blockers.md",
    ROOT / "prd/architecture/claims_ledger.md",
)

UNSAFE_POSITIVE_REPORT_PHRASES = (
    "product is production ready",
    "product-ready",
    "legal answers are correct",
    "legal-answer correctness is validated",
    "parser is complete",
    "parser completeness is proven",
    "retrieval quality is proven",
    "generated cypher is safe",
    "generated-cypher safety is validated",
    "falkordb production scale is validated",
    "llm output is authoritative",
    "dashboard is complete",
    "repair completed",
    "source repaired",
    "proof completed",
    "auto-repaired",
)


def assert_contains_boundary(content: str, required: str) -> None:
    normalized_content = re.sub(r"[*_`]+", "", content.lower())
    normalized_required = re.sub(r"[*_`]+", "", required.lower())
    assert normalized_required in normalized_content, f"missing report boundary/disclaimer: {required!r}"


def assert_omits_unsafe_positive_phrase(content: str, phrase: str, path: Path | str) -> None:
    assert phrase not in content.lower(), f"unsafe phrase {phrase!r} appears in generated report {path}"


def test_generated_reports_preserve_minimal_non_authoritative_disclaimers() -> None:
    for path in REPORT_PATHS:
        content = path.read_text(encoding="utf-8")
        assert_contains_boundary(content, "non-authoritative")
        assert_contains_boundary(content, "derived")
        assert_contains_boundary(content, "source-of-truth remains")

    health = (ROOT / "prd/architecture/architecture_health.md").read_text(encoding="utf-8")
    assert_contains_boundary(health, "A passing generated view check is not product/runtime/legal validation")

    blockers = (ROOT / "prd/architecture/product_readiness_blockers.md").read_text(encoding="utf-8")
    for boundary in (
        "does not assert product readiness",
        "does not validate runtime behavior",
        "retrieval quality",
        "parser completeness",
        "generated-Cypher safety",
        "FalkorDB production scale",
        "legal-answer correctness",
    ):
        assert_contains_boundary(blockers, boundary)

    claims = (ROOT / "prd/architecture/claims_ledger.md").read_text(encoding="utf-8")
    for boundary in (
        "do not use it as proof",
        "registry/view synchronization-only guardrails",
        "not standard, runtime, product behavior, retrieval quality, FalkorDB runtime, or R035 validation",
        "S07/S08 runtime remediation reference",
        "bounded runtime remediation or blocked prerequisite diagnostics only",
        "R035 remains Active",
        "Always cite source anchors",
    ):
        assert_contains_boundary(claims, boundary)


def test_current_generated_reports_do_not_assert_forbidden_completion_boundaries() -> None:
    for path in REPORT_PATHS:
        content = path.read_text(encoding="utf-8").lower()
        for phrase in UNSAFE_POSITIVE_REPORT_PHRASES:
            assert_omits_unsafe_positive_phrase(content, phrase, path)


def test_rendered_minimal_reports_keep_safety_boundaries_and_avoid_completion_claims() -> None:
    generator = load_view_generator_module()
    report = minimal_report()
    items = {
        "GATE-CRITICAL": item(
            "GATE-CRITICAL",
            title="Generated-Cypher safety gate",
            record_type="proof_gate",
            status="active",
            proof_level="none",
            risk_level="critical",
            priority="critical",
            layer="generated-cypher",
            non_claims=[
                "Does not assert product readiness.",
                "Does not validate legal correctness.",
                "Does not prove parser completeness.",
                "Does not prove retrieval quality.",
                "Does not authorize generated Cypher execution.",
                "Does not prove FalkorDB production scale.",
                "Does not make LLM output authoritative.",
            ],
        )
    }

    rendered_reports = {
        "health": generator.render_health_dashboard(report, items_lookup=items),
        "blockers": generator.render_blockers_report(report, items_lookup=items),
        "claims": generator.render_claims_ledger(items, report),
    }

    for name, content in rendered_reports.items():
        assert_contains_boundary(content, "non-authoritative")
        assert_contains_boundary(content, "derived")
        for phrase in UNSAFE_POSITIVE_REPORT_PHRASES:
            assert_omits_unsafe_positive_phrase(content, phrase, name)

    assert_contains_boundary(rendered_reports["health"], "not product/runtime/legal validation")
    assert_contains_boundary(rendered_reports["blockers"], "does not assert product readiness")
    assert_contains_boundary(rendered_reports["claims"], "do not use it as proof")
