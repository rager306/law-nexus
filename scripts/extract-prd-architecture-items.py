#!/usr/bin/env python3
"""Extract conservative PRD/GSD architecture registry JSONL records.

This script intentionally uses explicit curated mappings. It does not infer
architecture state from broad Markdown scans, and it never promotes current
records to ``validated``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "legalgraph-architecture-registry/v1"
DEFAULT_ITEMS = Path("prd/architecture/architecture_items.jsonl")
DEFAULT_EDGES = Path("prd/architecture/architecture_edges.jsonl")
DEFAULT_S08_FINDINGS = Path(".gsd/milestones/M001/slices/S08/S08-FINDINGS.json")
REQUIRED_SOURCE_PATHS = [
    Path("prd/architecture/architecture.schema.json"),
    Path("tests/fixtures/architecture/valid_items.jsonl"),
    Path("tests/fixtures/architecture/valid_edges.jsonl"),
    Path(".gsd/REQUIREMENTS.md"),
    Path(".gsd/DECISIONS.md"),
    Path(".gsd/PROJECT.md"),
    DEFAULT_S08_FINDINGS,
    Path("prd/05_final_architecture_review.md"),
    Path("prd/09_architecture_planning_verification_research.md"),
    Path("prd/04_review_findings.md"),
    Path("prd/parser/golden_test_proof_report.md"),
    Path("prd/parser/consultant_parser_proof.md"),
    Path(".gsd/milestones/M008/M008-SUMMARY.md"),
    Path(".gsd/milestones/M009/M009-SUMMARY.md"),
    Path("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis.md"),
    Path("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis_assessment.md"),
    Path("prd/research/habr_legal_rag_17_iterations_scaling_wall.md"),
    Path("prd/research/habr_legal_rag_17_iterations_scaling_wall_assessment.md"),
    Path("prd/research/habr_legal_rag_processed_architecture_json_comparison.md"),
]
REQUIRED_S08_IDS = {
    "S07-FIXED-PRD-CONSISTENCY",
    "G-005",
    "G-008",
    "G-011",
    "G-015",
    "S04-FALKORDB-RUNTIME-BOUNDED",
    "S05-PARSER-ODT-BOUNDARY",
    "S05-OLD-PROJECT-PRIOR-ART",
    "S10-USER-BGE-M3-BASELINE",
    "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED",
    "M001-ARCHITECTURE-ONLY-GUARDRAIL",
}
REQUIRED_ITEM_IDS = {
    "REQ-R001",
    "REQ-R009",
    "REQ-R010",
    "REQ-R017",
    "REQ-R022",
    "REQ-R028",
    "REQ-R029",
    "DEC-D031",
    "DEC-D032",
    "GATE-G005",
    "GATE-G008",
    "GATE-G011",
    "GATE-G015",
    "S07-FIXED-PRD-CONSISTENCY",
    "S04-FALKORDB-RUNTIME-BOUNDED",
    "S05-PARSER-ODT-BOUNDARY",
    "S05-OLD-PROJECT-PRIOR-ART",
    "S10-USER-BGE-M3-BASELINE",
    "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED",
    "M001-ARCHITECTURE-ONLY-GUARDRAIL",
    "ASSUMP-PRD-SOURCE-TRUTH",
    "RISK-OVERCLAIM-RUNTIME",
    "CHECK-ARCHITECTURE-EXTRACTOR",
    "COMP-LEGAL-NEXUS-ORCHESTRATOR",
    "DATA-LEGAL-EVIDENCE-CORE",
    "DATA-TEMPORAL-PROPERTY-BUNDLE",
    "EVID-PARSER-CONSULTANT-CANDIDATES",
    "EVID-PARSER-CONSULTANT-HIERARCHY-PROOF",
    "EVID-PARSER-GOLDEN-TEST-PROOF",
    "EVID-PARSER-ODT-SMOKE",
    "EVID-PARSER-RECORD-CONTRACT",
    "EVID-PARSER-SOURCE-FIXTURE-INVENTORY",
    "EVID-PARSER-STAGING-GRAPH",
    "GATE-EMBEDDING-SUPPLY-CHAIN",
    "GATE-GENERATED-CYPHER-SAFETY",
    "GATE-LEGAL-NEXUS-ACCESS-CONTROL",
    "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS",
    "EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING",
    "QS-OBSERVABILITY-OPERABILITY-BASELINE",
    "REQ-TEMPORAL-STATUS-SEMANTICS",
}
COMMON_NON_CLAIMS = [
    "No legal-answer correctness claim.",
    "No product Legal KnowQL behavior claim.",
    "No parser completeness claim.",
    "No product retrieval quality claim.",
    "No managed embedding API fallback claim.",
    "No production-scale FalkorDB claim.",
    "No LLM legal authority claim.",
]


@dataclass(frozen=True)
class ExtractionConfig:
    root: Path
    items_path: Path
    edges_path: Path
    s08_findings_path: Path
    check: bool


class ExtractionError(Exception):
    """User-visible extraction failure."""


Record = dict[str, Any]


def anchor(path: str, kind: str, *, selector: str | None = None, section: str | None = None) -> Record:
    value: Record = {"path": path, "kind": kind}
    if section:
        value["section"] = section
    if selector:
        value["selector"] = selector
    return value


def item(
    record_id: str,
    item_type: str,
    title: str,
    summary: str,
    layer: str,
    status: str,
    proof_level: str,
    risk_level: str,
    source_anchors: list[Record],
    owner: str,
    verification: str,
    non_claims: list[str],
    **extra: Any,
) -> Record:
    record: Record = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "item",
        "id": record_id,
        "type": item_type,
        "title": title,
        "summary": summary,
        "layer": layer,
        "status": status,
        "proof_level": proof_level,
        "risk_level": risk_level,
        "source_anchors": source_anchors,
        "owner": owner,
        "verification": verification,
        "generated_draft": False,
        "non_claims": non_claims,
    }
    record.update(extra)
    return record


def edge(
    record_id: str,
    from_id: str,
    to_id: str,
    edge_type: str,
    status: str,
    rationale: str,
    source_anchors: list[Record],
    owner: str,
    *,
    verification: str | None = None,
    confidence: float | None = None,
    tags: list[str] | None = None,
) -> Record:
    record: Record = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "edge",
        "id": record_id,
        "from": from_id,
        "to": to_id,
        "type": edge_type,
        "status": status,
        "rationale": rationale,
        "source_anchors": source_anchors,
        "generated_draft": False,
        "owner": owner,
    }
    if verification:
        record["verification"] = verification
    if confidence is not None:
        record["confidence"] = confidence
    if tags:
        record["tags"] = tags
    return record


def load_s08_findings(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ExtractionError(f"missing required source for S08 findings mapping: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise ExtractionError(f"malformed source JSON in {path}: {exc.msg} at line {exc.lineno} column {exc.colno}") from exc
    if not isinstance(data, dict):
        raise ExtractionError(f"malformed source JSON in {path}: top-level value must be an object")
    findings = data.get("findings")
    if not isinstance(findings, list):
        raise ExtractionError(f"malformed source JSON in {path}: missing array field 'findings'")
    ids = {row.get("id") for row in findings if isinstance(row, dict)}
    missing = sorted(REQUIRED_S08_IDS - ids)
    if missing:
        raise ExtractionError(f"malformed source JSON in {path}: missing required finding IDs {', '.join(missing)}")
    return data


def validate_sources(config: ExtractionConfig) -> None:
    required_paths = list(REQUIRED_SOURCE_PATHS)
    if config.s08_findings_path != config.root / DEFAULT_S08_FINDINGS:
        required_paths = [path for path in required_paths if path != DEFAULT_S08_FINDINGS]
    for rel_path in required_paths:
        path = config.root / rel_path
        if not path.exists():
            raise ExtractionError(f"missing required source for curated architecture extraction: {rel_path}")
    load_s08_findings(config.s08_findings_path)


def requirement_items() -> list[Record]:
    def req_anchor(rid: str) -> list[Record]:
        return [anchor(".gsd/REQUIREMENTS.md", "gsd-requirement", selector=rid)]

    return [
        item(
            "REQ-R001",
            "requirement",
            "Architecture review finding classification",
            "Architecture review reports must classify PRD claims with severity, evidence, impact, recommendation, owner, and roadmap effect.",
            "architecture-governance",
            "active",
            "source-anchor",
            "medium",
            req_anchor("R001"),
            "M001/S08",
            "Review S08 final report and S08-FINDINGS.json before using architecture conclusions.",
            COMMON_NON_CLAIMS,
            lifecycle="maintaining",
            priority="high",
            tags=["R001", "M001", "S08"],
        ),
        item(
            "REQ-R009",
            "requirement",
            "Architecture findings require owner and verification criteria",
            "Discovered architecture issues must carry owner, resolution path, and verification criteria.",
            "workflow-governance",
            "active",
            "source-anchor",
            "high",
            req_anchor("R009"),
            "M001/S08",
            "Check generated items and S08 findings for owner, resolution, and verification text.",
            COMMON_NON_CLAIMS,
            lifecycle="maintaining",
            priority="high",
            tags=["R009", "issue-tracking"],
        ),
        item(
            "REQ-R010",
            "requirement",
            "Machine-readable architecture findings path",
            "Final architecture review must include a machine-readable findings path or schema proposal.",
            "architecture-governance",
            "active",
            "source-anchor",
            "medium",
            req_anchor("R010"),
            "M001/S08",
            "Confirm S08-FINDINGS.json remains parseable and represented in architecture registry records.",
            COMMON_NON_CLAIMS,
            lifecycle="maintaining",
            priority="high",
            related_artifacts=[".gsd/milestones/M001/slices/S08/S08-FINDINGS.json"],
            tags=["R010", "machine-readable"],
        ),
        item(
            "REQ-R017",
            "requirement",
            "Assess FalkorDB text-to-cypher PyO3 route",
            "Future generated-Cypher work must keep R017 active until product Legal KnowQL behavior is separately proven.",
            "generated-cypher",
            "active",
            "source-anchor",
            "high",
            req_anchor("R017"),
            "M003/S05",
            "Review M003 proof closure and future product Legal KnowQL validation evidence.",
            [
                "No product Legal KnowQL behavior claim.",
                "No legal-answer correctness claim.",
                "No live legal graph execution claim.",
                "No LLM legal authority claim.",
            ],
            lifecycle="maintaining",
            priority="high",
            tags=["R017", "M003", "generated-cypher"],
        ),
        item(
            "REQ-R022",
            "requirement",
            "Proof artifacts remain redacted and categorical",
            "Proof artifacts must avoid raw provider bodies, credentials, prompts, raw legal text, and raw FalkorDB rows.",
            "security-safety",
            "active",
            "source-anchor",
            "critical",
            req_anchor("R022"),
            "project-wide proof artifacts",
            "Inspect proof artifacts for categorical status and absence of raw provider/legal/runtime payloads.",
            [
                "No raw provider body persistence claim.",
                "No credential, prompt, raw legal text, or raw row emission claim.",
                "No legal-answer correctness claim.",
            ],
            lifecycle="maintaining",
            priority="critical",
            tags=["R022", "redaction", "proof-artifacts"],
        ),
        item(
            "REQ-R028",
            "requirement",
            "LLM output is not legal authority",
            "Generated Cypher and LLM output must not be treated as legal authority.",
            "security-safety",
            "out-of-scope",
            "source-anchor",
            "critical",
            req_anchor("R028"),
            "project-wide guardrail",
            "Future legal-answering work must cite deterministic source evidence rather than LLM authority.",
            [
                "No LLM legal authority claim.",
                "No legal-answer correctness claim.",
                "No generated Cypher authority claim.",
            ],
            lifecycle="maintaining",
            priority="critical",
            tags=["R028", "LLM", "non-authoritative"],
        ),
        item(
            "REQ-R029",
            "requirement",
            "Executable architecture verification workflow",
            "Architecture planning and review must validate architecture registry traceability, anchors, unresolved gates, and forbidden overclaims.",
            "architecture-governance",
            "active",
            "source-anchor",
            "high",
            req_anchor("R029"),
            "M004",
            "M004 verifier passes on schema, registry, graph, and overclaim checks.",
            ["Does not itself prove product runtime behavior."],
            lifecycle="implementing",
            priority="critical",
            stakeholders=["Future agents", "LegalGraph Nexus maintainers"],
            tags=["R029", "M004"],
        ),
    ]


def decision_items() -> list[Record]:
    return [
        item(
            "DEC-D031",
            "decision",
            "Use docs-as-code architecture registry",
            "Use JSONL architecture item and edge records generated from PRD/GSD/ADR sources, analyzed through NetworkX, and verified by executable checks.",
            "architecture-governance",
            "active",
            "source-anchor",
            "high",
            [
                anchor(".gsd/DECISIONS.md", "gsd-decision", selector="D031"),
                anchor("prd/09_architecture_planning_verification_research.md", "prd", section="Current GSD recording"),
            ],
            "M004",
            "Architecture registry extractor/checks, graph builder, and verifier pass.",
            ["JSONL and GraphML are not source-of-truth replacements."],
            deciders=["human", "gsd-agent"],
            stakeholders=["Future agents", "LegalGraph Nexus maintainers"],
            priority="critical",
            lifecycle="implementing",
            decision_drivers=["Prevent architecture overclaims", "Make traceability executable", "Keep PRD/GSD/ADR evidence authoritative"],
            considered_options=[
                {
                    "id": "OPT-D031-docs-as-code",
                    "title": "Docs-as-code registry",
                    "summary": "Use tracked JSONL plus verifier as a derived projection.",
                    "status": "chosen",
                    "pros": ["Reviewable in git", "Machine-checkable"],
                    "cons": ["Requires schema and verifier maintenance"],
                },
                {
                    "id": "OPT-D031-gsd-only",
                    "title": "GSD-only architecture state",
                    "summary": "Keep architecture state only in GSD artifacts and memory.",
                    "status": "rejected",
                    "pros": ["No new projection format"],
                    "cons": ["Harder to review through git because .gsd is symlinked"],
                },
            ],
            positive_consequences=["Architecture claims become traceable and checkable."],
            negative_consequences=["Schema drift must be controlled by tests."],
            assumptions=["Tracked prd/architecture artifacts can be reviewed safely in git."],
            constraints=["Do not treat derived graph artifacts as authoritative."],
            implications=["Future architecture changes should update the registry or source anchors."],
            related_requirements=["REQ-R029"],
            governed_artifacts=["prd/architecture/architecture_items.jsonl", "prd/architecture/architecture_edges.jsonl", "scripts/verify-architecture-graph.py"],
            last_reviewed="2026-05-10",
            tags=["D031", "architecture-registry"],
        ),
        item(
            "DEC-D032",
            "decision",
            "Add architecture verification router skill in S05",
            "Create a compact project-local legalgraph-architecture-verification router skill after the schema and verifier stabilize.",
            "workflow-governance",
            "active",
            "source-anchor",
            "medium",
            [
                anchor(".gsd/DECISIONS.md", "gsd-decision", selector="D032"),
                anchor("prd/09_architecture_planning_verification_research.md", "prd", section="Current GSD recording"),
            ],
            "M004/S05",
            "S05 skill consistency test passes and references current verifier paths.",
            ["The skill is guidance, not a source of truth."],
            deciders=["human", "gsd-agent"],
            stakeholders=["Future agents"],
            priority="medium",
            lifecycle="implementing",
            decision_drivers=["Reduce cross-agent drift", "Avoid premature schema duplication"],
            considered_options=[
                {
                    "id": "OPT-D032-s05-skill",
                    "title": "Create skill in S05",
                    "summary": "Wait until schema and verifier stabilize.",
                    "status": "chosen",
                    "pros": ["Avoids stale field names", "References real commands"],
                    "cons": ["Skill arrives late in milestone"],
                },
                {
                    "id": "OPT-D032-now",
                    "title": "Create skill immediately",
                    "summary": "Write guidance before schema and verifier exist.",
                    "status": "rejected",
                    "pros": ["Earlier routing"],
                    "cons": ["High drift risk"],
                },
            ],
            positive_consequences=["Future architecture work has a compact router."],
            negative_consequences=["S05 must maintain skill consistency checks."],
            related_requirements=["REQ-R029"],
            governed_artifacts=[".agents/skills/legalgraph-architecture-verification/SKILL.md"],
            last_reviewed="2026-05-10",
            tags=["D032", "skill"],
        ),
    ]


def proof_gate_items() -> list[Record]:
    def prd_anchor(gate: str) -> list[Record]:
        return [anchor("prd/04_review_findings.md", "prd", selector=gate)]

    return [
        item(
            "GATE-G005",
            "proof_gate",
            "Temporal same-date multi-edition conflict policy",
            "Temporal same-date and multi-edition legal conflict policy remains unresolved and must stay visible.",
            "temporal-model",
            "active",
            "none",
            "high",
            prd_anchor("G-005"),
            "future-temporal-proof",
            "A future proof slice defines and verifies same-date/multi-edition conflict policy.",
            ["Does not validate temporal conflict resolution."],
            lifecycle="researching",
            priority="high",
            tags=["G-005"],
        ),
        item(
            "GATE-G008",
            "proof_gate",
            "Product parser and retrieval readiness gate",
            "M008 validates a bounded executable golden-test harness, but product parser completeness, citation-safe retrieval, and retrieval quality remain unresolved.",
            "parser-ingestion",
            "active",
            "none",
            "high",
            prd_anchor("G-008"),
            "future-product-parser-retrieval-proof",
            "Future product proof demonstrates parser completeness boundaries, citation-safe retrieval behavior, and retrieval quality over real legal source fixtures.",
            ["No parser completeness claim.", "No product retrieval quality claim."],
            lifecycle="researching",
            priority="high",
            tags=["G-008"],
        ),
        item(
            "GATE-G011",
            "proof_gate",
            "Local embedding quality proof",
            "Local embedding baseline is bounded and still needs product retrieval quality proof.",
            "retrieval-embedding",
            "active",
            "none",
            "high",
            prd_anchor("G-011"),
            "future-retrieval-quality-proof",
            "Retrieval quality benchmark passes under local/open-weight embedding constraints.",
            ["No product retrieval quality claim.", "No managed embedding API fallback claim."],
            lifecycle="researching",
            priority="high",
            tags=["G-011"],
        ),
        item(
            "GATE-G015",
            "proof_gate",
            "FalkorDBLite to Docker migration runbook",
            "FalkorDBLite to Docker migration remains a deployment/operability proof gate.",
            "graph-runtime",
            "active",
            "none",
            "medium",
            prd_anchor("G-015"),
            "future-runtime-migration-proof",
            "Migration runbook is executed against bounded fixtures and runtime diagnostics.",
            ["No production-scale FalkorDB claim."],
            lifecycle="researching",
            priority="medium",
            tags=["G-015"],
        ),
    ]


def product_coverage_items() -> list[Record]:
    return [
        item(
            "DATA-LEGAL-EVIDENCE-CORE",
            "data_entity",
            "Core legal evidence entities",
            "LegalAct, ActEdition, SourceDocument, SourceBlock, EvidenceSpan, and NormStatement are core source-backed concepts to be represented before product extraction or retrieval claims are upgraded.",
            "legal-evidence",
            "active",
            "source-anchor",
            "high",
            [
                anchor("prd/01_general_idea.md", "prd", selector="Evidence layer: EvidenceSpan"),
                anchor("prd/03_PRD.md", "prd", selector="EvidenceSpan"),
                anchor("prd/06_m002_cypher_safety_contract.md", "prd", selector="EvidenceSpan"),
            ],
            "future-legal-evidence-model",
            "Future implementation records concrete graph schema fields and validates source/evidence linkage on real parser outputs.",
            [
                "Does not assert final legal graph schema completeness.",
                "Does not prove legal-answer correctness.",
                "Does not prove parser completeness.",
            ],
            lifecycle="researching",
            priority="high",
            tags=["R04-REC-001", "R04-GAP-002", "legal-evidence"],
        ),
        item(
            "COMP-LEGAL-NEXUS-ORCHESTRATOR",
            "component",
            "Legal Nexus orchestrator component boundary",
            "Legal Nexus is the planned Python orchestration boundary for deterministic lookup, Legal KnowQL parsing, policy checks, and FalkorDB access.",
            "api-product",
            "active",
            "source-anchor",
            "high",
            [
                anchor("prd/01_general_idea.md", "prd", selector="Legal Nexus реализован как Python-модуль"),
                anchor("prd/03_PRD.md", "prd", selector="Legal Nexus Module"),
            ],
            "future-api-product-design",
            "Future implementation defines public API methods, access-control boundaries, and runtime diagnostics before product claims.",
            [
                "Does not implement Legal Nexus runtime behavior.",
                "Does not prove product Legal KnowQL behavior.",
                "Does not prove access-control enforcement.",
            ],
            lifecycle="researching",
            priority="high",
            governed_artifacts=["prd/01_general_idea.md", "prd/03_PRD.md"],
            tags=["R04-REC-001", "R04-GAP-003", "LegalNexus"],
        ),
        item(
            "QS-OBSERVABILITY-OPERABILITY-BASELINE",
            "quality_scenario",
            "Deterministic observability and auditability baseline",
            "Architecture work must preserve deterministic diagnostics, auditability, and explicit non-claim surfaces before runtime services are promoted.",
            "observability-operability",
            "active",
            "source-anchor",
            "medium",
            [
                anchor("prd/03_PRD.md", "prd", selector="NFR-2"),
                anchor("prd/03_PRD.md", "prd", selector="operational tests"),
            ],
            "future-operability-proof",
            "Future implementation defines measurable audit/latency/failure-state checks and verifies them against runtime surfaces.",
            [
                "Does not prove runtime SLOs.",
                "Does not prove production observability.",
                "Does not prove legal-answer correctness.",
            ],
            lifecycle="researching",
            priority="medium",
            tags=["R04-REC-001", "R04-GAP-004", "observability"],
        ),
        item(
            "GATE-GENERATED-CYPHER-SAFETY",
            "proof_gate",
            "Generated-Cypher safety and validation gate",
            "Generated-Cypher planning records a safety gate for read-only, schema-grounded, evidence-returning, deterministic validation before any future execution path.",
            "generated-cypher",
            "active",
            "none",
            "critical",
            [anchor("prd/06_m002_cypher_safety_contract.md", "prd", selector="Generated-Cypher Safety Contract")],
            "future-generated-cypher-safety-proof",
            "A future product proof demonstrates validator acceptance/rejection behavior across representative Legal KnowQL tasks and live graph schemas.",
            [
                "Does not prove provider generation quality.",
                "Does not prove production Legal KnowQL behavior.",
                "Does not authorize executing raw generated Cypher.",
            ],
            lifecycle="researching",
            priority="critical",
            tags=["R04-REC-003", "R017", "generated-cypher"],
        ),
        item(
            "GATE-LEGAL-NEXUS-ACCESS-CONTROL",
            "proof_gate",
            "Legal Nexus access-control proof gate",
            "Legal Nexus API access control, authentication, and authorization remain unproven product surfaces until explicit runtime checks exist.",
            "security-safety",
            "active",
            "none",
            "high",
            [anchor("prd/03_PRD.md", "prd", selector="Legal Nexus Module")],
            "future-api-security-proof",
            "Future security proof defines caller boundaries, authorization policy, audit logging, and denial diagnostics for Legal Nexus operations.",
            [
                "Does not assert current product is insecure.",
                "Does not prove access-control enforcement.",
                "Does not define a production API surface.",
            ],
            lifecycle="researching",
            priority="high",
            tags=["R04-REC-003", "access-control"],
        ),
        item(
            "GATE-EMBEDDING-SUPPLY-CHAIN",
            "proof_gate",
            "Embedding model supply-chain integrity gate",
            "Local/open-weight embedding candidates require provenance, artifact integrity, resource, and leakage checks before promotion.",
            "security-safety",
            "active",
            "none",
            "high",
            [
                anchor("prd/03_PRD.md", "prd", selector="FR-28b"),
                anchor(".gsd/PROJECT.md", "gsd-summary", selector="embedding"),
            ],
            "future-embedding-supply-chain-proof",
            "Future embedding proof records model source, checksum or revision, local runtime envelope, vector dimension, and no-secret/no-raw-vector leakage checks.",
            [
                "Does not promote any embedding model to product default.",
                "Does not allow managed embedding API fallback.",
                "Does not prove product retrieval quality.",
            ],
            lifecycle="researching",
            priority="high",
            tags=["R04-REC-003", "embedding", "supply-chain"],
        ),
        item(
            "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS",
            "evidence",
            "GraphRAG/FalkorDB mathematical analysis research input",
            "Imported research argues for deterministic graph pre-filtering, temporal legal graph reasoning, and graph algorithms before LLM synthesis, but remains a non-authoritative planning input.",
            "retrieval-embedding",
            "bounded-evidence",
            "source-anchor",
            "high",
            [
                anchor("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis.md", "manual-note"),
                anchor("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis_assessment.md", "manual-note"),
            ],
            "M011/S01",
            "Assessment classifies ideas into applicable-now principles, proof-gated candidates, and deferred/not-adopted claims; future proof must validate any runtime, SDK, benchmark, or retrieval-quality claim.",
            [
                "Does not prove product retrieval quality.",
                "Does not prove FalkorDB production-scale behavior.",
                "Does not prove GraphRAG-SDK compatibility.",
                "Does not validate benchmark, cost, or latency claims.",
                "Does not prove legal-answer correctness.",
            ],
            lifecycle="researching",
            priority="high",
            related_artifacts=["prd/research/graph_agent_knowledge_bases_falkordb_math_analysis_assessment.md"],
            tags=["M011", "GraphRAG", "FalkorDB", "research", "bounded"],
        ),
        item(
            "EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING",
            "evidence",
            "Habr Legal RAG iteration and scaling research input",
            "Imported Habr case study highlights format-first validation, citation precision, graph-constrained retrieval, no-answer evaluation, and scale/noise testing as proof-required candidates for LegalGraph Nexus.",
            "retrieval-embedding",
            "bounded-evidence",
            "source-anchor",
            "high",
            [
                anchor("prd/research/habr_legal_rag_17_iterations_scaling_wall.md", "manual-note"),
                anchor("prd/research/habr_legal_rag_17_iterations_scaling_wall_assessment.md", "manual-note"),
                anchor("prd/research/habr_legal_rag_processed_architecture_json_comparison.md", "manual-note", section="Corrected Bottom Line"),
            ],
            "D045 / future-retrieval-quality-proof",
            "Human-reviewed JSON comparison classifies all transferable ideas as requiring project-specific verification before adoption; future proof must validate retrieval IDs, evidence precision, no-answer behavior, scale/noise degradation, and any runtime or model claim.",
            [
                "Does not prove product retrieval quality.",
                "Does not prove parser completeness.",
                "Does not prove legal-answer correctness.",
                "Does not prove FalkorDB runtime/vector/full-text/rerank behavior.",
                "Does not authorize generated Cypher execution.",
            ],
            lifecycle="researching",
            priority="high",
            related_artifacts=[
                "prd/research/habr_legal_rag_17_iterations_scaling_wall_assessment.md",
                "prd/research/habr_legal_rag_processed_architecture_json_comparison.md",
            ],
            tags=["D045", "Habr", "LegalRAG", "retrieval", "research", "bounded"],
        ),
        item(
            "EVID-PARSER-SOURCE-FIXTURE-INVENTORY",
            "evidence",
            "Parser source fixture inventory evidence",
            "M006 fixture inventory establishes canonical parser source paths and hygiene diagnostics for downstream parser work.",
            "parser-ingestion",
            "bounded-evidence",
            "static-check",
            "medium",
            [anchor("prd/parser/source_fixture_inventory.md", "manual-note", selector="Parser Source Fixture Inventory")],
            "M006/S01",
            "`uv run python scripts/inventory-parser-fixtures.py --check` verifies fixture inventory freshness and hygiene.",
            ["Does not prove parser completeness.", "Does not prove legal correctness."],
            lifecycle="maintaining",
            tags=["M006", "parser", "R04-REC-005"],
        ),
        item(
            "EVID-PARSER-RECORD-CONTRACT",
            "evidence",
            "Parser record contract evidence",
            "Typed parser records define deterministic non-authoritative DocumentRecord, SourceBlockRecord, and RelationCandidateRecord boundaries.",
            "parser-ingestion",
            "bounded-evidence",
            "static-check",
            "medium",
            [anchor("prd/parser/parser_record_contract.md", "manual-note", selector="Parser Record Contract")],
            "M006/S02",
            "`uv run python scripts/validate-parser-records.py --check` verifies schemas, examples, and contract freshness.",
            ["Does not prove product ETL readiness.", "Does not prove parser completeness."],
            lifecycle="maintaining",
            tags=["M006", "parser-records", "R04-REC-005"],
        ),
        item(
            "EVID-PARSER-ODT-SMOKE",
            "evidence",
            "Bounded ODT smoke-record evidence",
            "Tracked ODT smoke records preserve raw content.xml order and capped SourceBlockRecord rows for canonical Garant ODT fixtures.",
            "parser-ingestion",
            "bounded-evidence",
            "real-document-proof",
            "high",
            [anchor("prd/parser/odt_smoke_records.md", "manual-note", selector="ODT Smoke Parser Records")],
            "M006/S03",
            "`uv run python scripts/build-odt-smoke-records.py --check` verifies ODT smoke artifact freshness.",
            ["No final legal hierarchy extraction claim.", "No parser completeness claim."],
            lifecycle="maintaining",
            priority="high",
            tags=["M006", "ODT", "R04-REC-005"],
        ),
        item(
            "EVID-PARSER-CONSULTANT-CANDIDATES",
            "evidence",
            "Consultant relation-candidate evidence",
            "Tracked Consultant WordML relation-candidate artifacts preserve candidate relation identity without asserting legal relation correctness.",
            "parser-ingestion",
            "bounded-evidence",
            "static-check",
            "medium",
            [anchor("prd/parser/consultant_relation_candidates.md", "manual-note", selector="Consultant WordML Relation Candidates")],
            "M006/S04",
            "`uv run python scripts/build-consultant-relation-candidates.py --check` verifies Consultant candidate artifact freshness.",
            ["Does not prove Consultant relation correctness.", "Does not prove parser completeness."],
            lifecycle="maintaining",
            tags=["M006", "Consultant", "R04-REC-005"],
        ),
        item(
            "EVID-PARSER-STAGING-GRAPH",
            "evidence",
            "Parser NetworkX staging graph evidence",
            "The NetworkX staging graph preserves validated parser JSONL records and keyed relation-candidate edges without loading FalkorDB.",
            "parser-ingestion",
            "bounded-evidence",
            "static-check",
            "medium",
            [anchor("prd/parser/parser_staging_graph.md", "manual-note", selector="Parser Staging Graph")],
            "M006/S05",
            "`uv run python scripts/build-parser-staging-graph.py --check` verifies staging graph freshness and invariants.",
            ["Does not prove FalkorDB loading/runtime behavior.", "Does not prove legal-answer correctness."],
            lifecycle="maintaining",
            tags=["M006", "NetworkX", "R04-REC-005"],
        ),
        item(
            "EVID-PARSER-GOLDEN-TEST-PROOF",
            "evidence",
            "Bounded parser/retrieval golden-test proof",
            "M008 establishes an executable five-case golden-test harness over tracked M006 parser artifacts with fail-closed evaluator behavior and explicit non-authoritative boundaries.",
            "parser-ingestion",
            "bounded-evidence",
            "unit-test",
            "medium",
            [
                anchor("prd/parser/golden_test_proof_report.md", "manual-note"),
                anchor(".gsd/milestones/M008/M008-SUMMARY.md", "gsd-summary"),
            ],
            "M008",
            "`.venv/bin/python3 -m pytest tests/test_parser_golden_contract.py tests/test_parser_golden_cases.py tests/test_parser_golden_evaluator.py tests/test_parser_golden_proof_report.py` and evaluator `--check` evidence pass for bounded scope.",
            [
                "Does not prove parser completeness.",
                "Does not prove product retrieval quality.",
                "Does not prove citation-safe retrieval readiness.",
                "Does not prove legal-answer correctness.",
                "Does not prove FalkorDB loading/runtime behavior.",
            ],
            lifecycle="maintaining",
            priority="medium",
            related_requirements=["REQ-R032"],
            tags=["M008", "golden-tests", "bounded"],
        ),
        item(
            "EVID-PARSER-CONSULTANT-HIERARCHY-PROOF",
            "evidence",
            "Consultant full-act hierarchy parser proof",
            "M009 establishes Consultant Plus WordML as the primary full-normative-act parser source for a single 44-FZ tracer and emits 2185 bounded hierarchy records with provenance and proof-package guardrails.",
            "parser-ingestion",
            "bounded-evidence",
            "real-document-proof",
            "medium",
            [
                anchor("prd/parser/consultant_parser_proof.md", "manual-note"),
                anchor("prd/parser/consultant_hierarchy_records.md", "manual-note"),
                anchor(".gsd/milestones/M009/M009-SUMMARY.md", "gsd-summary"),
            ],
            "M009",
            "`build-consultant-hierarchy-records.py --check`, prior-art comparison `--check`, and `test_consultant_parser_proof.py` pass for the Consultant-primary/Garant-deferred bounded proof package.",
            [
                "Does not prove multi-document Consultant expansion.",
                "Does not prove Garant ODT parser regression.",
                "Does not prove parser completeness.",
                "Does not prove product ETL readiness.",
                "Does not prove FalkorDB loading/runtime behavior.",
            ],
            lifecycle="maintaining",
            priority="medium",
            related_requirements=["REQ-R015", "REQ-R033"],
            tags=["M009", "Consultant", "hierarchy", "bounded"],
        ),
        item(
            "DATA-TEMPORAL-PROPERTY-BUNDLE",
            "data_entity",
            "Temporal property bundle",
            "Edition date, validity period, effective period, status, and temporal confidence are central temporal semantics for LegalGraph records.",
            "temporal-model",
            "active",
            "source-anchor",
            "high",
            [
                anchor("prd/01_general_idea.md", "prd", selector="edition_date"),
                anchor("prd/03_PRD.md", "prd", selector="edition_date"),
                anchor("prd/06_m002_cypher_safety_contract.md", "prd", selector="temporal field names"),
            ],
            "future-temporal-proof",
            "Future temporal proof validates field semantics on real document editions and query-time as-of behavior.",
            ["Does not specify temporal storage implementation.", "Does not validate temporal conflict resolution."],
            lifecycle="researching",
            priority="high",
            tags=["R04-REC-006", "temporal"],
        ),
        item(
            "REQ-TEMPORAL-STATUS-SEMANTICS",
            "requirement",
            "Temporal status semantics remain explicit",
            "LegalGraph records must preserve temporal status semantics and avoid mutating prior source revisions when editions or source hashes change.",
            "temporal-model",
            "active",
            "source-anchor",
            "high",
            [
                anchor("prd/03_PRD.md", "prd", selector="Changed `sha256`"),
                anchor("prd/03_PRD.md", "prd", selector="New `edition_date`"),
            ],
            "future-temporal-proof",
            "Future implementation verifies idempotent replay, changed-source revision handling, and new-edition behavior on fixture imports.",
            ["Does not prove import runtime behavior.", "Does not validate same-date conflict policy."],
            lifecycle="researching",
            priority="high",
            tags=["R04-REC-006", "temporal", "status"],
        ),
    ]


def evidence_and_governance_items() -> list[Record]:
    s08 = anchor(".gsd/milestones/M001/slices/S08/S08-FINDINGS.json", "gsd-summary")
    return [
        item(
            "ASSUMP-PRD-SOURCE-TRUTH",
            "assumption",
            "PRD and GSD artifacts remain source of truth",
            "Architecture registry JSONL remains a derived projection over PRD, GSD, ADR, source, and runtime evidence.",
            "architecture-governance",
            "active",
            "source-anchor",
            "high",
            [anchor("prd/09_architecture_planning_verification_research.md", "prd", section="Recommendation")],
            "M004",
            "Verifier rejects records or docs that claim JSONL/GraphML are authoritative over source docs.",
            ["Does not make generated artifacts authoritative."],
            lifecycle="maintaining",
            priority="critical",
            tags=["source-of-truth"],
        ),
        item(
            "RISK-OVERCLAIM-RUNTIME",
            "risk",
            "Runtime and legal overclaim risk",
            "Architecture documentation can drift into claiming product/runtime/legal behavior not proven by source, runtime, or real-document evidence.",
            "security-safety",
            "active",
            "source-anchor",
            "critical",
            [anchor("prd/09_architecture_planning_verification_research.md", "prd", section="LegalGraph Nexus-specific implications")],
            "M004/S04",
            "Verifier fails forbidden FalkorDB/vector/full-text/UDF/ODT/parser/retrieval/legal-answer overclaims.",
            ["Risk item does not assert current product failure."],
            lifecycle="maintaining",
            priority="critical",
            tags=["overclaim", "safety"],
        ),
        item(
            "CHECK-ARCHITECTURE-EXTRACTOR",
            "workflow_check",
            "Deterministic architecture extractor check",
            "The S02 extractor check reports stale generated JSONL, missing anchors, malformed S08 JSON, and unsafe status/proof mappings.",
            "workflow-governance",
            "active",
            "static-check",
            "high",
            [anchor(".gsd/milestones/M004/slices/S02/S02-PLAN.md", "gsd-summary", section="Verification")],
            "M004/S02",
            "`uv run python scripts/extract-prd-architecture-items.py --check` exits zero on current generated outputs.",
            ["Extractor check is not product runtime proof."],
            lifecycle="implementing",
            priority="high",
            governed_artifacts=["scripts/extract-prd-architecture-items.py", "prd/architecture/architecture_items.jsonl", "prd/architecture/architecture_edges.jsonl"],
            tags=["extractor", "S02"],
        ),
        item(
            "S07-FIXED-PRD-CONSISTENCY",
            "evidence",
            "S07 PRD consistency closure",
            "S07 fixed PRD consistency blockers and major specification mismatches before final architecture reporting.",
            "architecture-governance",
            "bounded-evidence",
            "source-anchor",
            "low",
            [s08, anchor("prd/04_review_findings.md", "prd", section="S07 final status and S08 handoff")],
            "S08 final architecture review",
            "Final report distinguishes fixed PRD consistency work from deferred proof gates.",
            ["Does not prove product behavior."],
            lifecycle="maintaining",
            tags=["S07", "fixed"],
        ),
        item(
            "S04-FALKORDB-RUNTIME-BOUNDED",
            "evidence",
            "FalkorDB runtime mechanics smoke boundary",
            "S04 confirms bounded FalkorDB and FalkorDBLite mechanics only within synthetic smoke probes.",
            "graph-runtime",
            "bounded-evidence",
            "runtime-smoke",
            "medium",
            [s08, anchor(".gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json", "runtime-artifact")],
            "S04 evidence owner / S08 final report",
            "S04 verifier passes and S08 labels claims as bounded runtime mechanics.",
            ["No production-scale FalkorDB claim.", "No legal retrieval quality claim.", "No direct LegalGraph GraphBLAS API/control surface claim."],
            lifecycle="maintaining",
            tags=["S04", "FalkorDB", "bounded"],
        ),
        item(
            "S05-PARSER-ODT-BOUNDARY",
            "evidence",
            "Real ODT parser evidence boundary",
            "Real ODT parser evidence favors odfdo investigation but does not prove product extraction.",
            "parser-ingestion",
            "bounded-evidence",
            "real-document-proof",
            "high",
            [s08, anchor(".gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md", "gsd-summary")],
            "S05/S08 parser evidence consolidation",
            "S05 verifier passes; future parser tests prove final extraction behavior before promotion.",
            ["No final legal hierarchy extraction claim.", "No parser completeness claim.", "No production SourceBlock/EvidenceSpan creation claim."],
            lifecycle="maintaining",
            priority="high",
            tags=["S05", "ODT", "bounded"],
        ),
        item(
            "S05-OLD-PROJECT-PRIOR-ART",
            "evidence",
            "Old_project artifacts remain prior art",
            "Old_project candidates are adapt/defer or reject/defer; none are accepted unchanged for current Garant ODT behavior.",
            "parser-ingestion",
            "bounded-evidence",
            "source-anchor",
            "high",
            [s08, anchor(".gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md", "gsd-summary")],
            "S08 final architecture review / future parser owners",
            "Downstream designs classify legacy reuse as prior art and avoid blessing ConsultantPlus behavior for Garant ODT.",
            ["No Old_project artifact accepted unchanged.", "No parser completeness claim."],
            lifecycle="maintaining",
            priority="high",
            tags=["Old_project", "prior-art"],
        ),
        item(
            "S10-USER-BGE-M3-BASELINE",
            "evidence",
            "USER-bge-m3 bounded local embedding baseline",
            "USER-bge-m3 is a bounded local/open-weight runtime embedding baseline with 1024-dimensional FalkorDB vector proof on this host.",
            "retrieval-embedding",
            "bounded-evidence",
            "runtime-smoke",
            "medium",
            [s08, anchor(".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json", "runtime-artifact")],
            "S10 evidence owner / future embedding proof owner",
            "Future embedding proof repeats runtime on target hardware and adds real EvidenceSpan/SourceBlock evaluation.",
            ["No product retrieval quality claim.", "No managed embedding API fallback claim.", "No raw embedding leakage claim beyond verifier scope."],
            lifecycle="maintaining",
            tags=["S10", "USER-bge-m3", "bounded"],
        ),
        item(
            "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED",
            "evidence",
            "GigaEmbeddings challenger blocked by environment and safety gates",
            "GigaEmbeddings remains a blocked local challenger, not a default or managed fallback.",
            "retrieval-embedding",
            "blocked",
            "none",
            "medium",
            [s08, anchor(".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json", "runtime-artifact")],
            "Future embedding/runtime proof",
            "Challenger proof records gate approvals, runtime status, vector dimension, resource envelope, and retrieval metrics before promotion.",
            ["No managed embedding API fallback claim.", "No default promotion while blocked-environment.", "No product retrieval quality claim."],
            lifecycle="researching",
            tags=["S10", "GigaEmbeddings", "blocked"],
        ),
        item(
            "M001-ARCHITECTURE-ONLY-GUARDRAIL",
            "workflow_check",
            "M001 architecture-only guardrail",
            "M001 remains architecture-only and must not ship product runtime behavior.",
            "architecture-governance",
            "out-of-scope",
            "source-anchor",
            "critical",
            [s08, anchor(".gsd/REQUIREMENTS.md", "gsd-requirement", selector="R011")],
            "S08 final architecture review",
            "S08 verifier rejects overclaim markers that promote architecture findings into product runtime or legal-quality claims.",
            ["No product ETL.", "No production graph schema.", "No LegalNexus API.", "No KnowQL parser.", "No hybrid retrieval.", "No legal-answering runtime."],
            lifecycle="maintaining",
            priority="critical",
            tags=["M001", "architecture-only", "guardrail"],
        ),
    ]


def build_items() -> list[Record]:
    records = requirement_items() + decision_items() + proof_gate_items() + product_coverage_items() + evidence_and_governance_items()
    ids = {record["id"] for record in records}
    missing = sorted(REQUIRED_ITEM_IDS - ids)
    if missing:
        raise ExtractionError(f"extractor mapping missing required item IDs: {', '.join(missing)}")
    if any(record["status"] == "validated" for record in records):
        bad = sorted(record["id"] for record in records if record["status"] == "validated")
        raise ExtractionError(f"unsafe status/proof mapping: extractor must not emit validated items: {', '.join(bad)}")
    return sorted(records, key=lambda record: str(record["id"]))


def build_edges() -> list[Record]:
    edges = [
        edge(
            "EDGE-DEC-D031-SATISFIES-REQ-R029",
            "DEC-D031",
            "REQ-R029",
            "satisfies",
            "active",
            "The docs-as-code architecture registry decision is the chosen approach for executable architecture verification.",
            [anchor(".gsd/DECISIONS.md", "gsd-decision", selector="D031"), anchor(".gsd/REQUIREMENTS.md", "gsd-requirement", selector="R029")],
            "M004",
            verification="Registry schema/extractor/verifier workflow passes.",
            confidence=0.95,
            tags=["traceability"],
        ),
        edge(
            "EDGE-DEC-D031-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
            "DEC-D031",
            "CHECK-ARCHITECTURE-EXTRACTOR",
            "checked_by",
            "active",
            "The high-risk architecture registry decision is checked by the deterministic extractor drift check in S02.",
            [anchor(".gsd/milestones/M004/slices/S02/S02-PLAN.md", "gsd-summary", section="Verification")],
            "M004/S02",
            verification="`uv run python scripts/extract-prd-architecture-items.py --check` passes.",
            confidence=0.9,
            tags=["fitness-function", "D031"],
        ),
        edge(
            "EDGE-DEC-D032-DEPENDS-ON-DEC-D031",
            "DEC-D032",
            "DEC-D031",
            "depends_on",
            "active",
            "The architecture verification skill should be created only after the registry contract and verifier workflow exist.",
            [anchor(".gsd/DECISIONS.md", "gsd-decision", selector="D032")],
            "M004/S05",
            confidence=0.9,
            tags=["skill", "dependency"],
        ),
        edge(
            "EDGE-REQ-R001-EVIDENCED-BY-S07-FIXED-PRD-CONSISTENCY",
            "REQ-R001",
            "S07-FIXED-PRD-CONSISTENCY",
            "evidenced_by",
            "active",
            "S07/S08 final report evidence supports architecture finding classification within M001 scope.",
            [anchor(".gsd/milestones/M001/slices/S08/S08-FINDINGS.json", "gsd-summary", selector="S07-FIXED-PRD-CONSISTENCY")],
            "M001/S08",
            confidence=0.85,
            tags=["R001", "S08"],
        ),
        edge(
            "EDGE-REQ-R009-EVIDENCED-BY-S08-FINDINGS",
            "REQ-R009",
            "S07-FIXED-PRD-CONSISTENCY",
            "evidenced_by",
            "active",
            "S08 findings rows preserve owner, resolution path, verification criteria, and roadmap effect for architecture issues.",
            [anchor(".gsd/milestones/M001/slices/S08/S08-FINDINGS.json", "gsd-summary")],
            "M001/S08",
            confidence=0.85,
            tags=["R009"],
        ),
        edge(
            "EDGE-REQ-R010-EVIDENCED-BY-S08-FINDINGS",
            "REQ-R010",
            "S07-FIXED-PRD-CONSISTENCY",
            "evidenced_by",
            "active",
            "S08 produced a machine-readable findings path and schema proposal consumed by this extractor.",
            [anchor(".gsd/milestones/M001/slices/S08/S08-FINDINGS.json", "gsd-summary")],
            "M001/S08",
            confidence=0.85,
            tags=["R010"],
        ),
        edge(
            "EDGE-REQ-R017-BOUNDED-BY-R028",
            "REQ-R017",
            "REQ-R028",
            "bounded_by",
            "active",
            "Generated Cypher proof work remains bounded by the non-authoritative LLM/legal authority guardrail.",
            [anchor(".gsd/REQUIREMENTS.md", "gsd-requirement", selector="R028")],
            "project-wide guardrail",
            confidence=0.9,
            tags=["R017", "R028", "non-claim"],
        ),
        edge(
            "EDGE-REQ-R022-BOUNDS-S04-FALKORDB-RUNTIME-BOUNDED",
            "REQ-R022",
            "S04-FALKORDB-RUNTIME-BOUNDED",
            "bounded_by",
            "active",
            "Runtime proof artifacts must remain categorical and avoid raw sensitive/provider/legal payloads.",
            [anchor(".gsd/REQUIREMENTS.md", "gsd-requirement", selector="R022")],
            "project-wide proof artifacts",
            confidence=0.85,
            tags=["redaction"],
        ),
        edge(
            "EDGE-GATE-G005-BLOCKS-TEMPORAL-VALIDATION",
            "GATE-G005",
            "REQ-R029",
            "blocks",
            "active",
            "Unresolved temporal conflict policy must remain visible in architecture verification outputs.",
            [anchor("prd/04_review_findings.md", "prd", selector="G-005")],
            "future-temporal-proof",
            confidence=0.75,
            tags=["G-005"],
        ),
        edge(
            "EDGE-GATE-G008-BLOCKS-PARSER-RETRIEVAL-PROOF",
            "GATE-G008",
            "REQ-R029",
            "blocks",
            "active",
            "Product parser/retrieval readiness gaps must remain explicit even after M008 bounded golden-test harness proof.",
            [anchor("prd/04_review_findings.md", "prd", selector="G-008"), anchor(".gsd/milestones/M008/M008-SUMMARY.md", "gsd-summary")],
            "future-product-parser-retrieval-proof",
            confidence=0.75,
            tags=["G-008", "M008"],
        ),
        edge(
            "EDGE-GATE-G011-BLOCKS-RETRIEVAL-QUALITY-CLAIMS",
            "GATE-G011",
            "REQ-R029",
            "blocks",
            "active",
            "Local embedding evidence remains bounded and cannot validate product retrieval quality without benchmarks.",
            [anchor("prd/04_review_findings.md", "prd", selector="G-011")],
            "future-retrieval-quality-proof",
            confidence=0.75,
            tags=["G-011"],
        ),
        edge(
            "EDGE-GATE-G015-BLOCKS-RUNTIME-MIGRATION-CLAIMS",
            "GATE-G015",
            "REQ-R029",
            "blocks",
            "active",
            "FalkorDBLite to Docker migration remains an explicit deployment proof gate.",
            [anchor("prd/04_review_findings.md", "prd", selector="G-015")],
            "future-runtime-migration-proof",
            confidence=0.75,
            tags=["G-015"],
        ),
        edge(
            "EDGE-RISK-OVERCLAIM-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
            "RISK-OVERCLAIM-RUNTIME",
            "CHECK-ARCHITECTURE-EXTRACTOR",
            "checked_by",
            "active",
            "The extractor check fails closed for unsafe status/proof mappings and stale generated outputs.",
            [anchor(".gsd/milestones/M004/slices/S02/S02-PLAN.md", "gsd-summary", section="Verification")],
            "M004/S02",
            verification="Extractor tests and --check mode pass.",
            confidence=0.8,
            tags=["fitness-function", "overclaim"],
        ),
        edge(
            "EDGE-S04-FALKORDB-RUNTIME-BOUNDED-BOUNDED-BY-RISK-OVERCLAIM-RUNTIME",
            "S04-FALKORDB-RUNTIME-BOUNDED",
            "RISK-OVERCLAIM-RUNTIME",
            "bounded_by",
            "active",
            "S04 smoke evidence must not be upgraded to product suitability, production scale, or legal-quality proof.",
            [anchor("prd/05_final_architecture_review.md", "prd", section="Non-goals and overclaim guardrails")],
            "M004/S04",
            confidence=0.9,
            tags=["FalkorDB", "bounded"],
        ),
        edge(
            "EDGE-S05-PARSER-ODT-BOUNDARY-BOUNDED-BY-GATE-G008",
            "S05-PARSER-ODT-BOUNDARY",
            "GATE-G008",
            "bounded_by",
            "active",
            "S05 parser smoke guides investigation but product parser/retrieval readiness remains behind GATE-G008.",
            [anchor(".gsd/milestones/M001/slices/S08/S08-FINDINGS.json", "gsd-summary", selector="G-008")],
            "future-product-parser-retrieval-proof",
            confidence=0.85,
            tags=["parser", "G-008"],
        ),
        edge(
            "EDGE-EVID-PARSER-GOLDEN-TEST-PROOF-BOUNDED-BY-GATE-G008",
            "EVID-PARSER-GOLDEN-TEST-PROOF",
            "GATE-G008",
            "bounded_by",
            "active",
            "M008 proves a bounded golden-test harness but remains bounded by the product parser/retrieval readiness gate.",
            [anchor(".gsd/milestones/M008/M008-SUMMARY.md", "gsd-summary")],
            "M008 / future product retrieval proof",
            verification="Future product proof must still validate parser completeness boundaries, citation-safe retrieval behavior, and retrieval quality.",
            confidence=0.9,
            tags=["M008", "parser", "bounded"],
        ),
        edge(
            "EDGE-EVID-PARSER-CONSULTANT-HIERARCHY-PROOF-BOUNDED-BY-GATE-G008",
            "EVID-PARSER-CONSULTANT-HIERARCHY-PROOF",
            "GATE-G008",
            "bounded_by",
            "active",
            "M009 proves a bounded single-document Consultant hierarchy path but remains bounded by the product parser/retrieval readiness gate.",
            [anchor(".gsd/milestones/M009/M009-SUMMARY.md", "gsd-summary")],
            "M009 / future product parser proof",
            verification="Future product proof must add multi-document expansion, parser completeness boundaries, and retrieval-readiness checks before product claims.",
            confidence=0.9,
            tags=["M009", "Consultant", "bounded"],
        ),
        edge(
            "EDGE-S10-USER-BGE-M3-BASELINE-BOUNDED-BY-GATE-G011",
            "S10-USER-BGE-M3-BASELINE",
            "GATE-G011",
            "bounded_by",
            "active",
            "USER-bge-m3 runtime proof is a local baseline, not product retrieval quality proof.",
            [anchor(".gsd/milestones/M001/slices/S08/S08-FINDINGS.json", "gsd-summary", selector="G-011")],
            "future-retrieval-quality-proof",
            confidence=0.85,
            tags=["embedding", "G-011"],
        ),
        edge(
            "EDGE-M001-ARCHITECTURE-ONLY-GUARDRAIL-BOUNDS-REQ-R029",
            "M001-ARCHITECTURE-ONLY-GUARDRAIL",
            "REQ-R029",
            "bounded_by",
            "active",
            "Architecture registry verification must preserve architecture-only/product non-claim guardrails.",
            [anchor("prd/05_final_architecture_review.md", "prd", section="Scope guardrail")],
            "M004",
            confidence=0.95,
            tags=["architecture-only", "non-claim"],
        ),
        edge(
            "EDGE-DEC-D031-HAS-ASSUMPTION-ASSUMP-PRD-SOURCE-TRUTH",
            "DEC-D031",
            "ASSUMP-PRD-SOURCE-TRUTH",
            "has_assumption",
            "active",
            "The architecture registry decision assumes PRD/GSD/ADR/source/runtime evidence remains authoritative and generated registry artifacts remain derived projections.",
            [anchor("prd/09_architecture_planning_verification_research.md", "prd", section="Recommendation")],
            "M007/S01",
            confidence=0.9,
            tags=["R04-REC-002", "orphan-connectivity"],
        ),
        edge(
            "EDGE-QS-OBSERVABILITY-BASELINE-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR",
            "QS-OBSERVABILITY-OPERABILITY-BASELINE",
            "CHECK-ARCHITECTURE-EXTRACTOR",
            "checked_by",
            "active",
            "The deterministic architecture extractor/check workflow keeps observability and auditability boundary records visible in derived planning views.",
            [anchor("prd/architecture/README.md", "manual-note", section="End-to-end architecture verification workflow")],
            "M010/S01",
            verification="Architecture extractor, graph, verifier, and derived view checks pass after M010 registry repair.",
            confidence=0.8,
            tags=["M010", "observability", "orphan-connectivity"],
        ),
        edge(
            "EDGE-S05-OLD-PROJECT-PRIOR-ART-BOUNDED-BY-GATE-G008",
            "S05-OLD-PROJECT-PRIOR-ART",
            "GATE-G008",
            "bounded_by",
            "active",
            "Old_project prior art remains bounded by executable parser/retrieval golden-test proof before any legacy assumption is promoted.",
            [anchor("prd/architecture/review_findings/04/06_recommendations.json", "manual-note", selector="R04-REC-002")],
            "M007/S01",
            confidence=0.85,
            tags=["R04-REC-002", "Old_project"],
        ),
        edge(
            "EDGE-S10-GIGAEMBEDDINGS-CHALLENGER-BOUNDED-BY-GATE-G011",
            "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED",
            "GATE-G011",
            "bounded_by",
            "active",
            "Blocked GigaEmbeddings challenger evidence remains behind local embedding quality proof and cannot become managed fallback or default retrieval model.",
            [anchor("prd/architecture/review_findings/04/06_recommendations.json", "manual-note", selector="R04-REC-002")],
            "M007/S01",
            confidence=0.85,
            tags=["R04-REC-002", "embedding"],
        ),
        edge(
            "EDGE-GATE-GENERATED-CYPHER-SAFETY-BLOCKS-REQ-R017",
            "GATE-GENERATED-CYPHER-SAFETY",
            "REQ-R017",
            "blocks",
            "active",
            "R017 cannot be validated for product Legal KnowQL until generated-Cypher safety is proven beyond M003 route/proof-harness evidence.",
            [anchor("prd/06_m002_cypher_safety_contract.md", "prd", selector="Generated-Cypher Safety Contract")],
            "M007/S01",
            verification="Future validator proof covers safe/unsafe generated-Cypher candidate suites.",
            confidence=0.9,
            tags=["R04-REC-003", "R017"],
        ),
        edge(
            "EDGE-GATE-LEGAL-NEXUS-ACCESS-CONTROL-BLOCKS-COMP-LEGAL-NEXUS",
            "GATE-LEGAL-NEXUS-ACCESS-CONTROL",
            "COMP-LEGAL-NEXUS-ORCHESTRATOR",
            "blocks",
            "active",
            "Legal Nexus component claims remain bounded until access-control behavior is specified and verified.",
            [anchor("prd/03_PRD.md", "prd", selector="Legal Nexus Module")],
            "M007/S01",
            confidence=0.8,
            tags=["R04-REC-003", "access-control"],
        ),
        edge(
            "EDGE-GATE-EMBEDDING-SUPPLY-CHAIN-BOUNDS-S10-USER-BGE-M3",
            "GATE-EMBEDDING-SUPPLY-CHAIN",
            "S10-USER-BGE-M3-BASELINE",
            "bounded_by",
            "active",
            "USER-bge-m3 remains a bounded local/open-weight baseline until model provenance and supply-chain gates are formalized for product use.",
            [anchor("prd/03_PRD.md", "prd", selector="FR-28b")],
            "M007/S01",
            confidence=0.8,
            tags=["R04-REC-003", "embedding"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G008",
            "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS",
            "GATE-G008",
            "bounded_by",
            "active",
            "Research ideas about graph pre-filtering and GraphRAG retrieval remain bounded by product parser/retrieval readiness proof.",
            [anchor("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis_assessment.md", "manual-note", section="Proof-Gated Candidates")],
            "M011/S01",
            verification="Future offline retrieval proof must compare graph strategies against M008 golden cases and preserve source anchors.",
            confidence=0.85,
            tags=["M011", "GraphRAG", "retrieval", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G011",
            "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS",
            "GATE-G011",
            "bounded_by",
            "active",
            "Research ideas about ranking, embeddings, and hybrid retrieval remain bounded by local embedding quality proof.",
            [anchor("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis_assessment.md", "manual-note", section="Proof-Gated Candidates")],
            "M011/S01",
            verification="Future retrieval benchmark must use local/open-weight embeddings and measure quality before product claims.",
            confidence=0.8,
            tags=["M011", "embedding", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G015",
            "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS",
            "GATE-G015",
            "bounded_by",
            "active",
            "Research performance and FalkorDB runtime claims remain bounded by runtime migration/load proof.",
            [anchor("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis_assessment.md", "manual-note", section="FalkorDB Claim Classification")],
            "M011/S01",
            verification="Future FalkorDB legal-shaped runtime smoke must verify algorithm output shape and bounded runtime diagnostics.",
            confidence=0.8,
            tags=["M011", "FalkorDB", "runtime", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G005",
            "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS",
            "GATE-G005",
            "bounded_by",
            "active",
            "Research ideas about temporal legal graph reasoning remain bounded by the unresolved temporal same-date conflict policy gate.",
            [anchor("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis_assessment.md", "manual-note", section="Applicable Now as Architecture Principles")],
            "M011/S01",
            verification="Future temporal proof must define and verify point-in-time and same-date conflict behavior on legal fixtures.",
            confidence=0.8,
            tags=["M011", "temporal", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-GENERATED-CYPHER-SAFETY",
            "EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS",
            "GATE-GENERATED-CYPHER-SAFETY",
            "bounded_by",
            "active",
            "Research ideas about LLM agent orchestration and generated queries remain bounded by generated-Cypher product safety proof.",
            [anchor("prd/research/graph_agent_knowledge_bases_falkordb_math_analysis_assessment.md", "manual-note", section="Non-Claims")],
            "M011/S01",
            verification="Future validator proof must cover generated-Cypher acceptance/rejection before execution claims.",
            confidence=0.75,
            tags=["M011", "generated-cypher", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-G008",
            "EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING",
            "GATE-G008",
            "bounded_by",
            "active",
            "Habr Legal RAG ideas about format-first validation, citation precision, and scoped no-answer behavior remain bounded by product parser/retrieval readiness proof.",
            [anchor("prd/research/habr_legal_rag_processed_architecture_json_comparison.md", "manual-note", section="Article Idea → Processed Record Mapping")],
            "D045 / future-product-parser-retrieval-proof",
            verification="Future product proof must validate parser completeness boundaries, citation-safe retrieval behavior, retrieval output IDs, and no-answer semantics over real legal source fixtures.",
            confidence=0.85,
            tags=["D045", "Habr", "retrieval", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-G011",
            "EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING",
            "GATE-G011",
            "bounded_by",
            "active",
            "Habr Legal RAG ideas about hybrid retrieval, evidence precision, reranking, and scale/noise evaluation remain bounded by local embedding quality proof.",
            [anchor("prd/research/habr_legal_rag_processed_architecture_json_comparison.md", "manual-note", section="Missing or Weakly Represented in Processed JSON")],
            "D045 / future-retrieval-quality-proof",
            verification="Future retrieval benchmark must measure precision/recall/F-beta over stable EvidenceSpan or citation IDs under local/open-weight embedding constraints.",
            confidence=0.85,
            tags=["D045", "Habr", "embedding", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-EMBEDDING-SUPPLY-CHAIN",
            "EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING",
            "GATE-EMBEDDING-SUPPLY-CHAIN",
            "bounded_by",
            "active",
            "Habr Legal RAG local retrieval and reranker model ideas remain bounded by embedding model provenance, integrity, local runtime, and leakage checks.",
            [anchor("prd/research/habr_legal_rag_processed_architecture_json_comparison.md", "manual-note", section="Recommended JSON-Level Architecture Action")],
            "D045 / future-embedding-supply-chain-proof",
            verification="Future embedding proof records model source, revision or checksum, local runtime envelope, vector dimension, and no-secret/no-raw-vector leakage checks before promotion.",
            confidence=0.8,
            tags=["D045", "Habr", "embedding", "supply-chain", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-G005",
            "EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING",
            "GATE-G005",
            "bounded_by",
            "active",
            "Habr Legal RAG scale/disambiguation lessons reinforce temporal routing but remain bounded by unresolved same-date and multi-edition conflict policy.",
            [anchor("prd/research/habr_legal_rag_processed_architecture_json_comparison.md", "manual-note", section="Article Idea → Processed Record Mapping")],
            "D045 / future-temporal-proof",
            verification="Future temporal proof must define point-in-time and same-date conflict behavior before temporal routing can support product retrieval claims.",
            confidence=0.75,
            tags=["D045", "Habr", "temporal", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-GENERATED-CYPHER-SAFETY",
            "EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING",
            "GATE-GENERATED-CYPHER-SAFETY",
            "bounded_by",
            "active",
            "Habr Legal RAG post-LLM verification lessons support generated-output caution but remain bounded by generated-Cypher safety proof.",
            [anchor("prd/research/habr_legal_rag_processed_architecture_json_comparison.md", "manual-note", section="Article Idea → Processed Record Mapping")],
            "D045 / future-generated-cypher-safety-proof",
            verification="Future validator proof must cover generated-Cypher acceptance/rejection and evidence-return behavior before execution claims.",
            confidence=0.75,
            tags=["D045", "Habr", "generated-cypher", "bounded"],
        ),
        edge(
            "EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-G015",
            "EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING",
            "GATE-G015",
            "bounded_by",
            "active",
            "Habr Legal RAG scale/noise degradation lessons remain bounded by future FalkorDBLite-to-Docker runtime migration and load proof.",
            [anchor("prd/research/habr_legal_rag_processed_architecture_json_comparison.md", "manual-note", section="Processed Graph Implications")],
            "D045 / future-runtime-migration-proof",
            verification="Future runtime proof must execute migration/load runbook against bounded fixtures and record runtime diagnostics before production-scale claims.",
            confidence=0.75,
            tags=["D045", "Habr", "runtime", "bounded"],
        ),
        edge(
            "EDGE-DATA-LEGAL-EVIDENCE-EVIDENCED-BY-PARSER-RECORD-CONTRACT",
            "DATA-LEGAL-EVIDENCE-CORE",
            "EVID-PARSER-RECORD-CONTRACT",
            "evidenced_by",
            "active",
            "Parser record contracts provide bounded evidence for SourceDocument/SourceBlock-related legal-evidence record shapes.",
            [anchor("prd/parser/parser_record_contract.md", "manual-note", selector="SourceBlockRecord")],
            "M007/S01",
            confidence=0.85,
            tags=["R04-REC-005", "legal-evidence"],
        ),
        edge(
            "EDGE-S05-PARSER-ODT-BOUNDARY-EVIDENCED-BY-PARSER-SOURCE-FIXTURE-INVENTORY",
            "S05-PARSER-ODT-BOUNDARY",
            "EVID-PARSER-SOURCE-FIXTURE-INVENTORY",
            "evidenced_by",
            "active",
            "M006 fixture inventory is tracked parser evidence that supersedes ad hoc source-path assumptions for downstream parser planning.",
            [anchor("prd/parser/source_fixture_inventory.md", "manual-note", selector="Parser Source Fixture Inventory")],
            "M007/S01",
            confidence=0.9,
            tags=["R04-REC-005", "parser"],
        ),
        edge(
            "EDGE-S05-PARSER-ODT-BOUNDARY-EVIDENCED-BY-PARSER-ODT-SMOKE",
            "S05-PARSER-ODT-BOUNDARY",
            "EVID-PARSER-ODT-SMOKE",
            "evidenced_by",
            "active",
            "Bounded ODT smoke records are tracked real-document parser evidence for current parser staging scope.",
            [anchor("prd/parser/odt_smoke_records.md", "manual-note", selector="ODT Smoke Parser Records")],
            "M007/S01",
            confidence=0.9,
            tags=["R04-REC-005", "ODT"],
        ),
        edge(
            "EDGE-S05-PARSER-ODT-BOUNDARY-EVIDENCED-BY-PARSER-CONSULTANT-CANDIDATES",
            "S05-PARSER-ODT-BOUNDARY",
            "EVID-PARSER-CONSULTANT-CANDIDATES",
            "evidenced_by",
            "active",
            "Consultant relation candidates are tracked prior-art relation evidence but remain non-authoritative candidate records.",
            [anchor("prd/parser/consultant_relation_candidates.md", "manual-note", selector="Consultant WordML Relation Candidates")],
            "M007/S01",
            confidence=0.8,
            tags=["R04-REC-005", "Consultant"],
        ),
        edge(
            "EDGE-S05-PARSER-ODT-BOUNDARY-EVIDENCED-BY-PARSER-STAGING-GRAPH",
            "S05-PARSER-ODT-BOUNDARY",
            "EVID-PARSER-STAGING-GRAPH",
            "evidenced_by",
            "active",
            "NetworkX staging graph evidence preserves parser JSONL and relation-candidate invariants without claiming FalkorDB runtime loading.",
            [anchor("prd/parser/parser_staging_graph.md", "manual-note", selector="Parser Staging Graph")],
            "M007/S01",
            confidence=0.85,
            tags=["R04-REC-005", "NetworkX"],
        ),
        edge(
            "EDGE-GATE-G005-DEPENDS-ON-DATA-TEMPORAL-PROPERTY-BUNDLE",
            "GATE-G005",
            "DATA-TEMPORAL-PROPERTY-BUNDLE",
            "depends_on",
            "active",
            "Same-date conflict policy depends on explicit temporal fields and status semantics being modeled before validation.",
            [anchor("prd/01_general_idea.md", "prd", selector="edition_date")],
            "M007/S01",
            confidence=0.85,
            tags=["R04-REC-006", "temporal"],
        ),
        edge(
            "EDGE-REQ-TEMPORAL-STATUS-SEMANTICS-DEPENDS-ON-DATA-TEMPORAL-PROPERTY-BUNDLE",
            "REQ-TEMPORAL-STATUS-SEMANTICS",
            "DATA-TEMPORAL-PROPERTY-BUNDLE",
            "depends_on",
            "active",
            "Temporal status semantics depend on a stable temporal property bundle contract.",
            [anchor("prd/03_PRD.md", "prd", selector="New `edition_date`")],
            "M007/S01",
            confidence=0.85,
            tags=["R04-REC-006", "temporal"],
        ),
        edge(
            "EDGE-RISK-OVERCLAIM-RISKS-GATE-GENERATED-CYPHER-SAFETY",
            "RISK-OVERCLAIM-RUNTIME",
            "GATE-GENERATED-CYPHER-SAFETY",
            "risks",
            "active",
            "Generated-Cypher proof gates are threatened by overclaiming draft LLM output as executable or legally authoritative behavior.",
            [anchor("prd/09_architecture_planning_verification_research.md", "prd", section="LegalGraph Nexus-specific implications")],
            "M007/S01",
            confidence=0.85,
            tags=["R04-REC-015", "overclaim"],
        ),
        edge(
            "EDGE-RISK-OVERCLAIM-RISKS-DATA-LEGAL-EVIDENCE-CORE",
            "RISK-OVERCLAIM-RUNTIME",
            "DATA-LEGAL-EVIDENCE-CORE",
            "risks",
            "active",
            "Legal-evidence entity records can be overclaimed as implemented schema or legal correctness if non-claims are ignored.",
            [anchor("prd/09_architecture_planning_verification_research.md", "prd", section="LegalGraph Nexus-specific implications")],
            "M007/S01",
            confidence=0.8,
            tags=["R04-REC-015", "overclaim"],
        ),
        edge(
            "EDGE-COMP-LEGAL-NEXUS-DEPENDS-ON-DATA-LEGAL-EVIDENCE-CORE",
            "COMP-LEGAL-NEXUS-ORCHESTRATOR",
            "DATA-LEGAL-EVIDENCE-CORE",
            "depends_on",
            "active",
            "Legal Nexus orchestration depends on source-backed legal-evidence entities before answer or query behavior can be validated.",
            [anchor("prd/01_general_idea.md", "prd", selector="Legal Nexus")],
            "M007/S01",
            confidence=0.8,
            tags=["api-product", "legal-evidence"],
        ),
    ]
    item_ids = {record["id"] for record in build_items()}
    for record in edges:
        if record["from"] not in item_ids or record["to"] not in item_ids:
            raise ExtractionError(
                f"edge endpoint missing for {record['id']}: from={record['from']} to={record['to']}"
            )
    return sorted(edges, key=lambda record: str(record["id"]))


def serialize_jsonl(records: list[Record]) -> str:
    if not records:
        raise ExtractionError("refusing to emit empty architecture registry output")
    return "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records)


def validate_anchor_paths(config: ExtractionConfig, records: list[Record]) -> None:
    for record in records:
        for source_anchor in record.get("source_anchors", []):
            path_value = source_anchor.get("path")
            if not isinstance(path_value, str) or not path_value:
                raise ExtractionError(f"record {record.get('id')} has malformed source anchor path")
            if path_value.startswith("/"):
                raise ExtractionError(f"record {record.get('id')} has absolute source anchor path: {path_value}")
            if path_value.startswith(".gsd/exec"):
                raise ExtractionError(f"record {record.get('id')} references ignored local execution path: {path_value}")
            if not (config.root / path_value).exists():
                raise ExtractionError(f"record {record.get('id')} references missing source anchor: {path_value}")


def validate_existing_jsonl(path: Path) -> None:
    if not path.exists():
        return
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except JSONDecodeError as exc:
            raise ExtractionError(
                f"existing generated JSONL is unparsable: {path}:{line_number}: {exc.msg}"
            ) from exc


def write_or_check(path: Path, expected: str, *, check: bool) -> bool:
    if check:
        validate_existing_jsonl(path)
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            print(
                "stale generated output: "
                f"{path}; regenerate with `uv run python scripts/extract-prd-architecture-items.py` "
                "and review the JSONL diff",
                file=sys.stderr,
            )
            return False
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8")
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=DEFAULT_ITEMS, help="Path for generated architecture item JSONL")
    parser.add_argument("--edges", type=Path, default=DEFAULT_EDGES, help="Path for generated architecture edge JSONL")
    parser.add_argument("--s08-findings", type=Path, default=DEFAULT_S08_FINDINGS, help="S08 machine-readable findings JSON source")
    parser.add_argument("--check", action="store_true", help="Compare generated bytes to existing outputs without rewriting")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    config = ExtractionConfig(
        root=root,
        items_path=args.items,
        edges_path=args.edges,
        s08_findings_path=args.s08_findings if args.s08_findings.is_absolute() else root / args.s08_findings,
        check=args.check,
    )
    try:
        validate_sources(config)
        items = build_items()
        edges = build_edges()
        validate_anchor_paths(config, [*items, *edges])
        expected_items = serialize_jsonl(items)
        expected_edges = serialize_jsonl(edges)
        items_ok = write_or_check(config.items_path, expected_items, check=config.check)
        edges_ok = write_or_check(config.edges_path, expected_edges, check=config.check)
    except ExtractionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not items_ok or not edges_ok:
        return 1
    if config.check:
        print("architecture JSONL outputs are current")
    else:
        print(f"wrote {len(items)} item records to {config.items_path}")
        print(f"wrote {len(edges)} edge records to {config.edges_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
