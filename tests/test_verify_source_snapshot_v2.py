"""Behavioral contract for scripts/verify-source-snapshot-v2.py (MIGRATION.md section 4.3)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-source-snapshot-v2.py"
SCHEMA_ID = "law-nexus-source-snapshot/v2"
ALGORITHM_ID = "sha256+sorted-paths/v1"


def git(repo: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, f"git {args} failed: {proc.stderr}"


def git_head(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return proc.stdout.strip()


def run_script(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        check=False,
    )


def snapshot_stdout(repo: Path) -> dict[str, Any]:
    proc = run_script("--repo", str(repo))
    assert proc.returncode == 0, proc.stderr.decode("utf-8")
    return json.loads(proc.stdout.decode("utf-8"))


def write(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")


def commit_all(repo: Path, *names: str) -> None:
    for name in names:
        write(repo, name, f"content of {name}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture commit")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "snapshot@example.com")
    git(repo, "config", "user.name", "Snapshot Test")
    return repo


def test_sorted_ordering_and_documented_aggregate_rule(repo: Path) -> None:
    commit_all(repo, "b.txt", "Z.txt", "a.txt", "Б.txt", "а.txt")

    document = snapshot_stdout(repo)

    assert document["schema"] == SCHEMA_ID
    assert document["algorithm"] == ALGORITHM_ID
    paths = [entry["path"] for entry in document["files"]]
    assert paths == ["Z.txt", "a.txt", "b.txt", "Б.txt", "а.txt"]
    assert paths == sorted(paths, key=lambda path: path.encode("utf-8"))

    # Recompute the aggregate from the documented canonical line rule.
    hasher = hashlib.sha256()
    for entry in document["files"]:
        digest = entry["sha256"] if entry["sha256"] is not None else "-"
        size = str(entry["bytes"]) if entry["bytes"] is not None else "-"
        line = f"{entry['path']}\0{entry['status']}\0{digest}\0{size}\n"
        hasher.update(line.encode("utf-8"))
    assert hasher.hexdigest() == document["aggregate"]

    again = snapshot_stdout(repo)
    assert again["files"] == document["files"]
    assert again["aggregate"] == document["aggregate"]
    assert again["head"] == document["head"]


def test_status_classification_tracked_dirty_untracked_deleted_ignored(repo: Path) -> None:
    write(repo, ".gitignore", "ignored.txt\n")
    commit_all(repo, "clean.txt", "dirty.txt", "staged.txt", "gone.txt")

    write(repo, "dirty.txt", "modified in the worktree, not staged\n")
    write(repo, "staged.txt", "modified and staged, worktree matches the index\n")
    git(repo, "add", "staged.txt")
    write(repo, "ignored.txt", "matched by .gitignore\n")
    write(repo, "new.txt", "untracked newcomer\n")
    (repo / "gone.txt").unlink()

    document = snapshot_stdout(repo)
    entries = {entry["path"]: entry for entry in document["files"]}

    assert entries["clean.txt"]["status"] == "tracked-clean"
    assert entries["staged.txt"]["status"] == "tracked-clean"
    assert entries["dirty.txt"]["status"] == "tracked-dirty"
    assert entries["new.txt"]["status"] == "untracked"
    assert entries["gone.txt"]["status"] == "deleted"
    assert entries["gone.txt"]["sha256"] is None
    assert entries["gone.txt"]["bytes"] is None
    assert "ignored.txt" not in entries
    assert entries["clean.txt"]["sha256"] == hashlib.sha256(b"content of clean.txt\n").hexdigest()
    assert entries["clean.txt"]["bytes"] == len(b"content of clean.txt\n")


def test_symlink_entries_hash_the_target_string_without_following(repo: Path) -> None:
    write(repo, "target.txt", "target file content\n")
    os.symlink("target.txt", repo / "tracked-link")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture commit")
    os.symlink("target.txt", repo / "untracked-link")
    os.symlink("missing-target", repo / "dangling-link")

    document = snapshot_stdout(repo)
    entries = {entry["path"]: entry for entry in document["files"]}

    expected = hashlib.sha256(b"target.txt").hexdigest()
    assert entries["tracked-link"]["type"] == "symlink"
    assert entries["tracked-link"]["status"] == "tracked-clean"
    assert entries["tracked-link"]["sha256"] == expected
    assert entries["tracked-link"]["bytes"] == len(b"target.txt")
    assert entries["untracked-link"] == {
        "path": "untracked-link",
        "status": "untracked",
        "sha256": expected,
        "bytes": len(b"target.txt"),
        "type": "symlink",
    }
    assert entries["dangling-link"]["type"] == "symlink"
    assert entries["dangling-link"]["sha256"] == hashlib.sha256(b"missing-target").hexdigest()

    # Rewriting the referenced file must not change link digests.
    write(repo, "target.txt", "completely different content\n")
    retargeted = snapshot_stdout(repo)
    entries_after = {entry["path"]: entry for entry in retargeted["files"]}
    assert entries_after["untracked-link"]["sha256"] == expected
    assert entries_after["tracked-link"]["sha256"] == expected

    # A tracked symlink whose target changed differs from the index.
    (repo / "tracked-link").unlink()
    os.symlink("target.txt.bak", repo / "tracked-link")
    changed = snapshot_stdout(repo)
    entries_changed = {entry["path"]: entry for entry in changed["files"]}
    assert entries_changed["tracked-link"]["status"] == "tracked-dirty"
    assert (
        entries_changed["tracked-link"]["sha256"] == hashlib.sha256(b"target.txt.bak").hexdigest()
    )


def test_own_output_exclusion_makes_write_and_check_idempotent(repo: Path, tmp_path: Path) -> None:
    commit_all(repo, "a.txt", "b.txt")

    inside = repo / "snapshot.json"
    proc = run_script("--repo", str(repo), "--out", str(inside))
    assert proc.returncode == 0, proc.stderr.decode("utf-8")
    document = json.loads(inside.read_text(encoding="utf-8"))
    assert "snapshot.json" not in [entry["path"] for entry in document["files"]]

    assert run_script("--repo", str(repo), "--check", str(inside)).returncode == 0

    outside = tmp_path / "outside.json"
    assert run_script("--repo", str(repo), "--out", str(outside)).returncode == 0
    assert run_script("--repo", str(repo), "--check", str(outside)).returncode == 0

    # Without --out/--check the enumeration has no exclusion and sees the file.
    plain = snapshot_stdout(repo)
    assert "snapshot.json" in [entry["path"] for entry in plain["files"]]


def test_check_exit_codes_and_diff_summary(repo: Path, tmp_path: Path) -> None:
    commit_all(repo, "clean.txt", "doomed.txt", "stable.txt")
    stored = repo / "snapshot.json"
    assert run_script("--repo", str(repo), "--out", str(stored)).returncode == 0

    write(repo, "clean.txt", "rewritten\n")
    write(repo, "extra.txt", "added after the snapshot\n")
    git(repo, "rm", "-q", "doomed.txt")
    (repo / "stable.txt").unlink()

    mismatch = run_script("--repo", str(repo), "--check", str(stored))
    assert mismatch.returncode == 3
    summary = mismatch.stdout.decode("utf-8")
    assert "source snapshot mismatch: 2 changed, 1 added, 1 removed" in summary
    assert "changed: clean.txt, stable.txt" in summary
    assert "added: extra.txt" in summary
    assert "removed: doomed.txt" in summary

    # Re-baseline, then move only HEAD: files identical, head differs.
    assert run_script("--repo", str(repo), "--out", str(stored)).returncode == 0
    old_head = git_head(repo)
    git(repo, "commit", "--allow-empty", "-q", "-m", "head moves")
    head_only = run_script("--repo", str(repo), "--check", str(stored))
    assert head_only.returncode == 3
    head_summary = head_only.stdout.decode("utf-8")
    assert "source snapshot mismatch: head changed" in head_summary
    assert f"head: {old_head} -> {git_head(repo)}" in head_summary
    assert "changed:" not in head_summary

    # Operational errors (exit 1): missing, invalid, and foreign-schema snapshots.
    missing = run_script("--repo", str(repo), "--check", str(tmp_path / "absent.json"))
    assert missing.returncode == 1
    assert missing.stderr

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not json", encoding="utf-8")
    assert run_script("--repo", str(repo), "--check", str(invalid)).returncode == 1

    foreign = tmp_path / "foreign.json"
    foreign.write_text(json.dumps({"schema": "other/v1"}), encoding="utf-8")
    assert run_script("--repo", str(repo), "--check", str(foreign)).returncode == 1

    # Usage errors (exit 2): --out together with --check, unknown arguments.
    both = run_script("--repo", str(repo), "--out", "x.json", "--check", "y.json")
    assert both.returncode == 2
    assert run_script("--repo", str(repo), "--bogus").returncode == 2


def test_operational_error_when_repo_is_not_a_git_work_tree(tmp_path: Path) -> None:
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    proc = run_script("--repo", str(plain))
    assert proc.returncode == 1
    assert proc.stderr


def test_head_records_the_current_commit(repo: Path) -> None:
    commit_all(repo, "a.txt")
    first = snapshot_stdout(repo)
    assert first["head"] == git_head(repo)

    git(repo, "commit", "--allow-empty", "-q", "-m", "second")
    second = snapshot_stdout(repo)
    assert second["head"] == git_head(repo)
    assert second["head"] != first["head"]


def test_empty_repository_records_null_head_and_still_works(repo: Path) -> None:
    write(repo, "untracked.txt", "never committed\n")
    write(repo, "staged.txt", "staged but unborn HEAD\n")
    git(repo, "add", "staged.txt")

    document = snapshot_stdout(repo)
    assert document["head"] is None
    entries = {entry["path"]: entry for entry in document["files"]}
    assert entries["untracked.txt"]["status"] == "untracked"
    assert entries["staged.txt"]["status"] == "tracked-clean"
    assert document["aggregate"]

    stored = repo / "snapshot.json"
    assert run_script("--repo", str(repo), "--out", str(stored)).returncode == 0
    assert run_script("--repo", str(repo), "--check", str(stored)).returncode == 0


def test_diff_listing_is_capped_at_fifty_paths(repo: Path) -> None:
    for index in range(60):
        write(repo, f"f{index:03d}.txt", f"content {index}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture commit")
    stored = repo / "snapshot.json"
    assert run_script("--repo", str(repo), "--out", str(stored)).returncode == 0

    for index in range(60):
        write(repo, f"f{index:03d}.txt", f"rewritten {index}\n")
    proc = run_script("--repo", str(repo), "--check", str(stored))
    assert proc.returncode == 3
    summary = proc.stdout.decode("utf-8")
    assert "60 changed" in summary
    changed_line = next(line for line in summary.splitlines() if line.startswith("changed: "))
    assert len(changed_line.split(", ")) == 50
    assert "diff listing capped at 50 paths; 10 more not listed" in summary
