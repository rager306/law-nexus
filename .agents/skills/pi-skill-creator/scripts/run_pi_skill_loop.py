#!/usr/bin/env python3
"""Orchestrate the local PI/GSD skill eval loop.

This command is intentionally honest about execution state:
- It always validates the skill and prepares an iteration workspace.
- If outputs/answer.md files are missing, it stops with a pending status.
- If outputs exist, it grades, aggregates, updates history, and generates a report.

It does not fake model outputs and does not shell out to Claude Code-specific
`claude -p`. By default it prepares prompts and waits for outputs; when called
with `--execute gsd-print` or `--execute command`, it runs a real local command
and saves stdout/stderr/exit-code evidence before grading.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
RUNNER = SCRIPT_DIR / "run_pi_skill_eval.py"
GRADER = SCRIPT_DIR / "grade_pi_skill_eval.py"
AGGREGATOR = SCRIPT_DIR / "aggregate_pi_skill_benchmark.py"
REPORTER = SCRIPT_DIR / "generate_pi_skill_report.py"
EXECUTOR = SCRIPT_DIR / "execute_pi_skill_eval.py"
VALIDATOR = SCRIPT_DIR / "validate_pi_skill.py"


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


def next_iteration(workspace: Path) -> int:
    if not workspace.exists():
        return 1
    nums = []
    for child in workspace.iterdir():
        if child.is_dir() and child.name.startswith("iteration-"):
            suffix = child.name.removeprefix("iteration-")
            if suffix.isdigit():
                nums.append(int(suffix))
    return max(nums, default=0) + 1


def outputs_ready(iteration_dir: Path) -> bool:
    run_dirs = [p for p in iteration_dir.glob("eval-*/*") if (p / "outputs").is_dir()]
    return bool(run_dirs) and all((p / "outputs" / "answer.md").is_file() for p in run_dirs)


def load_description(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def update_history(workspace: Path, iteration_dir: Path, skill_dir: Path, benchmark: dict[str, Any]) -> None:
    history_path = workspace / "history.json"
    if history_path.is_file():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    else:
        history = {
            "started_at": datetime.now(UTC).isoformat(),
            "skill_name": skill_dir.name,
            "current_best": None,
            "iterations": [],
        }
    best_rate = -1.0
    for item in history.get("iterations", []):
        best_rate = max(best_rate, float(item.get("pass_rate", 0.0)))
    with_skill = next((c for c in benchmark.get("configurations", []) if c.get("configuration") == "with_skill"), None)
    pass_rate = float(with_skill.get("pass_rate", 0.0)) if with_skill else 0.0
    is_best = pass_rate >= best_rate
    record = {
        "iteration": iteration_dir.name,
        "parent": history.get("current_best"),
        "benchmark_path": str(iteration_dir / "benchmark.json"),
        "pass_rate": pass_rate,
        "grading_result": "current_best" if is_best else "not_best",
        "description": load_description(skill_dir),
        "changes": [],
        "is_current_best": is_best,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    for item in history.get("iterations", []):
        item["is_current_best"] = False
    history.setdefault("iterations", []).append(record)
    if is_best:
        history["current_best"] = iteration_dir.name
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local PI/GSD skill eval loop")
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--iteration", type=int, default=None)
    parser.add_argument("--baseline", choices=["baseline", "old_skill"], default="baseline")
    parser.add_argument("--no-prepare", action="store_true", help="Use existing iteration workspace instead of preparing a new one")
    parser.add_argument("--min-pass-rate", type=float, default=0.0)
    parser.add_argument("--execute", choices=["none", "gsd-print", "command"], default="none", help="Optionally execute generated prompts before grading")
    parser.add_argument("--execute-command", default=None, help="Command override for execution; prompt is appended unless command contains {prompt}")
    parser.add_argument("--execute-timeout", type=int, default=300)
    parser.add_argument("--execute-overwrite", action="store_true")
    args = parser.parse_args()

    workspace = args.workspace or args.skill_dir.with_name(f"{args.skill_dir.name}-workspace")
    validate = run_cmd([sys.executable, str(VALIDATOR), str(args.skill_dir), "--require-evals"])
    print(validate.stdout, end="")
    if validate.returncode != 0:
        print(validate.stderr, file=sys.stderr)
        return validate.returncode

    if args.no_prepare:
        iteration_num = args.iteration or next_iteration(workspace) - 1
        iteration_dir = workspace / f"iteration-{iteration_num}"
        if not iteration_dir.is_dir():
            print(f"Missing iteration directory: {iteration_dir}", file=sys.stderr)
            return 1
    else:
        runner_args = [sys.executable, str(RUNNER), str(args.skill_dir), "--workspace", str(workspace), "--baseline", args.baseline]
        if args.iteration:
            runner_args.extend(["--iteration", str(args.iteration)])
        prepared = run_cmd(runner_args)
        print(prepared.stdout, end="")
        if prepared.returncode != 0:
            print(prepared.stderr, file=sys.stderr)
            return prepared.returncode
        iteration_num = args.iteration or next_iteration(workspace) - 1
        iteration_dir = workspace / f"iteration-{iteration_num}"

    if args.execute != "none" and not outputs_ready(iteration_dir):
        exec_args = [
            sys.executable,
            str(EXECUTOR),
            str(iteration_dir),
            "--backend",
            args.execute,
            "--timeout",
            str(args.execute_timeout),
        ]
        if args.execute_command:
            exec_args.extend(["--command", args.execute_command])
        if args.execute_overwrite:
            exec_args.append("--overwrite")
        executed = run_cmd(exec_args)
        print(executed.stdout, end="")
        if executed.returncode != 0:
            print(executed.stderr, file=sys.stderr)
            return executed.returncode

    if not outputs_ready(iteration_dir):
        manifest_path = iteration_dir / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        manifest["status"] = "pending_outputs"
        manifest["next_step"] = "Execute generated EXECUTOR_PROMPT.md files and save outputs/answer.md, then rerun with --no-prepare."
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Pending outputs: {iteration_dir}")
        print("Execute generated prompts, save outputs/answer.md, then rerun with --no-prepare.")
        return 2

    graded = run_cmd([sys.executable, str(GRADER), str(iteration_dir), "--min-pass-rate", str(args.min_pass_rate)])
    print(graded.stdout, end="")
    if graded.returncode != 0:
        print(graded.stderr, file=sys.stderr)
        return graded.returncode

    aggregated = run_cmd([sys.executable, str(AGGREGATOR), str(iteration_dir), "--skill-name", args.skill_dir.name])
    print(aggregated.stdout, end="")
    if aggregated.returncode != 0:
        print(aggregated.stderr, file=sys.stderr)
        return aggregated.returncode

    benchmark = json.loads((iteration_dir / "benchmark.json").read_text(encoding="utf-8"))
    update_history(workspace, iteration_dir, args.skill_dir, benchmark)
    reported = run_cmd([sys.executable, str(REPORTER), str(iteration_dir)])
    print(reported.stdout, end="")
    if reported.returncode != 0:
        print(reported.stderr, file=sys.stderr)
        return reported.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
