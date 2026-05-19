from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-held-out-semantic-descriptor-inputs.py"
MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json"


def load_module(name: str = "held_out_descriptor_input_verifier") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "held_out_descriptor_manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def expect_error(path: Path, text: str) -> None:
    verifier = load_module(f"held_out_descriptor_{text[:8].replace(' ', '_')}")
    try:
        verifier.verify_manifest(path)
    except verifier.HeldOutDescriptorInputError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("expected HeldOutDescriptorInputError")


def test_checked_in_manifest_passes() -> None:
    verifier = load_module("held_out_descriptor_happy")

    result = verifier.verify_manifest(MANIFEST)

    assert result["status"] == "ok"
    assert result["representation_kind"] == "safe_semantic_descriptor_v1"
    assert result["query_descriptor_count"] == 5
    assert result["candidate_descriptor_count"] == 10
    assert result["held_out_case_independence_required"] is True
    assert result["diagnostic_codes"] == ["held_out_semantic_descriptors_verified"]
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

    assert manifest["schema_version"] == "held-out-semantic-descriptor-inputs/v1"
    assert manifest["representation_kind"] == "safe_semantic_descriptor_v1"
    assert manifest["query_descriptor_count"] == 5
    assert manifest["candidate_descriptor_count"] == 10
    assert manifest["held_out_case_independence_required"] is True
    assert manifest["m025_design_case_reuse_forbidden"] is True
    assert manifest["m022_acceptance_case_reuse_forbidden"] is True
    assert manifest["redaction"]["external_payloads_excluded"] is True
    for forbidden in (
        "CASE-M022-",
        "QUERY-M022-",
        "CAND-M022-",
        "DESCQ-M025-",
        "DESCC-M025-",
        "raw_legal_text",
        "query_text\"",
        "provider_payloads_excluded",
        "embedding_vector",
        "expected_label",
        "expected_candidate_ids",
        ".gsd/exec",
        "/root/",
    ):
        assert forbidden not in serialized


def test_fails_closed_for_m022_case_reuse(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["case_id"] = "CASE-M022-001-POSITIVE-EVIDENCE-SPAN"
    expect_error(write_manifest(tmp_path, manifest), "forbidden acceptance id reuse")


def test_fails_closed_for_m025_descriptor_reuse(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["descriptor_input_id"] = "DESCC-M025-001-01"
    expect_error(write_manifest(tmp_path, manifest), "forbidden acceptance id reuse")


def test_fails_closed_for_expected_answer_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["expected_label"] = "relevant"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_selection_reason_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["selection_reason"] = "blocked"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_rank_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["rank"] = 1
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_raw_text_fragment(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptor_tokens"].append("raw_legal_text:blocked")
    expect_error(write_manifest(tmp_path, manifest), "unsafe payload fragment")


def test_fails_closed_for_free_text_descriptor_value(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptors"]["topic_class"] = "закупки контракт"
    manifest["query_descriptors"][0]["descriptor_tokens"] = [
        token if not token.startswith("topic_class:") else "topic_class:закупки контракт"
        for token in manifest["query_descriptors"][0]["descriptor_tokens"]
    ]
    expect_error(write_manifest(tmp_path, manifest), "unsafe descriptor enum grammar")


def test_fails_closed_for_vector_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["vector"] = [0.1, 0.2]
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_absolute_path(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["contract"] = "/root/law-nexus/contract.md"
    expect_error(write_manifest(tmp_path, manifest), "unsafe absolute path")


def test_fails_closed_for_unsafe_durable_vocabulary(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["redaction"]["provider_payloads_excluded"] = True
    expect_error(write_manifest(tmp_path, manifest), "unsafe payload fragment")


def test_fails_closed_for_redaction_false(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["redaction"]["raw_vectors_excluded"] = False
    expect_error(write_manifest(tmp_path, manifest), "redaction flags mismatch")


def test_fails_closed_for_bad_contract_hash(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["contract_sha256"] = "0" * 64
    expect_error(write_manifest(tmp_path, manifest), "sha256 mismatch")
