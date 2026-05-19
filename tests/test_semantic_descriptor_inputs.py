from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-semantic-descriptor-inputs.py"
MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/semantic_descriptor_inputs.json"


def load_module(name: str = "semantic_descriptor_input_verifier") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "descriptor_manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def expect_error(path: Path, text: str) -> None:
    verifier = load_module(f"semantic_descriptor_{text[:8].replace(' ', '_')}")
    try:
        verifier.verify_manifest(path)
    except verifier.DescriptorInputError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("expected DescriptorInputError")


def test_checked_in_manifest_passes() -> None:
    verifier = load_module("semantic_descriptor_happy")

    result = verifier.verify_manifest(MANIFEST)

    assert result["status"] == "ok"
    assert result["representation_kind"] == "safe_semantic_descriptor_v1"
    assert result["query_descriptor_count"] == 10
    assert result["candidate_descriptor_count"] == 10
    assert result["diagnostic_codes"] == ["semantic_descriptors_verified"]
    assert "does not prove semantic retrieval quality" in result["non_claim_boundary"]


def test_cli_emits_compact_ok_json() -> None:
    completed = subprocess.run(
        [sys.executable, str(VERIFIER)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["candidate_descriptor_count"] == 10


def test_manifest_shape_and_no_forbidden_fragments() -> None:
    manifest = load_manifest()
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    assert manifest["schema_version"] == "semantic-descriptor-inputs/v1"
    assert manifest["representation_kind"] == "safe_semantic_descriptor_v1"
    assert manifest["query_descriptor_count"] == 10
    assert manifest["candidate_descriptor_count"] == 10
    assert manifest["redaction"]["answer_fields_excluded_from_scoring_inputs"] is True
    for forbidden in (
        "raw_legal_text",
        "query_text\"",
        "provider_payload",
        "embedding_vector",
        "expected_label",
        "expected_candidate_ids",
        "expected_rejected_candidate_ids",
        ".gsd/exec",
        "/root/",
    ):
        assert forbidden not in serialized


def test_fails_closed_for_unknown_descriptor_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptors"]["free_text_summary"] = "blocked"
    manifest["query_descriptors"][0]["descriptor_tokens"].append("free_text_summary:blocked")
    expect_error(write_manifest(tmp_path, manifest), "descriptor field mismatch")


def test_fails_closed_for_free_text_descriptor_value(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptors"]["topic_class"] = "закупки контракт"
    manifest["query_descriptors"][0]["descriptor_tokens"] = [
        token if not token.startswith("topic_class:") else "topic_class:закупки контракт"
        for token in manifest["query_descriptors"][0]["descriptor_tokens"]
    ]
    expect_error(write_manifest(tmp_path, manifest), "unsafe descriptor enum grammar")


def test_fails_closed_for_raw_text_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["raw_text"] = "blocked"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_vector_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["vector"] = [0.1, 0.2]
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_provider_payload_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["provider_payload"] = {"blocked": True}
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_expected_answer_leakage(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["expected_label"] = "relevant"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_rank_leakage(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["rank"] = 1
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_generated_prose_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["generated_answer_prose"] = "blocked"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_generated_query_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["generated_cypher"] = "MATCH (n) RETURN n"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_absolute_path(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["source_fixture"] = "/root/law-nexus/fixture.json"
    expect_error(write_manifest(tmp_path, manifest), "unsafe absolute path")


def test_fails_closed_for_gsd_exec_anchor(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["contract"] = ".gsd/exec/example.stdout"
    expect_error(write_manifest(tmp_path, manifest), "unsafe payload fragment")


def test_fails_closed_for_bad_enum_value(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptors"]["query_intent"] = "fixture_expected_answer"
    manifest["query_descriptors"][0]["descriptor_tokens"] = [
        token if not token.startswith("query_intent:") else "query_intent:fixture_expected_answer"
        for token in manifest["query_descriptors"][0]["descriptor_tokens"]
    ]
    expect_error(write_manifest(tmp_path, manifest), "descriptor enum not allowed")


def test_fails_closed_for_token_mismatch(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["descriptor_tokens"][0] = "actor_role:wrong_role"
    expect_error(write_manifest(tmp_path, manifest), "descriptor token mismatch")


def test_fails_closed_for_missing_candidate_coverage(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"] = manifest["candidate_descriptors"][:-1]
    manifest["candidate_descriptor_count"] = len(manifest["candidate_descriptors"])
    expect_error(write_manifest(tmp_path, manifest), "representative descriptor coverage mismatch")


def test_fails_closed_for_bad_source_hash(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["source_fixture_sha256"] = "0" * 64
    expect_error(write_manifest(tmp_path, manifest), "sha256 mismatch")


def test_fails_closed_for_redaction_false(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["redaction"]["raw_vectors_excluded"] = False
    expect_error(write_manifest(tmp_path, manifest), "redaction flags")
