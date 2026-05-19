#!/usr/bin/env python3
"""Verify the M021/S04 EvidenceSpan golden retrieval fixture.

The fixture is non-authoritative and contains safe IDs/hashes only. This
verifier fails closed when required case classes, source anchors, deterministic
IDs, expected candidate references, diagnostics, or redaction boundaries drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json"
SCHEMA_VERSION = "evidence-span-golden-retrieval-cases/v1"
FIXTURE_ARTIFACT = "prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json"

REQUIRED_CASE_CLASSES = {
    "positive_evidence_span",
    "positive_source_block_marker",
    "stale_temporal_negative",
    "ambiguous_candidate_set",
    "unsupported_scope",
    "scoped_no_answer",
}

ALLOWED_EXPECTED_RESULTS = {"selected", "rejected", "ambiguous", "unsupported", "no_answer"}
ALLOWED_EXPECTED_LABELS = {"relevant", "stale", "ambiguous", "unsupported", "no_answer", "unsafe"}

REQUIRED_DIAGNOSTIC_CODES = {
    "stale_temporal_candidate",
    "ambiguous_candidate_set",
    "unsupported_scope",
    "scoped_no_answer",
    "unsafe_payload_rejected",
    "missing_evidence_span",
    "missing_source_block",
    "source_anchor_missing",
    "invalid_expected_candidate_reference",
    "unsafe_fixture_payload",
}

EXPECTED_DIAGNOSTICS_BY_CLASS = {
    "stale_temporal_negative": {"stale_temporal_candidate"},
    "ambiguous_candidate_set": {"ambiguous_candidate_set"},
    "unsupported_scope": {"unsupported_scope"},
    "scoped_no_answer": {"scoped_no_answer"},
}

FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "source_excerpts",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_response_body",
    "secret",
    "secrets",
    "pii",
    "vector",
    "embedding_vector",
    "runtime_row",
    "falkordb_row",
    "generated_answer_prose",
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

REQUIRED_NON_CLAIMS = {
    "Does not prove product retrieval quality.",
    "Does not prove local embedding quality.",
    "Does not prove graph-filtered retrieval quality.",
    "Does not prove production FalkorDB readiness.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove final legal hierarchy correctness.",
    "Does not prove graph-vector/HNSW behavior.",
    "Does not prove pilot or 1000-document readiness.",
    "Does not validate R035.",
}


class VerificationError(Exception):
    """Raised when the S04 fixture is invalid."""


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise VerificationError(f"path is outside repository: {path}") from exc


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise VerificationError("fixture must be a JSON object")
    return data


def walk(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, Mapping):
        for item in value.values():
            values.extend(walk(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(walk(item))
    return values


def check_no_unsafe_payload(data: Mapping[str, Any]) -> None:
    def check_keys(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise VerificationError(f"unsafe field name: {key}")
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)

    check_keys(data)
    serialized = json.dumps(data, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise VerificationError(f"unsafe fixture payload fragment: {fragment}")


def check_source_artifacts(data: Mapping[str, Any]) -> set[str]:
    artifacts = data.get("source_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise VerificationError("source_artifacts must be a non-empty list")
    paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise VerificationError("source_artifacts entries must be objects")
        path_value = artifact.get("path")
        sha_value = artifact.get("sha256")
        if not isinstance(path_value, str) or not path_value:
            raise VerificationError("source artifact path missing")
        if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
            raise VerificationError(f"unsafe source artifact path: {path_value}")
        path = ROOT / path_value
        if not path.exists():
            raise VerificationError(f"source artifact missing: {path_value}")
        if repo_relative(path) != path_value:
            raise VerificationError(f"source artifact is not stable repo-relative path: {path_value}")
        if not isinstance(sha_value, str) or len(sha_value) != 64:
            raise VerificationError(f"source artifact sha256 invalid: {path_value}")
        if sha256_file(path) != sha_value:
            raise VerificationError(f"source artifact sha256 mismatch: {path_value}")
        paths.add(path_value)
    return paths


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerificationError(f"{label} must be a non-empty string")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VerificationError(f"{label} must be a list")
    return value


def check_candidate(candidate: Mapping[str, Any], source_paths: set[str], seen_candidate_ids: set[str]) -> str:
    candidate_id = require_string(candidate.get("candidate_id"), "candidate_id")
    if not candidate_id.startswith("CAND-M021-S04-"):
        raise VerificationError(f"candidate_id prefix invalid: {candidate_id}")
    if candidate_id in seen_candidate_ids:
        raise VerificationError(f"duplicate candidate_id: {candidate_id}")
    seen_candidate_ids.add(candidate_id)
    source_artifact = require_string(candidate.get("source_artifact"), "source_artifact")
    if source_artifact not in source_paths:
        raise VerificationError(f"candidate source_artifact not declared: {source_artifact}")
    source_case_id = require_string(candidate.get("source_case_id"), "source_case_id")
    if not source_case_id.startswith("CASE-"):
        raise VerificationError(f"source_case_id prefix invalid: {source_case_id}")
    expected_label = require_string(candidate.get("expected_label"), "expected_label")
    if expected_label not in ALLOWED_EXPECTED_LABELS:
        raise VerificationError(f"unsupported expected_label: {expected_label}")
    require_string(candidate.get("selection_reason"), "selection_reason")
    for field in ("evidence_span_id", "source_block_id", "citation_key", "act_edition_id"):
        value = candidate.get(field)
        if not isinstance(value, str) or not value:
            raise VerificationError(f"candidate {candidate_id} missing {field}")
    source_record_ids = require_list(candidate.get("source_record_ids"), "source_record_ids")
    if not all(isinstance(item, str) for item in source_record_ids):
        raise VerificationError(f"candidate {candidate_id} source_record_ids must be strings")
    return candidate_id


def check_case(case: Mapping[str, Any], source_paths: set[str], seen_case_ids: set[str], seen_query_ids: set[str], seen_candidate_ids: set[str]) -> str:
    case_id = require_string(case.get("case_id"), "case_id")
    if not case_id.startswith("CASE-M021-S04-"):
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
    if not query_id.startswith("QUERY-M021-S04-"):
        raise VerificationError(f"query_id prefix invalid: {query_id}")
    if query_id in seen_query_ids:
        raise VerificationError(f"duplicate query_id: {query_id}")
    seen_query_ids.add(query_id)
    expected_result = require_string(query.get("expected_result"), "expected_result")
    if expected_result not in ALLOWED_EXPECTED_RESULTS:
        raise VerificationError(f"unsupported expected_result: {expected_result}")
    query_hash = require_string(query.get("query_text_sha256"), "query_text_sha256")
    if len(query_hash) != 64:
        raise VerificationError(f"query_text_sha256 invalid: {case_id}")
    require_string(query.get("scope_id"), "scope_id")
    require_string(query.get("as_of_date"), "as_of_date")

    refs = require_list(case.get("source_artifact_refs"), "source_artifact_refs")
    for ref in refs:
        if ref not in source_paths:
            raise VerificationError(f"case source_artifact_ref not declared: {ref}")
    source_record_ids = require_list(case.get("source_record_ids"), "source_record_ids")
    if not all(isinstance(item, str) for item in source_record_ids):
        raise VerificationError(f"case {case_id} source_record_ids must be strings")

    requirements = case.get("citation_requirements")
    if not isinstance(requirements, Mapping):
        raise VerificationError(f"citation_requirements missing: {case_id}")
    for key in ("requires_evidence_span_id", "requires_source_block_id", "requires_citation_key", "requires_act_edition_id"):
        if requirements.get(key) is not True:
            raise VerificationError(f"citation requirement {key} must be true: {case_id}")

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
    if not diagnostics.issubset(REQUIRED_DIAGNOSTIC_CODES):
        raise VerificationError(f"unsupported diagnostic code: {case_id}")
    required_diagnostics = EXPECTED_DIAGNOSTICS_BY_CLASS.get(case_class, set())
    if not required_diagnostics.issubset(diagnostics):
        raise VerificationError(f"missing expected diagnostics for {case_id}")
    if expected_result in {"rejected", "ambiguous", "unsupported", "no_answer"} and not diagnostics:
        raise VerificationError(f"non-positive case lacks diagnostics: {case_id}")
    return case_class


def verify_fixture(path: Path) -> dict[str, Any]:
    data = load_json(path)
    check_no_unsafe_payload(data)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise VerificationError("schema_version mismatch")
    if data.get("fixture_artifact") != FIXTURE_ARTIFACT:
        raise VerificationError("fixture_artifact mismatch")
    if data.get("generated_by") != "M021/S04":
        raise VerificationError("generated_by mismatch")
    if data.get("milestone_id") != "M021-qk4lze" or data.get("slice_id") != "S04":
        raise VerificationError("milestone/slice mismatch")
    if data.get("non_authoritative") is not True:
        raise VerificationError("fixture must be non_authoritative")
    if set(require_list(data.get("required_case_classes"), "required_case_classes")) != REQUIRED_CASE_CLASSES:
        raise VerificationError("required_case_classes mismatch")
    if set(require_list(data.get("allowed_expected_results"), "allowed_expected_results")) != ALLOWED_EXPECTED_RESULTS:
        raise VerificationError("allowed_expected_results mismatch")
    if set(require_list(data.get("diagnostic_taxonomy"), "diagnostic_taxonomy")) != REQUIRED_DIAGNOSTIC_CODES:
        raise VerificationError("diagnostic_taxonomy mismatch")
    source_paths = check_source_artifacts(data)
    non_claims = set(require_list(data.get("non_claims"), "non_claims"))
    if not REQUIRED_NON_CLAIMS.issubset(non_claims):
        raise VerificationError("required non_claims missing")
    redaction = data.get("redaction")
    if not isinstance(redaction, Mapping) or not all(value is True for value in redaction.values()):
        raise VerificationError("redaction values must all be true")

    cases = require_list(data.get("cases"), "cases")
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
    if case_classes != REQUIRED_CASE_CLASSES:
        raise VerificationError("case class coverage mismatch")
    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "fixture_artifact": FIXTURE_ARTIFACT,
        "case_count": len(cases),
        "candidate_count": len(seen_candidate_ids),
        "case_classes": sorted(case_classes),
        "diagnostic_taxonomy": sorted(REQUIRED_DIAGNOSTIC_CODES),
        "non_authoritative": True,
        "non_claim_boundary": "Fixture construction only; does not validate R035 or prove retrieval quality.",
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
