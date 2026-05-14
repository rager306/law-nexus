from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHECK_PATH = ROOT / "scripts/check-local-retrieval-runtime.py"


def load_check_module(name: str = "check_local_retrieval_runtime") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, CHECK_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_stdout_json(capsys: Any) -> dict[str, Any]:
    captured = capsys.readouterr()
    return json.loads(captured.out)


def test_confirmed_runtime_emits_deterministic_safe_json(monkeypatch: Any, capsys: Any) -> None:
    check = load_check_module("check_local_retrieval_runtime_confirmed")

    monkeypatch.setattr(
        check,
        "probe_dependency_versions",
        lambda: ({"torch": "2.11.0", "sentence-transformers": "5.4.1", "transformers": "4.51.0"}, []),
    )
    monkeypatch.setattr(check, "load_s10_metadata", lambda: {"id": check.MODEL_ID})
    monkeypatch.setattr(check, "model_cache_present", lambda: True)
    monkeypatch.setattr(check, "encode_dimension", lambda: check.EXPECTED_VECTOR_DIMENSION)

    exit_code = check.main([])
    payload = parse_stdout_json(capsys)

    assert exit_code == 0
    assert payload == {
        "dependency_versions": {
            "sentence-transformers": "5.4.1",
            "torch": "2.11.0",
            "transformers": "4.51.0",
        },
        "diagnostic_codes": [],
        "execution_mode": "local_open_weight",
        "expected_vector_dimension": 1024,
        "failure_class": "none",
        "giga_chat_used": False,
        "managed_api_used": False,
        "model_id": "deepvk/USER-bge-m3",
        "network_used": False,
        "non_claims": list(check.NON_CLAIMS),
        "provider_payload_persisted": False,
        "raw_legal_text_persisted": False,
        "raw_vectors_persisted": False,
        "redaction": check.redaction_flags(),
        "runtime_status": "confirmed_runtime",
        "schema_version": "local-retrieval-runtime-boundary/v1",
        "source_artifacts": list(check.SOURCE_ARTIFACTS),
        "vector_dimension": 1024,
    }


def test_missing_dependency_fails_closed_but_allow_unavailable_returns_zero(
    monkeypatch: Any, capsys: Any
) -> None:
    check = load_check_module("check_local_retrieval_runtime_missing_dep")

    monkeypatch.setattr(check, "probe_dependency_versions", lambda: ({"torch": "2.11.0"}, ["transformers"]))

    exit_code = check.main(["--allow-unavailable"])
    payload = parse_stdout_json(capsys)

    assert exit_code == 0
    assert payload["runtime_status"] == "blocked_environment"
    assert payload["failure_class"] == "environment"
    assert payload["diagnostic_codes"] == ["LRR_DEPENDENCY_MISSING"]
    assert payload["managed_api_used"] is False
    assert payload["network_used"] is False
    assert "vector_dimension" not in payload


def test_missing_model_cache_is_model_unavailable(monkeypatch: Any) -> None:
    check = load_check_module("check_local_retrieval_runtime_missing_model")

    monkeypatch.setattr(check, "probe_dependency_versions", lambda: ({"torch": "2.11.0"}, []))
    monkeypatch.setattr(check, "load_s10_metadata", lambda: {"id": check.MODEL_ID})
    monkeypatch.setattr(check, "model_cache_present", lambda: False)

    payload = check.build_runtime_report()

    assert payload["runtime_status"] == "blocked_model_unavailable"
    assert payload["failure_class"] == "model_unavailable"
    assert payload["diagnostic_codes"] == ["LRR_MODEL_CACHE_MISSING"]


def test_malformed_s10_metadata_fails_closed(monkeypatch: Any) -> None:
    check = load_check_module("check_local_retrieval_runtime_bad_s10")

    def raise_bad_metadata() -> dict[str, Any]:
        raise check.RuntimeCheckError("fixture malformed metadata")

    monkeypatch.setattr(check, "probe_dependency_versions", lambda: ({"torch": "2.11.0"}, []))
    monkeypatch.setattr(check, "load_s10_metadata", raise_bad_metadata)

    payload = check.build_runtime_report()

    assert payload["runtime_status"] == "blocked_environment"
    assert payload["failure_class"] == "environment"
    assert payload["diagnostic_codes"] == ["LRR_S10_METADATA_MALFORMED"]


def test_forbidden_gigachat_environment_is_reported_without_using_api(
    monkeypatch: Any, capsys: Any
) -> None:
    check = load_check_module("check_local_retrieval_runtime_forbidden_env")
    monkeypatch.setenv("GIGACHAT_AUTH_DATA", "redacted-test-value")

    exit_code = check.main(["--allow-unavailable"])
    payload = parse_stdout_json(capsys)

    assert exit_code == 0
    assert payload["runtime_status"] == "blocked_policy_violation"
    assert payload["failure_class"] == "policy_violation"
    assert payload["diagnostic_codes"] == ["LRR_MANAGED_API_FORBIDDEN"]
    assert payload["managed_api_used"] is False
    assert payload["giga_chat_used"] is False
    assert "redacted-test-value" not in json.dumps(payload)


def test_dimension_mismatch_fails_closed(monkeypatch: Any) -> None:
    check = load_check_module("check_local_retrieval_runtime_dimension")

    monkeypatch.setattr(check, "probe_dependency_versions", lambda: ({"torch": "2.11.0"}, []))
    monkeypatch.setattr(check, "load_s10_metadata", lambda: {"id": check.MODEL_ID})
    monkeypatch.setattr(check, "model_cache_present", lambda: True)
    monkeypatch.setattr(check, "encode_dimension", lambda: 768)

    payload = check.build_runtime_report()

    assert payload["runtime_status"] == "blocked_dimension_mismatch"
    assert payload["failure_class"] == "dimension_mismatch"
    assert payload["diagnostic_codes"] == ["LRR_DIMENSION_MISMATCH"]
    assert payload["vector_dimension"] == 768


def test_unsafe_output_is_rejected() -> None:
    check = load_check_module("check_local_retrieval_runtime_unsafe")
    payload = check.base_payload()
    payload["unsafe_path"] = "/root/secret-runtime.log"

    try:
        check.validate_payload(payload)
    except check.RuntimeCheckError as exc:
        assert "unsafe output" in str(exc)
    else:
        raise AssertionError("validate_payload must reject unsafe absolute paths")


def test_no_inference_mode_is_explicitly_not_run(monkeypatch: Any, capsys: Any) -> None:
    check = load_check_module("check_local_retrieval_runtime_no_inference")

    monkeypatch.setattr(check, "probe_dependency_versions", lambda: ({"torch": "2.11.0"}, []))
    monkeypatch.setattr(check, "load_s10_metadata", lambda: {"id": check.MODEL_ID})
    monkeypatch.setattr(check, "model_cache_present", lambda: True)

    exit_code = check.main(["--no-inference", "--allow-unavailable"])
    payload = parse_stdout_json(capsys)

    assert exit_code == 0
    assert payload["runtime_status"] == "not_run_contract_only"
    assert payload["diagnostic_codes"] == ["LRR_NOT_RUN_CONTRACT_ONLY"]
