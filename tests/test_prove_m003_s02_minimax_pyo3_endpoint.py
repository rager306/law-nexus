from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-m003-s02-minimax-pyo3-endpoint.py"
VERIFY_SCRIPT_PATH = ROOT / "scripts/verify-m003-s02-minimax-pyo3-endpoint.py"


def synthetic_secret_like_token() -> str:
    return "".join(["s", "k", "-"]) + ("x" * 16)


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
        ("https://user:pass@api.minimax.io/v1", "userinfo-not-allowed"),
        ("https://api.minimax.io/v1?" + "api" + "_key=" + synthetic_secret_like_token(), "query-not-allowed"),
        ("https://api.minimax.io/v1#" + "tok" + "en=" + synthetic_secret_like_token(), "fragment-not-allowed"),
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


def test_unsafe_endpoint_components_are_rejected_without_persisting_user_input() -> None:
    harness = load_harness()

    unsafe_endpoint = "https://user:pass@example@api.minimax.io/v1?" + "api" + "_key=" + synthetic_secret_like_token()
    endpoint = harness.normalize_genai_base_endpoint(unsafe_endpoint)

    assert endpoint["normalization_status"] == "invalid"
    assert endpoint["invalid_endpoint_reason"] == "userinfo-not-allowed"
    assert endpoint["endpoint_input"] == "<rejected-unsafe-endpoint>"
    persisted = json.dumps(endpoint)
    assert "pass@example" not in persisted
    assert "api" + "_key" not in persisted
    assert synthetic_secret_like_token() not in persisted


def test_invalid_endpoint_payload_is_blocked_input_not_provider_failure() -> None:
    harness = load_harness()

    payload = harness.run_proof(
        model=harness.DEFAULT_MODEL,
        endpoint="https://api.minimax.io/v1/models",
        api_key_env=harness.DEFAULT_API_KEY_ENV,
        timeout_seconds=5,
        artifact_dir=None,
        runtime_dir=None,
        keep_workspace=False,
    )

    assert payload["status"] == "blocked-environment"
    assert payload["root_cause"] == "invalid-endpoint"
    assert payload["provider_attempts"] == 0
    assert payload["phase"] == "endpoint-contract"
    assert payload["phases"]["provider"]["status"] == "not-run"


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
        "Graph.ro_query",
    )
    for concept in forbidden_runtime_concepts:
        assert concept not in source


def test_safe_payload_helpers_redact_secrets_and_refuse_forbidden_terms(tmp_path: Path) -> None:
    harness = load_harness()

    payload = harness.build_endpoint_contract_payload(model=harness.DEFAULT_MODEL, endpoint=harness.DEFAULT_ENDPOINT, timeout=5)
    payload["diagnostic"] = "Bearer " + synthetic_secret_like_token()
    sanitized = harness.sanitize(payload)
    json_path, markdown_path = harness.write_artifacts(tmp_path, sanitized)

    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "Bearer" not in persisted
    assert synthetic_secret_like_token() not in persisted
    assert json.loads(json_path.read_text(encoding="utf-8"))["diagnostic"] == "<redacted>"


def test_create_proof_project_generates_s02_scoped_pyo3_genai_workspace(tmp_path: Path) -> None:
    harness = load_harness()

    project_dir = harness.create_proof_project(tmp_path, "https://api.minimax.io/v1/")

    cargo = (project_dir / "Cargo.toml").read_text(encoding="utf-8")
    rust = (project_dir / "src/lib.rs").read_text(encoding="utf-8")
    assert 'name = "m003_s02_minimax_pyo3_endpoint"' in cargo
    assert 'genai = "0.5.3"' in cargo
    assert "pyo3" in cargo
    assert "ServiceTargetResolver::from_resolver_fn" in rust
    assert "AdapterKind::OpenAI" in rust
    assert "with_normalize_reasoning_content(true)" in rust
    assert 'const NORMALIZED_MINIMAX_ENDPOINT: &str = "https://api.minimax.io/v1/";' in rust
    assert "Endpoint::from_owned(NORMALIZED_MINIMAX_ENDPOINT.to_string())" in rust
    assert "auth_debug" not in rust
    assert "Graph.ro_query" not in rust


def test_resolver_metadata_rejects_lost_v1_endpoint_contract() -> None:
    harness = load_harness()

    metadata = {
        "module": harness.MODULE_NAME,
        "model": harness.DEFAULT_MODEL,
        "adapter_kind": "OpenAI",
        "normalized_endpoint_base_url": "https://api.minimax.io/chat/completions",
        "provider_body_persistence": "disabled",
    }

    result = harness.validate_resolver_metadata(
        metadata,
        endpoint_metadata=harness.normalize_genai_base_endpoint(harness.DEFAULT_ENDPOINT),
        model=harness.DEFAULT_MODEL,
    )

    assert result["status"] == "blocked-environment"
    assert result["root_cause"] == "endpoint-contract-lost-v1"
    assert result["phase"] == "resolver"
    assert result["provider_attempts"] == 0


def test_missing_credential_blocks_after_successful_build_import_resolver(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    harness = load_harness()
    monkeypatch.delenv(harness.DEFAULT_API_KEY_ENV, raising=False)

    def fake_run_command(command: list[str], **kwargs: object) -> harness.CommandResult:
        phase = str(kwargs["phase"])
        stdout = ""
        if phase == "python-import-resolver":
            stdout = json.dumps(
                {
                    "module": harness.MODULE_NAME,
                    "model": harness.DEFAULT_MODEL,
                    "adapter_kind": "OpenAI",
                    "normalized_endpoint_base_url": "https://api.minimax.io/v1/",
                    "provider_body_persistence": "disabled",
                }
            )
        return harness.CommandResult(phase, command, 0, False, 1, harness.summarize_stream(stdout), harness.summarize_stream(""), None)

    monkeypatch.setattr(harness, "command_available", lambda name: True)
    monkeypatch.setattr(harness, "run_command", fake_run_command)

    payload = harness.run_proof(
        model=harness.DEFAULT_MODEL,
        endpoint=harness.DEFAULT_ENDPOINT,
        api_key_env=harness.DEFAULT_API_KEY_ENV,
        timeout_seconds=5,
        artifact_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        keep_workspace=False,
    )

    assert payload["status"] == "blocked-credential"
    assert payload["root_cause"] == "minimax-credential-missing"
    assert payload["provider_attempts"] == 0
    assert payload["phases"]["provider"]["status"] == "blocked-credential"


def test_build_failure_stops_before_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    harness = load_harness()
    monkeypatch.setenv(harness.DEFAULT_API_KEY_ENV, "dummy-credential-value")

    def fake_run_command(command: list[str], **kwargs: object) -> harness.CommandResult:
        return harness.CommandResult(
            str(kwargs["phase"]), command, 101, False, 1, harness.summarize_stream(""), harness.summarize_stream("compile error"), None
        )

    monkeypatch.setattr(harness, "command_available", lambda name: True)
    monkeypatch.setattr(harness, "run_command", fake_run_command)

    payload = harness.run_proof(
        model=harness.DEFAULT_MODEL,
        endpoint=harness.DEFAULT_ENDPOINT,
        api_key_env=harness.DEFAULT_API_KEY_ENV,
        timeout_seconds=5,
        artifact_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        keep_workspace=False,
    )

    assert payload["status"] == "blocked-environment"
    assert payload["root_cause"] == "maturin-build-failed"
    assert payload["phases"]["build"]["exit_code"] == 101
    assert payload["provider_attempts"] == 0
    assert payload["phases"]["import"]["status"] == "not-run"
    assert payload["phases"]["provider"]["status"] == "not-run"


def test_provider_error_with_credential_records_one_attempt_without_raw_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    harness = load_harness()
    monkeypatch.setenv(harness.DEFAULT_API_KEY_ENV, "dummy-credential-value")
    calls: list[str] = []

    def fake_run_command(command: list[str], **kwargs: object) -> harness.CommandResult:
        phase = str(kwargs["phase"])
        calls.append(phase)
        if phase == "python-import-resolver":
            stdout = json.dumps(
                {
                    "module": harness.MODULE_NAME,
                    "model": harness.DEFAULT_MODEL,
                    "adapter_kind": "OpenAI",
                    "normalized_endpoint_base_url": "https://api.minimax.io/v1/",
                    "provider_body_persistence": "disabled",
                }
            )
            return harness.CommandResult(phase, command, 0, False, 1, harness.summarize_stream(stdout), harness.summarize_stream(""), None)
        if phase == "minimax-live-provider-call":
            return harness.CommandResult(
                phase,
                command,
                1,
                False,
                1,
                harness.summarize_stream("provider raw body should not persist"),
                harness.summarize_stream("404 not found /chat/completions"),
                None,
            )
        return harness.CommandResult(phase, command, 0, False, 1, harness.summarize_stream(""), harness.summarize_stream(""), None)

    monkeypatch.setattr(harness, "command_available", lambda name: True)
    monkeypatch.setattr(harness, "run_command", fake_run_command)

    payload = harness.run_proof(
        model=harness.DEFAULT_MODEL,
        endpoint=harness.DEFAULT_ENDPOINT,
        api_key_env=harness.DEFAULT_API_KEY_ENV,
        timeout_seconds=5,
        artifact_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
        keep_workspace=False,
    )

    assert payload["status"] == "failed-runtime"
    assert payload["root_cause"] == "endpoint-contract-lost-v1"
    assert payload["provider_attempts"] == 1
    assert calls.count("minimax-live-provider-call") == 1
    assert payload["phases"]["provider"]["raw_provider_body_persisted"] is False
    assert "provider raw body" not in json.dumps(payload)


def test_classify_provider_failures() -> None:
    harness = load_harness()

    assert harness.classify_provider_failure("401 unauthorized") == "minimax-auth-failed"
    assert harness.classify_provider_failure("429 rate limit exceeded") == "minimax-rate-limited"
    assert harness.classify_provider_failure("missing field choices deserialize") == "minimax-openai-schema-mismatch"
    assert harness.classify_provider_failure("404 not found /chat/completions") == "endpoint-contract-lost-v1"
    assert harness.classify_provider_failure("upstream refused connection") == "minimax-provider-call-failed"


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_m003_s02_minimax_pyo3_endpoint", VERIFY_SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_s02_artifacts(tmp_path: Path, payload: dict[str, object], markdown: str | None = None) -> None:
    (tmp_path / "S02-MINIMAX-PYO3-ENDPOINT.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "S02-MINIMAX-PYO3-ENDPOINT.md").write_text(
        markdown
        if markdown is not None
        else "\n".join(
            [
                "# S02 fixture",
                f"Status: `{payload['status']}`",
                f"Model: `{payload['model']}`",
                "Effective chat URL: `https://api.minimax.io/v1/chat/completions`",
                str(payload["boundary_statement"]),
                "- Raw provider body persisted: `False`",
                "- Credentials persisted: `False`",
                "- Auth headers persisted: `False`",
                "- Raw prompt persisted: `False`",
                "- Raw legal text persisted: `False`",
                "- Raw FalkorDB rows persisted: `False`",
                "- Think content persisted: `False`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def base_verifier_payload(status: str = "blocked-credential", root_cause: str = "minimax-credential-missing") -> dict[str, object]:
    harness = load_harness()
    payload = harness.build_endpoint_contract_payload(
        model=harness.DEFAULT_MODEL,
        endpoint=harness.DEFAULT_ENDPOINT,
        timeout=5,
    )
    payload["status"] = status
    payload["root_cause"] = root_cause
    payload["phase"] = "provider" if status == "blocked-credential" else "endpoint-contract"
    payload["provider_attempts"] = 0 if status in {"blocked-credential", "blocked-environment", "not-run-local-only"} else 1
    payload["phases"]["build"] = {"phase": "build", "status": "confirmed-runtime", "root_cause": "none", "category": "build"}
    payload["phases"]["import"] = {"phase": "import", "status": "confirmed-runtime", "root_cause": "none", "category": "import"}
    payload["phases"]["resolver"] = {"phase": "resolver", "status": "confirmed-runtime", "root_cause": "none", "category": "resolver"}
    payload["phases"]["provider"] = {
        "phase": "provider",
        "status": "blocked-credential" if status == "blocked-credential" else "not-run",
        "root_cause": root_cause if status == "blocked-credential" else "not-run",
        "category": "credential" if status == "blocked-credential" else "not-run",
        "raw_provider_body_persisted": False,
    }
    payload["resolver_metadata"] = {
        "module": harness.MODULE_NAME,
        "model": harness.DEFAULT_MODEL,
        "adapter_kind": "OpenAI",
        "normalized_endpoint_base_url": "https://api.minimax.io/v1/",
        "provider_body_persistence": "disabled",
    }
    if status == "confirmed-runtime":
        payload["root_cause"] = "none"
        payload["provider_attempts"] = 1
        payload["phases"]["provider"] = {
            "phase": "provider",
            "status": "confirmed-runtime",
            "root_cause": "none",
            "category": "provider",
            "raw_provider_body_persisted": False,
        }
    return payload


def test_s02_verifier_accepts_truthful_blocked_credential_fixture(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = base_verifier_payload()
    write_s02_artifacts(tmp_path, payload)

    result = verifier.verify_artifacts(tmp_path)

    assert result["verdict"] == "pass"
    assert result["status"] == "blocked-credential"
    assert result["root_cause"] == "minimax-credential-missing"
    assert result["provider_attempts"] == 0


@pytest.mark.parametrize(
    ("mutator", "expected_error"),
    [
        (lambda p: p["endpoint"].update({"effective_chat_completions_url": "https://api.minimax.io/chat/completions"}), "effective_chat_completions_url"),
        (lambda p: p["endpoint"].update({"normalized_base_url": "https://api.minimax.io/v1"}), "normalized_base_url"),
        (lambda p: p.update({"provider_attempts": 1}), "blocked-credential must not claim provider attempts"),
        (lambda p: p.update({"status": "confirmed-runtime", "root_cause": "endpoint-contract-lost-v1", "provider_attempts": 1}), "confirmed-runtime root_cause"),
        (lambda p: p.update({"unsafe": "Bearer " + synthetic_secret_like_token()}), "redaction violation"),
        (lambda p: p.update({"raw_prompt": "Return OK only"}), "unsafe field"),
        (lambda p: p.update({"diagnostic": "<think>hidden reasoning</think>"}), "think"),
    ],
)
def test_s02_verifier_rejects_endpoint_semantic_and_redaction_violations(
    tmp_path: Path, mutator: Callable[[dict[str, object]], object], expected_error: str
) -> None:
    verifier = load_verifier()
    payload = base_verifier_payload()
    mutator(payload)
    write_s02_artifacts(tmp_path, payload)

    with pytest.raises(verifier.VerificationError, match=expected_error):
        verifier.verify_artifacts(tmp_path)


@pytest.mark.parametrize(
    "overclaim",
    [
        "Legal KnowQL product behavior is validated",
        "legal-answer correctness is validated",
        "ODT parsing and retrieval quality are production ready",
        "FalkorDB execution is proven",
        "production schema quality is proven",
        "raw FalkorDB rows: []",
        "RAW_LEGAL_TEXT_SENTINEL article text",
    ],
)
def test_s02_verifier_rejects_boundary_overclaims_and_unsafe_markdown(tmp_path: Path, overclaim: str) -> None:
    verifier = load_verifier()
    payload = base_verifier_payload()
    write_s02_artifacts(tmp_path, payload, markdown=overclaim)

    with pytest.raises(verifier.VerificationError):
        verifier.verify_artifacts(tmp_path)
