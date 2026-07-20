"""Failure visibility for the process-only Rust harness boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from law_nexus_harness.subprocess_runner import run_rust_binary

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target" / "debug" / "ln-status"


@pytest.fixture(scope="module", autouse=True)
def _built_status_binary_exists() -> None:
    assert BINARY.is_file(), "run `cargo build --workspace --offline` before harness tests"


def test_nonzero_exit_is_structured() -> None:
    result = run_rust_binary(BINARY, ["--fail"])

    assert result.status == "failure"
    assert result.phase == "subprocess_complete"
    assert result.exit_code == 2
    assert result.failure_class == "nonzero_exit"
    assert "forced failure" in result.stderr_tail


def test_timeout_is_structured_and_bounded() -> None:
    result = run_rust_binary(BINARY, ["--sleep-ms", "200"], timeout_seconds=0.02)

    assert result.status == "failure"
    assert result.phase == "timeout"
    assert result.exit_code is None
    assert result.timed_out is True
    assert result.failure_class == "timeout"
    assert result.duration_ms < 1000


def test_missing_binary_is_structured() -> None:
    result = run_rust_binary(Path("target/debug/does-not-exist"), ["status"])

    assert result.status == "failure"
    assert result.phase == "binary_missing"
    assert result.exit_code is None
    assert result.failure_class == "binary_missing"
    assert result.stdout_bytes == 0
    assert result.stderr_bytes == 0


def test_output_is_tail_bounded_without_losing_raw_byte_count() -> None:
    result = run_rust_binary(BINARY, ["--verbose-bytes", "4096"], max_output_bytes=128)

    assert result.status == "ok"
    assert result.stdout_bytes == 4097
    assert len(result.stdout_tail.encode("utf-8")) == 128
    assert result.stdout_tail.endswith("\n")
    assert result.stdout_truncated is True
    assert result.stderr_truncated is False


def test_invalid_runner_limits_fail_before_process_start() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        run_rust_binary(BINARY, timeout_seconds=0)
    with pytest.raises(ValueError, match="max_output_bytes"):
        run_rust_binary(BINARY, max_output_bytes=-1)
