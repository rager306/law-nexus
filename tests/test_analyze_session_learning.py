from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/analyze-session-learning.py")


def write_exec_fixture(gsd_dir: Path, run_id: str, *, purpose: str, exit_code: int, stderr: str = "", stdout: str = "") -> None:
    exec_dir = gsd_dir / "exec"
    exec_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = exec_dir / f"{run_id}.stdout"
    stderr_path = exec_dir / f"{run_id}.stderr"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    (exec_dir / f"{run_id}.meta.json").write_text(
        json.dumps(
            {
                "purpose": purpose,
                "runtime": "bash",
                "exit_code": exit_code,
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
            }
        ),
        encoding="utf-8",
    )


def run_report(tmp_path: Path, gsd_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gsd-dir",
            str(gsd_dir),
            "--json-output",
            str(tmp_path / "session-learning-report.json"),
            "--markdown-output",
            str(tmp_path / "session-learning-report.md"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_session_learning_report_detects_failure_and_memory_candidates(tmp_path: Path) -> None:
    gsd_dir = tmp_path / ".gsd"
    write_exec_fixture(
        gsd_dir,
        "failed-run",
        purpose="verify skill",
        exit_code=1,
        stderr="Traceback: missing evals/evals.json failed",
    )
    result = run_report(tmp_path, gsd_dir)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "session-learning-report.json").read_text(encoding="utf-8"))
    assert report["exec_summary"]["failures"]
    assert report["memory_candidates"]
    assert any(rec["kind"] == "failure-learning" for rec in report["recommendations"])
    assert (tmp_path / "session-learning-report.md").read_text(encoding="utf-8").startswith("# Session Learning Retrospective")


def test_session_learning_report_handles_empty_evidence(tmp_path: Path) -> None:
    gsd_dir = tmp_path / ".gsd"
    gsd_dir.mkdir()
    result = run_report(tmp_path, gsd_dir)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "session-learning-report.json").read_text(encoding="utf-8"))
    assert report["exec_summary"]["total"] == 0
    assert report["recommendations"]
    assert report["recommendations"][0]["kind"] in {"no-action", "skill-verification", "gsd-state"}


def test_session_learning_report_does_not_treat_successful_zero_failed_output_as_failure(tmp_path: Path) -> None:
    gsd_dir = tmp_path / ".gsd"
    write_exec_fixture(
        gsd_dir,
        "success-run",
        purpose="quality gate",
        exit_code=0,
        stdout="Summary: failed: 0, passed: 61. All checks passed!",
    )
    result = run_report(tmp_path, gsd_dir)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "session-learning-report.json").read_text(encoding="utf-8"))
    assert report["exec_summary"]["failures"] == []
