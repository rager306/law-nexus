#!/usr/bin/env python3
"""Execute PI/GSD skill eval prompts and save real output artifacts.

This script fills an iteration workspace prepared by run_pi_skill_eval.py. It is
honest about execution: it runs an explicit local command, captures stdout/stderr
and exit code, and writes outputs/answer.md only from the command's real stdout.

Default backend is `gsd-print`, which expands to:
    gsd --print --no-session <prompt>

Use `--command` for tests or custom runners. The prompt text is appended as the
last argv item unless the command contains `{prompt}`.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def run_dirs(iteration_dir: Path, configurations: set[str] | None) -> list[Path]:
    dirs = []
    for candidate in sorted(iteration_dir.glob("eval-*/*")):
        if not candidate.is_dir() or not (candidate / "outputs").is_dir():
            continue
        if configurations and candidate.name not in configurations:
            continue
        if not (candidate / "EXECUTOR_PROMPT.md").is_file():
            continue
        dirs.append(candidate)
    return dirs


def build_command(base_command: str, prompt: str) -> list[str]:
    parts = shlex.split(base_command)
    if not parts:
        raise ValueError("execution command must not be empty")
    if any("{prompt}" in part for part in parts):
        return [part.replace("{prompt}", prompt) for part in parts]
    return [*parts, prompt]


def execute_run(run_dir: Path, base_command: str, timeout: int, overwrite: bool) -> dict[str, Any]:
    outputs = run_dir / "outputs"
    answer = outputs / "answer.md"
    if answer.is_file() and not overwrite:
        status = {
            "status": "skipped_existing_output",
            "run_dir": str(run_dir),
            "answer_path": str(answer),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        (run_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        return status

    prompt = (run_dir / "EXECUTOR_PROMPT.md").read_text(encoding="utf-8")
    command = build_command(base_command, prompt)
    started = time.monotonic()
    started_at = datetime.now(UTC).isoformat()
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        status = {
            "status": "timeout",
            "run_dir": str(run_dir),
            "command": command[:2] + ["<prompt>"],
            "started_at": started_at,
            "duration_ms": duration_ms,
            "timeout_seconds": timeout,
            "exit_code": None,
            "timed_out": True,
        }
        (outputs / "stdout.txt").write_text(stdout, encoding="utf-8")
        (outputs / "stderr.txt").write_text(stderr, encoding="utf-8")
        (outputs / "run.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        (run_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        return status

    duration_ms = int((time.monotonic() - started) * 1000)
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (outputs / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    answer_source = None
    if completed.returncode == 0:
        if answer.is_file():
            answer_source = "executor_created_file"
        else:
            answer.write_text(completed.stdout, encoding="utf-8")
            answer_source = "stdout_fallback"
    status = {
        "status": "complete" if completed.returncode == 0 else "failed",
        "run_dir": str(run_dir),
        "command": command[:2] + ["<prompt>"],
        "started_at": started_at,
        "duration_ms": duration_ms,
        "timeout_seconds": timeout,
        "exit_code": completed.returncode,
        "timed_out": timed_out,
        "stdout_path": str(outputs / "stdout.txt"),
        "stderr_path": str(outputs / "stderr.txt"),
        "answer_path": str(answer) if completed.returncode == 0 else None,
        "answer_source": answer_source,
    }
    (outputs / "run.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    (run_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


def execute_iteration(iteration_dir: Path, base_command: str, timeout: int, overwrite: bool, configurations: set[str] | None) -> dict[str, Any]:
    runs = []
    for run_dir in run_dirs(iteration_dir, configurations):
        runs.append(execute_run(run_dir, base_command, timeout, overwrite))
    complete = sum(1 for item in runs if item["status"] in {"complete", "skipped_existing_output"})
    failed = len(runs) - complete
    report = {
        "iteration": iteration_dir.name,
        "execution_kind": "real_subprocess",
        "actual_activation": "unavailable",
        "actual_activation_note": "PI/GSD headless execution output does not currently expose durable skill activation telemetry.",
        "summary": {
            "runs": len(runs),
            "complete": complete,
            "failed": failed,
        },
        "runs": runs,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    (iteration_dir / "execution-summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute PI/GSD skill eval prompts")
    parser.add_argument("iteration_dir", type=Path)
    parser.add_argument("--backend", choices=["gsd-print", "command"], default="gsd-print")
    parser.add_argument("--command", default=None, help="Command for backend=command, or override for gsd-print")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--configuration", action="append", choices=["with_skill", "baseline", "old_skill"], help="Limit execution to one or more configurations")
    args = parser.parse_args()

    if not args.iteration_dir.is_dir():
        print(f"Missing iteration directory: {args.iteration_dir}", file=sys.stderr)
        return 1
    command = args.command or "gsd --print --no-session"
    if args.backend == "command" and not args.command:
        print("--command is required when --backend=command", file=sys.stderr)
        return 1
    try:
        report = execute_iteration(args.iteration_dir, command, args.timeout, args.overwrite, set(args.configuration or []) or None)
    except (OSError, ValueError) as exc:
        print(f"PI skill eval execution failed: {exc}", file=sys.stderr)
        return 1
    print(
        "PI skill eval execution: "
        f"{report['summary']['complete']}/{report['summary']['runs']} runs complete; "
        f"{report['summary']['failed']} failed"
    )
    print(f"Execution summary: {args.iteration_dir / 'execution-summary.json'}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
