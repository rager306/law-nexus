#!/usr/bin/env python3
"""Verify M051/S08 ACP ontology prototype artifacts.

This verifier is intentionally deterministic and dependency-light. It performs
static checks over the proposed Turtle/JSON-LD/query artifacts without treating
those artifacts as authoritative architecture proof.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "prd/architecture/acp/ontology/M051-ACP-GIT-LEX-PROTOTYPE.ttl"
REPORT = ROOT / "prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md"
SAMPLE_TTL = ROOT / "prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.ttl"
SAMPLE_JSONLD = ROOT / "prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.jsonld"
QUERY_DIR = ROOT / "prd/architecture/acp/sparql/m051"
SHACL = ROOT / "prd/architecture/acp/shacl/m051/acp-prototype.shacl.ttl"
MAIN_LEX = ROOT / ".lex"

REQUIRED_CLASSES = [
    "acp:SourceRecord",
    "acp:Requirement",
    "acp:Decision",
    "acp:EvidenceAnchor",
    "acp:ProofGate",
    "acp:HealthFinding",
    "acp:Projection",
    "acp:LifecycleState",
    "acp:AuthorityClass",
    "acp:ValidationClaim",
    "acp:ProfileConstraint",
    "acp:RuntimeAdapter",
]

REQUIRED_PROPERTIES = [
    "acp:hasEvidenceAnchor",
    "acp:requiresProofGate",
    "acp:satisfiesProofGate",
    "acp:blocksClaim",
    "acp:validatesRequirement",
    "acp:doesNotValidateRequirement",
    "acp:derivedFrom",
    "acp:hasLifecycleState",
    "acp:hasAuthorityClass",
    "acp:sourcePath",
    "acp:nonAuthoritative",
]

REQUIRED_SAMPLE_TERMS = [
    "ex:req-r035",
    "ex:decision-keep-acp-native",
    "acp:EvidenceAnchor",
    "acp:ProofGate",
    "acp:HealthFinding",
    "acp:Projection",
    "acp:RuntimeAdapter",
    "ex:claim-r035-non-validation",
    "ex:claim-r037-non-validation",
    "ex:claim-r038-non-validation",
]

REQUIRED_QUERIES = [
    "find_projection_only_validations.rq",
    "find_decisions_without_proof_gate.rq",
    "find_unsafe_evidence_anchors.rq",
    "find_law_nexus_requirement_overclaims.rq",
    "find_blocked_runtime_adoption.rq",
    "trace_decision_to_evidence.rq",
]

REQUIRED_SHACL_TERMS = [
    "acp:EvidenceAnchorShape",
    "acp:SourceRecordShape",
    "acp:ProjectionShape",
    "acp:RuntimeAdapterShape",
    "sh:targetClass",
    "sh:property",
    "sh:minCount",
]

FORBIDDEN_ANCHOR_PATTERNS = [
    re.compile(r"acp:sourcePath\s+\"/"),
    re.compile(r"acp:sourcePath\s+\"[^\"]*\.gsd/exec"),
    re.compile(r"acp:sourcePath\s+\"[^\"]*secret", re.IGNORECASE),
    re.compile(r"acp:sourcePath\s+\"[^\"]*provider[-_]payload", re.IGNORECASE),
    re.compile(r"acp:sourcePath\s+\"[^\"]*raw[-_]vector", re.IGNORECASE),
    re.compile(r"acp:sourcePath\s+\"[^\"]*raw[-_]legal[-_]text", re.IGNORECASE),
]


@dataclass(frozen=True)
class Diagnostic:
    rule: str
    path: Path
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "rule": self.rule,
            "path": display_path(self.path),
            "message": self.message,
        }


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path, diagnostics: list[Diagnostic]) -> str:
    if not path.exists():
        diagnostics.append(Diagnostic("file-exists", path, "required artifact is missing"))
        return ""
    return path.read_text(encoding="utf-8")


def require_terms(path: Path, text: str, terms: list[str], diagnostics: list[Diagnostic], rule: str) -> None:
    for term in terms:
        if term not in text:
            diagnostics.append(Diagnostic(rule, path, f"missing required term {term}"))


def verify_jsonld(diagnostics: list[Diagnostic]) -> None:
    if not SAMPLE_JSONLD.exists():
        diagnostics.append(Diagnostic("jsonld-exists", SAMPLE_JSONLD, "JSON-LD sample is missing"))
        return
    try:
        data: Any = json.loads(SAMPLE_JSONLD.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        diagnostics.append(Diagnostic("jsonld-parse", SAMPLE_JSONLD, f"invalid JSON: {exc}"))
        return
    if not isinstance(data, dict):
        diagnostics.append(Diagnostic("jsonld-object", SAMPLE_JSONLD, "top-level JSON-LD value must be an object"))
        return
    if "@context" not in data:
        diagnostics.append(Diagnostic("jsonld-context", SAMPLE_JSONLD, "missing @context"))
    if "@graph" not in data:
        diagnostics.append(Diagnostic("jsonld-graph", SAMPLE_JSONLD, "missing @graph"))
    graph = data.get("@graph")
    if not isinstance(graph, list) or not graph:
        diagnostics.append(Diagnostic("jsonld-graph", SAMPLE_JSONLD, "@graph must be a non-empty array"))


def verify_queries(diagnostics: list[Diagnostic]) -> None:
    if not QUERY_DIR.exists():
        diagnostics.append(Diagnostic("query-dir", QUERY_DIR, "query directory is missing"))
        return
    for name in REQUIRED_QUERIES:
        path = QUERY_DIR / name
        text = read_text(path, diagnostics)
        if text and not re.search(r"\b(SELECT|ASK|CONSTRUCT)\b", text):
            diagnostics.append(Diagnostic("query-form", path, "query lacks SELECT/ASK/CONSTRUCT"))
        if text and "# Risk" not in text:
            diagnostics.append(Diagnostic("query-comment", path, "query lacks risk comment"))


def verify_forbidden_anchors(sample_text: str, diagnostics: list[Diagnostic]) -> None:
    for pattern in FORBIDDEN_ANCHOR_PATTERNS:
        if pattern.search(sample_text):
            diagnostics.append(
                Diagnostic("forbidden-anchor", SAMPLE_TTL, f"forbidden source anchor pattern: {pattern.pattern}")
            )


def main() -> int:
    diagnostics: list[Diagnostic] = []

    ontology_text = read_text(ONTOLOGY, diagnostics)
    report_text = read_text(REPORT, diagnostics)
    sample_text = read_text(SAMPLE_TTL, diagnostics)
    shacl_text = read_text(SHACL, diagnostics)

    require_terms(ONTOLOGY, ontology_text, REQUIRED_CLASSES, diagnostics, "ontology-required-class")
    require_terms(ONTOLOGY, ontology_text, REQUIRED_PROPERTIES, diagnostics, "ontology-required-property")
    require_terms(SAMPLE_TTL, sample_text, REQUIRED_SAMPLE_TERMS, diagnostics, "sample-required-term")
    require_terms(SHACL, shacl_text, REQUIRED_SHACL_TERMS, diagnostics, "shacl-required-term")

    if "acp:nonAuthoritative true" not in ontology_text:
        diagnostics.append(Diagnostic("ontology-non-authoritative", ONTOLOGY, "ontology lacks non-authoritative marker"))
    if "R035" not in ontology_text or "R037" not in ontology_text or "R038" not in ontology_text:
        diagnostics.append(Diagnostic("ontology-requirement-boundary", ONTOLOGY, "ontology lacks R035/R037/R038 boundary"))
    if "non-authoritative" not in report_text:
        diagnostics.append(Diagnostic("report-boundary", REPORT, "report lacks non-authoritative boundary language"))

    verify_jsonld(diagnostics)
    verify_queries(diagnostics)
    verify_forbidden_anchors(sample_text, diagnostics)

    if MAIN_LEX.exists():
        diagnostics.append(Diagnostic("main-lex-state", MAIN_LEX, "main repository .lex must not exist"))

    result = {
        "status": "ok" if not diagnostics else "failed",
        "failure_count": len(diagnostics),
        "non_authoritative": True,
        "boundary": "Verifier output is static-check evidence only; source evidence remains authoritative.",
        "parse_limitations": [
            "Turtle and SPARQL are checked structurally without an RDF/SPARQL engine dependency.",
            "JSON-LD is JSON-parsed for shape only; expansion/compaction is not verified.",
        ],
        "checked": {
            "ontology": display_path(ONTOLOGY),
            "sample_ttl": display_path(SAMPLE_TTL),
            "sample_jsonld": display_path(SAMPLE_JSONLD),
            "shacl": display_path(SHACL),
            "query_dir": display_path(QUERY_DIR),
            "report": display_path(REPORT),
            "main_lex_absent": not MAIN_LEX.exists(),
        },
        "diagnostics": [diagnostic.as_dict() for diagnostic in diagnostics],
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not diagnostics else 1


if __name__ == "__main__":
    sys.exit(main())
