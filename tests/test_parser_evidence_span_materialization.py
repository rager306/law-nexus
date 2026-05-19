from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build-parser-evidence-span-materialization.py"
VERIFIER = ROOT / "scripts/verify-parser-evidence-span-materialization.py"
ARTIFACT = ROOT / "prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json"


def load_verifier(name: str = "materialization_verifier") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_builder(name: str = "materialization_builder") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_artifact() -> dict[str, Any]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def write_artifact(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "materialization.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def expect_error(path: Path, text: str) -> None:
    verifier = load_verifier(f"materialization_{text[:8].replace(' ', '_')}")
    try:
        verifier.verify_artifact(path)
    except verifier.MaterializationVerificationError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("expected MaterializationVerificationError")


def test_checked_in_artifact_passes() -> None:
    verifier = load_verifier("materialization_happy")

    result = verifier.verify_artifact(ARTIFACT)

    assert result["status"] == "ok"
    assert result["artifact_status"] == "ok"
    assert result["representation_kind"] == "safe_materialized_evidence_candidates_v1"
    assert result["materialized_candidate_count"] == 6
    assert result["safe_source_anchors_verified"] is True
    assert result["diagnostic_codes"] == ["parser_evidence_span_materialization_verified"]


def test_cli_emits_compact_ok_json() -> None:
    completed = subprocess.run([sys.executable, str(VERIFIER)], cwd=ROOT, check=False, text=True, capture_output=True)

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["materialized_candidate_count"] == 6


def test_artifact_shape_and_no_forbidden_fragments() -> None:
    artifact = load_artifact()
    serialized = json.dumps(artifact, ensure_ascii=False, sort_keys=True)

    assert artifact["schema_version"] == "parser-evidence-span-materialization/v1"
    assert artifact["representation_kind"] == "safe_materialized_evidence_candidates_v1"
    assert artifact["status"] == "ok"
    assert artifact["redaction"]["source_text_excluded"] is True
    assert artifact["redaction"]["external_payloads_excluded"] is True
    assert artifact["r035_non_validation_declared"] is True
    assert artifact["r038_review_required"] is True
    for forbidden in ("Федеральный закон", "Статья ", "raw_legal_text", "source_excerpt", "provider_payload", "expected_candidate_ids", ".gsd/exec", "/root/"):
        assert forbidden not in serialized


def test_fails_closed_for_raw_text_field(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["materialized_candidates"][0]["raw_text"] = "blocked"
    expect_error(write_artifact(tmp_path, artifact), "unsafe field name")


def test_fails_closed_for_forbidden_fragment(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["materialized_candidates"][0]["source_anchor_id"] = "SRC-M027-001-Федеральный закон"
    expect_error(write_artifact(tmp_path, artifact), "unsafe payload fragment")


def test_fails_closed_for_absolute_path(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["source_document_ref"] = "/root/law-nexus/law-source/garant/44-fz.odt"
    expect_error(write_artifact(tmp_path, artifact), "unsafe absolute path")


def test_fails_closed_for_gsd_exec_anchor(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["parser_evidence_summary"]["debug_ref"] = ".gsd/exec/example.stdout"
    expect_error(write_artifact(tmp_path, artifact), "unsafe payload fragment")


def test_fails_closed_for_bad_source_hash(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["source_document_sha256"] = "sha256:" + "0" * 64
    expect_error(write_artifact(tmp_path, artifact), "source document sha mismatch")


def test_fails_closed_for_invalid_enum(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["materialized_candidates"][0]["candidate_kind"] = "legal_answer"
    expect_error(write_artifact(tmp_path, artifact), "candidate_kind enum mismatch")


def test_fails_closed_for_invalid_blocked_reason(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["status"] = "blocked"
    artifact["blocked_reason"] = "made_up_reason"
    artifact["materialized_candidate_count"] = 0
    artifact["materialized_candidates"] = []
    expect_error(write_artifact(tmp_path, artifact), "blocked reason mismatch")


def test_blocked_payload_shape_verifies(tmp_path: Path) -> None:
    builder = load_builder("materialization_builder_blocked")
    verifier = load_verifier("materialization_verifier_blocked")
    payload = builder.blocked_payload("source_unavailable")
    path = write_artifact(tmp_path, payload)

    result = verifier.verify_artifact(path)

    assert result["status"] == "ok"
    assert result["artifact_status"] == "blocked"
    assert result["blocked_reason"] == "source_unavailable"
    assert result["materialized_candidate_count"] == 0


def test_fails_closed_for_false_redaction(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["redaction"]["source_text_excluded"] = False
    expect_error(write_artifact(tmp_path, artifact), "redaction flags mismatch")


def test_fails_closed_for_missing_lifecycle_marker(tmp_path: Path) -> None:
    artifact = load_artifact()
    artifact["r035_non_validation_declared"] = False
    expect_error(write_artifact(tmp_path, artifact), "lifecycle boundary marker missing")
