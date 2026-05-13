from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "prd" / "retrieval" / "real_artifact_evidence_mapping.md"

REQUIRED_SECTIONS = [
    "# Real Artifact Retrieval Evidence Mapping",
    "## Source artifacts",
    "## Record mapping table",
    "## ID namespace strategy",
    "## Bounded and proxy fields",
    "## Invalid case classes",
    "## Diagnostic and redaction rules",
    "## Non-claims",
    "## S02 handoff",
    "## Verification hook",
]

REQUIRED_SOURCE_ARTIFACTS = [
    "prd/parser/consultant_hierarchy_records.json",
    "prd/parser/consultant_hierarchy_records.jsonl",
    "prd/parser/consultant_hierarchy_records.md",
    "prd/parser/parser_staging_graph.json",
    "prd/parser/parser_staging_graph.md",
    "prd/retrieval/retrieval_output_validator_contract.md",
    "prd/retrieval/fixtures/retrieval_output_validator_cases.json",
]

REQUIRED_VALIDATOR_CONCEPTS = [
    "SourceDocument",
    "SourceBlock",
    "EvidenceSpan",
    "LegalUnit",
    "ActEdition",
    "LegalAct",
    "citation_key",
    "retrieval_output_id",
]

REQUIRED_INVALID_CASE_CLASSES = [
    "valid_real_artifact_path",
    "missing_evidence_id",
    "unresolved_source_block",
    "ambiguous_citation_key",
    "wrong_edition_proxy",
    "scoped_no_answer",
    "unsafe_no_answer_with_citation",
]

REQUIRED_NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not prove local embedding quality",
    "does not close GATE-G008",
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

REQUIRED_PREFIX_SNIPPETS = [
    "RET-M012-*",
    "CIT-M012-*",
    "EV-M012-*",
    "SB-M012-*",
    "SD-M012-*",
    "LU-M012-*",
    "ED-M012-*",
    "AC-M012-*",
    "RET-M013-*",
    "CIT-M013-*",
    "EV-M013-*",
    "SB-M013-*",
    "SD-M013-*",
    "LU-M013-*",
    "ED-M013-*",
    "AC-M013-*",
]


def mapping_text() -> str:
    return MAPPING_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def test_mapping_required_sections_remain_present_in_order() -> None:
    text = mapping_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_mapping_source_artifacts_are_tracked_repository_paths() -> None:
    text = mapping_text()
    source_artifacts = section(text, "## Source artifacts")

    for artifact in REQUIRED_SOURCE_ARTIFACTS:
        assert f"`{artifact}`" in source_artifacts
        assert (ROOT / artifact).exists(), f"missing source artifact: {artifact}"
    assert "tracked repository-relative artifacts" in source_artifacts
    assert "must not rescan untracked local source directories" in source_artifacts
    assert ".gsd/exec" in source_artifacts


def test_mapping_covers_required_validator_concepts_and_boundaries() -> None:
    text = mapping_text()
    mapping_table = section(text, "## Record mapping table")
    bounded_fields = section(text, "## Bounded and proxy fields")

    for concept in REQUIRED_VALIDATOR_CONCEPTS:
        assert f"`{concept}`" in mapping_table or concept in mapping_table
    for required_phrase in [
        "not final document model",
        "not parser completeness",
        "not legal correctness",
        "not final legal graph schema",
        "does not resolve all amendments",
        "not a final citation format",
        "not a product retrieval ID",
    ]:
        assert required_phrase in mapping_table
    for field in [
        "source_document_id",
        "source_block_id",
        "evidence_span_id",
        "legal_unit_id",
        "act_edition_id",
        "citation_key",
        "retrieval_output_id",
    ]:
        assert f"`{field}`" in bounded_fields


def test_mapping_names_m012_namespace_constraint_and_m013_options() -> None:
    text = mapping_text()
    namespace_strategy = section(text, "## ID namespace strategy")

    assert "current `scripts/retrieval_output_validator.py` enforces those prefixes" in namespace_strategy
    assert "must not silently bypass this constraint" in namespace_strategy
    assert "Safe namespace extension" in namespace_strategy
    assert "Adapter normalization" in namespace_strategy
    assert "unknown-namespace rejection" in namespace_strategy
    for prefix in REQUIRED_PREFIX_SNIPPETS:
        assert f"`{prefix}`" in namespace_strategy


def test_mapping_invalid_case_classes_are_closed_and_safe() -> None:
    text = mapping_text()
    invalid_cases = section(text, "## Invalid case classes")

    for case_class in REQUIRED_INVALID_CASE_CLASSES:
        assert f"`{case_class}`" in invalid_cases
    assert "Additional invalid cases may be added only if they remain deterministic and safe." in invalid_cases


def test_mapping_diagnostic_redaction_and_non_claims_are_explicit() -> None:
    text = mapping_text()
    diagnostics = section(text, "## Diagnostic and redaction rules")
    non_claims = section(text, "## Non-claims")

    for blocked in [
        "raw legal text",
        "user prompts",
        "credentials",
        "raw embedding arrays",
        "raw FalkorDB rows",
        "generated legal advice",
    ]:
        assert blocked in diagnostics
    lowered_non_claims = non_claims.lower()
    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim.lower() in lowered_non_claims


def test_mapping_avoids_unsafe_or_absolute_anchors_outside_redaction_examples() -> None:
    text = mapping_text()

    for forbidden in FORBIDDEN_SNIPPETS:
        if forbidden == ".gsd/exec":
            # Mentioned only as an excluded anchor class.
            assert "must not" in text[text.index(forbidden) - 120 : text.index(forbidden) + 120]
            continue
        assert forbidden not in text


def test_verification_hook_points_to_this_test() -> None:
    text = mapping_text()
    verification = section(text, "## Verification hook")

    assert "uv run pytest tests/test_real_artifact_evidence_mapping.py -q" in verification
