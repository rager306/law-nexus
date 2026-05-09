from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts/run-s10-user-bge-m3-proof.py"
VERIFIER_PATH = ROOT / "scripts/verify-s10-embedding-runtime-proof.py"
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
        for index, _text in enumerate(texts):
            vector = [0.0] * 1024
            vector[index % 1024] = 1.0
            vectors.append(vector)
        return vectors


def available_packages() -> dict[str, Any]:
    return {
        "status": "available",
        "missing": [],
        "packages": [
            {"package": "sentence-transformers", "status": "available", "version": "5.4.1"},
            {"package": "transformers", "status": "available", "version": "4.51.0"},
            {"package": "torch", "status": "available", "version": "2.11.0"},
        ],
    }


def available_cache() -> dict[str, Any]:
    return {
        "model_id": USER_MODEL_ID,
        "status": "available",
        "present": True,
        "checked_paths": ["/tmp/models--deepvk--USER-bge-m3"],
        "snapshot_count": 1,
        "snapshots": ["fixture"],
    }


def test_main_writes_verifier_compatible_user_proof_when_boundaries_confirm(monkeypatch: Any, tmp_path: Path) -> None:
    runner = load_module("run_s10_user_bge_m3_proof_success", RUNNER_PATH)
    verifier = load_module("verify_s10_embedding_runtime_proof_for_runner", VERIFIER_PATH)
    output_dir = tmp_path / "S10"

    monkeypatch.setattr(runner, "package_status", lambda _requirements: available_packages())
    monkeypatch.setattr(runner, "probe_model_cache", lambda _model_id, _roots: available_cache())
    monkeypatch.setattr(runner, "load_sentence_transformer", lambda _model_id, _local_files_only: FakeEncoder())
    monkeypatch.setattr(
        runner,
        "run_falkordb_vector_proof",
        lambda *_args, **_kwargs: {
            "status": "confirmed-runtime",
            "index_created": True,
            "query_executed": True,
            "duration_ms": 12.5,
            "blocked_root_cause": None,
            "raw_log_paths": [runner.write_log(output_dir / "logs", "fake-vector", {"status": "confirmed-runtime"})],
        },
    )

    exit_code = runner.main(["--output-dir", str(output_dir), "--cache-or-explicit-download"])

    artifact = output_dir / "S10-EMBEDDING-RUNTIME-PROOF.json"
    user_artifact = output_dir / "S10-USER-BGE-M3-PROOF.json"
    result = verifier.verify_artifact(artifact, verifier.VerificationMode.REQUIRE_USER_PROOF)
    assert exit_code == 0
    assert user_artifact.is_file()
    assert result.ok is True


def test_main_records_terminal_blocker_without_overclaim_when_encode_fails(monkeypatch: Any, tmp_path: Path) -> None:
    runner = load_module("run_s10_user_bge_m3_proof_blocked", RUNNER_PATH)
    verifier = load_module("verify_s10_embedding_runtime_proof_for_blocked_runner", VERIFIER_PATH)
    output_dir = tmp_path / "S10"

    def raise_encoder(_model_id: str, _local_files_only: bool) -> FakeEncoder:
        raise RuntimeError("fixture model load failed")

    monkeypatch.setattr(runner, "package_status", lambda _requirements: available_packages())
    monkeypatch.setattr(runner, "probe_model_cache", lambda _model_id, _roots: available_cache())
    monkeypatch.setattr(runner, "load_sentence_transformer", raise_encoder)

    exit_code = runner.main(["--output-dir", str(output_dir)])

    artifact = output_dir / "S10-EMBEDDING-RUNTIME-PROOF.json"
    allow_blocked = verifier.verify_artifact(artifact, verifier.VerificationMode.ALLOW_BLOCKED)
    require_user = verifier.verify_artifact(artifact, verifier.VerificationMode.REQUIRE_USER_PROOF)
    payload = runner.load_json(artifact)
    user = next(model for model in payload["models"] if model["id"] == USER_MODEL_ID)
    vector = next(proof for proof in payload["vector_proofs"] if proof["dimension"] == 1024)

    assert exit_code == 1
    assert allow_blocked.ok is True
    assert require_user.ok is False
    assert user["verdict"] == "blocked-baseline"
    assert user["runtime_status"] != "confirmed-runtime"
    assert user["blocked_root_cause"].startswith("encode-runtime-failed")
    assert vector["status"] == "blocked-environment"
    assert vector["blocked_root_cause"] == "encode-proof-unavailable"


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


def test_vector_client_boundary_creates_1024_index_and_logs_no_vectors(tmp_path: Path) -> None:
    runner = load_module("run_s10_user_bge_m3_proof_vector", RUNNER_PATH)
    graph = FakeGraph()
    vector = [0.0] * 1024
    vector[0] = 1.0

    result = runner.run_vector_query_with_client(
        FakeClient(graph),
        "fixture_graph",
        ["doc-1"],
        [vector],
        vector,
        tmp_path / "logs",
    )

    log_text = Path(result["raw_log_paths"][0]).read_text(encoding="utf-8")
    assert result["status"] == "confirmed-runtime"
    assert graph.index_kwargs["dim"] == 1024
    assert "raw_vectors_logged" in log_text
    assert "doc-1" in log_text
    assert "1.00000000" not in log_text
