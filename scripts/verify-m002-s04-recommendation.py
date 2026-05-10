#!/usr/bin/env python3
"""Verify the M002/S04 R017 text-to-Cypher recommendation artifact.

The verifier intentionally treats the recommendation as an evidence-boundary
artifact, not product behavior. It cross-checks the Markdown recommendation
against the S04 proof JSON, rejects overclaim language, and fails closed on
malformed proof input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECOMMENDATION = ROOT / "prd/07_m002_text_to_cypher_recommendation.md"
DEFAULT_PROOF = ROOT / ".gsd/milestones/M002/slices/S04/S04-MINIMAX-PYO3-PROOF.json"

REQUIRED_TERMS = (
    "MiniMax-M2.7-highspeed",
    "https://api.minimax.io/v1",
    "ServiceTargetResolver",
    "PyO3",
    "REST baseline",
    "Graph.ro_query",
    "EvidenceSpan",
    "SourceBlock",
    "LLM non-authoritative",
    "R017",
    "R011",
    "validator-only",
    "defer",
)
REQUIRED_EVIDENCE_ROWS = ("S01", "S02", "S03", "S04")
FORBIDDEN_SECRET_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
FORBIDDEN_OVERCLAIMS = (
    "legal answer correctness is proven",
    "legal-answer correctness is proven",
    "provider generation quality is proven",
    "Legal KnowQL product behavior is proven",
    "product parser behavior is proven",
    "production graph schema fitness is proven",
    "ODT parsing is proven",
    "retrieval quality is proven",
    "TextToCypherClient can route MiniMax",
    "ship Legal KnowQL",
)
REQUIRED_BOUNDARY_TERMS = (
    "does not implement",
    "Legal KnowQL parser",
    "LegalGraph Nexus product pipeline",
    "product ETL/import",
    "production graph schema",
    "legal-answer correctness",
    "R011 remains a supported guardrail",
)

RecommendationCategory = Literal[
    "pursue-pyo3-conditioned",
    "pursue-pyo3",
    "pursue-rest-baseline",
    "validator-only",
    "defer",
]


@dataclass
class VerificationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


def read_text(path: Path, result: VerificationResult, label: str) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        result.add(f"{label} missing: {path}")
        return None


def read_json(path: Path, result: VerificationResult, label: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        result.add(f"{label} missing: {path}")
        return None
    except json.JSONDecodeError as exc:
        result.add(f"{label} invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return None
    if not isinstance(parsed, dict):
        result.add(f"{label} root must be an object: {path}")
        return None
    return cast("dict[str, Any]", parsed)


def check_required_terms(text: str, result: VerificationResult) -> None:
    missing = [term for term in REQUIRED_TERMS if term not in text]
    if missing:
        result.add(f"Recommendation missing required terms: {', '.join(missing)}")


def check_evidence_table(text: str, result: VerificationResult) -> None:
    if "## Evidence table" not in text:
        result.add("Recommendation missing evidence table section")
        return
    for row in REQUIRED_EVIDENCE_ROWS:
        if f"| {row} |" not in text:
            result.add(f"Recommendation evidence table missing {row} row")


def check_forbidden_content(text: str, result: VerificationResult) -> None:
    for pattern in FORBIDDEN_SECRET_PATTERNS:
        match = pattern.search(text)
        if match:
            result.add(f"Recommendation contains forbidden secret-like content matching {pattern.pattern!r}")
    lowered = text.lower()
    for phrase in FORBIDDEN_OVERCLAIMS:
        if phrase.lower() in lowered:
            result.add(f"Recommendation contains forbidden overclaim: {phrase}")


def extract_category(text: str, result: VerificationResult) -> RecommendationCategory | None:
    match = re.search(r"\*\*Recommendation category:\*\*\s*`([^`]+)`", text)
    if not match:
        result.add("Recommendation missing canonical recommendation category line")
        return None
    category = match.group(1)
    allowed = {
        "pursue-pyo3-conditioned",
        "pursue-pyo3",
        "pursue-rest-baseline",
        "validator-only",
        "defer",
    }
    if category not in allowed:
        result.add(f"Recommendation category is unsupported: {category}")
        return None
    return cast("RecommendationCategory", category)


def finding_statuses(proof: dict[str, Any]) -> dict[str, str]:
    findings = proof.get("findings", [])
    if not isinstance(findings, list):
        return {}
    statuses: dict[str, str] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        identifier = finding.get("id")
        status = finding.get("status")
        if isinstance(identifier, str) and isinstance(status, str):
            statuses[identifier] = status
    return statuses


def expected_category(proof: dict[str, Any], result: VerificationResult) -> RecommendationCategory | None:
    status = proof.get("status")
    validation = proof.get("validation")
    execution = proof.get("execution")
    provider_attempts = proof.get("provider_attempts")
    statuses = finding_statuses(proof)

    if not isinstance(status, str):
        result.add("Proof missing string status")
        return None
    if not isinstance(validation, dict):
        result.add("Proof missing validation object")
        return None
    if not isinstance(execution, dict):
        result.add("Proof missing execution object")
        return None
    if not isinstance(provider_attempts, int):
        result.add("Proof missing integer provider_attempts")
        return None

    validation_accepted = validation.get("accepted") is True
    execution_status = execution.get("status")
    route_confirmed = statuses.get("target-resolution") == "confirmed-runtime"
    build_confirmed = statuses.get("maturin-build") == "confirmed-runtime"
    live_status = statuses.get("minimax-live-proof")

    if status == "confirmed-runtime" and provider_attempts > 0 and validation_accepted and execution_status == "confirmed-runtime":
        return "pursue-pyo3"
    if status == "blocked-credential" and build_confirmed and route_confirmed and validation_accepted and execution_status == "confirmed-runtime" and live_status == "blocked-credential":
        return "pursue-pyo3-conditioned"
    if status in {"blocked-credential", "blocked-environment"} and validation_accepted:
        return "validator-only"
    if status in {"blocked-environment", "failed-runtime"}:
        return "defer"
    result.add(f"Proof status combination is unsupported for recommendation: status={status!r}")
    return None


def check_category_matches_proof(category: RecommendationCategory | None, proof: dict[str, Any], result: VerificationResult) -> None:
    expected = expected_category(proof, result)
    if category is not None and expected is not None and category != expected:
        result.add(f"Recommendation category {category!r} does not match proof-derived category {expected!r}")


def check_boundary_language(text: str, category: RecommendationCategory | None, result: VerificationResult) -> None:
    missing = [term for term in REQUIRED_BOUNDARY_TERMS if term not in text]
    if missing:
        result.add(f"Recommendation missing R011/out-of-scope boundary terms: {', '.join(missing)}")
    if "R017 is advanced but not fully validated" not in text:
        result.add("Recommendation must state that R017 is advanced but not fully validated")
    if category == "pursue-pyo3-conditioned" and "Keep R017 active" not in text:
        result.add("Conditioned PyO3 recommendation must keep R017 active")
    if "shares the exact same validation boundary" not in text:
        result.add("REST baseline must state that it shares the same validation boundary")
    if not re.search(r"does\s+(?:\*\*)?not(?:\*\*)?\s+claim that an upstream high-level `TextToCypherClient` can route MiniMax", text):
        result.add("REST baseline must avoid unproven TextToCypherClient MiniMax routing claims")


def verify_recommendation(recommendation_path: Path, proof_path: Path) -> VerificationResult:
    result = VerificationResult()
    text = read_text(recommendation_path, result, "Recommendation")
    proof = read_json(proof_path, result, "S04 proof")
    if text is None or proof is None:
        return result

    check_required_terms(text, result)
    check_evidence_table(text, result)
    check_forbidden_content(text, result)
    category = extract_category(text, result)
    check_category_matches_proof(category, proof, result)
    check_boundary_language(text, category, result)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recommendation", type=Path, default=DEFAULT_RECOMMENDATION)
    parser.add_argument("--proof", type=Path, default=DEFAULT_PROOF)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify_recommendation(args.recommendation, args.proof)
    if not result.ok:
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "pass",
                "recommendation": str(args.recommendation),
                "proof": str(args.proof),
                "required_terms": list(REQUIRED_TERMS),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
