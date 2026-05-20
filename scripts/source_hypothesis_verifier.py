#!/usr/bin/env python3
"""Deterministic no-LLM verifier for source-structuring hypotheses."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROPOSAL_SCHEMA_VERSION = "legalgraph-structural-hypothesis-proposal/v1"
DECISION_SCHEMA_VERSION = "legalgraph-verifier-decision/v1"
ALLOWED_PROPOSAL_FIELDS = {
    "schema_version",
    "proposal_id",
    "worker_attempt_id",
    "source_artifact_id",
    "source_revision_id",
    "run_id",
    "output_refs",
    "source_family",
    "document_role",
    "parser_route",
    "hypothesis_kind",
    "hypothesis_payload",
    "verifier_status",
    "non_authoritative",
    "non_claims",
}
ALLOWED_HYPOTHESIS_PAYLOAD_FIELDS = {
    "selector",
    "safe_rule_id",
    "confidence_bucket",
    "evidence_refs",
}
ALLOWED_HYPOTHESIS_KINDS = {
    "structural_marker_rule",
    "document_role_routing_hint",
    "safe_section_boundary_hint",
    "diagnostic_bucket_hint",
}
ALLOWED_CONFIDENCE_BUCKETS = {"low", "medium", "high"}
REQUIRED_NON_CLAIMS = {
    "proposal is a structural hypothesis only",
    "proposal does not claim legal correctness",
    "proposal does not claim parser completeness",
    "proposal does not validate R035",
}
SAFE_OUTPUT_PREFIXES = (
    "processed/consultant-wordml-v1/",
    "runs/",
    "registry/",
    "metrics.safe.json",
    "diagnostics.safe.jsonl",
    "review_pack.json",
)
FORBIDDEN_SUBSTRINGS = (
    "/tmp/",
    "/root/",
    "Федеральный закон",
    "Список документов",
    "SHOULD_NOT_APPEAR",
    "GIGACHAT_AUTH_DATA",
    "sk-",
    "raw_vector",
    "raw_vectors",
    "embedding_array",
    "BEGIN PROVIDER PAYLOAD",
    "raw_prompt",
    "raw_completion",
    "legal answer:",
    "legal_answer",
    "parser completeness validated",
    "validates R035",
)


class HypothesisVerifierError(Exception):
    """Raised for verifier IO or usage failures."""


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HypothesisVerifierError(f"missing proposal JSON: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HypothesisVerifierError(f"malformed proposal JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise HypothesisVerifierError("proposal JSON must be an object")
    return payload


def hash_id(prefix: str, payload: Any) -> str:
    digest = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:12]}"


def verify_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic verifier_decision for one proposal."""

    reasons = validation_reasons(proposal)
    status = decision_status(reasons)
    return decision_for(proposal, status, reasons)


def decision_status(reasons: list[str]) -> str:
    """Map validation reasons to accepted/rejected/needs_review."""

    if not reasons:
        return "accepted"
    if set(reasons) == {"insufficient_deterministic_evidence"}:
        return "needs_review"
    return "rejected"


def validation_reasons(proposal: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    extra = sorted(set(proposal) - ALLOWED_PROPOSAL_FIELDS)
    missing = sorted(ALLOWED_PROPOSAL_FIELDS - set(proposal))
    if extra or missing:
        reasons.append("schema_violation")
    if proposal.get("schema_version") != PROPOSAL_SCHEMA_VERSION:
        reasons.append("schema_violation")
    payload = proposal.get("hypothesis_payload")
    if not isinstance(payload, dict):
        reasons.append("schema_violation")
        payload = {}
    else:
        payload_extra = sorted(set(payload) - ALLOWED_HYPOTHESIS_PAYLOAD_FIELDS)
        payload_missing = sorted(ALLOWED_HYPOTHESIS_PAYLOAD_FIELDS - set(payload))
        if payload_extra or payload_missing:
            reasons.append("schema_violation")
    if proposal.get("hypothesis_kind") not in ALLOWED_HYPOTHESIS_KINDS:
        reasons.append("schema_violation")
    if payload.get("confidence_bucket") not in ALLOWED_CONFIDENCE_BUCKETS:
        reasons.append("schema_violation")
    if proposal.get("verifier_status") != "pending":
        reasons.append("schema_violation")
    if proposal.get("non_authoritative") is not True:
        reasons.append("schema_violation")
    non_claims = proposal.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        reasons.append("schema_violation")
    if not safe_id(str(proposal.get("proposal_id", "")), "SHP-"):
        reasons.append("schema_violation")
    if not safe_id(str(proposal.get("worker_attempt_id", "")), "WA-"):
        reasons.append("schema_violation")
    if not safe_id(str(proposal.get("source_artifact_id", "")), "SA-CONSULTANT-"):
        reasons.append("missing_safe_ref")
    if not str(proposal.get("source_revision_id", "")).startswith("SR-CONSULTANT-"):
        reasons.append("missing_safe_ref")
    if not safe_id(str(proposal.get("run_id", "")), "RUN-"):
        reasons.append("missing_safe_ref")
    if not safe_refs(proposal.get("output_refs")):
        reasons.append("missing_safe_ref")
    if not safe_refs(payload.get("evidence_refs")):
        reasons.append("insufficient_deterministic_evidence")
    reasons.extend(forbidden_reasons(proposal))
    return sorted(set(reasons))


def safe_id(value: str, prefix: str) -> bool:
    if not value.startswith(prefix):
        return False
    suffix = value[len(prefix):]
    return bool(suffix) and all(ch.isalnum() or ch == "-" for ch in suffix)


def safe_refs(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for ref in value:
        if not isinstance(ref, str) or not ref:
            return False
        if ref.startswith("/") or ".." in Path(ref).parts:
            return False
        if not ref.startswith(SAFE_OUTPUT_PREFIXES):
            return False
    return True


def forbidden_reasons(value: Any) -> list[str]:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True).lower()
    reasons: list[str] = []
    for marker in FORBIDDEN_SUBSTRINGS:
        if marker.lower() in rendered:
            reasons.append(reason_for_marker(marker))
    return reasons


def reason_for_marker(marker: str) -> str:
    lowered = marker.lower()
    if lowered.startswith("/tmp/") or lowered.startswith("/root/"):
        return "absolute_path_detected"
    if "provider" in lowered or "raw_prompt" in lowered or "raw_completion" in lowered:
        return "provider_payload_detected"
    if "legal answer" in lowered or "legal_answer" in lowered:
        return "legal_answer_prose_detected"
    if "parser completeness" in lowered:
        return "parser_completeness_overclaim"
    if "r035" in lowered:
        return "r035_validation_overclaim"
    if "sk-" in lowered or "gigachat" in lowered or "vector" in lowered or "embedding_array" in lowered:
        return "forbidden_payload_class"
    return "raw_text_detected"


def decision_for(proposal: dict[str, Any], status: str, reasons: list[str]) -> dict[str, Any]:
    proposal_id = str(proposal.get("proposal_id") or hash_id("SHP", proposal))
    raw_checked_refs = proposal.get("output_refs")
    checked_refs = raw_checked_refs if safe_refs(raw_checked_refs) else []
    raw_payload = proposal.get("hypothesis_payload")
    payload = raw_payload if isinstance(raw_payload, dict) else {}
    raw_evidence_refs = payload.get("evidence_refs")
    evidence_refs = raw_evidence_refs if isinstance(raw_evidence_refs, list) else []
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "proposal_id": proposal_id,
        "verifier_id": "deterministic-source-structure-verifier/v1",
        "verifier_status": status,
        "checked_refs": checked_refs,
        "acceptance_evidence_refs": evidence_refs if status == "accepted" else [],
        "rejection_reasons": [] if status == "accepted" else reasons,
        "decision_notes": [decision_note(status, reasons)],
        "non_authoritative": True,
        "non_claims": [
            "verifier decision accepts or rejects a structural hypothesis only",
            "verifier decision does not claim legal correctness",
            "verifier decision does not claim parser completeness",
            "verifier decision does not validate R035",
        ],
    }


def decision_note(status: str, reasons: list[str]) -> str:
    if status == "accepted":
        return "closed schema accepted and safe refs resolved"
    if status == "needs_review":
        return "proposal is safe but lacks sufficient deterministic evidence"
    if reasons:
        return f"proposal rejected with {len(reasons)} bounded reason categories"
    return "proposal requires review"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic no-LLM source hypothesis verifier.")
    parser.add_argument("proposal", type=Path, help="Path to structural_hypothesis_proposal JSON.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory for verifier_decision.json and review_queue_item.json outputs.",
    )
    return parser


def review_queue_item(proposal: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Return a safe review_queue_item for a needs_review decision."""

    proposal_id = str(decision["proposal_id"])
    worker_attempt_id = str(proposal.get("worker_attempt_id") or "WA-unknown")
    return {
        "schema_version": "legalgraph-review-queue-item/v1",
        "queue_item_id": hash_id("RQ", {"proposal_id": proposal_id, "worker_attempt_id": worker_attempt_id}),
        "proposal_id": proposal_id,
        "worker_attempt_id": worker_attempt_id,
        "verifier_status": "needs_review",
        "review_reason": "insufficient_deterministic_evidence",
        "safe_summary": "bounded structural hypothesis requires reviewer decision",
        "evidence_refs": decision.get("checked_refs", []),
        "non_authoritative": True,
        "non_claims": [
            "review queue item is not legal authority",
            "review queue item does not claim parser completeness",
            "review queue item does not validate R035",
        ],
    }


def write_outputs(output_dir: Path, proposal: dict[str, Any], decision: dict[str, Any]) -> None:
    """Write fixed verifier output files to a directory."""

    if output_dir.exists() and not output_dir.is_dir():
        raise HypothesisVerifierError("output-dir must be a directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "verifier_decision.json").write_text(stable_json(decision), encoding="utf-8")
    if decision["verifier_status"] == "needs_review":
        item = review_queue_item(proposal, decision)
        (output_dir / "review_queue_item.json").write_text(stable_json(item), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        proposal = load_json_object(args.proposal)
    except HypothesisVerifierError as exc:
        print(f"hypothesis verifier error: {exc}", file=sys.stderr)
        return 2
    decision = verify_proposal(proposal)
    if args.output_dir is not None:
        try:
            write_outputs(args.output_dir, proposal, decision)
        except HypothesisVerifierError as exc:
            print(f"hypothesis verifier error: {exc}", file=sys.stderr)
            return 2
    print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
    return 0 if decision["verifier_status"] in {"accepted", "needs_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
