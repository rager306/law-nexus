from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-semantic-retrieval-safe-inputs.py"
MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/semantic_retrieval_safe_inputs.json"


def load_module(name: str = "semantic_safe_input_verifier") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def expect_error(path: Path, text: str) -> None:
    verifier = load_module(f"semantic_safe_input_{text[:8].replace(' ', '_')}")
    try:
        verifier.verify_manifest(path)
    except verifier.SemanticInputError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("expected SemanticInputError")


def test_checked_in_manifest_passes() -> None:
    verifier = load_module("semantic_safe_input_happy")

    result = verifier.verify_manifest(MANIFEST)

    assert result["status"] == "ok"
    assert result["query_input_count"] == 10
    assert result["candidate_input_count"] == 10
    assert result["diagnostic_codes"] == ["semantic_inputs_verified"]
    assert "does not prove semantic retrieval quality" in result["non_claim_boundary"]


def test_manifest_shape_and_no_forbidden_fragments() -> None:
    manifest = load_manifest()
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    assert manifest["schema_version"] == "semantic-retrieval-safe-inputs/v1"
    assert manifest["query_input_count"] == 10
    assert manifest["candidate_input_count"] == 10
    assert manifest["redaction"]["answer_fields_excluded_from_scoring_inputs"] is True
    for forbidden in ("raw_legal_text", "query_text\"", "provider_payload", "embedding_vector", "expected_label", "expected_candidate_ids", ".gsd/exec", "/root/"):
        assert forbidden not in serialized


def test_fails_closed_for_raw_text_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_inputs"][0]["raw_text"] = "blocked"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_vector_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_inputs"][0]["vector"] = [0.1, 0.2]
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_provider_payload_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["provider_payload"] = {"blocked": True}
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_expected_answer_leakage(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_inputs"][0]["expected_candidate_ids"] = ["CAND-M024-BOGUS"]
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_rank_leakage(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_inputs"][0]["rank"] = 1
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_absolute_path(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["source_fixture"] = "/root/law-nexus/fixture.json"
    expect_error(write_manifest(tmp_path, manifest), "unsafe absolute path")


def test_fails_closed_for_gsd_exec_anchor(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_registry"] = ".gsd/exec/example.stdout"
    expect_error(write_manifest(tmp_path, manifest), "unsafe payload fragment")


def test_fails_closed_for_raw_query_like_token(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_inputs"][0]["representation_tokens"].append("размер обеспечения заявки")
    expect_error(write_manifest(tmp_path, manifest), "unsafe token grammar")


def test_fails_closed_for_absolute_path_token(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_inputs"][0]["representation_tokens"].append("/etc/passwd")
    expect_error(write_manifest(tmp_path, manifest), "unsafe absolute path")


def test_fails_closed_for_generated_prose_like_token(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_inputs"][0]["representation_tokens"].append("answer:allowed")
    expect_error(write_manifest(tmp_path, manifest), "unsafe token prefix")


def test_fails_closed_for_windows_path_token(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_inputs"][0]["representation_tokens"].append(r"C:\\secret\\payload.txt")
    expect_error(write_manifest(tmp_path, manifest), "unsafe absolute path")


def test_fails_closed_for_missing_candidate_coverage(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_inputs"] = manifest["candidate_inputs"][:-1]
    manifest["candidate_input_count"] = len(manifest["candidate_inputs"])
    expect_error(write_manifest(tmp_path, manifest), "representative input coverage mismatch")


def test_fails_closed_for_bad_source_hash(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["source_fixture_sha256"] = "0" * 64
    expect_error(write_manifest(tmp_path, manifest), "sha256 mismatch")
