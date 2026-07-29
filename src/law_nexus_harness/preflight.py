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

from law_nexus_harness.governor import GovernorReport, run_governor

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
DOCS_FRESHNESS_PATHS = (
    "prd/ARCHITECTURE.md",
    "prd/project-state/roadmap.md",
    "doc/adr/0004-rust-migration-decision.md",
    "doc/adr/0007-python-repository-harness.md",
    "doc/adr/0014-ruvector-primary-infrastructure.md",
)
_UNAVAILABLE_LOCAL_PROJECTION_CHECK_IDS = {
    "gsd-state-present",
    "roadmap-state-present",
}


@dataclass(frozen=True)
class CommandResult:
    """Bounded result for one repository preflight subprocess."""

    command: tuple[str, ...]
    duration_ms: int
    exit_code: int | None
    stdout_tail: str
    stderr_tail: str


Runner = Callable[[tuple[str, ...], Path], CommandResult]
GovernorRunner = Callable[[Path], GovernorReport]


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


def _warning_check(
    *,
    check_id: str,
    phase: str,
    command: tuple[str, ...],
    observed: str,
    remediation: str,
    duration_ms: int = 0,
    exit_code: int | None = None,
    stdout_tail: str = "",
    stderr_tail: str = "",
) -> PreflightCheck:
    return PreflightCheck(
        check_id=check_id,
        phase=phase,
        status="warn",
        severity="warn",
        command=command,
        duration_ms=duration_ms,
        exit_code=exit_code,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
        observed=observed,
        remediation=remediation,
    )


def _pass_check(
    *,
    check_id: str,
    phase: str,
    command: tuple[str, ...],
    observed: str,
    duration_ms: int = 0,
    exit_code: int | None = 0,
    stdout_tail: str = "",
    stderr_tail: str = "",
) -> PreflightCheck:
    return PreflightCheck(
        check_id=check_id,
        phase=phase,
        status="pass",
        severity="ok",
        command=command,
        duration_ms=duration_ms,
        exit_code=exit_code,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
        observed=observed,
        remediation="none",
    )


def _gitnexus_freshness_check(root: Path, runner: Runner) -> PreflightCheck:
    head = runner(("git", "rev-parse", "HEAD"), root)
    status = runner(("git", "status", "--porcelain"), root)
    meta_path = root / ".gitnexus" / "meta.json"
    command = ("read", ".gitnexus/meta.json")
    remediation = "Run `gitnexus analyze --force --name law-nexus` after local code changes."
    if head.exit_code != 0:
        return _warning_check(
            check_id="gitnexus-index-freshness",
            phase="graph-freshness",
            command=head.command,
            observed="Unable to read current git HEAD for GitNexus freshness check.",
            remediation=remediation,
            duration_ms=head.duration_ms,
            exit_code=head.exit_code,
            stdout_tail=head.stdout_tail,
            stderr_tail=head.stderr_tail,
        )
    if status.exit_code != 0:
        return _warning_check(
            check_id="gitnexus-index-freshness",
            phase="graph-freshness",
            command=status.command,
            observed="Unable to read working tree status for GitNexus freshness check.",
            remediation=remediation,
            duration_ms=status.duration_ms,
            exit_code=status.exit_code,
            stdout_tail=status.stdout_tail,
            stderr_tail=status.stderr_tail,
        )
    if status.stdout_tail.strip():
        return _warning_check(
            check_id="gitnexus-index-freshness",
            phase="graph-freshness",
            command=status.command,
            observed="GitNexus index may be stale: working tree has uncommitted changes.",
            remediation=remediation,
            duration_ms=status.duration_ms,
            exit_code=status.exit_code,
            stdout_tail=status.stdout_tail,
            stderr_tail=status.stderr_tail,
        )
    if not meta_path.is_file():
        return _warning_check(
            check_id="gitnexus-index-freshness",
            phase="graph-freshness",
            command=command,
            observed="GitNexus metadata is missing.",
            remediation=remediation,
        )
    try:
        indexed_commit = str(
            json.loads(meta_path.read_text(encoding="utf-8")).get("lastCommit", "")
        )
    except (OSError, json.JSONDecodeError) as error:
        return _warning_check(
            check_id="gitnexus-index-freshness",
            phase="graph-freshness",
            command=command,
            observed="GitNexus metadata could not be read as JSON.",
            remediation=remediation,
            stderr_tail=str(error),
        )
    current_commit = head.stdout_tail.strip()
    if indexed_commit != current_commit:
        return _warning_check(
            check_id="gitnexus-index-freshness",
            phase="graph-freshness",
            command=command,
            observed=f"GitNexus index commit {indexed_commit or '<missing>'} does not match HEAD {current_commit}.",
            remediation=remediation,
        )
    return _pass_check(
        check_id="gitnexus-index-freshness",
        phase="graph-freshness",
        command=command,
        observed="GitNexus metadata matches HEAD and working tree is clean.",
    )


def _gsd_state_surface_check(root: Path) -> PreflightCheck:
    state_path = root / ".gsd" / "STATE.md"
    command = ("read", ".gsd/STATE.md")
    remediation = "Use GSD tools such as `gsd_milestone_status` to inspect active task/slice state."
    if not state_path.is_file():
        return _warning_check(
            check_id="gsd-state-surface",
            phase="gsd-state",
            command=command,
            observed="GSD STATE.md surface is missing; preflight will not query .gsd/gsd.db directly.",
            remediation=remediation,
        )
    state_text = state_path.read_text(encoding="utf-8")
    terminal = "**Phase:** complete" in state_text
    required = (
        ("**Last Completed Milestone:**", "**Active Slice:**", "**Phase:**")
        if terminal
        else ("**Active Milestone:**", "**Active Slice:**", "**Phase:**")
    )
    missing = [field for field in required if field not in state_text]
    if missing:
        return _warning_check(
            check_id="gsd-state-surface",
            phase="gsd-state",
            command=command,
            observed=f"GSD STATE.md is present but missing fields: {', '.join(missing)}.",
            remediation=remediation,
        )
    return _pass_check(
        check_id="gsd-state-surface",
        phase="gsd-state",
        command=command,
        observed=(
            "GSD STATE.md exposes a completed terminal state."
            if terminal
            else "GSD STATE.md exposes active milestone, slice, and phase surface."
        ),
    )


def _trajectory_governor_check(root: Path, governor_runner: GovernorRunner) -> PreflightCheck:
    report = governor_runner(root)
    failed_ids = sorted(item.check_id for item in report.findings if item.status == "fail")
    command = ("internal", "trajectory-governor")
    if not failed_ids:
        return _pass_check(
            check_id="trajectory-governor",
            phase="trajectory",
            command=command,
            observed=f"governor_pass={report.pass_count}; governor_errors=0",
        )
    if set(failed_ids) <= _UNAVAILABLE_LOCAL_PROJECTION_CHECK_IDS:
        return _warning_check(
            check_id="trajectory-governor",
            phase="trajectory",
            command=command,
            observed=f"local-projection-unavailable; failed_checks={failed_ids}",
            remediation=(
                "Materialize or repair local GSD projections and rerun governor; portable tracked "
                "architecture checks remain authoritative in clean-clone CI"
            ),
            exit_code=1,
        )
    return PreflightCheck(
        check_id="trajectory-governor",
        phase="trajectory",
        status="fail",
        severity="error",
        command=command,
        duration_ms=0,
        exit_code=1,
        stdout_tail="",
        stderr_tail="",
        observed=f"failed_checks={failed_ids}",
        remediation="Run `uv run law-nexus-harness governor` and resolve every portable failure.",
    )


def _port_contract_coverage_check(root: Path, runner: Runner) -> PreflightCheck:
    """Advisory inventory of InMemory adapters lacking shared ln-testkit contracts.

    Debt remains non-blocking (warn) so remaining adapters stay visible without
    thrashing every commit. Script crash or unreadable payload is fail-closed.
    """
    command = (
        "uv",
        "run",
        "python",
        "scripts/verify-port-contract-coverage.py",
    )
    result = runner(command, root)
    remediation = (
        "Expand ln-testkit shared port contracts for uncovered InMemory adapters "
        "(ADR-0015) or inspect `uv run python scripts/verify-port-contract-coverage.py`. "
        "Do not claim full coverage or real TEI/RuVector validation from inventory alone."
    )
    if result.exit_code != 0:
        return PreflightCheck(
            check_id="port-contract-coverage",
            phase="architecture",
            status="fail",
            severity="error",
            command=result.command,
            duration_ms=result.duration_ms,
            exit_code=result.exit_code,
            stdout_tail=result.stdout_tail,
            stderr_tail=result.stderr_tail,
            observed="Port-contract coverage inventory script failed.",
            remediation=remediation,
        )
    try:
        payload = json.loads(result.stdout_tail or "{}")
    except json.JSONDecodeError as error:
        return PreflightCheck(
            check_id="port-contract-coverage",
            phase="architecture",
            status="fail",
            severity="error",
            command=result.command,
            duration_ms=result.duration_ms,
            exit_code=result.exit_code,
            stdout_tail=result.stdout_tail,
            stderr_tail=str(error),
            observed="Port-contract coverage inventory did not emit valid JSON.",
            remediation=remediation,
        )
    uncovered = int(payload.get("uncovered_count") or 0)
    covered = int(payload.get("covered_count") or 0)
    discovered = int(payload.get("discovered_count") or 0)
    status = str(payload.get("status") or "")
    if uncovered > 0 or status == "debt":
        return _warning_check(
            check_id="port-contract-coverage",
            phase="architecture",
            command=result.command,
            observed=(
                f"InMemory port-contract coverage debt: covered={covered}, "
                f"uncovered={uncovered}, discovered={discovered} "
                f"(lifecycle [bounded]; not real-adapter validation)."
            ),
            remediation=remediation,
            duration_ms=result.duration_ms,
            exit_code=result.exit_code,
            stdout_tail=result.stdout_tail,
            stderr_tail=result.stderr_tail,
        )
    return _pass_check(
        check_id="port-contract-coverage",
        phase="architecture",
        command=result.command,
        observed=(
            f"All discovered InMemory adapters are covered by ln-testkit shared "
            f"contracts (covered={covered}, discovered={discovered})."
        ),
        duration_ms=result.duration_ms,
        exit_code=result.exit_code,
        stdout_tail=result.stdout_tail,
        stderr_tail=result.stderr_tail,
    )


def _docs_freshness_surface_check(root: Path) -> PreflightCheck:
    command = ("read", *DOCS_FRESHNESS_PATHS)
    remediation = (
        "Assess and update tracked architecture, roadmap, and ADR surfaces after each wave; "
        "preserve lifecycle tags and do not promote generated projections to source truth."
    )
    missing: list[str] = []
    for rel_path in DOCS_FRESHNESS_PATHS:
        path = root / rel_path
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(rel_path)
    if missing:
        return _warning_check(
            check_id="docs-freshness-surface",
            phase="docs-freshness",
            command=command,
            observed=f"Missing or empty docs: {', '.join(missing)}.",
            remediation=remediation,
        )
    return _pass_check(
        check_id="docs-freshness-surface",
        phase="docs-freshness",
        command=command,
        observed="All required tracked architecture, roadmap, and ADR surfaces are present.",
    )


def run_preflight(
    root: Path,
    *,
    runner: Runner = run_command,
    governor_runner: GovernorRunner = run_governor,
) -> PreflightReport:
    """Run non-mutating formatter and lint preflight checks."""

    resolved_root = root.resolve()
    cargo_fmt = runner(("cargo", "fmt", "--all", "--", "--check"), resolved_root)
    ruff_format = runner(
        ("uv", "run", "ruff", "format", "--check", *AGENT_SKILL_SCRIPT_PATHS),
        resolved_root,
    )
    crate_allowlist = runner(
        (
            "uv",
            "run",
            "python",
            "scripts/verify-crate-dependency-allowlist.py",
        ),
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
        _check_from_result(
            check_id="crate-dependency-allowlist",
            phase="architecture",
            result=crate_allowlist,
            observed_ok="Workspace crate path-dependency allowlist is clean.",
            observed_fail="Workspace crate path-dependency allowlist violations detected.",
            remediation=(
                "Run `uv run python scripts/verify-crate-dependency-allowlist.py` and "
                "update prd/architecture/crate-dependency-allowlist.json only for intentional "
                "hexagonal composition edges (ADR-0015)."
            ),
        ),
        _port_contract_coverage_check(resolved_root, runner),
        _gitnexus_freshness_check(resolved_root, runner),
        _gsd_state_surface_check(resolved_root),
        _docs_freshness_surface_check(resolved_root),
        _trajectory_governor_check(resolved_root, governor_runner),
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
