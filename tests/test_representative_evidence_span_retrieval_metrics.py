from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-representative-evidence-span-retrieval-metrics.py"
FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
PROOF = ROOT / "prd/research/ontology_architecture_requirements/representative_evidence_span_retrieval_metrics_proof.json"

EXPECTED_METRICS = {
    "mrr",
    "recall_at_1",
    "recall_at_3",
    "distractor_rejection_rate",
    "stale_rejection_rate",
    "ambiguous_preservation_rate",
    "unsupported_scope_accuracy",
    "no_answer_accuracy",
    "citation_preservation_rate",
    "unsafe_rejection_rate",
    "runtime_boundary_confirmed",
}


def load_module(name: str = "representative_metrics_verifier") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime_file(tmp_path: Path, **overrides: Any) -> Path:
    payload = {
        "runtime_status": "confirmed_runtime",
        "model_id": "deepvk/USER-bge-m3",
        "observed_vector_dimension": 1024,
        "managed_api_used": False,
        "raw_vectors_persisted": False,
        "network_used": False,
    }
    payload.update(overrides)
    path = tmp_path / "runtime.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def fixture_copy(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def test_checked_in_proof_shape() -> None:
    proof = json.loads(PROOF.read_text(encoding="utf-8"))

    assert proof["schema_version"] == "representative-evidence-span-retrieval-metrics-proof/v1"
    assert proof["status"] == "passed"
    assert proof["case_count"] == 10
    assert set(proof["metrics"]) == EXPECTED_METRICS
    assert all(value == 1.0 for value in proof["metrics"].values())
    assert proof["runtime_boundary"]["model_id"] == "deepvk/USER-bge-m3"
    assert proof["runtime_boundary"]["observed_vector_dimension"] == 1024
    assert proof["redaction"]["source_text_excluded"] is True
    assert "Does not validate R035." in proof["non_claims"]


def test_build_report_with_injected_confirmed_runtime(tmp_path: Path) -> None:
    verifier = load_module("representative_metrics_confirmed")

    report = verifier.build_report(FIXTURE, runtime_file(tmp_path), timeout_seconds=30)

    assert report["status"] == "passed"
    assert report["diagnostic_codes"] == ["representative_metrics_verified", "runtime_confirmed"]
    assert all(value == 1.0 for value in report["metrics"].values())


def test_build_report_blocks_unconfirmed_runtime(tmp_path: Path) -> None:
    verifier = load_module("representative_metrics_blocked_runtime")

    report = verifier.build_report(FIXTURE, runtime_file(tmp_path, runtime_status="blocked_environment"), timeout_seconds=30)

    assert report["status"] == "blocked"
    assert "runtime_blocked" in report["diagnostic_codes"]
    assert "runtime_boundary_confirmed" in report["threshold_failures"]


def test_build_report_blocks_managed_api_runtime(tmp_path: Path) -> None:
    verifier = load_module("representative_metrics_managed_api")

    report = verifier.build_report(FIXTURE, runtime_file(tmp_path, managed_api_used=True), timeout_seconds=30)

    assert report["status"] == "blocked"
    assert "managed_api_forbidden" in report["diagnostic_codes"]
    assert report["metrics"]["runtime_boundary_confirmed"] == 0.0


def test_build_report_blocks_raw_vector_persistence(tmp_path: Path) -> None:
    verifier = load_module("representative_metrics_raw_vectors")

    report = verifier.build_report(FIXTURE, runtime_file(tmp_path, raw_vectors_persisted=True), timeout_seconds=30)

    assert report["status"] == "blocked"
    assert "raw_vector_persistence_forbidden" in report["diagnostic_codes"]


def test_build_report_blocks_threshold_mismatch(tmp_path: Path) -> None:
    verifier = load_module("representative_metrics_threshold")
    fixture_path = fixture_copy(tmp_path)
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    for case in fixture["cases"]:
        if case["case_class"] == "positive_with_distractor":
            case["expected_rejected_candidate_ids"] = []
            break
    fixture_path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = verifier.build_report(fixture_path, runtime_file(tmp_path), timeout_seconds=30)

    assert report["status"] == "blocked"
    assert "threshold_mismatch" in report["diagnostic_codes"]
    assert "distractor_rejection_rate" in report["threshold_failures"]


def test_safe_payload_rejects_unsafe_field() -> None:
    verifier = load_module("representative_metrics_unsafe")

    try:
        verifier.assert_safe_payload({"raw_text": "blocked"})
    except verifier.MetricsError as exc:
        assert "unsafe field name" in str(exc)
    else:
        raise AssertionError("expected MetricsError")
