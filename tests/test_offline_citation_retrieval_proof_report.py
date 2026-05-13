from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "prd" / "retrieval" / "offline_citation_retrieval_proof.md"

REQUIRED_SECTIONS = [
    "# Offline Citation Retrieval Proof",
    "## Proof inputs",
    "## Executable command",
    "## Proof result",
    "## Case coverage",
    "## Diagnostic inventory",
    "## Validator integration",
    "## GATE-G008 status",
    "## Non-claims",
    "## S03 handoff",
]

REQUIRED_INPUTS = [
    "prd/retrieval/offline_citation_retrieval_contract.md",
    "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
    "scripts/build-offline-citation-retrieval-cases.py",
    "scripts/verify-offline-citation-retrieval-proof.py",
    "scripts/retrieval_output_validator.py",
    "prd/parser/consultant_hierarchy_records.json",
    "prd/parser/consultant_hierarchy_records.jsonl",
    "prd/parser/parser_staging_graph.json",
    "prd/retrieval/fixtures/real_artifact_retrieval_cases.json",
]

REQUIRED_CASE_CLASSES = [
    "valid_exact_record_candidate",
    "valid_marker_level_candidate",
    "scoped_no_candidate",
    "ambiguous_candidate_set",
    "unresolved_candidate_evidence",
    "unsafe_candidate_payload",
]

REQUIRED_DIAGNOSTICS = [
    "ambiguous_candidate_set",
    "id_path_mismatch",
    "orphaned_source_path",
    "scoped_no_answer",
    "scoped_no_candidate",
    "unresolved_candidate_evidence",
    "unsafe_payload_rejected",
]

REQUIRED_M014_PREFIXES = [
    "RET-M014-*",
    "SCOPE-M014-*",
    "CIT-M014-*",
    "EV-M014-*",
    "SB-M014-*",
    "SD-M014-*",
    "LU-M014-*",
    "ED-M014-*",
    "AC-M014-*",
]

REQUIRED_NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not prove local embedding quality",
    "does not close GATE-G008",
    "does not close GATE-G011",
    "does not make LLM output legal authority",
    "does not make proof-local IDs production IDs",
]

FORBIDDEN_SNIPPETS = [
    "/root/",
    ".gsd/exec",
    "BEGIN PRIVATE KEY",
    "provider response body",
    "legal advice:",
]


def report_text() -> str:
    return REPORT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def test_report_required_sections_are_present_in_order() -> None:
    text = report_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_report_inputs_are_tracked_repository_relative_paths() -> None:
    text = report_text()
    inputs = section(text, "## Proof inputs")

    for path in REQUIRED_INPUTS:
        assert f"`{path}`" in inputs
        assert (ROOT / path).exists(), path
    assert "tracked repository-relative inputs" in inputs
    assert "does not fetch external data" in inputs
    assert "run FalkorDB" in inputs


def test_report_records_command_and_exact_summary_counts() -> None:
    text = report_text()
    command = section(text, "## Executable command")
    result = section(text, "## Proof result")

    assert "uv run python scripts/verify-offline-citation-retrieval-proof.py" in command
    assert "uv run pytest tests/test_offline_citation_retrieval_proof_cli.py tests/test_offline_citation_retrieval_proof_report.py -q" in command
    for snippet in [
        '"total_cases":6',
        '"selected_count":2',
        '"scoped_no_answer_count":1',
        '"rejected_count":3',
        '"validator_accepted_count":3',
        '"validator_rejected_count":1',
        '"mismatch_count":0',
        '"non_authoritative":true',
    ]:
        assert snippet in result
    for row in [
        "| `total_cases` | 6 |",
        "| `selected_count` | 2 |",
        "| `mismatch_count` | 0 |",
    ]:
        assert row in result


def test_report_case_coverage_and_diagnostics_match_fixture_contract() -> None:
    text = report_text()
    coverage = section(text, "## Case coverage")
    diagnostics = section(text, "## Diagnostic inventory")

    for case_class in REQUIRED_CASE_CLASSES:
        assert f"`{case_class}`" in coverage
    assert "rejects without arbitrary tie-breaking" in coverage
    for diagnostic in REQUIRED_DIAGNOSTICS:
        assert f"`{diagnostic}`" in diagnostics
    assert "They do not persist raw legal text" in diagnostics


def test_report_validator_integration_preserves_fail_closed_namespace_boundary() -> None:
    text = report_text()
    validator = section(text, "## Validator integration")

    for prefix in REQUIRED_M014_PREFIXES:
        assert f"`{prefix}`" in validator
    assert "Regression tests preserve fail-closed behavior for unknown namespaces" in validator
    assert "does not introduce a parallel citation validator" in validator


def test_report_advances_but_does_not_close_gate_g008() -> None:
    text = report_text()
    gate = section(text, "## GATE-G008 status")
    handoff = section(text, "## S03 handoff")

    assert "This proof advances `GATE-G008`" in gate
    assert "`GATE-G008` remains open" in gate
    assert "not closing it" in handoff
    assert "bounded-evidence" in handoff


def test_report_non_claims_and_redaction_boundaries_are_explicit() -> None:
    text = report_text()
    non_claims = section(text, "## Non-claims").lower()

    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim.lower() in non_claims
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in text
    assert "Настоящий Федеральный закон регулирует отношения" not in text
