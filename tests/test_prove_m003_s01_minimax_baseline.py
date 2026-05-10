from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib import error

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-m003-s01-minimax-baseline.py"
VERIFY_SCRIPT_PATH = ROOT / "scripts/verify-m003-s01-minimax-baseline.py"


class FakeResponse:
    def __init__(self, body: bytes, *, status: int = 200) -> None:
        self.body = body
        self.status = status

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prove_m003_s01_minimax_baseline", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_m003_s01_minimax_baseline", VERIFY_SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.minimax.io/v1",
        "https://api.minimax.io/v1/",
        "https://api.minimax.io/v1/chat/completions",
    ],
)
def test_compose_chat_completions_url_preserves_v1(base_url: str) -> None:
    harness = load_harness()

    endpoint = harness.compose_chat_completions_url(base_url)

    assert endpoint["base_url_input"] == base_url
    assert endpoint["effective_url"] == "https://api.minimax.io/v1/chat/completions"
    assert endpoint["preserves_v1"] is True


def test_build_request_body_sets_minimax_reasoning_split_contract() -> None:
    harness = load_harness()

    body = harness.build_request_body(user_prompt="Generate safe Cypher without raw legal text.")

    assert body["model"] == "MiniMax-M2.7-highspeed"
    assert body["reasoning_split"] is True
    assert body["stream"] is False
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"


def test_response_classifier_accepts_cypher_like_match_and_call_content() -> None:
    harness = load_harness()

    match_shape = harness.classify_response_shape(
        {"choices": [{"message": {"content": "MATCH (n) RETURN n LIMIT 1"}}]}
    )
    call_shape = harness.classify_response_shape({"choices": [{"message": {"content": "CALL db.labels()"}}]})

    assert match_shape["root_cause"] is None
    assert match_shape["content_kind"] == "cypher_like"
    assert match_shape["candidate_prefix"] == "MATCH"
    assert call_shape["root_cause"] is None
    assert call_shape["candidate_prefix"] == "CALL"


@pytest.mark.parametrize(
    "decoded",
    [
        {},
        {"choices": None},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": 42}}]},
    ],
)
def test_response_classifier_malformed_choices_are_safe_schema_mismatches(decoded: object) -> None:
    harness = load_harness()

    shape = harness.classify_response_shape(decoded)

    assert shape["status"] == "failed-runtime"
    assert shape["root_cause"] == "provider-schema-mismatch"
    assert "raw_body" not in json.dumps(shape)


def test_response_classifier_detects_think_contamination_without_persisting_content() -> None:
    harness = load_harness()

    shape = harness.classify_response_shape(
        {"choices": [{"message": {"content": "<think>hidden chain</think> MATCH (n) RETURN n"}}]}
    )

    assert shape["status"] == "failed-runtime"
    assert shape["root_cause"] == "reasoning-contamination"
    assert shape["has_think_tag"] is True
    assert "hidden chain" not in json.dumps(shape)


@pytest.mark.parametrize(
    ("reasoning_details", "expected_count", "expected_types"),
    [
        (
            [{"type": "reasoning.summary"}, {"type": "reasoning.trace"}],
            2,
            ["reasoning.summary", "reasoning.trace"],
        ),
        ({"type": "reasoning.summary"}, 1, ["dict"]),
        ("present", 1, ["str"]),
    ],
)
def test_response_classifier_categorizes_reasoning_details_without_values(
    reasoning_details: object, expected_count: int, expected_types: list[str]
) -> None:
    harness = load_harness()

    shape = harness.classify_response_shape(
        {
            "choices": [
                {
                    "message": {
                        "content": "MATCH (n) RETURN n",
                        "reasoning_details": reasoning_details,
                    }
                }
            ]
        }
    )

    assert shape["has_reasoning_details"] is True
    assert shape["reasoning_details_count"] == expected_count
    assert shape["reasoning_detail_types"] == expected_types
    serialized = json.dumps(shape)
    assert "present" not in serialized
    if expected_count == 2:
        assert "reasoning.trace" in serialized


def test_missing_credential_blocks_before_http_and_writes_safe_artifacts(tmp_path: Path) -> None:
    harness = load_harness()
    calls: list[Any] = []

    def fail_if_called(*args: Any, **kwargs: Any) -> FakeResponse:
        calls.append((args, kwargs))
        raise AssertionError("HTTP should not be attempted without credentials")

    payload, sensitive_values = harness.build_live_payload(
        model=harness.DEFAULT_MODEL,
        base_url=harness.DEFAULT_BASE_URL,
        timeout=5,
        api_key_env="MINIMAX_API_KEY",
        environ={},
        urlopen=fail_if_called,
    )
    json_path, markdown_path = harness.write_artifacts(tmp_path, payload, sensitive_values=sensitive_values)

    assert calls == []
    assert payload["status"] == "blocked-credential"
    assert payload["root_cause"] == "minimax-credential-missing"
    assert payload["provider_attempts"] == 0
    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "Bearer" not in persisted
    assert "Return one read-only" not in persisted


def test_live_payload_posts_once_with_reasoning_split_and_confirms_runtime(tmp_path: Path) -> None:
    harness = load_harness()
    calls: list[tuple[Any, int]] = []

    def fake_urlopen(req: Any, *, timeout: int) -> FakeResponse:
        calls.append((req, timeout))
        body = json.dumps({"choices": [{"message": {"content": "MATCH (n) RETURN n LIMIT 1"}}]}).encode()
        return FakeResponse(body, status=200)

    payload, sensitive_values = harness.build_live_payload(
        model=harness.DEFAULT_MODEL,
        base_url=harness.DEFAULT_BASE_URL,
        timeout=7,
        api_key_env="MINIMAX_API_KEY",
        environ={"MINIMAX_API_KEY": "sk-testsecret123456"},
        urlopen=fake_urlopen,
    )
    json_path, markdown_path = harness.write_artifacts(tmp_path, payload, sensitive_values=sensitive_values)

    assert len(calls) == 1
    req, timeout = calls[0]
    request_body = json.loads(req.data.decode("utf-8"))
    assert timeout == 7
    assert req.full_url == "https://api.minimax.io/v1/chat/completions"
    assert req.headers["Authorization"] == "Bearer sk-testsecret123456"
    assert request_body["reasoning_split"] is True
    assert request_body["stream"] is False
    assert payload["status"] == "confirmed-runtime"
    assert payload["root_cause"] is None
    assert payload["provider_attempts"] == 1
    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "MATCH (n) RETURN" not in persisted
    assert "sk-testsecret" not in persisted
    assert "Bearer" not in persisted
    assert "Return one read-only" not in persisted


@pytest.mark.parametrize(
    ("status_code", "expected_root_cause"),
    [
        (401, "minimax-auth-failed"),
        (429, "minimax-rate-limited"),
        (500, "minimax-http-5xx"),
    ],
)
def test_http_error_paths_are_categorical_and_safe(
    tmp_path: Path, status_code: int, expected_root_cause: str
) -> None:
    harness = load_harness()

    def fake_urlopen(_req: Any, *, timeout: int) -> FakeResponse:
        _ = timeout
        raise error.HTTPError(
            url="https://api.minimax.io/v1/chat/completions",
            code=status_code,
            msg="simulated RAW_LEGAL_TEXT_SENTINEL Bearer sk-testsecret123456",
            hdrs=None,
            fp=None,
        )

    payload, sensitive_values = harness.build_live_payload(
        model=harness.DEFAULT_MODEL,
        base_url=harness.DEFAULT_BASE_URL,
        timeout=5,
        api_key_env="MINIMAX_API_KEY",
        environ={"MINIMAX_API_KEY": "sk-testsecret123456"},
        urlopen=fake_urlopen,
    )
    json_path, markdown_path = harness.write_artifacts(tmp_path, payload, sensitive_values=sensitive_values)

    assert payload["status"] == "failed-runtime"
    assert payload["root_cause"] == expected_root_cause
    assert payload["provider_attempts"] == 1
    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "RAW_LEGAL_TEXT_SENTINEL" not in persisted
    assert "simulated" not in persisted
    assert "sk-testsecret" not in persisted


def test_timeout_path_is_categorical_and_attempted_once(tmp_path: Path) -> None:
    harness = load_harness()

    def fake_urlopen(_req: Any, *, timeout: int) -> FakeResponse:
        _ = timeout
        raise TimeoutError("timed out with raw provider detail")

    payload, sensitive_values = harness.build_live_payload(
        model=harness.DEFAULT_MODEL,
        base_url=harness.DEFAULT_BASE_URL,
        timeout=5,
        api_key_env="MINIMAX_API_KEY",
        environ={"MINIMAX_API_KEY": "sk-testsecret123456"},
        urlopen=fake_urlopen,
    )
    json_path, markdown_path = harness.write_artifacts(tmp_path, payload, sensitive_values=sensitive_values)

    assert payload["status"] == "failed-runtime"
    assert payload["root_cause"] == "provider-timeout"
    assert payload["provider_attempts"] == 1
    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "raw provider detail" not in persisted


def test_invalid_json_path_is_schema_mismatch_without_raw_body(tmp_path: Path) -> None:
    harness = load_harness()

    def fake_urlopen(_req: Any, *, timeout: int) -> FakeResponse:
        _ = timeout
        return FakeResponse(b"not-json RAW_LEGAL_TEXT_SENTINEL Bearer sk-testsecret123456", status=200)

    payload, sensitive_values = harness.build_live_payload(
        model=harness.DEFAULT_MODEL,
        base_url=harness.DEFAULT_BASE_URL,
        timeout=5,
        api_key_env="MINIMAX_API_KEY",
        environ={"MINIMAX_API_KEY": "sk-testsecret123456"},
        urlopen=fake_urlopen,
    )
    json_path, markdown_path = harness.write_artifacts(tmp_path, payload, sensitive_values=sensitive_values)

    assert payload["status"] == "failed-runtime"
    assert payload["root_cause"] == "provider-schema-mismatch"
    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "not-json" not in persisted
    assert "RAW_LEGAL_TEXT_SENTINEL" not in persisted


@pytest.mark.parametrize(
    ("content", "expected_root_cause"),
    [
        ("<think>private reasoning</think> MATCH (n) RETURN n", "reasoning-contamination"),
        ("Here is a query: MATCH (n) RETURN n", "non-cypher-content"),
    ],
)
def test_provider_content_failures_are_categorical_without_content_persistence(
    tmp_path: Path, content: str, expected_root_cause: str
) -> None:
    harness = load_harness()

    def fake_urlopen(_req: Any, *, timeout: int) -> FakeResponse:
        _ = timeout
        return FakeResponse(json.dumps({"choices": [{"message": {"content": content}}]}).encode(), status=200)

    payload, sensitive_values = harness.build_live_payload(
        model=harness.DEFAULT_MODEL,
        base_url=harness.DEFAULT_BASE_URL,
        timeout=5,
        api_key_env="MINIMAX_API_KEY",
        environ={"MINIMAX_API_KEY": "sk-testsecret123456"},
        urlopen=fake_urlopen,
    )
    json_path, markdown_path = harness.write_artifacts(tmp_path, payload, sensitive_values=sensitive_values)

    assert payload["status"] == "failed-runtime"
    assert payload["root_cause"] == expected_root_cause
    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "private reasoning" not in persisted
    assert "Here is a query" not in persisted


def test_artifacts_preserve_boundaries_and_never_persist_prompts_or_raw_bodies(tmp_path: Path) -> None:
    harness = load_harness()
    prompt = "RAW_LEGAL_TEXT_SENTINEL: Article 1 secret prompt"
    request_body = harness.build_request_body(user_prompt=prompt)
    payload = {
        "schema_version": harness.SCHEMA_VERSION,
        "generated_at": "2026-05-10T00:00:00Z",
        "status": "confirmed-runtime",
        "root_cause": None,
        "model": harness.DEFAULT_MODEL,
        "endpoint": harness.compose_chat_completions_url(harness.DEFAULT_BASE_URL),
        "request_contract": {
            "reasoning_split_requested": True,
            "stream_requested": False,
            "message_count": 2,
            "user_message_persisted": False,
        },
        "provider_attempts": 1,
        "request_body": request_body,
        "provider_diagnostics": {"category": "http-success", "http_status_class": "2xx"},
        "response_shape": harness.classify_response_shape(
            {"choices": [{"message": {"content": "MATCH (n) RETURN n LIMIT 1"}}]}
        ),
        "raw_response_body": "Authorization: Bearer sk-testsecret123456 RAW_LEGAL_TEXT_SENTINEL",
        "boundaries": harness.boundary_payload(),
        "safety": {"raw_body_persisted": False, "credential_persisted": False},
    }

    json_path, markdown_path = harness.write_artifacts(tmp_path, payload)

    machine_text = json_path.read_text(encoding="utf-8")
    markdown = markdown_path.read_text(encoding="utf-8")
    persisted = machine_text + markdown
    machine = json.loads(machine_text)
    assert machine["request_body"] == "<omitted-request-body>"
    assert "direct MiniMax OpenAI-compatible baseline proof" in markdown
    assert "does not prove Legal KnowQL product behavior" in markdown
    assert "raw provider bodies are not persisted" in markdown
    assert prompt not in persisted
    assert "RAW_LEGAL_TEXT_SENTINEL" not in persisted
    assert "Authorization" not in persisted
    assert "Bearer" not in persisted
    assert "sk-testsecret" not in persisted


def test_assert_safe_payload_rejects_secret_like_values() -> None:
    harness = load_harness()

    with pytest.raises(ValueError, match="forbidden term"):
        harness.assert_safe_payload({"unsafe": "Bearer sk-testsecret123456"})


def test_write_artifacts_redacts_secret_like_fields_before_persisting(tmp_path: Path) -> None:
    harness = load_harness()

    json_path, markdown_path = harness.write_artifacts(
        tmp_path,
        {
            "schema_version": harness.SCHEMA_VERSION,
            "status": "failed-runtime",
            "root_cause": "provider-schema-mismatch",
            "authorization_header": "Authorization: Bearer sk-testsecret123456",
            "api_key": "sk-testsecret123456",
            "secret_note": "token=abcd1234",
            "boundaries": harness.boundary_payload(),
        },
    )

    persisted = json_path.read_text(encoding="utf-8") + markdown_path.read_text(encoding="utf-8")
    assert "authorization_header" not in persisted
    assert "api_key" not in persisted
    assert "secret_note" not in persisted
    assert "Authorization" not in persisted
    assert "Bearer" not in persisted
    assert "sk-testsecret" not in persisted


def write_verifier_fixture(tmp_path: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    harness = load_harness()
    return harness.write_artifacts(tmp_path, payload)


def clone_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload))


def blocked_credential_payload() -> dict[str, Any]:
    harness = load_harness()
    return harness.build_missing_credential_payload(
        model=harness.DEFAULT_MODEL,
        base_url=harness.DEFAULT_BASE_URL,
        api_key_env="MINIMAX_API_KEY",
    )


def confirmed_runtime_payload() -> dict[str, Any]:
    harness = load_harness()

    def fake_urlopen(_req: Any, *, timeout: int) -> FakeResponse:
        _ = timeout
        body = json.dumps({"choices": [{"message": {"content": "MATCH (n) RETURN n LIMIT 1"}}]}).encode()
        return FakeResponse(body, status=200)

    payload, _sensitive_values = harness.build_live_payload(
        model=harness.DEFAULT_MODEL,
        base_url=harness.DEFAULT_BASE_URL,
        timeout=5,
        api_key_env="MINIMAX_API_KEY",
        environ={"MINIMAX_API_KEY": "sk-testsecret123456"},
        urlopen=fake_urlopen,
    )
    return payload


def verify_mutated_payload_rejection(tmp_path: Path, payload: dict[str, Any], match: str) -> None:
    verifier = load_verifier()
    write_verifier_fixture(tmp_path, payload)

    with pytest.raises(verifier.VerificationError, match=match):
        verifier.verify_artifacts(tmp_path)


def test_verifier_accepts_truthful_blocked_credential_artifact(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = blocked_credential_payload()
    write_verifier_fixture(tmp_path, payload)

    result = verifier.verify_artifacts(tmp_path)

    assert result["verdict"] == "pass"
    assert result["status"] == "blocked-credential"
    assert result["root_cause"] == "minimax-credential-missing"
    assert result["provider_attempts"] == 0


def test_verifier_accepts_confirmed_runtime_only_with_candidate_like_content(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = confirmed_runtime_payload()
    write_verifier_fixture(tmp_path, payload)

    result = verifier.verify_artifacts(tmp_path)

    assert result["verdict"] == "pass"
    assert result["status"] == "confirmed-runtime"
    assert result["provider_attempts"] == 1


def test_verifier_rejects_missing_v1_chat_completions_endpoint(tmp_path: Path) -> None:
    payload = blocked_credential_payload()
    payload["endpoint"]["effective_url"] = "https://api.minimax.io/chat/completions"

    verify_mutated_payload_rejection(tmp_path, payload, "effective_url")


def test_verifier_rejects_missing_reasoning_split_request(tmp_path: Path) -> None:
    payload = blocked_credential_payload()
    del payload["request_contract"]["reasoning_split_requested"]

    verify_mutated_payload_rejection(tmp_path, payload, "reasoning_split_requested")


def test_verifier_rejects_confirmed_runtime_without_provider_attempt(tmp_path: Path) -> None:
    payload = confirmed_runtime_payload()
    payload["provider_attempts"] = 0

    verify_mutated_payload_rejection(tmp_path, payload, "provider_attempts >= 1")


def test_verifier_rejects_secret_like_strings_in_json_artifact(tmp_path: Path) -> None:
    verifier = load_verifier()
    harness = load_harness()
    payload = blocked_credential_payload()
    json_path, _markdown_path = write_verifier_fixture(tmp_path, payload)
    machine = json.loads(json_path.read_text(encoding="utf-8"))
    machine["provider_diagnostics"]["leaked_detail"] = "token=abcd1234"
    json_path.write_text(json.dumps(machine), encoding="utf-8")

    with pytest.raises(verifier.VerificationError, match="redaction violation"):
        verifier.verify_artifacts(tmp_path)
    assert harness.JSON_ARTIFACT in str(json_path)


def test_verifier_rejects_raw_body_and_prompt_flags(tmp_path: Path) -> None:
    payload = blocked_credential_payload()
    payload["safety"]["raw_body_persisted"] = True

    verify_mutated_payload_rejection(tmp_path, payload, "raw_body_persisted")


def test_verifier_rejects_boundary_overclaims(tmp_path: Path) -> None:
    payload = clone_payload(blocked_credential_payload())
    payload["boundaries"]["does_not_prove"] = [
        item for item in payload["boundaries"]["does_not_prove"] if "S03 validation" not in item
    ]

    verify_mutated_payload_rejection(tmp_path, payload, "S03 validation")


def test_verifier_rejects_confirmed_runtime_with_think_tag_contamination(tmp_path: Path) -> None:
    payload = confirmed_runtime_payload()
    payload["response_shape"]["has_think_tag"] = True
    payload["response_shape"]["root_cause"] = "reasoning-contamination"

    verify_mutated_payload_rejection(tmp_path, payload, "think-tag")
