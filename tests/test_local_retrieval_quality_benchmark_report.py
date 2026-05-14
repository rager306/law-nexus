from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "prd" / "retrieval" / "local_retrieval_quality_benchmark_proof.md"

REQUIRED_SECTIONS = [
    "# Local Retrieval Quality Benchmark Proof",
    "## Proof inputs",
    "## Executable command",
    "## Proof result",
    "## Case coverage",
    "## Metric inventory",
    "## Model boundary",
    "## Diagnostic inventory",
    "## GATE-G011 status",
    "## Non-claims",
    "## S03 handoff",
]

REQUIRED_INPUTS = [
    "prd/retrieval/local_retrieval_quality_benchmark_contract.md",
    "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json",
    "scripts/build-local-retrieval-quality-benchmark.py",
    "scripts/verify-local-retrieval-quality-benchmark.py",
    "tests/test_local_retrieval_quality_benchmark_contract.py",
    "tests/test_local_retrieval_quality_benchmark_fixture.py",
    "tests/test_local_retrieval_quality_benchmark_cli.py",
    "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
    ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
]

REQUIRED_CASE_CLASSES = [
    "positive_exact_relevance",
    "positive_with_distractor",
    "scoped_no_answer_quality",
    "ambiguous_retrieval_rejected",
    "unsafe_payload_rejected",
    "environment_boundary",
]

REQUIRED_METRICS = [
    "mrr",
    "recall_at_1",
    "recall_at_3",
    "no_answer_accuracy",
    "ambiguous_rejection_rate",
    "unsafe_rejection_rate",
]

REQUIRED_DIAGNOSTICS = [
    "ambiguous_rejected",
    "model_runtime_available",
    "scoped_no_answer",
    "unsafe_payload_rejected",
]

REQUIRED_NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not allow managed embedding API fallback",
    "does not promote GigaEmbeddings",
    "does not close GATE-G011",
    "does not close GATE-G008",
    "does not make LLM output legal authority",
    "does not make proof-local fixture metrics production metrics",
]

FORBIDDEN_SNIPPETS = [
    "/root/",
    ".gsd/exec",
    "BEGIN PRIVATE KEY",
    "provider response body",
    "legal advice:",
    "Настоящий Федеральный закон регулирует отношения",
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
    assert "managed embedding API" in inputs
    assert "raw embedding vectors" in inputs


def test_report_records_command_and_exact_summary_counts() -> None:
    text = report_text()
    command = section(text, "## Executable command")
    result = section(text, "## Proof result")

    assert "uv run python scripts/verify-local-retrieval-quality-benchmark.py" in command
    assert "uv run pytest tests/test_local_retrieval_quality_benchmark_cli.py tests/test_local_retrieval_quality_benchmark_report.py -q" in command
    for snippet in [
        '"total_cases":6',
        '"positive_query_count":2',
        '"threshold_passed":true',
        '"mismatch_count":0',
        '"model_id":"deepvk/USER-bge-m3"',
        '"observed_vector_dimension":1024',
        '"managed_api_used":false',
        '"raw_vectors_persisted":false',
    ]:
        assert snippet in result
    for row in [
        "| `total_cases` | 6 |",
        "| `positive_query_count` | 2 |",
        "| `threshold_passed` | true |",
        "| `mismatch_count` | 0 |",
    ]:
        assert row in result


def test_report_case_metric_and_diagnostic_coverage_are_explicit() -> None:
    text = report_text()
    coverage = section(text, "## Case coverage")
    metrics = section(text, "## Metric inventory")
    diagnostics = section(text, "## Diagnostic inventory")

    for case_class in REQUIRED_CASE_CLASSES:
        assert f"`{case_class}`" in coverage
    for metric in REQUIRED_METRICS:
        assert f"`{metric}`" in metrics
    assert "not production Russian legal retrieval quality" in metrics
    for diagnostic in REQUIRED_DIAGNOSTICS:
        assert f"`{diagnostic}`" in diagnostics
    assert "They do not persist raw legal text" in diagnostics


def test_report_model_boundary_uses_user_bge_and_blocks_overclaims() -> None:
    text = report_text()
    model = section(text, "## Model boundary")

    assert "deepvk/USER-bge-m3" in model
    assert "1024" in model
    assert "managed_api_used`: `false`" in model
    assert "raw_vectors_persisted`: `false`" in model
    assert ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json" in model
    assert "does not prove production retrieval quality" in model
    assert "GigaEmbeddings remains blocked/gated" in model


def test_report_advances_but_does_not_close_gate_g011() -> None:
    text = report_text()
    gate = section(text, "## GATE-G011 status")
    handoff = section(text, "## S03 handoff")

    assert "This proof advances `GATE-G011`" in gate
    assert "`GATE-G011` remains open" in gate
    assert "not satisfying or closing it" in handoff
    assert "bounded-evidence" in handoff


def test_report_non_claims_and_redaction_boundaries_are_explicit() -> None:
    text = report_text()
    non_claims = section(text, "## Non-claims").lower()

    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim.lower() in non_claims
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in text
