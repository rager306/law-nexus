from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd" / "parser" / "golden_test_contract.md"

REQUIRED_SECTIONS = [
    "# Parser/Retrieval Golden-Test Contract",
    "## Source artifacts",
    "## Case classes",
    "## Required input record fields",
    "## Golden case fixture schema draft",
    "## Expected evaluator result shape",
    "## Diagnostic shape",
    "## Source-anchor rules",
    "## Allowed non-claims",
    "## Explicit out-of-scope claims",
    "## R032 acceptance mapping",
    "## Verification hook",
]

REQUIRED_SOURCE_ARTIFACTS = [
    "prd/parser/parser_record_contract.md",
    "prd/parser/schemas/document_record.schema.json",
    "prd/parser/schemas/source_block_record.schema.json",
    "prd/parser/schemas/relation_candidate_record.schema.json",
    "prd/parser/odt_document_records.jsonl",
    "prd/parser/odt_source_block_records.jsonl",
    "prd/parser/odt_smoke_records.json",
    "prd/parser/consultant_relation_candidates.jsonl",
    "prd/parser/consultant_relation_candidates.json",
    "prd/parser/parser_staging_graph.json",
    "prd/parser/parser_staging_graph.md",
]

REQUIRED_CASE_CLASSES = [
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
]

REQUIRED_ANSWER_STATES = [
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative-boundary",
]

REQUIRED_RECORD_FIELDS = {
    "Document record fields": [
        "id",
        "source_kind",
        "source_path",
        "source_sha256",
        "non_claims",
        "record_kind",
        "title",
        "non_authoritative",
    ],
    "Source block record fields": [
        "id",
        "source_kind",
        "source_path",
        "source_sha256",
        "non_claims",
        "record_kind",
        "document_id",
        "order_index",
        "location",
        "excerpt",
        "excerpt_sha256",
    ],
    "Relation candidate record fields": [
        "id",
        "source_kind",
        "source_path",
        "source_sha256",
        "non_claims",
        "record_kind",
        "source_block_id",
        "subject_ref",
        "object_ref",
        "relation_type",
        "status",
        "evidence_excerpt",
        "evidence_sha256",
    ],
}

REQUIRED_DIAGNOSTIC_FIELDS = [
    "case_id",
    "case_class",
    "severity",
    "rule",
    "artifact_path",
    "record_id",
    "record_kind",
    "source_path",
    "expected_state",
    "actual_state",
    "message",
    "non_authoritative",
]

BLOCKED_CLAIMS = [
    "parser completeness",
    "retrieval quality",
    "legal-answer correctness",
]

OUT_OF_SCOPE_CLAIMS = [
    "citation-safe retrieval readiness",
    "authoritative legal interpretation",
    "product ETL/import readiness",
    "production graph schema validity",
    "FalkorDB loading/runtime readiness",
    "FalkorDB production scale",
    "relation correctness or resolved Consultant-to-ODT endpoint matching",
    "LLM answer authority",
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


def test_contract_source_artifacts_are_tracked_parser_paths_only() -> None:
    text = contract_text()
    source_artifacts = section(text, "## Source artifacts")

    for artifact in REQUIRED_SOURCE_ARTIFACTS:
        assert f"`{artifact}`" in source_artifacts
    assert "not rescan undocumented local source directories" in source_artifacts
    assert "uv run python scripts/validate-parser-records.py --check" in source_artifacts
    assert "uv run python scripts/build-parser-staging-graph.py --check" in source_artifacts


def test_contract_case_classes_and_answer_states_are_closed_sets() -> None:
    text = contract_text()
    case_classes = section(text, "## Case classes")
    fixture_schema = section(text, "## Golden case fixture schema draft")

    for case_class in REQUIRED_CASE_CLASSES:
        assert f"`{case_class}`" in case_classes
        assert case_class in fixture_schema
    for answer_state in REQUIRED_ANSWER_STATES:
        assert f"{answer_state}" in fixture_schema
    assert "Allowed `case_class` values are exactly" in fixture_schema
    assert "Allowed `answer_state` values are exactly" in fixture_schema


def test_contract_required_record_and_diagnostic_fields_remain_inspectable() -> None:
    text = contract_text()
    record_fields = section(text, "## Required input record fields")
    diagnostic_shape = section(text, "## Diagnostic shape")

    for record_heading, required_fields in REQUIRED_RECORD_FIELDS.items():
        assert f"### {record_heading}" in record_fields
        for field in required_fields:
            assert f"`{field}`" in record_fields
    for field in REQUIRED_DIAGNOSTIC_FIELDS:
        assert f"`{field}`" in diagnostic_shape
    assert "must not include secrets" in diagnostic_shape
    assert "unbounded raw legal text" in diagnostic_shape


def test_contract_preserves_non_claim_boundaries_and_source_anchors() -> None:
    text = contract_text()
    source_anchor_rules = section(text, "## Source-anchor rules")
    allowed_non_claims = section(text, "## Allowed non-claims")
    out_of_scope = section(text, "## Explicit out-of-scope claims")

    for blocked_claim in BLOCKED_CLAIMS:
        assert blocked_claim in allowed_non_claims
        assert blocked_claim in out_of_scope
    for out_of_scope_claim in OUT_OF_SCOPE_CLAIMS:
        assert out_of_scope_claim in out_of_scope
    assert "repository-relative artifact paths" in source_anchor_rules
    assert "source_sha256" in text
    assert "excerpt_sha256" in text
    assert "REL-CONS-0001" in source_anchor_rules
    assert "must not repair missing or unresolved endpoints" in source_anchor_rules


def test_contract_maps_r032_acceptance_to_bounded_evidence_cases() -> None:
    text = contract_text()
    acceptance_mapping = section(text, "## R032 acceptance mapping")

    for criterion in [
        "Bounded expected evidence",
        "No-answer cases",
        "Candidate-only relation cases",
        "No product legal-answer claims",
        "Tracked M006 artifacts",
    ]:
        assert criterion in acceptance_mapping
    for case_class in REQUIRED_CASE_CLASSES:
        assert case_class in acceptance_mapping or case_class == "non-authoritative"
    assert "tracked `prd/parser/` files" in acceptance_mapping
