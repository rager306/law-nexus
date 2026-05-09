from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/smoke-s09-local-embeddings.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_s09_local_embeddings", HARNESS_PATH)
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
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_model_cache_name_uses_huggingface_directory_convention() -> None:
    harness = load_harness()

    assert harness.model_cache_name("deepvk/USER-bge-m3") == "models--deepvk--USER-bge-m3"
    assert (
        harness.model_cache_name("ai-sage/Giga-Embeddings-instruct")
        == "models--ai-sage--Giga-Embeddings-instruct"
    )


def test_huggingface_cache_roots_prefer_explicit_env_and_deduplicate(tmp_path: Path) -> None:
    harness = load_harness()
    hub = tmp_path / "hf-hub"
    home = tmp_path / "hf-home"

    roots = harness.huggingface_cache_roots(
        {"HUGGINGFACE_HUB_CACHE": str(hub), "HF_HOME": str(home)}
    )

    assert roots[:2] == (hub, home / "hub")
    assert Path.home() / ".cache/huggingface/hub" in roots


def test_probe_model_cache_reports_absent_and_present_snapshots(tmp_path: Path) -> None:
    harness = load_harness()
    absent = harness.probe_model_cache("deepvk/USER-bge-m3", [tmp_path / "hub"])
    assert absent.present is False
    assert absent.status == "absent"
    assert "models--deepvk--USER-bge-m3" in absent.checked_paths[0]

    snapshot = tmp_path / "hub" / "models--deepvk--USER-bge-m3" / "snapshots" / "abc123"
    snapshot.mkdir(parents=True)
    present = harness.probe_model_cache("deepvk/USER-bge-m3", [tmp_path / "hub"])
    assert present.present is True
    assert present.status == "available"
    assert present.snapshots == ("abc123",)


def test_no_download_absent_cache_blocks_without_encode_attempt(tmp_path: Path, monkeypatch) -> None:
    harness = load_harness()

    def fake_package_probe(packages: list[str]) -> dict[str, object]:
        return {"status": "available", "missing": [], "packages": []}

    def fail_encode(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("encode must not run when cache is absent in no-download mode")

    monkeypatch.setattr(harness, "probe_required_packages", fake_package_probe)
    monkeypatch.setattr(harness, "encode_with_sentence_transformers", fail_encode)
    result = harness.probe_candidate(
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
    )

    assert result["package_status"] == "available"
    assert result["cache_status"] == "absent"
    assert result["download_status"] == "disabled-no-download"
    assert result["runtime_status"] == "blocked-environment"
    assert result["blocked_root_cause"] == "model-cache-absent-no-download"
    assert result["falkordb_vector_compatibility"]["status"] == "pending-dimension-specific-probe"
    assert Path(tmp_path / "logs" / "deepvk__USER-bge-m3.log").is_file()


def test_missing_packages_are_reported_as_blocked_root_cause(tmp_path: Path, monkeypatch) -> None:
    harness = load_harness()

    def fake_find_spec(import_name: str) -> object | None:
        if import_name == "torch":
            return object()
        return None

    monkeypatch.setattr(harness.importlib.util, "find_spec", fake_find_spec)
    result = harness.probe_required_packages(["sentence-transformers", "transformers", "torch"])

    assert result["status"] == "blocked-environment"
    assert result["missing"] == ["sentence-transformers", "transformers"]
    root = harness.blocked_root_cause("blocked-environment", result["missing"], True, False)
    assert root == "embedding-packages-missing:sentence-transformers,transformers"


def test_main_writes_no_download_artifacts_without_managed_api_terms(tmp_path: Path, monkeypatch) -> None:
    harness = load_harness()
    contract = tmp_path / "contract.json"
    write_contract(contract)
    output_dir = tmp_path / "out"

    def fake_package_probe(packages: list[str]) -> dict[str, object]:
        return {"status": "blocked-environment", "missing": list(packages), "packages": []}

    monkeypatch.setattr(harness, "probe_required_packages", fake_package_probe)
    exit_code = harness.main(["--contract", str(contract), "--output-dir", str(output_dir), "--no-download"])

    assert exit_code == 0
    payload_path = output_dir / "S09-LOCAL-EMBEDDING-SMOKE.json"
    markdown_path = output_dir / "S09-LOCAL-EMBEDDING-SMOKE.md"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["download_mode"] == "no-download"
    assert payload["managed_apis_contacted"] is False
    assert {model["id"] for model in payload["models"]} == {
        "deepvk/USER-bge-m3",
        "ai-sage/Giga-Embeddings-instruct",
    }
    assert all(model["raw_log_paths"] for model in payload["models"])
    combined = payload_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "GIGACHAT_AUTH_DATA" not in combined
    assert "managed GigaChat" in combined


def test_encode_success_records_shape_when_download_is_allowed(tmp_path: Path, monkeypatch) -> None:
    harness = load_harness()

    def fake_package_probe(_packages: list[str]) -> dict[str, object]:
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
        return {
            "runtime_status": "confirmed-runtime",
            "encode_duration_ms": 12.5,
            "vector_count": 2,
            "observed_vector_dimension": 2048,
            "error": None,
        }

    monkeypatch.setattr(harness, "probe_required_packages", fake_package_probe)
    monkeypatch.setattr(harness, "encode_with_sentence_transformers", fake_encode)
    result = harness.probe_candidate(
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
    )

    assert result["download_status"] == "allowed-download-may-run"
    assert result["runtime_status"] == "confirmed-runtime"
    assert result["observed_vector_dimension"] == 2048
    assert result["encode_duration_ms"] == 12.5
    assert result["blocked_root_cause"] is None


def test_contract_filters_to_s09_open_weight_allow_list(tmp_path: Path) -> None:
    harness = load_harness()
    contract = {
        "candidates": [
            {"id": "deepvk/USER-bge-m3"},
            {"id": "ai-sage/Giga-Embeddings-instruct"},
            {"id": "BAAI/bge-m3"},
            {"id": "managed/provider-model"},
        ]
    }

    candidates = harness.configured_candidates(contract)

    assert [candidate["id"] for candidate in candidates] == [
        "deepvk/USER-bge-m3",
        "ai-sage/Giga-Embeddings-instruct",
        "BAAI/bge-m3",
    ]
