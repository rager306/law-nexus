from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts/verify-s09-local-embeddings.py"


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_s09_local_embeddings", VERIFIER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def contract_payload() -> dict[str, Any]:
    return {
        "policy": {
            "managed_gigachat_api": "excluded",
            "external_embedding_api_dependency": "excluded",
            "local_open_weight_models_only": True,
        },
        "candidates": [
            {
                "id": "ai-sage/Giga-Embeddings-instruct",
                "role": "quality-first-candidate",
                "license": "mit",
                "vector_dimension": 2048,
                "max_token_limit": 4096,
                "runtime_status": "not-run",
                "benchmark_result_status": "not-run",
                "blocked_root_cause": "runtime pending",
                "owner": "S09",
                "resolution_path": "Run local runtime probe.",
                "verification_criteria": "Record runtime/vector/benchmark status.",
                "roadmap_impact": "Quality challenger only after runtime proof.",
            },
            {
                "id": "deepvk/USER-bge-m3",
                "role": "practical-russian-baseline-candidate",
                "license": "apache-2.0",
                "vector_dimension": 1024,
                "max_token_limit": 8192,
                "runtime_status": "not-run",
                "benchmark_result_status": "not-run",
                "blocked_root_cause": "runtime pending",
                "owner": "S09",
                "resolution_path": "Run local runtime probe.",
                "verification_criteria": "Record runtime/vector/benchmark status.",
                "roadmap_impact": "Practical baseline if runtime proof passes.",
            },
            {
                "id": "BAAI/bge-m3",
                "role": "optional-upstream-baseline-note",
                "license": "mit",
                "vector_dimension": 1024,
                "max_token_limit": 8192,
                "runtime_status": "not-run",
                "benchmark_result_status": "not-run",
                "blocked_root_cause": "optional reference",
                "owner": "S09",
                "resolution_path": "Use only if budget allows.",
                "verification_criteria": "Record same fields if evaluated.",
                "roadmap_impact": "Optional reference only.",
            },
        ],
    }


def model_result(model_id: str, dimension: int, raw_log: str) -> dict[str, Any]:
    return {
        "id": model_id,
        "package_status": "blocked-environment",
        "cache_status": "absent",
        "download_status": "disabled-no-download",
        "runtime_status": "blocked-environment",
        "vector_dimension": dimension,
        "max_token_limit": 4096 if dimension == 2048 else 8192,
        "encode_duration_ms": None,
        "resource_metadata": {"cpu_count": 2},
        "falkordb_vector_compatibility": {
            "dimension": dimension,
            "status": "blocked-environment",
            "blocked_root_cause": "falkordb-client-packages-missing:falkordb,redis",
            "raw_log_paths": [raw_log],
        },
        "benchmark_result_status": "blocked",
        "blocked_root_cause": "embedding-packages-missing",
        "raw_log_paths": [raw_log],
    }


def result_payload(tmp_path: Path) -> dict[str, Any]:
    log_dir = tmp_path / ".gsd/milestones/M001/slices/S09/logs"
    log_dir.mkdir(parents=True)
    logs = {
        "giga": ".gsd/milestones/M001/slices/S09/logs/giga.log",
        "user": ".gsd/milestones/M001/slices/S09/logs/user.log",
        "bge": ".gsd/milestones/M001/slices/S09/logs/bge.log",
        "v1024": ".gsd/milestones/M001/slices/S09/logs/vector-1024.log",
        "v2048": ".gsd/milestones/M001/slices/S09/logs/vector-2048.log",
    }
    for path in logs.values():
        (tmp_path / path).write_text("{}\n", encoding="utf-8")
    return {
        "managed_apis_contacted": False,
        "synthetic_fixtures_only": True,
        "download_mode": "no-download",
        "models": [
            model_result("ai-sage/Giga-Embeddings-instruct", 2048, logs["giga"]),
            model_result("deepvk/USER-bge-m3", 1024, logs["user"]),
            model_result("BAAI/bge-m3", 1024, logs["bge"]),
        ],
        "falkordb_vector_probes": [
            {
                "dimension": 1024,
                "status": "blocked-environment",
                "blocked_root_cause": "falkordb-client-packages-missing:falkordb,redis",
                "raw_log_paths": [logs["v1024"]],
            },
            {
                "dimension": 2048,
                "status": "blocked-environment",
                "blocked_root_cause": "falkordb-client-packages-missing:falkordb,redis",
                "raw_log_paths": [logs["v2048"]],
            },
        ],
    }


def write_artifacts(tmp_path: Path, *, contract: dict[str, Any] | None = None, retrieval: dict[str, Any] | None = None) -> tuple[Path, Path, Path, Path]:
    contract_path = tmp_path / "contract.json"
    markdown_path = tmp_path / "contract.md"
    smoke_path = tmp_path / "smoke.json"
    retrieval_path = tmp_path / "retrieval.json"
    contract_path.write_text(json.dumps(contract_payload() if contract is None else contract), encoding="utf-8")
    markdown_path.write_text("# Contract\n\nManaged APIs are excluded.\n", encoding="utf-8")
    payload = result_payload(tmp_path) if retrieval is None else retrieval
    smoke_path.write_text(json.dumps(payload), encoding="utf-8")
    retrieval_path.write_text(json.dumps(payload), encoding="utf-8")
    return contract_path, markdown_path, smoke_path, retrieval_path


def run_verify(tmp_path: Path, *, contract: dict[str, Any] | None = None, retrieval: dict[str, Any] | None = None, write_recommendation: bool = False) -> Any:
    verifier = load_verifier()
    contract_path, markdown_path, smoke_path, retrieval_path = write_artifacts(tmp_path, contract=contract, retrieval=retrieval)
    return verifier.verify(
        contract_path=contract_path,
        markdown_path=markdown_path,
        smoke_path=smoke_path,
        retrieval_path=retrieval_path,
        require_results=True,
        write_recommendation=write_recommendation,
    )


def test_accepts_complete_bounded_results_and_writes_recommendation(tmp_path: Path) -> None:
    verifier = load_verifier()
    contract_path, markdown_path, smoke_path, retrieval_path = write_artifacts(tmp_path)

    result = verifier.verify(
        contract_path=contract_path,
        markdown_path=markdown_path,
        smoke_path=smoke_path,
        retrieval_path=retrieval_path,
        require_results=True,
        write_recommendation=True,
    )

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert result.ok is True
    assert contract["final_recommendation"]["selected_practical_baseline"] == "deepvk/USER-bge-m3"
    assert contract["final_recommendation"]["quality_challenger"] == "ai-sage/Giga-Embeddings-instruct"
    assert contract["final_recommendation"]["legal_quality_claim"].startswith("not-proven")
    assert "Ты на 100% уверен" in markdown
    assert "bounded-recommendation-blocked-environment" in markdown


def test_rejects_managed_api_policy_regression(tmp_path: Path) -> None:
    contract = contract_payload()
    contract["policy"]["managed_gigachat_api"] = "allowed"

    result = run_verify(tmp_path, contract=contract)

    assert result.ok is False
    assert any("managed_gigachat_api" in error for error in result.errors)


def test_rejects_forbidden_secret_terms(tmp_path: Path) -> None:
    contract_path, markdown_path, smoke_path, retrieval_path = write_artifacts(tmp_path)
    forbidden_env = "GIGACHAT" + "_AUTH_DATA"
    markdown_path.write_text(f"# Contract\n\n{forbidden_env}\n", encoding="utf-8")
    verifier = load_verifier()

    result = verifier.verify(
        contract_path=contract_path,
        markdown_path=markdown_path,
        smoke_path=smoke_path,
        retrieval_path=retrieval_path,
        require_results=True,
        write_recommendation=False,
    )

    assert result.ok is False
    assert any("forbidden" in error for error in result.errors)


def test_rejects_missing_primary_candidate(tmp_path: Path) -> None:
    contract = contract_payload()
    contract["candidates"] = [candidate for candidate in contract["candidates"] if candidate["id"] != "deepvk/USER-bge-m3"]

    result = run_verify(tmp_path, contract=contract)

    assert result.ok is False
    assert any("deepvk/USER-bge-m3" in error and "missing" in error for error in result.errors)


def test_rejects_non_terminal_runtime_status(tmp_path: Path) -> None:
    retrieval = result_payload(tmp_path)
    retrieval["models"][0]["runtime_status"] = "not-run"

    result = run_verify(tmp_path, retrieval=retrieval)

    assert result.ok is False
    assert any("non-terminal runtime_status" in error for error in result.errors)


def test_rejects_missing_raw_logs(tmp_path: Path) -> None:
    retrieval = result_payload(tmp_path)
    retrieval["models"][1]["raw_log_paths"] = []

    result = run_verify(tmp_path, retrieval=retrieval)

    assert result.ok is False
    assert any("raw_log_paths" in error for error in result.errors)


def test_rejects_missing_vector_probe_dimensions(tmp_path: Path) -> None:
    retrieval = result_payload(tmp_path)
    retrieval["falkordb_vector_probes"] = [retrieval["falkordb_vector_probes"][0]]

    result = run_verify(tmp_path, retrieval=retrieval)

    assert result.ok is False
    assert any("1024 and 2048" in error for error in result.errors)


def test_rejects_vector_dimension_mismatch(tmp_path: Path) -> None:
    retrieval = result_payload(tmp_path)
    retrieval["models"][0]["falkordb_vector_compatibility"]["dimension"] = 1024

    result = run_verify(tmp_path, retrieval=retrieval)

    assert result.ok is False
    assert any("dimension mismatch" in error for error in result.errors)
