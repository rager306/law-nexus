from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR_PATH = ROOT / "scripts/evaluate-s09-local-embeddings.py"


def load_evaluator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("evaluate_s09_local_embeddings", EVALUATOR_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_contract(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "test-contract/v1",
                "candidates": [
                    {
                        "id": "deepvk/USER-bge-m3",
                        "role": "practical-russian-baseline-candidate",
                        "vector_dimension": 1024,
                        "max_token_limit": 8192,
                        "runtime_requirements": {
                            "python_packages": ["sentence-transformers", "transformers", "torch"],
                            "trust_remote_code_required": False,
                        },
                    },
                    {
                        "id": "ai-sage/Giga-Embeddings-instruct",
                        "role": "quality-first-candidate",
                        "vector_dimension": 2048,
                        "max_token_limit": 4096,
                        "runtime_requirements": {
                            "python_packages": [
                                "transformers",
                                "sentence-transformers",
                                "torch",
                                "flash-attn",
                            ],
                            "trust_remote_code_required": True,
                        },
                    },
                    {
                        "id": "managed/provider-model",
                        "vector_dimension": 1536,
                        "runtime_requirements": {"python_packages": []},
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def perfect_fixture_vectors(evaluator: ModuleType) -> tuple[list[list[float]], list[list[float]]]:
    size = len(evaluator.DOCUMENTS)
    vectors = [[1.0 if row == column else 0.0 for column in range(size)] for row in range(size)]
    return vectors, vectors


def test_fixture_ids_are_deterministic_and_do_not_log_contents() -> None:
    evaluator = load_evaluator()

    metadata = evaluator.fixture_metadata()

    assert metadata["deterministic_ids"] is True
    assert metadata["contents_logged"] is False
    assert metadata["documents"] == [
        "doc-procurement-notice-term",
        "doc-contract-performance-penalty",
        "doc-court-appeal-deadline",
        "doc-personal-data-consent",
    ]
    assert metadata["queries"] == [
        "query-procurement-notice-term",
        "query-contract-performance-penalty",
        "query-court-appeal-deadline",
        "query-personal-data-consent",
    ]


def test_giga_query_instruction_and_document_no_instruction_are_explicit() -> None:
    evaluator = load_evaluator()

    giga_query = evaluator.format_query_for_model("ai-sage/Giga-Embeddings-instruct", "Что искать?")
    user_query = evaluator.format_query_for_model("deepvk/USER-bge-m3", "Что искать?")
    document = evaluator.format_document_for_model("ai-sage/Giga-Embeddings-instruct", "Текст нормы")

    assert giga_query.startswith("Instruct: ")
    assert "\nQuery: Что искать?" in giga_query
    assert user_query == "Что искать?"
    assert document == "Текст нормы"


def test_retrieval_metrics_score_perfect_fixture_vectors() -> None:
    evaluator = load_evaluator()
    query_vectors, document_vectors = perfect_fixture_vectors(evaluator)

    metrics = evaluator.compute_retrieval_metrics(query_vectors, document_vectors)

    assert metrics["query_count"] == 4
    assert metrics["document_count"] == 4
    assert metrics["recall_at_1"] == 1.0
    assert metrics["recall_at_3"] == 1.0
    assert metrics["mrr"] == 1.0
    assert all(hit["rank"] == 1 for hit in metrics["top_hits"])


def test_no_download_absent_cache_blocks_runtime_and_records_vector_probe(
    tmp_path: Path, monkeypatch
) -> None:
    evaluator = load_evaluator()

    def fake_package_probe(packages: list[str]) -> dict[str, Any]:
        if packages == ["falkordb", "redis"]:
            return {"status": "blocked-environment", "missing": ["falkordb", "redis"], "packages": []}
        return {"status": "available", "missing": [], "packages": []}

    def fail_encode(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("encode must not run when cache is absent in no-download mode")

    monkeypatch.setattr(evaluator, "probe_required_packages", fake_package_probe)
    monkeypatch.setattr(evaluator, "encode_fixture_with_sentence_transformers", fail_encode)
    vector_probe = evaluator.probe_falkordb_vector_dimension(1024, tmp_path / "logs")
    result = evaluator.evaluate_candidate(
        {
            "id": "deepvk/USER-bge-m3",
            "role": "practical-russian-baseline-candidate",
            "vector_dimension": 1024,
            "max_token_limit": 8192,
            "runtime_requirements": {
                "python_packages": ["sentence-transformers", "transformers", "torch"],
                "trust_remote_code_required": False,
            },
        },
        cache_roots=[tmp_path / "empty-cache"],
        allow_download=False,
        log_dir=tmp_path / "logs",
        resources={"cpu_count": 2},
        vector_probes={1024: vector_probe},
    )

    assert result["package_status"] == "available"
    assert result["cache_status"] == "absent"
    assert result["download_status"] == "disabled-no-download"
    assert result["runtime_status"] == "blocked-environment"
    assert result["benchmark_result_status"] == "blocked"
    assert result["blocked_root_cause"] == "model-cache-absent-no-download"
    assert result["falkordb_vector_compatibility"]["dimension"] == 1024
    assert result["falkordb_vector_compatibility"]["status"] == "blocked-environment"
    assert result["raw_log_paths"]


def test_evaluate_candidate_records_successful_metrics_and_instruction_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    evaluator = load_evaluator()

    def fake_package_probe(_packages: list[str]) -> dict[str, Any]:
        return {"status": "available", "missing": [], "packages": []}

    def fake_encode(
        model_id: str,
        *,
        allow_download: bool,
        trust_remote_code: bool,
        max_token_limit: int | None,
    ) -> dict[str, object]:
        assert model_id == "ai-sage/Giga-Embeddings-instruct"
        assert allow_download is True
        assert trust_remote_code is True
        assert max_token_limit == 4096
        query_vectors, document_vectors = perfect_fixture_vectors(evaluator)
        return {
            "runtime_status": "confirmed-runtime",
            "encode_duration_ms": 14.25,
            "observed_vector_dimension": 2048,
            "metrics": evaluator.compute_retrieval_metrics(query_vectors, document_vectors),
            "error": None,
        }

    monkeypatch.setattr(evaluator, "probe_required_packages", fake_package_probe)
    monkeypatch.setattr(evaluator, "encode_fixture_with_sentence_transformers", fake_encode)
    vector_probe = {"dimension": 2048, "status": "not-attempted", "raw_log_paths": []}
    result = evaluator.evaluate_candidate(
        {
            "id": "ai-sage/Giga-Embeddings-instruct",
            "role": "quality-first-candidate",
            "vector_dimension": 2048,
            "max_token_limit": 4096,
            "runtime_requirements": {
                "python_packages": ["transformers", "sentence-transformers", "torch", "flash-attn"],
                "trust_remote_code_required": True,
            },
        },
        cache_roots=[tmp_path / "empty-cache"],
        allow_download=True,
        log_dir=tmp_path / "logs",
        resources={"cpu_count": 2},
        vector_probes={2048: vector_probe},
    )

    assert result["runtime_status"] == "confirmed-runtime"
    assert result["benchmark_result_status"] == "completed"
    assert result["retrieval_metrics"]["recall_at_1"] == 1.0
    assert result["observed_vector_dimension"] == 2048
    assert result["instruction_handling"]["query_instruction_applied"] is True
    assert result["instruction_handling"]["document_instruction_applied"] is False
    assert result["blocked_root_cause"] is None


def test_main_writes_artifacts_and_updates_contract_without_managed_api_terms(
    tmp_path: Path, monkeypatch
) -> None:
    evaluator = load_evaluator()
    contract = tmp_path / "contract.json"
    write_contract(contract)
    output_dir = tmp_path / "out"

    def fake_package_probe(_packages: list[str]) -> dict[str, Any]:
        return {"status": "blocked-environment", "missing": ["package-a"], "packages": []}

    monkeypatch.setattr(evaluator, "probe_required_packages", fake_package_probe)
    exit_code = evaluator.main(["--contract", str(contract), "--output-dir", str(output_dir), "--no-download"])

    assert exit_code == 0
    payload_path = output_dir / "S09-LOCAL-EMBEDDING-RETRIEVAL-EVAL.json"
    markdown_path = output_dir / "S09-LOCAL-EMBEDDING-RETRIEVAL-EVAL.md"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    contract_payload = json.loads(contract.read_text(encoding="utf-8"))
    assert payload["download_mode"] == "no-download"
    assert payload["managed_apis_contacted"] is False
    assert {probe["dimension"] for probe in payload["falkordb_vector_probes"]} == {1024, 2048}
    assert {model["id"] for model in payload["models"]} == {
        "deepvk/USER-bge-m3",
        "ai-sage/Giga-Embeddings-instruct",
    }
    assert "latest_synthetic_retrieval_evaluation" in contract_payload
    assert contract_payload["latest_synthetic_retrieval_evaluation"]["vector_probe_dimensions"] == [1024, 2048]
    forbidden_env = "GIGACHAT" + "_AUTH_DATA"
    combined = payload_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert forbidden_env not in combined
    assert "managed GigaChat" in combined
