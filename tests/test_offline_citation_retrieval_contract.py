from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd" / "retrieval" / "offline_citation_retrieval_contract.md"

REQUIRED_SECTIONS = [
    "# Offline Citation Retrieval Contract",
    "## Source artifacts",
    "## Query record shape",
    "## Candidate record shape",
    "## Selection reason codes",
    "## Case classes",
    "## Validator envelope handoff",
    "## No-answer behavior",
    "## Diagnostic shape",
    "## Redaction and forbidden payloads",
    "## Non-claims",
    "## S02 handoff",
    "## Verification hook",
]

REQUIRED_SOURCE_ARTIFACTS = [
    "prd/retrieval/real_artifact_evidence_mapping.md",
    "prd/retrieval/fixtures/real_artifact_retrieval_cases.json",
    "prd/retrieval/real_artifact_retrieval_proof.md",
    "scripts/retrieval_output_validator.py",
    "scripts/verify-real-artifact-retrieval-proof.py",
    "prd/parser/consultant_hierarchy_records.json",
    "prd/parser/consultant_hierarchy_records.jsonl",
    "prd/parser/parser_staging_graph.json",
]

REQUIRED_QUERY_FIELDS = [
    "query_id",
    "query_kind",
    "scope_id",
    "target_level",
    "target_record_id",
    "expected_result",
]

REQUIRED_CANDIDATE_FIELDS = [
    "candidate_id",
    "query_id",
    "source_record_id",
    "source_path",
    "source_sha256",
    "excerpt_sha256",
    "selection_reason",
    "validator_output",
]

REQUIRED_SELECTION_REASONS = [
    "exact_record_id_match",
    "marker_level_match",
    "scoped_no_candidate",
    "ambiguous_candidate_set",
    "unresolved_candidate_evidence",
    "unsafe_payload_rejected",
]

REQUIRED_CASE_CLASSES = [
    "valid_exact_record_candidate",
    "valid_marker_level_candidate",
    "scoped_no_candidate",
    "ambiguous_candidate_set",
    "unresolved_candidate_evidence",
    "unsafe_candidate_payload",
]

REQUIRED_NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not prove local embedding quality",
    "does not close GATE-G008 unless final milestone validation explicitly confirms full gate criteria",
    "does not close GATE-G011",
    "does not make LLM output legal authority",
    "does not make proof-local IDs production IDs",
]

FORBIDDEN_SNIPPETS = [
    ".gsd/exec",
    "/root/",
    "BEGIN PRIVATE KEY",
    "provider response body",
    "legal advice:",
]


def contract_text() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def test_contract_required_sections_remain_present_in_order() -> None:
    text = contract_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_contract_source_artifacts_are_tracked_repository_paths() -> None:
    text = contract_text()
    source_artifacts = section(text, "## Source artifacts")

    for artifact in REQUIRED_SOURCE_ARTIFACTS:
        assert f"`{artifact}`" in source_artifacts
        assert (ROOT / artifact).exists(), f"missing source artifact: {artifact}"
    assert "tracked repository-relative artifacts" in source_artifacts
    assert "must not rescan untracked local directories" in source_artifacts
    assert ".gsd/exec" in source_artifacts


def test_contract_query_and_candidate_shapes_are_explicit() -> None:
    text = contract_text()
    query_shape = section(text, "## Query record shape")
    candidate_shape = section(text, "## Candidate record shape")

    for field in REQUIRED_QUERY_FIELDS:
        assert f"`{field}`" in query_shape
    for field in REQUIRED_CANDIDATE_FIELDS:
        assert f"`{field}`" in candidate_shape
    assert "not user prompt text" in query_shape
    assert "must not contain raw legal text" in query_shape
    assert "raw excerpt text must not be persisted" in candidate_shape
    assert "not product search results" in candidate_shape


def test_contract_selection_reasons_and_case_classes_are_closed_sets() -> None:
    text = contract_text()
    selection_reasons = section(text, "## Selection reason codes")
    case_classes = section(text, "## Case classes")

    for reason in REQUIRED_SELECTION_REASONS:
        assert f"`{reason}`" in selection_reasons
    for case_class in REQUIRED_CASE_CLASSES:
        assert f"`{case_class}`" in case_classes
    assert "No ranking score, embedding distance, LLM confidence, FalkorDB score, or legal relevance score" in selection_reasons
    assert "Additional case classes may be added only if they are deterministic" in case_classes


def test_contract_validator_handoff_and_no_answer_boundaries_are_safe() -> None:
    text = contract_text()
    handoff = section(text, "## Validator envelope handoff")
    no_answer = section(text, "## No-answer behavior")

    for field in [
        "retrieval_output_id",
        "scope_id",
        "query_id",
        "retrieval_run_id",
        "as_of_date",
        "source_corpus_id",
        "validator_contract_version",
        "citation_key",
        "evidence_span_id",
        "source_block_id",
        "source_document_id",
        "legal_unit_id",
        "act_edition_id",
    ]:
        assert f"`{field}`" in handoff
    assert "reuse `scripts/retrieval_output_validator.py`" in handoff
    assert "unknown_id_namespace" in handoff
    assert "not a global legal absence claim" in no_answer
    assert "must not hide parser gaps" in no_answer


def test_contract_diagnostics_redaction_and_non_claims_are_explicit() -> None:
    text = contract_text()
    diagnostics = section(text, "## Diagnostic shape")
    redaction = section(text, "## Redaction and forbidden payloads")
    non_claims = section(text, "## Non-claims")

    for field in ["code", "severity", "case_id", "query_id", "candidate_id", "source_record_id", "field_path", "proof_artifact"]:
        assert f"`{field}`" in diagnostics
    for blocked in [
        "raw legal text",
        "user prompts",
        "credentials",
        "raw embedding arrays",
        "raw FalkorDB rows",
        "generated legal advice",
        "product-facing relevance/ranking claims",
    ]:
        assert blocked in redaction
    lowered_non_claims = non_claims.lower()
    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim.lower() in lowered_non_claims


def test_contract_avoids_unsafe_or_absolute_anchors_outside_redaction_examples() -> None:
    text = contract_text()

    for forbidden in FORBIDDEN_SNIPPETS:
        if forbidden == ".gsd/exec":
            assert "must not" in text[text.index(forbidden) - 120 : text.index(forbidden) + 120]
            continue
        assert forbidden not in text


def test_verification_hook_points_to_this_test() -> None:
    text = contract_text()
    verification = section(text, "## Verification hook")

    assert "uv run pytest tests/test_offline_citation_retrieval_contract.py -q" in verification
