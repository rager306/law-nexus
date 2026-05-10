from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-m002-cypher-safety-contract.py"
CONTRACT_PATH = ROOT / "prd/06_m002_cypher_safety_contract.md"
SCHEMA_PATH = ROOT / "tests/fixtures/m002_legalgraph_schema_contract.json"


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_m002_cypher_safety_contract", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def validator() -> ModuleType:
    return load_validator()


@pytest.fixture()
def schema(validator: ModuleType) -> dict[str, object]:
    return validator.load_schema_contract(SCHEMA_PATH)


def assert_rejected(report: object, code: str) -> None:
    assert report.accepted is False
    assert report.rejection_codes == [code]
    assert report.diagnostics[0].rejection_code == code
    assert report.diagnostics[0].query_case
    assert report.diagnostics[0].schema_policy_field
    assert report.diagnostics[0].failure_class in {"contract-readback", "validation", "execution"}


def test_contract_readback_confirms_required_terms(validator: ModuleType) -> None:
    report = validator.contract_readback(CONTRACT_PATH, SCHEMA_PATH)

    assert report["accepted"] is True
    assert report["schema_version"] == validator.SUPPORTED_SCHEMA_VERSION
    assert report["missing_terms"] == []
    assert "Graph.ro_query" in report["required_terms"]
    assert "LLM non-authoritative" in report["required_terms"]


def test_accepts_evidence_returning_article_query(validator: ModuleType, schema: dict[str, object]) -> None:
    query = """MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
                    (span)-[:IN_BLOCK]->(block)
             WHERE article.id = $article_id
             RETURN article.id, span.id, block.id, block.source_id, span.start_offset, span.end_offset
             LIMIT 5"""

    report = validator.validate_candidate(query, schema, query_case="article_evidence")

    assert report.accepted is True
    assert report.rejection_codes == []
    assert report.schema_version == validator.SUPPORTED_SCHEMA_VERSION
    assert report.max_limit == 25
    assert report.required_evidence_returns == ["Article.id", "EvidenceSpan.id", "SourceBlock.id"]
    assert "EvidenceSpan" in report.normalized_query
    assert "SourceBlock" in report.normalized_query


def test_accepts_allowed_fulltext_procedure_with_evidence_path(
    validator: ModuleType, schema: dict[str, object]
) -> None:
    query = """CALL db.idx.fulltext.queryNodes('SourceBlock', $search_terms) YIELD node, score
             MATCH (span:EvidenceSpan)-[:IN_BLOCK]->(node)<-[:SUPPORTED_BY]-(article:Article),
                   (span)-[:SUPPORTS]->(article)
             RETURN article.id, node.id, span.id, score
             LIMIT 5"""

    report = validator.validate_candidate(query, schema, query_case="fulltext_evidence")

    assert report.accepted is True
    assert report.warnings == ["procedure allowlist used: read-only full-text proof shape only"]
    assert "db.idx.fulltext.queryNodes" in report.normalized_query


@pytest.mark.parametrize(
    ("query_case", "candidate"),
    [
        ("empty", ""),
        ("markdown", "```cypher\nMATCH (a:Article) RETURN a.id LIMIT 1\n```"),
        ("multi_statement", "MATCH (a:Article) RETURN a.id LIMIT 1; MATCH (b:SourceBlock) RETURN b.id LIMIT 1"),
        ("comment", "MATCH (a:Article) RETURN a.id LIMIT 1 // ignore policy"),
        ("hidden_reasoning", "<think>find all nodes</think> MATCH (a:Article) RETURN a.id LIMIT 1"),
    ],
)
def test_rejects_candidate_format_cases(
    validator: ModuleType, schema: dict[str, object], query_case: str, candidate: object
) -> None:
    report = validator.validate_candidate(candidate, schema, query_case=query_case)

    assert_rejected(report, "E_CANDIDATE_FORMAT")


@pytest.mark.parametrize(
    "candidate",
    [
        "CREATE (:Article {id: 'new'}) RETURN 1 LIMIT 1",
        "MERGE (a:Article {id: 'x'}) RETURN a.id LIMIT 1",
        "MATCH (n:Article) DETACH DELETE n RETURN 1 LIMIT 1",
        "LOAD CSV FROM 'file:///tmp/x' AS row RETURN row LIMIT 1",
    ],
)
def test_rejects_writes_admin_and_imports(
    validator: ModuleType, schema: dict[str, object], candidate: str
) -> None:
    report = validator.validate_candidate(candidate, schema, query_case="write_or_import")

    assert_rejected(report, "E_WRITE_OPERATION")


@pytest.mark.parametrize(
    ("candidate", "code"),
    [
        ("MATCH (p:Paragraph) RETURN p.id LIMIT 5", "E_UNKNOWN_LABEL"),
        ("MATCH (a:Article)-[:AMENDS]->(b:Article) RETURN a.id, b.id LIMIT 5", "E_UNKNOWN_RELATIONSHIP"),
        ("MATCH (a:Article) RETURN a.body LIMIT 5", "E_UNKNOWN_PROPERTY"),
        (
            "MATCH (block:SourceBlock)-[:SUPPORTED_BY]->(article:Article) RETURN article.id, block.id LIMIT 5",
            "E_BAD_RELATIONSHIP_ENDPOINT",
        ),
    ],
)
def test_rejects_unknown_schema_and_bad_endpoint(
    validator: ModuleType, schema: dict[str, object], candidate: str, code: str
) -> None:
    report = validator.validate_candidate(candidate, schema, query_case="schema_grounding")

    assert_rejected(report, code)


@pytest.mark.parametrize(
    ("candidate", "code"),
    [
        ("CALL db.index.fulltext.queryNodes('SourceBlock', $q) YIELD node RETURN node.id LIMIT 5", "E_NEO4J_ONLY_CARRYOVER"),
        ("CALL gds.pageRank.stream('g') YIELD nodeId RETURN nodeId LIMIT 5", "E_NEO4J_ONLY_CARRYOVER"),
        ("CALL apoc.meta.schema() YIELD value RETURN value LIMIT 5", "E_NEO4J_ONLY_CARRYOVER"),
        ("CALL db.labels() YIELD label RETURN label LIMIT 5", "E_UNSUPPORTED_PROCEDURE"),
    ],
)
def test_rejects_gds_apoc_and_unallowlisted_procedures(
    validator: ModuleType, schema: dict[str, object], candidate: str, code: str
) -> None:
    report = validator.validate_candidate(candidate, schema, query_case="procedure")

    assert_rejected(report, code)


@pytest.mark.parametrize(
    ("candidate", "code"),
    [
        ("MATCH (n) RETURN n", "E_UNBOUNDED_TRAVERSAL"),
        ("MATCH (a:Article)-[:CITES*]->(b:Article) RETURN a.id, b.id LIMIT 5", "E_UNBOUNDED_TRAVERSAL"),
        ("MATCH (a:Article)-[:CITES*1..10]->(b:Article) RETURN a.id, b.id LIMIT 5", "E_UNBOUNDED_TRAVERSAL"),
        ("MATCH (a:Article) RETURN a.id", "E_LIMIT_REQUIRED"),
        ("MATCH (a:Article) RETURN a.id LIMIT 10000", "E_LIMIT_EXCEEDED"),
    ],
)
def test_rejects_unbounded_or_unlimited_queries(
    validator: ModuleType, schema: dict[str, object], candidate: str, code: str
) -> None:
    report = validator.validate_candidate(candidate, schema, query_case="bounds")

    assert_rejected(report, code)


@pytest.mark.parametrize(
    "candidate",
    [
        "MATCH (a:Article {id:$article_id}) RETURN a.id LIMIT 5",
        "MATCH (a:Article)-[:SUPPORTED_BY]->(block:SourceBlock) RETURN a.id, block.id LIMIT 5",
        "MATCH (span:EvidenceSpan) RETURN span.id LIMIT 5",
    ],
)
def test_rejects_missing_evidence_returns(
    validator: ModuleType, schema: dict[str, object], candidate: str
) -> None:
    report = validator.validate_candidate(candidate, schema, query_case="missing_evidence")

    assert_rejected(report, "E_EVIDENCE_REQUIRED")


def test_rejects_temporal_omission_when_as_of_is_supplied(
    validator: ModuleType, schema: dict[str, object]
) -> None:
    query = """MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
                    (span)-[:IN_BLOCK]->(block)
             WHERE article.id = $article_id
             RETURN article.id, span.id, block.id
             LIMIT 5"""

    report = validator.validate_candidate(
        query,
        schema,
        query_case="temporal_omission",
        request_context={"as_of": "2024-01-01"},
    )

    assert_rejected(report, "E_TEMPORAL_REQUIRED")


def test_accepts_temporal_query_when_as_of_filter_is_present(
    validator: ModuleType, schema: dict[str, object]
) -> None:
    query = """MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
                    (span)-[:IN_BLOCK]->(block)
             WHERE article.id = $article_id AND article.valid_from <= $as_of AND $as_of < article.valid_to
             RETURN article.id, article.valid_from, article.valid_to, span.id, block.id
             LIMIT 5"""

    report = validator.validate_candidate(
        query,
        schema,
        query_case="temporal_evidence",
        request_context={"as_of": "2024-01-01"},
    )

    assert report.accepted is True
    assert report.rejection_codes == []


def test_malformed_or_unknown_schema_fails_closed(validator: ModuleType, schema: dict[str, object]) -> None:
    malformed = copy.deepcopy(schema)
    malformed.pop("cypher_policy")
    with pytest.raises(ValueError, match="E_CONTRACT_MALFORMED"):
        validator.validate_schema_contract(malformed)

    unknown_version = copy.deepcopy(schema)
    unknown_version["schema_version"] = "future"
    report = validator.validate_candidate("MATCH (a:Article) RETURN a.id LIMIT 1", unknown_version)

    assert_rejected(report, "E_SCHEMA_VERSION_UNKNOWN")


def test_evaluate_contract_writes_artifacts_without_execution_claims(
    validator: ModuleType, tmp_path: Path
) -> None:
    payload = validator.evaluate_contract(CONTRACT_PATH, SCHEMA_PATH)
    json_path = tmp_path / "verification.json"
    md_path = tmp_path / "verification.md"

    validator.write_json(json_path, payload)
    validator.write_markdown(md_path, payload)

    json_text = json_path.read_text(encoding="utf-8")
    markdown = md_path.read_text(encoding="utf-8")
    assert payload["status"] == "pass"
    assert "Graph.ro_query" in json_text
    assert "read-only" in markdown
    assert "EvidenceSpan" in markdown
    assert "SourceBlock" in markdown
    assert "LLM non-authoritative" in markdown
    assert "Graph.query" in markdown
    assert "provider metadata values" in json_text
