"""Offline retrieval case builder use case.

[bounded] M076 S10 application seam extracted from the offline citation
retrieval fixture script. The builder assembles deterministic proof fixtures
only; it does not claim product retrieval quality, legal citation correctness,
or parser extraction correctness.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from law_nexus.ports.offline_retrieval_cases import (
    OFFLINE_RETRIEVAL_CASE_NON_CLAIMS,
    OfflineRetrievalCaseBuildRequest,
)

SCHEMA_VERSION = "offline-citation-retrieval-cases/v1"
GENERATED_BY = "scripts/build-offline-citation-retrieval-cases.py"
VALIDATOR_CONTRACT_VERSION = "retrieval-output-validator/v1"
AS_OF_DATE = "2026-01-01"
SOURCE_CORPUS_ID = "CORPUS-M014-CONSULTANT-44FZ"
SCOPE_ID = "SCOPE-M014-CONSULTANT-44FZ-2026"
RETRIEVAL_RUN_ID = "RET-RUN-M014-OFFLINE-CITATION-001"
FIXTURE_ARTIFACT = "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
CONTRACT_ARTIFACT = "prd/retrieval/offline_citation_retrieval_contract.md"
NON_CLAIMS = list(OFFLINE_RETRIEVAL_CASE_NON_CLAIMS)

FORBIDDEN_PAYLOAD_FIELDS = [
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
    "falkordb_row",
    "runtime_row",
    "generated_answer_prose",
    "legal_advice",
    "llm_reasoning",
]


def replace_m013_with_m014(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("M013", "M014")
    if isinstance(value, list):
        return [replace_m013_with_m014(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_m013_with_m014(item) for key, item in value.items()}
    return value


def record_by_id(records: list[dict[str, Any]], record_id: str) -> dict[str, Any]:
    return next(record for record in records if record["id"] == record_id)


def first_record_by_level(records: list[dict[str, Any]], level: str) -> dict[str, Any]:
    return next(record for record in records if record.get("level") == level)


def base_scope(query_id: str) -> dict[str, str]:
    return {
        "scope_id": SCOPE_ID,
        "query_id": query_id,
        "retrieval_run_id": RETRIEVAL_RUN_ID,
        "as_of_date": AS_OF_DATE,
        "source_corpus_id": SOURCE_CORPUS_ID,
        "validator_contract_version": VALIDATOR_CONTRACT_VERSION,
    }


def validator_output(
    *, query_id: str, output_id: str, citation_key: str, evidence_span_id: str, source_block_id: str
) -> dict[str, Any]:
    return {
        "retrieval_output_id": output_id,
        "output_kind": "retrieval_candidate",
        "scope": base_scope(query_id),
        "citations": [
            {
                "retrieval_output_id": output_id,
                "citation_key": citation_key,
                "evidence_span_id": evidence_span_id,
                "source_block_id": source_block_id,
                "source_document_id": "SD-M014-DOC-CONS-44FZ",
                "legal_unit_id": "LU-M014-HIER-CONS-ARTICLE-0001",
                "act_edition_id": "ED-M014-44FZ-2026-01-01",
            }
        ],
        "answer_claims": [],
    }


def scoped_no_answer_output(query_id: str) -> dict[str, Any]:
    return {
        "retrieval_output_id": "RET-M014-SCOPED-NO-CANDIDATE-001",
        "output_kind": "scoped_no_answer",
        "scope": base_scope(query_id),
        "citations": [],
        "answer_claims": [],
    }


def candidate(
    record: dict[str, Any],
    *,
    candidate_id: str,
    query_id: str,
    reason: str,
    output: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "candidate_id": candidate_id,
        "query_id": query_id,
        "source_record_id": record["id"],
        "source_path": record["source_path"],
        "source_sha256": record["source_sha256"],
        "excerpt_sha256": record["excerpt_sha256"],
        "selection_reason": reason,
    }
    if output is not None:
        payload["validator_output"] = output
    return payload


def diagnostic(
    code: str,
    *,
    case_id: str,
    query_id: str,
    severity: str = "error",
    candidate_id: str | None = None,
    field_path: str | None = None,
) -> dict[str, str]:
    payload = {
        "code": code,
        "severity": severity,
        "case_id": case_id,
        "query_id": query_id,
        "proof_artifact": FIXTURE_ARTIFACT,
    }
    if candidate_id:
        payload["candidate_id"] = candidate_id
    if field_path:
        payload["field_path"] = field_path
    return payload


def case(
    *,
    case_id: str,
    case_class: str,
    query: dict[str, Any],
    candidates: list[dict[str, Any]],
    expected_selection_result: str,
    expected_validator_result: str | None,
    expected_diagnostic_codes: list[str],
    diagnostics: list[dict[str, str]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "case_id": case_id,
        "case_class": case_class,
        "query": query,
        "candidates": candidates,
        "expected_selection_result": expected_selection_result,
        "expected_validator_result": expected_validator_result,
        "expected_diagnostic_codes": expected_diagnostic_codes,
        "diagnostics": diagnostics,
        "source_record_ids": sorted({candidate["source_record_id"] for candidate in candidates}),
        "non_authoritative": True,
    }
    selected = [candidate for candidate in candidates if "validator_output" in candidate]
    if len(selected) == 1:
        payload["output"] = selected[0]["validator_output"]
    elif expected_selection_result == "scoped_no_answer":
        payload["output"] = scoped_no_answer_output(query["query_id"])
    return payload


def _build_payload(request: OfflineRetrievalCaseBuildRequest) -> dict[str, Any]:
    real_cases = request.real_cases
    records = [dict(record) for record in request.hierarchy_records]
    article = first_record_by_level(records, "article")
    chapter = first_record_by_level(records, "chapter")
    clause_1 = first_record_by_level(records, "clause")
    clause_2 = next(
        record
        for record in records
        if record.get("level") == "clause" and record["id"] != clause_1["id"]
    )

    derived_graph = replace_m013_with_m014(deepcopy(real_cases["derived_fixture_graph"]))

    exact_query = {
        "query_id": "QUERY-M014-EXACT-ARTICLE-0001",
        "query_kind": "exact_id_lookup",
        "scope_id": SCOPE_ID,
        "target_level": "article",
        "target_record_id": article["id"],
        "expected_result": "selected",
    }
    marker_query = {
        "query_id": "QUERY-M014-MARKER-ARTICLE-0001",
        "query_kind": "marker_lookup",
        "scope_id": SCOPE_ID,
        "target_level": "article",
        "target_marker": "статья 1.",
        "expected_result": "selected",
    }
    no_answer_query = {
        "query_id": "QUERY-M014-SCOPED-NO-CANDIDATE-001",
        "query_kind": "scoped_no_answer",
        "scope_id": SCOPE_ID,
        "target_level": "article",
        "target_record_id": "HIER-CONS-ARTICLE-9999",
        "expected_result": "scoped_no_answer",
    }
    ambiguous_query = {
        "query_id": "QUERY-M014-AMBIGUOUS-CLAUSE-MARKER-001",
        "query_kind": "ambiguous_lookup",
        "scope_id": SCOPE_ID,
        "target_level": "clause",
        "target_marker": "1",
        "expected_result": "rejected",
    }
    unresolved_query = {
        "query_id": "QUERY-M014-UNRESOLVED-EVIDENCE-001",
        "query_kind": "invalid_candidate",
        "scope_id": SCOPE_ID,
        "target_level": "article",
        "target_record_id": article["id"],
        "expected_result": "rejected",
    }
    unsafe_query = {
        "query_id": "QUERY-M014-UNSAFE-PAYLOAD-001",
        "query_kind": "invalid_candidate",
        "scope_id": SCOPE_ID,
        "target_level": "chapter",
        "target_record_id": chapter["id"],
        "expected_result": "rejected",
        "unsafe_payload_fields": ["raw_text"],
    }

    cases = [
        case(
            case_id="CASE-M014-VALID-EXACT-RECORD-CANDIDATE",
            case_class="valid_exact_record_candidate",
            query=exact_query,
            candidates=[
                candidate(
                    article,
                    candidate_id="CAND-M014-ARTICLE-0001-EXACT",
                    query_id=exact_query["query_id"],
                    reason="exact_record_id_match",
                    output=validator_output(
                        query_id=exact_query["query_id"],
                        output_id="RET-M014-EXACT-ARTICLE-0001",
                        citation_key="CIT-M014-HIER-CONS-ARTICLE-0001",
                        evidence_span_id="EV-M014-HIER-CONS-ARTICLE-0001",
                        source_block_id="SB-M014-HIER-CONS-ARTICLE-0001",
                    ),
                )
            ],
            expected_selection_result="selected",
            expected_validator_result="accepted",
            expected_diagnostic_codes=[],
            diagnostics=[],
        ),
        case(
            case_id="CASE-M014-VALID-MARKER-LEVEL-CANDIDATE",
            case_class="valid_marker_level_candidate",
            query=marker_query,
            candidates=[
                candidate(
                    article,
                    candidate_id="CAND-M014-ARTICLE-0001-MARKER",
                    query_id=marker_query["query_id"],
                    reason="marker_level_match",
                    output=validator_output(
                        query_id=marker_query["query_id"],
                        output_id="RET-M014-MARKER-ARTICLE-0001",
                        citation_key="CIT-M014-HIER-CONS-ARTICLE-0001",
                        evidence_span_id="EV-M014-HIER-CONS-ARTICLE-0001",
                        source_block_id="SB-M014-HIER-CONS-ARTICLE-0001",
                    ),
                )
            ],
            expected_selection_result="selected",
            expected_validator_result="accepted",
            expected_diagnostic_codes=[],
            diagnostics=[],
        ),
        case(
            case_id="CASE-M014-SCOPED-NO-CANDIDATE",
            case_class="scoped_no_candidate",
            query=no_answer_query,
            candidates=[],
            expected_selection_result="scoped_no_answer",
            expected_validator_result="accepted_scoped_no_answer",
            expected_diagnostic_codes=["scoped_no_candidate", "scoped_no_answer"],
            diagnostics=[
                diagnostic(
                    "scoped_no_candidate",
                    case_id="CASE-M014-SCOPED-NO-CANDIDATE",
                    query_id=no_answer_query["query_id"],
                    severity="info",
                )
            ],
        ),
        case(
            case_id="CASE-M014-AMBIGUOUS-CANDIDATE-SET",
            case_class="ambiguous_candidate_set",
            query=ambiguous_query,
            candidates=[
                candidate(
                    clause_1,
                    candidate_id="CAND-M014-CLAUSE-0001-AMBIG",
                    query_id=ambiguous_query["query_id"],
                    reason="ambiguous_candidate_set",
                    output=None,
                ),
                candidate(
                    clause_2,
                    candidate_id="CAND-M014-CLAUSE-0002-AMBIG",
                    query_id=ambiguous_query["query_id"],
                    reason="ambiguous_candidate_set",
                    output=None,
                ),
            ],
            expected_selection_result="rejected",
            expected_validator_result=None,
            expected_diagnostic_codes=["ambiguous_candidate_set"],
            diagnostics=[
                diagnostic(
                    "ambiguous_candidate_set",
                    case_id="CASE-M014-AMBIGUOUS-CANDIDATE-SET",
                    query_id=ambiguous_query["query_id"],
                    field_path="candidates",
                )
            ],
        ),
        case(
            case_id="CASE-M014-UNRESOLVED-CANDIDATE-EVIDENCE",
            case_class="unresolved_candidate_evidence",
            query=unresolved_query,
            candidates=[
                candidate(
                    article,
                    candidate_id="CAND-M014-ARTICLE-0001-UNRESOLVED",
                    query_id=unresolved_query["query_id"],
                    reason="unresolved_candidate_evidence",
                    output=validator_output(
                        query_id=unresolved_query["query_id"],
                        output_id="RET-M014-UNRESOLVED-EVIDENCE-001",
                        citation_key="CIT-M014-HIER-CONS-ARTICLE-0001",
                        evidence_span_id="EV-M014-ORPHAN-SOURCE",
                        source_block_id="SB-M014-MISSING-SOURCE-BLOCK",
                    ),
                )
            ],
            expected_selection_result="rejected",
            expected_validator_result="rejected",
            expected_diagnostic_codes=[
                "unresolved_candidate_evidence",
                "id_path_mismatch",
                "orphaned_source_path",
            ],
            diagnostics=[
                diagnostic(
                    "unresolved_candidate_evidence",
                    case_id="CASE-M014-UNRESOLVED-CANDIDATE-EVIDENCE",
                    query_id=unresolved_query["query_id"],
                    candidate_id="CAND-M014-ARTICLE-0001-UNRESOLVED",
                    field_path="candidates[0].validator_output.citations[0]",
                )
            ],
        ),
        case(
            case_id="CASE-M014-UNSAFE-CANDIDATE-PAYLOAD",
            case_class="unsafe_candidate_payload",
            query=unsafe_query,
            candidates=[
                candidate(
                    chapter,
                    candidate_id="CAND-M014-CHAPTER-0001-UNSAFE",
                    query_id=unsafe_query["query_id"],
                    reason="unsafe_payload_rejected",
                    output=None,
                )
            ],
            expected_selection_result="rejected",
            expected_validator_result=None,
            expected_diagnostic_codes=["unsafe_payload_rejected"],
            diagnostics=[
                diagnostic(
                    "unsafe_payload_rejected",
                    case_id="CASE-M014-UNSAFE-CANDIDATE-PAYLOAD",
                    query_id=unsafe_query["query_id"],
                    candidate_id="CAND-M014-CHAPTER-0001-UNSAFE",
                    field_path="query.unsafe_payload_fields",
                )
            ],
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_artifact": FIXTURE_ARTIFACT,
        "generated_by": GENERATED_BY,
        "contract": CONTRACT_ARTIFACT,
        "requirement": "GATE-G008",
        "non_authoritative": True,
        "source_artifacts": [artifact.as_dict() for artifact in request.source_artifacts],
        "source_summary": {
            "hierarchy_record_count": len(records),
            "selected_record_ids": [article["id"], chapter["id"], clause_1["id"], clause_2["id"]],
        },
        "namespace_strategy": {
            "status": "m014_proof_local_prefixes_allowed_by_shared_validator",
            "must_preserve_unknown_namespace_rejection": True,
        },
        "selection_contract": {
            "allowed_reason_codes": [
                "exact_record_id_match",
                "marker_level_match",
                "scoped_no_candidate",
                "ambiguous_candidate_set",
                "unresolved_candidate_evidence",
                "unsafe_payload_rejected",
            ],
            "forbidden_payload_fields": FORBIDDEN_PAYLOAD_FIELDS,
        },
        "derived_fixture_graph": derived_graph,
        "cases": cases,
        "non_claims": NON_CLAIMS,
    }


def stable_retrieval_case_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class OfflineRetrievalCaseBuilder:
    """Build deterministic offline citation retrieval fixture payloads."""

    def build_payload(self, request: OfflineRetrievalCaseBuildRequest) -> dict[str, Any]:
        """Build the offline retrieval case payload from supplied source data."""

        return _build_payload(request)
