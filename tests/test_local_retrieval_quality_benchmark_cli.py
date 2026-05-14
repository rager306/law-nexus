from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "verify-local-retrieval-quality-benchmark.py"
FIXTURE = ROOT / "prd" / "retrieval" / "fixtures" / "local_retrieval_quality_benchmark.json"

EXPECTED_SUMMARY = {
    "diagnostic_code_inventory": [
        "ambiguous_rejected",
        "model_runtime_available",
        "scoped_no_answer",
        "unsafe_payload_rejected",
    ],
    "fixture_path": "prd/retrieval/fixtures/local_retrieval_quality_benchmark.json",
    "managed_api_used": False,
    "metrics": {
        "ambiguous_rejection_rate": 1.0,
        "mrr": 1.0,
        "no_answer_accuracy": 1.0,
        "recall_at_1": 1.0,
        "recall_at_3": 1.0,
        "unsafe_rejection_rate": 1.0,
    },
    "mismatch_count": 0,
    "model_id": "deepvk/USER-bge-m3",
    "model_status": "available",
    "non_authoritative": True,
    "observed_vector_dimension": 1024,
    "positive_query_count": 2,
    "raw_vectors_persisted": False,
    "schema_version": "local-retrieval-quality-benchmark-proof/v1",
    "threshold_passed": True,
    "total_cases": 6,
}


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "python", str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def write_fixture(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_cli_passes_for_checked_in_fixture() -> None:
    result = run_cli()

    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout) == EXPECTED_SUMMARY


def test_cli_reports_missing_fixture_with_bounded_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    result = run_cli("--fixture", str(missing))

    assert result.returncode == 2
    summary = json.loads(result.stdout)
    assert summary["mismatch_count"] == 1
    assert summary["mismatches"][0]["code"] == "fixture_not_found"
    assert "/root/" not in json.dumps(summary)


def test_cli_rejects_malformed_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")

    result = run_cli("--fixture", str(bad))

    assert result.returncode == 2
    summary = json.loads(result.stdout)
    assert summary["mismatches"][0]["phase"] == "fixture_load"
    assert summary["mismatches"][0]["code"] == "malformed_fixture_json"


def test_cli_detects_threshold_mismatch(tmp_path: Path) -> None:
    fixture = load_fixture()
    fixture["thresholds"]["mrr"] = 1.1
    mutated = tmp_path / "threshold-mismatch.json"
    write_fixture(mutated, fixture)

    result = run_cli("--fixture", str(mutated))

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["threshold_passed"] is False
    assert any(
        mismatch["code"] == "threshold_mismatch"
        and mismatch["metric"] == "mrr"
        and mismatch["actual"] == 1.0
        for mismatch in summary["mismatches"]
    )


def test_cli_detects_case_metric_mismatch(tmp_path: Path) -> None:
    fixture = load_fixture()
    case = next(row for row in fixture["cases"] if row["case_class"] == "positive_exact_relevance")
    case["candidates"][0]["rank"] = 2
    mutated = tmp_path / "metric-mismatch.json"
    write_fixture(mutated, fixture)

    result = run_cli("--fixture", str(mutated))

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert any(
        mismatch["code"] == "metric_mismatch"
        and mismatch["case_id"] == "CASE-M015-POSITIVE-EXACT-RELEVANCE"
        and mismatch["actual"]["mrr"] == 0.5
        for mismatch in summary["mismatches"]
    )


def test_cli_detects_unsafe_diagnostic_fields(tmp_path: Path) -> None:
    fixture = load_fixture()
    case = next(row for row in fixture["cases"] if row["case_class"] == "scoped_no_answer_quality")
    case["diagnostics"][0]["raw_text"] = "unsafe diagnostic payload"
    mutated = tmp_path / "unsafe-diagnostic.json"
    write_fixture(mutated, fixture)

    result = run_cli("--fixture", str(mutated))

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert any(
        mismatch["code"] == "unsafe_payload_field"
        and "raw_text" in mismatch["field_path"]
        for mismatch in summary["mismatches"]
    )
    assert any(
        mismatch["code"] == "unsafe_diagnostic_field"
        and "raw_text" in mismatch["actual_fields"]
        for mismatch in summary["mismatches"]
    )


def test_cli_detects_raw_vector_or_managed_api_boundary_failure(tmp_path: Path) -> None:
    fixture = load_fixture()
    fixture["model_boundary"]["managed_api_used"] = True
    fixture["model_boundary"]["raw_vectors_persisted"] = True
    mutated = tmp_path / "unsafe-model-boundary.json"
    write_fixture(mutated, fixture)

    result = run_cli("--fixture", str(mutated))

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert any(mismatch["field_path"] == "model_boundary.managed_api_used" for mismatch in summary["mismatches"])
    assert any(mismatch["field_path"] == "model_boundary.raw_vectors_persisted" for mismatch in summary["mismatches"])


def test_cli_detects_forbidden_text_payload(tmp_path: Path) -> None:
    fixture = load_fixture()
    fixture["cases"][0]["query"]["debug_note"] = "provider response body"
    mutated = tmp_path / "unsafe-text.json"
    write_fixture(mutated, fixture)

    result = run_cli("--fixture", str(mutated))

    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert any(mismatch["code"] == "unsafe_text_payload" for mismatch in summary["mismatches"])
