from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / "scripts/probe-s10-embedding-runtime-env.py"
VERIFIER_PATH = ROOT / "scripts/verify-s10-embedding-runtime-proof.py"


def load_probe() -> ModuleType:
    spec = importlib.util.spec_from_file_location("probe_s10_embedding_runtime_env", PROBE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_s10_embedding_runtime_proof", VERIFIER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def contract_payload() -> dict[str, Any]:
    return {
        "candidates": [
            {
                "id": "deepvk/USER-bge-m3",
                "role": "practical-russian-baseline-candidate",
                "vector_dimension": 1024,
                "max_token_limit": 8192,
                "runtime_requirements": {
                    "python_packages": ["sentence-transformers", "transformers", "torch"],
                },
            },
            {
                "id": "ai-sage/Giga-Embeddings-instruct",
                "role": "quality-first-candidate",
                "vector_dimension": 2048,
                "max_token_limit": 4096,
                "runtime_requirements": {
                    "python_packages": [
                        "transformers==4.51.0",
                        "sentence-transformers==5.1.1",
                        "torch",
                        "flash-attn",
                    ],
                },
            },
            {
                "id": "managed/provider",
                "vector_dimension": 1536,
                "runtime_requirements": {"python_packages": []},
            },
        ]
    }


def write_contract(tmp_path: Path) -> Path:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract_payload()), encoding="utf-8")
    return path


def test_parse_download_modes() -> None:
    probe = load_probe()

    no_download = probe.parse_args(["--no-download"])
    cache_only = probe.parse_args(["--cache-only"])
    user = probe.parse_args(["--allow-download-user"])
    giga = probe.parse_args(["--allow-download-giga"])

    assert probe.parse_download_mode(no_download) == ("disabled", set())
    assert probe.parse_download_mode(cache_only) == ("cache-only", set())
    assert probe.parse_download_mode(user) == ("explicit-open-weight-only", {"deepvk/USER-bge-m3"})
    assert probe.parse_download_mode(giga) == (
        "explicit-open-weight-only",
        {"ai-sage/Giga-Embeddings-instruct"},
    )


def test_cache_probe_uses_huggingface_snapshot_convention(tmp_path: Path) -> None:
    probe = load_probe()
    root = tmp_path / "hub"

    absent = probe.probe_cache("deepvk/USER-bge-m3", [root])
    snapshot = root / "models--deepvk--USER-bge-m3" / "snapshots" / "abc123"
    snapshot.mkdir(parents=True)
    present = probe.probe_cache("deepvk/USER-bge-m3", [root])

    assert absent["status"] == "absent"
    assert absent["present"] is False
    assert present["status"] == "available"
    assert present["present"] is True
    assert present["snapshots"] == ["abc123"]


def test_package_probe_classifies_missing_imports(monkeypatch) -> None:
    probe = load_probe()

    def fake_find_spec(import_name: str) -> object | None:
        return object() if import_name == "torch" else None

    monkeypatch.setattr(probe.importlib.util, "find_spec", fake_find_spec)
    result = probe.probe_packages(["sentence-transformers", "torch"])

    assert result["status"] == "blocked-environment"
    assert result["missing"] == ["sentence-transformers"]


def test_model_entry_fails_closed_when_packages_missing(tmp_path: Path) -> None:
    probe = load_probe()
    candidate = contract_payload()["candidates"][0]
    hardware = {"python": "3.13", "platform": "linux", "cpu_count": 2, "memory_mib": 4096, "no_swap": True}

    model = probe.model_entry(
        candidate,
        package_probe={"status": "blocked-environment", "missing": ["torch"], "packages": []},
        cache_probe={"status": "absent", "present": False},
        downloads_policy="disabled",
        allowed_downloads=set(),
        hardware=hardware,
        log_dir=tmp_path / "logs",
    )

    assert model["id"] == "deepvk/USER-bge-m3"
    assert model["status"] == "blocked-environment"
    assert model["verdict"] == "blocked-baseline"
    assert model["blocked_root_cause"] == "embedding-packages-missing:torch"
    assert model["encode_duration_ms"] is None
    assert model["raw_log_paths"]


def test_giga_model_records_not_safe_gate_without_gpu(tmp_path: Path) -> None:
    probe = load_probe()
    candidate = contract_payload()["candidates"][1]
    hardware = {
        "python": "3.13",
        "platform": "linux",
        "cpu_count": 2,
        "memory_mib": 4096,
        "no_swap": True,
        "gpu_probe": {"status": "absent"},
    }

    model = probe.model_entry(
        candidate,
        package_probe={"status": "available", "missing": [], "packages": []},
        cache_probe={"status": "available", "present": True},
        downloads_policy="cache-only",
        allowed_downloads=set(),
        hardware=hardware,
        log_dir=tmp_path / "logs",
    )

    assert model["status"] == "not-safe-to-run"
    assert model["verdict"] == "not-safe-challenger"
    assert model["safety_gate"]["status"] == "not-safe-to-run"
    assert "gpu-not-detected" in model["safety_gate"]["reasons"]
    assert model["instruction_handling"]["query_instruction_applied"] is True


def test_main_writes_verifier_compatible_no_download_artifact(tmp_path: Path, monkeypatch) -> None:
    probe = load_probe()
    verifier = load_verifier()
    contract = write_contract(tmp_path)
    output_dir = tmp_path / "out"

    def fake_package_probe(requirements: list[str]) -> dict[str, Any]:
        return {"status": "blocked-environment", "missing": list(requirements), "packages": []}

    monkeypatch.setattr(probe, "probe_packages", fake_package_probe)
    exit_code = probe.main(["--contract", str(contract), "--output-dir", str(output_dir), "--no-download"])

    artifact = output_dir / "S10-EMBEDDING-RUNTIME-PROOF.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    result = verifier.verify_artifact(artifact, verifier.VerificationMode.ALLOW_BLOCKED)

    assert exit_code == 0
    assert result.ok is True
    assert payload["policy"]["downloads"] == "disabled"
    assert {model["id"] for model in payload["models"]} == {
        "deepvk/USER-bge-m3",
        "ai-sage/Giga-Embeddings-instruct",
    }
    assert {proof["dimension"] for proof in payload["vector_proofs"]} == {1024, 2048}
    assert payload["confidence_loop"]["question"] == "Ты на 100% уверен в этой стратегии?"


def test_allow_download_user_only_marks_user_download_as_allowed(tmp_path: Path, monkeypatch) -> None:
    probe = load_probe()
    contract = write_contract(tmp_path)
    output_dir = tmp_path / "out"

    def fake_package_probe(_requirements: list[str]) -> dict[str, Any]:
        return {"status": "available", "missing": [], "packages": []}

    monkeypatch.setattr(probe, "probe_packages", fake_package_probe)
    monkeypatch.setattr(probe, "hardware_metadata", lambda: {"python": "3.13", "platform": "linux", "cpu_count": 2, "memory_mib": 4096, "no_swap": False, "gpu_probe": {"status": "absent"}, "docker_probe": {"status": "absent"}})
    exit_code = probe.main(
        ["--contract", str(contract), "--output-dir", str(output_dir), "--allow-download-user"]
    )

    payload = json.loads((output_dir / "S10-EMBEDDING-RUNTIME-PROOF.json").read_text(encoding="utf-8"))
    by_id = {model["id"]: model for model in payload["models"]}

    assert exit_code == 0
    assert payload["policy"]["downloads"] == "explicit-open-weight-only"
    assert by_id["deepvk/USER-bge-m3"]["download_status"] == "allowed-download-not-executed-by-env-probe"
    assert by_id["ai-sage/Giga-Embeddings-instruct"]["download_status"] == "disabled"


def test_write_artifact_rejects_forbidden_literal(tmp_path: Path) -> None:
    probe = load_probe()
    forbidden = "GIGACHAT" + "_AUTH_DATA"

    payload = {"bad": forbidden}

    try:
        probe.write_artifact(tmp_path, payload)
    except ValueError as exc:
        assert "forbidden" in str(exc)
    else:
        raise AssertionError("write_artifact must reject forbidden credential literals")
