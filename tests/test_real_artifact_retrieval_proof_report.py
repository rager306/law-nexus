from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "prd" / "retrieval" / "real_artifact_retrieval_proof.md"

REQUIRED_SECTIONS = [
    "# Real Artifact Retrieval Proof",
    "## Proof command",
    "## Inputs and anchors",
    "## Case coverage",
    "## Namespace strategy",
    "## Diagnostic and redaction boundaries",
    "## R034 status",
    "## Remaining gates",
    "## Non-claims",
]

REQUIRED_ARTIFACTS = [
    "prd/retrieval/real_artifact_evidence_mapping.md",
    "prd/retrieval/fixtures/real_artifact_retrieval_cases.json",
    "scripts/build-real-artifact-retrieval-cases.py",
    "scripts/verify-real-artifact-retrieval-proof.py",
    "scripts/retrieval_output_validator.py",
    "tests/test_real_artifact_retrieval_proof_cli.py",
    "tests/test_real_artifact_retrieval_cases.py",
    "tests/test_retrieval_output_validator.py",
]

REQUIRED_CASE_IDS = [
    "CASE-M013-VALID-REAL-ARTIFACT",
    "CASE-M013-MISSING-EVIDENCE-ID",
    "CASE-M013-UNRESOLVED-SOURCE-BLOCK",
    "CASE-M013-AMBIGUOUS-CITATION",
    "CASE-M013-WRONG-EDITION-PROXY",
    "CASE-M013-SCOPED-NO-ANSWER",
    "CASE-M013-UNSAFE-NO-ANSWER-WITH-CITATION",
]

REQUIRED_DIAGNOSTIC_CODES = [
    "ambiguous_citation_key",
    "id_path_mismatch",
    "missing_required_field",
    "orphaned_source_path",
    "scoped_no_answer",
    "unsafe_no_answer_shape",
    "wrong_edition",
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
    "BEGIN PRIVATE KEY",
    "provider response body",
    "embedding_vector",
    "falkordb_row",
    "legal advice:",
]


def report_text() -> str:
    return REPORT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def test_report_required_sections_remain_present_in_order() -> None:
    text = report_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_report_names_proof_commands_and_expected_counts() -> None:
    text = report_text()
    proof_command = section(text, "## Proof command")

    assert "uv run python scripts/verify-real-artifact-retrieval-proof.py" in proof_command
    assert "uv run python scripts/verify-retrieval-output-validator.py" in proof_command
    assert '"total_cases": 7' in proof_command
    assert '"accepted_count": 2' in proof_command
    assert '"rejected_count": 5' in proof_command
    assert '"mismatch_count": 0' in proof_command
    assert '"namespace_strategy": "safe_namespace_extension_selected"' in proof_command


def test_report_artifact_anchors_are_tracked_paths() -> None:
    text = report_text()
    anchors = section(text, "## Inputs and anchors")

    for artifact in REQUIRED_ARTIFACTS:
        assert f"`{artifact}`" in anchors
        assert (ROOT / artifact).exists(), f"missing artifact: {artifact}"
    assert "/root/" not in anchors
    assert ".gsd/exec" not in anchors


def test_report_case_coverage_and_diagnostics_are_complete() -> None:
    text = report_text()
    case_coverage = section(text, "## Case coverage")
    proof_command = section(text, "## Proof command")

    for case_id in REQUIRED_CASE_IDS:
        assert f"`{case_id}`" in case_coverage
    for code in REQUIRED_DIAGNOSTIC_CODES:
        assert f"`{code}`" in case_coverage or f'"{code}"' in proof_command
    assert case_coverage.count("| `CASE-M013-") == 7


def test_report_preserves_namespace_and_gate_boundaries() -> None:
    text = report_text()
    namespace = section(text, "## Namespace strategy")
    gates = section(text, "## Remaining gates")
    r034 = section(text, "## R034 status")

    assert "safe namespace extension" in namespace
    assert "M012 and M013 proof-local ID prefixes" in namespace
    assert "unknown_id_namespace" in namespace
    assert "does not define final production ID formats" in namespace
    assert "R034 should not be marked fully validated until M013/S03" in r034
    assert "`GATE-G008` remains open" in gates
    assert "`GATE-G011` remains open" in gates
    assert "FalkorDB runtime/load proof remains out of scope" in gates
    assert "Legal-answer correctness and LLM authority remain out of scope" in gates


def test_report_non_claims_and_redaction_boundaries_are_explicit() -> None:
    text = report_text()
    diagnostics = section(text, "## Diagnostic and redaction boundaries")
    non_claims = section(text, "## Non-claims")
    lowered_non_claims = non_claims.lower()

    for phrase in [
        "raw legal text",
        "prompts",
        "provider payloads",
        "secrets",
        "raw embedding arrays",
        "raw FalkorDB rows",
        "generated answer prose",
        "legal advice markers",
    ]:
        assert phrase in diagnostics
    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim.lower() in lowered_non_claims
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in text
