from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-m003-s02-minimax-pyo3-endpoint.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prove_m003_s02_minimax_pyo3_endpoint", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("endpoint_input", "expected_status", "expected_applied"),
    [
        ("https://api.minimax.io/v1", "normalized", True),
        ("https://api.minimax.io/v1/", "already-normalized", False),
        ("https://api.minimax.io/v1/chat/completions", "normalized", True),
    ],
)
def test_endpoint_normalization_preserves_v1_chat_completions(
    endpoint_input: str, expected_status: str, expected_applied: bool
) -> None:
    harness = load_harness()

    endpoint = harness.normalize_genai_base_endpoint(endpoint_input)

    assert endpoint["endpoint_input"] == endpoint_input
    assert endpoint["normalized_base_url"] == "https://api.minimax.io/v1/"
    assert endpoint["effective_chat_completions_url"] == "https://api.minimax.io/v1/chat/completions"
    assert endpoint["preserves_v1"] is True
    assert endpoint["normalization_applied"] is expected_applied
    assert endpoint["normalization_status"] == expected_status
    assert endpoint["endpoint_contract_valid"] is True


@pytest.mark.parametrize(
    ("endpoint_input", "reason"),
    [
        ("", "empty"),
        ("api.minimax.io/v1", "unsupported-scheme"),
        ("http://api.minimax.io/v1", "unsupported-scheme"),
        ("https:///v1", "missing-host"),
        ("https://example.com/v1", "unsupported-host"),
        ("https://api.minimax.io", "missing-v1-path"),
        ("https://api.minimax.io/v2/chat/completions", "missing-v1-path"),
        ("https://api.minimax.io/proxy/v1/chat/completions", "missing-v1-path"),
        ("https://api.minimax.io/v1/models", "unsupported-path"),
    ],
)
def test_endpoint_invalid_inputs_block_before_provider_phase(endpoint_input: str, reason: str) -> None:
    harness = load_harness()

    endpoint = harness.normalize_genai_base_endpoint(endpoint_input)

    assert endpoint["normalization_status"] == "invalid"
    assert endpoint["status"] == "blocked-environment"
    assert endpoint["root_cause"] == "invalid-endpoint"
    assert endpoint["invalid_endpoint_reason"] == reason
    assert endpoint["endpoint_contract_valid"] is False
    assert endpoint["normalized_base_url"] is None
    assert endpoint["effective_chat_completions_url"] is None
    assert endpoint["preserves_v1"] is False


def test_invalid_endpoint_payload_is_blocked_input_not_provider_failure() -> None:
    harness = load_harness()

    payload = harness.build_local_payload(model=harness.DEFAULT_MODEL, endpoint="https://api.minimax.io/v1/models", timeout=5)

    assert payload["status"] == "blocked-environment"
    assert payload["root_cause"] == "invalid-endpoint"
    assert payload["provider_attempts"] == 0
    assert payload["phase"] == "endpoint-contract"
    assert payload["phases"]["provider"] == "not-run-in-t01"


def test_boundary_text_names_s02_proof_limits_without_claiming_product_behavior() -> None:
    harness = load_harness()

    boundary = harness.BOUNDARY_STATEMENT

    assert "proof harness" in boundary
    assert "Legal KnowQL product behavior" in boundary
    assert "legal-answer correctness" in boundary
    assert "S03 validation" in boundary
    assert "FalkorDB execution" in boundary
    assert "ODT parsing" in boundary
    assert "retrieval quality" in boundary
    assert "production schema quality" in boundary


def test_s02_harness_does_not_reintroduce_m002_s04_validation_or_graph_runtime_logic() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    forbidden_runtime_concepts = (
        "DEFAULT_FALKOR_HOST",
        "DEFAULT_FALKOR_PORT",
        "FalkorClient",
        "FalkorGraph",
        "load_s03_validator",
        "S03_VALIDATOR_PATH",
        "DEFAULT_SCHEMA_CONTRACT",
        "READ_ONLY_TIMEOUT_MS",
        "default_safe_candidate",
        "generated_cypher",
        "schema_contract",
    )
    for concept in forbidden_runtime_concepts:
        assert concept not in source


def test_safe_payload_helpers_redact_secrets_and_refuse_forbidden_terms(tmp_path: Path) -> None:
    harness = load_harness()

    payload = harness.build_local_payload(model=harness.DEFAULT_MODEL, endpoint=harness.DEFAULT_ENDPOINT, timeout=5)
    payload["diagnostic"] = "Bearer sk-secret123456789"
    sanitized = harness.sanitize(payload)
    json_path, markdown_path = harness.write_artifacts(tmp_path, sanitized)

    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "Bearer" not in persisted
    assert "sk-secret" not in persisted
    assert json.loads(json_path.read_text(encoding="utf-8"))["diagnostic"] == "<redacted>"
