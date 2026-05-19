from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/verify-evidence-span-local-retrieval-metrics.py"
FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json"
PROOF = ROOT / "prd/research/ontology_architecture_requirements/evidence_span_local_retrieval_metrics_proof.json"

FORBIDDEN_SNIPPETS = {
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
}


def load_module(name: str = "s05_metrics") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, CLI)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def confirmed_runtime_payload() -> dict[str, Any]:
    return {
        "schema_version": "local-retrieval-runtime-boundary/v1",
        "model_id": "deepvk/USER-bge-m3",
        "runtime_status": "confirmed_runtime",
        "failure_class": "none",
        "managed_api_used": False,
        "raw_vectors_persisted": False,
        "network_used": False,
        "vector_dimension": 1024,
    }


def blocked_runtime_payload() -> dict[str, Any]:
    payload = confirmed_runtime_payload()
    payload.update({"runtime_status": "blocked_model_unavailable", "failure_class": "model_unavailable", "vector_dimension": None})
    return payload


def run_cli(tmp_path: Path, runtime_payload: dict[str, Any], *extra: str) -> subprocess.CompletedProcess[str]:
    runtime_path = tmp_path / "runtime.json"
    write_json(runtime_path, runtime_payload)
    return subprocess.run(
        ["uv", "run", "python", str(CLI), "--runtime-json", str(runtime_path), "--no-write", *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_checked_in_proof_is_safe_and_passing() -> None:
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    serialized = json.dumps(proof, ensure_ascii=False, sort_keys=True)

    assert proof["schema_version"] == "evidence-span-local-retrieval-metrics-proof/v1"
    assert proof["threshold_passed"] is True
    assert proof["mismatch_count"] == 0
    assert proof["runtime_boundary"]["runtime_status"] == "confirmed_runtime"
    assert proof["runtime_boundary"]["observed_vector_dimension"] == 1024
    assert proof["runtime_boundary"]["managed_api_used"] is False
    assert proof["runtime_boundary"]["raw_vectors_persisted"] is False
    assert proof["metrics"] == {
        "ambiguous_rejection_rate": 1.0,
        "mrr": 1.0,
        "no_answer_accuracy": 1.0,
        "recall_at_1": 1.0,
        "recall_at_3": 1.0,
        "runtime_boundary_confirmed": 1.0,
        "stale_rejection_rate": 1.0,
        "unsupported_scope_accuracy": 1.0,
    }
    for snippet in FORBIDDEN_SNIPPETS:
        assert snippet not in serialized


def test_cli_passes_with_injected_confirmed_runtime(tmp_path: Path) -> None:
    result = run_cli(tmp_path, confirmed_runtime_payload())

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["threshold_passed"] is True
    assert payload["runtime_boundary"]["confirmed"] is True
    assert payload["diagnostic_codes"] == [
        "ambiguous_candidate_set",
        "runtime_confirmed",
        "scoped_no_answer",
        "stale_temporal_candidate",
        "unsupported_scope",
    ]


def test_cli_reports_blocked_runtime_without_fallback(tmp_path: Path) -> None:
    result = run_cli(tmp_path, blocked_runtime_payload())

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["threshold_passed"] is False
    assert payload["runtime_boundary"]["confirmed"] is False
    assert payload["runtime_boundary"]["runtime_status"] == "blocked_model_unavailable"
    assert "runtime_blocked" in payload["diagnostic_codes"]
    assert any(mismatch["metric"] == "runtime_boundary_confirmed" for mismatch in payload["mismatches"])


def test_compute_metrics_detects_threshold_mismatch() -> None:
    module = load_module("s05_threshold")
    fixture = load_fixture()
    case = next(row for row in fixture["cases"] if row["case_class"] == "positive_evidence_span")
    case["candidates"][0]["expected_label"] = "stale"

    metrics, diagnostics, mismatches = module.compute_metrics(fixture, {"confirmed": True, "diagnostic_codes": ["runtime_confirmed"]})

    assert metrics["mrr"] == 0.5
    assert metrics["recall_at_1"] == 0.5
    assert "threshold_mismatch" in diagnostics
    assert {mismatch["metric"] for mismatch in mismatches} >= {"mrr", "recall_at_1"}


def test_safety_rejects_unsafe_payload_field() -> None:
    module = load_module("s05_unsafe")
    fixture = load_fixture()
    fixture["raw_text"] = "blocked"

    try:
        module.check_no_unsafe_payload(fixture)
    except module.MetricsError as exc:
        assert "unsafe field name" in str(exc)
    else:
        raise AssertionError("expected MetricsError")


def test_runtime_boundary_rejects_managed_or_vector_persistence(tmp_path: Path) -> None:
    module = load_module("s05_runtime_policy")
    runtime = confirmed_runtime_payload()
    runtime["managed_api_used"] = True
    runtime["raw_vectors_persisted"] = True
    runtime_path = tmp_path / "runtime.json"
    write_json(runtime_path, runtime)

    boundary = module.runtime_boundary(1, runtime_path)

    assert boundary["confirmed"] is False
    assert "managed_api_forbidden" in boundary["diagnostic_codes"]
    assert "raw_vector_persistence_forbidden" in boundary["diagnostic_codes"]
