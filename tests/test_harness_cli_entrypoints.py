"""Process-level contracts for repository harness entrypoints."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SUBCOMMANDS = ("status", "governor", "preflight")


def run_entrypoint(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed repository-control commands only
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def assert_help_contract(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    for command in EXPECTED_SUBCOMMANDS:
        assert command in result.stdout


def test_console_script_and_package_module_expose_same_commands() -> None:
    package = run_entrypoint("uv", "run", "python", "-m", "law_nexus_harness", "--help")
    console = run_entrypoint("uv", "run", "law-nexus-harness", "--help")

    assert_help_contract(package)
    assert_help_contract(console)


def test_console_script_and_package_module_emit_equivalent_governor_reports() -> None:
    package = run_entrypoint("uv", "run", "python", "-m", "law_nexus_harness", "governor")
    console = run_entrypoint("uv", "run", "law-nexus-harness", "governor")

    assert package.stderr == ""
    assert console.stderr == ""

    package_report = json.loads(package.stdout)
    console_report = json.loads(console.stdout)
    assert package_report == console_report
    assert package_report["schema_version"] == "law-nexus-governor-report/v1"
    expected_code = 0 if package_report["status"] == "ok" else 1
    assert package.returncode == expected_code
    assert console.returncode == expected_code
