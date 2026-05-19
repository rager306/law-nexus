from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build-materialized-descriptor-inputs.py"
VERIFIER = ROOT / "scripts/verify-materialized-descriptor-inputs.py"
MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_inputs.json"


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_verifier(name: str = "materialized_descriptor_verifier") -> ModuleType:
    return load_module(VERIFIER, name)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "materialized_descriptor_inputs.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def expect_error(path: Path, text: str) -> None:
    verifier = load_verifier(f"verifier_{text[:8].replace(' ', '_')}")
    try:
        verifier.verify_manifest(path)
    except verifier.MaterializedDescriptorInputError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("expected MaterializedDescriptorInputError")


def test_checked_in_manifest_passes() -> None:
    verifier = load_verifier("verifier_happy")

    result = verifier.verify_manifest(MANIFEST)

    assert result["status"] == "ok"
    assert result["representation_kind"] == "safe_materialized_descriptor_v1"
    assert result["query_descriptor_count"] == 6
    assert result["candidate_descriptor_count"] == 6
    assert result["source_materialization_verified"] is True


def test_builder_emits_manifest_with_safe_derivation_fields() -> None:
    builder = load_module(BUILDER, "builder_safe_fields")

    manifest = builder.build_inputs()

    assert manifest["schema_version"] == "materialized-descriptor-inputs/v1"
    assert manifest["representation_kind"] == "safe_materialized_descriptor_v1"
    assert manifest["derivation_fields"] == [
        "candidate_kind",
        "structural_unit_kind",
        "citation_granularity",
        "content_role",
        "temporal_status",
        "materialization_method",
        "source_order_index_bucket",
    ]
    assert manifest["query_descriptor_count"] == 6
    assert manifest["candidate_descriptor_count"] == 6


def test_cli_verifier_emits_compact_json() -> None:
    completed = subprocess.run([sys.executable, str(VERIFIER)], cwd=ROOT, check=False, text=True, capture_output=True)

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["query_descriptor_count"] == 6
    assert payload["candidate_descriptor_count"] == 6


def test_manifest_shape_and_forbidden_fragment_absence() -> None:
    manifest = load_manifest()
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    assert manifest["r035_non_validation_declared"] is True
    assert manifest["r038_review_required"] is True
    assert manifest["redaction"]["source_text_excluded"] is True
    assert manifest["redaction"]["expected_answer_fields_excluded_from_descriptor_inputs"] is True
    for forbidden in ("Федеральный закон", "Статья ", "raw_legal_text", "source_excerpt", "provider_payload", "expected_label", "expected_candidate_ids", ".gsd/exec", "/root/"):
        assert forbidden not in serialized


def test_fails_closed_for_raw_text_field(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["raw_text"] = "blocked"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_expected_candidate_ids(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["expected_candidate_ids"] = ["DESC-CAND-M027-001"]
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_forbidden_raw_text_fragment(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["source_anchor_ref"] = "SRC-M027-001-Федеральный закон"
    expect_error(write_manifest(tmp_path, manifest), "unsafe payload fragment")


def test_fails_closed_for_absolute_path(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["materialization_source"] = "/root/law-nexus/prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json"
    expect_error(write_manifest(tmp_path, manifest), "unsafe absolute path")


def test_fails_closed_for_bad_materialization_hash(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["materialization_source_sha256"] = "sha256:" + "0" * 64
    expect_error(write_manifest(tmp_path, manifest), "materialization source hash mismatch")


def test_fails_closed_for_invalid_enum(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["descriptors"]["content_role"] = "legal_answer"
    manifest["candidate_descriptors"][0]["descriptor_tokens"] = [
        token if not token.startswith("content_role:") else "content_role:legal_answer"
        for token in manifest["candidate_descriptors"][0]["descriptor_tokens"]
    ]
    expect_error(write_manifest(tmp_path, manifest), "descriptor enum not allowed")


def test_fails_closed_for_token_mismatch(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptor_tokens"] = manifest["query_descriptors"][0]["descriptor_tokens"][:-1]
    expect_error(write_manifest(tmp_path, manifest), "descriptor token mismatch")


def test_fails_closed_for_false_redaction(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["redaction"]["source_text_excluded"] = False
    expect_error(write_manifest(tmp_path, manifest), "redaction flags mismatch")


def test_fails_closed_for_non_materialized_source_id(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["materialized_candidate_ref"] = "CAND-M026-001"
    manifest["candidate_descriptors"][0]["source_record_ids"] = ["CAND-M026-001"]
    expect_error(write_manifest(tmp_path, manifest), "unsafe materialized ref")


def test_fails_closed_for_missing_lifecycle_marker(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["r038_review_required"] = False
    expect_error(write_manifest(tmp_path, manifest), "lifecycle boundary marker missing")
