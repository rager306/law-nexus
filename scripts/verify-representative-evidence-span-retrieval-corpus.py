#!/usr/bin/env python3
"""Verify the M022 representative EvidenceSpan retrieval corpus fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
SCHEMA_VERSION = "representative-evidence-span-retrieval-corpus/v1"
FIXTURE_ARTIFACT = "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"

REQUIRED_CASE_CLASSES = {
    "positive_evidence_span",
    "positive_source_block_marker",
    "positive_with_distractor",
    "stale_temporal_negative",
    "ambiguous_candidate_set",
    "unsupported_scope",
    "scoped_no_answer",
    "citation_preservation_boundary",
    "edition_mismatch_negative",
    "unsafe_payload_boundary",
}

ALLOWED_EXPECTED_RESULTS = {"selected", "rejected", "ambiguous", "unsupported", "no_answer", "boundary_rejected"}
ALLOWED_EXPECTED_LABELS = {"relevant", "distractor", "stale", "ambiguous", "unsupported", "no_answer", "unsafe"}
REQUIRED_NON_CLAIMS = {
    "Does not validate R035.",
    "Does not validate R037.",
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove legal interpretation authority.",
    "Does not prove graph-vector or HNSW behavior.",
    "Does not prove hybrid retrieval quality.",
    "Does not prove production FalkorDB readiness.",
    "Does not prove bulk-loader production readiness.",
    "Does not prove pilot or 1000-document readiness.",
    "Does not authorize managed embedding API fallback.",
}

EXPECTED_DIAGNOSTICS_BY_CLASS = {
    "stale_temporal_negative": {"stale_temporal_candidate"},
    "ambiguous_candidate_set": {"ambiguous_candidate_set"},
    "unsupported_scope": {"unsupported_scope"},
    "scoped_no_answer": {"scoped_no_answer"},
    "edition_mismatch_negative": {"stale_temporal_candidate"},
    "unsafe_payload_boundary": {"unsafe_payload_rejected"},
}

FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "source_excerpts",
    "query_text",
    "raw_query_text",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_response_body",
    "secret",
    "secrets",
    "token",
    "password",
    "vector",
    "vectors",
    "embedding",
    "embedding_vector",
    "raw_falkordb_row",
    "falkordb_row",
    "runtime_row",
    "generated_answer_prose",
    "generated_query",
    "generated_cypher",
    "legal_advice",
    "llm_reasoning",
}

FORBIDDEN_STRING_FRAGMENTS = (
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
)


class VerificationError(Exception):
    """Raised when the representative corpus fixture is invalid."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise VerificationError("fixture root must be an object")
    return payload


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise VerificationError(f"path outside repository: {path}") from exc


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerificationError(f"{label} must be a non-empty string")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VerificationError(f"{label} must be a list")
    return value


def check_no_unsafe_payload(payload: Mapping[str, Any]) -> None:
    def check_keys(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise VerificationError(f"unsafe field name: {key}")
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)

    check_keys(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise VerificationError(f"unsafe payload fragment: {fragment}")


def check_source_artifacts(payload: Mapping[str, Any]) -> set[str]:
    artifacts = require_list(payload.get("source_artifacts"), "source_artifacts")
    if not artifacts:
        raise VerificationError("source_artifacts must not be empty")
    declared: set[str] = set()
    for item in artifacts:
        if not isinstance(item, Mapping):
            raise VerificationError("source artifact must be object")
        path_value = require_string(item.get("path"), "source artifact path")
        digest = require_string(item.get("sha256"), "source artifact sha256")
        if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
            raise VerificationError(f"unsafe source artifact path: {path_value}")
        path = ROOT / path_value
        if not path.exists():
            raise VerificationError(f"source anchor missing: {path_value}")
        if repo_relative(path) != path_value:
            raise VerificationError(f"source artifact is not stable repo-relative path: {path_value}")
        if len(digest) != 64 or sha256_path(path) != digest:
            raise VerificationError(f"source artifact sha256 mismatch: {path_value}")
        declared.add(path_value)
    return declared


def check_candidate(candidate: Mapping[str, Any], source_paths: set[str], seen_candidate_ids: set[str]) -> str:
    candidate_id = require_string(candidate.get("candidate_id"), "candidate_id")
    if not candidate_id.startswith("CAND-M022-"):
        raise VerificationError(f"candidate_id prefix invalid: {candidate_id}")
    if candidate_id in seen_candidate_ids:
        raise VerificationError(f"duplicate candidate_id: {candidate_id}")
    seen_candidate_ids.add(candidate_id)
    source_artifact = require_string(candidate.get("source_artifact"), "candidate source_artifact")
    if source_artifact not in source_paths:
        raise VerificationError(f"candidate source_artifact not declared: {source_artifact}")
    source_case_id = require_string(candidate.get("source_case_id"), "source_case_id")
    if not source_case_id.startswith("CASE-"):
        raise VerificationError(f"source_case_id prefix invalid: {source_case_id}")
    expected_label = require_string(candidate.get("expected_label"), "expected_label")
    if expected_label not in ALLOWED_EXPECTED_LABELS:
        raise VerificationError(f"unsupported expected_label: {expected_label}")
    rank = candidate.get("rank")
    if not isinstance(rank, int) or rank < 1:
        raise VerificationError(f"candidate rank invalid: {candidate_id}")
    for field in ("evidence_span_id", "source_block_id", "citation_key", "act_edition_id", "selection_reason"):
        require_string(candidate.get(field), f"candidate {field}")
    record_ids = require_list(candidate.get("source_record_ids"), "candidate source_record_ids")
    if not all(isinstance(item, str) for item in record_ids):
        raise VerificationError(f"candidate source_record_ids invalid: {candidate_id}")
    return candidate_id


def check_case(case: Mapping[str, Any], source_paths: set[str], seen_case_ids: set[str], seen_query_ids: set[str], seen_candidate_ids: set[str]) -> str:
    case_id = require_string(case.get("case_id"), "case_id")
    if not case_id.startswith("CASE-M022-"):
        raise VerificationError(f"case_id prefix invalid: {case_id}")
    if case_id in seen_case_ids:
        raise VerificationError(f"duplicate case_id: {case_id}")
    seen_case_ids.add(case_id)
    case_class = require_string(case.get("case_class"), "case_class")
    if case_class not in REQUIRED_CASE_CLASSES:
        raise VerificationError(f"unsupported case_class: {case_class}")
    if case.get("non_authoritative") is not True:
        raise VerificationError(f"case must be non_authoritative: {case_id}")
    query = case.get("query")
    if not isinstance(query, Mapping):
        raise VerificationError(f"query must be object: {case_id}")
    query_id = require_string(query.get("query_id"), "query_id")
    if not query_id.startswith("QUERY-M022-"):
        raise VerificationError(f"query_id prefix invalid: {query_id}")
    if query_id in seen_query_ids:
        raise VerificationError(f"duplicate query_id: {query_id}")
    seen_query_ids.add(query_id)
    expected_result = require_string(query.get("expected_result"), "expected_result")
    if expected_result not in ALLOWED_EXPECTED_RESULTS:
        raise VerificationError(f"unsupported expected_result: {expected_result}")
    query_hash = require_string(query.get("query_text_sha256"), "query_text_sha256")
    if len(query_hash) != 64:
        raise VerificationError(f"query hash invalid: {case_id}")
    require_string(query.get("query_kind"), "query_kind")
    require_string(query.get("scope_id"), "scope_id")
    require_string(query.get("as_of_date"), "as_of_date")
    for ref in require_list(case.get("source_artifact_refs"), "source_artifact_refs"):
        if ref not in source_paths:
            raise VerificationError(f"case source ref not declared: {ref}")
    requirements = case.get("citation_requirements")
    if not isinstance(requirements, Mapping) or not all(requirements.get(key) is True for key in ("requires_evidence_span_id", "requires_source_block_id", "requires_citation_key", "requires_act_edition_id")):
        raise VerificationError(f"citation requirements invalid: {case_id}")
    candidates = require_list(case.get("candidates"), "candidates")
    local_candidate_ids = {check_candidate(candidate, source_paths, seen_candidate_ids) for candidate in candidates if isinstance(candidate, Mapping)}
    if len(local_candidate_ids) != len(candidates):
        raise VerificationError(f"candidate entries must be objects: {case_id}")
    expected_candidate_ids = set(require_list(case.get("expected_candidate_ids"), "expected_candidate_ids"))
    expected_rejected_ids = set(require_list(case.get("expected_rejected_candidate_ids"), "expected_rejected_candidate_ids"))
    if not expected_candidate_ids.issubset(local_candidate_ids):
        raise VerificationError(f"invalid expected candidate reference: {case_id}")
    if not expected_rejected_ids.issubset(local_candidate_ids):
        raise VerificationError(f"invalid expected rejected candidate reference: {case_id}")
    diagnostics = set(require_list(case.get("expected_diagnostic_codes"), "expected_diagnostic_codes"))
    required_diagnostics = EXPECTED_DIAGNOSTICS_BY_CLASS.get(case_class, set())
    if not required_diagnostics.issubset(diagnostics):
        raise VerificationError(f"missing expected diagnostics for {case_id}")
    if expected_result != "selected" and not diagnostics:
        raise VerificationError(f"non-positive case lacks diagnostics: {case_id}")
    return case_class


def verify_fixture(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    check_no_unsafe_payload(payload)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise VerificationError("schema_version mismatch")
    if payload.get("fixture_artifact") != FIXTURE_ARTIFACT:
        raise VerificationError("fixture_artifact mismatch")
    if payload.get("generated_by") != "M022/S02" or payload.get("milestone_id") != "M022-5t4bzn" or payload.get("slice_id") != "S02":
        raise VerificationError("generator or milestone mismatch")
    if payload.get("non_authoritative") is not True:
        raise VerificationError("fixture must be non_authoritative")
    if set(require_list(payload.get("required_case_classes"), "required_case_classes")) != REQUIRED_CASE_CLASSES:
        raise VerificationError("required_case_classes mismatch")
    if set(require_list(payload.get("allowed_expected_results"), "allowed_expected_results")) != ALLOWED_EXPECTED_RESULTS:
        raise VerificationError("allowed_expected_results mismatch")
    if not REQUIRED_NON_CLAIMS.issubset(set(require_list(payload.get("non_claims"), "non_claims"))):
        raise VerificationError("required non_claims missing")
    redaction = payload.get("redaction")
    if not isinstance(redaction, Mapping) or not all(value is True for value in redaction.values()):
        raise VerificationError("redaction values must all be true")
    policy = payload.get("source_anchor_policy")
    if not isinstance(policy, Mapping) or policy.get("stable_sources_preferred") is not True or policy.get("mutable_runtime_hashes_avoided") is not True:
        raise VerificationError("source anchor policy invalid")
    source_paths = check_source_artifacts(payload)
    cases = require_list(payload.get("cases"), "cases")
    if len(cases) < 10:
        raise VerificationError("case_count below representative minimum")
    seen_case_ids: set[str] = set()
    seen_query_ids: set[str] = set()
    seen_candidate_ids: set[str] = set()
    case_classes = {
        check_case(case, source_paths, seen_case_ids, seen_query_ids, seen_candidate_ids)
        for case in cases
        if isinstance(case, Mapping)
    }
    if len(case_classes) != len(cases):
        raise VerificationError("case entries must be objects")
    if not REQUIRED_CASE_CLASSES.issubset(case_classes):
        raise VerificationError("case class coverage mismatch")
    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "fixture_artifact": FIXTURE_ARTIFACT,
        "case_count": len(cases),
        "candidate_count": len(seen_candidate_ids),
        "case_classes": sorted(case_classes),
        "diagnostic_inventory": sorted(set(payload.get("diagnostic_taxonomy", []))),
        "non_authoritative": True,
        "non_claim_boundary": "Representative corpus fixture only; does not validate R035 or prove product retrieval quality.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_fixture(args.fixture)
    except VerificationError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
