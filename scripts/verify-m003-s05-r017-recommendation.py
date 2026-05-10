#!/usr/bin/env python3
"""Verify the M003/S05 R017 recommendation artifact.

The verifier treats the PRD as an evidence-boundary artifact. It reads the
recommendation, S05 proof-closure JSON, and upstream S01-S04 evidence, derives
the allowed category independently, and fails closed on missing evidence rows,
unsupported upgrades, product/legal overclaims, and raw or secret-like content.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECOMMENDATION = ROOT / "prd/08_m003_minimax_pyo3_functioning_proof.md"
DEFAULT_CLOSURE = ROOT / ".gsd/milestones/M003/slices/S05/S05-R017-PROOF-CLOSURE.json"
DEFAULT_UPSTREAM_PATHS = {
    "S01": ROOT / ".gsd/milestones/M003/slices/S01/S01-MINIMAX-LIVE-BASELINE.json",
    "S02": ROOT / ".gsd/milestones/M003/slices/S02/S02-MINIMAX-PYO3-ENDPOINT.json",
    "S03": ROOT / ".gsd/milestones/M003/slices/S03/S03-REASONING-SAFE-CANDIDATE.json",
    "S04": ROOT / ".gsd/milestones/M003/slices/S04/S04-VALIDATION-READONLY-EXECUTION.json",
}

RecommendationCategory = Literal[
    "pursue-pyo3-conditioned",
    "pursue-pyo3",
    "pursue-rest-baseline",
    "validator-only",
    "defer",
]

REQUIRED_TERMS = (
    "MiniMax-M2.7-highspeed",
    "https://api.minimax.io/v1",
    "PyO3",
    "REST",
    "EvidenceSpan",
    "SourceBlock",
    "LLM non-authoritative",
    "R017",
    "advanced-not-validated",
    "requirements_validated=[]",
    "validator-only",
    "defer",
)
REQUIRED_EVIDENCE_ROWS = ("S01", "S02", "S03", "S04", "S05")
REQUIRED_NON_CLAIMS = (
    "provider generation quality",
    "product Legal KnowQL behavior",
    "legal-answer correctness",
    "ODT parsing",
    "retrieval quality",
    "Russian legal terminology quality",
    "production schema grounding",
    "production FalkorDB scale",
    "raw legal evidence quality",
)
REQUIRED_NON_CLAIM_MIN_COUNTS = {
    "legal-answer correctness": 4,
    "ODT parsing": 2,
    "retrieval quality": 3,
    "Russian legal terminology quality": 3,
    "production schema grounding": 2,
    "production FalkorDB scale": 3,
    "raw legal evidence quality": 3,
}
REQUIRED_BRANCH_CATEGORIES = (
    "pursue-pyo3-conditioned",
    "pursue-pyo3",
    "pursue-rest-baseline",
    "validator-only",
    "defer",
)
REQUIRED_CLOSURE_SCHEMA = "m003-s05-r017-proof-closure/v1"
REQUIRED_UPSTREAM_SCHEMAS = {
    "S01": "m003-s01-minimax-live-baseline/v1",
    "S02": "m003-s02-minimax-pyo3-endpoint/v2",
    "S03": "m003-s03-reasoning-safe-candidate/v2",
    "S04": "m003-s04-validation-readonly-execution/v1",
}
FORBIDDEN_SECRET_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
FORBIDDEN_RAW_PATTERNS = (
    re.compile(r"(?is)<think\b.*?</think>"),
    re.compile(r"(?i)raw_provider_body\s*[:=]"),
    re.compile(r"(?i)raw_provider_bodies\s*[:=]"),
    re.compile(r"(?i)raw_reasoning\s*[:=]"),
    re.compile(r"(?i)raw_legal_text\s*[:=]"),
    re.compile(r"(?i)raw_graph_rows\s*[:=]"),
    re.compile(r"(?i)prompt\s*:\s*generate"),
)
FORBIDDEN_OVERCLAIMS = (
    "Legal KnowQL product behavior is proven",
    "legal-answer correctness is proven",
    "provider generation quality is proven",
    "ODT parsing is proven",
    "retrieval quality is proven",
    "production FalkorDB scale is proven",
    "production schema grounding is proven",
    "Russian legal terminology quality is proven",
    "raw legal evidence quality is proven",
    "ship Legal KnowQL",
)


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


def bool_field(payload: Mapping[str, Any], key: str) -> bool:
    return payload.get(key) is True


def int_field(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    return value if isinstance(value, int) else 0


def str_field(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def closure_slice(closure: Mapping[str, Any], slice_id: str) -> dict[str, Any]:
    upstream = closure.get("upstream_artifacts")
    if not isinstance(upstream, dict):
        return {}
    payload = upstream.get(slice_id)
    return payload if isinstance(payload, dict) else {}


def merged_slice(closure: Mapping[str, Any], upstream: Mapping[str, Mapping[str, Any]], slice_id: str) -> dict[str, Any]:
    merged = dict(upstream.get(slice_id, {}))
    merged.update(closure_slice(closure, slice_id))
    return merged


def check_schema(closure: Mapping[str, Any], upstream: Mapping[str, Mapping[str, Any]], result: VerificationResult) -> None:
    if closure.get("schema_version") != REQUIRED_CLOSURE_SCHEMA:
        result.add(f"Closure schema_version must be {REQUIRED_CLOSURE_SCHEMA!r}")
    for slice_id, expected in REQUIRED_UPSTREAM_SCHEMAS.items():
        actual = upstream.get(slice_id, {}).get("schema_version")
        if actual != expected:
            result.add(f"{slice_id} schema_version must be {expected!r}; got {actual!r}")
    effect = closure.get("r017_effect")
    if not isinstance(effect, dict) or effect.get("status") != "advanced-not-validated":
        result.add("Closure r017_effect.status must be 'advanced-not-validated'")
    validated = closure.get("requirements_validated")
    if validated != []:
        result.add("Closure requirements_validated must remain []")


def has_safety_regression(s03: Mapping[str, Any], s04: Mapping[str, Any]) -> bool:
    categories = s03.get("candidate_categories")
    rejection_codes = s04.get("validation_rejection_codes")
    category_text = " ".join(str(value).lower() for value in categories) if isinstance(categories, list) else ""
    code_text = " ".join(str(value).lower() for value in rejection_codes) if isinstance(rejection_codes, list) else ""
    return any(term in category_text or term in code_text for term in ("unsafe", "write", "delete", "mutation", "non-read-only"))


def derive_category(
    closure: Mapping[str, Any],
    upstream: Mapping[str, Mapping[str, Any]],
    result: VerificationResult,
) -> RecommendationCategory | None:
    check_schema(closure, upstream, result)
    s01 = merged_slice(closure, upstream, "S01")
    s02 = merged_slice(closure, upstream, "S02")
    s03 = merged_slice(closure, upstream, "S03")
    s04 = merged_slice(closure, upstream, "S04")

    endpoint_ok = bool_field(s01, "endpoint_preserves_v1") or str_field(s01, "status") == "blocked-credential"
    s02_endpoint_ok = bool_field(s02, "endpoint_preserves_v1")
    mechanics_ok = bool_field(s02, "mechanics_confirmed")
    provider_attempted = int_field(s02, "provider_attempts") > 0 or int_field(s03, "provider_attempts") > 0
    accepted_candidate = bool_field(s03, "candidate_accepted")
    validation_accepted = bool_field(s04, "validation_accepted")
    execution_confirmed = bool_field(s04, "execution_attempted") and str_field(s04, "execution_status") == "confirmed-runtime"

    if not endpoint_ok:
        result.add("S01 endpoint normalization evidence is missing or regressed")
        return None
    if has_safety_regression(s03, s04):
        return "defer"
    if not s02_endpoint_ok or not mechanics_ok:
        return "pursue-rest-baseline"
    if accepted_candidate and validation_accepted and execution_confirmed:
        return "pursue-pyo3"
    if provider_attempted:
        return "pursue-pyo3-conditioned"
    return "validator-only"


def extract_category(text: str, result: VerificationResult) -> RecommendationCategory | None:
    match = re.search(r"\*\*Recommendation category:\*\*\s*`([^`]+)`", text)
    if not match:
        result.add("Recommendation missing canonical recommendation category line")
        return None
    category = match.group(1)
    if category not in REQUIRED_BRANCH_CATEGORIES:
        result.add(f"Recommendation category is unsupported: {category}")
        return None
    return cast("RecommendationCategory", category)


def check_required_terms(text: str, result: VerificationResult) -> None:
    missing = [term for term in REQUIRED_TERMS if term not in text]
    if missing:
        result.add(f"Recommendation missing required terms: {', '.join(missing)}")


def check_evidence_rows(text: str, result: VerificationResult) -> None:
    if "## Evidence table" not in text:
        result.add("Recommendation missing evidence table section")
        return
    for row in REQUIRED_EVIDENCE_ROWS:
        if f"| {row} |" not in text:
            result.add(f"Recommendation evidence table missing {row} row")


def check_branch_rules(text: str, result: VerificationResult) -> None:
    if "## Branch rules" not in text:
        result.add("Recommendation missing branch rules section")
    missing = [category for category in REQUIRED_BRANCH_CATEGORIES if f"`{category}`" not in text]
    if missing:
        result.add(f"Recommendation missing branch rules for: {', '.join(missing)}")
    if "accepted S03 candidate" not in text or "confirmed S04 read-only execution" not in text:
        result.add("Recommendation must require accepted candidate plus confirmed read-only execution for upgrade")
    if "route regresses" not in text and "route regression" not in text:
        result.add("Recommendation must state route-regression fallback rules")
    if "safety" not in text or "redaction" not in text:
        result.add("Recommendation must state safety/redaction defer rules")


def check_non_claims(text: str, result: VerificationResult) -> None:
    missing = [term for term in REQUIRED_NON_CLAIMS if term not in text]
    undercounted = [term for term, minimum in REQUIRED_NON_CLAIM_MIN_COUNTS.items() if text.count(term) < minimum]
    if missing or undercounted:
        all_missing = sorted(set(missing + undercounted))
        result.add(f"Recommendation missing explicit non-claims: {', '.join(all_missing)}")


def check_r017_language(text: str, category: RecommendationCategory | None, result: VerificationResult) -> None:
    if "R017 is advanced but not fully validated" not in text:
        result.add("Recommendation must state that R017 is advanced but not fully validated")
    if "R017 remains active and is advanced-not-validated" not in text:
        result.add("Recommendation must state that R017 remains active and is advanced-not-validated")
    if "does not validate R017" not in text and "does not validate it" not in text:
        result.add("Recommendation must avoid validating R017")
    if category == "pursue-pyo3-conditioned" and "rather than `pursue-pyo3`" not in text:
        result.add("Conditioned recommendation must explain why it is not pursue-pyo3")


def check_forbidden_content(text: str, result: VerificationResult) -> None:
    for pattern in FORBIDDEN_SECRET_PATTERNS:
        if pattern.search(text):
            result.add(f"Recommendation contains forbidden secret-like content matching {pattern.pattern!r}")
    for pattern in FORBIDDEN_RAW_PATTERNS:
        if pattern.search(text):
            result.add(f"Recommendation contains forbidden raw/think content matching {pattern.pattern!r}")
    lowered = text.lower()
    for phrase in FORBIDDEN_OVERCLAIMS:
        if phrase.lower() in lowered:
            result.add(f"Recommendation contains forbidden overclaim: {phrase}")


def check_closure_consistency(
    text_category: RecommendationCategory | None,
    closure: Mapping[str, Any],
    derived: RecommendationCategory | None,
    result: VerificationResult,
) -> None:
    closure_category = closure.get("derived_recommendation_category")
    if closure_category != derived:
        result.add(
            f"Closure category {closure_category!r} does not match independently derived category {derived!r}"
        )
    if text_category is not None and derived is not None and text_category != derived:
        result.add(
            f"Recommendation category {text_category!r} does not match independently derived category {derived!r}"
        )
    non_claims = closure.get("non_claims")
    if not isinstance(non_claims, list):
        result.add("Closure non_claims must be a list")
        return
    missing = [claim for claim in ("provider generation quality", "Legal KnowQL product behavior", "legal-answer correctness", "ODT parsing", "retrieval quality") if claim not in non_claims]
    if missing:
        result.add(f"Closure missing required non-claims: {', '.join(missing)}")


def verify_recommendation(
    recommendation_path: Path,
    closure_path: Path,
    upstream_paths: Mapping[str, Path] | None = None,
) -> VerificationResult:
    result = VerificationResult()
    upstream_paths = upstream_paths or DEFAULT_UPSTREAM_PATHS
    text = read_text(recommendation_path, result, "Recommendation")
    closure = read_json(closure_path, result, "Closure")
    upstream: dict[str, dict[str, Any]] = {}
    for slice_id in REQUIRED_EVIDENCE_ROWS[:-1]:
        path = upstream_paths.get(slice_id)
        if path is None:
            result.add(f"{slice_id} upstream path missing from verifier input")
            continue
        payload = read_json(path, result, f"{slice_id} upstream evidence")
        if payload is not None:
            upstream[slice_id] = payload
    if text is None or closure is None or len(upstream) != 4:
        return result

    category = extract_category(text, result)
    derived = derive_category(closure, upstream, result)
    check_required_terms(text, result)
    check_evidence_rows(text, result)
    check_branch_rules(text, result)
    check_non_claims(text, result)
    check_r017_language(text, category, result)
    check_forbidden_content(text, result)
    check_closure_consistency(category, closure, derived, result)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recommendation", type=Path, default=DEFAULT_RECOMMENDATION)
    parser.add_argument("--closure", type=Path, default=DEFAULT_CLOSURE)
    parser.add_argument("--s01", type=Path, default=DEFAULT_UPSTREAM_PATHS["S01"])
    parser.add_argument("--s02", type=Path, default=DEFAULT_UPSTREAM_PATHS["S02"])
    parser.add_argument("--s03", type=Path, default=DEFAULT_UPSTREAM_PATHS["S03"])
    parser.add_argument("--s04", type=Path, default=DEFAULT_UPSTREAM_PATHS["S04"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    upstream_paths = {"S01": args.s01, "S02": args.s02, "S03": args.s03, "S04": args.s04}
    result = verify_recommendation(args.recommendation, args.closure, upstream_paths)
    if not result.ok:
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    closure = read_json(args.closure, VerificationResult(), "Closure") or {}
    print(
        json.dumps(
            {
                "status": "pass",
                "recommendation": str(args.recommendation),
                "closure": str(args.closure),
                "derived_recommendation_category": closure.get("derived_recommendation_category"),
                "r017_effect": closure.get("r017_effect"),
                "checked_upstream_slices": ["S01", "S02", "S03", "S04"],
                "non_claims_checked": list(REQUIRED_NON_CLAIMS),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
