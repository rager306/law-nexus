"""TDD contracts for the repository preflight control-plane command."""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.cli import main
from law_nexus_harness.preflight import PREFLIGHT_SCHEMA_VERSION, CommandResult, run_preflight

ROOT = Path(__file__).resolve().parents[1]


def passing_runner(command: tuple[str, ...], root: Path) -> CommandResult:
    return CommandResult(
        command=command, duration_ms=1, exit_code=0, stdout_tail="", stderr_tail=""
    )


def failing_cargo_runner(command: tuple[str, ...], root: Path) -> CommandResult:
    if command[:2] == ("cargo", "fmt"):
        return CommandResult(
            command=command,
            duration_ms=2,
            exit_code=1,
            stdout_tail="",
            stderr_tail="Diff in crates/example/src/lib.rs at line 7",
        )
    return passing_runner(command, root)


def test_preflight_report_schema_and_formatter_profile_pass() -> None:
    report = run_preflight(ROOT, runner=passing_runner)
    payload = report.to_dict()

    assert payload["schema_version"] == PREFLIGHT_SCHEMA_VERSION
    assert payload["status"] == "ok"
    assert payload["root"] == str(ROOT)
    assert [item["check_id"] for item in payload["checks"]] == [
        "cargo-fmt-workspace",
        "ruff-format-explicit-python-paths",
    ]
    assert payload["pass_count"] == 2
    assert payload["warn_count"] == 0
    assert payload["error_count"] == 0


def test_cli_preflight_command_emits_stable_json(capsys) -> None:
    code = main(["preflight", "--root", str(ROOT)])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert code == 0
    assert payload["schema_version"] == PREFLIGHT_SCHEMA_VERSION
    assert payload["status"] == "ok"
    assert [item["check_id"] for item in payload["checks"]] == [
        "cargo-fmt-workspace",
        "ruff-format-explicit-python-paths",
    ]


def test_cargo_formatter_failure_is_fail_closed_and_actionable() -> None:
    report = run_preflight(ROOT, runner=failing_cargo_runner)
    payload = report.to_dict()

    assert payload["status"] == "failure"
    assert payload["error_count"] == 1
    failed = {item["check_id"]: item for item in payload["checks"] if item["status"] == "fail"}
    assert failed["cargo-fmt-workspace"]["command"] == ["cargo", "fmt", "--all", "--", "--check"]
    assert "cargo fmt --all" in failed["cargo-fmt-workspace"]["remediation"]
    assert "crates/example/src/lib.rs" in failed["cargo-fmt-workspace"]["stderr_tail"]


def test_ruff_format_check_includes_agent_skill_scripts() -> None:
    commands: list[tuple[str, ...]] = []

    def recording_runner(command: tuple[str, ...], root: Path) -> CommandResult:
        commands.append(command)
        return passing_runner(command, root)

    run_preflight(ROOT, runner=recording_runner)

    ruff_commands = [command for command in commands if command[:3] == ("uv", "run", "ruff")]
    assert ruff_commands == [
        (
            "uv",
            "run",
            "ruff",
            "format",
            "--check",
            ".agents/skills/pi-skill-creator/scripts/aggregate_pi_skill_benchmark.py",
            ".agents/skills/pi-skill-creator/scripts/analyze_skill_triggers.py",
            ".agents/skills/pi-skill-creator/scripts/execute_pi_skill_eval.py",
            ".agents/skills/pi-skill-creator/scripts/generate_pi_skill_report.py",
            ".agents/skills/pi-skill-creator/scripts/grade_pi_skill_eval.py",
            ".agents/skills/pi-skill-creator/scripts/package_pi_skill.py",
            ".agents/skills/pi-skill-creator/scripts/run_pi_skill_eval.py",
            ".agents/skills/pi-skill-creator/scripts/run_pi_skill_loop.py",
            ".agents/skills/pi-skill-creator/scripts/suggest_description.py",
            ".agents/skills/pi-skill-creator/scripts/validate_pi_skill.py",
        )
    ]
