#!/usr/bin/env python3
"""Verify M027 safe parser-to-EvidenceSpan materialization artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json"
SCHEMA_VERSION = "parser-evidence-span-materialization/v1"
REPRESENTATION_KIND = "safe_materialized_evidence_candidates_v1"
ALLOWED_STATUS = {"ok", "blocked", "failed"}
ALLOWED_BLOCKED_REASONS = {"none", "source_unavailable", "parser_unavailable", "raw_text_leakage_risk", "schema_boundary_missing", "insufficient_structural_evidence"}
ALLOWED_ROOT_FIELDS = {
    "blocked_reason",
    "contract",
    "contract_sha256",
    "materialized_candidate_count",
    "materialized_candidates",
    "milestone_id",
    "non_authoritative",
    "non_claim_boundary",
    "parser_evidence_summary",
    "r035_non_validation_declared",
    "r038_review_required",
    "redaction",
    "representation_kind",
    "safe_source_anchors_verified",
    "schema_version",
    "slice_id",
    "source_document_ref",
    "source_document_sha256",
    "status",
}
ALLOWED_CANDIDATE_FIELDS = {
    "candidate_id",
    "candidate_kind",
    "source_document_ref",
    "source_document_sha256",
    "source_anchor_id",
    "source_anchor_sha256",
    "source_order_index",
    "structural_unit_kind",
    "citation_granularity",
    "content_role",
    "temporal_status",
    "materialization_method",
    "parser_evidence_ref",
    "non_authoritative",
}
ALLOWED_CANDIDATE_KIND = {"evidence_span", "source_block", "citation_boundary", "temporal_scope_marker", "blocked_candidate"}
ALLOWED_STRUCTURAL_UNIT_KIND = {"document", "article", "clause", "paragraph", "table", "list_item", "unknown_structural_unit"}
ALLOWED_CITATION_GRANULARITY = {"act_edition", "article_or_evidence_span", "clause", "source_block_marker", "temporal_marker", "unknown_granularity"}
ALLOWED_CONTENT_ROLE = {"retrieval_candidate", "citation_boundary", "scope_boundary", "temporal_boundary", "blocked_unsafe"}
ALLOWED_TEMPORAL_STATUS = {"current_edition", "as_of_date_required", "edition_consistency_required", "unknown_temporal_status"}
ALLOWED_MATERIALIZATION_METHOD = {"odt_structure_smoke", "content_xml_order_anchor", "parser_blocked"}
FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "source_excerpts",
    "query_text",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_response_body",
    "secret",
    "secrets",
    "vector",
    "vectors",
    "embedding",
    "embedding_vector",
    "runtime_row",
    "falkordb_row",
    "generated_answer_prose",
    "generated_query",
    "generated_cypher",
    "legal_advice",
    "llm_reasoning",
    "expected_label",
    "expected_rank",
    "rank",
    "expected_candidate_ids",
    "expected_rejected_candidate_ids",
    "expected_diagnostic_codes",
    "selection_reason",
    "expected_result",
}
FORBIDDEN_STRING_FRAGMENTS = (
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "expected_label",
    "expected_candidate_ids",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
)
SAFE_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE_CANDIDATE_ID_RE = re.compile(r"^MAT-M027-[0-9]{3}-[A-Z0-9-]+$")
SAFE_ANCHOR_ID_RE = re.compile(r"^SRC-M027-[0-9]{3}-[A-Z0-9-]+$")
SAFE_EVIDENCE_REF_RE = re.compile(r"^parser-smoke:SRC-M027-[0-9]{3}-[A-Z0-9-]+$")
ABSOLUTE_PATH_RE = re.compile(r"(^|[\s:=])(?:/[A-Za-z0-9_.-]+|[A-Za-z]:\\)")


class MaterializationVerificationError(RuntimeError):
    """Raised when materialization verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MaterializationVerificationError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise MaterializationVerificationError("artifact root must be object")
    return payload


def repo_path(path_value: str) -> Path:
    if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
        raise MaterializationVerificationError(f"unsafe path: {path_value}")
    path = ROOT / path_value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise MaterializationVerificationError(f"path outside repository: {path_value}") from exc
    return path


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise MaterializationVerificationError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and ABSOLUTE_PATH_RE.search(value):
            raise MaterializationVerificationError("unsafe absolute path fragment")

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise MaterializationVerificationError(f"unsafe payload fragment: {fragment}")
    if "provider_payloads_excluded" in serialized:
        raise MaterializationVerificationError("unsafe durable vocabulary")


def validate_redaction(redaction: Any) -> None:
    required = {
        "source_text_excluded",
        "query_text_excluded",
        "raw_vectors_excluded",
        "external_payloads_excluded",
        "generated_answer_prose_excluded",
        "generated_query_excluded",
        "absolute_paths_excluded",
        "gsd_exec_paths_excluded",
    }
    if not isinstance(redaction, Mapping) or set(redaction) != required or any(value is not True for value in redaction.values()):
        raise MaterializationVerificationError("redaction flags mismatch")


def validate_candidate(candidate: Any, source_ref: str, source_sha: str, seen_ids: set[str]) -> None:
    if not isinstance(candidate, Mapping):
        raise MaterializationVerificationError("candidate must be object")
    unexpected = set(candidate) - ALLOWED_CANDIDATE_FIELDS
    if unexpected:
        raise MaterializationVerificationError(f"unexpected candidate fields: {sorted(unexpected)}")
    candidate_id = str(candidate.get("candidate_id"))
    anchor_id = str(candidate.get("source_anchor_id"))
    if not SAFE_CANDIDATE_ID_RE.fullmatch(candidate_id):
        raise MaterializationVerificationError(f"unsafe candidate id: {candidate_id}")
    if not SAFE_ANCHOR_ID_RE.fullmatch(anchor_id):
        raise MaterializationVerificationError(f"unsafe source anchor id: {anchor_id}")
    if candidate_id in seen_ids or anchor_id in seen_ids:
        raise MaterializationVerificationError("duplicate materialization id")
    seen_ids.update({candidate_id, anchor_id})
    if candidate.get("candidate_kind") not in ALLOWED_CANDIDATE_KIND:
        raise MaterializationVerificationError("candidate_kind enum mismatch")
    if candidate.get("structural_unit_kind") not in ALLOWED_STRUCTURAL_UNIT_KIND:
        raise MaterializationVerificationError("structural_unit_kind enum mismatch")
    if candidate.get("citation_granularity") not in ALLOWED_CITATION_GRANULARITY:
        raise MaterializationVerificationError("citation_granularity enum mismatch")
    if candidate.get("content_role") not in ALLOWED_CONTENT_ROLE:
        raise MaterializationVerificationError("content_role enum mismatch")
    if candidate.get("temporal_status") not in ALLOWED_TEMPORAL_STATUS:
        raise MaterializationVerificationError("temporal_status enum mismatch")
    if candidate.get("materialization_method") not in ALLOWED_MATERIALIZATION_METHOD:
        raise MaterializationVerificationError("materialization_method enum mismatch")
    if candidate.get("source_document_ref") != source_ref or candidate.get("source_document_sha256") != source_sha:
        raise MaterializationVerificationError("candidate source reference mismatch")
    if not isinstance(candidate.get("source_order_index"), int) or candidate["source_order_index"] <= 0:
        raise MaterializationVerificationError("source_order_index mismatch")
    if not isinstance(candidate.get("source_anchor_sha256"), str) or not SAFE_HASH_RE.fullmatch(candidate["source_anchor_sha256"]):
        raise MaterializationVerificationError("source anchor hash mismatch")
    if not isinstance(candidate.get("parser_evidence_ref"), str) or not SAFE_EVIDENCE_REF_RE.fullmatch(candidate["parser_evidence_ref"]):
        raise MaterializationVerificationError("parser evidence ref mismatch")
    if candidate.get("non_authoritative") is not True:
        raise MaterializationVerificationError("candidate non-authoritative marker missing")


def verify_artifact(path: Path) -> dict[str, Any]:
    artifact = load_json(path)
    assert_safe_payload(artifact)
    unexpected = set(artifact) - ALLOWED_ROOT_FIELDS
    if unexpected:
        raise MaterializationVerificationError(f"unexpected root fields: {sorted(unexpected)}")
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise MaterializationVerificationError("schema_version mismatch")
    if artifact.get("representation_kind") != REPRESENTATION_KIND:
        raise MaterializationVerificationError("representation_kind mismatch")
    if artifact.get("milestone_id") != "M027-vxdy7c" or artifact.get("slice_id") != "S02":
        raise MaterializationVerificationError("milestone or slice marker mismatch")
    if artifact.get("status") not in ALLOWED_STATUS:
        raise MaterializationVerificationError("status mismatch")
    if artifact.get("blocked_reason") not in ALLOWED_BLOCKED_REASONS:
        raise MaterializationVerificationError("blocked reason mismatch")
    validate_redaction(artifact.get("redaction"))
    if artifact.get("r035_non_validation_declared") is not True or artifact.get("r038_review_required") is not True:
        raise MaterializationVerificationError("lifecycle boundary marker missing")
    source_ref = artifact.get("source_document_ref")
    if not isinstance(source_ref, str):
        raise MaterializationVerificationError("source document ref missing")
    source_path = repo_path(source_ref)
    source_sha = artifact.get("source_document_sha256")
    if artifact.get("status") == "ok":
        if source_sha != sha256_path(source_path):
            raise MaterializationVerificationError("source document sha mismatch")
        if artifact.get("safe_source_anchors_verified") is not True:
            raise MaterializationVerificationError("safe source anchors marker missing")
        if not isinstance(artifact.get("contract"), str) or sha256_path(repo_path(artifact["contract"])) != artifact.get("contract_sha256"):
            raise MaterializationVerificationError("contract sha mismatch")
        candidates = artifact.get("materialized_candidates")
        if not isinstance(candidates, list) or not candidates:
            raise MaterializationVerificationError("materialized candidates missing")
        if artifact.get("materialized_candidate_count") != len(candidates):
            raise MaterializationVerificationError("materialized candidate count mismatch")
        seen_ids: set[str] = set()
        for candidate in candidates:
            validate_candidate(candidate, source_ref, str(source_sha), seen_ids)
        summary = artifact.get("parser_evidence_summary")
        if not isinstance(summary, Mapping) or summary.get("raw_text_persisted") is not False or summary.get("content_xml_ordering_oracle_used") is not True:
            raise MaterializationVerificationError("parser evidence summary mismatch")
    else:
        if artifact.get("materialized_candidate_count") != 0 or artifact.get("materialized_candidates") != []:
            raise MaterializationVerificationError("blocked artifact must not contain candidates")
    boundary = artifact.get("non_claim_boundary")
    if not isinstance(boundary, str) or "validate R035" not in boundary:
        raise MaterializationVerificationError("non-claim boundary missing")
    return {
        "schema_version": "parser-evidence-span-materialization-verification/v1",
        "status": "ok",
        "artifact_status": artifact.get("status"),
        "blocked_reason": artifact.get("blocked_reason"),
        "representation_kind": REPRESENTATION_KIND,
        "materialized_candidate_count": int(artifact.get("materialized_candidate_count", 0)),
        "safe_source_anchors_verified": artifact.get("safe_source_anchors_verified") is True,
        "diagnostic_codes": ["parser_evidence_span_materialization_verified"],
        "non_authoritative": True,
        "non_claim_boundary": "Materialization verification only; does not prove parser completeness or validate R035.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", nargs="?", type=Path, default=DEFAULT_ARTIFACT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_artifact(args.artifact)
    except MaterializationVerificationError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
