from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/smoke-m002-text-to-cypher-pyo3.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_m002_text_to_cypher_pyo3", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_positive_timeout_rejects_invalid_values() -> None:
    harness = load_harness()

    assert harness.parse_positive_timeout("5") == 5
    with pytest.raises(Exception):
        harness.parse_positive_timeout("0")
    with pytest.raises(Exception):
        harness.parse_positive_timeout("nope")


def test_redact_masks_secret_like_values() -> None:
    harness = load_harness()

    redacted = harness.redact("api_key=sk-testsecret123456789 token:abcd1234")

    assert "sk-testsecret" not in redacted
    assert "abcd1234" not in redacted
    assert "<redacted>" in redacted


def test_create_smoke_project_writes_proof_only_sources(tmp_path: Path) -> None:
    harness = load_harness()

    project_dir = harness.create_smoke_project(tmp_path)

    cargo = (project_dir / "Cargo.toml").read_text(encoding="utf-8")
    lib = (project_dir / "src/lib.rs").read_text(encoding="utf-8")
    pyproject = (project_dir / "pyproject.toml").read_text(encoding="utf-8")

    assert "text-to-cypher" in cargo
    assert "default-features = false" in cargo
    assert "pyo3" in cargo
    assert "requires-python = \">=3.13\"" in pyproject
    assert "provider_calls" in lib
    assert "skipped-by-design" in lib
    assert "__redacted_test_key__" in lib
    assert "text_to_cypher(" not in lib
    assert "cypher_only(" not in lib


def test_payload_status_confirms_only_build_and_import() -> None:
    harness = load_harness()

    assert (
        harness.payload_status(
            {
                "maturin-build": {"status": "confirmed-runtime"},
                "python-import": {"status": "confirmed-runtime"},
                "provider-backed-generation": {"status": "skipped"},
            }
        )
        == "confirmed-runtime"
    )
    assert (
        harness.payload_status(
            {
                "maturin-build": {"status": "failed-runtime"},
                "provider-backed-generation": {"status": "skipped"},
            }
        )
        == "failed-runtime"
    )
    assert harness.payload_status({"provider-backed-generation": {"status": "skipped"}}) == "blocked-environment"


def test_write_artifacts_preserves_boundary_language(tmp_path: Path) -> None:
    harness = load_harness()
    payload = {
        "schema_version": harness.SCHEMA_VERSION,
        "status": "confirmed-runtime",
        "provider_calls": "skipped-by-design",
        "falkordb_url": "falkor://127.0.0.1:6380",
        "findings": [
            {
                "id": "provider-backed-generation",
                "status": "skipped",
                "evidence_class": "out-of-scope",
                "summary": "Provider-backed cypher generation was skipped by design.",
                "diagnostics": {"root_cause": "provider-required-skipped"},
            }
        ],
    }

    json_path, markdown_path = harness.write_artifacts(tmp_path, payload)

    json_text = json_path.read_text(encoding="utf-8")
    markdown = markdown_path.read_text(encoding="utf-8")
    assert '"schema_version": "m002-text-to-cypher-pyo3-smoke/v1"' in json_text
    assert "provider-required-skipped" in markdown
    assert "does not prove provider-backed NL-to-Cypher generation" in markdown
    assert "Legal KnowQL product behavior" in markdown
    assert "legal-answer correctness" in markdown
