#!/usr/bin/env python3
"""Thin launcher for installed GSD Path 1.6.2 helpers; not a host adapter.

Invoke the copy in the primary checkout by its absolute path when working in a
task worktree. All state changes belong to native helpers; there is no retry loop.
"""

import argparse
import json
import re
import runpy
import shlex
import subprocess
import sys
from pathlib import Path

SHARED = runpy.run_path(str(Path(__file__).with_name("stack-env.py")))
ROOT = SHARED["canonical_root"](Path(__file__).resolve().parents[2])
# Preserve the caller's HOME: both host and Allspark homes have the exact
# native runtime restored. Everything else comes from one shared profile.
ENV = SHARED["build_env"](ROOT, isolated=False)
BUILD = ROOT / ".agents/skills/gsd-path-build/scripts"
SHIM = ROOT / ".gsd-path/status_runtime.py"
CONFIG = ROOT / ".ai/path-run.json"


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def settings():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    keys = {
        "schema",
        "projectDir",
        "worker",
        "capacity",
        "childTimeoutSeconds",
        "pollSeconds",
        "maxAttempts",
    }
    if (
        not isinstance(data, dict)
        or set(data) != keys
        or type(data["schema"]) is not int
        or data["schema"] != 1
    ):
        raise ValueError(f"invalid launcher configuration: {CONFIG}")
    if data["projectDir"] not in (".project", ".project/next"):
        raise ValueError("projectDir must be .project or .project/next")
    worker = data["worker"]
    if (
        not isinstance(worker, list)
        or not worker
        or any(not isinstance(item, str) or not item or "\0" in item for item in worker)
    ):
        raise ValueError("worker must be a nonempty argv array of strings")
    for key in ("capacity", "maxAttempts"):
        if type(data[key]) is not int or data[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("childTimeoutSeconds", "pollSeconds"):
        if type(data[key]) not in (int, float) or not 0 < data[key] < float("inf"):
            raise ValueError(f"{key} must be positive and finite")
    return data


def python(script, *arguments):
    if not script.is_file():
        raise ValueError(f"missing upstream helper: {script}; run the pinned bootstrap")
    return [sys.executable, "-B", str(script), *map(str, arguments)]


def runtime():
    result = subprocess.run(
        python(SHIM, "--repo", ROOT, "--runtime-path"),
        cwd=ROOT,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Path runtime resolution failed")
    path = Path(result.stdout.strip())
    if not path.is_absolute() or not path.is_dir():
        raise ValueError("Path runtime resolver did not return an absolute directory")
    return path


def worker_command(data):
    argv = data["worker"][:]
    if not any(flag in argv for flag in ("-p", "--print")):
        raise ValueError("Path worker argv must include -p/--print; Path does not add it")
    executable = (ROOT / argv[0]).resolve()
    if not executable.is_file():
        raise ValueError(f"worker is missing: {executable}")
    argv[0] = str(executable)
    # Path parses this string with shlex.split; it does not execute a shell.
    return shlex.join(argv)


def command(args):
    if args.action in ("status", "runtime"):
        extra = ["--runtime-path"] if args.action == "runtime" else []
        return python(SHIM, "--repo", ROOT, *extra)
    data = settings()
    common = ["--repo", str(ROOT), "--project-dir", data["projectDir"]]
    if args.action in ("validate", "resume-checkpoint"):
        extra = ["--repo", str(ROOT)] if args.action == "resume-checkpoint" else common
        return python(runtime() / "pipeline_state.py", args.action, *extra)
    if args.action in ("route", "gate-plan", "lint-round", "approve-plan"):
        extra = []
        if args.action == "approve-plan":
            if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", args.expected_head):
                raise ValueError("--expected-head must be a full reviewed Git commit SHA")
            extra = ["--expected-head", args.expected_head]
        return python(BUILD / "workflow_run.py", args.action, *common, *extra)
    if args.action == "dispatch-status":
        return python(BUILD / "dispatch_driver.py", "status", "--repo", ROOT)
    if args.action == "answer":
        return python(
            BUILD / "dispatch_driver.py",
            "answer",
            "--repo",
            ROOT,
            "--task-id",
            args.task_id,
            "--answer",
            args.answer,
        )
    if args.action == "complete":
        return python(BUILD / "dispatch_driver.py", "complete", *common)
    extra = [
        "--wave",
        str(args.wave),
        "--child-command",
        worker_command(data),
        "--child-timeout",
        str(data["childTimeoutSeconds"]),
        "--wait",
        str(data["pollSeconds"]),
    ]
    if args.action == "round":
        extra += ["--capacity", str(data["capacity"]), "--max-attempts", str(data["maxAttempts"])]
    else:
        extra += ["--cycle", str(args.cycle)]
        if args.repair_evidence:
            receipt = (ROOT / args.repair_evidence).resolve()
            if not receipt.is_file():
                raise ValueError(f"repair evidence is missing: {receipt}")
            extra += ["--repair-evidence", str(receipt)]
    return python(BUILD / "dispatch_driver.py", args.action, *common, *extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="print argv/cwd without running the selected helper"
    )
    actions = parser.add_subparsers(dest="action", required=True)
    for name in (
        "status",
        "runtime",
        "validate",
        "route",
        "gate-plan",
        "lint-round",
        "dispatch-status",
        "complete",
        "resume-checkpoint",
    ):
        actions.add_parser(name)
    approval = actions.add_parser("approve-plan", help="only after explicit owner approval")
    approval.add_argument("--expected-head", required=True)
    answer = actions.add_parser("answer", help="record an actual orchestrator/owner answer")
    answer.add_argument("--task-id", required=True)
    answer.add_argument("--answer", required=True)
    for name in ("round", "review"):
        child = actions.add_parser(name)
        child.add_argument("--wave", type=positive, required=True)
        if name == "review":
            child.add_argument("--cycle", type=positive, required=True)
            child.add_argument("--repair-evidence", type=Path)
    args = parser.parse_args()
    try:
        argv = command(args)
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "cwd": str(ROOT),
                        "argv": argv,
                        "runtimeHome": ENV["HOME"],
                        "worktreeStorage": ENV["GSD_PATH_WORKTREE_ROOT"],
                    },
                    indent=2,
                )
            )
            return 0
        return subprocess.run(argv, cwd=ROOT, env=ENV, check=False).returncode
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"path-run: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
