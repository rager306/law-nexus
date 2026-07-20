"""Bounded H01 status-tracer integration checks.

The tests never build the Rust workspace. ``cargo build --workspace --offline``
is an explicit prerequisite so pytest remains fast and side-effect free.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from law_nexus_harness.cli import main
from law_nexus_harness.subprocess_runner import run_rust_binary

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target" / "debug" / "ln-status"
CONTRACT = ROOT / "prd" / "migration" / "rust-harness" / "h01-status-tracer-contract.json"


@pytest.fixture(scope="module", autouse=True)
def _built_status_binary_exists() -> None:
    assert BINARY.is_file(), "run `cargo build --workspace --offline` before harness tests"


def test_status_payload_matches_frozen_contract() -> None:
    result = run_rust_binary(BINARY, ["status"])
    expected = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert result.status == "ok"
    assert result.phase == "subprocess_complete"
    assert result.exit_code == 0
    assert result.failure_class is None
    assert result.stderr_bytes == 0
    assert json.loads(result.stdout_tail) == expected


def test_harness_cli_emits_stable_run_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["status", "--binary", str(BINARY)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "law-nexus-harness-run/v1"
    assert payload["status"] == "ok"
    assert payload["phase"] == "subprocess_complete"
    assert payload["binary_path"] == "target/debug/ln-status"
    assert payload["command"] == ["target/debug/ln-status", "status"]
    assert payload["timed_out"] is False
    assert payload["duration_ms"] >= 0
