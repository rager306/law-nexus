from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/verify-representative-retrieval-runtime-benchmark.py"
MANIFEST = ROOT / "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json"


def confirmed_runtime() -> dict[str, Any]:
    return {
        "schema_version": "local-retrieval-runtime-boundary/v1",
        "runtime_status": "confirmed_runtime",
        "failure_class": "none",
        "diagnostic_codes": [],
        "model_id": "deepvk/USER-bge-m3",
        "execution_mode": "local_open_weight",
        "vector_dimension": 1024,
        "expected_vector_dimension": 1024,
        "managed_api_used": False,
        "giga_chat_used": False,
        "network_used": False,
        "source_artifacts": ["scripts/check-local-retrieval-runtime.py"],
    }


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def run_cli(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]:
    report = tmp_path / "proof.md"
    completed = subprocess.run(
        [sys.executable, str(CLI), "--report", str(report), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = None
    if completed.stdout.strip():
        payload = json.loads(completed.stdout)
    return completed, payload


def test_pass_emits_one_safe_json_object_and_report(tmp_path: Path) -> None:
    runtime_path = write_json(tmp_path / "runtime.json", confirmed_runtime())
    manifest_path = write_json(tmp_path / "manifest.json", load_manifest())

    completed, payload = run_cli(
        tmp_path,
        "--runtime-summary",
        str(runtime_path),
        "--manifest",
        str(manifest_path),
    )

    assert completed.returncode == 0, completed.stderr
    assert payload is not None
    assert completed.stdout.count("\n") == 1
    assert payload["benchmark_status"] == "metrics_confirmed"
    assert payload["failure_class"] == "none"
    assert payload["diagnostic_codes"] == []
    assert payload["runtime_boundary_confirmed"] is True
    assert all(payload["metrics"][metric] == 1.0 for metric in payload["thresholds"] if metric != "runtime_boundary_confirmed")
    assert payload["metrics"]["runtime_boundary_confirmed"] is True
    assert all(value is False for value in payload["redaction"].values())
    assert payload["managed_api_used"] is False
    assert payload["giga_chat_used"] is False
    assert payload["network_used"] is False
    assert payload["gate"] == {"gate_id": "GATE-G011", "status": "open", "claim": "gate remains open"}
    assert "QRL-M016-001" in payload["metric_inputs"]["query_label_ids"]
    assert (tmp_path / "proof.md").exists()


def test_blocked_runtime_summary_exits_nonzero_without_successful_metric_claim(tmp_path: Path) -> None:
    runtime = confirmed_runtime()
    runtime["runtime_status"] = "blocked_model_unavailable"
    runtime["failure_class"] = "model_unavailable"
    runtime["diagnostic_codes"] = ["LRR_MODEL_CACHE_MISSING"]
    runtime.pop("vector_dimension")
    runtime_path = write_json(tmp_path / "runtime.json", runtime)

    completed, payload = run_cli(tmp_path, "--runtime-summary", str(runtime_path))

    assert completed.returncode == 1
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_runtime"
    assert payload["failure_class"] == "runtime_boundary"
    assert payload["thresholds"]["runtime_boundary_confirmed"] == 1.0
    assert payload["metrics"]["runtime_boundary_confirmed"] is False
    assert "RRB_RUNTIME_NOT_CONFIRMED" in payload["diagnostic_codes"]


def test_allow_runtime_blocker_relaxes_exit_only(tmp_path: Path) -> None:
    runtime = confirmed_runtime()
    runtime["runtime_status"] = "blocked_environment"
    runtime["diagnostic_codes"] = ["LRR_DEPENDENCY_MISSING"]
    runtime_path = write_json(tmp_path / "runtime.json", runtime)

    completed, payload = run_cli(tmp_path, "--runtime-summary", str(runtime_path), "--allow-runtime-blocker")

    assert completed.returncode == 0
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_runtime"
    assert payload["runtime_boundary_confirmed"] is False


def test_malformed_runtime_json_is_runtime_blocker(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime.json"
    runtime_path.write_text("{not-json", encoding="utf-8")

    completed, payload = run_cli(tmp_path, "--runtime-summary", str(runtime_path))

    assert completed.returncode == 1
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_runtime"
    assert payload["failure_class"] == "runtime_boundary"
    assert payload["diagnostic_codes"] == ["RRB_RUNTIME_DIAGNOSTIC_MALFORMED"]


def test_missing_manifest_is_fixture_blocker(tmp_path: Path) -> None:
    runtime_path = write_json(tmp_path / "runtime.json", confirmed_runtime())

    completed, payload = run_cli(
        tmp_path,
        "--runtime-summary",
        str(runtime_path),
        "--manifest",
        str(tmp_path / "missing.json"),
    )

    assert completed.returncode == 1
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_manifest"
    assert payload["failure_class"] == "manifest_input"
    assert payload["diagnostic_codes"] == ["RRB_MANIFEST_MISSING"]


def test_malformed_manifest_json_is_fixture_blocker(tmp_path: Path) -> None:
    runtime_path = write_json(tmp_path / "runtime.json", confirmed_runtime())
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{not-json", encoding="utf-8")

    completed, payload = run_cli(
        tmp_path,
        "--runtime-summary",
        str(runtime_path),
        "--manifest",
        str(manifest_path),
    )

    assert completed.returncode == 1
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_manifest"
    assert payload["diagnostic_codes"] == ["RRB_MANIFEST_MALFORMED"]


def test_unsafe_raw_payload_field_is_policy_failure(tmp_path: Path) -> None:
    runtime_path = write_json(tmp_path / "runtime.json", confirmed_runtime())
    manifest = load_manifest()
    manifest["candidate_references"][0]["raw" + "_legal_text"] = "forbidden snippet"
    manifest_path = write_json(tmp_path / "manifest.json", manifest)

    completed, payload = run_cli(
        tmp_path,
        "--runtime-summary",
        str(runtime_path),
        "--manifest",
        str(manifest_path),
    )

    assert completed.returncode == 1
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_policy_violation"
    assert payload["failure_class"] == "policy_violation"
    assert "RRB_RAW_TEXT_FORBIDDEN" in payload["diagnostic_codes"]


def test_unsafe_raw_payload_text_is_policy_failure(tmp_path: Path) -> None:
    runtime_path = write_json(tmp_path / "runtime.json", confirmed_runtime())
    manifest = load_manifest()
    manifest["diagnostics"] = ["raw legal text should never appear"]
    manifest_path = write_json(tmp_path / "manifest.json", manifest)

    completed, payload = run_cli(
        tmp_path,
        "--runtime-summary",
        str(runtime_path),
        "--manifest",
        str(manifest_path),
    )

    assert completed.returncode == 1
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_policy_violation"
    assert "RRB_RAW_TEXT_FORBIDDEN" in payload["diagnostic_codes"]


def test_threshold_mismatch_is_metric_failure(tmp_path: Path) -> None:
    runtime_path = write_json(tmp_path / "runtime.json", confirmed_runtime())
    manifest = load_manifest()
    for reference in manifest["candidate_references"]:
        if reference["reference_id"] == "RC-M016-001":
            reference["reference_role"] = "distractor"
    manifest_path = write_json(tmp_path / "manifest.json", manifest)

    completed, payload = run_cli(
        tmp_path,
        "--runtime-summary",
        str(runtime_path),
        "--manifest",
        str(manifest_path),
    )

    assert completed.returncode == 1
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_metric"
    assert payload["failure_class"] == "metric_threshold"
    assert payload["diagnostic_codes"] == ["RRB_METRIC_THRESHOLD_MISSED"]
    assert payload["mismatch_records"]


def test_absolute_paths_do_not_leak_from_injected_inputs(tmp_path: Path) -> None:
    runtime_path = write_json(tmp_path / "runtime.json", confirmed_runtime())
    manifest_path = write_json(tmp_path / "manifest.json", load_manifest())

    completed, payload = run_cli(
        tmp_path,
        "--runtime-summary",
        str(runtime_path),
        "--manifest",
        str(manifest_path),
    )

    assert completed.returncode == 0
    assert payload is not None
    stdout = completed.stdout
    assert str(tmp_path) not in stdout
    assert str(ROOT) not in stdout
    assert ".gsd/exec" not in stdout
    assert payload["manifest"]["source_path"] == "manifest.json"


def test_runtime_command_malformed_json_is_runtime_blocker(tmp_path: Path) -> None:
    command = f"{sys.executable} -c 'print(\"not-json\")'"

    completed, payload = run_cli(tmp_path, "--runtime-command", command)

    assert completed.returncode == 1
    assert payload is not None
    assert payload["benchmark_status"] == "blocked_runtime"
    assert payload["diagnostic_codes"] == ["RRB_RUNTIME_DIAGNOSTIC_MALFORMED"]
