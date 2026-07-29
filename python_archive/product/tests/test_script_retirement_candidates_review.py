from __future__ import annotations

from pathlib import Path

REVIEW = Path("prd/architecture/script-retirement-candidates-review.md")


def read_review() -> str:
    return REVIEW.read_text(encoding="utf-8")


def test_script_retirement_review_has_required_sections() -> None:
    text = read_review()

    for section in [
        "## Purpose",
        "## Scope",
        "## Classification labels",
        "## Candidate matrix",
        "## No-premature-deletion guardrails",
        "## Compatibility gates to keep",
        "## GitNexus traceability notes",
        "## S22 handoff",
        "## Non-claims",
    ]:
        assert section in text


def test_script_retirement_review_keeps_all_classification_labels() -> None:
    text = read_review()

    for label in ["keep-wrapper", "retire-later", "do-not-retire", "review-later"]:
        assert label in text

    for script in [
        "scripts/inventory-parser-fixtures.py",
        "scripts/build_representative_retrieval_corpus_manifest.py",
        "scripts/retrieval_output_validator.py",
        "scripts/verify-falkordb-csv-ingest-proof.py",
        "scripts/verify-semantic-descriptor-scoring.py",
        "scripts/acp_git_lex_backend.py",
    ]:
        assert script in text


def test_script_retirement_review_blocks_premature_deletion() -> None:
    text = read_review()

    assert "It does not delete, rename, or retire any script." in text
    assert "No script may be deleted, renamed, or hidden from CLI users" in text
    assert "Do not rely on bare-name lookups for retirement decisions." in text
    assert "Safe script deletion." in text


def test_script_retirement_review_keeps_required_compatibility_gates() -> None:
    text = read_review()

    required_gates = [
        "uv run pytest tests/test_parser_source_cli_compatibility.py -q",
        "uv run pytest tests/test_representative_corpus_manifest_use_case.py -q",
        "uv run python scripts/build_representative_retrieval_corpus_manifest.py --check",
        "uv run pytest tests/test_falkordb_csv_loader_adapter.py tests/test_falkordb_csv_ingest_proof.py -q",
        "CSV_FILE_ACCESS_BLOCKED",
        "uv run pytest tests/test_citation_safe_answer_validator_use_case.py -q",
        "uv run pytest tests/test_semantic_descriptor_scoring.py -q",
    ]
    for gate in required_gates:
        assert gate in text


def test_script_retirement_review_records_gitnexus_traceability() -> None:
    text = read_review()

    for phrase in [
        "Function:scripts/acp_git_lex_backend.py:normalize_wrapper_record",
        "Function:scripts/build_representative_retrieval_corpus_manifest.py:main",
        "Function:scripts/verify-falkordb-csv-ingest-proof.py:main",
        "file-qualified GitNexus UIDs",
    ]:
        assert phrase in text
