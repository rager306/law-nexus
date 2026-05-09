from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts/run-s10-gigaembeddings-proof.py"
VERIFIER_PATH = ROOT / "scripts/verify-s10-embedding-runtime-proof.py"
GIGA_MODEL_ID = "ai-sage/Giga-Embeddings-instruct"
USER_MODEL_ID = "deepvk/USER-bge-m3"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeEncoder:
    def encode(self, texts: list[str], **_kwargs: Any) -> list[list[float]]:
        vectors: list[list[float]] = []
        for index, text in enumerate(texts):
            vector = [0.0] * 2048
            if text.startswith("Instruct:"):
                vector[index % 2048] = 1.0
            else:
                vector[index % 2048] = 1.0
            vectors.append(vector)
        return vectors


def available_packages() -> dict[str, Any]:
    return {
        "status": "available",
        "missing": [],
        "packages": [
            {"package": "transformers==4.51.0", "status": "available", "version": "4.51.0"},
            {"package": "sentence-transformers>=5.1.1", "status": "available", "version": "5.4.1"},
            {"package": "torch", "status": "available", "version": "2.11.0"},
            {"package": "flash-attn", "status": "available", "version": "2.8.3"},
        ],
    }


def missing_flash_packages() -> dict[str, Any]:
    data = available_packages()
    data["status"] = "blocked-environment"
    data["missing"] = ["flash-attn"]
    data["packages"][-1] = {"package": "flash-attn", "status": "absent", "version": None}
    return data


def available_cache() -> dict[str, Any]:
    return {
        "model_id": GIGA_MODEL_ID,
        "status": "available",
        "present": True,
        "checked_paths": ["/tmp/models--ai-sage--Giga-Embeddings-instruct"],
        "snapshot_count": 1,
        "snapshots": ["fixture"],
    }


def safe_resources() -> dict[str, Any]:
    return {
        "python": "3.13.12",
        "platform": "Linux-test",
        "machine": "x86_64",
        "cpu_count": 12,
        "gpu_probe": {"nvidia_smi": "/usr/bin/nvidia-smi", "status": "available"},
        "docker_probe": {"docker": "/usr/bin/docker", "status": "available"},
        "memory_mib": 48_000,
        "memory_available_mib": 40_000,
        "swap_total_mib": 8_000,
        "no_swap": False,
        "disk_mib": {"free_mib": 90_000, "total_mib": 200_000, "used_mib": 110_000},
    }


def test_format_giga_query_uses_required_instruction_and_leaves_documents_plain() -> None:
    runner = load_module("run_s10_gigaembeddings_proof_format", RUNNER_PATH)

    formatted = runner.format_giga_query("Когда заказчик размещает извещение?")
    document = runner.synthetic_documents()[0].text

    assert formatted.startswith("Instruct: ")
    assert "\nQuery: Когда заказчик размещает извещение?" in formatted
    assert not document.startswith("Instruct:")


def test_main_records_terminal_safety_gate_without_overclaim(monkeypatch: Any, tmp_path: Path) -> None:
    runner = load_module("run_s10_gigaembeddings_proof_gated", RUNNER_PATH)
    verifier = load_module("verify_s10_embedding_runtime_proof_for_giga_gate", VERIFIER_PATH)
    output_dir = tmp_path / "S10"

    monkeypatch.setattr(runner, "package_status", lambda _requirements: missing_flash_packages())
    monkeypatch.setattr(runner, "probe_model_cache", lambda _model_id, _roots: available_cache())
    monkeypatch.setattr(runner, "resource_metadata", lambda _output_dir=None: safe_resources())

    exit_code = runner.main(["--output-dir", str(output_dir), "--cache-or-explicit-download", "--require-safety-gate"])

    artifact = output_dir / "S10-EMBEDDING-RUNTIME-PROOF.json"
    giga_artifact = output_dir / "S10-GIGAEMBEDDINGS-PROOF.json"
    result = verifier.verify_artifact(artifact, verifier.VerificationMode.ALLOW_GIGA_BLOCKED_WITH_GATE)
    payload = runner.load_json(artifact)
    giga = next(model for model in payload["models"] if model["id"] == GIGA_MODEL_ID)
    vector = next(proof for proof in payload["vector_proofs"] if proof["dimension"] == 2048)

    assert exit_code == 0
    assert giga_artifact.is_file()
    assert result.ok is True
    assert giga["runtime_status"] == "blocked-environment"
    assert "embedding-packages-missing:flash-attn" in giga["blocked_root_cause"]
    assert giga["instruction_handling"]["query_instruction_applied"] is True
    assert giga["instruction_handling"]["document_instruction_applied"] is False
    assert vector["status"] == "blocked-environment"
    assert vector["blocked_root_cause"] == "encode-proof-unavailable"


def test_main_writes_confirmed_2048_proof_when_gate_and_boundaries_confirm(monkeypatch: Any, tmp_path: Path) -> None:
    runner = load_module("run_s10_gigaembeddings_proof_success", RUNNER_PATH)
    verifier = load_module("verify_s10_embedding_runtime_proof_for_giga_success", VERIFIER_PATH)
    output_dir = tmp_path / "S10"

    monkeypatch.setattr(runner, "package_status", lambda _requirements: available_packages())
    monkeypatch.setattr(runner, "probe_model_cache", lambda _model_id, _roots: available_cache())
    monkeypatch.setattr(runner, "resource_metadata", lambda _output_dir=None: safe_resources())
    monkeypatch.setattr(runner, "load_sentence_transformer", lambda _model_id, _local_files_only, _trust_remote_code: FakeEncoder())
    monkeypatch.setattr(
        runner,
        "run_falkordb_vector_proof",
        lambda *_args, **_kwargs: {
            "status": "confirmed-runtime",
            "index_created": True,
            "query_executed": True,
            "duration_ms": 14.0,
            "blocked_root_cause": None,
            "raw_log_paths": [runner.write_log(output_dir / "logs", "fake-vector-2048", {"status": "confirmed-runtime"})],
        },
    )

    exit_code = runner.main(
        [
            "--output-dir",
            str(output_dir),
            "--cache-or-explicit-download",
            "--require-safety-gate",
            "--allow-custom-code",
            "--allow-trust-remote-code",
        ]
    )

    artifact = output_dir / "S10-EMBEDDING-RUNTIME-PROOF.json"
    result = verifier.verify_artifact(artifact, verifier.VerificationMode.ALLOW_GIGA_BLOCKED_WITH_GATE)
    payload = runner.load_json(artifact)
    giga = next(model for model in payload["models"] if model["id"] == GIGA_MODEL_ID)
    vector = next(proof for proof in payload["vector_proofs"] if proof["dimension"] == 2048)

    assert exit_code == 0
    assert result.ok is True
    assert giga["runtime_status"] == "confirmed-runtime"
    assert giga["observed_vector_dimension"] == 2048
    assert giga["retrieval_metrics"]["fixture_ids_only"] is True
    assert vector["status"] == "confirmed-runtime"


class FakeGraph:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.index_kwargs: dict[str, Any] = {}

    def create_node_vector_index(self, label: str, attr: str, **kwargs: Any) -> object:
        self.index_kwargs = {"label": label, "attr": attr, **kwargs}
        return object()

    def query(self, query: str) -> object:
        self.queries.append(query)
        if query.startswith("CALL db.idx.vector.queryNodes"):
            return type("Result", (), {"result_set": [["doc-1", 0.0]]})()
        return type("Result", (), {"result_set": []})()


class FakeClient:
    def __init__(self, graph: FakeGraph) -> None:
        self.graph = graph

    def select_graph(self, _graph_name: str) -> FakeGraph:
        return self.graph


def test_vector_client_boundary_creates_2048_index_and_logs_no_vectors(tmp_path: Path) -> None:
    runner = load_module("run_s10_gigaembeddings_proof_vector", RUNNER_PATH)
    graph = FakeGraph()
    vector = [0.0] * 2048
    vector[0] = 1.0

    result = runner.run_vector_query_with_client(FakeClient(graph), "fixture_graph", ["doc-1"], [vector], vector, tmp_path / "logs")

    log_text = Path(result["raw_log_paths"][0]).read_text(encoding="utf-8")
    assert result["status"] == "confirmed-runtime"
    assert graph.index_kwargs["dim"] == 2048
    assert "raw_vectors_logged" in log_text
    assert "doc-1" in log_text
    assert "1.00000000" not in log_text
