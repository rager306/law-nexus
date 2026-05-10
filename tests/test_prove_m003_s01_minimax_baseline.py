from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-m003-s01-minimax-baseline.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prove_m003_s01_minimax_baseline", SCRIPT_PATH)
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
    call_shape = harness.classify_response_shape(
        {"choices": [{"message": {"content": "CALL db.labels()"}}]}
    )

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


def test_artifacts_preserve_boundaries_and_never_persist_prompts_or_raw_bodies(
    tmp_path: Path,
) -> None:
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
        "provider_attempts": 1,
        "request_body": request_body,
        "response_shape": harness.classify_response_shape(
            {"choices": [{"message": {"content": "MATCH (n) RETURN n LIMIT 1"}}]}
        ),
        "raw_response_body": "Authorization: Bearer sk-testsecret123456 RAW_LEGAL_TEXT_SENTINEL",
        "boundaries": harness.boundary_payload(),
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
