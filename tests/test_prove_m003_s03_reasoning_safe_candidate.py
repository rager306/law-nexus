from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-m003-s03-reasoning-safe-candidate.py"


FORBIDDEN_ARTIFACT_TERMS = (
    "Authorization",
    "Bearer",
    "api_key",
    "api-key",
    "sk-",
    "BEGIN PRIVATE KEY",
    "RAW_LEGAL_TEXT_SENTINEL",
    "raw_provider_body_value",
    "raw_response",
    "request_prompt",
    "reasoning_text_value",
    "raw_legal_text_value",
    "falkordb_rows_value",
)


def load_proof() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prove_m003_s03_reasoning_safe_candidate", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def proof() -> ModuleType:
    return load_proof()


def provider_payload(content: Any, **message_extra: Any) -> dict[str, Any]:
    return {"choices": [{"message": {"content": content, **message_extra}}]}


def assert_no_forbidden_terms(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for term in FORBIDDEN_ARTIFACT_TERMS:
        assert term not in serialized


@pytest.mark.parametrize(
    ("content", "starts_with"),
    [
        ("  MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article) RETURN article.id, span.id LIMIT 5\n", "MATCH"),
        ("\nCALL db.idx.fulltext.queryNodes('SourceBlock', $search_terms) YIELD node RETURN node.id LIMIT 5", "CALL"),
    ],
)
def test_accepts_clean_match_and_call_after_whitespace_trim(
    proof: ModuleType, content: str, starts_with: str
) -> None:
    result = proof.classify_provider_response(provider_payload(content))

    assert result["accepted"] is True
    assert result["root_cause"] == "none"
    assert result["candidate"]["normalized_text"] == content.strip()
    assert result["candidate"]["starts_with"] == starts_with
    assert result["candidate"]["has_think_tag"] is False
    assert result["candidate"]["has_markdown_fence"] is False
    assert result["candidate"]["has_prose_prefix"] is False
    assert result["candidate"]["has_prose_suffix"] is False
    assert result["candidate"]["raw_provider_body_persisted"] is False
    assert result["reasoning"]["present"] is False


def test_separated_reasoning_metadata_does_not_contaminate_clean_candidate(proof: ModuleType) -> None:
    result = proof.classify_provider_response(
        provider_payload(
            "MATCH (block:SourceBlock)<-[:SUPPORTED_BY]-(article:Article) RETURN article.id, block.id LIMIT 5",
            reasoning_details=[{"type": "summary", "text": "do not persist this reasoning"}],
        )
    )

    assert result["accepted"] is True
    assert result["reasoning"]["present"] is True
    assert result["reasoning"]["separated"] is True
    assert result["reasoning"]["detail_count"] == 1
    assert result["candidate"]["has_think_tag"] is False
    assert "reasoning_text" not in json.dumps(result, ensure_ascii=False)
    assert "do not persist this reasoning" not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize(
    ("case_name", "payload", "root_cause", "category"),
    [
        ("empty", provider_payload(""), "empty-content", "malformed-content"),
        ("whitespace", provider_payload("   \n"), "empty-content", "malformed-content"),
        ("ok", provider_payload("OK"), "non-cypher-output", "non-cypher"),
        ("non_string", provider_payload({"text": "MATCH (n) RETURN n LIMIT 1"}), "provider-schema-mismatch", "malformed-provider-shape"),
        ("missing_choices", {}, "provider-schema-mismatch", "malformed-provider-shape"),
        ("missing_message", {"choices": [{}]}, "provider-schema-mismatch", "malformed-provider-shape"),
        (
            "think",
            provider_payload("<think>reason</think> MATCH (n) RETURN n LIMIT 1"),
            "reasoning-contamination",
            "reasoning-tag-contamination",
        ),
        (
            "prose_prefix",
            provider_payload("Here is the query: MATCH (n) RETURN n LIMIT 1"),
            "non-cypher-output",
            "prose-prefix",
        ),
        (
            "prose_suffix",
            provider_payload("MATCH (n) RETURN n LIMIT 1\nThis returns nodes."),
            "prose-contamination",
            "prose-suffix",
        ),
        (
            "markdown",
            provider_payload("```cypher\nMATCH (n) RETURN n LIMIT 1\n```"),
            "markdown-contamination",
            "markdown-fence-contamination",
        ),
        (
            "comment",
            provider_payload("MATCH (n) RETURN n LIMIT 1 // explanation"),
            "candidate-comment-contamination",
            "comment-contamination",
        ),
        (
            "multi_statement",
            provider_payload("MATCH (n) RETURN n LIMIT 1; MATCH (m) RETURN m LIMIT 1"),
            "candidate-multi-statement",
            "multi-statement",
        ),
    ],
)
def test_rejects_malformed_and_contaminated_provider_shapes(
    proof: ModuleType, case_name: str, payload: dict[str, Any], root_cause: str, category: str
) -> None:
    result = proof.classify_provider_response(payload)

    assert result["accepted"] is False, case_name
    assert result["root_cause"] == root_cause
    assert category in result["candidate"]["categories"]
    assert "normalized_text" not in result["candidate"]
    assert result["candidate"]["raw_provider_body_persisted"] is False
    assert result["candidate"]["text_length"] >= 0
    assert result["candidate"]["sha256_12"] is None or len(result["candidate"]["sha256_12"]) == 12


def test_artifact_helpers_expose_safe_runtime_signals_without_forbidden_fields(proof: ModuleType) -> None:
    classification = proof.classify_provider_response(
        provider_payload(
            "MATCH (span:EvidenceSpan)-[:IN_BLOCK]->(block:SourceBlock) RETURN span.id, block.id LIMIT 5",
            reasoning_details=[{"type": "summary", "text": "hidden chain of thought"}],
        )
    )

    confirmed = proof.build_confirmed_runtime_artifact(
        classification=classification,
        provider_attempts=1,
        commands=[{"command": "fixture", "exit_code": 0, "duration_ms": 1}],
    )
    blocked = proof.build_blocked_credential_artifact()
    failed = proof.build_failed_runtime_artifact(
        root_cause="provider-schema-mismatch",
        phase="provider-response",
        classification=proof.classify_provider_response({"choices": []}),
        provider_attempts=1,
    )

    assert confirmed["status"] == "confirmed-runtime"
    assert confirmed["root_cause"] == "none"
    assert confirmed["phase"] == "candidate-classification"
    assert confirmed["provider_attempts"] == 1
    assert confirmed["candidate"]["normalized_text"].startswith("MATCH")
    assert confirmed["reasoning"]["present"] is True
    assert confirmed["reasoning"]["separated"] is True
    assert blocked["status"] == "blocked-credential"
    assert blocked["root_cause"] == "minimax-credential-missing"
    assert failed["status"] == "failed-runtime"
    assert failed["root_cause"] == "provider-schema-mismatch"

    for artifact in (confirmed, blocked, failed):
        assert artifact["safety"]["raw_provider_body_persisted"] is False
        assert artifact["safety"]["credential_persisted"] is False
        assert artifact["safety"]["auth_header_persisted"] is False
        assert artifact["safety"]["request_text_persisted"] is False
        assert artifact["safety"]["raw_reasoning_text_persisted"] is False
        assert artifact["safety"]["raw_legal_text_persisted"] is False
        assert artifact["safety"]["raw_falkordb_rows_persisted"] is False
        proof.assert_safe_artifact(artifact)
        assert_no_forbidden_terms(artifact)


def test_write_artifacts_persists_safe_json_and_markdown(proof: ModuleType, tmp_path: Path) -> None:
    classification = proof.classify_provider_response(provider_payload("MATCH (article:Article) RETURN article.id LIMIT 5"))
    artifact = proof.build_confirmed_runtime_artifact(classification=classification, provider_attempts=1, commands=[])

    json_path, markdown_path = proof.write_artifacts(tmp_path, artifact)

    written = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert written["status"] == "confirmed-runtime"
    assert written["candidate"]["normalized_text"] == "MATCH (article:Article) RETURN article.id LIMIT 5"
    assert "confirmed-runtime" in markdown
    assert "raw provider bodies are not persisted" in markdown
    assert_no_forbidden_terms(written)
    for term in FORBIDDEN_ARTIFACT_TERMS:
        assert term not in markdown
