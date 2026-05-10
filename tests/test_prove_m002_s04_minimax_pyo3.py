from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-m002-s04-minimax-pyo3.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prove_m002_s04_minimax_pyo3", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_redact_masks_credentials_headers_and_secret_like_values() -> None:
    harness = load_harness()

    redacted = harness.redact(
        "Authorization: Bearer sk-testsecret123456789 api_key=minimax-secret token:abcd",
        sensitive_values=["minimax-secret"],
    )

    assert "Bearer sk-" not in redacted
    assert "minimax-secret" not in redacted
    assert "abcd" not in redacted
    assert "<redacted>" in redacted


def test_classify_provider_failure_codes() -> None:
    harness = load_harness()

    assert harness.classify_provider_failure("401 unauthorized invalid api key") == "minimax-auth-failed"
    assert harness.classify_provider_failure("missing field choices in response json") == "minimax-openai-schema-mismatch"
    assert harness.classify_provider_failure("resolver endpoint route failed") == "minimax-endpoint-routing-blocked"
    assert harness.classify_provider_failure("anything else") == "minimax-provider-call-failed"


def test_reasoning_contamination_detects_think_and_prose() -> None:
    harness = load_harness()

    assert harness.detect_reasoning_contamination({"has_think_tag": True})
    assert harness.detect_reasoning_contamination({"candidate_kind": "non_cypher_text"})
    assert not harness.detect_reasoning_contamination({"candidate_kind": "cypher_like", "has_think_tag": False})


def test_create_proof_project_writes_minimax_target_resolver_source(tmp_path: Path) -> None:
    harness = load_harness()

    project_dir = harness.create_proof_project(tmp_path)

    cargo = (project_dir / "Cargo.toml").read_text(encoding="utf-8")
    lib = (project_dir / "src/lib.rs").read_text(encoding="utf-8")

    assert "genai = \"0.5.3\"" in cargo
    assert "text-to-cypher" not in cargo
    assert "ServiceTargetResolver::from_resolver_fn" in lib
    assert "Endpoint::from_static(DEFAULT_MINIMAX_ENDPOINT)" in lib
    assert "AdapterKind::OpenAI" in lib
    assert "MiniMax-M2.7-highspeed" in lib
    assert "https://api.minimax.io/v1" in lib
    assert "with_normalize_reasoning_content(true)" in lib
    assert "TextToCypherClient" not in lib


def test_payload_status_prefers_specific_blockers() -> None:
    harness = load_harness()

    assert (
        harness.payload_status(
            [
                {"status": "confirmed-runtime"},
                {"status": "blocked-credential", "root_cause": "minimax-credential-missing"},
            ]
        )
        == "blocked-credential"
    )
    assert harness.payload_status([{"status": "blocked-environment"}]) == "blocked-environment"
    assert harness.payload_status([{"status": "failed-runtime"}]) == "failed-runtime"
    assert harness.payload_status([{"status": "confirmed-runtime"}]) == "confirmed-runtime"


def test_write_artifacts_preserves_boundary_language_and_safety(tmp_path: Path) -> None:
    harness = load_harness()
    payload = {
        "schema_version": harness.SCHEMA_VERSION,
        "generated_at": "2026-05-10T00:00:00Z",
        "status": "blocked-credential",
        "phase": "credential-check",
        "model": harness.DEFAULT_MODEL,
        "endpoint": harness.DEFAULT_ENDPOINT,
        "provider_attempts": 0,
        "findings": [
            {
                "id": "minimax-live-proof",
                "status": "blocked-credential",
                "phase": "credential-check",
                "root_cause": "minimax-credential-missing",
                "summary": "MiniMax API key was not present; no provider request was made.",
                "diagnostics": {"safe_category": "missing-credential"},
            }
        ],
        "commands": [],
        "boundaries": harness.boundary_payload(),
    }

    json_path, markdown_path = harness.write_artifacts(tmp_path, payload)

    machine = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert machine["status"] == "blocked-credential"
    assert "proof-only MiniMax PyO3/genai adapter route" in markdown
    assert "does not prove Legal KnowQL product behavior" in markdown
    assert "raw provider bodies are not persisted" in markdown
    assert "Authorization" not in markdown
    assert "api_key" not in markdown
    assert "sk-" not in json_path.read_text(encoding="utf-8")


def test_safe_payload_redacts_forbidden_terms_before_persisting(tmp_path: Path) -> None:
    harness = load_harness()

    json_path, markdown_path = harness.write_artifacts(
        tmp_path,
        {
            "schema_version": harness.SCHEMA_VERSION,
            "status": "failed-runtime",
            "phase": "test",
            "findings": [{"summary": "Authorization: Bearer sk-testsecret123456789"}],
            "commands": [],
            "boundaries": harness.boundary_payload(),
        },
    )

    assert "Authorization" not in json_path.read_text(encoding="utf-8")
    assert "Bearer" not in markdown_path.read_text(encoding="utf-8")
    assert "sk-testsecret" not in markdown_path.read_text(encoding="utf-8")
