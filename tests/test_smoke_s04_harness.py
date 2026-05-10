from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/smoke-s04-falkordb-capabilities.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_s04_harness", HARNESS_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_positive_timeout_rejects_invalid_values() -> None:
    harness = load_harness()

    assert harness.parse_positive_timeout("3") == 3
    with pytest.raises(argparse.ArgumentTypeError):
        harness.parse_positive_timeout("0")
    with pytest.raises(argparse.ArgumentTypeError):
        harness.parse_positive_timeout("not-an-int")


def test_planned_cleanup_command_targets_unique_container_name() -> None:
    harness = load_harness()

    name = harness.make_container_name()
    assert name.startswith("s04-falkordb-smoke-")
    assert harness.planned_cleanup_commands(name) == [["docker", "rm", "-f", name]]


def test_wait_for_container_ready_records_ping_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    harness = load_harness()
    state = harness.create_state(tmp_path, 10)
    calls: list[list[str]] = []

    def fake_run_command(command: list[str], timeout_seconds: int, log_dir: Path, phase: str):
        calls.append(command)
        log_path = harness.write_log(log_dir, phase, "PONG")
        return harness.CommandResult(command, 0, False, 0.01, "PONG\n", "", log_path)

    monkeypatch.setattr(harness, "run_command", fake_run_command)

    assert harness.wait_for_container_ready(state) is True
    assert calls == [["docker", "exec", state.container_name, "redis-cli", "PING"]]
    assert state.command_summary["container-readiness"]["exit_code"] == 0


def test_wait_for_container_ready_cascades_blocker_on_ping_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    harness = load_harness()
    state = harness.create_state(tmp_path, 1)

    def fake_run_command(command: list[str], timeout_seconds: int, log_dir: Path, phase: str):
        log_path = harness.write_log(log_dir, phase, "not ready")
        return harness.CommandResult(command, 1, False, 0.01, "", "not ready", log_path)

    monkeypatch.setattr(harness, "run_command", fake_run_command)
    monkeypatch.setattr(harness.time, "sleep", lambda _seconds: None)

    assert harness.wait_for_container_ready(state) is False
    assert state.findings["falkordb-basic-graph"].status == "blocked-environment"
    assert state.findings["falkordb-basic-graph"].diagnostics["root_cause"] == "docker-falkordb-readiness-exit-1"


def test_cascade_blocker_applies_same_root_cause_and_log(tmp_path: Path) -> None:
    harness = load_harness()
    state = harness.create_state(tmp_path, 10)
    log_path = harness.write_log(state.log_dir, "docker-daemon", "docker unavailable")

    harness.cascade_blocker(
        state,
        ("falkordb-basic-graph", "falkordb-vector-node", "falkordb-algo-pagerank"),
        "docker-daemon-timeout",
        "Docker daemon did not respond before timeout.",
        "docker-daemon",
        log_path,
    )

    first = state.findings["falkordb-basic-graph"]
    second = state.findings["falkordb-vector-node"]
    third = state.findings["falkordb-algo-pagerank"]
    assert first.status == "blocked-environment"
    assert second.status == "blocked-environment"
    assert third.status == "blocked-environment"
    assert first.diagnostics["root_cause"] == "docker-daemon-timeout"
    assert second.diagnostics["root_cause"] == "docker-daemon-timeout"
    assert third.diagnostics["root_cause"] == "docker-daemon-timeout"
    assert first.raw_log_reference == second.raw_log_reference == third.raw_log_reference
    assert first.raw_log_reference.endswith("logs/docker-daemon.log")


def test_run_command_records_timeout_classification(tmp_path: Path) -> None:
    harness = load_harness()
    log_dir = tmp_path / "logs"

    result = harness.run_command(
        ["python", "-c", "import time; time.sleep(2)"],
        1,
        log_dir,
        "slow-command",
    )

    assert result.timed_out is True
    assert result.exit_code is None
    assert harness.command_root_cause(result, "slow-command") == "slow-command-timeout"
    assert result.log_path.is_file()
    assert "TIMEOUT after 1s" in result.log_path.read_text(encoding="utf-8")


def test_mark_out_of_harness_capabilities_are_terminal(tmp_path: Path) -> None:
    harness = load_harness()
    state = harness.create_state(tmp_path, 10)
    log_path = harness.write_log(state.log_dir, "boundary", "boundary")

    harness.mark_out_of_harness_capabilities(state, log_path)

    for capability_id in harness.LITE_AND_EMBEDDING_IDS:
        finding = state.findings[capability_id]
        assert finding.status == "bounded-not-product-proven"
        assert finding.evidence_class == "out-of-scope"
        assert finding.diagnostics["root_cause"] == "outside-docker-falkordb-harness"


def test_falkordblite_binary_blockers_distinguish_missing_binary_metadata() -> None:
    harness = load_harness()

    assert harness.falkordblite_binary_blockers({"redis_executable": "/tmp/redis", "falkordb_module": "/tmp/falkordb.so"}) == []
    assert harness.falkordblite_binary_blockers({"redis_executable": "", "falkordb_module": "/tmp/falkordb.so"}) == [
        "missing-redis-server-binary"
    ]
    assert harness.falkordblite_binary_blockers({"redis_executable": "/tmp/redis", "falkordb_module": ""}) == [
        "missing-falkordb-module"
    ]


def test_embedding_model_cache_metadata_handles_absent_and_present_cache(tmp_path: Path) -> None:
    harness = load_harness()

    absent = harness.embedding_model_cache_metadata("deepvk/USER-bge-m3", [tmp_path / "empty"])
    assert absent["present"] is False
    assert "models--deepvk--USER-bge-m3" in absent["checked"][0]

    model_dir = tmp_path / "hub" / "models--deepvk--USER-bge-m3" / "snapshots" / "abc123"
    model_dir.mkdir(parents=True)
    present = harness.embedding_model_cache_metadata("deepvk/USER-bge-m3", [tmp_path / "hub"])
    assert present["present"] is True
    assert present["snapshot_count"] == 1
    assert present["snapshots"] == ["abc123"]


def test_json_and_markdown_artifacts_include_runtime_diagnostics(tmp_path: Path) -> None:
    harness = load_harness()
    state = harness.create_state(tmp_path, 10)
    log_path = harness.write_log(state.log_dir, "all-blocked", "blocked")
    harness.mark_out_of_harness_capabilities(state, log_path)
    harness.put_finding(
        state,
        "docker-daemon",
        "blocked-environment",
        "docker-daemon",
        log_path,
        "docker-daemon-exit-1",
        "Docker daemon unavailable in test fixture.",
    )
    harness.cascade_blocker(
        state,
        ("docker-falkordb-image", *harness.FALKORDB_CAPABILITY_IDS),
        "docker-daemon-exit-1",
        "Docker daemon unavailable in test fixture.",
        "docker-daemon",
        log_path,
    )
    harness.finalize_missing_findings(state, log_path)

    json_path = harness.write_json_artifact(state, log_path)
    markdown_path = harness.write_markdown_artifact(state, json_path)

    payload = json_path.read_text(encoding="utf-8")
    assert '"id": "docker-daemon"' in payload
    assert '"runtime_evidence":' in payload
    assert '"phase": "runtime-results"' in payload
    assert '"status": "blocked-environment"' in payload
    assert '"root_cause": "docker-daemon-exit-1"' in payload
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "## Failure Diagnostics" in markdown
    assert "`falkordb-basic-graph`" in markdown
    assert "`falkordb-algo-pagerank`" in markdown
    assert "`falkordb-algo-wcc`" in markdown
    assert "M001 architecture-only" in markdown
