from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd" / "retrieval" / "local_retrieval_quality_benchmark_contract.md"

REQUIRED_SECTIONS = [
    "# Local Retrieval Quality Benchmark Contract",
    "## Source artifacts",
    "## Benchmark query shape",
    "## Candidate shape",
    "## Relevance labels",
    "## Metric semantics",
    "## Threshold contract",
    "## Environment and model diagnostics",
    "## Benchmark case classes",
    "## Diagnostic shape",
    "## Redaction and forbidden payloads",
    "## GATE-G011 status",
    "## Non-claims",
    "## S02 handoff",
    "## Verification hook",
]

REQUIRED_SOURCE_ARTIFACTS = [
    "prd/retrieval/offline_citation_retrieval_proof.md",
    "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
    ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
    "prd/architecture/product_readiness_blockers.md",
]

REQUIRED_QUERY_FIELDS = [
    "benchmark_query_id",
    "query_kind",
    "query_text_sha256",
    "scope_id",
    "expected_relevant_candidate_ids",
    "expected_result",
]

REQUIRED_CANDIDATE_FIELDS = [
    "candidate_id",
    "source_case_id",
    "source_record_ids",
    "relevance_label",
    "score_input_id",
    "source_artifact",
]

REQUIRED_LABELS = ["relevant", "distractor", "ambiguous", "no_answer", "unsafe"]
REQUIRED_METRICS = [
    "mrr",
    "recall_at_1",
    "recall_at_3",
    "no_answer_accuracy",
    "ambiguous_rejection_rate",
    "unsafe_rejection_rate",
]
REQUIRED_CASE_CLASSES = [
    "positive_exact_relevance",
    "positive_with_distractor",
    "scoped_no_answer_quality",
    "ambiguous_retrieval_rejected",
    "unsafe_payload_rejected",
    "environment_boundary",
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
    "does not close GATE-G011 unless final milestone validation explicitly confirms full gate criteria",
    "does not close GATE-G008",
    "does not make LLM output legal authority",
]

FORBIDDEN_SNIPPETS = [
    "/root/",
    ".gsd/exec",
    "BEGIN PRIVATE KEY",
    "provider response body",
    "legal advice:",
    "Настоящий Федеральный закон регулирует отношения",
]


def contract_text() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def test_contract_required_sections_are_present_in_order() -> None:
    text = contract_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_contract_source_artifacts_are_tracked_repository_relative_paths() -> None:
    text = contract_text()
    source_artifacts = section(text, "## Source artifacts")

    for artifact in REQUIRED_SOURCE_ARTIFACTS:
        assert f"`{artifact}`" in source_artifacts
        assert (ROOT / artifact).exists(), artifact
    assert "tracked repository-relative inputs" in source_artifacts
    assert "must not fetch external data" in source_artifacts
    assert "call a managed embedding API" in source_artifacts
    assert "persist raw embedding vectors" in source_artifacts


def test_contract_query_candidate_shapes_are_explicit_and_redacted() -> None:
    text = contract_text()
    query_shape = section(text, "## Benchmark query shape")
    candidate_shape = section(text, "## Candidate shape")

    for field in REQUIRED_QUERY_FIELDS:
        assert f"`{field}`" in query_shape
    for field in REQUIRED_CANDIDATE_FIELDS:
        assert f"`{field}`" in candidate_shape
    assert "never raw user prompt text" in query_shape
    assert "raw query text must not be persisted" in query_shape
    assert "must not include raw legal text" in query_shape
    assert "must not persist raw source excerpts" in candidate_shape
    assert "raw embeddings" in candidate_shape


def test_contract_labels_metrics_and_thresholds_are_closed_and_strict() -> None:
    text = contract_text()
    labels = section(text, "## Relevance labels")
    metrics = section(text, "## Metric semantics")
    thresholds = section(text, "## Threshold contract")

    for label in REQUIRED_LABELS:
        assert f"`{label}`" in labels
    for metric in REQUIRED_METRICS:
        assert f"`{metric}`" in metrics
        assert f"`{metric}` | 1.0 |" in thresholds
    assert "fixture-level quality signals only" in metrics
    assert "never present these metrics as production Russian legal retrieval quality" in metrics
    assert "future broader benchmark may lower or stratify thresholds only with a new contract" in thresholds


def test_contract_environment_model_boundary_uses_s10_user_bge_only() -> None:
    text = contract_text()
    environment = section(text, "## Environment and model diagnostics")

    assert "deepvk/USER-bge-m3" in environment
    assert "observed dimension `1024`" in environment
    assert "GigaEmbeddings" not in environment
    for field in [
        "model_id",
        "model_status",
        "observed_vector_dimension",
        "managed_api_used",
        "raw_vectors_persisted",
        "runtime_evidence_source",
    ]:
        assert f"`{field}`" in environment
    assert "Must be `false`" in environment
    assert "blocked_environment" in environment
    assert "must not silently pass as runtime proof" in environment


def test_contract_case_classes_diagnostics_and_forbidden_payloads_are_safe() -> None:
    text = contract_text()
    case_classes = section(text, "## Benchmark case classes")
    diagnostics = section(text, "## Diagnostic shape")
    redaction = section(text, "## Redaction and forbidden payloads")

    for case_class in REQUIRED_CASE_CLASSES:
        assert f"`{case_class}`" in case_classes
    for field in ["code", "severity", "benchmark_case_id", "benchmark_query_id", "candidate_id", "metric", "field_path", "proof_artifact"]:
        assert f"`{field}`" in diagnostics
    for blocked in [
        "raw legal text",
        "raw query prompts",
        "credentials",
        "raw embedding arrays",
        "managed embedding API payloads",
        "raw FalkorDB runtime rows",
        "generated legal advice",
        "product-facing retrieval quality claims",
    ]:
        assert blocked in redaction


def test_contract_gate_status_and_non_claims_keep_g011_open() -> None:
    text = contract_text()
    gate = section(text, "## GATE-G011 status")
    non_claims = section(text, "## Non-claims").lower()

    assert "M015 can advance `GATE-G011` only as bounded seed-benchmark evidence" in gate
    assert "`GATE-G011` remains open" in gate
    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim.lower() in non_claims


def test_contract_s02_handoff_and_verification_hook_are_actionable() -> None:
    text = contract_text()
    handoff = section(text, "## S02 handoff")
    verification = section(text, "## Verification hook")

    for phrase in [
        "loads the benchmark fixture",
        "computes deterministic fixture-level metrics",
        "records `deepvk/USER-bge-m3` runtime availability",
        "exits non-zero on stale fixtures",
    ]:
        assert phrase in handoff
    assert "uv run pytest tests/test_local_retrieval_quality_benchmark_contract.py -q" in verification


def test_contract_avoids_unsafe_absolute_or_raw_payload_snippets() -> None:
    text = contract_text()

    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in text
