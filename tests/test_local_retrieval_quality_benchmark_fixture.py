from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd" / "retrieval" / "fixtures" / "local_retrieval_quality_benchmark.json"

REQUIRED_CASE_CLASSES = {
    "positive_exact_relevance",
    "positive_with_distractor",
    "scoped_no_answer_quality",
    "ambiguous_retrieval_rejected",
    "unsafe_payload_rejected",
    "environment_boundary",
}

REQUIRED_THRESHOLDS = {
    "mrr": 1.0,
    "recall_at_1": 1.0,
    "recall_at_3": 1.0,
    "no_answer_accuracy": 1.0,
    "ambiguous_rejection_rate": 1.0,
    "unsafe_rejection_rate": 1.0,
}

FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "source_excerpts",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_response_body",
    "secret",
    "secrets",
    "pii",
    "vector",
    "embedding_vector",
    "embedding",
    "falkordb_row",
    "runtime_row",
    "generated_answer_prose",
    "legal_advice",
    "llm_reasoning",
}

REQUIRED_NON_CLAIMS = [
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove production FalkorDB runtime behavior.",
    "Does not allow managed embedding API fallback.",
    "Does not promote GigaEmbeddings.",
    "Does not close GATE-G011 unless final milestone validation explicitly confirms full gate criteria.",
    "Does not close GATE-G008.",
    "Does not make LLM output legal authority.",
]


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def walk(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, Mapping):
        for item in value.values():
            values.extend(walk(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(walk(item))
    return values


def test_fixture_top_level_schema_sources_and_model_boundary() -> None:
    fixture = load_fixture()

    assert fixture["schema_version"] == "local-retrieval-quality-benchmark/v1"
    assert fixture["fixture_artifact"] == "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json"
    assert fixture["generated_by"] == "scripts/build-local-retrieval-quality-benchmark.py"
    assert fixture["contract"] == "prd/retrieval/local_retrieval_quality_benchmark_contract.md"
    assert fixture["gate"] == "GATE-G011"
    assert fixture["non_authoritative"] is True

    source_paths = {artifact["path"] for artifact in fixture["source_artifacts"]}
    for path in [
        "prd/retrieval/local_retrieval_quality_benchmark_contract.md",
        "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
        ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json",
    ]:
        assert path in source_paths
        assert (ROOT / path).exists()
    for artifact in fixture["source_artifacts"]:
        assert len(artifact["sha256"]) == 64
        int(artifact["sha256"], 16)

    model = fixture["model_boundary"]
    assert model["model_id"] == "deepvk/USER-bge-m3"
    assert model["observed_vector_dimension"] == 1024
    assert model["managed_api_used"] is False
    assert model["raw_vectors_persisted"] is False
    assert model["runtime_evidence_source"] == ".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json"
    assert "not production Russian legal retrieval quality" in model["quality_boundary"]


def test_fixture_contains_required_cases_thresholds_and_labels() -> None:
    fixture = load_fixture()

    assert fixture["thresholds"] == REQUIRED_THRESHOLDS
    assert set(fixture["allowed_relevance_labels"]) == {"relevant", "distractor", "ambiguous", "no_answer", "unsafe"}
    assert {case["case_class"] for case in fixture["cases"]} == REQUIRED_CASE_CLASSES
    assert len(fixture["cases"]) == 6

    for case in fixture["cases"]:
        assert case["benchmark_case_id"].startswith("CASE-M015-")
        assert case["query"]["benchmark_query_id"].startswith("QR-M015-")
        assert case["query"]["scope_id"] == "SCOPE-M015-LOCAL-RETRIEVAL-QUALITY-001"
        assert len(case["query"]["query_text_sha256"]) == 64
        assert case["non_authoritative"] is True


def test_fixture_candidate_ids_scores_and_relevance_are_deterministic() -> None:
    fixture = load_fixture()
    candidate_ids: list[str] = []

    for case in fixture["cases"]:
        for candidate in case["candidates"]:
            candidate_ids.append(candidate["candidate_id"])
            assert candidate["candidate_id"].startswith("BQ-M015-")
            assert candidate["score_input_id"].startswith("SCORE-M015-")
            assert candidate["source_artifact"] == "prd/retrieval/fixtures/offline_citation_retrieval_cases.json"
            assert candidate["relevance_label"] in fixture["allowed_relevance_labels"]
            if candidate["relevance_label"] in {"relevant", "distractor"}:
                assert isinstance(candidate["rank"], int)
                assert isinstance(candidate["deterministic_score"], float)
            else:
                assert candidate["rank"] is None
                assert candidate["deterministic_score"] is None
    assert len(candidate_ids) == len(set(candidate_ids))


def test_fixture_expected_metrics_cover_positive_no_answer_ambiguous_and_unsafe_cases() -> None:
    fixture = load_fixture()
    by_class = {case["case_class"]: case for case in fixture["cases"]}

    assert by_class["positive_exact_relevance"]["expected_metrics"] == {"mrr": 1.0, "recall_at_1": 1.0, "recall_at_3": 1.0}
    assert by_class["positive_with_distractor"]["candidates"][0]["relevance_label"] == "relevant"
    assert by_class["positive_with_distractor"]["candidates"][1]["relevance_label"] == "distractor"
    assert by_class["scoped_no_answer_quality"]["expected_metrics"] == {"no_answer_accuracy": 1.0}
    assert by_class["ambiguous_retrieval_rejected"]["expected_metrics"] == {"ambiguous_rejection_rate": 1.0}
    assert by_class["unsafe_payload_rejected"]["expected_metrics"] == {"unsafe_rejection_rate": 1.0}
    assert by_class["environment_boundary"]["expected_diagnostic_codes"] == ["model_runtime_available"]


def test_fixture_diagnostics_are_safe_and_bounded() -> None:
    fixture = load_fixture()

    for case in fixture["cases"]:
        for diagnostic in case["diagnostics"]:
            assert set(diagnostic) <= {
                "code",
                "severity",
                "benchmark_case_id",
                "benchmark_query_id",
                "candidate_id",
                "metric",
                "field_path",
                "proof_artifact",
            }
            assert diagnostic["proof_artifact"] == "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json"
            assert diagnostic["benchmark_case_id"] == case["benchmark_case_id"]


def test_fixture_redaction_forbids_raw_text_vectors_and_provider_payloads() -> None:
    fixture = load_fixture()

    for value in walk(fixture):
        if isinstance(value, Mapping):
            assert not FORBIDDEN_FIELD_NAMES.intersection(value.keys())
        if isinstance(value, str):
            assert "/root/" not in value
            assert ".gsd/exec" not in value
            assert "BEGIN PRIVATE KEY" not in value
            assert "Настоящий Федеральный закон регулирует отношения" not in value
            assert "provider response body" not in value
            assert "legal advice:" not in value
    assert set(fixture["forbidden_payload_fields"]) == FORBIDDEN_FIELD_NAMES


def test_fixture_non_claims_keep_g011_open() -> None:
    fixture = load_fixture()

    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim in fixture["non_claims"]


def test_builder_check_mode_passes_for_checked_in_fixture() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/build-local-retrieval-quality-benchmark.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout) == {
        "case_count": 6,
        "model_id": "deepvk/USER-bge-m3",
        "path": "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json",
        "status": "pass",
    }
