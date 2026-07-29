from __future__ import annotations

import json
from pathlib import Path

from law_nexus.application.generated_cypher_policy import (
    GENERATED_CYPHER_POLICY_NON_CLAIMS,
    GeneratedCypherPolicy,
    GeneratedCypherValidationRequest,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "tests/fixtures/m002_legalgraph_schema_contract.json"


def _schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_policy_accepts_explicit_read_only_evidence_query() -> None:
    query = """MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
                    (span)-[:IN_BLOCK]->(block)
             WHERE article.id = $article_id
             RETURN article.id, span.id, block.id, block.source_id, span.start_offset, span.end_offset
             LIMIT 5"""

    result = GeneratedCypherPolicy().validate(
        GeneratedCypherValidationRequest(
            query=query, schema_contract=_schema(), query_case="article_evidence", generated=False
        )
    )

    assert result.accepted is True
    assert result.rejection_codes == ()
    assert result.non_claims == GENERATED_CYPHER_POLICY_NON_CLAIMS
    assert result.to_graph_store_query().read_only is True
    assert result.to_graph_store_query().generated is False


def test_policy_rejects_generated_query_by_default_even_if_read_only() -> None:
    query = "MATCH (span:EvidenceSpan) RETURN span.id LIMIT 5"

    result = GeneratedCypherPolicy().validate(
        GeneratedCypherValidationRequest(
            query=query, schema_contract=_schema(), query_case="generated_candidate", generated=True
        )
    )

    assert result.accepted is False
    assert "E_GENERATED_QUERY_UNAPPROVED" in result.rejection_codes
    assert result.to_graph_store_query() is None


def test_policy_rejects_mutating_and_multi_statement_queries() -> None:
    policy = GeneratedCypherPolicy()

    mutating = policy.validate(
        GeneratedCypherValidationRequest(
            query="CREATE (:LegalUnit) RETURN 1",
            schema_contract=_schema(),
            query_case="mutating",
            generated=False,
        )
    )
    multi = policy.validate(
        GeneratedCypherValidationRequest(
            query="MATCH (n:EvidenceSpan) RETURN n.id LIMIT 5; MATCH (m:SourceBlock) RETURN m.id LIMIT 5",
            schema_contract=_schema(),
            query_case="multi",
            generated=False,
        )
    )

    assert mutating.accepted is False
    assert "E_WRITE_OPERATION" in mutating.rejection_codes
    assert multi.accepted is False
    assert "E_MULTIPLE_STATEMENTS" in multi.rejection_codes


def test_policy_rejects_unsafe_procedure_and_raw_context() -> None:
    policy = GeneratedCypherPolicy()

    procedure = policy.validate(
        GeneratedCypherValidationRequest(
            query="CALL db.labels() YIELD label RETURN label LIMIT 5",
            schema_contract=_schema(),
            query_case="procedure",
        )
    )
    raw_context = policy.validate(
        GeneratedCypherValidationRequest(
            query="MATCH (span:EvidenceSpan) RETURN span.id LIMIT 5",
            schema_contract=_schema(),
            query_case="raw_context",
            request_context={"raw_legal_text": "forbidden"},
        )
    )

    assert procedure.accepted is False
    assert "E_PROCEDURE_NOT_ALLOWLISTED" in procedure.rejection_codes
    assert raw_context.accepted is False
    assert "E_UNSAFE_CONTEXT_FIELD" in raw_context.rejection_codes


def test_policy_diagnostics_are_bounded_and_non_authoritative() -> None:
    result = GeneratedCypherPolicy().validate(
        GeneratedCypherValidationRequest(
            query="DELETE n", schema_contract=_schema(), query_case="delete", generated=False
        )
    )

    assert result.accepted is False
    assert result.non_authoritative is True
    assert "Does not prove FalkorDB runtime safety." in result.non_claims
    payload = result.to_dict()
    assert "raw_legal_text" not in json.dumps(payload, ensure_ascii=False)
    assert payload["query_case"] == "delete"
