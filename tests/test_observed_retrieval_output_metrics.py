from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-observed-retrieval-output-metrics.py"
OBSERVED = ROOT / "prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_outputs.json"
PROOF = ROOT / "prd/research/ontology_architecture_requirements/observed_retrieval_output_metrics_proof.json"

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


def load_module(name: str = "observed_output_metrics_verifier") -> ModuleType:
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
    return write_json(tmp_path, "runtime.json", payload)


def observed_copy(tmp_path: Path) -> Path:
    return write_json(tmp_path, "observed.json", load_json(OBSERVED))


def test_checked_in_proof_shape() -> None:
    proof = load_json(PROOF)

    assert proof["schema_version"] == "observed-retrieval-output-metrics-proof/v1"
    assert proof["status"] == "passed"
    assert proof["retrieval_mode"] == "safe_id_provenance_rule_retrieval_v1"
    assert set(proof["metrics"]) == EXPECTED_METRICS
    assert all(value == 1.0 for value in proof["metrics"].values())
    assert "metric_comparison_verified" in proof["diagnostic_codes"]
    assert "Does not prove model semantic retrieval quality; observed outputs are safe-ID rule retrieval outputs." in proof["non_claims"]


def test_build_report_with_injected_confirmed_runtime(tmp_path: Path) -> None:
    verifier = load_module("observed_output_confirmed")

    report = verifier.build_report(OBSERVED, runtime_file(tmp_path), timeout_seconds=30)

    assert report["status"] == "passed"
    assert report["metrics"]["runtime_boundary_confirmed"] == 1.0
    assert "query_registry_verified" in report["diagnostic_codes"]
    assert "source_provenance_verified" in report["diagnostic_codes"]


def test_fails_closed_when_observed_output_missing(tmp_path: Path) -> None:
    verifier = load_module("observed_output_missing")

    try:
        verifier.build_report(tmp_path / "missing.json", runtime_file(tmp_path), timeout_seconds=30)
    except verifier.ObservedMetricsError as exc:
        assert "observed_output_missing" in str(exc)
    else:
        raise AssertionError("expected ObservedMetricsError")


def test_fails_closed_for_forbidden_expected_fields(tmp_path: Path) -> None:
    verifier = load_module("observed_output_expected_fields")
    observed = load_json(OBSERVED)
    observed["entries"][0]["expected_candidate_ids"] = ["CAND-M023-SELF-CONFIRMING"]
    observed_path = write_json(tmp_path, "observed.json", observed)

    try:
        verifier.build_report(observed_path, runtime_file(tmp_path), timeout_seconds=30)
    except verifier.ObservedMetricsError as exc:
        assert "observed_output_self_confirming" in str(exc)
    else:
        raise AssertionError("expected ObservedMetricsError")


def test_fails_closed_for_missing_retrieval_mode(tmp_path: Path) -> None:
    verifier = load_module("observed_output_no_mode")
    observed = load_json(OBSERVED)
    observed["entries"][0]["retrieval_mode"] = "fixture_expected_copy"
    observed_path = write_json(tmp_path, "observed.json", observed)

    try:
        verifier.build_report(observed_path, runtime_file(tmp_path), timeout_seconds=30)
    except verifier.ObservedMetricsError as exc:
        assert "retrieval mode mismatch" in str(exc)
    else:
        raise AssertionError("expected ObservedMetricsError")


def test_blocks_inconsistent_positive_ranking(tmp_path: Path) -> None:
    verifier = load_module("observed_output_bad_ranking")
    observed = load_json(OBSERVED)
    for entry in observed["entries"]:
        if entry["case_id"] == "CASE-M022-001-POSITIVE-EVIDENCE-SPAN":
            entry["observed_ranked_candidate_ids"] = []
            break
    observed_path = write_json(tmp_path, "observed.json", observed)

    try:
        verifier.build_report(observed_path, runtime_file(tmp_path), timeout_seconds=30)
    except verifier.ObservedMetricsError as exc:
        assert "observed ranked candidates missing" in str(exc)
    else:
        raise AssertionError("expected ObservedMetricsError")


def test_blocks_inconsistent_diagnostic_metric(tmp_path: Path) -> None:
    verifier = load_module("observed_output_bad_diagnostic")
    observed = load_json(OBSERVED)
    for entry in observed["entries"]:
        if entry["case_id"] == "CASE-M022-006-UNSUPPORTED-SCOPE":
            entry["observed_diagnostic_codes"] = []
            break
    observed_path = write_json(tmp_path, "observed.json", observed)

    report = verifier.build_report(observed_path, runtime_file(tmp_path), timeout_seconds=30)

    assert report["status"] == "blocked"
    assert "unsupported_scope_accuracy" in report["threshold_failures"]
    assert "metric_mismatch" in report["diagnostic_codes"]


def test_blocks_unconfirmed_runtime(tmp_path: Path) -> None:
    verifier = load_module("observed_output_blocked_runtime")

    report = verifier.build_report(OBSERVED, runtime_file(tmp_path, runtime_status="blocked_environment"), timeout_seconds=30)

    assert report["status"] == "blocked"
    assert "runtime_boundary_confirmed" in report["threshold_failures"]
    assert "runtime_blocked" in report["diagnostic_codes"]


def test_fails_closed_for_unsafe_payload_field(tmp_path: Path) -> None:
    verifier = load_module("observed_output_unsafe")
    observed = load_json(OBSERVED)
    observed["entries"][0]["raw_text"] = "blocked"
    observed_path = write_json(tmp_path, "observed.json", observed)

    try:
        verifier.build_report(observed_path, runtime_file(tmp_path), timeout_seconds=30)
    except verifier.ObservedMetricsError as exc:
        assert "unsafe field name" in str(exc)
    else:
        raise AssertionError("expected ObservedMetricsError")
