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
            "Executable parser and retrieval golden tests",
            "Parser and retrieval claims need executable golden tests before product proof.",
            "parser-ingestion",
            "active",
            "none",
            "high",
            prd_anchor("G-008"),
            "future-parser-retrieval-proof",
            "Golden tests pass on real legal source fixtures and retrieval expectations.",
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
    records = requirement_items() + decision_items() + proof_gate_items() + evidence_and_governance_items()
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
            "Parser/retrieval proof gaps must remain explicit until executable golden tests exist.",
            [anchor("prd/04_review_findings.md", "prd", selector="G-008")],
            "future-parser-retrieval-proof",
            confidence=0.75,
            tags=["G-008"],
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
            [anchor(".gsd/milestones/M004/slices/S02/S02-PLAN.md", "gsd-summary", section="Failure Modes")],
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
            "S05 parser smoke guides investigation but parser/retrieval quality remains behind G-008 golden tests.",
            [anchor(".gsd/milestones/M001/slices/S08/S08-FINDINGS.json", "gsd-summary", selector="G-008")],
            "future-parser-retrieval-proof",
            confidence=0.85,
            tags=["parser", "G-008"],
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
