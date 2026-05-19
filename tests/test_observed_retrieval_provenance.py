from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-observed-retrieval-provenance.py"
FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
QUERY_REGISTRY = ROOT / "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_query_provenance_registry.json"
SOURCE_MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_source_provenance_manifest.json"


def load_module(name: str = "observed_retrieval_provenance_verifier") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(tmp_path: Path, name: str, payload: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_checked_in_provenance_verifier_passes() -> None:
    verifier = load_module("observed_provenance_happy")

    result = verifier.verify(FIXTURE, QUERY_REGISTRY, SOURCE_MANIFEST)

    assert result["status"] == "ok"
    assert result["query_count"] == 10
    assert result["candidate_count"] == 10
    assert result["diagnostic_codes"] == ["query_registry_verified", "source_provenance_verified"]
    assert "does not prove observed retrieval ranking" in result["non_claim_boundary"]


def test_query_registry_shape_and_redaction() -> None:
    registry = load_json(QUERY_REGISTRY)
    serialized = json.dumps(registry, ensure_ascii=False, sort_keys=True)

    assert registry["schema_version"] == "observed-retrieval-query-provenance-registry/v1"
    assert registry["entry_count"] == 10
    assert all(len(entry["query_hash"]) == 64 for entry in registry["entries"])
    assert all(entry["query_hash_field"] == "query_text_sha256" for entry in registry["entries"])
    assert registry["redaction"]["query_text_excluded"] is True
    for forbidden in ("raw_legal_text", "provider_payload", "embedding_vector", ".gsd/exec", "/root/"):
        assert forbidden not in serialized


def test_source_manifest_shape_and_redaction() -> None:
    manifest = load_json(SOURCE_MANIFEST)
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    assert manifest["schema_version"] == "observed-retrieval-source-provenance-manifest/v1"
    assert manifest["candidate_count"] == 10
    assert all(entry["validation_expectations"]["source_case_exists"] for entry in manifest["candidate_entries"])
    assert all(entry["validation_expectations"]["source_records_exist"] for entry in manifest["candidate_entries"])
    assert manifest["redaction"]["source_text_excluded"] is True
    for forbidden in ("raw_legal_text", "provider_payload", "embedding_vector", ".gsd/exec", "/root/"):
        assert forbidden not in serialized


def test_fails_closed_for_unregistered_query_hash(tmp_path: Path) -> None:
    verifier = load_module("observed_provenance_bad_query")
    registry = load_json(QUERY_REGISTRY)
    registry["entries"][0]["query_hash"] = "0" * 64
    registry_path = write_json(tmp_path, "query_registry.json", registry)

    try:
        verifier.verify(FIXTURE, registry_path, SOURCE_MANIFEST)
    except verifier.ProvenanceError as exc:
        assert "query_hash_unregistered" in str(exc)
    else:
        raise AssertionError("expected ProvenanceError")


def test_fails_closed_for_bogus_source_case_id(tmp_path: Path) -> None:
    verifier = load_module("observed_provenance_bad_case")
    manifest = load_json(SOURCE_MANIFEST)
    manifest["candidate_entries"][0]["source_case_id"] = "CASE-M023-BOGUS"
    manifest_path = write_json(tmp_path, "source_manifest.json", manifest)

    try:
        verifier.verify(FIXTURE, QUERY_REGISTRY, manifest_path)
    except verifier.ProvenanceError as exc:
        assert "source_case_id" in str(exc) or "candidate provenance field mismatch" in str(exc)
    else:
        raise AssertionError("expected ProvenanceError")


def test_fails_closed_for_bogus_source_record_id(tmp_path: Path) -> None:
    verifier = load_module("observed_provenance_bad_record")
    manifest = load_json(SOURCE_MANIFEST)
    manifest["candidate_entries"][0]["source_record_ids"] = ["HIER-M023-BOGUS"]
    manifest_path = write_json(tmp_path, "source_manifest.json", manifest)

    try:
        verifier.verify(FIXTURE, QUERY_REGISTRY, manifest_path)
    except verifier.ProvenanceError as exc:
        assert "source_record_ids" in str(exc) or "source_record_id" in str(exc)
    else:
        raise AssertionError("expected ProvenanceError")


def test_fails_closed_for_source_artifact_hash_mismatch(tmp_path: Path) -> None:
    verifier = load_module("observed_provenance_bad_hash")
    manifest = load_json(SOURCE_MANIFEST)
    manifest["source_artifacts"][0]["sha256"] = "0" * 64
    manifest_path = write_json(tmp_path, "source_manifest.json", manifest)

    try:
        verifier.verify(FIXTURE, QUERY_REGISTRY, manifest_path)
    except verifier.ProvenanceError as exc:
        assert "source artifact sha256 mismatch" in str(exc)
    else:
        raise AssertionError("expected ProvenanceError")


def test_fails_closed_for_unsafe_payload_field(tmp_path: Path) -> None:
    verifier = load_module("observed_provenance_unsafe")
    registry = load_json(QUERY_REGISTRY)
    registry["entries"][0]["raw_text"] = "blocked"
    registry_path = write_json(tmp_path, "query_registry.json", registry)

    try:
        verifier.verify(FIXTURE, registry_path, SOURCE_MANIFEST)
    except verifier.ProvenanceError as exc:
        assert "unsafe field name" in str(exc)
    else:
        raise AssertionError("expected ProvenanceError")
