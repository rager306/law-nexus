"""E1 contract: an interrupted task landing recovers only through the helper.

``isolation.py recover`` is the pipeline's single sanctioned recovery path;
manual git repair is vetoed. The helper is resolved through the tracked
launcher (``python3 -B .gsd-path/status_runtime.py --runtime-path``) so the
contracts below pin the installed runtime rather than a copy, then drive
``recover`` inside temporary git repositories: a detached HEAD is refused
fail-closed, and an interrupted or unlanded task receives an honest verdict
from the helper's own verdict set — never a fabricated success.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / ".gsd-path" / "status_runtime.py"

# The helper's own verdict vocabulary (isolation.py recover docstring and
# LANDED_VERDICTS); anything outside it would be an invented verdict.
RECOVER_VERDICTS = frozenset({"recovered", "resume", "reconcile", "block", "none"})
LANDED_VERDICTS = frozenset({"recovered", "attested"})

TASK_TEXT = """\
---
id: T001
title: Sample interrupted task
wave: 1
deps: []
status: {status}
agent: null
base: null
worktree: null
task_branch: null
files:
  - src/example.py
---

# T001 — Sample interrupted task
"""


@pytest.fixture(scope="module")
def isolation_helper() -> Path:
    """Resolve the pipeline isolation helper through the tracked launcher."""
    resolution = subprocess.run(
        ["python3", "-B", str(LAUNCHER), "--runtime-path", "--repo", str(ROOT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resolution.returncode == 0, resolution.stderr
    helper = Path(resolution.stdout.strip()) / "isolation.py"
    assert helper.is_file(), f"isolation.py missing from the resolved runtime: {helper}"
    return helper


def _seed_repo(tmp_path: Path, status: str) -> Path:
    """A minimal git repository whose committed task inventory holds one task."""
    repo = tmp_path / "repo"
    tasks = repo / ".project" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "T001.md").write_text(TASK_TEXT.format(status=status), encoding="utf-8")

    def git(*arguments: str) -> str:
        run = subprocess.run(
            ["git", *arguments], cwd=repo, check=True, capture_output=True, text=True
        )
        return run.stdout.strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "recovery-test@example.com")
    git("config", "user.name", "Path Recovery Test")
    git("add", ".")
    git("commit", "-q", "-m", "chore: seed task inventory")
    return repo


def _git_output(repo: Path, *arguments: str) -> str:
    run = subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True, text=True)
    return run.stdout.strip()


def _recover(helper: Path, repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-B", str(helper), "recover", "--repo", str(repo)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def test_recover_refuses_detached_head(isolation_helper: Path, tmp_path: Path) -> None:
    """A detached HEAD is refused fail-closed; no verdict is invented for it."""
    repo = _seed_repo(tmp_path, "in-progress")
    _git_output(repo, "checkout", "-q", "--detach", "HEAD")
    refusal = _recover(isolation_helper, repo)
    assert refusal.returncode != 0
    assert "detached" in refusal.stderr


def test_unlanded_task_reports_none_not_success(isolation_helper: Path, tmp_path: Path) -> None:
    """A pending task with no retained isolate is honestly ``none``."""
    repo = _seed_repo(tmp_path, "pending")
    report = json.loads(_recover(isolation_helper, repo).stdout)
    assert report["verdict"] == "ok"
    [task] = report["tasks"]
    assert task["task_id"] == "T001"
    assert task["verdict"] == "none"
    assert task["verdict"] in RECOVER_VERDICTS
    assert task["verdict"] not in LANDED_VERDICTS
    assert "no retained isolate" in task["reason"]


def test_interrupted_task_reports_resume_not_landed(isolation_helper: Path, tmp_path: Path) -> None:
    """An interrupted task with a retained branch is ``resume`` at its base."""
    repo = _seed_repo(tmp_path, "in-progress")
    head = _git_output(repo, "rev-parse", "HEAD")
    _git_output(repo, "branch", "gsd-path-task/T001")
    report = json.loads(_recover(isolation_helper, repo).stdout)
    assert report["verdict"] == "ok"
    [task] = report["tasks"]
    assert task["verdict"] == "resume"
    assert task["verdict"] in RECOVER_VERDICTS
    assert task["verdict"] not in LANDED_VERDICTS
    assert task["base"] == head
    assert task["task_branch"] == "gsd-path-task/T001"
