from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build-source-record-cardinality-signal-inputs.py"
VERIFIER = ROOT / "scripts/verify-source-record-cardinality-signal-inputs.py"
MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/source_record_cardinality_signal_inputs.json"


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_verifier(name: str = "cardinality_signal_verifier") -> ModuleType:
    return load_module(VERIFIER, name)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "source_record_cardinality_signal_inputs.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def expect_error(path: Path, text: str) -> None:
    verifier = load_verifier(f"cardinality_{text[:8].replace(' ', '_')}")
    try:
        verifier.verify_manifest(path)
    except verifier.SourceRecordCardinalityInputError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("expected SourceRecordCardinalityInputError")


def test_checked_in_manifest_passes() -> None:
    verifier = load_verifier("cardinality_happy")

    result = verifier.verify_manifest(MANIFEST)

    assert result["status"] == "ok"
    assert result["representation_kind"] == "safe_materialized_descriptor_with_source_record_cardinality_v1"
    assert result["selected_signal"] == "safe_source_record_cardinality_bucket"
    assert result["forbidden_prior_signals"] == ["safe_anchor_family_bucket", "safe_source_order_neighborhood_bucket"]
    assert result["query_descriptor_count"] == 6
    assert result["candidate_descriptor_count"] == 6
    assert result["cardinality_distribution"] == {"source_record_cardinality_single": 12}
    assert result["constant_signal_risk"] is True


def test_builder_emits_exactly_one_cardinality_signal() -> None:
    builder = load_module(BUILDER, "cardinality_signal_builder")

    manifest = builder.build_inputs()

    assert manifest["selected_signal"] == "safe_source_record_cardinality_bucket"
    assert set(manifest["forbidden_prior_signals"]) == {"safe_source_order_neighborhood_bucket", "safe_anchor_family_bucket"}
    assert manifest["added_descriptor_fields"] == ["safe_source_record_cardinality_bucket"]
    assert manifest["single_signal_change_only"] is True
    assert set(manifest["enhanced_derivation_fields"]) == set(manifest["base_derivation_fields"]) | {"safe_source_record_cardinality_bucket"}
    assert manifest["signal_derivation_summary"]["allowed_inputs"] == ["materialized_candidate_ref", "source_record_ids", "source_anchor_sha256"]
    assert manifest["signal_derivation_summary"]["source_order_index_used"] is False
    assert manifest["signal_derivation_summary"]["prior_signals_used"] is False
    assert manifest["signal_derivation_summary"]["constant_signal_risk"] is True
    assert manifest["query_descriptor_count"] == 6
    assert manifest["candidate_descriptor_count"] == 6


def test_cli_verifier_emits_compact_json() -> None:
    completed = subprocess.run([sys.executable, str(VERIFIER)], cwd=ROOT, check=False, text=True, capture_output=True)

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["selected_signal"] == "safe_source_record_cardinality_bucket"
    assert payload["constant_signal_risk"] is True


def test_manifest_shape_and_forbidden_fragment_absence() -> None:
    manifest = load_manifest()
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True)

    assert manifest["m027_baseline_metrics"] == {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0}
    assert manifest["m028_baseline_metrics"] == {"mrr": 0.916667, "recall_at_1": 0.833333, "recall_at_3": 1.0, "runtime_boundary_confirmed": 1.0}
    assert manifest["m029_baseline_metrics"] == {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0}
    assert manifest["r035_non_validation_declared"] is True
    assert manifest["r038_review_required"] is True
    assert manifest["redaction"]["source_text_excluded"] is True
    for forbidden in ("Федеральный закон", "Статья ", "raw_legal_text", "source_excerpt", "provider_payload", "expected_label", "expected_candidate_ids", ".gsd/exec", "/root/"):
        assert forbidden not in serialized
    for item in manifest["query_descriptors"] + manifest["candidate_descriptors"]:
        assert "safe_source_order_neighborhood_bucket" not in item["descriptors"]
        assert "safe_anchor_family_bucket" not in item["descriptors"]
        assert "source_order_index" not in item


def test_fails_closed_for_reused_m028_signal(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptors"]["safe_source_order_neighborhood_bucket"] = "source_order_neighbor_first"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_reused_m029_signal(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptors"]["safe_anchor_family_bucket"] = "source_anchor_family_article"
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_source_order_index_leakage(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["source_order_index"] = 1
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_expected_candidate_ids(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["expected_candidate_ids"] = ["DESC-CAND-M027-001"]
    expect_error(write_manifest(tmp_path, manifest), "unsafe field name")


def test_fails_closed_for_raw_text_fragment(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["source_anchor_ref"] = "SRC-M027-001-Федеральный закон"
    expect_error(write_manifest(tmp_path, manifest), "unsafe payload fragment")


def test_fails_closed_for_invalid_signal_enum(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["candidate_descriptors"][0]["descriptors"]["safe_source_record_cardinality_bucket"] = "label_derived_bucket"
    manifest["candidate_descriptors"][0]["selected_signal_value"] = "label_derived_bucket"
    manifest["candidate_descriptors"][0]["descriptor_tokens"] = [
        token if not token.startswith("safe_source_record_cardinality_bucket:") else "safe_source_record_cardinality_bucket:label_derived_bucket"
        for token in manifest["candidate_descriptors"][0]["descriptor_tokens"]
    ]
    expect_error(write_manifest(tmp_path, manifest), "descriptor enum not allowed")


def test_fails_closed_for_token_mismatch(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["descriptor_tokens"] = manifest["query_descriptors"][0]["descriptor_tokens"][:-1]
    expect_error(write_manifest(tmp_path, manifest), "descriptor token mismatch")


def test_fails_closed_for_cardinality_derivation_mismatch(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["source_record_cardinality"] = 2
    expect_error(write_manifest(tmp_path, manifest), "cardinality derivation mismatch")


def test_fails_closed_for_query_candidate_cardinality_mismatch(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["query_descriptors"][0]["source_record_cardinality"] = 0
    manifest["query_descriptors"][0]["descriptors"]["safe_source_record_cardinality_bucket"] = "source_record_cardinality_unknown"
    manifest["query_descriptors"][0]["selected_signal_value"] = "source_record_cardinality_unknown"
    manifest["query_descriptors"][0]["descriptor_tokens"] = [
        token if not token.startswith("safe_source_record_cardinality_bucket:") else "safe_source_record_cardinality_bucket:source_record_cardinality_unknown"
        for token in manifest["query_descriptors"][0]["descriptor_tokens"]
    ]
    expect_error(write_manifest(tmp_path, manifest), "query cardinality derivation mismatch")


def test_fails_closed_for_base_source_hash_mismatch(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["base_descriptor_inputs_sha256"] = "sha256:" + "0" * 64
    expect_error(write_manifest(tmp_path, manifest), "base descriptor source hash mismatch")


def test_fails_closed_for_false_redaction(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["redaction"]["source_text_excluded"] = False
    expect_error(write_manifest(tmp_path, manifest), "redaction flags mismatch")


def test_fails_closed_for_missing_lifecycle_marker(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["r038_review_required"] = False
    expect_error(write_manifest(tmp_path, manifest), "lifecycle boundary marker missing")


def test_fails_closed_for_m027_baseline_change(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["m027_baseline_metrics"]["mrr"] = 1.0
    expect_error(write_manifest(tmp_path, manifest), "M027 baseline mismatch")


def test_fails_closed_for_m028_baseline_change(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["m028_baseline_metrics"]["mrr"] = 1.0
    expect_error(write_manifest(tmp_path, manifest), "M028 baseline mismatch")


def test_fails_closed_for_m029_baseline_change(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["m029_baseline_metrics"]["mrr"] = 1.0
    expect_error(write_manifest(tmp_path, manifest), "M029 baseline mismatch")


def test_fails_closed_for_constant_signal_risk_mismatch(tmp_path: Path) -> None:
    manifest = load_manifest()
    manifest["signal_derivation_summary"]["constant_signal_risk"] = False
    expect_error(write_manifest(tmp_path, manifest), "constant signal risk mismatch")
