"""TDD contracts for the repository preflight control-plane command."""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.cli import main
from law_nexus_harness.governor import GovernorFinding, GovernorReport
from law_nexus_harness.preflight import (
    DOCS_FRESHNESS_PATHS,
    PREFLIGHT_SCHEMA_VERSION,
    CommandResult,
    run_preflight,
)

ROOT = Path(__file__).resolve().parents[1]


def passing_runner(command: tuple[str, ...], root: Path) -> CommandResult:
    stdout = ""
    if command == ("git", "rev-parse", "HEAD"):
        stdout = "abc123\n"
    elif command == ("git", "status", "--porcelain"):
        stdout = ""
    return CommandResult(
        command=command, duration_ms=1, exit_code=0, stdout_tail=stdout, stderr_tail=""
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


def write_gsd_state(root: Path) -> None:
    gsd = root / ".gsd"
    gsd.mkdir()
    (gsd / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Active Milestone:** M128-z37bqq\n"
        "**Active Slice:** S04\n"
        "**Phase:** executing\n",
        encoding="utf-8",
    )


def write_gitnexus_meta(root: Path, last_commit: str = "abc123") -> None:
    gitnexus = root / ".gitnexus"
    gitnexus.mkdir()
    (gitnexus / "meta.json").write_text(json.dumps({"lastCommit": last_commit}), encoding="utf-8")


def passing_governor(root: Path) -> GovernorReport:
    return GovernorReport(
        schema_version="law-nexus-governor-report/v1",
        status="ok",
        root=str(root),
        findings=(),
        error_count=0,
        warn_count=0,
        pass_count=0,
    )


def governor_failure(*check_ids: str) -> GovernorReport:
    findings = tuple(
        GovernorFinding(
            check_id=check_id,
            status="fail",
            severity="error",
            message="test failure",
            observed="test",
            remediation="fix it",
        )
        for check_id in check_ids
    )
    return GovernorReport(
        schema_version="law-nexus-governor-report/v1",
        status="failure",
        root="/tmp",
        findings=findings,
        error_count=len(findings),
        warn_count=0,
        pass_count=0,
    )


def run_test_preflight(root: Path, *, runner=passing_runner, governor_runner=passing_governor):
    return run_preflight(root, runner=runner, governor_runner=governor_runner)


def write_docs(root: Path) -> None:
    for rel_path in DOCS_FRESHNESS_PATHS:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# placeholder\n", encoding="utf-8")


EXPECTED_CHECK_IDS = [
    "cargo-fmt-workspace",
    "ruff-format-explicit-python-paths",
    "crate-dependency-allowlist",
    "gitnexus-index-freshness",
    "gsd-state-surface",
    "docs-freshness-surface",
    "trajectory-governor",
]


def test_preflight_report_schema_and_formatter_profile_pass(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_gsd_state(tmp_path)
    write_docs(tmp_path)
    report = run_test_preflight(tmp_path)
    payload = report.to_dict()

    assert payload["schema_version"] == PREFLIGHT_SCHEMA_VERSION
    assert payload["status"] == "ok"
    assert payload["root"] == str(tmp_path.resolve())
    assert [item["check_id"] for item in payload["checks"]] == EXPECTED_CHECK_IDS
    assert payload["pass_count"] == 7
    assert payload["warn_count"] == 0
    assert payload["error_count"] == 0


def test_cli_preflight_command_emits_stable_json(capsys) -> None:
    code = main(["preflight", "--root", str(ROOT)])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert code == 0
    assert payload["schema_version"] == PREFLIGHT_SCHEMA_VERSION
    assert payload["status"] == "ok"
    assert [item["check_id"] for item in payload["checks"]] == EXPECTED_CHECK_IDS


def test_cargo_formatter_failure_is_fail_closed_and_actionable() -> None:
    report = run_test_preflight(ROOT, runner=failing_cargo_runner)
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

    run_test_preflight(ROOT, runner=recording_runner)

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


def test_stale_gitnexus_metadata_is_warn_with_reindex_remediation(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path, last_commit="old456")
    write_gsd_state(tmp_path)
    write_docs(tmp_path)

    report = run_test_preflight(tmp_path)
    payload = report.to_dict()

    assert payload["status"] == "ok"
    assert payload["warn_count"] == 1
    by_id = {item["check_id"]: item for item in payload["checks"]}
    assert by_id["gitnexus-index-freshness"]["status"] == "warn"
    assert (
        "gitnexus analyze --force --name law-nexus"
        in by_id["gitnexus-index-freshness"]["remediation"]
    )


def test_dirty_worktree_marks_gitnexus_freshness_warning(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_gsd_state(tmp_path)
    write_docs(tmp_path)

    def dirty_runner(command: tuple[str, ...], root: Path) -> CommandResult:
        if command == ("git", "status", "--porcelain"):
            return CommandResult(
                command=command,
                duration_ms=1,
                exit_code=0,
                stdout_tail=" M file.py\n",
                stderr_tail="",
            )
        return passing_runner(command, root)

    payload = run_test_preflight(tmp_path, runner=dirty_runner).to_dict()
    by_id = {item["check_id"]: item for item in payload["checks"]}

    assert by_id["gitnexus-index-freshness"]["status"] == "warn"
    assert "working tree has uncommitted changes" in by_id["gitnexus-index-freshness"]["observed"]


def test_completed_gsd_state_without_active_milestone_passes(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_docs(tmp_path)
    gsd = tmp_path / ".gsd"
    gsd.mkdir()
    (gsd / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Last Completed Milestone:** M130-bzeiq1: Governor debt closure\n"
        "**Active Slice:** None\n"
        "**Phase:** complete\n",
        encoding="utf-8",
    )

    payload = run_test_preflight(tmp_path).to_dict()
    finding = {item["check_id"]: item for item in payload["checks"]}["gsd-state-surface"]

    assert finding["status"] == "pass"
    assert "completed terminal state" in finding["observed"]


def test_executing_gsd_state_without_active_milestone_warns(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_docs(tmp_path)
    gsd = tmp_path / ".gsd"
    gsd.mkdir()
    (gsd / "STATE.md").write_text(
        "# GSD State\n\n"
        "**Last Completed Milestone:** M130-bzeiq1: Governor debt closure\n"
        "**Active Slice:** S01\n"
        "**Phase:** executing\n",
        encoding="utf-8",
    )

    payload = run_test_preflight(tmp_path).to_dict()
    finding = {item["check_id"]: item for item in payload["checks"]}["gsd-state-surface"]

    assert finding["status"] == "warn"
    assert "Active Milestone" in finding["observed"]


def test_missing_gsd_state_surface_is_warn_not_db_access(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_docs(tmp_path)

    payload = run_test_preflight(tmp_path).to_dict()
    by_id = {item["check_id"]: item for item in payload["checks"]}

    assert by_id["gsd-state-surface"]["status"] == "warn"
    assert by_id["gsd-state-surface"]["command"] == ["read", ".gsd/STATE.md"]
    assert "GSD tools" in by_id["gsd-state-surface"]["remediation"]


def test_docs_freshness_uses_only_tracked_portable_authority_surfaces(
    tmp_path: Path,
) -> None:
    assert ".gsd/REQUIREMENTS.md" not in DOCS_FRESHNESS_PATHS
    assert "prd/project-state/roadmap.md" in DOCS_FRESHNESS_PATHS
    assert "doc/adr/0014-ruvector-primary-infrastructure.md" in DOCS_FRESHNESS_PATHS

    write_gitnexus_meta(tmp_path)
    write_gsd_state(tmp_path)
    write_docs(tmp_path)
    payload = run_test_preflight(tmp_path).to_dict()
    finding = {item["check_id"]: item for item in payload["checks"]}["docs-freshness-surface"]
    assert finding["status"] == "pass"
    assert "requirements" not in finding["observed"].lower()


def test_portable_governor_failure_fails_preflight(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_gsd_state(tmp_path)
    write_docs(tmp_path)

    payload = run_test_preflight(
        tmp_path,
        governor_runner=lambda _root: governor_failure("architecture-direction-contract"),
    ).to_dict()
    finding = {item["check_id"]: item for item in payload["checks"]}["trajectory-governor"]

    assert payload["status"] == "failure"
    assert finding["status"] == "fail"
    assert "architecture-direction-contract" in finding["observed"]


def test_portable_failure_is_not_hidden_by_missing_local_projection(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_docs(tmp_path)

    payload = run_test_preflight(
        tmp_path,
        governor_runner=lambda _root: governor_failure(
            "gsd-state-present", "architecture-direction-contract"
        ),
    ).to_dict()
    finding = {item["check_id"]: item for item in payload["checks"]}["trajectory-governor"]

    assert payload["status"] == "failure"
    assert finding["status"] == "fail"
    assert "architecture-direction-contract" in finding["observed"]


def test_existing_local_projection_debt_fails_preflight(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_gsd_state(tmp_path)
    write_docs(tmp_path)

    payload = run_test_preflight(
        tmp_path,
        governor_runner=lambda _root: governor_failure("gsd-no-open-registry-debt"),
    ).to_dict()
    finding = {item["check_id"]: item for item in payload["checks"]}["trajectory-governor"]

    assert payload["status"] == "failure"
    assert finding["status"] == "fail"


def test_local_projection_only_governor_failures_warn_in_preflight(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_docs(tmp_path)

    payload = run_test_preflight(
        tmp_path,
        governor_runner=lambda _root: governor_failure(
            "gsd-state-present", "roadmap-state-present"
        ),
    ).to_dict()
    finding = {item["check_id"]: item for item in payload["checks"]}["trajectory-governor"]

    assert payload["status"] == "ok"
    assert finding["status"] == "warn"
    assert "local-projection-unavailable" in finding["observed"]


def test_missing_docs_surface_warns_with_required_files(tmp_path: Path) -> None:
    write_gitnexus_meta(tmp_path)
    write_gsd_state(tmp_path)

    payload = run_test_preflight(tmp_path).to_dict()
    by_id = {item["check_id"]: item for item in payload["checks"]}

    assert by_id["docs-freshness-surface"]["status"] == "warn"
    assert "prd/ARCHITECTURE.md" in by_id["docs-freshness-surface"]["observed"]
    assert (
        "doc/adr/0007-python-repository-harness.md" in by_id["docs-freshness-surface"]["observed"]
    )
    assert "assess" in by_id["docs-freshness-surface"]["remediation"].lower()
