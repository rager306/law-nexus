"""Repository preflight checks for early auto-mode trajectory failures.

This module is ADR-0007 repository control-plane logic only. It runs
non-mutating repository checks and emits bounded diagnostics for humans and
auto-mode before commit time.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

PREFLIGHT_SCHEMA_VERSION = "law-nexus-preflight-report/v1"

PreflightStatus = Literal["ok", "failure"]
CheckStatus = Literal["pass", "fail", "warn"]
Severity = Literal["ok", "warn", "error"]
DEFAULT_MAX_OUTPUT_BYTES = 8192
AGENT_SKILL_SCRIPT_PATHS = (
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


@dataclass(frozen=True)
class CommandResult:
    """Bounded result for one repository preflight subprocess."""

    command: tuple[str, ...]
    duration_ms: int
    exit_code: int | None
    stdout_tail: str
    stderr_tail: str


Runner = Callable[[tuple[str, ...], Path], CommandResult]


@dataclass(frozen=True)
class PreflightCheck:
    """Bounded diagnostics for one repository preflight check."""

    check_id: str
    phase: str
    status: CheckStatus
    severity: Severity
    command: tuple[str, ...]
    duration_ms: int
    exit_code: int | None
    stdout_tail: str
    stderr_tail: str
    observed: str
    remediation: str


@dataclass(frozen=True)
class PreflightReport:
    """Stable preflight report for auto-mode and human operators."""

    schema_version: str
    status: PreflightStatus
    root: str
    checks: tuple[PreflightCheck, ...]
    error_count: int
    warn_count: int
    pass_count: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [asdict(item) for item in self.checks]
        for item in payload["checks"]:
            item["command"] = list(item["command"])
        return payload

    def to_json(self) -> str:
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        )


def _bounded_tail(value: bytes | str | None, limit: int = DEFAULT_MAX_OUTPUT_BYTES) -> str:
    if value is None:
        return ""
    raw = value if isinstance(value, bytes) else value.encode("utf-8", errors="replace")
    return raw[-limit:].decode("utf-8", errors="replace")


def run_command(command: tuple[str, ...], root: Path) -> CommandResult:
    """Run one non-mutating repository check through a bounded subprocess."""

    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S603 - explicit repository-control command boundary
            command,
            cwd=root,
            check=False,
            capture_output=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        return CommandResult(
            command=command,
            duration_ms=round((time.monotonic() - started) * 1000),
            exit_code=None,
            stdout_tail=_bounded_tail(error.stdout),
            stderr_tail=_bounded_tail(error.stderr),
        )
    except OSError as error:
        return CommandResult(
            command=command,
            duration_ms=round((time.monotonic() - started) * 1000),
            exit_code=None,
            stdout_tail="",
            stderr_tail=str(error),
        )
    return CommandResult(
        command=command,
        duration_ms=round((time.monotonic() - started) * 1000),
        exit_code=completed.returncode,
        stdout_tail=_bounded_tail(completed.stdout),
        stderr_tail=_bounded_tail(completed.stderr),
    )


def _check_from_result(
    *,
    check_id: str,
    phase: str,
    result: CommandResult,
    observed_ok: str,
    observed_fail: str,
    remediation: str,
) -> PreflightCheck:
    passed = result.exit_code == 0
    return PreflightCheck(
        check_id=check_id,
        phase=phase,
        status="pass" if passed else "fail",
        severity="ok" if passed else "error",
        command=result.command,
        duration_ms=result.duration_ms,
        exit_code=result.exit_code,
        stdout_tail=result.stdout_tail,
        stderr_tail=result.stderr_tail,
        observed=observed_ok if passed else observed_fail,
        remediation="none" if passed else remediation,
    )


def run_preflight(root: Path, *, runner: Runner = run_command) -> PreflightReport:
    """Run non-mutating formatter and lint preflight checks."""

    resolved_root = root.resolve()
    cargo_fmt = runner(("cargo", "fmt", "--all", "--", "--check"), resolved_root)
    ruff_format = runner(
        ("uv", "run", "ruff", "format", "--check", *AGENT_SKILL_SCRIPT_PATHS),
        resolved_root,
    )
    checks = (
        _check_from_result(
            check_id="cargo-fmt-workspace",
            phase="formatter",
            result=cargo_fmt,
            observed_ok="Rust workspace formatting is clean.",
            observed_fail="Rust workspace formatting drift detected.",
            remediation="Run `cargo fmt --all` before committing Rust/Cargo changes.",
        ),
        _check_from_result(
            check_id="ruff-format-explicit-python-paths",
            phase="formatter",
            result=ruff_format,
            observed_ok="Explicit Python harness/tooling paths are Ruff-formatted.",
            observed_fail="Explicit Python harness/tooling path formatting drift detected.",
            remediation=(
                "Run `uv run ruff format .agents/skills/pi-skill-creator/scripts/*.py` "
                "or format the listed files explicitly."
            ),
        ),
    )
    error_count = sum(1 for item in checks if item.severity == "error")
    warn_count = sum(1 for item in checks if item.severity == "warn")
    pass_count = sum(1 for item in checks if item.severity == "ok")
    return PreflightReport(
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        status="failure" if error_count else "ok",
        root=str(resolved_root),
        checks=checks,
        error_count=error_count,
        warn_count=warn_count,
        pass_count=pass_count,
    )
