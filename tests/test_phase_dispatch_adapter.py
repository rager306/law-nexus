"""Deterministic stub-child contracts for the Allspark phase dispatch adapter.

Every child here is a stub script driven through ``--child-command``; no real
Allspark process or model call is ever spawned. Contract under test:
``docs/agent-stack/PHASE-ADAPTER.md``.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts/ai/phase-dispatch.py"
RECORD_SCHEMA = "law-nexus-phase-dispatch/v1"
CAPTURE_LIMIT_BYTES = 256 * 1024
ROLE_FIELDS = [
    "name",
    "brief_file",
    "cwd",
    "pid",
    "started_at",
    "ended_at",
    "duration_ms",
    "exit_code",
    "timed_out",
    "stdout_tail",
    "stderr_tail",
    "outcome",
]

READY_STUB = """import os
import sys

print("cwd=" + os.getcwd())
sys.stdout.write("brief=" + sys.stdin.read())
print("RESULT: T001 ready")
"""

BLOCKED_STUB = """print("RESULT: T001 blocked")"""

QUESTION_STUB = """print("NEEDS-ORCHESTRATOR: which corpus root must the audit use?")"""

CRASH_STUB = """import sys

print("partial progress")
sys.exit(7)
"""

NO_MARKER_STUB = """print("finished without a terminal marker")"""

SLEEPER_STUB = """import time

print("working")
time.sleep(30)
"""

BIG_OUTPUT_STUB = """import sys

print("x" * (300 * 1024))
print("noise", file=sys.stderr)
print("RESULT: T001 ready")
"""

MARKER_STUB = """import pathlib
import sys

pathlib.Path(sys.argv[1]).write_text("spawned", encoding="utf-8")
print("RESULT: T001 ready")
"""

BRANCHING_STUB = """import sys

brief = sys.stdin.read()
if "blocked" in brief:
    print("RESULT: T001 blocked")
elif "question" in brief:
    print("NEEDS-ORCHESTRATOR: which gate applies to this role?")
else:
    print("RESULT: T001 ready")
"""


def write_stub(tmp_path: Path, name: str, body: str) -> Path:
    stub = tmp_path / f"{name}.py"
    stub.write_text(body, encoding="utf-8")
    return stub


def make_role(
    tmp_path: Path, name: str = "build_T001", *, brief: str | None = None, timeout_seconds: int = 30
) -> dict:
    brief_file = tmp_path / f"{name}.brief.md"
    brief_file.write_text(brief or f"Complete brief for {name}.\n", encoding="utf-8")
    cwd = tmp_path / f"{name}.worktree"
    cwd.mkdir()
    return {
        "name": name,
        "brief_file": str(brief_file),
        "cwd": str(cwd),
        "timeout_seconds": timeout_seconds,
        "artifact": str(tmp_path / f"{name}.artifact.json"),
    }


def write_plan(tmp_path: Path, roles: list[dict], phase: str = "build") -> Path:
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"schema": 1, "phase": phase, "roles": roles}), encoding="utf-8")
    return plan


def run_adapter(
    plan: Path, record: Path, *, child_command: list[str] | None = None, dry_run: bool = False
) -> subprocess.CompletedProcess:
    command = [sys.executable, str(ADAPTER), "--plan", str(plan), "--record", str(record)]
    if child_command is not None:
        command += ["--child-command", json.dumps(child_command)]
    if dry_run:
        command.append("--dry-run")
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
        cwd=ROOT,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ready_role_writes_artifact_and_record(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "ready", READY_STUB)
    role = make_role(tmp_path)
    plan = write_plan(tmp_path, [role])
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 0
    artifact = load_json(Path(role["artifact"]))
    assert list(artifact) == ROLE_FIELDS
    assert artifact["name"] == role["name"]
    assert artifact["brief_file"] == role["brief_file"]
    assert artifact["cwd"] == role["cwd"]
    assert isinstance(artifact["pid"], int)
    assert artifact["exit_code"] == 0
    assert artifact["timed_out"] is False
    assert artifact["outcome"] == "ready"
    assert isinstance(artifact["duration_ms"], int)
    assert artifact["started_at"] and artifact["ended_at"]
    assert f"cwd={role['cwd']}" in artifact["stdout_tail"]
    assert "brief=Complete brief for build_T001." in artifact["stdout_tail"]
    assert "RESULT: T001 ready" in artifact["stdout_tail"]
    assert artifact["stderr_tail"] == ""

    summary = load_json(record)
    assert list(summary) == ["schema", "phase", "started_at", "ended_at", "roles", "overall"]
    assert summary["schema"] == RECORD_SCHEMA
    assert summary["phase"] == "build"
    assert summary["overall"] == "ready"
    assert summary["roles"] == [artifact]
    assert not list(tmp_path.glob(".*.tmp"))


def test_blocked_role_exits_4(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "blocked", BLOCKED_STUB)
    role = make_role(tmp_path)
    plan = write_plan(tmp_path, [role])
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 4
    artifact = load_json(Path(role["artifact"]))
    assert artifact["outcome"] == "blocked"
    assert artifact["exit_code"] == 0
    assert load_json(record)["overall"] == "blocked"


def test_question_role_exits_4(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "question", QUESTION_STUB)
    role = make_role(tmp_path)
    plan = write_plan(tmp_path, [role])
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 4
    artifact = load_json(Path(role["artifact"]))
    assert artifact["outcome"] == "question"
    assert "NEEDS-ORCHESTRATOR" in artifact["stdout_tail"]
    assert load_json(record)["overall"] == "question"


def test_failed_role_on_nonzero_exit_exits_5(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "crash", CRASH_STUB)
    role = make_role(tmp_path)
    plan = write_plan(tmp_path, [role])
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 5
    artifact = load_json(Path(role["artifact"]))
    assert artifact["outcome"] == "failed"
    assert artifact["exit_code"] == 7
    assert load_json(record)["overall"] == "failed"


def test_clean_exit_without_terminal_marker_is_failed(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "no_marker", NO_MARKER_STUB)
    role = make_role(tmp_path)
    plan = write_plan(tmp_path, [role])
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 5
    artifact = load_json(Path(role["artifact"]))
    assert artifact["exit_code"] == 0
    assert artifact["outcome"] == "failed"


def test_timeout_kills_the_child_and_no_orphan_remains(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "sleeper", SLEEPER_STUB)
    role = make_role(tmp_path, timeout_seconds=1)
    plan = write_plan(tmp_path, [role])
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 5
    artifact = load_json(Path(role["artifact"]))
    assert artifact["timed_out"] is True
    assert artifact["outcome"] == "timeout"
    assert artifact["exit_code"] == -signal.SIGKILL
    with pytest.raises(ProcessLookupError):
        os.kill(artifact["pid"], 0)
    summary = load_json(record)
    assert summary["overall"] == "timeout"


def test_mixed_non_ready_outcomes_report_mixed_and_exit_4(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "branching", BRANCHING_STUB)
    first = make_role(tmp_path, "build_T001", brief="Report this role as blocked.")
    second = make_role(tmp_path, "review_wave_1_cycle_1", brief="Ask the orchestrator a question.")
    plan = write_plan(tmp_path, [first, second])
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 4
    outcomes = [load_json(Path(role["artifact"]))["outcome"] for role in (first, second)]
    assert outcomes == ["blocked", "question"]
    summary = load_json(record)
    assert summary["overall"] == "mixed"
    assert [entry["name"] for entry in summary["roles"]] == ["build_T001", "review_wave_1_cycle_1"]


def test_independent_roles_get_separate_processes_and_cwds(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "ready", READY_STUB)
    first = make_role(tmp_path, "inspect_codebase")
    second = make_role(tmp_path, "inspect_docs")
    plan = write_plan(tmp_path, [first, second], phase="inspect")
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 0
    artifacts = [load_json(Path(role["artifact"])) for role in (first, second)]
    assert artifacts[0]["pid"] != artifacts[1]["pid"]
    for role, artifact in zip((first, second), artifacts):
        assert f"cwd={role['cwd']}" in artifact["stdout_tail"]
        assert f"brief=Complete brief for {role['name']}." in artifact["stdout_tail"]
        assert artifact["outcome"] == "ready"
    summary = load_json(record)
    assert summary["phase"] == "inspect"
    assert summary["overall"] == "ready"
    assert summary["roles"] == artifacts


def test_stdout_tail_is_bounded_to_256_kib(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "big", BIG_OUTPUT_STUB)
    role = make_role(tmp_path)
    plan = write_plan(tmp_path, [role])
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, str(stub)])

    assert result.returncode == 0
    artifact = load_json(Path(role["artifact"]))
    assert artifact["outcome"] == "ready"
    assert len(artifact["stdout_tail"].encode("utf-8")) == CAPTURE_LIMIT_BYTES
    assert artifact["stdout_tail"].count("x") < 300 * 1024
    assert artifact["stdout_tail"].endswith("RESULT: T001 ready\n")
    assert artifact["stderr_tail"] == "noise\n"


def test_invalid_plan_json_exits_2(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{not json", encoding="utf-8")
    record = tmp_path / "record.json"

    result = run_adapter(plan, record, child_command=[sys.executable, "-c", "print(1)"])

    assert result.returncode == 2
    assert "plan error" in result.stderr
    assert "not valid JSON" in result.stderr
    assert not record.exists()


def test_unknown_plan_key_exits_2(tmp_path: Path) -> None:
    role = make_role(tmp_path)
    cases = [
        {"schema": 1, "phase": "build", "roles": [role], "extra": True},
        {"schema": 1, "phase": "build", "roles": [{**role, "extra": True}]},
    ]
    for index, payload in enumerate(cases):
        plan = tmp_path / f"plan-{index}.json"
        plan.write_text(json.dumps(payload), encoding="utf-8")
        record = tmp_path / f"record-{index}.json"

        result = run_adapter(plan, record, child_command=[sys.executable, "-c", "print(1)"])

        assert result.returncode == 2, result.stderr
        assert "plan error" in result.stderr
        assert "unknown key" in result.stderr
        assert not record.exists()


def test_plan_schema_violations_exit_2(tmp_path: Path) -> None:
    good = make_role(tmp_path)
    missing_brief = make_role(tmp_path, "build_T002")
    missing_brief["brief_file"] = str(tmp_path / "absent.md")
    missing_cwd = make_role(tmp_path, "build_T003")
    missing_cwd["cwd"] = str(tmp_path / "absent-dir")
    cases = [
        ({"schema": 1, "phase": "build"}, "missing required key 'roles'"),
        ({"schema": 2, "phase": "build", "roles": [good]}, "$.schema must be 1"),
        ({"schema": 1, "phase": "", "roles": [good]}, "$.phase must be a non-empty string"),
        ({"schema": 1, "phase": "build", "roles": []}, "$.roles must be a non-empty array"),
        (
            {
                "schema": 1,
                "phase": "build",
                "roles": [{k: v for k, v in good.items() if k != "cwd"}],
            },
            "missing required key 'cwd'",
        ),
        (
            {"schema": 1, "phase": "build", "roles": [{**good, "brief_file": "relative/brief.md"}]},
            "must be an absolute path",
        ),
        (
            {"schema": 1, "phase": "build", "roles": [{**good, "timeout_seconds": 0}]},
            "positive finite number",
        ),
        ({"schema": 1, "phase": "build", "roles": [missing_brief]}, "is not an existing file"),
        ({"schema": 1, "phase": "build", "roles": [missing_cwd]}, "is not an existing directory"),
        (
            {
                "schema": 1,
                "phase": "build",
                "roles": [good, {**good, "artifact": str(tmp_path / "other.json")}],
            },
            "duplicates earlier role",
        ),
    ]
    for index, (payload, fragment) in enumerate(cases):
        plan = tmp_path / f"invalid-{index}.json"
        plan.write_text(json.dumps(payload), encoding="utf-8")
        record = tmp_path / f"record-{index}.json"

        result = run_adapter(plan, record, child_command=[sys.executable, "-c", "print(1)"])

        assert result.returncode == 2, (payload, result.stderr)
        assert "plan error" in result.stderr
        assert fragment in result.stderr
        assert not record.exists()


def test_missing_plan_file_exits_3(tmp_path: Path) -> None:
    record = tmp_path / "record.json"

    result = run_adapter(tmp_path / "absent-plan.json", record)

    assert result.returncode == 3
    assert "usage error" in result.stderr
    assert "cannot read plan" in result.stderr


def test_malformed_child_command_exits_3(tmp_path: Path) -> None:
    role = make_role(tmp_path)
    plan = write_plan(tmp_path, [role])
    for index, raw in enumerate(["not json", "[]", '[""]', '"python3"']):
        record = tmp_path / f"record-{index}.json"

        result = subprocess.run(
            [
                sys.executable,
                str(ADAPTER),
                "--plan",
                str(plan),
                "--record",
                str(record),
                "--child-command",
                raw,
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
            cwd=ROOT,
        )

        assert result.returncode == 3, (raw, result.stderr)
        assert "usage error" in result.stderr
        assert not record.exists()


def test_dry_run_prints_resolved_plan_and_spawns_nothing(tmp_path: Path) -> None:
    stub = write_stub(tmp_path, "marker", MARKER_STUB)
    marker = tmp_path / "spawned.txt"
    role = make_role(tmp_path, timeout_seconds=5)
    plan = write_plan(tmp_path, [role])
    record = tmp_path / "record.json"
    child_command = [sys.executable, str(stub), str(marker)]

    result = run_adapter(plan, record, child_command=child_command, dry_run=True)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema"] == "law-nexus-phase-dispatch-plan/v1"
    assert payload["phase"] == "build"
    assert payload["worker"] == child_command
    assert payload["roles"] == [
        {
            "name": role["name"],
            "brief_file": role["brief_file"],
            "cwd": role["cwd"],
            "timeout_seconds": 5,
            "artifact": role["artifact"],
        }
    ]
    assert not marker.exists()
    assert not Path(role["artifact"]).exists()
    assert not record.exists()


def test_dry_run_resolves_configured_worker_against_primary(tmp_path: Path) -> None:
    role = make_role(tmp_path)
    plan = write_plan(tmp_path, [role])

    result = run_adapter(plan, tmp_path / "record.json", dry_run=True)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["worker"] == [str((ROOT / "scripts/ai/allspark-worker").resolve()), "-p"]
