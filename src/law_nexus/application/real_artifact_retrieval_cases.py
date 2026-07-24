"""Real artifact retrieval case builder use case.

[bounded] M076 S11 application seam extracted from the real artifact
retrieval fixture script. The builder assembles deterministic proof fixtures
only; it does not claim retrieval quality, legal correctness, parser
completeness, or production runtime readiness.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from law_nexus.ports.real_artifact_retrieval_cases import (
    REAL_ARTIFACT_RETRIEVAL_CASE_NON_CLAIMS,
    RealArtifactRetrievalCaseBuildRequest,
)

SCHEMA_VERSION = "real-artifact-retrieval-cases/v1"
SCOPE_ID = "SCOPE-M013-CONSULTANT-44FZ-2026-001"
SOURCE_CORPUS_ID = "CORPUS-M013-CONSULTANT-44FZ"
RETRIEVAL_RUN_ID = "RUN-M013-REAL-ARTIFACT-001"
QUERY_ID = "QUERY-M013-REAL-ARTIFACT-001"
AS_OF_DATE = "2026-01-01"
VALIDATOR_CONTRACT_VERSION = "retrieval-output-validator/v1"
FIXTURE_ARTIFACT = "prd/retrieval/fixtures/real_artifact_retrieval_cases.json"
GENERATED_BY = "scripts/build-real-artifact-retrieval-cases.py"
NON_CLAIMS = list(REAL_ARTIFACT_RETRIEVAL_CASE_NON_CLAIMS)

REQUIRED_CASES = [
    ("CASE-M013-VALID-REAL-ARTIFACT", "valid_real_artifact_path", "accepted", []),
    (
        "CASE-M013-MISSING-EVIDENCE-ID",
        "missing_evidence_id",
        "rejected",
        ["missing_required_field"],
    ),
    (
        "CASE-M013-UNRESOLVED-SOURCE-BLOCK",
        "unresolved_source_block",
        "rejected",
        ["id_path_mismatch", "orphaned_source_path"],
    ),
    (
        "CASE-M013-AMBIGUOUS-CITATION",
        "ambiguous_citation_key",
        "rejected",
        ["ambiguous_citation_key"],
    ),
    ("CASE-M013-WRONG-EDITION-PROXY", "wrong_edition_proxy", "rejected", ["wrong_edition"]),
    (
        "CASE-M013-SCOPED-NO-ANSWER",
        "scoped_no_answer",
        "accepted_scoped_no_answer",
        ["scoped_no_answer"],
    ),
    (
        "CASE-M013-UNSAFE-NO-ANSWER-WITH-CITATION",
        "unsafe_no_answer_with_citation",
        "rejected",
        ["unsafe_no_answer_shape"],
    ),
]


def source_identity(
    hierarchy_summary: Mapping[str, Any], article_record: Mapping[str, Any]
) -> tuple[str, str]:
    """Return source path and SHA from summary metadata or selected record."""

    source = hierarchy_summary.get("source")
    if isinstance(source, Mapping):
        source_path = str(source["path"])
        source_sha256 = str(source["sha256"])
        if source_path != article_record["source_path"]:
            raise ValueError(
                "source path mismatch between hierarchy summary and selected article record"
            )
        if source_sha256 != article_record["source_sha256"]:
            raise ValueError(
                "source sha256 mismatch between hierarchy summary and selected article record"
            )
        return source_path, source_sha256
    return str(article_record["source_path"]), str(article_record["source_sha256"])


def select_records(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    document = next(record for record in records if record.get("level") == "document")
    article = next(record for record in records if record.get("level") == "article")
    return document, article


def base_scope() -> dict[str, str]:
    return {
        "scope_id": SCOPE_ID,
        "query_id": QUERY_ID,
        "retrieval_run_id": RETRIEVAL_RUN_ID,
        "as_of_date": AS_OF_DATE,
        "source_corpus_id": SOURCE_CORPUS_ID,
        "validator_contract_version": VALIDATOR_CONTRACT_VERSION,
    }


def valid_citation() -> dict[str, str]:
    return {
        "retrieval_output_id": "RET-M013-REAL-ARTIFACT-001",
        "citation_key": "CIT-M013-HIER-CONS-ARTICLE-0001",
        "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
        "source_block_id": "SB-M013-HIER-CONS-ARTICLE-0001",
        "source_document_id": "SD-M013-DOC-CONS-44FZ",
        "legal_unit_id": "LU-M013-HIER-CONS-ARTICLE-0001",
        "act_edition_id": "ED-M013-44FZ-2026-01-01",
    }


def make_output(case_id: str, case_class: str) -> dict[str, Any]:
    if case_class == "scoped_no_answer":
        return {
            "retrieval_output_id": "RET-M013-SCOPED-NO-ANSWER",
            "output_kind": "scoped_no_answer",
            "scope": base_scope(),
            "citations": [],
            "answer_claims": [],
        }

    citation = valid_citation()
    retrieval_output_id = citation["retrieval_output_id"]
    output_kind = "retrieval_candidate"
    citations = [citation]
    answer_claims: list[dict[str, Any]] = []

    if case_class == "missing_evidence_id":
        citation = citation.copy()
        citation.pop("evidence_span_id")
        citations = [citation]
    elif case_class == "unresolved_source_block":
        citation = citation.copy()
        citation["evidence_span_id"] = "EV-M013-ORPHAN-SOURCE"
        citation["source_block_id"] = "SB-M013-MISSING-SOURCE-BLOCK"
        citations = [citation]
    elif case_class == "ambiguous_citation_key":
        citation = citation.copy()
        citation["citation_key"] = "CIT-M013-AMBIG"
        citations = [citation]
    elif case_class == "wrong_edition_proxy":
        citation = citation.copy()
        citation["act_edition_id"] = "ED-M013-44FZ-1900-01-01"
        citations = [citation]
    elif case_class == "unsafe_no_answer_with_citation":
        retrieval_output_id = "RET-M013-UNSAFE-NO-ANSWER-WITH-CITATION"
        citation = citation.copy()
        citation["retrieval_output_id"] = retrieval_output_id
        output_kind = "scoped_no_answer"
        citations = [citation]

    return {
        "retrieval_output_id": retrieval_output_id,
        "output_kind": output_kind,
        "scope": base_scope(),
        "citations": citations,
        "answer_claims": answer_claims,
    }


def _build_payload(request: RealArtifactRetrievalCaseBuildRequest) -> dict[str, Any]:
    hierarchy_summary = request.hierarchy_summary
    staging_graph = request.staging_graph
    hierarchy_records = [dict(record) for record in request.hierarchy_records]
    document_record, article_record = select_records(hierarchy_records)

    source_path, source_sha256 = source_identity(hierarchy_summary, article_record)

    cases = []
    expected_diagnostics: dict[str, list[str]] = {}
    for case_id, case_class, expected_result, expected_codes in REQUIRED_CASES:
        cases.append(
            {
                "case_id": case_id,
                "case_class": case_class,
                "expected_result": expected_result,
                "expected_diagnostic_codes": expected_codes,
                "source_record_ids": [article_record["id"]]
                if case_class != "scoped_no_answer"
                else [],
                "output": make_output(case_id, case_class),
            }
        )
        expected_diagnostics[case_id] = expected_codes

    return {
        "schema_version": SCHEMA_VERSION,
        "non_authoritative": True,
        "contract_version": VALIDATOR_CONTRACT_VERSION,
        "requirement": "R034",
        "fixture_artifact": FIXTURE_ARTIFACT,
        "generated_by": GENERATED_BY,
        "source_artifacts": [artifact.as_dict() for artifact in request.source_artifacts],
        "namespace_strategy": {
            "status": "safe_namespace_extension_selected",
            "current_validator_prefixes": ["*-M012-*", "*-M013-*"],
            "proposed_m013_prefixes": [
                "RET-M013-*",
                "CIT-M013-*",
                "EV-M013-*",
                "SB-M013-*",
                "SD-M013-*",
                "LU-M013-*",
                "ED-M013-*",
                "AC-M013-*",
            ],
            "implemented_s02_option": "safe_namespace_extension",
        },
        "fixture_boundaries": {
            "proof_only": True,
            "real_artifact_derived": True,
            "source_text_persisted": False,
            "excerpt_hashes_only": True,
            "falkordb_runtime_executed": False,
            "embedding_quality_measured": False,
        },
        "non_claims": NON_CLAIMS,
        "source_summary": {
            "source_path": source_path,
            "source_sha256": source_sha256,
            "hierarchy_record_count": len(hierarchy_records),
            "staging_graph_status": staging_graph["graph_status"],
            "staging_graph_diagnostic_count": staging_graph["diagnostic_count"],
        },
        "derived_fixture_graph": {
            "legal_acts": [
                {
                    "legal_act_id": "LA-M013-44FZ",
                    "source_record_id": document_record["id"],
                    "source_path": source_path,
                    "source_sha256": source_sha256,
                    "status": "bounded_proxy",
                }
            ],
            "act_editions": [
                {
                    "act_edition_id": "ED-M013-44FZ-2026-01-01",
                    "legal_act_id": "LA-M013-44FZ",
                    "valid_from": AS_OF_DATE,
                    "valid_to": None,
                    "status": "active",
                    "proof_boundary": "bounded_source_snapshot_proxy",
                    "source_sha256": source_sha256,
                }
            ],
            "legal_units": [
                {
                    "legal_unit_id": "LU-M013-HIER-CONS-ARTICLE-0001",
                    "source_hierarchy_id": article_record["id"],
                    "level": article_record["level"],
                    "parent_id": article_record["parent_id"],
                    "act_edition_id": "ED-M013-44FZ-2026-01-01",
                    "legal_act_id": "LA-M013-44FZ",
                    "status": "bounded_hierarchy_proxy",
                }
            ],
            "source_documents": [
                {
                    "source_document_id": "SD-M013-DOC-CONS-44FZ",
                    "source_corpus_id": SOURCE_CORPUS_ID,
                    "source_path": source_path,
                    "source_sha256": source_sha256,
                    "source_record_id": document_record["id"],
                    "status": "active",
                }
            ],
            "source_blocks": [
                {
                    "source_block_id": "SB-M013-HIER-CONS-ARTICLE-0001",
                    "source_document_id": "SD-M013-DOC-CONS-44FZ",
                    "source_hierarchy_id": article_record["id"],
                    "location": article_record["location"],
                    "excerpt_sha256": article_record["excerpt_sha256"],
                    "status": "active",
                }
            ],
            "evidence_spans": [
                {
                    "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
                    "source_block_id": "SB-M013-HIER-CONS-ARTICLE-0001",
                    "source_document_id": "SD-M013-DOC-CONS-44FZ",
                    "legal_unit_id": "LU-M013-HIER-CONS-ARTICLE-0001",
                    "act_edition_id": "ED-M013-44FZ-2026-01-01",
                    "source_hierarchy_id": article_record["id"],
                    "excerpt_sha256": article_record["excerpt_sha256"],
                    "status": "active",
                },
                {
                    "evidence_span_id": "EV-M013-ORPHAN-SOURCE",
                    "source_block_id": "SB-M013-MISSING-SOURCE-BLOCK",
                    "source_document_id": "SD-M013-DOC-CONS-44FZ",
                    "legal_unit_id": "LU-M013-HIER-CONS-ARTICLE-0001",
                    "act_edition_id": "ED-M013-44FZ-2026-01-01",
                    "source_hierarchy_id": article_record["id"],
                    "excerpt_sha256": article_record["excerpt_sha256"],
                    "status": "orphan_fixture",
                },
            ],
            "citation_bindings": [
                {
                    "citation_key": "CIT-M013-HIER-CONS-ARTICLE-0001",
                    "scope_id": SCOPE_ID,
                    "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
                    "binding_role": "unique",
                },
                {
                    "citation_key": "CIT-M013-AMBIG",
                    "scope_id": SCOPE_ID,
                    "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
                    "binding_role": "ambiguous",
                },
                {
                    "citation_key": "CIT-M013-AMBIG",
                    "scope_id": SCOPE_ID,
                    "evidence_span_id": "EV-M013-HIER-CONS-ARTICLE-0001",
                    "binding_role": "ambiguous",
                },
            ],
        },
        "cases": cases,
        "expected_diagnostics": expected_diagnostics,
    }


def stable_real_artifact_retrieval_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class RealArtifactRetrievalCaseBuilder:
    """Build deterministic real artifact retrieval fixture payloads."""

    def build_payload(self, request: RealArtifactRetrievalCaseBuildRequest) -> dict[str, Any]:
        """Build the real artifact retrieval case payload from supplied source data."""

        return _build_payload(request)
